"""
脚本管理器
负责管理和创建不同的脚本实例
"""
import logging
from typing import Dict, Any, Optional

from src.application.scripts.backtest_script import BacktestScript
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

    def run_backtest(self, enable_plot: bool = False) -> Dict[str, Any]:
        if enable_plot:
            self.logger.info("启用回测图表")

        # 如果脚本不存在，则创建
        if 'backtest' not in self.scripts:
            self.create_backtest_script()

        # 运行回测
        backtest_script = self.scripts['backtest']
        results = backtest_script.run(enable_plot=enable_plot)

        # 展示回测结果
        self.logger.info("回测执行完成，返回结果")
        return results

    def get_script(self, script_name: str) -> Optional[Any]:
        return self.scripts.get(script_name)

    def create_live_trade_script(self) -> LiveTradeScript:
        self.logger.info("实盘交易脚本")
        live_script = LiveTradeScript()
        self.scripts['live'] = live_script
        return live_script

    def run_live_trade(self, symbols: []):
        if 'live' not in self.scripts:
            self.create_live_trade_script()
        live_script = self.scripts['live']
        results = live_script.run(symbols)
        self.logger.info("实盘交易执行完成，返回结果")
        return results
