"""
神奇九转指标
计算连续上涨或下跌的K线数量，用于神奇九转策略
"""
import backtrader as bt
import numpy as np

class MagicNineIndicator(bt.Indicator):
    """
    神奇九转指标
    计算连续上涨或下跌的K线数量，用于识别潜在的超买超卖点
    
    lines = ('up_count', 'down_count')
    """
    
    lines = ('up_count', 'down_count',)
    params = (('period', 9),)
    
    def __init__(self):
        """初始化指标"""
        # 使用close价格
        self.data_close = self.data.close
        
        # 初始化计数器 - 避免与lines名称冲突
        self._up_counter = 0
        self._down_counter = 0
        
        # 不要在此处初始化line值，而是在next方法中进行
        
        # 添加指标的绘图设置
        self.plotinfo.plotymargin = 0.1
        self.plotinfo.plotyhlines = [0, self.p.period]
        self.plotinfo.plot = True
        
        # 设置线条颜色
        self.plotlines.up_count.color = 'green'
        self.plotlines.down_count.color = 'red'
    
    def prenext(self):
        """数据不足时调用，确保初始值为0"""
        self.lines.up_count[0] = 0
        self.lines.down_count[0] = 0
    
    def next(self):
        """计算下一个值"""
        # 如果是第一个K线，无法比较
        if len(self.data) <= 1:
            self.lines.up_count[0] = 0
            self.lines.down_count[0] = 0
            return
            
        # 计算价格变化
        price_change = self.data_close[0] - self.data_close[-1]
        
        # 更新连续上涨/下跌计数
        if price_change > 0:
            # 上涨
            self._up_counter += 1
            self._down_counter = 0
        elif price_change < 0:
            # 下跌
            self._down_counter += 1
            self._up_counter = 0
        # 价格不变时保持计数不变
        
        # 更新指标值
        self.lines.up_count[0] = self._up_counter
        self.lines.down_count[0] = self._down_counter 