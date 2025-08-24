# 量化回测系统｜渐进式开发计划 V2

> **协作说明**：本计划面向人工与AI协作开发。以5个人工检查点为核心节点，每个节点必须人工确认后才能继续。开发文档以时间戳方式保存在`docs/dev/`目录。

---

## 开发执行规范

### AI开发者必读

**每个任务开始前：**
1. 读取 `ui.html` 对应部分
2. 查看最新的开发文档
3. 检查 `docs/dev/` 中的历史记录
4. 确认前置任务状态

**每个任务完成后：**
1. 生成开发记录：`docs/dev/YYYYMMDD_HHMM_任务名.md`
2. 更新任务状态文件：`docs/dev/task_status.json`
3. 运行相关测试并记录结果
4. 等待人工确认或AI验证

### 文档管理策略

```
docs/
├── dev/                    # 开发过程文档
│   ├── 20250120_1430_framework_init.md
│   ├── 20250121_0930_data_layer.md
│   └── task_status.json   # 任务状态跟踪
├── checkpoints/           # 人工检查点记录
│   ├── checkpoint_1_confirmed.md
│   └── ...
├── contracts/             # API契约快照
│   └── openapi.json      # 自动生成的API契约
└── final/                 # 最终文档（项目完成后）
```

---

## 人工检查点定义

| 检查点 | 名称 | 核心验证内容 | 通过标准 |
|--------|------|--------------|----------|
| CP1 | 框架验证 | 框架运行+**服务可控** | UI框架一致+**服务控制台可用** |
| CP2 | 页面完成 | 所有页面UI元素完整 | 像素级对齐ui.html |
| CP3 | 数据下载 | 数据下载功能完整 | 成功下载并存储数据 |
| CP4 | 数据筛选 | 标签计算和筛选功能 | 6种标签规则正确 |
| CP5 | 策略回测 | 完整回测流程 | 指标准确，可保存实验 |

---

## Phase 0：环境准备

### M0：基础环境

#### T0.1：项目初始化
```yaml
任务ID: T0.1
前置: 无
输入: 项目需求文档
动作:
  1. 创建项目目录结构
  2. 初始化Git仓库
  3. 配置.gitignore和.editorconfig
  4. 创建CI/CD配置文件（.github/workflows/）
输出:
  - 完整的项目结构
  - CI配置文件
验收:
  - 目录结构清晰
  - Git正常工作
  - CI配置就绪
文档: docs/dev/[timestamp]_project_init.md
```

#### T0.2：依赖安装（增强版）
```yaml
任务ID: T0.2
前置: T0.1
输入: 技术栈要求
动作:
  1. 前端依赖：
     - React, Electron, Ant Design
     - Zustand（状态管理）
     - Recharts（图表库）
     - TypeScript, ESLint, Prettier
  2. 后端依赖：
     - FastAPI, DuckDB, Polars
     - pydantic, uvicorn
     - pytest, black, mypy
  3. 工具链配置
输出:
  - package.json（含所有前端依赖）
  - pyproject.toml（含所有后端依赖）
  - 依赖锁文件
验收:
  - npm install成功
  - poetry install成功
  - 所有工具可用
文档: docs/dev/[timestamp]_dependencies.md
```

---

## Phase 1：框架搭建（含服务控制） → 检查点1

### M1：基础框架与服务可控性

#### T1.1：Electron壳程序
```yaml
任务ID: T1.1
前置: T0.2
关键: 必须参考ui.html的整体布局
输入: ui.html整体结构
动作:
  1. Electron主进程配置
  2. 窗口创建（1280x800）
  3. 基础菜单配置（含"系统→服务控制台"）
  4. 单实例锁实现
输出:
  - frontend/electron/main.js
  - 单实例锁机制
验收:
  - 窗口正常显示
  - 重复启动被阻止
  - 菜单项完整
文档: docs/dev/[timestamp]_electron_shell.md
```

#### T1.2：React应用框架
```yaml
任务ID: T1.2
前置: T1.1
关键: 5个页面名称必须与ui.html完全一致
输入: ui.html的5个页面定义
动作:
  1. React Router配置
  2. 创建5个页面组件占位
  3. Zustand状态管理初始化
  4. Electron加载React
输出:
  - frontend/src/App.tsx
  - frontend/src/pages/*.tsx (5个页面)
  - frontend/src/store/index.ts
验收:
  - 5个页面可切换
  - 路由正常工作
  - Zustand可用
文档: docs/dev/[timestamp]_react_framework.md
```

#### T1.3：UI布局实现
```yaml
任务ID: T1.3
前置: T1.2
关键: 侧边栏样式必须100%匹配ui.html
输入: ui.html的侧边栏设计
动作:
  1. Ant Design集成
  2. 侧边栏组件（宽240px，背景#1f2937）
  3. 导航菜单实现
  4. 底部状态栏
输出:
  - frontend/src/layouts/MainLayout.tsx
  - 完整的导航UI
验收:
  - 侧边栏样式完全匹配
  - 5个菜单项正确显示
  - 底部状态栏显示
文档: docs/dev/[timestamp]_ui_layout.md
```

#### T1.4：FastAPI服务框架（增强版）
```yaml
任务ID: T1.4
前置: T0.2
输入: 后端架构设计
动作:
  1. FastAPI应用结构
  2. 基础路由配置
  3. 健康检查接口（/healthz）
  4. 进程控制接口：
     - GET /process/status
     - POST /process/restart
     - POST /process/port/{port}
  5. 锁文件机制实现
输出:
  - backend/app/main.py
  - backend/app/api/health.py
  - backend/app/api/process.py
  - backend/app/core/lock.py
验收:
  - uvicorn可启动
  - /healthz返回200
  - 进程状态可查询
  - 锁文件防止重复启动
文档: docs/dev/[timestamp]_fastapi_enhanced.md
```

#### T1.5：契约自动化守护
```yaml
任务ID: T1.5
前置: T1.4
关键: 建立自动化契约验证机制
输入: 契约管理需求
动作:
  1. 配置FastAPI自动生成openapi.json
  2. 创建契约生成脚本：
     - 从openapi.json生成TypeScript类型
     - 快照比对机制
  3. 配置CI流程：
     - 契约变更检测
     - 类型自动同步
     - 不一致时阻断合并
输出:
  - scripts/generate-types.js
  - .github/workflows/contract-check.yml
  - frontend/src/types/api-generated.ts
验收:
  - 类型自动生成成功
  - CI检查正常工作
  - 契约变更可追踪
文档: docs/dev/[timestamp]_contract_automation.md
测试: 必须包含契约验证测试
```

#### T1.6：服务控制台与端口防护【核心】
```yaml
任务ID: T1.6
前置: T1.1, T1.4
关键: 这是CP1的核心验收项
输入: 服务管理需求
动作:
  1. 端口管理：
     - 端口池定义（5317, 5320-5350）
     - 端口探测与占用检测
     - 端口切换机制
  2. 进程管理：
     - Electron spawn Python进程
     - 健康检查轮询（每30秒）
     - 进程崩溃自动重启（最多3次）
  3. 服务控制台UI：
     - 独立窗口或嵌入式面板
     - 显示：状态、端口、PID、日志尾部
     - 操作：启动/停止/重启/切换端口
  4. 锁文件机制：
     - service.lock格式：{pid, port, started_at}
     - Windows: %APPDATA%\QuantBacktest\
     - macOS/Linux: ~/.quant-backtest/
输出:
  - frontend/electron/services/backend.js
  - frontend/src/windows/ServiceConsole.tsx
  - 完整的服务管理功能
验收:
  - Python随Electron启动/关闭
  - 端口冲突时自动切换
  - 重复启动显示明确错误
  - 服务状态实时可见
  - 可手动重启和切换端口
文档: docs/dev/[timestamp]_service_control.md
测试: 必须包含端口冲突和进程管理测试
```

#### T1.7：前后端通信验证
```yaml
任务ID: T1.7
前置: T1.6
输入: API调用需求
动作:
  1. CORS配置
  2. API客户端封装
  3. 错误处理机制
  4. 重试逻辑
输出:
  - frontend/src/api/client.ts
  - 统一的API调用层
验收:
  - 前端能调用所有API
  - 错误有友好提示
  - 网络异常可恢复
文档: docs/dev/[timestamp]_api_client.md
测试: API调用集成测试
```

### 【检查点1：框架验证+服务可控】
```yaml
人工确认项:
□ Electron应用正常启动
□ 5个页面都可以访问和切换
□ 侧边栏样式与ui.html完全一致
□ 服务控制台可以打开
□ 显示后端服务状态（运行/端口/PID）
□ 端口被占用时能自动切换
□ 重复启动有明确错误提示
□ 可以手动重启服务
□ 契约自动生成工作
□ CI契约检查通过

确认后生成: docs/checkpoints/checkpoint_1_confirmed.md
```

---

## Phase 2：页面完善 → 检查点2

### M2：页面UI实现

#### T2.1：数据管理页面
```yaml
任务ID: T2.1
前置: CP1确认
关键: 严格对照ui.html的数据管理页
输入: ui.html数据管理页面
动作:
  1. 基础数据下载卡片
  2. 数据标签管理表格
  3. 分钟级数据（折叠面板）
  4. 任务队列显示组件
输出:
  - frontend/src/pages/DataManagement/*.tsx
验收:
  - 所有UI元素齐全
  - 表格列完全匹配
  - 按钮文案一致
文档: docs/dev/[timestamp]_data_page_ui.md
测试: UI快照测试
```

#### T2.2：策略管理页面
```yaml
任务ID: T2.2
前置: CP1确认
关键: 两个策略卡片的8个参数必须完整
输入: ui.html策略管理页面
动作:
  1. 策略卡片组件
  2. 参数展示列表（8个字段）
  3. 操作按钮
输出:
  - frontend/src/pages/StrategyManagement.tsx
  - frontend/src/components/StrategyCard.tsx
验收:
  - 两个策略卡片正确显示
  - 所有参数字段齐全
  - 样式完全匹配
文档: docs/dev/[timestamp]_strategy_page_ui.md
测试: 组件渲染测试
```

#### T2.3：回测页面
```yaml
任务ID: T2.3
前置: CP1确认
关键: 三步骤配置流程必须清晰
输入: ui.html回测页面
动作:
  1. 当前策略蓝条
  2. 三步骤表单
  3. 结果展示区域（初始隐藏）
  4. Recharts图表组件准备
输出:
  - frontend/src/pages/Backtest/*.tsx
验收:
  - 步骤1-3表单完整
  - 参数输入框齐全
  - 结果区域布局正确
文档: docs/dev/[timestamp]_backtest_page_ui.md
测试: 表单验证测试
```

#### T2.4：深度测试页面
```yaml
任务ID: T2.4
前置: CP1确认
关键: 显示"功能开发中"
输入: ui.html深度测试页面
动作:
  1. 页面布局
  2. 参数配置表单
  3. 禁用状态处理
输出:
  - frontend/src/pages/DeepTest.tsx
验收:
  - 布局与ui.html一致
  - 按钮显示"功能开发中"
文档: docs/dev/[timestamp]_deeptest_page_ui.md
```

#### T2.5：历史实验页面
```yaml
任务ID: T2.5
前置: CP1确认
关键: 表格7列必须完整
输入: ui.html历史实验页面
动作:
  1. 筛选条件区
  2. 实验列表表格（7列）
  3. 操作按钮组
输出:
  - frontend/src/pages/Experiments.tsx
验收:
  - 表格列完全匹配
  - 筛选表单完整
  - 操作按钮齐全
文档: docs/dev/[timestamp]_experiments_page_ui.md
测试: 表格渲染测试
```

### 【检查点2：页面完成】
```yaml
人工确认项:
□ 数据管理页面所有元素齐全
□ 策略管理两个卡片完整显示
□ 回测页面三步骤清晰
□ 深度测试显示"功能开发中"
□ 历史实验表格列正确
□ 所有文案与ui.html一字不差
□ 颜色、间距、字体完全匹配

确认后生成: docs/checkpoints/checkpoint_2_confirmed.md
```

---

## Phase 3：数据功能（增强版） → 检查点3

### M3：数据下载与存储

#### T3.1：DuckDB企业级初始化
```yaml
任务ID: T3.1
前置: CP2确认
关键: 必须包含版本管理和备份机制
输入: 数据库设计文档
动作:
  1. 数据库初始化：
     - DuckDB连接池管理
     - 表结构创建（含索引）
     - schema_version表创建
  2. 版本管理：
     - 数据库版本跟踪
     - 升级脚本框架
  3. 备份机制：
     - 自动备份策略（每日）
     - 备份目录：backup/YYYYMMDD/
     - 保留最近7份备份
  4. 并发控制：
     - 实现单写多读策略
     - 写操作串行化队列
输出:
  - backend/app/db/connection.py
  - backend/app/db/schema.sql
  - backend/app/db/migration.py
  - backend/app/db/backup.py
  - data.duckdb文件
验收:
  - 数据库版本可查询
  - 备份自动执行
  - 并发写入无冲突
文档: docs/dev/[timestamp]_database_enterprise.md
测试: 数据库并发测试、备份恢复测试
```

#### T3.2：数据迁移工具
```yaml
任务ID: T3.2
前置: T3.1
输入: 旧数据格式规范
动作:
  1. 迁移脚本实现：
     - 支持Parquet导入
     - 支持SQLite导入
     - 批量处理机制
  2. 数据校验：
     - 行数对比
     - 数据完整性检查
     - 异常数据报告
输出:
  - tools/migrate.py
  - 迁移报告模板
验收:
  - 可导入旧数据
  - 校验报告准确
文档: docs/dev/[timestamp]_data_migration.md
测试: 迁移正确性测试
```

#### T3.3：数据模型定义
```yaml
任务ID: T3.3
前置: T3.1
输入: 领域模型设计
动作:
  1. Pydantic模型定义
  2. TypeScript类型定义
  3. 契约同步验证
输出:
  - backend/app/models/*.py
  - frontend/src/types/*.ts
验收:
  - 类型定义完整
  - 前后端一致
文档: docs/dev/[timestamp]_data_models.md
测试: 模型序列化测试
```

#### T3.4：任务队列系统（精确定义）
```yaml
任务ID: T3.4
前置: T3.3
关键: 任务模型必须完整
输入: 异步任务需求
动作:
  1. 任务模型定义：
     - status: queued/running/succeeded/failed/canceled
     - progress: 0-100整数
     - error_code: 错误代码
     - message: 用户友好信息
  2. 任务队列实现：
     - 内存队列（单机版）
     - 优先级支持
     - 取消机制
  3. 幂等性保证：
     - 任务去重
     - 重试机制（最多3次）
输出:
  - backend/app/core/task_queue.py
  - backend/app/models/task.py
验收:
  - 任务状态正确流转
  - 可取消运行中任务
  - 重试机制工作
文档: docs/dev/[timestamp]_task_queue_precise.md
测试: 任务状态机测试
```

#### T3.5：下载服务实现
```yaml
任务ID: T3.5
前置: T3.4
输入: yfinance API文档
动作:
  1. 股票列表获取（NASDAQ/NYSE）
  2. 批量下载（每批100只）
  3. 断点续传支持
  4. 数据验证与存储
输出:
  - backend/app/services/downloader.py
  - backend/app/api/data.py
验收:
  - 可下载3500+股票
  - 失败自动重试
  - 数据完整存储
文档: docs/dev/[timestamp]_download_service.md
测试: 下载服务单元测试
```

#### T3.6：WebSocket进度推送
```yaml
任务ID: T3.6
前置: T3.4
输入: 实时通信需求
动作:
  1. WebSocket端点实现
  2. 任务进度事件定义
  3. 断线重连机制
  4. 前端WebSocket客户端
输出:
  - backend/app/api/websocket.py
  - frontend/src/api/websocket.ts
验收:
  - 连接稳定
  - 进度实时更新
  - 断线自动重连
文档: docs/dev/[timestamp]_websocket_progress.md
测试: WebSocket连接测试
```

#### T3.7：下载UI集成
```yaml
任务ID: T3.7
前置: T3.6
输入: 数据下载交互需求
动作:
  1. 任务触发界面
  2. 进度条组件
  3. 错误提示处理
  4. 任务队列显示
输出:
  - 下载功能完整集成
验收:
  - 点击下载触发任务
  - 进度实时显示
  - 错误友好提示
文档: docs/dev/[timestamp]_download_ui_integration.md
测试: 端到端下载测试
```

### 【检查点3：数据下载成功】
```yaml
人工确认项:
□ 点击"执行下载"按钮响应正常
□ 任务进度条实时更新
□ NASDAQ数据下载成功（3000+股票）
□ NYSE数据下载成功（2000+股票）
□ 数据正确存储在DuckDB中
□ 数据库备份自动执行
□ 并发写入无错误
□ 任务可取消和重试

确认后生成: docs/checkpoints/checkpoint_3_confirmed.md
```

---

## Phase 4：数据筛选 → 检查点4

### M4：标签计算功能

#### T4.1：标签规则实现（含测试）
```yaml
任务ID: T4.1
前置: CP3确认
关键: 6种规则必须与ui.html一致
输入: ui.html标签规则列表
动作:
  1. 规则实现：
     - 涨幅最大TOP20
     - 跌幅最大TOP20
     - 市值涨幅最大TOP20
     - 市值跌幅最大TOP20
     - 成交量最大TOP20
     - 换手率最高TOP20
  2. 单元测试编写：
     - 每个规则的正确性测试
     - 边界条件测试
输出:
  - backend/app/services/label_calculator.py
  - backend/app/labels/rules/*.py
  - tests/test_label_rules.py
验收:
  - 6种规则计算正确
  - TOP20排名准确
  - 测试覆盖率>90%
文档: docs/dev/[timestamp]_label_rules.md
测试: 标签规则单元测试必须通过
```

#### T4.2：标签计算API
```yaml
任务ID: T4.2
前置: T4.1
输入: 标签管理需求
动作:
  1. API接口实现：
     - POST /labels/run
     - GET /labels/list
     - GET /labels/preview
  2. 异步任务集成
  3. 结果缓存机制
输出:
  - backend/app/api/labels.py
验收:
  - API可触发计算
  - 结果可查询
  - 性能满足要求
文档: docs/dev/[timestamp]_label_api.md
测试: API集成测试
```

#### T4.3：标签UI功能
```yaml
任务ID: T4.3
前置: T4.2
输入: 标签管理交互
动作:
  1. 创建标签对话框
  2. 标签列表刷新
  3. 查看结果功能
  4. 状态实时更新
输出:
  - 标签管理功能完整
验收:
  - 可创建新标签
  - 计算状态更新
  - 结果可查看
文档: docs/dev/[timestamp]_label_ui_integration.md
测试: 标签管理端到端测试
```

### 【检查点4：数据筛选成功】
```yaml
人工确认项:
□ 6种标签规则全部可用
□ 标签计算结果正确（抽查验证）
□ 每日TOP20数据完整
□ 筛选条件正常工作
□ 市值过滤有效
□ 涨跌幅限制有效
□ 查看结果功能正常
□ 所有标签测试通过

确认后生成: docs/checkpoints/checkpoint_4_confirmed.md
```

---

## Phase 5：核心功能 → 检查点5

### M5：策略与回测

#### T5.1：策略模板实现（含测试）
```yaml
任务ID: T5.1
前置: CP4确认
关键: 策略参数必须与ui.html完全一致
输入: 策略逻辑定义
动作:
  1. 逆向策略实现
  2. 动量策略实现
  3. 策略注册机制
  4. 策略单元测试
输出:
  - backend/app/strategies/*.py
  - tests/test_strategies.py
验收:
  - 策略逻辑正确
  - 参数完整匹配
  - 测试覆盖完整
文档: docs/dev/[timestamp]_strategy_templates.md
测试: 策略逻辑测试必须通过
```

#### T5.2：回测引擎
```yaml
任务ID: T5.2
前置: T5.1
输入: 回测逻辑设计
动作:
  1. 信号生成器
  2. 交易执行器
  3. 净值计算器
  4. 批次管理器
输出:
  - backend/app/engine/backtest.py
  - backend/app/engine/portfolio.py
验收:
  - 回测逻辑正确
  - 批次执行准确
文档: docs/dev/[timestamp]_backtest_engine.md
测试: 回测引擎单元测试
```

#### T5.3：指标计算（含验证）
```yaml
任务ID: T5.3
前置: T5.2
关键: 4个指标必须准确
输入: 指标计算公式
动作:
  1. 指标实现：
     - 总收益率
     - 年化收益
     - 最大回撤
     - 夏普比率
  2. 准确性测试：
     - 与Excel手工计算对比
     - 误差必须<0.1%
输出:
  - backend/app/engine/metrics.py
  - tests/test_metrics.py
验收:
  - 计算准确
  - 性能达标
文档: docs/dev/[timestamp]_metrics_calc.md
测试: 指标准确性测试（含对比数据）
```

#### T5.4：回测API
```yaml
任务ID: T5.4
前置: T5.3
输入: 回测接口设计
动作:
  1. POST /backtest/run
  2. 任务异步执行
  3. 结果返回格式
输出:
  - backend/app/api/backtest.py
验收:
  - API正常工作
  - 结果格式正确
文档: docs/dev/[timestamp]_backtest_api.md
测试: 回测API集成测试
```

#### T5.5：回测UI集成
```yaml
任务ID: T5.5
前置: T5.4
输入: 回测交互流程
动作:
  1. 参数提交
  2. 进度显示
  3. 结果展示（Recharts图表）
  4. 指标卡片
输出:
  - 回测功能完整集成
验收:
  - 完整流程通过
  - 图表正确显示
文档: docs/dev/[timestamp]_backtest_ui_integration.md
测试: 回测端到端测试
```

#### T5.6：实验管理（增强版）
```yaml
任务ID: T5.6
前置: T5.5
关键: 必须保证科学可复现性
输入: 实验管理需求
动作:
  1. 实验数据模型：
     - strategy_cfg_json: 完整策略参数
     - data_snapshot_hash: 数据集哈希
     - result_hash: 结果唯一哈希
  2. 保存实验功能
  3. 实验列表查询
  4. 复跑功能：
     - 参数恢复
     - 结果一致性校验
     - 哈希值对比警告
  5. 软删除机制
输出:
  - backend/app/api/experiments.py
  - backend/app/services/experiment_manager.py
验收:
  - 可保存和复跑
  - result_hash一致
  - 数据可追溯
文档: docs/dev/[timestamp]_experiment_reproducible.md
测试: 实验复现性测试
```

#### T5.7：性能基准测试
```yaml
任务ID: T5.7
前置: T5.6
关键: 必须满足性能指标
输入: 性能要求
动作:
  1. 创建基准测试脚本
  2. 测试场景：
     - 硬件：Apple M1, 16GB RAM（或等效）
     - 数据：500股票 x 2年日线
     - 策略：5批次回测
  3. 性能优化（如需要）
输出:
  - tests/benchmark/backtest_performance.py
  - 性能测试报告
验收:
  - 端到端耗时<10秒
  - 内存占用<2GB
文档: docs/dev/[timestamp]_performance_benchmark.md
测试: 性能基准必须通过
```

### 【检查点5：策略回测成功】
```yaml
人工确认项:
□ 两个策略都可以运行
□ 回测参数配置正常
□ 回测执行无错误
□ 4个指标显示正确（误差<0.1%）
□ 净值曲线合理
□ 交易明细完整
□ 可保存为实验
□ 实验可以复跑
□ 复跑结果哈希一致
□ 性能测试通过（<10秒）

确认后生成: docs/checkpoints/checkpoint_5_confirmed.md
```

---

## Phase 6：系统完善

### M6：集成优化

#### T6.1：错误处理增强
```yaml
任务ID: T6.1
前置: CP5确认
输入: 错误场景列表
动作:
  1. 全局错误边界
  2. API错误统一处理
  3. 用户友好提示
  4. 错误日志记录
输出:
  - 错误处理机制完善
验收:
  - 错误提示清晰
  - 可恢复操作
文档: docs/dev/[timestamp]_error_handling.md
测试: 错误处理测试
```

#### T6.2：UI细节对齐
```yaml
任务ID: T6.2
前置: M5
关键: 逐像素对比ui.html
输入: ui.html完整内容
动作:
  1. 颜色值精确匹配
  2. 间距尺寸调整
  3. 文案完全一致
  4. 交互行为对齐
输出:
  - UI 100%对齐
验收:
  - 对比工具无差异
  - 所有文案一字不差
文档: docs/dev/[timestamp]_ui_alignment.md
测试: UI快照对比测试
```

#### T6.3：测试覆盖率提升
```yaml
任务ID: T6.3
前置: M5
输入: 测试要求
动作:
  1. 补充单元测试
  2. 集成测试完善
  3. E2E测试场景
输出:
  - 完整测试套件
验收:
  - 后端覆盖率>60%
  - 前端覆盖率>60%
  - 关键路径100%覆盖
文档: docs/dev/[timestamp]_test_coverage.md
```

---

## Phase 7：打包交付

### M7：产品化

#### T7.1：打包配置（详细化）
```yaml
任务ID: T7.1
前置: M6
关键: Python运行时必须正确打包
输入: 打包需求
动作:
  1. electron-builder配置：
     - 应用图标和元数据
     - 代码签名（如有）
     - 自动更新配置
  2. Python运行时打包：
     - 使用PyInstaller打包后端
     - 或嵌入Python解释器
  3. 启动逻辑：
     - 轮询/healthz确保后端就绪
     - 失败时显示诊断信息
输出:
  - 可执行程序包
  - 安装程序
验收:
  - Windows包正常运行
  - macOS包正常运行
  - 无需预装Python
文档: docs/dev/[timestamp]_packaging.md
```

#### T7.2：最终文档
```yaml
任务ID: T7.2
前置: 所有功能完成
输入: 所有开发文档
动作:
  1. 用户手册
  2. API文档（从openapi.json生成）
  3. 部署指南
  4. 故障排查指南
输出:
  - docs/final/*.md
验收:
  - 文档完整清晰
  - 包含所有功能说明
文档: 正式文档
```

---

## 风险管理（更新版）

### 关键风险缓解

| 风险 | 缓解策略 | 实施时机 |
|------|---------|----------|
| 服务黑盒调试困难 | 服务控制台提前到Phase 1 | T1.6完成 |
| 前后端类型不一致 | 契约自动化守护 | T1.5建立 |
| 数据丢失风险 | 自动备份机制 | T3.1实现 |
| 实验不可复现 | 哈希值校验机制 | T5.6保证 |
| 性能不达标 | 基准测试提前验证 | T5.7执行 |

### 质量保证措施

1. **测试左移**：每个功能任务必须包含对应测试
2. **契约守护**：CI自动检查API契约一致性
3. **性能门槛**：基准测试不通过则阻断发布
4. **文档同步**：每个任务完成必须更新文档

---

## 执行检查清单

### 每个任务执行时

- [ ] 查看ui.html对应部分
- [ ] 检查契约是否需要更新
- [ ] 编写对应的测试用例
- [ ] 运行测试确保通过
- [ ] 生成任务文档
- [ ] 更新task_status.json

### 每个检查点前

- [ ] 所有前置任务完成
- [ ] 测试全部通过
- [ ] 契约检查通过
- [ ] 性能指标达标
- [ ] 文档已更新

---

*本计划为活文档，根据实际开发情况动态调整。所有修改需记录在`docs/dev/`目录。*