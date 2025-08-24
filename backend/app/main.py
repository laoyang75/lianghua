"""
量化回测系统后端服务主入口
基于 FastAPI + DuckDB + Polars 构建
"""

import argparse
import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import init_database, get_db_manager
from app.api import health, data, labels, backtest, experiments, websocket, system


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("正在启动量化回测系统后端服务...")
    
    try:
        # 初始化数据库
        await init_database()
        logger.info("数据库初始化完成")
        
        # 检查数据目录
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        os.makedirs(settings.LOG_DIR, exist_ok=True)
        logger.info(f"数据目录: {settings.DATA_DIR}")
        
        logger.info(f"后端服务启动成功，端口: {settings.PORT}")
        
    except Exception as e:
        logger.error(f"服务启动失败: {e}")
        sys.exit(1)
    
    yield
    
    # 关闭时清理
    logger.info("正在关闭后端服务...")
    db_manager = get_db_manager()
    if db_manager:
        db_manager.close()


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    
    app = FastAPI(
        title="量化回测系统 API",
        description="基于 FastAPI + DuckDB + Polars 构建的量化回测系统",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:5182", "http://127.0.0.1:5173", "http://127.0.0.1:5182"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 路由注册
    app.include_router(health.router, tags=["健康检查"])
    app.include_router(data.router, prefix="/data", tags=["数据管理"])
    app.include_router(labels.router, prefix="/labels", tags=["标签管理"])
    app.include_router(backtest.router, prefix="/backtest", tags=["回测"])
    app.include_router(experiments.router, prefix="/experiments", tags=["实验管理"])
    app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
    app.include_router(system.router, prefix="/system", tags=["系统管理"])

    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"全局异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": f"服务器内部错误: {str(exc)}"}
        )

    # 404 处理
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        return JSONResponse(
            status_code=404,
            content={"detail": "接口不存在"}
        )

    return app


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="量化回测系统后端服务")
    parser.add_argument(
        "--port", 
        type=int, 
        default=5318, 
        help="服务端口 (默认: 5317)"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default="127.0.0.1", 
        help="服务地址 (默认: 127.0.0.1)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="启用调试模式"
    )
    parser.add_argument(
        "--reload", 
        action="store_true", 
        help="启用自动重载"
    )
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    # 更新设置
    settings.PORT = args.port
    settings.HOST = args.host
    settings.DEBUG = args.debug
    
    # 配置日志
    logger.remove()  # 移除默认处理器
    logger.add(
        sys.stderr,
        level="DEBUG" if settings.DEBUG else "INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # 添加文件日志
    logger.add(
        os.path.join(settings.LOG_DIR, "backend_{time:YYYY-MM-DD}.log"),
        rotation="1 day",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    logger.info(f"启动参数: host={args.host}, port={args.port}, debug={args.debug}")
    
    # 创建应用
    app = create_app()
    
    # 运行服务
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_config=None,  # 禁用 uvicorn 的日志配置，使用 loguru
        access_log=False
    )


if __name__ == "__main__":
    main()