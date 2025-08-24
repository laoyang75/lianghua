"""
数据下载服务模块
使用yfinance下载股票数据并存储到DuckDB
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import yfinance as yf
import polars as pl
import pandas as pd
from loguru import logger

from app.core.database import get_db_manager
from app.api.websocket import send_task_update, send_task_completed, send_task_failed
from app.models.data import Task


class DataDownloader:
    """数据下载器"""
    
    def __init__(self):
        self.db = get_db_manager()
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
    
    async def download_universe_data(
        self,
        universe: str,
        start_date: str,
        end_date: str,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """下载指定股票池的数据"""
        
        if not task_id:
            task_id = f"download_{uuid.uuid4().hex[:8]}"
        
        try:
            # 创建任务记录
            await self._create_task_record(task_id, universe, start_date, end_date)
            
            # 获取股票池符号列表
            symbols = await self._get_universe_symbols(universe)
            if not symbols:
                raise ValueError(f"股票池 {universe} 没有有效的股票符号")
            
            logger.info(f"开始下载 {universe} 股票池数据，共 {len(symbols)} 只股票")
            await send_task_update(task_id, "running", 0, f"准备下载 {len(symbols)} 只股票数据")
            
            # 批量下载数据
            download_results = await self._download_batch_data(
                symbols, start_date, end_date, task_id
            )
            
            # 处理下载结果
            success_count = len([r for r in download_results if r['success']])
            failed_count = len(download_results) - success_count
            
            # 更新任务状态
            await self._update_task_status(task_id, "completed", 100, 
                                         f"下载完成：{success_count} 成功，{failed_count} 失败")
            
            await send_task_completed(task_id, 
                                    f"数据下载完成：{success_count} 成功，{failed_count} 失败")
            
            return {
                "task_id": task_id,
                "universe": universe,
                "total_symbols": len(symbols),
                "success_count": success_count,
                "failed_count": failed_count,
                "download_results": download_results
            }
            
        except Exception as e:
            logger.error(f"下载数据失败 [任务ID: {task_id}]: {e}")
            await self._update_task_status(task_id, "failed", 0, str(e))
            await send_task_failed(task_id, str(e))
            raise
    
    async def _get_universe_symbols(self, universe: str) -> List[str]:
        """获取股票池的符号列表"""
        
        # 预定义的股票池
        universes = {
            "nasdaq": [
                # 科技股
                "AAPL", "GOOGL", "MSFT", "AMZN", "NVDA", "META", "TSLA", "NFLX",
                "AMD", "INTC", "CRM", "ORCL", "ADBE", "NOW", "INTU", "QCOM",
                "AVGO", "TXN", "LRCX", "ADI", "KLAC", "MRVL", "FTNT", "PANW",
                "CRWD", "ZS", "OKTA", "SNOW", "NET", "DDOG", "MDB", "PLTR",
                # 生物科技
                "MRNA", "BNTX", "REGN", "GILD", "VRTX", "BIIB", "AMGN", "CELG"
            ],
            "nyse": [
                # 传统蓝筹股
                "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "AXP",
                "JNJ", "PFE", "MRK", "UNH", "CVS", "ABBV", "TMO", "DHR",
                "V", "MA", "PYPL", "SQ", "WMT", "HD", "NKE", "SBUX",
                "DIS", "CMCSA", "VZ", "T", "KO", "PEP", "MCD", "BA",
                # 能源和工业
                "XOM", "CVX", "COP", "SLB", "GE", "CAT", "DE", "MMM"
            ]
        }
        
        return universes.get(universe.lower(), [])
    
    async def _download_batch_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        task_id: str
    ) -> List[Dict[str, Any]]:
        """批量下载股票数据"""
        
        results = []
        total_symbols = len(symbols)
        batch_size = 5  # 每批处理5只股票
        
        for i in range(0, total_symbols, batch_size):
            batch_symbols = symbols[i:i + batch_size]
            batch_results = await self._download_symbols_batch(
                batch_symbols, start_date, end_date, task_id
            )
            results.extend(batch_results)
            
            # 更新进度
            progress = min(100, int((i + batch_size) / total_symbols * 100))
            await send_task_update(
                task_id, "running", progress,
                f"已下载 {min(i + batch_size, total_symbols)}/{total_symbols} 只股票数据"
            )
            
            # 避免请求频率过高
            await asyncio.sleep(0.1)
        
        return results
    
    async def _download_symbols_batch(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        task_id: str
    ) -> List[Dict[str, Any]]:
        """下载一批股票数据"""
        
        results = []
        
        for symbol in symbols:
            try:
                result = await self._download_single_symbol(symbol, start_date, end_date)
                results.append({
                    "symbol": symbol,
                    "success": True,
                    "records_count": result["records_count"],
                    "message": "下载成功"
                })
                logger.debug(f"股票 {symbol} 下载成功，{result['records_count']} 条记录")
                
            except Exception as e:
                results.append({
                    "symbol": symbol,
                    "success": False,
                    "records_count": 0,
                    "message": str(e)
                })
                logger.warning(f"股票 {symbol} 下载失败: {e}")
        
        return results
    
    async def _download_single_symbol(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """下载单只股票数据"""
        
        # 在线程池中执行同步的yfinance操作
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, self._fetch_yahoo_data, symbol, start_date, end_date
        )
        
        if data is None or data.empty:
            raise ValueError(f"股票 {symbol} 没有可用数据")
        
        # 转换为Polars DataFrame并重新索引
        pandas_df = data.reset_index()
        logger.debug(f"Pandas列名: {list(pandas_df.columns)}")
        logger.debug(f"前几行数据: {pandas_df.head()}")
        
        # 转换为Polars
        df = pl.from_pandas(pandas_df)
        
        # 重命名列以匹配数据库结构
        column_mapping = {}
        for col in df.columns:
            if col == "Date":
                column_mapping[col] = "date"
            elif col == "Open":
                column_mapping[col] = "open"
            elif col == "High":
                column_mapping[col] = "high"
            elif col == "Low":
                column_mapping[col] = "low"
            elif col == "Close":
                column_mapping[col] = "close"
            elif col == "Volume":
                column_mapping[col] = "volume"
            elif col == "Adj Close":
                column_mapping[col] = "adj_close"
        
        logger.debug(f"列映射: {column_mapping}")
        df = df.rename(column_mapping)
        
        # 选择需要的列并添加股票符号，如果没有adj_close，用close代替
        required_columns = ["date", "open", "high", "low", "close", "volume"]
        existing_columns = [col for col in required_columns if col in df.columns]
        
        df = df.select(existing_columns)
        
        # 添加adj_close列（如果不存在，则用close列的值）
        if "adj_close" not in df.columns:
            df = df.with_columns([
                pl.col("close").alias("adj_close")
            ])
        
        df = df.with_columns([
            pl.lit(symbol).alias("symbol"),
            pl.lit(None, dtype=pl.Utf8).alias("calendar_id"),
            pl.lit(datetime.now()).alias("created_at")
        ])
        
        # 重新排列列顺序以匹配数据库表结构
        column_order = ["date", "symbol", "open", "high", "low", "close", "volume", "adj_close", "calendar_id", "created_at"]
        available_columns = [col for col in column_order if col in df.columns]
        df = df.select(available_columns)
        
        # 确保数据类型正确
        if "date" in df.columns:
            df = df.with_columns([
                pl.col("date").cast(pl.Date)
            ])
        
        logger.debug(f"最终DataFrame结构: {df.schema}")
        logger.debug(f"最终数据预览: {df.head()}")
        logger.debug(f"DataFrame列数: {len(df.columns)}")
        logger.debug(f"DataFrame列名: {df.columns}")
        
        # 确保DataFrame有正确的列数 (10列)
        if len(df.columns) != 10:
            logger.error(f"DataFrame列数不匹配: 期望10列，实际{len(df.columns)}列")
            logger.error(f"现有列: {df.columns}")
            raise ValueError(f"DataFrame列数不匹配: 期望10列，实际{len(df.columns)}列")
        
        # 存储到数据库
        await self.db.insert_df("prices_daily", df, if_exists="append")
        
        # 获取日期范围信息
        date_min = df["date"].min()
        date_max = df["date"].max()
        
        return {
            "records_count": len(df),
            "date_range": {
                "start": str(date_min) if date_min else None,
                "end": str(date_max) if date_max else None
            }
        }
    
    def _fetch_yahoo_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """同步获取Yahoo Finance数据"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            return data
        except Exception as e:
            logger.error(f"获取 {symbol} 数据失败: {e}")
            raise
    
    async def _create_task_record(
        self, 
        task_id: str, 
        universe: str, 
        start_date: str, 
        end_date: str
    ):
        """创建任务记录"""
        await self.db.execute("""
            INSERT INTO tasks (task_id, type, status, progress, message, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            "data_download",
            "queued",
            0,
            f"准备下载 {universe} 股票池数据",
            f'{{"universe": "{universe}", "start_date": "{start_date}", "end_date": "{end_date}"}}'
        ))
        
        self.active_tasks[task_id] = {
            "type": "data_download",
            "universe": universe,
            "start_date": start_date,
            "end_date": end_date,
            "created_at": datetime.now().isoformat()
        }
    
    async def _update_task_status(
        self,
        task_id: str,
        status: str,
        progress: int,
        message: str
    ):
        """更新任务状态"""
        now = datetime.now()
        
        if status == "completed":
            await self.db.execute("""
                UPDATE tasks 
                SET status = ?, progress = ?, message = ?, finished_at = ?
                WHERE task_id = ?
            """, (status, progress, message, now, task_id))
        elif status == "failed":
            await self.db.execute("""
                UPDATE tasks 
                SET status = ?, progress = ?, error_message = ?, finished_at = ?
                WHERE task_id = ?
            """, (status, progress, message, now, task_id))
        else:
            await self.db.execute("""
                UPDATE tasks 
                SET status = ?, progress = ?, message = ?, started_at = ?
                WHERE task_id = ?
            """, (status, progress, message, now, task_id))
    
    async def get_download_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取下载历史记录"""
        result = await self.db.execute("""
            SELECT task_id, status, progress, message, payload_json, 
                   created_at, started_at, finished_at, error_message
            FROM tasks 
            WHERE type = 'data_download'
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        history = []
        for row in result:
            history.append({
                "task_id": row[0],
                "status": row[1],
                "progress": row[2],
                "message": row[3],
                "payload": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "started_at": row[6].isoformat() if row[6] else None,
                "finished_at": row[7].isoformat() if row[7] else None,
                "error_message": row[8]
            })
        
        return history
    
    async def cancel_download_task(self, task_id: str) -> bool:
        """取消下载任务"""
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
            
            await self.db.execute("""
                UPDATE tasks 
                SET status = 'cancelled', finished_at = ?
                WHERE task_id = ?
            """, (datetime.now(), task_id))
            
            return True
        
        return False


# 全局数据下载器实例
_downloader: Optional[DataDownloader] = None


def get_data_downloader() -> DataDownloader:
    """获取数据下载器实例"""
    global _downloader
    if _downloader is None:
        _downloader = DataDownloader()
    return _downloader