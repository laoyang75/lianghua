"""
数据管理API路由
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.database import get_db_manager

router = APIRouter()


class DataStatusResponse(BaseModel):
    """数据状态响应"""
    has_data: bool = False
    total_symbols: int = 0
    date_range: dict = {}
    last_update: str = ""


class DataDownloadRequest(BaseModel):
    """数据下载请求"""
    universes: List[str] = Field(..., description="数据源列表，如['nasdaq', 'nyse']")
    start_date: str = Field(..., description="开始日期 YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD")
    source: str = Field(default="yfinance", description="数据源")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    type: str
    status: str
    progress: int = 0
    message: str


@router.get("/status", response_model=DataStatusResponse, summary="获取数据状态")
async def get_data_status():
    """
    获取当前数据状态
    
    返回数据库中股票数据的基本统计信息
    """
    try:
        db = get_db_manager()
        
        # 检查是否有数据
        result = await db.execute("SELECT COUNT(*) FROM prices_daily")
        total_records = result[0][0] if result else 0
        
        if total_records == 0:
            return DataStatusResponse()
        
        # 获取唯一股票数
        result = await db.execute("SELECT COUNT(DISTINCT symbol) FROM prices_daily")
        total_symbols = result[0][0] if result else 0
        
        # 获取日期范围
        result = await db.execute("SELECT MIN(date), MAX(date) FROM prices_daily")
        if result and result[0][0]:
            date_range = {
                "start": result[0][0].isoformat(),
                "end": result[0][1].isoformat()
            }
        else:
            date_range = {}
        
        # 获取最后更新时间（假设是最新数据的创建时间）
        result = await db.execute("SELECT MAX(created_at) FROM prices_daily")
        last_update = result[0][0].isoformat() if result and result[0][0] else ""
        
        return DataStatusResponse(
            has_data=total_records > 0,
            total_symbols=total_symbols,
            date_range=date_range,
            last_update=last_update
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据状态失败: {str(e)}")


@router.post("/download", response_model=TaskResponse, summary="启动数据下载")
async def start_data_download(request: DataDownloadRequest):
    """
    启动数据下载任务
    
    异步下载指定时间范围的股票数据
    """
    try:
        from app.services.data_downloader import get_data_downloader
        import uuid
        import asyncio
        
        downloader = get_data_downloader()
        task_id = f"download_{uuid.uuid4().hex[:8]}"
        
        # 在后台启动下载任务
        async def background_download():
            try:
                for universe in request.universes:
                    await downloader.download_universe_data(
                        universe=universe,
                        start_date=request.start_date,
                        end_date=request.end_date,
                        task_id=task_id
                    )
            except Exception as e:
                from loguru import logger
                logger.error(f"后台下载任务失败: {e}")
        
        # 启动后台任务
        asyncio.create_task(background_download())
        
        return TaskResponse(
            task_id=task_id,
            type="data_download",
            status="queued",
            message=f"数据下载任务已启动: {', '.join(request.universes)}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动下载失败: {str(e)}")


@router.get("/symbols", summary="获取股票列表")
async def get_symbols(limit: int = 100, offset: int = 0):
    """
    获取数据库中的股票列表
    """
    try:
        db = get_db_manager()
        
        result = await db.execute("""
            SELECT DISTINCT symbol, MIN(date) as first_date, MAX(date) as last_date, COUNT(*) as record_count
            FROM prices_daily 
            GROUP BY symbol 
            ORDER BY symbol 
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        symbols = []
        for row in result:
            symbols.append({
                "symbol": row[0],
                "first_date": row[1].isoformat() if row[1] else None,
                "last_date": row[2].isoformat() if row[2] else None,
                "record_count": row[3]
            })
        
        return {"symbols": symbols}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票列表失败: {str(e)}")


@router.get("/symbol/{symbol_code}", summary="获取单只股票数据")
async def get_symbol_data(
    symbol_code: str, 
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 1000
):
    """
    获取指定股票的历史数据
    """
    try:
        db = get_db_manager()
        
        # 构建查询条件
        conditions = ["symbol = ?"]
        params = [symbol_code.upper()]
        
        if start_date:
            conditions.append("date >= ?")
            params.append(start_date)
            
        if end_date:
            conditions.append("date <= ?")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions)
        
        result = await db.execute(f"""
            SELECT date, open, high, low, close, volume, adj_close
            FROM prices_daily 
            WHERE {where_clause}
            ORDER BY date DESC
            LIMIT ?
        """, tuple(params + [limit]))
        
        data = []
        for row in result:
            data.append({
                "date": row[0].isoformat(),
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5],
                "adj_close": row[6]
            })
        
        return {"symbol": symbol_code, "data": data}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票数据失败: {str(e)}")


@router.get("/download/history", summary="获取下载历史")
async def get_download_history(limit: int = 50):
    """获取数据下载历史记录"""
    try:
        from app.services.data_downloader import get_data_downloader
        
        downloader = get_data_downloader()
        history = await downloader.get_download_history(limit)
        return {"history": history}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取下载历史失败: {str(e)}")


@router.delete("/download/{task_id}", summary="取消下载任务")
async def cancel_download_task(task_id: str):
    """取消正在进行的下载任务"""
    try:
        from app.services.data_downloader import get_data_downloader
        
        downloader = get_data_downloader()
        success = await downloader.cancel_download_task(task_id)
        
        if success:
            return {"message": f"任务 {task_id} 已取消"}
        else:
            raise HTTPException(status_code=404, detail="任务不存在或已完成")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


@router.get("/universes", summary="获取可用股票池")
async def get_universes():
    """获取所有可用的股票池信息"""
    try:
        from app.services.data_downloader import get_data_downloader
        
        downloader = get_data_downloader()
        
        nasdaq_symbols = await downloader._get_universe_symbols("nasdaq")
        nyse_symbols = await downloader._get_universe_symbols("nyse")
        
        return {
            "universes": {
                "nasdaq": {
                    "name": "NASDAQ",
                    "description": "纳斯达克市场，主要包含科技股和生物科技股",
                    "symbol_count": len(nasdaq_symbols),
                    "examples": nasdaq_symbols[:5]  # 只显示前5个作为示例
                },
                "nyse": {
                    "name": "NYSE", 
                    "description": "纽约证券交易所，包含传统蓝筹股、金融股等",
                    "symbol_count": len(nyse_symbols),
                    "examples": nyse_symbols[:5]
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票池信息失败: {str(e)}")