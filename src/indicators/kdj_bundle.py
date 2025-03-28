import backtrader as bt

class KDJBundle(bt.Indicator):
    """
    KDJ指标组合
    
    实现KDJ(随机指标)，常用于判断市场超买超卖状态和潜在反转点
    
    参数:
        period (int): 计算周期，默认为9
        period_dfast (int): K值平滑周期，默认为3
        period_dslow (int): D值平滑周期，默认为3
        
    输出线:
        K: K值线，快速随机线
        D: D值线，慢速随机线
        J: J值线，3*K-2*D
    """
    lines = ('K', 'D', 'J')
    params = (
        ('period', 9),
        ('period_dfast', 3),
        ('period_dslow', 3),
    )
    
    def __init__(self):
        # 创建标准化指标
        high_period = bt.indicators.Highest(self.data.high, period=self.p.period)
        low_period = bt.indicators.Lowest(self.data.low, period=self.p.period)
        
        # 计算原始K值
        self.rawK = 100.0 * (self.data.close - low_period) / (high_period - low_period)
        # 计算K值 (SMA平滑)
        self.K = bt.indicators.SMA(self.rawK, period=self.p.period_dfast)
        # 计算D值 (SMA平滑)
        self.D = bt.indicators.SMA(self.K, period=self.p.period_dslow)
        # 计算J值 (3*K - 2*D)
        self.J = 3.0 * self.K - 2.0 * self.D
        
    def next(self):
        # 将计算出的值赋给输出线
        self.lines.K[0] = self.K[0]
        self.lines.D[0] = self.D[0]
        self.lines.J[0] = self.J[0] 