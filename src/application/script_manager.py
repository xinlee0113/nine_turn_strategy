"""
脚本管理器
负责管理和创建不同的脚本实例
"""
import logging
from typing import Dict, Any, Optional, List, Union

from src.application.scripts.backtest_script import BacktestScript
from src.application.scripts.optimize_script import OptimizeScript
from src.application.scripts.live_trade_script import LiveTradeScript
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
        self.logger.info("创建回测脚本")
        backtest_script = BacktestScript()
        self.scripts['backtest'] = backtest_script
        return backtest_script

    def run_backtest(self, enable_plot: bool = False, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """运行回测脚本
        
        Args:
            enable_plot: 是否启用图表
            symbols: 回测标的列表，如果为None则使用默认标的
            
        Returns:
            Dict: 回测结果
        """
        if enable_plot:
            self.logger.info("启用回测图表")

        # 如果脚本不存在，则创建
        if 'backtest' not in self.scripts:
            self.create_backtest_script()

        # 运行回测
        backtest_script = self.scripts['backtest']
        
        # 如果提供了标的列表，则设置
        if symbols:
            backtest_script.set_symbols(symbols)
            
        results = backtest_script.run(enable_plot=enable_plot)

        # 返回回测结果
        self.logger.info("回测执行完成，返回结果")
        return results
        
    def create_optimize_script(self) -> OptimizeScript:
        """创建优化脚本
        
        Returns:
            OptimizeScript: 优化脚本实例
        """
        self.logger.info("创建优化脚本")
        optimize_script = OptimizeScript()
        self.scripts['optimize'] = optimize_script
        return optimize_script
        
    def run_optimize(self, symbol: Optional[str] = None, param_grid: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """运行优化脚本
        
        Args:
            symbol: 要优化的交易标的，如果为None则使用默认的target_symbols
            param_grid: 参数网格配置，如果为None则使用默认配置
            
        Returns:
            Dict: 优化结果
        """
        # 如果脚本不存在，则创建
        if 'optimize' not in self.scripts:
            self.create_optimize_script()
            
        # 运行优化
        optimize_script = self.scripts['optimize']
        results = optimize_script.run(symbol=symbol, param_grid=param_grid)
        
        # 返回优化结果
        self.logger.info("优化执行完成，返回结果")
        return results

    def get_script(self, script_name: str) -> Optional[Any]:
        return self.scripts.get(script_name)

    def create_live_trade_script(self) -> LiveTradeScript:
        self.logger.info("实盘交易脚本")
        live_script = LiveTradeScript()
        self.scripts['live'] = live_script
        return live_script

    def run_live_trade(self, symbols: List[str]):
        """运行实盘交易脚本
        
        Args:
            symbols: 交易标的列表
        """
        if 'live' not in self.scripts:
            self.create_live_trade_script()
        live_script = self.scripts['live']
        results = live_script.run(symbols)
        self.logger.info("实盘交易执行完成，返回结果")
        return results
