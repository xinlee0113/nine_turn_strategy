"""
脚本工厂
负责创建各种类型的脚本
"""
from src.application.scripts.backtest_script import BacktestScript
from src.application.scripts.optimize_script import OptimizeScript
from src.application.scripts.trade_script import TradeScript

class ScriptFactory:
    """
    脚本工厂类
    """
    @staticmethod
    def create_backtest_script():
        """
        创建回测脚本
        
        Returns:
            BacktestScript实例
        """
        return BacktestScript()
    
    @staticmethod
    def create_optimize_script():
        """
        创建优化脚本
        
        Returns:
            OptimizeScript实例
        """
        return OptimizeScript()
    
    @staticmethod
    def create_trade_script():
        """
        创建交易脚本
        
        Returns:
            TradeScript实例
        """
        return TradeScript() 