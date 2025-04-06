"""
回测脚本
负责回测流程的控制
"""
from src.business.engines.backtest_engine import BacktestEngine
from src.business.strategy.magic_nine import MagicNineStrategy
from src.interface.data.pandas_data import PandasData
from src.interface.broker.backtest_broker import BacktestBroker
from src.infrastructure.config import Config
from src.infrastructure.logging import Logger

class BacktestScript:
    """
    回测脚本类
    """
    def __init__(self):
        """
        初始化回测脚本
        """
        self.engine = None
        self.strategy = None
        self.data = None
        self.broker = None
        self.config = Config()
        self.logger = Logger()
    
    def run(self):
        """
        运行回测
        """
        # 加载配置
        self.config.load_config('configs/strategy/magic_nine.yaml')
        
        # 创建回测引擎
        self.engine = BacktestEngine()
        
        # 创建策略
        self.strategy = MagicNineStrategy()
        
        # 创建数据源
        self.data = PandasData()
        
        # 创建Broker
        self.broker = BacktestBroker()
        
        # 设置引擎
        self.engine.set_strategy(self.strategy)
        self.engine.set_data(self.data)
        self.engine.set_broker(self.broker)
        
        # 运行回测
        self.engine.run()
        
        # 分析结果
        self.engine.analyze()
    
    def stop(self):
        """
        停止回测
        """
        if self.engine:
            self.engine.stop() 