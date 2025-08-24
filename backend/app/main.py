"""
量化回测系统后端服务主入口
基于 FastAPI + DuckDB + Polars 构建
"""

import argparse
import asyncio
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

# 确保项目根目录在 Python 路径中，但避免重复添加
_project_root = str(Path(__file__).parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.core.config import settings
from app.core.database import init_database, get_db_manager
from app.api import health, data, labels, backtest, experiments, websocket, system

# 导入统一端口配置
try:
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from ports_config import get_frontend_port
    FRONTEND_PORT = get_frontend_port()
except ImportError:
    FRONTEND_PORT = 5187  # 默认前端端口


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
        # 不要在lifespan中使用sys.exit()，因为它会导致FastAPI异常
        raise RuntimeError(f"服务启动失败: {e}")  # 抛出RuntimeError让FastAPI处理
    
    yield
    
    # 关闭时清理
    logger.info("正在关闭后端服务...")
    
    # 清理任务管理器
    from app.core.task_manager import cleanup_task_manager
    await cleanup_task_manager()
    
    # 清理数据库连接
    db_manager = await get_db_manager()
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

    # CORS 中间件 - 使用动态端口配置
    frontend_origins = [
        f"http://localhost:{FRONTEND_PORT}",
        f"http://127.0.0.1:{FRONTEND_PORT}",
        "http://localhost:5173",  # Vite默认端口作为备选
        "http://127.0.0.1:5173",
        "http://localhost:5182",  # Electron可能使用的端口
        "http://127.0.0.1:5182"
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=frontend_origins,
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

    # 全局异常处理 - 改进错误信息处理，避免泄露内部细节
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        import traceback
        from fastapi import HTTPException
        
        # 记录详细的错误信息到日志
        logger.error(f"全局异常: {exc}", exc_info=True)
        
        # 对于不同类型的异常返回不同的错误信息
        if isinstance(exc, HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail}
            )
        elif isinstance(exc, ValueError):
            return JSONResponse(
                status_code=400,
                content={"detail": "请求参数错误"}
            )
        elif isinstance(exc, FileNotFoundError):
            return JSONResponse(
                status_code=404,
                content={"detail": "请求的资源不存在"}
            )
        else:
            # 对于其他异常，不暴露内部错误细节
            error_id = f"ERR_{int(time.time() * 1000)}"
            logger.error(f"内部错误 {error_id}: {traceback.format_exc()}")
            
            if settings.DEBUG:
                # 开发模式下返回详细错误
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": f"服务器内部错误: {str(exc)}",
                        "error_id": error_id,
                        "debug_info": traceback.format_exc()
                    }
                )
            else:
                # 生产模式下只返回通用错误信息
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": "服务器内部错误，请稍后重试",
                        "error_id": error_id
                    }
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
        default=settings.PORT, 
        help=f"服务端口 (默认: {settings.PORT})"
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