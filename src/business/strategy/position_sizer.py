"""
仓位计算器模块
用于根据交易信号计算合适的仓位大小
"""
import logging

logger = logging.getLogger(__name__)


class PositionSizer:
    """仓位计算器类
    
    根据交易信号和账户状态计算合适的仓位大小
    """
    
    def __init__(self, params=None):
        """初始化仓位计算器
        
        Args:
            params: 仓位参数字典，包含仓位计算所需的各种参数
        """
        # 默认参数
        self.params = {
            'position_size': 0.95,       # 仓位大小(占总资金比例)
            'atr_period': 14,            # ATR周期
            'atr_multiplier': 2.5,       # ATR乘数
            'short_atr_multiplier': 2.8, # 空头ATR乘数
            'volatility_adjust': False   # 是否启用波动率调整
        }
        
        # 如果提供了参数，则更新默认参数
        if params:
            self.params.update(params)
            
    def calculate_long_position_size(self, broker_value, current_price):
        """计算多头仓位大小
        
        Args:
            broker_value: 当前账户价值
            current_price: 当前价格
            
        Returns:
            int: 多头仓位大小（股数）
        """
        # 基础仓位计算：账户价值 * 仓位比例 / 当前价格
        size = int(broker_value * self.params['position_size'] / current_price)
        return size
    
    def calculate_short_position_size(self, broker_value, current_price):
        """计算空头仓位大小
        
        Args:
            broker_value: 当前账户价值
            current_price: 当前价格
            
        Returns:
            int: 空头仓位大小（股数）
        """
        # 空头仓位计算逻辑与多头相同
        # 与原始代码完全相同的计算方式
        size = int(broker_value * self.params['position_size'] / current_price)
        return size
        
    def adjust_position_size_by_volatility(self, size, atr_value, is_short=False):
        """根据波动率调整仓位大小
        
        目前这个方法只是留作未来实现，不会改变仓位大小
        
        Args:
            size: 初始仓位大小
            atr_value: ATR值
            is_short: 是否为空头仓位
            
        Returns:
            int: 调整后的仓位大小
        """
        # 暂时不启用波动率调整，直接返回原始大小
        # 这是为了保持与原代码相同的行为
        return size
        
        # 下面是波动率调整的示例实现，暂时不启用
        """
        if not self.params['volatility_adjust'] or atr_value <= 0:
            return size
            
        # 选择对应的ATR乘数
        multiplier = self.params['short_atr_multiplier'] if is_short else self.params['atr_multiplier']
        
        # 计算风险调整系数 (ATR越大，仓位越小)
        risk_factor = 1.0 / (atr_value * multiplier)
        
        # 调整仓位大小
        adjusted_size = int(size * risk_factor)
        
        # 确保最小仓位为1
        if adjusted_size < 1:
            adjusted_size = 1
            
        logger.debug(f"波动率调整仓位: 原始仓位={size}, ATR={atr_value:.4f}, 乘数={multiplier}, 调整后={adjusted_size}")
        
        return adjusted_size
        """
