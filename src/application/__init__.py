"""
应用层模块
负责程序的入口和整体流程控制
"""
from .script_factory import ScriptFactory
from .script_manager import ScriptManager
from .scripts.base_script import BaseScript
from .scripts.backtest_script import BacktestScript
from .scripts.optimize_script import OptimizeScript
from .scripts.live_trade_script import LiveTradeScript

# 暂时注释掉其他脚本的导入，以解决导入错误
# from .scripts.trade_script import TradeScript

__all__ = [
    'ScriptManager',
    'ScriptFactory',
    'BaseScript',
    'BacktestScript',
    'OptimizeScript',
    'LiveTradeScript',
    # 'TradeScript'
]
