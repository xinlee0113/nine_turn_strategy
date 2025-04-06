# 项目结构指南

## 目录结构

```
.
├── configs/                 # 配置文件目录
│   ├── tiger/              # 老虎证券配置
│   │   ├── private_key.pem
│   │   └── tiger_openapi_config.properties
│   └── ib/                 # IB配置
│       ├── ib_config.yaml
│       └── ib_credentials.yaml
│
├── docs/                   # 文档目录
│   ├── api/               # API文档
│   ├── strategy/          # 策略文档
│   ├── development/       # 开发文档
│   └── examples/          # 示例代码
│       └── backtrader_tiger_live_trading_demo.py  # 老虎证券实盘交易示例
│
├── logs/                  # 日志目录
│   ├── backtest/         # 回测日志
│   ├── live/            # 实盘日志
│   └── optimization/    # 优化日志
│
├── outputs/              # 输出目录
│   ├── backtest/        # 回测结果
│   ├── live/           # 实盘结果
│   └── optimization/   # 优化结果
│
├── research/            # 研究目录
│   ├── data/          # 研究数据
│   ├── notebooks/     # 研究笔记
│   └── reports/       # 研究报告
│
├── scripts/            # 脚本目录
│   ├── backtest.py    # 回测脚本
│   ├── live.py        # 实盘脚本
│   └── optimize.py    # 优化脚本
│
├── src/               # 源代码目录
│   ├── brokers/      # 券商接口
│   │   ├── tiger/   # 老虎证券 (基于tigeropen3.3.3)
│   │   │   ├── __init__.py
│   │   │   ├── client.py      # 客户端管理
│   │   │   ├── config.py      # 配置管理
│   │   │   ├── contract.py    # 合约管理
│   │   │   ├── data.py        # 数据获取
│   │   │   ├── market.py      # 市场状态
│   │   │   ├── order.py       # 订单管理
│   │   │   └── examples/      # 官方示例代码
│   │   │       ├── __init__.py
│   │   │       ├── client_config.py        # 客户端配置示例
│   │   │       ├── trade_client_demo.py    # 交易客户端示例
│   │   │       ├── push_client_demo.py     # 推送客户端示例
│   │   │       ├── push_client_stomp_demo.py  # STOMP协议推送示例
│   │   │       ├── quote_client_demo.py    # 行情客户端示例
│   │   │       ├── financial_demo.py       # 财务数据示例
│   │   │       ├── nasdaq100.py            # 纳斯达克100指数示例
│   │   │       ├── backtrader_tiger_live_trading_demo.py  # 基于backtrader的实盘交易示例
│   │   │       └── option_helpers/         # 期权工具示例
│   │   │           ├── __init__.py
│   │   │           └── helpers.py          # 期权辅助函数
│   │   └── ib/      # Interactive Brokers
│   │       ├── __init__.py
│   │       ├── client.py
│   │       ├── config.py
│   │       ├── contract.py
│   │       ├── data.py
│   │       ├── market.py
│   │       └── order.py
│   │
│   ├── strategy/     # 策略模块
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── signal.py
│   │   ├── position.py
│   │   └── risk.py
│   │
│   ├── strategies/   # 具体策略
│   │   └── magic_nine/  # 神奇九转策略
│   │       ├── __init__.py
│   │       └── base.py  # 综合版本（包含九转序列、均线、RSI、KDJ、MACD）
│   │
│   ├── backtest/    # 回测模块 (基于backtrader1.9.78.123)
│   │   ├── __init__.py
│   │   ├── engine.py      # 回测引擎
│   │   ├── analyzer.py    # 回测分析器
│   │   ├── metrics.py     # 回测指标
│   │   └── visualizer.py  # 回测可视化
│   │
│   ├── optimization/  # 优化模块
│   │   ├── __init__.py
│   │   ├── optimizer.py
│   │   ├── grid_search.py
│   │   └── genetic.py
│   │
│   └── live/        # 实盘模块
│       ├── __init__.py
│       └── engine.py
│
├── tests/           # 测试目录
│   ├── __init__.py
│   ├── test_strategy.py
│   ├── test_backtest.py
│   ├── test_optimization.py
│   └── test_live.py
│
├── main.py         # 主程序入口
├── requirements.txt  # 依赖包
└── README.md       # 项目说明
```

## 模块说明

### 1. 研究模块 (research/)
- **notebooks/**: 用于策略研究、回测分析和实盘交易的Jupyter notebooks
- **data/**: 存储市场数据、回测结果和实盘结果

### 2. 策略模块 (src/strategy/)
- **base.py**: 定义策略基类，提供通用接口
- **signal.py**: 信号生成模块
- **position.py**: 仓位管理模块
- **risk.py**: 风险管理模块

### 3. 具体策略 (src/strategies/)
- **magic_nine/**: 神奇九转策略实现
  - **base.py**: 综合版本（包含九转序列、均线、RSI、KDJ、MACD）

### 4. 回测模块 (src/backtest/)
- **engine.py**: 回测引擎
- **analyzer.py**: 回测分析器
- **metrics.py**: 性能指标计算
- **visualizer.py**: 回测结果可视化

### 5. 参数优化模块 (src/optimization/)
- **optimizer.py**: 优化器基类
- **grid_search.py**: 网格搜索优化器
- **genetic.py**: 遗传算法优化器

### 6. 实盘交易模块 (src/live/)
- **engine.py**: 实盘交易引擎

### 7. 券商接口模块 (src/brokers/)
- **tiger/**: 老虎证券接口
  - **config.py**: 配置管理
  - **client.py**: 客户端管理
  - **market.py**: 市场状态
  - **contract.py**: 合约管理
  - **order.py**: 订单执行
  - **data.py**: 数据获取
- **ib/**: Interactive Brokers接口
  - **config.py**: 配置管理
  - **client.py**: 客户端管理
  - **market.py**: 市场状态
  - **contract.py**: 合约管理
  - **order.py**: 订单执行
  - **data.py**: 数据获取

### 8. 数据模块 (src/data/)
- **fetcher.py**: 数据获取
- **processor.py**: 数据处理
- **validator.py**: 数据验证

### 9. 工具模块 (src/utils/)
- **config.py**: 配置管理
- **logging.py**: 日志工具
- **helpers.py**: 辅助函数

### 10. 配置模块 (configs/)
- **strategy/**: 策略相关配置
- **backtest.yaml**: 回测配置
- **live.yaml**: 实盘配置
- **optimization.yaml**: 参数优化配置
- **tiger/**: 老虎证券配置
  - **private_key.pem**: 私钥文件
  - **tiger_openapi_config.properties**: API配置
- **ib/**: Interactive Brokers配置
  - **ib_config.yaml**: API配置

### 11. 脚本模块 (scripts/)
- **run_backtest.py**: 运行回测
- **analyze.py**: 分析回测结果
- **run_live.py**: 运行实盘
- **optimize.py**: 运行参数优化

### 12. 文档模块 (docs/)
- **strategy.md**: 策略文档
- **backtest.md**: 回测文档
- **live.md**: 实盘文档
- **optimization.md**: 优化文档
- **images/**: 图片目录
  - **神奇九转.png**: 策略说明图

### 13. 日志模块 (logs/)
- **backtest/**: 回测日志
- **live/**: 实盘日志
- **optimization/**: 优化日志
- **tiger/**: 老虎证券日志
- **ib/**: Interactive Brokers日志

### 14. 输出模块 (out/)
- **backtest/**: 回测结果
- **live/**: 实盘结果
- **optimization/**: 优化结果

### 15. 测试模块 (tests/)
- 单元测试和集成测试

## 依赖说明

- 老虎证券SDK: tigeropen3.3.3
- 回测框架: backtrader1.9.78.123
- 数据处理: pandas, numpy
- 可视化: matplotlib, seaborn
- 优化算法: scipy, sklearn

## 开发规范

### 1. 代码规范
- 遵循PEP 8规范
- 使用类型注解
- 编写完整的文档字符串
- 保持代码简洁清晰

### 2. 测试规范
- 为每个模块编写单元测试
- 测试覆盖率要求>80%
- 定期运行集成测试

### 3. 文档规范
- 及时更新文档
- 保持文档与代码同步
- 使用Markdown格式

### 4. 版本控制
- 使用Git进行版本控制
- 遵循语义化版本号
- 保持提交信息清晰

## 回测框架说明

本项目使用 backtrader1.9.78.123 作为回测框架，主要特点：

1. 策略开发
   - 继承 `backtrader.Strategy` 类
   - 实现 `next()` 方法进行交易逻辑
   - 使用 `self.datas[0]` 访问数据
   - 使用 `self.buy()` 和 `self.sell()` 进行交易

2. 数据加载
   - 支持 CSV、Pandas DataFrame 等多种数据格式
   - 支持多时间周期数据
   - 支持多资产回测

3. 指标计算
   - 内置常用技术指标
   - 支持自定义指标
   - 支持指标组合

4. 交易执行
   - 支持市价单、限价单等多种订单类型
   - 支持滑点、手续费等交易成本
   - 支持仓位管理

5. 结果分析
   - 计算收益率、夏普比率等指标
   - 生成交易记录和权益曲线
   - 支持结果可视化

## 部署指南

### 1. 环境配置
- Python 3.8+
- 安装依赖包
- 配置环境变量

### 2. 数据准备
- 准备市场数据
- 配置数据源
- 验证数据质量

### 3. 运行流程
1. 配置策略参数
2. 运行回测
3. 分析回测结果
4. 优化策略参数
5. 部署实盘

### 4. 监控维护
- 监控实盘运行
- 定期检查日志
- 及时处理异常