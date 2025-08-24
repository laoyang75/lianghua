"""
数据相关的Pydantic模型
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PriceData(BaseModel):
    """价格数据模型"""
    date: date
    symbol: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    adj_close: Optional[float] = None
    calendar_id: Optional[str] = None
    

class LabelData(BaseModel):
    """标签数据模型"""
    trade_date: date
    label_name: str
    symbol: str
    score: Optional[float] = None
    rank: int
    meta_json: Optional[Dict[str, Any]] = None


class StrategyCfg(BaseModel):
    """策略配置模型"""
    name: str = Field(..., description="策略名称")
    buy_timing: str = Field(..., description="买入时机")
    sell_timing: str = Field(..., description="卖出时机")
    hold_days: int = Field(..., ge=1, le=30, description="持仓天数")
    execution_frequency: int = Field(..., ge=1, description="执行频率（天）")
    execution_count: int = Field(..., ge=1, description="执行次数")
    positioning: str = Field(..., description="仓位管理方式")
    initial_capital: float = Field(..., gt=0, description="初始资金")
    filter_rules: Dict[str, Any] = Field(default_factory=dict, description="筛选规则")


class BacktestMetrics(BaseModel):
    """回测指标模型"""
    total_return: float = Field(..., description="总收益率")
    ann_return: float = Field(..., description="年化收益率")
    max_drawdown: float = Field(..., description="最大回撤")
    sharpe_ratio: float = Field(..., description="夏普比率")
    calmar_ratio: Optional[float] = Field(None, description="卡尔玛比率")
    win_rate: Optional[float] = Field(None, description="胜率")
    avg_trade_return: Optional[float] = Field(None, description="平均交易收益")


class TradeRecord(BaseModel):
    """交易记录模型"""
    batch: int = Field(..., description="批次号")
    symbol: str = Field(..., description="股票代码")
    buy_date: date = Field(..., description="买入日期")
    sell_date: date = Field(..., description="卖出日期")
    buy_price: float = Field(..., description="买入价格")
    sell_price: float = Field(..., description="卖出价格")
    shares: int = Field(..., description="股数")
    return_value: float = Field(..., description="收益金额")
    return_pct: float = Field(..., description="收益率")


class BacktestResult(BaseModel):
    """回测结果模型"""
    metrics: BacktestMetrics
    equity_curve: List[Dict[str, Any]] = Field(default_factory=list, description="净值曲线")
    trades: List[TradeRecord] = Field(default_factory=list, description="交易记录")
    result_hash: str = Field(..., description="结果哈希值")


class Experiment(BaseModel):
    """实验模型"""
    id: str = Field(..., description="实验ID")
    created_at: datetime = Field(..., description="创建时间")
    strategy_name: str = Field(..., description="策略名称")
    label_name: str = Field(..., description="标签名称")
    cfg_json: StrategyCfg = Field(..., description="策略配置")
    metrics_json: BacktestMetrics = Field(..., description="回测指标")
    result_hash: str = Field(..., description="结果哈希值")
    deleted_at: Optional[datetime] = Field(None, description="删除时间")


class Task(BaseModel):
    """任务模型"""
    task_id: str = Field(..., description="任务ID")
    type: str = Field(..., description="任务类型")
    status: str = Field(default="queued", description="任务状态")
    progress: int = Field(default=0, ge=0, le=100, description="进度百分比")
    message: Optional[str] = Field(None, description="状态消息")
    payload_json: Optional[Dict[str, Any]] = Field(None, description="任务载荷")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    finished_at: Optional[datetime] = Field(None, description="完成时间")
    error_message: Optional[str] = Field(None, description="错误信息")