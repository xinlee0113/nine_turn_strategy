"""
交易脚本
负责实盘交易流程的控制
"""
import backtrader

from src.business.strategy import MagicNineStrategy
from src.business.strategy.test_strategy import TestStrategy
from src.infrastructure.config.strategy_config import StrategyConfig
from src.infrastructure.logging.logger import Logger
from src.interface.tiger.tiger_store import TigerStore


class LiveTradeScript:
    """
    交易脚本类
    """

    def __init__(self):
        """
        初始化交易脚本
        """
        self.cerebro = None
        self.strategy = None
        self.data = None
        self.broker = None
        self.store = None
        self.config = StrategyConfig()
        self.logger = Logger()

    def run(self, symbols):
        """
        运行交易
        """
        # 加载配置
        self.config.load_config('configs/strategy/magic_nine.yaml')

        # 创建交易引擎
        self.cerebro = backtrader.cerebro.Cerebro()
        
        # 确保symbols列表不为空
        if not symbols:
            self.logger.error("未提供交易标的，请指定至少一个交易标的")
            return False
            
        # 获取第一个交易标的
        symbol = symbols[0]
        self.logger.info(f"使用交易标的: {symbol}")
        
        # 创建数据存储
        self.store = TigerStore(symbols=symbols)
        self.cerebro.addstore(self.store)
        
        # 获取数据源并设置名称
        data = self.store.getdata()
        data._name = symbol  # 确保数据对象有正确的标的名称
        self.cerebro.adddata(data)
        self.cerebro.broker = self.store.getbroker()

        # 创建策略，并传入正确的symbol参数
        self.cerebro.addstrategy(TestStrategy, symbol=symbol)

        # 运行交易
        self.cerebro.run()
        return True

    def stop(self):
        """
        停止交易
        """
        if self.cerebro:
            self.cerebro.stop()
        if self.store:
            self.store.stop()
