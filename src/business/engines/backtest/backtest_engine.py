from ..base_engine import BaseEngine
from ...analyzers.performance_analyzer import PerformanceAnalyzer
from ...analyzers.risk_analyzer import RiskAnalyzer

class BacktestEngine(BaseEngine):
    """回测引擎"""

    def __init__(self, config):
        """初始化回测引擎"""
        super().__init__(config)
        self.analyzers = []
        self.performance_analyzer = PerformanceAnalyzer()
        self.risk_analyzer = RiskAnalyzer()
        self.analyzers.extend([self.performance_analyzer, self.risk_analyzer])

    def run(self):
        """运行回测"""
        self.initialize()
        self.process_data()
        self.finalize()

    def initialize(self):
        """初始化回测环境"""
        for analyzer in self.analyzers:
            analyzer.initialize()

    def process_data(self):
        """处理回测数据"""
        for data in self.data_source:
            self.strategy.next(data)
            for analyzer in self.analyzers:
                analyzer.update(self.strategy)

    def finalize(self):
        """完成回测"""
        results = {}
        for analyzer in self.analyzers:
            results.update(analyzer.get_results())
        return results 