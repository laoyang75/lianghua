// API 响应类型定义

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  code?: number
}

// 健康检查响应
export interface HealthResponse {
  version: string
  duckdb_path: string
  uptime: number
}

// 数据状态响应
export interface DataStatusResponse {
  has_data: boolean
  total_symbols: number
  date_range: {
    start: string
    end: string
  }
  last_update: string
}

// 任务相关类型
export interface Task {
  task_id: string
  type: 'data_download' | 'label_calculation' | 'backtest'
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'canceled'
  progress: number
  message: string
  started_at?: string
  finished_at?: string
}

// 数据下载请求
export interface DataDownloadRequest {
  universes: string[]
  start_date: string
  end_date: string
  source: 'yfinance'
}

// 标签请求
export interface LabelRequest {
  rule: string
  start_date: string
  end_date: string
  params: {
    top_k: number
    min_market_cap?: number
    max_drop_pct?: number
  }
}

// 标签响应
export interface Label {
  name: string
  status: 'pending' | 'computing' | 'done' | 'error'
  date_range: string
  record_count: number
  rule: string
}

// 策略配置
export interface StrategyCfg {
  name: string
  buy_timing: 'T+1开盘' | 'T+1收盘' | 'T+2开盘'
  sell_timing: '开盘' | '收盘'
  hold_days: number
  execution_frequency: number
  execution_count: number
  positioning: 'equal_weight' | 'market_cap_weight'
  initial_capital: number
  filter_rules: {
    min_market_cap?: number
    max_market_cap?: number
    min_change_pct?: number
    max_change_pct?: number
    max_drop_pct?: number
    top_k?: number
  }
}

// 回测请求
export interface BacktestRequest {
  strategy_cfg: StrategyCfg
  label_name: string
  date_range: {
    start: string
    end: string
  }
}

// 回测指标
export interface BacktestMetrics {
  total_return: number
  ann_return: number
  max_drawdown: number
  sharpe_ratio: number
  calmar_ratio: number
  win_rate: number
  avg_trade_return: number
}

// 交易记录
export interface TradeRecord {
  batch: number
  symbol: string
  buy_date: string
  sell_date: string
  buy_price: number
  sell_price: number
  shares: number
  return: number
  return_pct: number
}

// 回测结果
export interface BacktestResult {
  metrics: BacktestMetrics
  equity_curve: Array<{
    date: string
    value: number
  }>
  trades: TradeRecord[]
  result_hash: string
}

// 实验类型
export interface Experiment {
  id: string
  created_at: string
  strategy_name: string
  label_name: string
  cfg_json: StrategyCfg
  metrics_json: BacktestMetrics
  result_hash: string
  deleted_at?: string
}

// WebSocket 事件类型
export interface WebSocketEvent {
  type: 'task_progress' | 'task_completed' | 'task_failed' | 'task_cancelled'
  task_id: string
  progress?: number
  message?: string
  data?: any
  timestamp: string
}

// 策略模板
export interface StrategyTemplate {
  name: string
  type: 'reversal' | 'momentum'
  description: string
  parameters: {
    buy_timing: string
    sell_timing: string
    hold_days: number
    execution_frequency: number
    execution_count: number
    positioning: string
    initial_capital: number
    filter_rules: Record<string, any>
  }
}

// 筛选规则
export interface FilterRule {
  field: string
  operator: 'gt' | 'lt' | 'gte' | 'lte' | 'eq' | 'ne'
  value: number | string
  label: string
}

// 错误响应
export interface ErrorResponse {
  detail: string | Array<{
    loc: string[]
    msg: string
    type: string
  }>
}