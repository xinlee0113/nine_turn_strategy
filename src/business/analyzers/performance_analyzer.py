from .base_analyzer import BaseAnalyzer

class PerformanceAnalyzer(BaseAnalyzer):
    """性能分析器"""
    
    def __init__(self):
        """初始化性能分析器"""
        super().__init__()
        self.returns = []
        self.drawdowns = []
        self.sharpe_ratio = 0.0
        self.max_drawdown = 0.0
        self.win_rate = 0.0
        
    def next(self):
        """处理下一个数据点"""
        pass
    
    def get_analysis(self):
        """获取分析结果"""
        return {
            'returns': self.returns,
            'drawdowns': self.drawdowns,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate
        } 