# 项目架构设计图

## 目录

1. [工程结构](#工程结构)
    - [目录结构说明](#目录结构说明)
        - [配置文件目录](#1-配置文件目录-configs)
        - [源代码目录](#2-源代码目录-src)
        - [研究目录](#3-研究目录-research)
        - [日志目录](#4-日志目录-logs)
        - [输出目录](#5-输出目录-outputs)
        - [测试目录](#6-测试目录-tests)

2. [分层架构](#分层架构)
    - [分层说明](#分层说明)
        - [应用层](#1-应用层)
        - [业务层](#2-业务层)
        - [接口层](#3-接口层)
        - [基础设施层](#4-基础设施层)
    - [依赖关系说明](#依赖关系说明)

3. [关键流程时序图](#关键流程时序图)
    - [回测流程](#1-回测流程)
    - [参数优化流程](#2-参数优化流程)
    - [实盘交易流程](#3-实盘交易流程)
    - [数据加载流程](#4-数据加载流程)
    - [流程说明](#流程说明)

4. [分层架构类图](#分层架构类图)
    - [类关系说明](#类关系说明)

## 工程结构

```
nine_turn_strategy/
├── architecture_diagram.md
├── src/
│   ├── application/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── script_manager.py
│   │   ├── script_factory.py
│   │   └── scripts/
│   │       ├── __init__.py
│   │       ├── backtest_script.py
│   │       ├── optimize_script.py
│   │       └── trade_script.py
│   ├── business/
│   │   ├── __init__.py
│   │   ├── strategy/
│   │   │   ├── __init__.py
│   │   │   ├── base_strategy.py
│   │   │   ├── magic_nine.py
│   │   │   ├── signal_generator.py
│   │   │   ├── position_sizer.py
│   │   │   └── risk_manager.py
│   │   ├── indicators/
│   │   │   ├── __init__.py
│   │   │   ├── base_indicator.py
│   │   │   └── custom_indicators.py
│   │   ├── analyzers/
│   │   │   ├── __init__.py
│   │   │   ├── base_analyzer.py
│   │   │   ├── performance_analyzer.py
│   │   │   └── risk_analyzer.py
│   │   └── engines/
│   │       ├── __init__.py
│   │       ├── base_engine.py
│   │       ├── backtest_engine.py
│   │       ├── optimize_engine.py
│   │       └── live_engine.py
│   ├── interface/
│   │   ├── __init__.py
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── base_data.py
│   │   │   ├── pandas_data.py
│   │   │   ├── csv_data.py
│   │   │   └── realtime_data.py
│   │   ├── store/
│   │   │   ├── __init__.py
│   │   │   ├── base_store.py
│   │   │   ├── tiger_store.py
│   │   │   └── ib_store.py
│   │   └── broker/
│   │       ├── __init__.py
│   │       ├── base_broker.py
│   │       ├── backtest_broker.py
│   │       ├── tiger/
│   │       │   ├── __init__.py
│   │       │   ├── tiger_broker.py
│   │       │   ├── tiger_client.py
│   │       │   ├── tiger_config.py
│   │       │   ├── tiger_contract.py
│   │       │   ├── tiger_data.py
│   │       │   ├── tiger_data_fetcher.py
│   │       │   ├── tiger_market.py
│   │       │   ├── tiger_order.py
│   │       │   └── examples/
│   │       │       ├── __init__.py
│   │       │       ├── push_client_demo.py
│   │       │       ├── quote_client_demo.py
│   │       │       ├── trade_client_demo.py
│   │       │       ├── financial_demo.py
│   │       │       ├── nasdaq100.py
│   │       │       └── backtrader_tiger_live_trading_demo.py
│   │       └── ib/
│   │           ├── __init__.py
│   │           ├── ib_broker.py
│   │           ├── client.py
│   │           ├── client_config.py
│   │           ├── config.py
│   │           ├── contract.py
│   │           ├── data.py
│   │           ├── market.py
│   │           └── order.py
│   └── infrastructure/
│       ├── __init__.py
│       ├── config/
│       │   ├── __init__.py
│       │   ├── base_config.py
│       │   ├── strategy_config.py
│       │   └── data_config.py
│       ├── constants/
│       │   ├── __init__.py
│       │   └── const.py
│       ├── logging/
│       │   ├── __init__.py
│       │   └── logger.py
│       └── event/
│           ├── __init__.py
│           └── event_manager.py
├── configs/
│   ├── data/
│   │       ib_config.yaml
│   ├── strategy/
│   │       backtest.yaml
│   │       common.yaml
│   │       live.yaml
│   │       magic_nine.yaml
│   │       optimization.yaml
│   │       symbol_params.json
│   └── tiger/
│           private_key.pem
│           tiger_openapi_config.properties
├── research/
│   ├── data/
│   │   ├── raw/
│   │   └── processed/
│   ├── notebooks/
│   │   ├── strategy_development/
│   │   └── backtest_analysis/
│   └── reports/
│       ├── strategy/
│       └── backtest/
├── logs/
│   ├── backtest/
│   └── live/
├── outputs/
│   ├── backtest/
│   │   ├── results/
│   │   └── charts/
│   └── live/
│       ├── trades/
│       └── positions/
└── tests/
    ├── __init__.py
    ├── unit/
    │   ├── __init__.py
    │   ├── test_strategy.py
    │   ├── test_indicators.py
    │   └── test_analyzers.py
    └── integration/
        ├── __init__.py
        ├── test_backtest.py
        └── test_live.py
```

## 目录结构说明

### 1. 配置文件目录 (configs/)

- **strategy/**: 策略配置
    - magic_nine.yaml: 策略配置文件
    - risk_control.yaml: 风险控制配置文件
- **data/**: 数据源配置
    - tiger_config.yaml: 老虎证券配置文件
    - ib_config.yaml: Interactive Brokers配置文件

### 2. 源代码目录 (src/)

- **application/**: 应用程序模块
    - main.py: 主程序入口
    - scripts/: 脚本模块
- **business/**: 业务模块
    - strategy/: 策略模块
    - indicators/: 技术指标模块
    - analyzers/: 分析器模块
    - engines/: 引擎模块
- **interface/**: 接口模块
    - data/: 数据接口
- **infrastructure/**: 基础设施模块
    - config/: 配置管理
    - constants/: 常量定义
    - logging/: 日志管理
    - event/: 事件管理

### 3. 研究目录 (research/)

- **data/**: 研究数据
- **notebooks/**: 研究笔记
- **reports/**: 研究报告

### 4. 日志目录 (logs/)

- **backtest/**: 回测日志
- **live/**: 实盘日志

### 5. 输出目录 (outputs/)

- **backtest/**: 回测结果
- **live/**: 实盘结果

### 6. 测试目录 (tests/)

- 单元测试和集成测试文件

## 分层架构

```mermaid
graph TD
%% 应用层
    subgraph 应用层
        A1[Main]
        A2[ScriptManager]
        A3[ScriptFactory]
        A4[BacktestScript]
        A5[OptimizeScript]
        A6[TradeScript]
    end

%% 业务层
    subgraph 业务层
        B1[MagicNineStrategy]
        B2[SignalGenerator]
        B3[PositionSizer]
        B4[RiskManager]
        B5[MagicNineIndicator]
        B6[PerformanceAnalyzer]
        B7[BacktestEngine]
        B8[OptimizeEngine]
        B9[LiveEngine]
    end

%% 接口层
    subgraph 接口层
        C1[DataStoreBase]
        C2[TigerStore]
        C3[IBStore]
        C4[BTBroker]
        C5[TigerBroker]
        C6[IBBroker]
    end

%% 基础设施层
    subgraph 基础设施层
        D1[Config]
        D2[Logger]
        D3[EventManager]
        D4[EventHandler]
        D5[TradeEventHandler]
        D6[RiskEventHandler]
        D7[DataEventHandler]
        D8[Const]
    end

%% 依赖关系
    应用层 --> 业务层
    业务层 --> 接口层
    接口层 --> 基础设施层
%% 应用层内部关系
    A1 --> A2
    A2 --> A3
    A3 --> A4
    A3 --> A5
    A3 --> A6
%% 业务层内部关系
    B1 --> B2
    B1 --> B3
    B1 --> B4
    B1 --> B5
    B1 --> B6
    B7 --> B1
    B8 --> B1
    B9 --> B1
%% 接口层内部关系
    C1 --> C2
    C1 --> C3
    C4 --> C5
    C4 --> C6
%% 基础设施层内部关系
    D3 --> D4
    D4 --> D5
    D4 --> D6
    D4 --> D7
    D1 --> D3
    D2 --> D3
```

## 分层说明

### 1. 应用层

- **主程序入口**：负责程序的启动和整体流程控制
- **脚本管理**：提供各种运行脚本，如回测、优化、实盘等

### 2. 业务层

- **策略模块**：提供策略开发的基础框架
- **技术指标**：提供技术指标计算功能
- **分析器**：提供策略分析功能
- **引擎**：提供策略回测、优化和实盘交易功能

### 3. 接口层

- **券商接口**：对接不同券商的交易接口
- **数据接口**：提供市场数据获取功能

### 4. 基础设施层

- **配置管理**：管理所有配置信息
- **常量定义**：定义系统中使用的各种常量和枚举
- **日志系统**：提供日志记录功能
- **事件系统**：提供事件管理功能
- **测试系统**：提供测试支持
- **研究模块**：提供研究支持

### 依赖关系说明

1. 上层模块可以依赖下层模块，但下层模块不能依赖上层模块
2. 同层模块之间可以有依赖关系，但应尽量减少
3. 依赖关系应该是单向的，避免循环依赖
4. 基础设施层为所有上层模块提供基础服务

## 关键流程时序图

### 1. 回测流程

```mermaid
sequenceDiagram
    participant Main
    participant ScriptManager
    participant BacktestScript
    participant BacktestEngine
    participant Strategy
    participant SignalGenerator
    participant PositionSizer
    participant RiskManager
    participant MagicNine
    participant Analyzer
    participant PandasData
    participant DataStoreBase
    participant TigerStore
    participant TigerClient
    participant Logger
    participant EventManager
    participant Config
    Main ->> ScriptManager: 创建回测脚本
    ScriptManager ->> BacktestScript: 初始化回测脚本
    BacktestScript ->> Config: 加载回测配置
    BacktestScript ->> BacktestEngine: 创建回测引擎
    BacktestScript ->> Strategy: 注册策略类
    Note over Strategy: BacktestEngine通过\ncerebro.addstrategy()\n实际创建策略实例
    BacktestEngine ->> Strategy: 添加策略
    BacktestScript ->> PandasData: 创建数据源
    PandasData ->> DataStoreBase: 请求历史数据
    DataStoreBase ->> TigerStore: 获取数据
    TigerStore ->> TigerClient: 请求历史数据
    TigerClient -->> TigerStore: 返回数据
    TigerStore -->> DataStoreBase: 返回数据
    DataStoreBase -->> PandasData: 返回数据
    BacktestEngine ->> PandasData: 添加数据源
    BacktestScript ->> Analyzer: 添加分析器
    BacktestEngine ->> Analyzer: 注册分析器
    BacktestEngine ->> EventManager: 注册事件监听
    BacktestEngine ->> Logger: 开始回测
    Note over BacktestEngine, Strategy: 回测引擎通过cerebro.run()执行回测
    BacktestEngine ->> Strategy: 初始化策略
    Strategy ->> SignalGenerator: 初始化信号生成器
    Strategy ->> PositionSizer: 初始化仓位管理器
    Strategy ->> RiskManager: 初始化风险管理器
    Strategy ->> MagicNine: 初始化神奇九转指标
    Note over Strategy: 初始化内置指标\n(RSI, EMA等)

    loop 每个交易日
        PandasData ->> Strategy: next()
        Strategy ->> MagicNine: 计算神奇九转指标
        MagicNine -->> Strategy: 返回指标值
        Note over Strategy: 内置指标自动计算\n(RSI, EMA等)
        Strategy ->> SignalGenerator: 生成交易信号
        SignalGenerator -->> Strategy: 返回信号
        Strategy ->> RiskManager: 检查风险限制
        RiskManager -->> Strategy: 返回风险评估
        Strategy ->> PositionSizer: 计算目标仓位
        PositionSizer -->> Strategy: 返回仓位大小
        Strategy ->> BacktestEngine: 发出交易指令
        BacktestEngine ->> EventManager: 触发交易事件
        EventManager ->> Logger: 记录交易日志
        Strategy ->> Analyzer: 更新分析数据
    end

    BacktestEngine ->> Analyzer: 分析回测结果
    Analyzer -->> BacktestScript: 返回分析报告
    BacktestScript ->> Logger: 记录回测报告
    BacktestScript -->> ScriptManager: 返回回测结果
    ScriptManager -->> Main: 展示回测结果
```

### 2. 参数优化流程

```mermaid
sequenceDiagram
    participant Main
    participant ScriptManager
    participant OptimizeScript
    participant OptimizeEngine
    participant ParamSearchStrategy
    participant Strategy
    participant SignalGenerator
    participant PositionSizer
    participant RiskManager
    participant MagicNineIndicator
    participant BtIndicators
    participant Analyzer
    participant ResultVisualizer
    participant PandasData
    participant DataStoreBase
    participant TigerStore
    participant ParamStore
    participant Logger
    participant EventManager
    participant Config
    Main ->> ScriptManager: 创建优化脚本
    ScriptManager ->> OptimizeScript: 初始化优化脚本
    OptimizeScript ->> Config: 加载优化配置
%% 参数搜索策略选择
    OptimizeScript ->> ParamSearchStrategy: 选择参数搜索策略
    Note over ParamSearchStrategy: 多种搜索策略选择:<br/>1. 网格搜索 (Grid Search)<br/>2. 随机搜索 (Random Search)<br/>3. 贝叶斯优化 (Bayesian Optimization)<br/>4. 遗传算法 (Genetic Algorithm)
    ParamSearchStrategy ->> OptimizeScript: 返回搜索策略
%% 参数空间定义
    OptimizeScript ->> ParamSearchStrategy: 设定参数空间
    Note over ParamSearchStrategy: 定义参数搜索范围:<br/>- 神奇九转参数<br/>- RSI参数<br/>- EMA参数<br/>- MACD参数<br/>- KDJ参数<br/>- 止损参数<br/>- 仓位参数
    OptimizeScript ->> OptimizeEngine: 创建优化引擎
    OptimizeScript ->> Analyzer: 设置评估指标
    Note over Analyzer: 多目标优化指标:<br/>1. 收益率 (Return)<br/>2. 夏普比率 (Sharpe)<br/>3. 最大回撤 (Drawdown)<br/>4. 胜率 (Win Rate)<br/>5. 盈亏比 (Profit/Loss Ratio)
    OptimizeScript ->> PandasData: 创建数据源
    PandasData ->> DataStoreBase: 请求历史数据
    DataStoreBase ->> TigerStore: 获取数据
    TigerStore -->> DataStoreBase: 返回数据
    DataStoreBase -->> PandasData: 返回数据
    OptimizeEngine ->> PandasData: 添加数据源
    OptimizeEngine ->> Strategy: 添加策略类
    OptimizeEngine ->> Analyzer: 注册分析器
    OptimizeEngine ->> EventManager: 注册事件监听
    OptimizeEngine ->> Logger: 开始优化流程
%% 参数优化主循环
    loop 参数搜索迭代
        ParamSearchStrategy ->> OptimizeEngine: 生成参数组合
        OptimizeEngine ->> Strategy: 创建策略实例
        Strategy ->> SignalGenerator: 配置信号参数
        Strategy ->> PositionSizer: 配置仓位参数
        Strategy ->> RiskManager: 配置风险参数
        Strategy ->> MagicNineIndicator: 配置神奇九转指标参数
        Strategy ->> BtIndicators: 配置技术指标参数
    %% 回测特定参数组合
        loop 每个交易日
            PandasData ->> Strategy: next()
            Strategy ->> MagicNineIndicator: 计算神奇九转指标
            MagicNineIndicator -->> Strategy: 返回指标值
            Strategy ->> BtIndicators: 计算技术指标
            BtIndicators -->> Strategy: 返回指标值
            Strategy ->> SignalGenerator: 生成交易信号
            SignalGenerator -->> Strategy: 返回信号
            Strategy ->> RiskManager: 检查风险限制
            RiskManager -->> Strategy: 返回风险评估
            Strategy ->> PositionSizer: 计算目标仓位
            PositionSizer -->> Strategy: 返回仓位大小
            Strategy ->> OptimizeEngine: 提交订单
            OptimizeEngine -->> Strategy: 返回订单状态
            Strategy ->> Analyzer: 更新分析数据
        end

    %% 性能评估与记录
        OptimizeEngine ->> Analyzer: 分析当前参数结果
        Analyzer -->> OptimizeEngine: 返回性能指标
        OptimizeEngine ->> Logger: 记录参数组合性能
        OptimizeEngine ->> ParamSearchStrategy: 提供结果反馈

        alt 自适应参数搜索
            ParamSearchStrategy ->> ParamSearchStrategy: 根据性能调整搜索方向
            Note over ParamSearchStrategy: 贝叶斯优化或遗传算法<br/>会根据历史结果调整搜索
        end
    end

%% 结果处理与可视化
    OptimizeEngine ->> Analyzer: 汇总所有参数组合结果
    Analyzer ->> OptimizeEngine: 返回优化统计数据
    OptimizeEngine ->> ParamSearchStrategy: 请求最优参数组合
    ParamSearchStrategy ->> OptimizeEngine: 返回最优参数集
    OptimizeEngine ->> ResultVisualizer: 生成优化结果可视化
    Note over ResultVisualizer: 创建多种可视化:<br/>1. 参数敏感度分析<br/>2. 参数热力图<br/>3. 性能分布图<br/>4. Pareto最优前沿
    OptimizeEngine ->> ParamStore: 保存最优参数集
    OptimizeEngine ->> OptimizeScript: 返回优化结果
    OptimizeScript ->> Config: 更新策略配置文件
    OptimizeScript ->> Logger: 生成优化报告
    OptimizeScript -->> ScriptManager: 返回优化结果及报告
    ScriptManager -->> Main: 展示优化结果

    alt 验证最优参数
        Main ->> ScriptManager: 使用最优参数运行回测
        Note over ScriptManager: 验证优化效果<br/>并进行跨周期验证
    end
```

### 3. 实盘交易流程

```mermaid
sequenceDiagram
    participant Main
    participant ScriptManager
    participant TradeScript
    participant LiveEngine
    participant Strategy
    participant SignalGenerator
    participant PositionSizer
    participant RiskManager
    participant MagicNineIndicator
    participant BtIndicators
    participant Analyzer
    participant TigerRealtimeData
    participant TigerStore
    participant TigerClient
    participant Logger
    participant EventManager
    participant Config
    Main ->> ScriptManager: 创建交易脚本
    ScriptManager ->> TradeScript: 初始化交易脚本
    TradeScript ->> Config: 加载交易配置
    TradeScript ->> LiveEngine: 创建交易引擎
    TradeScript ->> Strategy: 初始化策略
    Strategy ->> SignalGenerator: 配置信号生成器
    Strategy ->> PositionSizer: 配置仓位管理器
    Strategy ->> RiskManager: 配置风险管理器
    Strategy ->> MagicNineIndicator: 配置连续K线指标
    Strategy ->> BtIndicators: 配置技术指标(SMA,RSI等)
    LiveEngine ->> Strategy: 添加策略
    TradeScript ->> TigerStore: 连接Tiger服务器
    TigerStore ->> TigerClient: 初始化连接
    TigerClient -->> TigerStore: 返回连接状态
    TigerStore -->> TradeScript: 返回连接状态
    TradeScript ->> TigerRealtimeData: 创建实时数据源
    TigerRealtimeData ->> TigerStore: 订阅实时数据
    TigerStore ->> TigerClient: 订阅数据
    TigerClient -->> TigerStore: 确认订阅
    TigerStore -->> TigerRealtimeData: 确认订阅
    LiveEngine ->> TigerRealtimeData: 添加数据源
    TradeScript ->> TigerStore: 创建交易接口
    TigerStore ->> TigerClient: 初始化交易
    TigerClient -->> TigerStore: 返回账户信息
    TigerStore -->> TradeScript: 返回账户信息
    LiveEngine ->> TigerStore: 设置交易接口
    TradeScript ->> Analyzer: 添加分析器
    LiveEngine ->> Analyzer: 注册分析器
    LiveEngine ->> EventManager: 注册事件监听
    LiveEngine ->> Logger: 开始交易

    loop 实时交易循环
        TigerClient ->> TigerStore: 推送实时数据
        TigerStore ->> TigerRealtimeData: 推送数据
        TigerRealtimeData ->> Strategy: next()
        Strategy ->> MagicNineIndicator: 计算连续K线指标
        MagicNineIndicator -->> Strategy: 返回指标值
        Strategy ->> BtIndicators: 计算技术指标
        BtIndicators -->> Strategy: 返回指标值
        Strategy ->> SignalGenerator: 生成交易信号
        SignalGenerator -->> Strategy: 返回信号
        Strategy ->> RiskManager: 检查风险限制
        RiskManager -->> Strategy: 返回风险评估
        Strategy ->> PositionSizer: 计算目标仓位
        PositionSizer -->> Strategy: 返回仓位大小

        alt 需要交易
            Strategy ->> TigerStore: 提交订单
            TigerStore ->> TigerClient: 发送订单请求
            TigerClient -->> TigerStore: 返回订单状态
            TigerStore -->> Strategy: 更新订单状态
            Strategy ->> Analyzer: 更新分析数据
            EventManager ->> Logger: 记录交易日志
        end

        opt 定期分析
            LiveEngine ->> Analyzer: 执行分析
            Analyzer -->> LiveEngine: 返回分析结果
            LiveEngine ->> Logger: 记录分析结果
        end

        opt 错误处理
            TigerClient -->> TigerStore: 推送错误信息
            TigerStore ->> EventManager: 触发错误事件
            EventManager ->> Logger: 记录错误信息
            EventManager ->> Strategy: 通知策略
        end
    end

    TradeScript ->> TigerStore: 关闭连接
    TigerStore ->> TigerClient: 断开连接
    TradeScript ->> Logger: 记录交易结果
    TradeScript -->> ScriptManager: 返回执行结果
    ScriptManager -->> Main: 展示交易结果
```

### 4. 数据加载流程

```mermaid
sequenceDiagram
    participant App as Main
    participant Script as BacktestScript
    participant Engine as BacktestEngine
    participant Data as PandasData
    participant Store as DataStoreBase
    participant TigerStore
    participant Client as TigerClient
    participant Cache as CSVData
    participant Strategy as MagicNineStrategy
    App ->> Script: 创建回测脚本
    Script ->> Engine: 创建回测引擎
    Script ->> Data: 创建数据源
    Data ->> Store: 请求历史数据
    Store ->> TigerStore: 获取数据
    Note over TigerStore: 参数：<br/>- symbol: str<br/>- start_date: datetime<br/>- end_date: datetime<br/>- interval: str

    alt 检查本地缓存
        TigerStore ->> Cache: 查询CSV文件
        Cache -->> TigerStore: 返回缓存数据
    else 缓存未命中
        TigerStore ->> Client: 请求历史数据
        Note over Client: 分段获取数据<br/>- 每段最多5天<br/>- 分钟级数据
        Client -->> TigerStore: 返回数据
        TigerStore ->> Cache: 保存为CSV
    end

    TigerStore -->> Store: 返回数据
    Store -->> Data: 返回DataFrame
    Note over Data: 数据格式：<br/>- 时间索引<br/>- OHLCV数据<br/>- UTC时间
    Data ->> Engine: 添加数据源
    Engine ->> Strategy: 初始化策略
    Note over Strategy: 数据验证：<br/>- 完整性检查<br/>- 连续性检查<br/>- 数据点数量检查
```

数据加载流程说明：

1. **初始化阶段**
    - `Main`创建`BacktestScript`实例
    - `BacktestScript`创建`BacktestEngine`和`PandasData`实例
    - `PandasData`通过`TigerStore`请求历史数据

2. **数据获取阶段**
    - `TigerStore`首先检查本地CSV缓存
    - 如果缓存未命中，则通过`TigerClient`从API获取数据
    - 采用分段获取策略，每段最多5天
    - 获取的数据保存为CSV文件

3. **数据处理阶段**
    - `TigerStore`将数据转换为DataFrame格式
    - 数据包含时间索引和OHLCV数据
    - 时间使用UTC格式

4. **数据验证阶段**
    - `MagicNineStrategy`对数据进行验证
    - 检查数据完整性（每个交易日390个数据点）
    - 检查数据连续性（1分钟间隔）
    - 检查数据点数量（允许90%的完整度）

5. **数据使用阶段**
    - 数据加载完成后，`BacktestEngine`将数据源添加到回测引擎
    - `MagicNineStrategy`使用加载的数据进行回测
    - 策略在回测过程中可以访问完整的历史数据

## 流程说明

1. 回测数据加载流程：
    - `PandasData/GenericCSVData` 调用 `DataStoreBase` 的 `get_historical_data` 方法
    - `DataStoreBase` 将请求转发给 `TigerStore`
    - `TigerStore` 首先检查缓存
    - 如果缓存存在，直接返回缓存数据
    - 如果缓存不存在，通过 `TigerClient` 从 API 获取数据
    - 获取到数据后保存到缓存并返回

2. 实盘数据加载流程：
    - `PandasData/GenericCSVData` 调用 `DataStoreBase` 的 `get_realtime_quotes` 方法
    - `DataStoreBase` 将请求转发给 `TigerStore`
    - `TigerStore` 通过 `TigerClient` 订阅实时行情
    - `TigerClient` 从 API 获取实时行情并返回

3. 数据流向：
    - 回测数据流：`PandasData/GenericCSVData -> DataStoreBase -> TigerStore -> TigerClient -> API`
    - 实盘数据流：`PandasData/GenericCSVData -> DataStoreBase -> TigerStore -> TigerClient -> API`
    - 缓存管理：`TigerStore` 负责缓存的管理，包括检查、保存和读取

## 分层架构类图

```mermaid
classDiagram
    %% 接口层
    class DataStoreBase {
        <<abstract>>
        +get_historical_data()
        +get_realtime_quotes()
        +get_account_info()
    }
    
    class TigerStore {
        -config: TigerConfig
        -client: TigerClient
        +get_historical_data()
        +get_realtime_quotes()
        +get_account_info()
    }
    
    class IBStore {
        -config: IBConfig
        -client: IBClient
        +get_historical_data()
        +get_realtime_quotes()
        +get_account_info()
    }
    
    %% 数据源层
    class BTDataBase {
        <<abstract>>
        -_store: DataStoreBase
        +get_data()
    }
    
    class PandasData {
        +get_data()
    }
    
    class GenericCSVData {
        +get_data()
    }
    
    class TigerRealtimeData {
        +get_data()
    }
    
    %% 关系
    DataStoreBase <|-- TigerStore
    DataStoreBase <|-- IBStore
    BTDataBase <|-- PandasData
    BTDataBase <|-- GenericCSVData
    BTDataBase <|-- TigerRealtimeData
    BTDataBase --> DataStoreBase
    TigerStore --> TigerClient
    IBStore --> IBClient
```

## 类关系说明

1. 数据存储层：
    - `DataStoreBase` 是数据存储的抽象基类，位于 `src/interface/store/` 目录
    - 定义了数据存储的接口规范
    - `TigerStore` 和 `IBStore` 继承自 `DataStoreBase`，实现具体的数据存储逻辑

2. 数据源层：
    - `BTDataBase` 是数据源的抽象基类
    - 包含 `_store` 属性，用于访问数据存储
    - `PandasData`、`GenericCSVData` 和 `TigerRealtimeData` 继承自 `BTDataBase`

3. 数据流向：
    - 回测数据流：`PandasData/GenericCSVData -> DataStoreBase -> TigerStore -> TigerClient -> API`
    - 实盘数据流：`PandasData/GenericCSVData -> DataStoreBase -> TigerStore -> TigerClient -> API`
    - 经纪商数据流：`TigerBroker -> TigerStore -> TigerClient -> API` 和 `IBBroker -> IBStore -> IBClient -> API`