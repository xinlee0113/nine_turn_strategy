"""
交易脚本
负责实盘交易流程的控制
"""
from src.business.engines.live.live_engine import LiveEngine
from src.business.strategy import MagicNineStrategy
from src.interface.data.tiger_realtime_data import TigerRealtimeData
from src.interface.broker.tiger.tiger_broker import TigerBroker
from src.interface.store.tiger_store import TigerStore
from src.infrastructure.config.strategy_config import StrategyConfig
from src.infrastructure.logging.logger import Logger

class TradeScript:
    """
    交易脚本类
    """
    def __init__(self):
        """
        初始化交易脚本
        """
        self.engine = None
        self.strategy = None
        self.data = None
        self.broker = None
        self.store = None
        self.config = StrategyConfig()
        self.logger = Logger()
    
    def run(self):
        """
        运行交易
        """
        # 加载配置
        self.config.load_config('configs/strategy/magic_nine.yaml')
        self.config.load_config('configs/data/tiger_config.yaml')
        
        # 创建交易引擎
        self.engine = LiveEngine()
        
        # 创建策略
        self.strategy = MagicNineStrategy()
        
        # 创建数据存储
        self.store = TigerStore()
        self.store.start()
        
        # 创建数据源
        self.data = TigerRealtimeData()
        self.data.set_store(self.store)
        
        # 创建Broker
        self.broker = TigerBroker()
        self.broker.set_store(self.store)
        
        # 设置引擎
        self.engine.set_strategy(self.strategy)
        self.engine.set_data(self.data)
        self.engine.set_broker(self.broker)
        
        # 运行交易
        self.engine.run()
    
    def stop(self):
        """
        停止交易
        """
        if self.engine:
            self.engine.stop()
        if self.store:
            self.store.stop() 