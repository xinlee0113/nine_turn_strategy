"""
脚本管理器
负责管理各种运行脚本，如回测、优化、实盘等
"""
from src.application.scripts.backtest_script import BacktestScript
from src.application.scripts.optimize_script import OptimizeScript
from src.application.scripts.trade_script import TradeScript

class ScriptManager:
    """
    脚本管理器类
    """
    def __init__(self):
        """
        初始化脚本管理器
        """
        self.backtest_script = None
        self.optimize_script = None
        self.trade_script = None
    
    def create_script(self, script_type):
        """
        创建指定类型的脚本
        
        Args:
            script_type: 脚本类型，可选值：'backtest', 'optimize', 'trade'
            
        Returns:
            创建的脚本实例
        """
        if script_type == 'backtest':
            self.backtest_script = BacktestScript()
            return self.backtest_script
        elif script_type == 'optimize':
            self.optimize_script = OptimizeScript()
            return self.optimize_script
        elif script_type == 'trade':
            self.trade_script = TradeScript()
            return self.trade_script
        else:
            raise ValueError(f"Unknown script type: {script_type}")
    
    def run_script(self, script_type):
        """
        运行指定类型的脚本
        
        Args:
            script_type: 脚本类型，可选值：'backtest', 'optimize', 'trade'
        """
        script = self.create_script(script_type)
        script.run()
    
    def stop_script(self, script_type):
        """
        停止指定类型的脚本
        
        Args:
            script_type: 脚本类型，可选值：'backtest', 'optimize', 'trade'
        """
        if script_type == 'backtest' and self.backtest_script:
            self.backtest_script.stop()
        elif script_type == 'optimize' and self.optimize_script:
            self.optimize_script.stop()
        elif script_type == 'trade' and self.trade_script:
            self.trade_script.stop()
        else:
            raise ValueError(f"Unknown script type: {script_type}") 