"""
应用层模块
负责程序的入口和整体流程控制
"""
from .script_manager import ScriptManager
from .script_factory import ScriptFactory
from .scripts.backtest_script import BacktestScript
# 暂时注释掉其他脚本的导入，以解决导入错误
# from .scripts.optimize_script import OptimizeScript
# from .scripts.trade_script import TradeScript

__all__ = [
    'ScriptManager',
    'ScriptFactory',
    'BacktestScript',
    # 'OptimizeScript',
    # 'TradeScript'
] 