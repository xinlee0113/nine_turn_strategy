import backtrader as bt
import numpy as np


class MagicNine(bt.Indicator):
    """
    神奇九转指标
    基于TD序列理论，计算买入和卖出信号
    
    参数:
        period (int): 比较周期，默认为2
        signal_threshold (int): 信号阈值，当计数达到此值时触发信号
        
    输出线:
        buy_setup: 买入序列计数
        sell_setup: 卖出序列计数
        buy_signal: 买入信号 (当buy_setup>=signal_threshold时触发)
        sell_signal: 卖出信号 (当sell_setup>=signal_threshold时触发)
    """
    # 定义输出线
    lines = ('buy_setup', 'sell_setup', 'buy_signal', 'sell_signal')
    # 定义参数
    params = (
        ('period', 2),  # 比较周期，默认为2
        ('signal_threshold', 5),  # 信号阈值，当计数达到此值时触发信号
    )

    def __init__(self):
        # 初始化计数器和信号
        self.buy_count = 0
        self.sell_count = 0

    def next(self):
        # 确保有足够的数据来进行比较
        if len(self.data) <= self.p.period:
            # 数据不足，设置默认值
            self.lines.buy_setup[0] = np.nan
            self.lines.sell_setup[0] = np.nan
            self.lines.buy_signal[0] = 0
            self.lines.sell_signal[0] = 0
            return
            
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
        self.lines.buy_setup[0] = self.buy_count if self.buy_count > 0 else np.nan
        self.lines.sell_setup[0] = self.sell_count if self.sell_count > 0 else np.nan

        # 生成信号
        self.lines.buy_signal[0] = 1 if self.buy_count >= self.p.signal_threshold else 0
        self.lines.sell_signal[0] = 1 if self.sell_count >= self.p.signal_threshold else 0
