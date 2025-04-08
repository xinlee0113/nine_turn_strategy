"""
优化脚本
负责参数优化流程的控制
"""
from src.business.engines.optimize.optimize_engine import OptimizeEngine
from src.business.strategy import MagicNineStrategy
from src.infrastructure.config.strategy_config import StrategyConfig
from src.infrastructure.logging.logger import Logger
from src.interface.broker.backtest_broker import BacktestBroker
from src.interface.data.pandas_data import PandasData


class OptimizeScript:
    """
    优化脚本类
    """

    def __init__(self):
        """
        初始化优化脚本
        """
        self.engine = None
        self.strategy = None
        self.data = None
        self.broker = None
        self.config = StrategyConfig()
        self.logger = Logger()

    def run(self):
        """
        运行优化
        """
        # 加载配置
        self.config.load_config('configs/strategy/magic_nine.yaml')

        # 创建优化引擎
        self.engine = OptimizeEngine()

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

        # 设置参数范围
        self.engine.set_param_ranges({
            'param1': (0, 100),
            'param2': (0, 1.0),
            'param3': (1, 10)
        })

        # 运行优化
        self.engine.run()

        # 获取最优参数
        best_params = self.engine.get_best_params()
        self.logger.info(f"Best parameters: {best_params}")

    def stop(self):
        """
        停止优化
        """
        if self.engine:
            self.engine.stop()
