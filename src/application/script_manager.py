"""
脚本管理器
负责管理和创建不同的脚本实例
"""
import logging
from typing import Dict, Any, Optional, Type

from src.application.scripts.backtest_script import BacktestScript
from src.infrastructure.logging.logger import Logger

class ScriptManager:
    """
    脚本管理器
    负责创建和管理各种脚本实例，如回测脚本、优化脚本、实盘脚本等
    符合架构图中的设计
    """
    def __init__(self):
        """初始化脚本管理器"""
        self.logger = logging.getLogger(__name__)
        self.logger_manager = Logger()
        self.scripts = {}
        self.logger.info("ScriptManager初始化完成")
    
    def create_backtest_script(self) -> BacktestScript:
        """
        创建回测脚本
        按照架构图中的回测流程设计
        
        Returns:
            BacktestScript: 回测脚本实例
        """
        self.logger.info("创建回测脚本")
        backtest_script = BacktestScript()
        self.scripts['backtest'] = backtest_script
        return backtest_script
    
    def run_backtest(self, symbol: str, start_date, end_date, period: str) -> Dict[str, Any]:
        """
        运行回测脚本
        
        Args:
            symbol: 交易标的代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期
            
        Returns:
            Dict[str, Any]: 回测结果
        """
        self.logger.info(f"运行回测: {symbol}, {start_date} - {end_date}")
        
        # 如果脚本不存在，则创建
        if 'backtest' not in self.scripts:
            self.create_backtest_script()
            
        # 运行回测
        backtest_script = self.scripts['backtest']
        results = backtest_script.run(symbol, start_date, end_date, period)
        
        # 展示回测结果
        self.logger.info("回测执行完成，返回结果")
        return results
    
    def get_script(self, script_name: str) -> Optional[Any]:
        """
        获取已创建的脚本实例
        
        Args:
            script_name: 脚本名称
            
        Returns:
            Optional[Any]: 脚本实例，如果不存在则返回None
        """
        return self.scripts.get(script_name) 