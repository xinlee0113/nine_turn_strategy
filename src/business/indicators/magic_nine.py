import backtrader as bt
import numpy as np


class MagicNine(bt.Indicator):
    """
    神奇九转指标
    基于TD序列理论，计算连续上涨和连续下跌的次数来产生交易信号
    
    参数:
        lookback (int): 价格比较间隔，默认为2 (与2分钟前比较，使用1分钟K线)
        signal_threshold (int): 信号阈值，当计数达到此值时触发信号
        
    输出线:
        drop_count: 连续下跌次数(原buy_setup)
        rise_count: 连续上涨次数(原sell_setup)
        buy_signal: 买入信号 (当连续下跌次数>=signal_threshold时触发)
        sell_signal: 卖出信号 (当连续上涨次数>=signal_threshold时触发)
    """
    # 定义输出线
    lines = ('drop_count', 'rise_count', 'buy_signal', 'sell_signal')
    # 定义参数
    params = (
        ('lookback', 2),  # 回溯间隔，默认为2个K线(使用1分钟K线时为2分钟)
        ('signal_threshold', 5),  # 信号阈值，当计数达到此值时触发信号
    )

    def __init__(self):
        # 初始化计数器和信号
        self.drop_counter = 0  # 连续下跌计数器
        self.rise_counter = 0  # 连续上涨计数器

    def next(self):
        # 确保有足够的数据来进行比较
        if len(self.data) <= self.p.lookback:
            # 数据不足，设置默认值
            self.lines.drop_count[0] = np.nan
            self.lines.rise_count[0] = np.nan
            self.lines.buy_signal[0] = 0
            self.lines.sell_signal[0] = 0
            return
            
        # 当前收盘价低于lookback个K线前的收盘价，视为下跌
        if self.data.close[0] < self.data.close[-self.p.lookback]:
            self.drop_counter += 1   # 下跌计数增加
            self.rise_counter = 0    # 重置上涨计数
        # 当前收盘价高于lookback个K线前的收盘价，视为上涨
        elif self.data.close[0] > self.data.close[-self.p.lookback]:
            self.rise_counter += 1   # 上涨计数增加
            self.drop_counter = 0    # 重置下跌计数
        else:
            # 价格相等，重置计数
            self.drop_counter = 0
            self.rise_counter = 0

        # 更新序列值
        self.lines.drop_count[0] = self.drop_counter if self.drop_counter > 0 else np.nan
        self.lines.rise_count[0] = self.rise_counter if self.rise_counter > 0 else np.nan

        # 生成信号
        # 连续下跌达到阈值，产生买入信号(逆势买入)
        self.lines.buy_signal[0] = 1 if self.drop_counter >= self.p.signal_threshold else 0
        # 连续上涨达到阈值，产生卖出信号(逆势卖出)
        self.lines.sell_signal[0] = 1 if self.rise_counter >= self.p.signal_threshold else 0
