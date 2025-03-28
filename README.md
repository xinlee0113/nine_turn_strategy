# 神奇九转量化交易策略

基于backtrader框架实现的神奇九转量化交易策略，连接老虎证券API进行数据获取和回测。

## 策略原理

神奇九转策略源自汤姆·狄马克(Tom DeMark)的TD序列理论，是一种短线择时工具。其核心思想是：

- 通过比较当前价格与前几个周期价格确定趋势方向
- 当连续多次出现同方向比较结果时，市场可能出现反转
- 结合RSI、KDJ、MACD等指标增强信号可靠性

## 项目结构

```
.
├── config/                     # 配置文件目录
│   ├── tiger_openapi_config.properties  # 老虎证券API配置
│   └── private_key.pem         # API私钥
├── data/                       # 数据目录
│   └── cache/                  # 缓存目录
├── logs/                       # 日志目录
├── src/                        # 源代码
│   ├── data_fetcher.py         # 数据获取模块
│   ├── indicators/             # 技术指标目录
│   │   ├── __init__.py         # 指标包初始化文件
│   │   ├── magic_nine.py       # 神奇九转指标
│   │   ├── rsi_bundle.py       # RSI组合指标
│   │   └── kdj_bundle.py       # KDJ组合指标
│   ├── magic_nine_strategy.py  # 策略实现
│   ├── multi_asset_strategy.py # 多资产独立交易策略
│   ├── visualization.py        # 可视化模块
│   └── utils.py                # 工具类
├── main.py                     # 主程序
├── requirements.txt            # 依赖项
└── README.md                   # 项目说明
```

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

1. 配置老虎证券API

   将`tiger_openapi_config.properties`和`private_key.pem`放入`config`目录。

2. 运行策略

   **原始策略** (单一资金池):
   ```bash
   python main.py --symbols QQQ SPY --days 30 --use-cache
   ```

   **多资产独立交易策略** (每个标的独立资金池):
   ```bash
   python main.py --symbols QQQ SPY AAPL MSFT AMZN GOOGL META NVDA TSLA --days 30 --use-cache --multi-asset
   ```

   **自定义资产权重配置**:
   ```bash
   python main.py --symbols QQQ SPY AAPL --days 30 --use-cache --multi-asset --weights '{"QQQ": 0.5, "SPY": 0.3, "AAPL": 0.2}'
   ```

3. 参数说明

   - `--symbols`: 要交易的股票代码列表，默认 QQQ SPY
   - `--days`: 回测天数，默认 30
   - `--cash`: 初始资金，默认 100000
   - `--commission`: 佣金率，默认 0.0（不计费用）
   - `--config`: 配置文件路径，默认 config
   - `--key`: 私钥文件路径，默认 config/private_key.pem
   - `--use-cache`: 使用缓存数据，不需要每次都从API获取
   - `--magic-period`: 神奇九转比较周期，默认 2
   - `--multi-asset`: 使用多资产独立交易策略（每个标的独立资金池）
   - `--weights`: 资产权重配置，JSON格式，例如: '{"QQQ": 0.6, "SPY": 0.4}'

## 策略参数

- 神奇九转比较周期: 2（可通过参数调整）
- 神奇九转信号触发计数: 5（可修改代码调整）
- RSI超买超卖: 70/30
- KDJ超买超卖: 80/20
- MACD信号: 0

## 两种策略对比

1. **原始策略** (magic_nine_strategy.py)
   - 所有标的共享一个资金池
   - 一次只交易一个标的
   - 资金集中，可能导致单个标的交易占据所有资金
   - 适合当标的之间有高度相关性时

2. **多资产独立交易策略** (multi_asset_strategy.py)
   - 为每个标的分配独立的资金池
   - 各标的独立生成信号和执行交易
   - 实现真正的多标的并行交易
   - 可自定义各标的的资金权重
   - 更好的风险分散效果

## 性能表现

使用以下参数进行5天回测的结果：

```
python main.py --days 5 --use-cache --magic-period 2
```

- 总交易次数: 18
- 平均每天交易次数: 3.6
- 胜率: 66.67%
- 总收益率: 0.66% 