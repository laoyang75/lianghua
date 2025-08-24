"""
标签计算引擎模块
实现6种股票筛选规则，计算TOP20股票并生成标签
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import polars as pl
from loguru import logger

from app.core.database import get_db_manager
from app.api.websocket import send_task_update, send_task_completed, send_task_failed
from app.models.data import Task


class LabelCalculator:
    """标签计算引擎"""
    
    def __init__(self):
        self.db = None
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
    
    async def _ensure_db(self):
        """确保数据库连接"""
        if self.db is None:
            self.db = await get_db_manager()
    
    async def calculate_label(
        self,
        rule: str,
        start_date: str,
        end_date: str,
        params: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """计算指定规则的标签"""
        
        if not task_id:
            task_id = f"label_{uuid.uuid4().hex[:8]}"
        
        try:
            # 创建任务记录
            await self._create_task_record(task_id, rule, start_date, end_date, params)
            
            logger.info(f"开始计算标签 {rule}，任务ID: {task_id}")
            await send_task_update(task_id, "running", 10, f"准备计算标签: {rule}")
            
            # 根据规则类型执行相应的计算
            label_data = await self._execute_rule_calculation(
                rule, start_date, end_date, params, task_id
            )
            
            # 保存标签数据到数据库
            label_name = f"{rule}_{start_date}_{end_date}"
            await self._save_label_data(label_name, rule, label_data, start_date, end_date, task_id)
            
            await send_task_completed(task_id, f"标签计算完成: {len(label_data)} 只股票")
            
            return {
                "task_id": task_id,
                "label_name": label_name,
                "rule": rule,
                "stock_count": len(label_data),
                "date_range": {"start": start_date, "end": end_date},
                "stocks": label_data[:20]  # 返回前20只股票
            }
            
        except Exception as e:
            logger.error(f"标签计算失败 [任务ID: {task_id}]: {e}")
            await self._update_task_status(task_id, "failed", 0, str(e))
            await send_task_failed(task_id, str(e))
            raise
    
    async def _execute_rule_calculation(
        self,
        rule: str,
        start_date: str,
        end_date: str,
        params: Dict[str, Any],
        task_id: str
    ) -> List[Dict[str, Any]]:
        """执行具体的规则计算"""
        
        await send_task_update(task_id, "running", 30, "获取股票列表...")
        
        # 获取所有可用的股票符号列表
        symbols = await self._get_available_symbols()
        
        if not symbols:
            raise ValueError("没有可用的股票数据")
        
        await send_task_update(task_id, "running", 40, f"找到 {len(symbols)} 只股票，开始计算...")
        
        # 根据规则类型执行计算（使用逐只股票处理）
        if rule == "涨幅最大TOP20":
            return await self._calculate_price_change_top_optimized(symbols, start_date, end_date, True, params, task_id)
        elif rule == "跌幅最大TOP20":
            return await self._calculate_price_change_top_optimized(symbols, start_date, end_date, False, params, task_id)
        elif rule == "市值涨幅最大TOP20":
            # 暂时使用旧方法，后续可以优化
            await send_task_update(task_id, "running", 50, "加载股票数据...")
            price_data = await self._load_price_data(start_date, end_date)
            return await self._calculate_market_cap_change_top(price_data, True, params, task_id)
        elif rule == "市值跌幅最大TOP20":
            await send_task_update(task_id, "running", 50, "加载股票数据...")
            price_data = await self._load_price_data(start_date, end_date)
            return await self._calculate_market_cap_change_top(price_data, False, params, task_id)
        elif rule == "成交量最大TOP20":
            await send_task_update(task_id, "running", 50, "加载股票数据...")
            price_data = await self._load_price_data(start_date, end_date)
            return await self._calculate_volume_top(price_data, params, task_id)
        elif rule == "换手率最高TOP20":
            await send_task_update(task_id, "running", 50, "加载股票数据...")
            price_data = await self._load_price_data(start_date, end_date)
            return await self._calculate_turnover_rate_top(price_data, params, task_id)
        else:
            raise ValueError(f"未知的规则类型: {rule}")
    
    async def _load_price_data(self, start_date: str, end_date: str) -> pl.DataFrame:
        """加载指定时间范围的股票价格数据"""
        
        query = """
        SELECT symbol, date, open, high, low, close, volume, adj_close
        FROM prices_daily
        WHERE date >= ? AND date <= ?
        ORDER BY symbol, date
        """
        
        result = await self.db.execute(query, (start_date, end_date))
        
        if not result:
            return pl.DataFrame()
        
        # 转换为Polars DataFrame
        df = pl.DataFrame({
            "symbol": [row[0] for row in result],
            "date": [row[1] for row in result],
            "open": [float(row[2]) for row in result],
            "high": [float(row[3]) for row in result],
            "low": [float(row[4]) for row in result],
            "close": [float(row[5]) for row in result],
            "volume": [int(row[6]) for row in result],
            "adj_close": [float(row[7]) for row in result]
        })
        
        return df
    
    async def _load_price_data_for_symbol(self, symbol: str, start_date: str, end_date: str) -> pl.DataFrame:
        """加载单只股票的价格数据"""
        await self._ensure_db()
        
        query = """
        SELECT symbol, date, open, high, low, close, volume, adj_close
        FROM prices_daily
        WHERE symbol = ? AND date >= ? AND date <= ?
        ORDER BY date
        """
        
        try:
            result = await self.db.execute(query, (symbol, start_date, end_date))
            
            if not result:
                return pl.DataFrame()
            
            # 转换为Polars DataFrame
            df = pl.DataFrame({
                "symbol": [row[0] for row in result],
                "date": [row[1] for row in result],
                "open": [float(row[2]) for row in result],
                "high": [float(row[3]) for row in result],
                "low": [float(row[4]) for row in result],
                "close": [float(row[5]) for row in result],
                "volume": [int(row[6]) for row in result],
                "adj_close": [float(row[7]) for row in result]
            })
            
            return df
            
        except Exception as e:
            logger.error(f"加载股票 {symbol} 数据失败: {e}")
            return pl.DataFrame()
    
    async def _get_available_symbols(self) -> List[str]:
        """获取所有可用的股票符号列表"""
        await self._ensure_db()
        
        query = "SELECT DISTINCT symbol FROM prices_daily ORDER BY symbol"
        
        try:
            result = await self.db.execute(query)
            symbols = [row[0] for row in result] if result else []
            return symbols
        except Exception as e:
            logger.error(f"获取股票符号列表失败: {e}")
            return []
    
    async def _calculate_price_change_top_optimized(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        ascending: bool,  # True for 涨幅最大, False for 跌幅最大
        params: Dict[str, Any],
        task_id: str
    ) -> List[Dict[str, Any]]:
        """优化的涨跌幅TOP20计算 - 逐只股票处理避免内存问题"""
        
        stock_changes = []
        total_symbols = len(symbols)
        processed_symbols = 0
        
        logger.info(f"开始逐只计算 {total_symbols} 只股票的涨跌幅")
        
        for symbol in symbols:
            try:
                # 加载单只股票数据
                symbol_data = await self._load_price_data_for_symbol(symbol, start_date, end_date)
                
                if symbol_data.is_empty() or len(symbol_data) < 2:
                    logger.debug(f"股票 {symbol} 数据不足，跳过")
                    processed_symbols += 1
                    continue
                
                # 计算周期涨跌幅
                first_price = symbol_data['close'].first()
                last_price = symbol_data['close'].last()
                
                if first_price and last_price and first_price > 0:
                    change_pct = (last_price - first_price) / first_price * 100
                    
                    # 应用市值过滤（如果有的话）
                    min_market_cap = params.get('min_market_cap', 0)
                    if min_market_cap > 0:
                        # 简化的市值计算：收盘价 * 平均成交量
                        estimated_market_cap = last_price * symbol_data['volume'].mean()
                        if estimated_market_cap < min_market_cap:
                            processed_symbols += 1
                            continue
                    
                    stock_changes.append({
                        'symbol': symbol,
                        'change_pct': change_pct,
                        'start_price': float(first_price),
                        'end_price': float(last_price),
                        'avg_volume': float(symbol_data['volume'].mean())
                    })
                
                processed_symbols += 1
                
                # 更新进度 (40% + 50% * 处理进度)
                progress = 40 + int((processed_symbols / total_symbols) * 50)
                await send_task_update(task_id, "running", progress, 
                                     f"已处理 {processed_symbols}/{total_symbols} 只股票")
                
                # 每处理10只股票暂停一下，避免过度占用资源
                if processed_symbols % 10 == 0:
                    await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"处理股票 {symbol} 时出错: {e}")
                processed_symbols += 1
                continue
        
        # 排序并取TOP20
        stock_changes.sort(key=lambda x: x['change_pct'], reverse=not ascending)
        top_stocks = stock_changes[:20]
        
        logger.info(f"计算完成，从 {total_symbols} 只股票中筛选出 {len(top_stocks)} 只")
        
        return top_stocks
    
    async def _calculate_price_change_top(
        self,
        data: pl.DataFrame,
        ascending: bool,
        params: Dict[str, Any],
        task_id: str
    ) -> List[Dict[str, Any]]:
        """计算涨跌幅TOP20"""
        
        # 计算每只股票的涨跌幅
        stock_changes = []
        
        symbols = data['symbol'].unique().to_list()
        total_symbols = len(symbols)
        
        for i, symbol in enumerate(symbols):
            symbol_data = data.filter(pl.col('symbol') == symbol).sort('date')
            
            if len(symbol_data) < 2:
                continue
            
            first_price = symbol_data['close'].first()
            last_price = symbol_data['close'].last()
            
            if first_price and last_price and first_price > 0:
                change_pct = (last_price - first_price) / first_price * 100
                
                # 应用市值过滤（如果有的话）
                min_market_cap = params.get('min_market_cap', 0)
                if min_market_cap > 0:
                    # 简化的市值计算：收盘价 * 成交量
                    estimated_market_cap = last_price * symbol_data['volume'].mean()
                    if estimated_market_cap < min_market_cap:
                        continue
                
                stock_changes.append({
                    'symbol': symbol,
                    'change_pct': change_pct,
                    'start_price': float(first_price),
                    'end_price': float(last_price),
                    'avg_volume': float(symbol_data['volume'].mean())
                })
            
            # 更新进度
            progress = 50 + int((i + 1) / total_symbols * 40)
            await send_task_update(task_id, "running", progress, 
                                 f"计算进度: {i + 1}/{total_symbols} 只股票")
        
        # 排序并取TOP20
        stock_changes.sort(key=lambda x: x['change_pct'], reverse=not ascending)
        top_k = params.get('top_k', 20)
        
        return stock_changes[:top_k]
    
    async def _calculate_market_cap_change_top(
        self,
        data: pl.DataFrame,
        ascending: bool,
        params: Dict[str, Any],
        task_id: str
    ) -> List[Dict[str, Any]]:
        """计算市值涨跌幅TOP20"""
        
        # 简化实现：使用价格变化作为市值变化的代理指标
        return await self._calculate_price_change_top(data, ascending, params, task_id)
    
    async def _calculate_volume_top(
        self,
        data: pl.DataFrame,
        params: Dict[str, Any],
        task_id: str
    ) -> List[Dict[str, Any]]:
        """计算成交量最大TOP20"""
        
        stock_volumes = []
        symbols = data['symbol'].unique().to_list()
        total_symbols = len(symbols)
        
        for i, symbol in enumerate(symbols):
            symbol_data = data.filter(pl.col('symbol') == symbol)
            
            avg_volume = symbol_data['volume'].mean()
            total_volume = symbol_data['volume'].sum()
            last_price = symbol_data['close'].last()
            
            if avg_volume and total_volume and last_price:
                # 应用市值过滤
                min_market_cap = params.get('min_market_cap', 0)
                if min_market_cap > 0:
                    estimated_market_cap = float(last_price) * float(avg_volume)
                    if estimated_market_cap < min_market_cap:
                        continue
                
                stock_volumes.append({
                    'symbol': symbol,
                    'avg_volume': float(avg_volume),
                    'total_volume': float(total_volume),
                    'last_price': float(last_price)
                })
            
            # 更新进度
            progress = 50 + int((i + 1) / total_symbols * 40)
            await send_task_update(task_id, "running", progress, 
                                 f"计算进度: {i + 1}/{total_symbols} 只股票")
        
        # 按平均成交量排序
        stock_volumes.sort(key=lambda x: x['avg_volume'], reverse=True)
        top_k = params.get('top_k', 20)
        
        return stock_volumes[:top_k]
    
    async def _calculate_turnover_rate_top(
        self,
        data: pl.DataFrame,
        params: Dict[str, Any],
        task_id: str
    ) -> List[Dict[str, Any]]:
        """计算换手率最高TOP20"""
        
        # 简化实现：使用成交量/股价作为换手率的代理指标
        stock_turnover = []
        symbols = data['symbol'].unique().to_list()
        total_symbols = len(symbols)
        
        for i, symbol in enumerate(symbols):
            symbol_data = data.filter(pl.col('symbol') == symbol)
            
            avg_volume = symbol_data['volume'].mean()
            avg_price = symbol_data['close'].mean()
            
            if avg_volume and avg_price and avg_price > 0:
                # 简化的换手率计算
                turnover_rate = float(avg_volume) / float(avg_price)
                
                stock_turnover.append({
                    'symbol': symbol,
                    'turnover_rate': turnover_rate,
                    'avg_volume': float(avg_volume),
                    'avg_price': float(avg_price)
                })
            
            # 更新进度
            progress = 50 + int((i + 1) / total_symbols * 40)
            await send_task_update(task_id, "running", progress, 
                                 f"计算进度: {i + 1}/{total_symbols} 只股票")
        
        # 按换手率排序
        stock_turnover.sort(key=lambda x: x['turnover_rate'], reverse=True)
        top_k = params.get('top_k', 20)
        
        return stock_turnover[:top_k]
    
    async def _save_label_data(
        self,
        label_name: str,
        rule: str,
        label_data: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
        task_id: str
    ):
        """保存标签数据到数据库"""
        
        await send_task_update(task_id, "running", 90, "保存标签数据...")
        
        # 删除同名的旧标签
        await self.db.execute("DELETE FROM labels WHERE name = ?", (label_name,))
        
        # 插入新标签记录
        await self.db.execute("""
            INSERT INTO labels (name, rule, start_date, end_date, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (label_name, rule, start_date, end_date, datetime.now()))
        
        # 插入标签股票数据
        for i, stock in enumerate(label_data):
            await self.db.execute("""
                INSERT INTO label_stocks (label_name, symbol, rank, score, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                label_name,
                stock['symbol'],
                i + 1,
                stock.get('change_pct', stock.get('avg_volume', stock.get('turnover_rate', 0))),
                json.dumps(stock, ensure_ascii=False),
                datetime.now()
            ))
    
    async def _create_task_record(
        self, 
        task_id: str, 
        rule: str, 
        start_date: str, 
        end_date: str, 
        params: Dict[str, Any]
    ):
        """创建任务记录"""
        await self.db.execute("""
            INSERT INTO tasks (task_id, type, status, progress, message, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            "label_calculation",
            "queued",
            0,
            f"准备计算标签: {rule}",
            json.dumps({"rule": rule, "start_date": start_date, "end_date": end_date, "params": params}, ensure_ascii=False)
        ))
        
        self.active_tasks[task_id] = {
            "type": "label_calculation",
            "rule": rule,
            "start_date": start_date,
            "end_date": end_date,
            "params": params,
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
    
    async def get_labels_list(self) -> List[Dict[str, Any]]:
        """获取标签列表"""
        await self._ensure_db()
        result = await self.db.execute("""
            SELECT l.name, l.rule, l.start_date, l.end_date, l.created_at,
                   COUNT(ls.symbol) as stock_count
            FROM labels l
            LEFT JOIN label_stocks ls ON l.name = ls.label_name
            GROUP BY l.name, l.rule, l.start_date, l.end_date, l.created_at
            ORDER BY l.created_at DESC
        """)
        
        labels = []
        for row in result:
            labels.append({
                "name": row[0],
                "rule": row[1],
                "start_date": row[2],
                "end_date": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "stock_count": row[5] or 0
            })
        
        return labels
    
    async def get_label_stocks(self, label_name: str) -> List[Dict[str, Any]]:
        """获取标签的股票列表"""
        await self._ensure_db()
        result = await self.db.execute("""
            SELECT symbol, rank, score, metadata_json
            FROM label_stocks
            WHERE label_name = ?
            ORDER BY rank
        """, (label_name,))
        
        stocks = []
        for row in result:
            try:
                metadata = eval(row[3]) if row[3] else {}
            except:
                metadata = {}
            
            stocks.append({
                "symbol": row[0],
                "rank": row[1],
                "score": row[2],
                **metadata
            })
        
        return stocks
    
    async def delete_label(self, label_name: str) -> bool:
        """删除标签"""
        try:
            await self._ensure_db()
            # 删除标签股票数据
            await self.db.execute("DELETE FROM label_stocks WHERE label_name = ?", (label_name,))
            # 删除标签记录
            await self.db.execute("DELETE FROM labels WHERE name = ?", (label_name,))
            return True
        except Exception as e:
            logger.error(f"删除标签失败: {e}")
            return False


# 全局标签计算器实例
_calculator: Optional[LabelCalculator] = None


def get_label_calculator() -> LabelCalculator:
    """获取标签计算器实例"""
    global _calculator
    if _calculator is None:
        _calculator = LabelCalculator()
    return _calculator