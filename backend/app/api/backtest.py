"""
回测API路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from app.engine.backtest_engine import BacktestEngine

router = APIRouter()


class BacktestRequest(BaseModel):
    """回测请求"""
    strategy_type: str = Field(..., description="策略类型: 'momentum' 或 'mean_reversion'")
    label_name: str = Field(..., description="标签名称")
    start_date: str = Field(..., description="开始日期 YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD") 
    initial_capital: float = Field(default=1000000.0, description="初始资金")
    rebalance_frequency: str = Field(default="monthly", description="调仓频率: daily/weekly/monthly")
    top_k: int = Field(default=20, description="选择股票数量")
    lookback_period: int = Field(default=20, description="回看期")


class BacktestMetrics(BaseModel):
    """回测指标"""
    total_return: float = 0.0
    annual_return: float = 0.0  
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    total_trades: int = 0
    win_rate: float = 0.0


class BacktestResult(BaseModel):
    """回测结果"""
    result_hash: str
    strategy_type: str
    label_name: str
    start_date: str
    end_date: str
    initial_capital: float
    metrics: BacktestMetrics
    equity_curve: List[Dict[str, Any]] = []
    trades: List[Dict[str, Any]] = []
    created_at: str


@router.post("/run", response_model=BacktestResult, summary="运行回测")
async def run_backtest(request: BacktestRequest):
    """
    执行回测
    
    支持动量和均值回归策略，基于给定的标签选择股票池进行回测
    """
    try:
        engine = BacktestEngine()
        
        result = await engine.run_backtest(
            strategy_type=request.strategy_type,
            label_name=request.label_name,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            rebalance_frequency=request.rebalance_frequency,
            top_k=request.top_k,
            lookback_period=request.lookback_period
        )
        
        # 转换为API响应格式
        return BacktestResult(
            result_hash=result["result_hash"],
            strategy_type=result["strategy_type"],
            label_name=result["label_name"], 
            start_date=result["start_date"],
            end_date=result["end_date"],
            initial_capital=result["initial_capital"],
            metrics=BacktestMetrics(**result["metrics"]),
            equity_curve=result["equity_curve"],
            trades=result["trades"],
            created_at=result["created_at"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回测执行失败: {str(e)}")


@router.get("/strategies", summary="获取可用策略列表") 
async def get_strategies():
    """获取支持的策略类型列表"""
    return {
        "strategies": [
            {
                "type": "momentum",
                "name": "动量策略",
                "description": "基于价格动量选择表现最好的股票"
            },
            {
                "type": "mean_reversion", 
                "name": "均值回归策略",
                "description": "基于均值回归选择被低估的股票"
            }
        ]
    }


@router.get("/labels", summary="获取可用标签列表")
async def get_backtest_labels():
    """获取可用于回测的标签列表"""
    try:
        from app.services.label_calculator import get_label_calculator
        
        calculator = get_label_calculator()
        labels = await calculator.get_labels_list()
        
        # 转换为回测需要的格式
        backtest_labels = []
        for label in labels:
            backtest_labels.append({
                "name": label["name"],
                "rule": label["rule"], 
                "date_range": f"{label['start_date']} ~ {label['end_date']}",
                "stock_count": label["stock_count"],
                "created_at": label["created_at"]
            })
        
        return {"labels": backtest_labels}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取标签列表失败: {str(e)}")