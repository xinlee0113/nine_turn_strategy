import backtrader as bt
import numpy as np

class MagicNine(bt.Indicator):
    """
    神奇九转指标
    基于TD序列理论，计算买入和卖出信号
    """
    # 定义输出线
    lines = ('buy_setup', 'sell_setup', 'buy_signal', 'sell_signal')
    # 定义参数
    params = (
        ('period', 4),  # 比较周期，默认为4
    )
    
    def __init__(self):
        # 初始化计数器和信号
        self.buy_count = 0
        self.sell_count = 0
        
        # backtrader中不需要手动计算比较价格，可以使用self.data.close的偏移
        # 初始化不会生成实际信号，这些会在next方法中更新
    
    def next(self):
        # 计算买入序列
        if self.data.close[0] < self.data.close[-self.p.period]:
            self.buy_count += 1
            self.sell_count = 0
        # 计算卖出序列
        elif self.data.close[0] > self.data.close[-self.p.period]:
            self.sell_count += 1
            self.buy_count = 0
        else:
            # 价格相等，重置计数
            self.buy_count = 0
            self.sell_count = 0
        
        # 更新序列值
        # 在backtrader中，lines是直接用索引访问的特殊对象
        self.lines.buy_setup[0] = self.buy_count if self.buy_count > 0 else np.nan
        self.lines.sell_setup[0] = self.sell_count if self.sell_count > 0 else np.nan
        
        # 生成信号
        self.lines.buy_signal[0] = 1 if self.buy_count == 9 else 0
        self.lines.sell_signal[0] = 1 if self.sell_count == 9 else 0


# RSI指标组合
class RSIBundle(bt.Indicator):
    """RSI指标组合(6,12,24)"""
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


# KDJ指标组合
class KDJBundle(bt.Indicator):
    """KDJ指标组合(9,3,3)"""
    lines = ('K', 'D', 'J')
    params = (
        ('period', 9),
        ('period_dfast', 3),
        ('period_dslow', 3),
    )
    
    def __init__(self):
        # 创建标准化指标
        self.k = bt.indicators.Stochastic(
            self.data,
            period=self.p.period,
            period_dfast=self.p.period_dfast,
            period_dslow=self.p.period_dslow,
            movav=bt.indicators.MovAv.SMA,
            upperband=80.0,
            lowerband=20.0,
        )
        
        # 或者使用自定义KDJ计算方法
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