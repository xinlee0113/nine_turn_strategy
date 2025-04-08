"""
信号生成器模块
用于生成交易信号的组件
"""
import logging
from typing import Dict, Any, Tuple

import numpy as np


class SignalGenerator:
    """信号生成器类
    
    根据传入的数据和参数生成交易信号：
    1 = 买入信号
    0 = 无信号
    -1 = 卖出信号
    """
    
    def __init__(self, params=None):
        """初始化信号生成器
        
        Args:
            params: 信号参数字典，包含信号生成所需的各种参数
        """
        # 默认参数
        self.params = {
            'magic_count': 5,        # 神奇九转信号触发计数
            'rsi_overbought': 70,    # RSI超买值
            'rsi_oversold': 30,      # RSI超卖值
            'enable_short': True     # 是否允许做空
        }
        
        # 如果提供了参数，则更新默认参数
        if params:
            self.params.update(params)
            
        self.logger = logging.getLogger(__name__)
            
    def check_long_signal(self, magic_nine, rsi, ema20, ema50) -> bool:
        """检查是否产生多头信号
        
        Args:
            magic_nine: 神奇九转指标对象
            rsi: RSI指标对象
            ema20: 20日EMA指标对象
            ema50: 50日EMA指标对象
            
        Returns:
            bool: 是否产生多头信号
        """
        # 多头信号条件：买入计数达标且EMA20>EMA50（上升趋势）且RSI不超买
        if magic_nine.lines.buy_setup[0] >= self.params['magic_count']:
            # 确认趋势方向 (EMA20 > EMA50 为上升趋势)
            trend_up = ema20[0] > ema50[0]
            
            # RSI不在超买区域 (避免在高点买入)
            rsi_ok = rsi[0] < self.params['rsi_overbought']
            
            return trend_up and rsi_ok
        
        return False
    
    def check_short_signal(self, magic_nine, rsi, ema20, ema50) -> bool:
        """检查是否产生空头信号
        
        Args:
            magic_nine: 神奇九转指标对象
            rsi: RSI指标对象
            ema20: 20日EMA指标对象
            ema50: 50日EMA指标对象
            
        Returns:
            bool: 是否产生空头信号
        """
        # 空头信号条件：卖出计数达标且EMA20<EMA50（下降趋势）且RSI不超卖
        if self.params['enable_short'] and magic_nine.lines.sell_setup[0] >= self.params['magic_count']:
            # 确认趋势方向 (EMA20 < EMA50 为下降趋势)
            trend_down = ema20[0] < ema50[0]
            
            # RSI不在超卖区域 (避免在低点卖空)
            rsi_ok = rsi[0] > self.params['rsi_oversold']
            
            return trend_down and rsi_ok
        
        return False
    
    def check_long_exit_signal(self, magic_nine) -> bool:
        """检查是否产生多头平仓信号
        
        Args:
            magic_nine: 神奇九转指标对象
            
        Returns:
            bool: 是否产生多头平仓信号
        """
        # 卖出信号作为多头平仓条件
        return magic_nine.lines.sell_setup[0] >= self.params['magic_count']
    
    def check_short_exit_signal(self, magic_nine) -> bool:
        """检查是否产生空头平仓信号
        
        Args:
            magic_nine: 神奇九转指标对象
            
        Returns:
            bool: 是否产生空头平仓信号
        """
        # 买入信号作为空头平仓条件
        return magic_nine.lines.buy_setup[0] >= self.params['magic_count']
    
    def generate_signal(self, magic_nine, rsi, ema20, ema50, current_position: int = 0) -> Tuple[int, str]:
        """生成交易信号
        
        Args:
            magic_nine: 神奇九转指标对象
            rsi: RSI指标对象
            ema20: 20日EMA指标对象
            ema50: 50日EMA指标对象
            current_position: 当前持仓状态 (1=多头, -1=空头, 0=无持仓)
            
        Returns:
            Tuple[int, str]: 信号类型和信号描述
                信号类型: 1=买入, -1=卖出, 0=无信号
                信号描述: 信号的文字描述
        """
        # 检查平仓信号
        if current_position > 0:  # 当前持有多头
            if self.check_long_exit_signal(magic_nine):
                return 0, "多头平仓信号"
        elif current_position < 0:  # 当前持有空头
            if self.check_short_exit_signal(magic_nine):
                return 0, "空头平仓信号"
        
        # 检查开仓信号
        if current_position == 0:  # 当前无持仓
            if self.check_long_signal(magic_nine, rsi, ema20, ema50):
                return 1, "多头开仓信号"
            elif self.check_short_signal(magic_nine, rsi, ema20, ema50):
                return -1, "空头开仓信号"
        
        # 默认无信号
        return 0, "无信号"

