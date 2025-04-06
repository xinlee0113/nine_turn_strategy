import logging
import time
from datetime import datetime
from typing import Optional, Any, Tuple

import backtrader as bt
from tigeropen.common.consts import Market, SecurityType, Language, Currency
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.quote.domain.market_status import MarketStatus
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.trade.trade_client import TradeClient

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ConfigManager:
    """配置管理类，负责管理Tiger API配置"""

    @staticmethod
    def create_default_config(config_path: str = '../../config',
                              private_key_path: str = '../../config/private_key.pem') -> TigerOpenClientConfig:
        """创建默认的Tiger API配置"""
        client_config = TigerOpenClientConfig(sandbox_debug=False, props_path=config_path)
        client_config.private_key = read_private_key(private_key_path)
        client_config.language = Language.zh_CN
        client_config.timeout = 60
        return client_config


class ClientFactory:
    """客户端工厂类，负责创建交易和行情客户端"""

    @staticmethod
    def create_clients(config: TigerOpenClientConfig) -> Tuple[TradeClient, QuoteClient]:
        """创建交易和行情客户端"""
        trade_client = TradeClient(config)
        quote_client = QuoteClient(config)
        return trade_client, quote_client


class MarketStatus:
    """市场状态类，封装市场状态相关逻辑"""

    def __init__(self, quote_client: QuoteClient, default_market: Market = Market.US):
        """初始化市场状态类"""
        self.quote_client = quote_client
        self.default_market = default_market
        self.cached_status = None
        self.cached_status_time = 0
        self.status_cache_validity = 300  # 缓存有效期（秒）

    def is_market_open(self, market: Optional[Market] = None) -> bool:
        """检查市场是否开盘"""
        market = market or self.default_market

        # 检查缓存是否有效
        current_time = time.time()
        if (current_time - self.cached_status_time < self.status_cache_validity and
                self.cached_status is not None):
            return self.cached_status

        try:
            market_status = self.quote_client.get_market_status(market)[0]
            is_open = market_status.trading_status != 'MARKET_CLOSED'

            # 更新缓存
            self.cached_status = is_open
            self.cached_status_time = current_time

            logging.info(f'市场状态检查: {market_status}，是否开盘: {is_open}')
            return is_open
        except Exception as e:
            logging.error(f"检查市场状态时出错: {e}")
            return False  # 出错时保守处理，假设市场关闭

    def get_next_open_time(self, market: Optional[Market] = None) -> Optional[datetime]:
        """获取市场下次开盘时间"""
        market = market or self.default_market
        try:
            market_status = self.quote_client.get_market_status(market)[0]
            return market_status.open_time
        except Exception as e:
            logging.error(f"获取下次开盘时间出错: {e}")
            return None

    def wait_for_market_open(self, market: Optional[Market] = None) -> bool:
        """等待市场开盘"""
        market = market or self.default_market

        # 如果市场已开盘，直接返回
        if self.is_market_open(market):
            logging.info("市场已开盘，可以交易")
            return True

        # 获取下次开盘时间
        next_open_time = self.get_next_open_time(market)
        if not next_open_time:
            logging.warning("无法获取下次开盘时间，将休眠5分钟后重试")
            time.sleep(300)  # 休眠5分钟
            return False

        # 计算等待时间
        now = datetime.now(next_open_time.tzinfo)
        wait_seconds = (next_open_time - now).total_seconds()

        if wait_seconds <= 0:
            logging.warning(f"市场状态信息异常：下次开盘时间早于当前时间，将继续尝试获取实时数据")
            return True

        # 根据等待时间长短决定等待策略
        return self._wait_strategy(wait_seconds, next_open_time)

    def _wait_strategy(self, wait_seconds: float, next_open_time: datetime) -> bool:
        """根据等待时间长短选择不同的等待策略"""
        # 超过一天的等待
        if wait_seconds > 86400:  # 24小时 = 86400秒
            days = wait_seconds // 86400
            hours = (wait_seconds % 86400) // 3600
            minutes = (wait_seconds % 3600) // 60
            logging.info(f"市场休市中，下次开盘时间: {next_open_time}，需等待: {days:.0f}天{hours:.0f}小时{minutes:.0f}分钟")

            # 等待时间太长，休眠一小时后重新检查
            if wait_seconds > 7200:  # 超过2小时
                logging.info("等待时间较长，系统将休眠1小时后重新检查市场状态")
                time.sleep(3600)  # 休眠1小时
                return False
        else:
            # 不到一天的等待
            hours = wait_seconds // 3600
            minutes = (wait_seconds % 3600) // 60
            seconds = wait_seconds % 60
            logging.info(f"市场休市中，下次开盘时间: {next_open_time}，需等待: {hours:.0f}小时{minutes:.0f}分钟{seconds:.0f}秒")

            # 30分钟内开盘，直接等待到开盘
            if wait_seconds <= 1800:  # 30分钟 = 1800秒
                logging.info(f"距离开盘时间不足30分钟，系统将等待至开盘...")
                time.sleep(wait_seconds)
                logging.info("等待结束，市场即将开盘")
                return True
            else:
                # 等待时间较长，休眠一段时间后重新检查
                sleep_time = min(wait_seconds / 2, 3600)  # 休眠一半时间或最多1小时
                logging.info(f"距离开盘时间较长，系统将休眠{sleep_time:.0f}秒后重新检查")
                time.sleep(sleep_time)
                return False


class ContractManager:
    """合约管理类，负责获取和管理合约信息"""

    def __init__(self, trade_client: TradeClient):
        """初始化合约管理类"""
        self.trade_client = trade_client
        self.contract_cache = {}  # 缓存已获取的合约信息

    def get_contract(self, symbol: str, currency: Currency = Currency.USD,
                     sec_type: SecurityType = SecurityType.STK) -> Any:
        """获取合约信息，优先从缓存获取"""
        cache_key = f"{symbol}_{currency}_{sec_type}"
        if cache_key in self.contract_cache:
            return self.contract_cache[cache_key]

        try:
            contracts = self.trade_client.get_contracts(
                symbol=symbol, currency=currency, sec_type=sec_type)
            if contracts:
                self.contract_cache[cache_key] = contracts[0]
                return contracts[0]
            else:
                logging.error(f"未找到合约: {symbol}")
                return None
        except Exception as e:
            logging.error(f"获取合约信息时出错: {e}")
            return None


class OrderExecutor:
    """订单执行器，负责下单和管理订单"""

    def __init__(self, trade_client: TradeClient, account: str):
        """初始化订单执行器"""
        self.trade_client = trade_client
        self.account = account

    def place_order(self, contract: Any, action: str, order_type: str = 'MKT',
                    quantity: int = 10) -> bool:
        """下单"""
        try:
            # 创建订单
            order = self.trade_client.create_order(
                self.account, contract, action=action,
                order_type=order_type, quantity=quantity
            )

            # 预览订单
            result = self.trade_client.preview_order(order)
            logging.info(f"订单预览结果: {result}")

            # 下单
            self.trade_client.place_order(order)
            logging.info(f"成功下单{action}")
            return True
        except Exception as e:
            logging.error(f"{action}下单失败: {e}")
            return False


class TigerRealtimeData(bt.feeds.DataBase):
    """Tiger实时数据加载器"""

    lines = ('open', 'high', 'low', 'close', 'volume')
    params = (
        ('symbol', 'QQQ'),
        ('market', Market.US),
        ('sec_type', SecurityType.STK),
        ('interval', 30),  # 数据更新间隔，单位：秒
    )

    def __init__(self, trade_client: TradeClient, quote_client: QuoteClient,
                 market_status: MarketStatus, contract_manager: ContractManager):
        """初始化数据加载器"""
        super().__init__()
        self.trade_client = trade_client
        self.quote_client = quote_client
        self.market_status = market_status
        self.contract_manager = contract_manager
        self.last_time = time.time()

        # 获取合约信息
        self.contract = self.contract_manager.get_contract(
            self.p.symbol, Currency.USD, self.p.sec_type)
        logging.info(f'初始化数据源，合约= {self.contract}')

        # 检查市场状态
        self.market_open = self.market_status.is_market_open(self.p.market)
        logging.info(f'市场开盘状态: {"开盘" if self.market_open else "休市"}')

    def start(self):
        """启动数据加载器"""
        super().start()
        logging.info(f'启动数据源，last_time= {self.last_time}')

    def _load(self):
        """加载实时数据"""
        # 首先检查市场是否开盘，如果没开盘则等待
        if not self.market_open:
            self.market_open = self.market_status.wait_for_market_open(self.p.market)
            if not self.market_open:
                return False  # 如果市场仍未开盘，则返回False继续等待

        current_time = time.time()
        # 控制数据获取频率
        if current_time - self.last_time < self.p.interval:
            time.sleep(self.p.interval - (current_time - self.last_time))
            current_time = time.time()

        self.last_time = current_time
        try:
            symbols = [self.contract.symbol]
            quote = self.quote_client.get_stock_briefs(symbols, include_hour_trading=False)

            # 检查返回的数据是否有效
            if quote is None or quote.empty:
                logging.warning(f"获取行情数据失败或数据为空，将在{self.p.interval}秒后重试")
                time.sleep(self.p.interval)
                return False

            logging.info(f'获取行情数据成功，symbols= {symbols}, 最新价格= {quote["close"][0]}')

            # 更新数据线
            self.array[0][0] = float(quote['open'][0])  # open
            self.array[1][0] = float(quote['high'][0])  # high
            self.array[2][0] = float(quote['low'][0])  # low
            self.array[3][0] = float(quote['close'][0])  # close
            self.array[4][0] = float(quote['volume'][0])  # volume

            # 更新时间戳
            dt = datetime.fromtimestamp(current_time)
            # 使用array方式设置datetime
            bt.num2date(bt.date2num(dt))  # 转换时间格式

            # 每10次数据获取检查一次市场状态，避免频繁API调用
            if int(current_time) % 10 == 0:
                self.market_open = self.market_status.is_market_open(self.p.market)
                if not self.market_open:
                    logging.info("检测到市场已关闭，将等待下次开盘")
                    return False

            return True
        except Exception as e:
            logging.error(f"获取实时数据时出错: {e}")
            time.sleep(self.p.interval)  # 发生错误时等待一段时间再重试
            return False


class SMAStrategy(bt.Strategy):
    """基于SMA的策略"""

    params = (
        ('symbol', 'QQQ'),  # 交易的股票代码
        ('sma_period', 10),  # SMA周期
    )

    def __init__(self, order_executor: OrderExecutor, market_status: MarketStatus,
                 contract_manager: ContractManager):
        """初始化策略"""
        self.order_executor = order_executor
        self.market_status = market_status
        self.contract_manager = contract_manager

        # 获取合约信息
        self.contract = self.contract_manager.get_contract(self.p.symbol)

        # 策略状态
        self.sma = None
        self.data_ready = False
        self.last_check_time = 0  # 上次检查市场状态的时间
        self.check_interval = 300  # 每5分钟检查一次市场状态

        logging.info('初始化策略完成')

    def next(self):
        """策略主逻辑，每个数据点都会执行一次"""
        current_time = time.time()

        # 定期检查市场状态
        if current_time - self.last_check_time > self.check_interval:
            self.last_check_time = current_time
            # 使用市场状态控制器检查市场状态
            if not self.market_status.is_market_open():
                logging.info("当前非交易时间，策略暂停执行")
                time.sleep(60)  # 非交易时间，减少检查频率
                return

        # 执行策略逻辑
        self._execute_strategy()

    def _execute_strategy(self):
        """执行策略逻辑"""
        # 检查数据长度是否足够
        if len(self.data) < self.p.sma_period:
            logging.debug(f'数据不足，当前长度: {len(self.data)}，需要至少{self.p.sma_period}个数据点')
            return

        # 初始化SMA指标（仅第一次）
        if not self.data_ready:
            try:
                self.sma = bt.indicators.SMA(self.data.close, period=self.p.sma_period)
                self.data_ready = True
                logging.info('SMA指标初始化成功')
            except Exception as e:
                logging.error(f"初始化SMA指标出错: {e}")
                return

        # 确保SMA指标有足够的数据
        if not self.sma or len(self.sma) == 0:
            logging.debug('SMA指标数据不足')
            return

        # 交易决策
        try:
            current_price = self.data.close[0]
            sma_value = self.sma[0]
            logging.info(f"当前价格: {current_price:.2f}, SMA值: {sma_value:.2f}")

            if current_price > sma_value and not self.position:
                # 买入信号
                self.order_executor.place_order(self.contract, 'BUY')
            elif current_price < sma_value and self.position:
                # 卖出信号
                self.order_executor.place_order(self.contract, 'SELL')
        except Exception as e:
            logging.error(f"执行交易逻辑时出错: {e}")


class TradingEngine:
    """交易引擎，负责协调各组件运行交易系统"""

    def __init__(self, config_path: str = '../../config',
                 private_key_path: str = '../../config/private_key.pem',
                 initial_cash: float = 100000.0):
        """初始化交易引擎"""
        # 创建配置
        self.client_config = ConfigManager.create_default_config(config_path, private_key_path)

        # 创建客户端
        self.trade_client, self.quote_client = ClientFactory.create_clients(self.client_config)

        # 创建各组件
        self.market_status = MarketStatus(self.quote_client)
        self.contract_manager = ContractManager(self.trade_client)
        self.order_executor = OrderExecutor(self.trade_client, self.client_config.account)

        # Cerebro引擎配置
        self.cerebro = bt.Cerebro()
        self.cerebro.broker.setcash(initial_cash)

    def add_data_feed(self, symbol: str = 'QQQ', market: Market = Market.US,
                      sec_type: SecurityType = SecurityType.STK, interval: int = 1):
        """添加数据源"""
        data = TigerRealtimeData(
            trade_client=self.trade_client,
            quote_client=self.quote_client,
            market_status=self.market_status,
            contract_manager=self.contract_manager
        )
        data.p.symbol = symbol
        data.p.market = market
        data.p.sec_type = sec_type
        data.p.interval = interval

        self.cerebro.adddata(data)
        return self

    def add_strategy(self, symbol: str = 'QQQ', sma_period: int = 10):
        """添加策略"""
        self.cerebro.addstrategy(
            SMAStrategy,
            order_executor=self.order_executor,
            market_status=self.market_status,
            contract_manager=self.contract_manager,
            symbol=symbol,
            sma_period=sma_period
        )
        return self

    def run(self):
        """运行交易系统"""
        logging.info(f'初始投资组合价值: {self.cerebro.broker.getvalue():.2f}')
        try:
            self.cerebro.run()
            logging.info(f'最终投资组合价值: {self.cerebro.broker.getvalue():.2f}')
        except KeyboardInterrupt:
            logging.info("用户中断程序，正在退出...")
        except Exception as e:
            logging.error(f"运行策略时发生错误: {e}")
            import traceback
            traceback.print_exc()


def main():
    """主函数"""
    # 创建并配置交易引擎
    engine = TradingEngine()

    # 添加数据源和策略
    engine.add_data_feed(symbol='QQQ').add_strategy(symbol='QQQ', sma_period=10)

    # 运行交易系统
    engine.run()


if __name__ == "__main__":
    main()
