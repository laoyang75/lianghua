# 量化回测系统 (QuantBacktest)

基于 Electron + FastAPI + DuckDB 的本地桌面量化策略回测工具

## 技术栈

### 前端
- **框架**: React + Electron + TypeScript
- **UI库**: Ant Design
- **状态管理**: Zustand
- **图表库**: Recharts

### 后端
- **框架**: FastAPI + Python 3.11
- **数据库**: DuckDB (单文件存储)
- **数据处理**: Polars (主要) + Pandas (兼容)
- **数据源**: yfinance

## 功能特性

- ✅ **数据管理**: 自动下载NASDAQ/NYSE股票数据
- ✅ **标签计算**: 6种预设筛选规则（涨幅、跌幅、市值等TOP20）
- ✅ **策略回测**: 逆向/动量策略回测，支持多批次执行
- ✅ **指标分析**: 总收益率、年化收益、最大回撤、夏普比率
- ✅ **实验管理**: 结果保存、复跑验证、历史对比
- ✅ **服务控制**: 端口管理、进程控制、状态监控

## 目录结构

```
├── frontend/          # 前端代码
│   ├── src/          # React应用源码
│   ├── electron/     # Electron主进程
│   └── public/       # 静态资源
├── backend/           # 后端代码
│   ├── app/          # FastAPI应用
│   └── tests/        # 后端测试
├── docs/             # 项目文档
├── data/             # 数据存储目录
└── tools/            # 工具脚本
```

## 开发指南

### 环境要求
- Node.js >= 18
- Python >= 3.11
- Git

### 安装依赖
```bash
# 前端依赖
cd frontend && npm install

# 后端依赖  
cd backend && pip install -r requirements.txt
```

### 开发运行
```bash
# 启动后端服务
cd backend && python -m app.main

# 启动前端开发服务器
cd frontend && npm run dev

# 启动Electron应用
npm run electron:dev
```

### 构建打包
```bash
# 构建生产版本
npm run build

# 打包Electron应用
npm run electron:build
```

## 使用说明

1. **数据准备**: 首次启动后，进入"数据管理"页面下载基础数据
2. **标签创建**: 选择筛选规则，创建股票标签
3. **策略配置**: 在"回测"页面配置策略参数
4. **执行回测**: 运行回测并查看结果指标
5. **实验管理**: 保存重要的回测结果供后续分析

## 开发状态

- [x] 项目架构设计
- [ ] 前端框架搭建
- [ ] 后端服务开发
- [ ] 数据处理模块
- [ ] 回测引擎实现
- [ ] UI界面开发
- [ ] 集成测试
- [ ] 打包发布

## 许可证

MIT License