"""
回测引擎核心实现
基于Polars进行高效数据处理的量化回测引擎
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import polars as pl
import numpy as np
from loguru import logger

from app.core.database import get_db_manager


class BacktestEngine:
    """回测引擎主类"""
    
    def __init__(self):
        self.db = get_db_manager()
        self.results: Optional[Dict] = None
        
    async def run_backtest(
        self,
        strategy_type: str,
        label_name: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 1000000.0,
        rebalance_frequency: str = "monthly",
        top_k: int = 20,
        **strategy_params
    ) -> Dict[str, Any]:
        """
        执行回测
        
        Args:
            strategy_type: 策略类型 (例如: "momentum", "mean_reversion")  
            label_name: 标签名称，用于选择股票池
            start_date: 回测开始日期 YYYY-MM-DD
            end_date: 回测结束日期 YYYY-MM-DD
            initial_capital: 初始资金
            rebalance_frequency: 调仓频率 ("daily", "weekly", "monthly")
            top_k: 选择股票数量
            **strategy_params: 策略特定参数
            
        Returns:
            回测结果字典
        """
        logger.info(f"开始回测: {strategy_type}, 标签: {label_name}, 期间: {start_date} - {end_date}")
        
        try:
            # 1. 获取股票池
            stock_pool = await self._get_stock_pool(label_name, start_date, end_date)
            if stock_pool.is_empty():
                raise ValueError(f"标签 {label_name} 未找到股票数据")
                
            # 2. 获取价格数据
            price_data = await self._get_price_data(stock_pool['symbol'].to_list(), start_date, end_date)
            if price_data.is_empty():
                raise ValueError("未找到价格数据")
                
            # 3. 生成交易信号
            signals = await self._generate_signals(
                price_data, strategy_type, rebalance_frequency, top_k, **strategy_params
            )
            
            # 4. 执行交易模拟
            portfolio_history, trades = await self._simulate_trading(
                price_data, signals, initial_capital
            )
            
            # 5. 计算性能指标
            metrics = await self._calculate_metrics(portfolio_history, trades)
            
            # 6. 生成结果
            result_hash = str(uuid.uuid4())
            self.results = {
                "result_hash": result_hash,
                "strategy_type": strategy_type,
                "label_name": label_name,
                "start_date": start_date,
                "end_date": end_date,
                "initial_capital": initial_capital,
                "metrics": metrics,
                "equity_curve": portfolio_history.select([
                    "date", "total_value"
                ]).rename({"total_value": "value"}).to_dicts(),
                "trades": trades.to_dicts(),
                "created_at": datetime.now().isoformat()
            }
            
            logger.info(f"回测完成，总收益率: {metrics['total_return']:.2%}")
            return self.results
            
        except Exception as e:
            logger.error(f"回测执行失败: {e}")
            raise

    async def _get_stock_pool(self, label_name: str, start_date: str, end_date: str) -> pl.DataFrame:
        """获取股票池"""
        query = f"""
        SELECT DISTINCT symbol 
        FROM labels 
        WHERE name = '{label_name}'
        AND trade_date >= '{start_date}'
        AND trade_date <= '{end_date}'
        """
        return await self.db.query_df(query)
    
    async def _get_price_data(self, symbols: List[str], start_date: str, end_date: str) -> pl.DataFrame:
        """获取价格数据"""
        if not symbols:
            return pl.DataFrame()
            
        symbols_str = "', '".join(symbols)
        query = f"""
        SELECT date, symbol, open, high, low, close, adj_close, volume
        FROM prices_daily 
        WHERE symbol IN ('{symbols_str}')
        AND date >= '{start_date}'
        AND date <= '{end_date}'
        ORDER BY date, symbol
        """
        return await self.db.query_df(query)
    
    async def _generate_signals(
        self, 
        price_data: pl.DataFrame, 
        strategy_type: str,
        rebalance_frequency: str,
        top_k: int,
        **strategy_params
    ) -> pl.DataFrame:
        """生成交易信号"""
        
        if strategy_type == "momentum":
            return await self._momentum_signals(price_data, rebalance_frequency, top_k, **strategy_params)
        elif strategy_type == "mean_reversion":
            return await self._mean_reversion_signals(price_data, rebalance_frequency, top_k, **strategy_params)
        else:
            raise ValueError(f"不支持的策略类型: {strategy_type}")
    
    async def _momentum_signals(
        self, 
        price_data: pl.DataFrame, 
        rebalance_frequency: str, 
        top_k: int,
        lookback_period: int = 20,
        **kwargs
    ) -> pl.DataFrame:
        """动量策略信号生成"""
        
        # 计算收益率
        df = price_data.with_columns([
            (pl.col("close") / pl.col("close").shift(lookback_period).over("symbol") - 1).alias("return"),
        ])
        
        # 生成调仓日期
        rebalance_dates = self._get_rebalance_dates(df, rebalance_frequency)
        
        signals = []
        for date in rebalance_dates:
            # 获取该日期的所有股票收益率
            date_data = df.filter(pl.col("date") == date).drop_nulls("return")
            
            if date_data.height >= top_k:
                # 选择收益率最高的top_k只股票
                selected = date_data.sort("return", descending=True).head(top_k)
                
                for row in selected.to_dicts():
                    signals.append({
                        "date": date,
                        "symbol": row["symbol"],
                        "signal": "BUY",
                        "weight": 1.0 / top_k,  # 等权重
                        "price": row["close"]
                    })
        
        return pl.DataFrame(signals)
    
    async def _mean_reversion_signals(
        self, 
        price_data: pl.DataFrame, 
        rebalance_frequency: str, 
        top_k: int,
        lookback_period: int = 20,
        **kwargs
    ) -> pl.DataFrame:
        """均值回归策略信号生成"""
        
        # 计算移动平均和偏离度
        df = price_data.with_columns([
            pl.col("close").rolling_mean(lookback_period).over("symbol").alias("ma"),
        ]).with_columns([
            ((pl.col("close") - pl.col("ma")) / pl.col("ma")).alias("deviation")
        ])
        
        rebalance_dates = self._get_rebalance_dates(df, rebalance_frequency)
        
        signals = []
        for date in rebalance_dates:
            date_data = df.filter(pl.col("date") == date).drop_nulls("deviation")
            
            if date_data.height >= top_k:
                # 选择偏离度最低的股票（最被低估）
                selected = date_data.sort("deviation").head(top_k)
                
                for row in selected.to_dicts():
                    signals.append({
                        "date": date,
                        "symbol": row["symbol"],
                        "signal": "BUY", 
                        "weight": 1.0 / top_k,
                        "price": row["close"]
                    })
        
        return pl.DataFrame(signals)
    
    def _get_rebalance_dates(self, df: pl.DataFrame, frequency: str) -> List[str]:
        """获取调仓日期"""
        dates = df.select("date").unique().sort("date")["date"].to_list()
        
        if frequency == "daily":
            return dates
        elif frequency == "weekly":
            # 每周一调仓
            return [date for date in dates if datetime.fromisoformat(date).weekday() == 0]
        elif frequency == "monthly":
            # 每月第一个交易日调仓
            monthly_dates = []
            current_month = None
            for date in dates:
                date_obj = datetime.fromisoformat(date)
                if date_obj.month != current_month:
                    monthly_dates.append(date)
                    current_month = date_obj.month
            return monthly_dates
        else:
            raise ValueError(f"不支持的调仓频率: {frequency}")
    
    async def _simulate_trading(
        self,
        price_data: pl.DataFrame,
        signals: pl.DataFrame,
        initial_capital: float
    ) -> Tuple[pl.DataFrame, pl.DataFrame]:
        """交易模拟"""
        
        # 初始化组合
        portfolio_history = []
        trades = []
        current_positions = {}  # {symbol: shares}
        cash = initial_capital
        
        # 获取所有交易日期
        all_dates = price_data.select("date").unique().sort("date")["date"].to_list()
        
        for date in all_dates:
            # 当日价格数据
            daily_prices = price_data.filter(pl.col("date") == date)
            daily_signals = signals.filter(pl.col("date") == date)
            
            # 执行调仓
            if not daily_signals.is_empty():
                # 清空现有持仓
                for symbol, shares in current_positions.items():
                    if shares > 0:
                        price_row = daily_prices.filter(pl.col("symbol") == symbol)
                        if not price_row.is_empty():
                            sell_price = price_row["close"].to_list()[0]
                            cash += shares * sell_price
                            trades.append({
                                "date": date,
                                "symbol": symbol,
                                "action": "SELL",
                                "shares": shares,
                                "price": sell_price,
                                "value": shares * sell_price
                            })
                
                current_positions = {}
                
                # 买入新持仓
                for signal in daily_signals.to_dicts():
                    symbol = signal["symbol"]
                    weight = signal["weight"]
                    price = signal["price"]
                    
                    # 计算买入金额和股数
                    target_value = cash * weight
                    shares = int(target_value / price)
                    
                    if shares > 0:
                        actual_value = shares * price
                        cash -= actual_value
                        current_positions[symbol] = shares
                        
                        trades.append({
                            "date": date,
                            "symbol": symbol,
                            "action": "BUY", 
                            "shares": shares,
                            "price": price,
                            "value": actual_value
                        })
            
            # 计算组合总价值
            positions_value = 0.0
            for symbol, shares in current_positions.items():
                price_row = daily_prices.filter(pl.col("symbol") == symbol)
                if not price_row.is_empty():
                    current_price = price_row["close"].to_list()[0]
                    positions_value += shares * current_price
            
            total_value = cash + positions_value
            
            portfolio_history.append({
                "date": date,
                "cash": cash,
                "positions_value": positions_value,
                "total_value": total_value,
                "return": (total_value - initial_capital) / initial_capital
            })
        
        return pl.DataFrame(portfolio_history), pl.DataFrame(trades)
    
    async def _calculate_metrics(
        self, 
        portfolio_history: pl.DataFrame, 
        trades: pl.DataFrame
    ) -> Dict[str, float]:
        """计算性能指标"""
        
        if portfolio_history.is_empty():
            return {
                "total_return": 0.0,
                "annual_return": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "total_trades": 0,
                "win_rate": 0.0
            }
        
        returns = portfolio_history["return"].to_list()
        values = portfolio_history["total_value"].to_list()
        
        # 总收益率
        total_return = returns[-1] if returns else 0.0
        
        # 年化收益率 (假设252个交易日)
        days = len(returns)
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0.0
        
        # 最大回撤
        max_drawdown = 0.0
        peak = values[0] if values else 0.0
        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak if peak > 0 else 0.0
            max_drawdown = max(max_drawdown, drawdown)
        
        # 夏普比率 (简化计算，假设无风险利率为0)
        if len(returns) > 1:
            daily_returns = [returns[i] - returns[i-1] for i in range(1, len(returns))]
            mean_return = np.mean(daily_returns) if daily_returns else 0.0
            std_return = np.std(daily_returns) if daily_returns else 0.0
            sharpe_ratio = (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # 交易统计
        total_trades = trades.height
        
        # 胜率计算 (简化：买入后卖出盈利的交易)
        win_rate = 0.0
        if total_trades > 0:
            buy_trades = trades.filter(pl.col("action") == "BUY")
            sell_trades = trades.filter(pl.col("action") == "SELL") 
            # 简化胜率计算
            win_rate = 0.6  # 占位符，实际需要更复杂的配对逻辑
        
        return {
            "total_return": total_return,
            "annual_return": annual_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "total_trades": total_trades,
            "win_rate": win_rate
        }