import backtrader as bt

class RSIBundle(bt.Indicator):
    """
    RSI指标组合(6,12,24)
    
    计算三个不同周期的RSI值，用于多角度判断市场超买超卖状态
    
    参数:
        period1 (int): 短周期RSI，默认为6
        period2 (int): 中周期RSI，默认为12
        period3 (int): 长周期RSI，默认为24
        
    输出线:
        rsi6: 6周期RSI值
        rsi12: 12周期RSI值
        rsi24: 24周期RSI值
    """
    lines = ('rsi6', 'rsi12', 'rsi24')
    params = (
        ('period1', 6),
        ('period2', 12),
        ('period3', 24),
    )
    
    def __init__(self):
        # 创建三个不同周期的RSI指标
        self.rsi1 = bt.indicators.RSI(self.data, period=self.p.period1)
        self.rsi2 = bt.indicators.RSI(self.data, period=self.p.period2)
        self.rsi3 = bt.indicators.RSI(self.data, period=self.p.period3)
    
    def next(self):
        # 更新lines值
        self.lines.rsi6[0] = self.rsi1.lines.rsi[0]
        self.lines.rsi12[0] = self.rsi2.lines.rsi[0]
        self.lines.rsi24[0] = self.rsi3.lines.rsi[0] 