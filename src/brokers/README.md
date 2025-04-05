## 接入老虎证券实盘交易
- 参考tigeropen/examples/push_client_demo.py 订阅数据
- 参考tigeropen/examples/trade_client_demo.py 获取账户等各类交易信息
- 参考tigeropen/examples/quote_client_demo.py 进行实盘交易等操作
- 使用模拟账户接入
- 使用现有策略交易期权
  - 思想：使用期权撬动杠杆，抵消交易费用
  - 找到最合适的期权
  - 做期权交易

- 初始化是主动获取必要啊数据，后面的实时数据都采用订阅的方式获取，禁止使用轮询，避免频繁调用老虎证券api触发限制。
- 订阅数据，获取实时的1分钟k线数据，注意数据采集频率
- 使用当前策略产生交易信号
- 做实盘的期权交易
- 注意，每次神奇九转的信号，应该只有一个，而不是频繁触发。
- 使用市价单交易，确保交易成功
- 框架：backtrader:1.9.78.123,代码仓：https://github.com/mementum/backtrader# ，使用backtrader官方推荐的最佳实践的方式实现实盘交易
- 老虎证券，api：tigeropen3.3.3，官方demo代码仓：https://github.com/tigerfintech/openapi-python-sdk
- 使用test_tiger_broker_api.py测试一下接口