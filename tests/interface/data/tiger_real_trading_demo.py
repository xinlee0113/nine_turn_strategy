# 配置日志
import logging
import os

import backtrader as bt
from tigeropen.common.consts import Currency, SecurityType, Language
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.push.push_client import PushClient
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.trade.trade_client import TradeClient

from src.interface.data.tiger_real_time_data import TigerRealtimeData

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def _get_config_paths() -> tuple[str, str]:
    # 获取项目根目录的绝对路径
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    config_path = os.path.join(base_dir, "configs", "tiger", "tiger_openapi_config.properties")
    private_key_path = os.path.join(base_dir, "configs", "tiger", "private_key.pem")
    return config_path, private_key_path


class TigerTradeStrategy(bt.Strategy):
    """基于移动平均线的交易策略"""

    params = (
        ('sma_period', 20),
    )

    def __init__(self, trade_client, account):
        self.trade_client = trade_client
        self.account = account
        self.sma = bt.indicators.SMA(self.data.close, period=self.p.sma_period)
        self.order = None

    def next(self):
        """策略主逻辑，每个数据点都会执行一次"""
        print(f"当前价格: {self.data.close[0]:.2f}")
        # 没有持仓且收盘价上穿SMA
        # if not self.position and self.data.close[0] > self.sma[0]:
        #     # 买入信号
        #     self.order = self.buy()
        #     logging.info(f"买入信号触发: 价格={self.data.close[0]:.2f}")
        #
        #     # 同时在老虎证券执行交易
        #     self._execute_tiger_order('BUY')
        #
        # # 有持仓且收盘价下穿SMA
        # elif self.position and self.data.close[0] < self.sma[0]:
        #     # 卖出信号
        #     self.order = self.sell()
        #     logging.info(f"卖出信号触发: 价格={self.data.close[0]:.2f}")
        #
        #     # 同时在老虎证券执行交易
        #     self._execute_tiger_order('SELL')

    def _execute_tiger_order(self, action, quantity=10):
        """在老虎证券执行交易"""
        try:
            contract = self.data._contract

            # 创建订单
            order = self.trade_client.create_order(
                self.account, contract,
                action=action,
                order_type='MKT',
                quantity=quantity
            )

            # 预览订单
            result = self.trade_client.preview_order(order)
            logging.info(f"订单预览结果: {result}")

            # 下单
            self.trade_client.place_order(order)
            logging.info(f"成功提交{action}订单")

        except Exception as e:
            logging.error(f"执行{action}订单出错: {e}")


def main():
    """主函数"""
    config_path, private_key_path = _get_config_paths()
    # 初始化Tiger API客户端
    client_config = TigerOpenClientConfig(sandbox_debug=False, props_path=config_path)
    client_config.private_key = read_private_key(private_key_path)
    client_config.language = Language.zh_CN
    client_config.timeout = 60

    protocol, host, port = client_config.socket_host_port
    push_client = PushClient(host, port, use_ssl=(protocol == 'ssl'))

    # 创建客户端
    trade_client = TradeClient(client_config)
    quote_client = QuoteClient(client_config)
    quote_client.grab_quote_permission()

    # 创建合约管理器
    contract_manager = ContractManager(trade_client)

    # 创建cerebro引擎
    cerebro = bt.Cerebro()

    # 添加实时数据源
    data = TigerRealtimeData(
        trade_client=trade_client,
        quote_client=quote_client,
        contract_manager=contract_manager
    )
    cerebro.adddata(data)

    # 添加策略
    cerebro.addstrategy(
        TigerTradeStrategy,
        trade_client=trade_client,
        account=client_config.account
    )

    # 设置初始资金 #todo 要获取账号的当前的真实资金
    cerebro.broker.setcash(100000.0)

    # 设置佣金  #todo 要设置吗？真实交易费用订单信息里面有真实的的佣金信息
    cerebro.broker.setcommission(commission=0.001)

    # 运行策略
    logging.info(f"初始资金: {cerebro.broker.getvalue():.2f}")
    cerebro.run()
    logging.info(f"最终资金: {cerebro.broker.getvalue():.2f}")

    # 绘制结果
    # cerebro.plot()


# 合约管理器类
class ContractManager:
    """合约管理器，负责获取和管理合约信息"""

    def __init__(self, trade_client):
        self.trade_client = trade_client
        self.contract_cache = {}

    def get_contract(self, symbol, currency=Currency.USD, sec_type=SecurityType.STK):
        """获取合约信息"""
        cache_key = f"{symbol}_{currency}_{sec_type}"

        # 检查缓存
        if cache_key in self.contract_cache:
            return self.contract_cache[cache_key]

        # 获取合约
        try:
            contracts = self.trade_client.get_contracts(
                symbol=symbol,
                currency=currency,
                sec_type=sec_type
            )

            if contracts:
                # 缓存并返回
                self.contract_cache[cache_key] = contracts[0]
                return contracts[0]
            else:
                logging.error(f"未找到合约: {symbol}")
                return None

        except Exception as e:
            logging.error(f"获取合约信息出错: {e}")
            return None


if __name__ == "__main__":
    main()
