import backtrader as bt
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False    # 用来正常显示负号

class MagicNineObserver(bt.Observer):
    """神奇九转观察器，用于在主图上显示买入和卖出序列"""
    # 定义观察器输出线
    lines = ('buy_setup', 'sell_setup', 'buy_signal', 'sell_signal')
    
    # 配置绘图属性
    plotinfo = dict(plot=True, subplot=False, plotlinelabels=True)
    
    # 配置线的绘图样式
    plotlines = dict(
        buy_setup=dict(marker='o', markersize=8, color='green', fillstyle='full'),
        sell_setup=dict(marker='o', markersize=8, color='red', fillstyle='full'),
        buy_signal=dict(marker='^', markersize=12, color='blue', fillstyle='full'),
        sell_signal=dict(marker='v', markersize=12, color='purple', fillstyle='full')
    )
    
    def next(self):
        # 从策略中获取神奇九转指标的值
        # 因为我们在策略中添加了magic_nine属性，所以可以直接访问
        if hasattr(self._owner, 'magic_nine'):
            # 获取buy_setup值
            if hasattr(self._owner.magic_nine, 'buy_count'):
                buy_count = self._owner.magic_nine.buy_count
                self.lines.buy_setup[0] = buy_count if buy_count > 0 else float('nan')
            else:
                self.lines.buy_setup[0] = float('nan')
                
            # 获取sell_setup值
            if hasattr(self._owner.magic_nine, 'sell_count'):
                sell_count = self._owner.magic_nine.sell_count
                self.lines.sell_setup[0] = sell_count if sell_count > 0 else float('nan')
            else:
                self.lines.sell_setup[0] = float('nan')
                
            # 获取信号值
            if hasattr(self._owner.magic_nine.lines, 'buy_signal'):
                self.lines.buy_signal[0] = self._owner.magic_nine.lines.buy_signal[0]
            else:
                self.lines.buy_signal[0] = 0
                
            if hasattr(self._owner.magic_nine.lines, 'sell_signal'):
                self.lines.sell_signal[0] = self._owner.magic_nine.lines.sell_signal[0]
            else:
                self.lines.sell_signal[0] = 0
        else:
            # 如果没有magic_nine属性，则所有值设为NaN或0
            self.lines.buy_setup[0] = float('nan')
            self.lines.sell_setup[0] = float('nan')
            self.lines.buy_signal[0] = 0
            self.lines.sell_signal[0] = 0 