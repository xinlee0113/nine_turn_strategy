"""
策略模块包，包含策略开发的基础框架。
用于实现各种交易策略。
"""

# 导入策略基类
from .base_strategy import BaseStrategy
# 导入具体策略实现
from .magic_nine_strategy import MagicNineStrategy
from .position_sizer import PositionSizer
from .risk_manager import RiskManager
# 导入具体策略组件
from .signal_generator import SignalGenerator
from .time_manager import TimeManager
from .order_manager import OrderManager
from .position_manager import PositionManager

__all__ = [
    'BaseStrategy',
    'SignalGenerator',
    'PositionSizer',
    'RiskManager',
    'MagicNineStrategy',
    'TimeManager',
    'OrderManager',
    'PositionManager'
]
