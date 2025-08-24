"""
健康检查API路由
"""

import time
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_database_stats

router = APIRouter()

# 服务启动时间
_start_time = time.time()


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    version: str
    duckdb_path: str
    uptime: float
    status: str = "healthy"
    timestamp: str
    database_stats: dict = {}


@router.get("/healthz", response_model=HealthResponse, summary="健康检查")
async def health_check():
    """
    健康检查接口
    
    返回服务状态、版本信息、运行时间等
    """
    try:
        # 获取数据库统计信息（简单检查）
        db_stats = await get_database_stats()
        
        return HealthResponse(
            version=settings.VERSION,
            duckdb_path=settings.DATABASE_URL,
            uptime=time.time() - _start_time,
            status="healthy",
            timestamp=datetime.now().isoformat(),
            database_stats=db_stats
        )
    except Exception as e:
        return HealthResponse(
            version=settings.VERSION,
            duckdb_path=settings.DATABASE_URL,
            uptime=time.time() - _start_time,
            status=f"unhealthy: {str(e)}",
            timestamp=datetime.now().isoformat()
        )


@router.get("/", summary="根路径")
async def root():
    """根路径重定向到健康检查"""
    return {"message": "量化回测系统后端API", "version": settings.VERSION}


@router.get("/version", summary="版本信息")
async def get_version():
    """获取版本信息"""
    return {
        "version": settings.VERSION,
        "service": "量化回测系统后端",
        "api_docs": "/docs" if settings.DEBUG else None
    }