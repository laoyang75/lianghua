# 本地桌面量化回测工具｜开发文档（Electron + FastAPI + 单文件存储版）

> 目标：**严格对齐 UI（ui.html）**，基于 React + Electron + Python(FastAPI) + DuckDB 单文件存储方案，提供完整的量化回测系统。

---

## 0. 总览与硬约束

### 核心目标
- **UI 对齐**：5 个一级页面（数据管理/策略管理/回测/深度测试/历史实验）的信息架构、控件与文案严格对齐 ui.html
- **单文件存储**：所有数据统一存储在 DuckDB 单文件中
- **契约优先**：所有接口、模型、流程先定义契约，再实现

### 技术栈（强约束）
- **前端**：React + Electron + Ant Design；Recharts（图表）；Zustand（状态管理）
- **后端**：Python 3.11 + FastAPI（本地 127.0.0.1:PORT）；Polars（批量导入/查询优先），Pandas（仅用于兼容）
- **存储**：DuckDB 单文件（.duckdb）
- **通信**：HTTP/JSON + WebSocket（任务进度）
- **测试**：前端 Jest + React Testing Library；后端 PyTest；M1-M3 覆盖率 ≥30%，最终 ≥60%
- **打包**：electron-builder（捆绑 Python 运行时）

### 开发原则
1. **阶段闸门**：每个里程碑必须通过验收标准（DoD）才能进入下一阶段
2. **一致性优先**：以 ui.html 的命名/布局/文案为唯一真相源（SSOT）
3. **契约优先**：任何改动必须先更新接口/模型契约，再改实现
4. **可回退**：每步提交均可独立运行或被后续完全覆盖

---

## 1. 架构与运行时

### 1.1 组件架构
- **Electron 主进程**：应用生命周期、窗口管理、启动/监控 Python 子进程
- **Renderer（React）**：UI 渲染、状态管理、调用后端 API
- **Python FastAPI**：业务逻辑、数据处理、DuckDB 读写
- **本地数据目录**：
  - Windows: `%APPDATA%\QuantBacktest\`
  - macOS/Linux: `~/.quant-backtest/`
  - 包含：`data.duckdb`、`logs/`、`exports/`、`reports/`、`config.toml`

### 1.2 启动流程
1. Electron 主进程拉起 `python -m backend.app --port=5317`
2. 健康检查 `/healthz`，失败自动重启（最多3次）
3. Renderer 获取端口后渲染 UI
4. 长任务以任务队列执行，进度通过 WebSocket 推送

### 1.3 首次启动流程
1. Electron 检查数据目录是否存在，不存在则创建
2. 检查 `data.duckdb` 是否存在
3. 若不存在，FastAPI 服务初始化空数据库并执行 schema 脚本
4. 前端检测数据状态（`GET /data/status`），显示引导信息
5. 提示用户"执行下载"初始化基础数据

### 1.4 服务控制台与端口管理

#### UI设计
- 通过菜单 `系统 → 服务控制台` 打开独立窗口
- 显示：状态、端口、PID、日志尾部、健康检查结果
- 操作：启动/停止/重启/切换端口/刷新模块

#### 端口冲突防护
```typescript
// 端口探测实现
const PORT_POOL = [5317, ...Array.from({length:30}, (_,i)=>5320+i)];

async function ensureBackend() {
  for (const p of PORT_POOL) {
    const ok = await tryAdoptExisting(p) || await trySpawnNew(p);
    if (ok) return p;
  }
  dialog.showErrorBox('端口冲突','无法获得可用端口');
}
```

#### 锁文件机制
- Windows: `%APPDATA%\QuantBacktest\service.lock`
- macOS/Linux: `~/.quant-backtest/service.lock`
- 格式：`{pid, port, started_at}`

---

## 2. 统一存储方案（DuckDB）

### 2.1 表结构设计

```sql
-- 日线价格数据
CREATE TABLE prices_daily (
    date DATE,
    symbol VARCHAR,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    adj_close DOUBLE,
    calendar_id VARCHAR,
    PRIMARY KEY (date, symbol)
);

-- 标签数据
CREATE TABLE labels (
    trade_date DATE,
    label_name VARCHAR,
    symbol VARCHAR,
    score DOUBLE,
    rank INTEGER,
    meta_json JSON, -- {'rule': '涨幅最大TOP20', 'description': '...'}
    UNIQUE (trade_date, label_name, rank)
);

-- 实验记录
CREATE TABLE experiments (
    id VARCHAR PRIMARY KEY,
    created_at TIMESTAMP,
    strategy_name VARCHAR,
    label_name VARCHAR,
    cfg_json JSON,
    metrics_json JSON,
    result_hash VARCHAR,
    deleted_at TIMESTAMP
);

-- 任务队列
CREATE TABLE tasks (
    task_id VARCHAR PRIMARY KEY,
    type VARCHAR,
    status VARCHAR,
    progress INTEGER,
    message TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    payload_json JSON
);
```

### 2.2 数据操作规范
- **批量导入**：使用 Polars DataFrame → DuckDB COPY
- **增量更新**：基于 `date >= last_date(symbol)` 判断
- **查询优化**：常用字段建立索引和 zone map
- **并发控制**：单机串行写、多读共享

---

## 3. 领域模型定义

### 3.1 策略配置（StrategyCfg）

**Python (Pydantic)**
```python
class StrategyCfg(BaseModel):
    name: str
    buy_timing: Literal["T+1开盘", "T+1收盘", "T+2开盘"]
    sell_timing: Literal["开盘", "收盘"]
    hold_days: int = Field(ge=1, le=30)
    execution_frequency: int  # 执行频率（天）
    execution_count: int      # 执行次数
    positioning: Literal["equal_weight", "market_cap_weight"]
    initial_capital: float
    filter_rules: dict  # 市值、涨跌幅等过滤条件
```

**TypeScript**
```typescript
interface StrategyCfg {
  name: string;
  buy_timing: "T+1开盘" | "T+1收盘" | "T+2开盘";
  sell_timing: "开盘" | "收盘";
  hold_days: number;
  execution_frequency: number;
  execution_count: number;
  positioning: "equal_weight" | "market_cap_weight";
  initial_capital: number;
  filter_rules: FilterRules;
}
```

### 3.2 回测结果（BacktestResult）

```python
class BacktestMetrics(BaseModel):
    total_return: float      # 总收益率
    ann_return: float       # 年化收益
    max_drawdown: float     # 最大回撤
    sharpe_ratio: float     # 夏普比率
    calmar_ratio: float     # 卡尔玛比率
    win_rate: float         # 胜率
    avg_trade_return: float # 平均交易收益

class BacktestResult(BaseModel):
    metrics: BacktestMetrics
    equity_curve: List[float]
    trades: List[TradeRecord]
    result_hash: str
```

### 3.3 实验（Experiment）

```python
class Experiment(BaseModel):
    id: str = Field(default_factory=lambda: f"EXP_{uuid4().hex[:6]}")
    created_at: datetime
    strategy_name: str
    label_name: str
    cfg_json: StrategyCfg
    metrics_json: BacktestMetrics
    result_hash: str
    deleted_at: Optional[datetime] = None
```

---

## 4. API 接口契约

### 4.1 健康与配置

#### GET /healthz
**Response 200:**
```json
{
  "version": "1.0.0",
  "duckdb_path": "/Users/data/cache/data.duckdb",
  "uptime": 3600
}
```

### 4.2 数据管理

#### POST /data/download
**Request Body:**
```json
{
  "universes": ["nasdaq", "nyse"],
  "start_date": "2023-01-01",
  "end_date": "2025-01-20",
  "source": "yfinance"
}
```
**Response 202:**
```json
{
  "task_id": "t-12345-download",
  "type": "data_download",
  "status": "queued",
  "message": "数据下载任务已加入队列"
}
```
**Error 400:**
```json
{
  "detail": "Invalid date range: start_date cannot be after end_date"
}
```

#### GET /data/status
**Response 200:**
```json
{
  "has_data": true,
  "total_symbols": 3500,
  "date_range": {
    "start": "2023-01-01",
    "end": "2025-01-20"
  },
  "last_update": "2025-01-20T10:30:00Z"
}
```

### 4.3 标签管理

#### POST /labels/run
**Request Body:**
```json
{
  "rule": "涨幅最大TOP20",
  "start_date": "2023-01-01",
  "end_date": "2025-01-20",
  "params": {
    "top_k": 20,
    "min_market_cap": 100000000
  }
}
```
**Response 202:**
```json
{
  "task_id": "t-67890-label",
  "label_name": "rise20_20230101_20250120"
}
```

#### GET /labels/list
**Response 200:**
```json
{
  "labels": [
    {
      "name": "涨幅最大TOP20",
      "status": "done",
      "date_range": "2023-01-01 至 2025-01-20",
      "record_count": 10000
    }
  ]
}
```

### 4.4 策略与回测

#### POST /backtest/run
**Request Body:**
```json
{
  "strategy_cfg": {
    "name": "下跌买入策略",
    "buy_timing": "T+1开盘",
    "sell_timing": "开盘",
    "hold_days": 5,
    "execution_frequency": 7,
    "execution_count": 5,
    "positioning": "equal_weight",
    "initial_capital": 100000,
    "filter_rules": {
      "min_market_cap": 100000000,
      "max_drop_pct": -60
    }
  },
  "label_name": "drop20",
  "date_range": {
    "start": "2023-01-01",
    "end": "2025-01-20"
  }
}
```
**Response 200:**
```json
{
  "metrics": {
    "total_return": 0.235,
    "ann_return": 0.182,
    "max_drawdown": -0.123,
    "sharpe_ratio": 1.45,
    "calmar_ratio": 1.48,
    "win_rate": 0.65,
    "avg_trade_return": 0.024
  },
  "equity_curve": [1.0, 1.02, 1.01, ...],
  "trades": [...],
  "result_hash": "abc123def456"
}
```

### 4.5 WebSocket 事件

#### 连接：ws://localhost:5317/ws/tasks

**事件格式:**
```json
{
  "type": "task_progress",
  "task_id": "t-12345",
  "progress": 45,
  "message": "正在下载 AAPL 数据...",
  "data": {},
  "timestamp": "2025-01-20T10:30:00Z"
}
```

**事件类型:**
- `task_queued`: 任务入队
- `task_started`: 开始执行
- `task_progress`: 进度更新
- `task_completed`: 成功完成
- `task_failed`: 执行失败
- `task_cancelled`: 用户取消

---

## 5. 标签与策略扩展机制

### 5.1 标签计算规则（可扩展）

标签计算作为独立模块，新规则通过编程添加而非界面配置：

```python
# backend/labels/rules.py
class LabelRule(ABC):
    @abstractmethod
    def calculate(self, df: pl.DataFrame) -> pl.DataFrame:
        pass

class Top20RiseRule(LabelRule):
    """涨幅最大TOP20"""
    def calculate(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            ((pl.col("close") - pl.col("open")) / pl.col("open") * 100)
            .alias("change_pct")
        ).sort("change_pct", descending=True).head(20)

# 规则注册表
LABEL_RULES = {
    "涨幅最大TOP20": Top20RiseRule(),
    "跌幅最大TOP20": Top20DropRule(),
    "市值涨幅最大TOP20": MarketCapRiseRule(),
    "市值跌幅最大TOP20": MarketCapDropRule(),
    "成交量最大TOP20": VolumeTop20Rule(),
    "换手率最高TOP20": TurnoverTop20Rule()
}
```

### 5.2 策略模板（可扩展）

策略同样作为独立模块管理：

```python
# backend/strategies/templates.py
class StrategyTemplate(ABC):
    @abstractmethod
    def generate_signals(self, label_data: pl.DataFrame) -> List[Signal]:
        pass
    
    @abstractmethod
    def execute_trades(self, signals: List[Signal], prices: pl.DataFrame) -> List[Trade]:
        pass

class ReversalStrategy(StrategyTemplate):
    """逆向策略：下跌买入"""
    def generate_signals(self, label_data):
        # T日跌幅TOP N → T+1买入信号
        pass

class MomentumStrategy(StrategyTemplate):
    """动量策略：上涨买入"""
    def generate_signals(self, label_data):
        # T日市值涨幅TOP N → T+1买入信号
        pass

# 策略注册表
STRATEGY_TEMPLATES = {
    "下跌买入策略": ReversalStrategy(),
    "上涨买入策略": MomentumStrategy()
}
```

---

## 6. 指标计算规范

```python
class MetricsCalculator:
    def calculate_total_return(self, nav: List[float]) -> float:
        """总收益率 = nav[-1] - 1"""
        return nav[-1] - 1
    
    def calculate_annual_return(self, nav: List[float], days: int) -> float:
        """年化收益 = (nav[-1])^(252/days) - 1"""
        return (nav[-1] ** (252 / days)) - 1
    
    def calculate_max_drawdown(self, nav: List[float]) -> float:
        """最大回撤：峰值到谷值的最大跌幅"""
        peak = nav[0]
        max_dd = 0
        for value in nav:
            if value > peak:
                peak = value
            drawdown = (value - peak) / peak
            if drawdown < max_dd:
                max_dd = drawdown
        return max_dd
    
    def calculate_sharpe_ratio(self, returns: List[float], rf: float = 0) -> float:
        """夏普比率 = (mean_return - rf) / std_return * sqrt(252)"""
        mean_ret = np.mean(returns)
        std_ret = np.std(returns)
        return (mean_ret - rf) / std_ret * np.sqrt(252) if std_ret > 0 else 0
    
    def calculate_calmar_ratio(self, ann_return: float, max_dd: float) -> float:
        """卡尔玛比率 = ann_return / abs(max_dd)"""
        return ann_return / abs(max_dd) if max_dd != 0 else 0
```

---

## 7. 任务分解与计划

### 7.1 里程碑与任务

【PLAN_HINT】M0-服务可见化：
- 前置依赖：无
- 输入：端口配置、进程管理需求
- 动作：1)实现端口探测 2)进程锁机制 3)服务控制台UI
- 输出：服务控制台窗口、service.lock文件
- DoD：重复启动有提示、端口冲突可切换、Windows/macOS测试通过

【PLAN_HINT】M1-框架基线：
- 前置依赖：M0完成
- 输入：UI设计稿、路由配置
- 动作：1)Electron+React框架 2)FastAPI服务 3)DuckDB初始化
- 输出：5页可访问、API可调用、数据库文件创建
- DoD：页面切换正常、/healthz返回200、data.duckdb存在

此里程碑应分解为以下任务：

【PLAN_HINT】T-FR-01: Electron与React项目初始化
- 输入：无
- 动作：使用electron-builder和create-react-app搭建项目
- 输出：可启动的Electron应用，显示5个页面
- DoD：应用成功打包，页面切换正常

【PLAN_HINT】T-FR-02: FastAPI后端服务骨架
- 输入：无
- 动作：建立FastAPI项目结构，实现/healthz接口
- 输出：可被Electron拉起的FastAPI服务
- DoD：访问http://127.0.0.1:5317/healthz返回成功

【PLAN_HINT】T-FR-03: DuckDB初始化与连接
- 输入：表结构定义
- 动作：创建数据库文件，执行schema脚本
- 输出：data.duckdb文件，包含所有表结构
- DoD：所有表创建成功，可执行基本查询

【PLAN_HINT】T-FR-04: WebSocket任务通知通道
- 输入：任务事件定义
- 动作：实现WebSocket端点，定义事件格式
- 输出：可连接的ws://localhost:5317/ws/tasks
- DoD：前端可接收任务进度事件

【PLAN_HINT】M2-数据统一：
- 前置依赖：M1完成
- 输入：旧数据格式、迁移需求
- 动作：实现数据导入、迁移工具
- 输出：数据成功导入DuckDB
- DoD：DuckDB中labels表包含≥4个ui.html示例标签

【PLAN_HINT】T-DATA-001: 数据下载功能
- 前置依赖：M1-框架基线
- 输入：yfinance API、股票列表
- 动作：1)获取NASDAQ/NYSE列表 2)批量下载 3)进度推送
- 输出：prices_daily表数据、下载报告
- DoD：3500+股票数据入库、缺失率<5%、进度实时更新

【PLAN_HINT】T-LABEL-001: 标签计算引擎
- 前置依赖：T-DATA-001
- 输入：ui.html标签规则（6个）
- 动作：定义计算公式、Polars排序TOP20
- 输出：/labels/run接口、labels表数据
- DoD：至少6个规则测试通过、每日TOP20完整

【PLAN_HINT】M3-闭环最小可用：
- 前置依赖：M2完成
- 输入：完整数据、标签、策略定义
- 动作：实现回测引擎、指标计算
- 输出：完整回测流程
- DoD：四项指标齐全、实验可保存复跑

【PLAN_HINT】T-BT-001: 回测核心引擎
- 前置依赖：T-LABEL-001
- 输入：策略配置、价格数据、标签数据
- 动作：实现信号生成、交易执行、净值计算
- 输出：/backtest/run接口
- DoD：逆向策略运行成功、净值曲线正确

【PLAN_HINT】T-BT-002: 指标计算模块
- 前置依赖：T-BT-001
- 输入：交易记录、净值序列
- 动作：实现6个核心指标计算
- 输出：metrics_json结构
- DoD：所有指标与手工计算误差<0.1%

【PLAN_HINT】T-EXP-001: 实验管理功能
- 前置依赖：T-BT-002
- 输入：回测结果
- 动作：实现保存、列表、复跑、软删除
- 输出：/experiments/* 接口
- DoD：实验可保存、列表显示、复跑结果一致

---

## 8. 测试计划

### 8.1 集成测试场景

**完整闭环测试：**
1. 下载2年NASDAQ数据（~3500股票）
2. 计算跌幅TOP20标签
3. 运行逆向策略（5批次）
4. 验证4个核心指标
5. 保存并复跑实验
6. 验证result_hash一致性

**性能基准：**
- 3500股票2年数据导入 < 5分钟
- 标签计算 < 1分钟
- 单次回测 < 10秒
- WebSocket延迟 < 100ms

### 8.2 自检脚本

```python
# tools/self_check.py
def check_ui_alignment(ui_file: str, app_url: str) -> dict:
    """检查UI与接口对齐"""
    ui_elements = parse_ui_html(ui_file)
    app_state = fetch_app_state(app_url)
    
    diff_report = {
        "missing_pages": [],
        "incorrect_labels": [],
        "api_mismatches": []
    }
    
    # 检查页面、标签、按钮等
    return diff_report

# 执行：python -m tools.self_check --ui ui.html --app http://localhost:5317
```

---

## 9. UI对齐断言

### 数据管理页
- 存在"基础数据下载"、"数据标签管理"、"任务队列"
- "分钟级数据"为折叠面板，按钮禁用，显示"按需"
- 标签包含6种规则（涨幅/跌幅/市值涨幅/市值跌幅/成交量/换手率TOP20）

### 策略管理页
- 两张卡片："下跌买入策略"、"上涨买入策略"
- 字段严格匹配ui.html中的8个参数
- 按钮："使用此策略"、"查看详情"

### 回测页
- 三步骤配置 + "当前策略"蓝条显示
- 结果包含：总收益率、年化、最大回撤、夏普
- 净值曲线图表、交易明细表格
- 操作："保存为实验"、"导出报告"

### 深度测试页
- 参数穷举设置（持仓天数、执行频率、保留股票数）
- 优化目标选择（最大化收益/最小化回撤/最优夏普/最优卡尔玛）
- 按钮显示"开始深度测试（功能开发中）"并禁用

### 历史实验页
- 表格列：编号、时间、策略、标签、年化收益、最大回撤、夏普
- 操作：查看、复跑、删除（软删除）

### 系统菜单
- "系统→服务控制台"菜单项
- 控制台显示：端口、PID、状态、日志
- 重复启动显示错误提示

---

## 10. 配置管理

### config.toml
```toml
[server]
default_port = 5317
port_range = [5320, 5350]
health_check_interval = 30

[data]
default_source = "yfinance"
cache_days = 7
batch_size = 100

[strategy]
default_hold_days = 5
default_top_k = 20
default_capital = 100000

[database]
path = "data.duckdb"
backup_count = 3
```

---

## 11. 异常处理规范

### 网络异常
- 下载失败自动重试3次，支持断点续传
- 提供手动重试和跳过选项

### 数据异常
- 识别并标记异常数据（如涨跌幅>100%）
- 生成异常报告，提供修复建议

### 计算异常
- 保存中间状态，支持从断点恢复
- 详细错误日志，可导出分析

### 用户提示
- 分级显示：信息（蓝色）、警告（黄色）、错误（红色）
- 提供详细日志导出功能

---

## 12. 开发优先级

- **P0（必须）**：数据下载、标签计算、基础回测、实验保存
- **P1（重要）**：服务控制台、批量任务、导出功能
- **P2（可选）**：深度测试、分钟数据、高级优化器

---

## 13. 风险与备选方案

### 潜在风险
1. **DuckDB性能瓶颈**：若查询>1M行，考虑使用Parquet外部表
2. **Electron打包Python失败**：备选使用pyinstaller独立打包后端
3. **端口冲突无法解决**：提供手动配置端口选项
4. **内存溢出**：实现数据分批处理和流式计算

### 缓解措施
- 所有关键操作添加超时和取消机制
- 实现渐进式加载和虚拟滚动
- 提供数据导出和外部分析选项

---

## 14. 验收标准（DoD）

1. **UI对齐**：自检脚本diff_report为空
2. **功能闭环**：下载→标签→策略→回测→保存完整可用
3. **指标正确**：4项核心指标计算准确
4. **任务可见**：进度实时更新，错误明确提示
5. **数据完整**：result_hash可追溯，实验可复现
6. **测试覆盖**：M1-M3≥30%，最终≥60%
7. **存储统一**：单文件DuckDB正常工作
8. **服务可控**：控制台三项检查通过
9. **计划完整**：生成≥12个T-*任务
10. **文档一致**：代码实现与本文档契约100%匹配