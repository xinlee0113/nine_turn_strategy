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
    
    def __init__(self, params: Dict[str, Any]):
        """初始化信号生成器
        
        Args:
            params: 参数字典，包含信号生成所需参数
        """
        self.params = params
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"信号生成器初始化，参数: {params}")
        
    def generate_signal(self, data: Dict[str, Any]) -> int:
        """生成交易信号
        
        Args:
            data: 包含决策所需数据的字典
                magic_nine_buy: MagicNine买入计数
                magic_nine_sell: MagicNine卖出计数
                rsi: RSI指标值
                ema20: 20周期EMA
                ema50: 50周期EMA
                current_position: 当前持仓 (1=多头, -1=空头, 0=无持仓)
                price: 当前价格
                time_info: 市场时间信息
                
        Returns:
            int: 交易信号 (1=买入, 0=无信号, -1=卖出)
        """
        # 获取神奇九转计数
        magic_nine_buy = data.get('magic_nine_buy', 0)
        magic_nine_sell = data.get('magic_nine_sell', 0)
        
        # 获取RSI和EMA指标
        rsi = data.get('rsi', 50)
        ema20 = data.get('ema20', 0)
        ema50 = data.get('ema50', 0)
        
        # 获取当前持仓状态
        current_position = data.get('current_position', 0)
        
        # 获取参数
        magic_count = self.params.get('magic_count', 5)
        rsi_overbought = self.params.get('rsi_overbought', 70)
        rsi_oversold = self.params.get('rsi_oversold', 30)
        enable_short = self.params.get('enable_short', True)
        
        # 初始化信号
        signal = 0
        
        # 生成交易信号
        
        # 如果已有持仓，检查平仓信号
        if current_position > 0:  # 多头持仓
            # 检查是否有卖出信号
            if not np.isnan(magic_nine_sell) and magic_nine_sell >= magic_count:
                signal = -1
                self.logger.info(f"生成卖出信号: 多头平仓 (MagicNine卖出计数={magic_nine_sell})")
        
        elif current_position < 0:  # 空头持仓
            # 检查是否有买入信号
            if not np.isnan(magic_nine_buy) and magic_nine_buy >= magic_count:
                signal = 1
                self.logger.info(f"生成买入信号: 空头平仓 (MagicNine买入计数={magic_nine_buy})")
        
        else:  # 无持仓，检查开仓信号
            # 多头信号条件：买入计数达标且EMA20>EMA50（上升趋势）且RSI不超买
            if not np.isnan(magic_nine_buy) and magic_nine_buy >= magic_count:
                # 确认趋势方向 (EMA20 > EMA50 为上升趋势)
                trend_up = ema20 > ema50
                
                # RSI不在超买区域 (避免在高点买入)
                rsi_ok = rsi < rsi_overbought
                
                if trend_up and rsi_ok:
                    signal = 1
                    self.logger.info(f"生成买入信号: 新建多头 (MagicNine买入计数={magic_nine_buy}, RSI={rsi:.1f})")
            
            # 空头信号条件：卖出计数达标且EMA20<EMA50（下降趋势）且RSI不超卖
            elif enable_short and not np.isnan(magic_nine_sell) and magic_nine_sell >= magic_count:
                # 确认趋势方向 (EMA20 < EMA50 为下降趋势)
                trend_down = ema20 < ema50
                
                # RSI不在超卖区域 (避免在低点卖空)
                rsi_ok = rsi > rsi_oversold
                
                if trend_down and rsi_ok:
                    signal = -1
                    self.logger.info(f"生成卖出信号: 新建空头 (MagicNine卖出计数={magic_nine_sell}, RSI={rsi:.1f})")
            
        return signal 