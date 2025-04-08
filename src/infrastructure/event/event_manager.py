"""
事件管理器
管理系统中的事件注册、触发和处理
"""
import logging
from typing import Dict, List, Callable, Any


class EventManager:
    """事件管理器，处理系统中的事件"""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self.logger = logging.getLogger(__name__)
        self.engine = None
        self.strategy = None
        self.broker = None

    def register_event(self, event_type: str, handler: Callable):
        """注册事件处理器
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        self.logger.debug(f"注册事件: {event_type}")

    def unregister_event(self, event_type: str, handler: Callable):
        """注销事件处理器
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
            self.logger.debug(f"注销事件: {event_type}")

    def trigger_event(self, event_type: str, *args, **kwargs):
        """触发事件
        
        Args:
            event_type: 事件类型
            *args, **kwargs: 事件参数
        """
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"事件处理异常: {event_type}, {str(e)}")
            self.logger.debug(f"触发事件: {event_type}")

    def register_listeners(self, engine: Any, strategy: Any, broker: Any):
        """注册回测相关的事件监听器
        
        Args:
            engine: 回测引擎
            strategy: 策略实例
            broker: 经纪商实例
        """
        self.logger.info("注册事件监听器")

        # 记录所有对象，方便后续使用
        self.engine = engine
        self.strategy = strategy
        self.broker = broker

        # 注册引擎事件
        self.register_event('engine_start', self._on_engine_start)
        self.register_event('engine_stop', self._on_engine_stop)

        # 注册策略事件
        self.register_event('strategy_signal', self._on_strategy_signal)

        # 注册交易事件
        self.register_event('trade_executed', self._on_trade_executed)
        self.register_event('order_submitted', self._on_order_submitted)

        # 注册错误事件
        self.register_event('error', self._on_error)

        # 注册数据事件
        self.register_event('data_ready', self._on_data_ready)

        # 给引擎添加事件触发的钩子方法
        self._patch_engine()

        self.logger.info("事件监听器注册完成")

    def _patch_engine(self):
        """
        给引擎添加事件触发的钩子
        这样可以在引擎的关键点上触发事件
        """
        self.logger.info("添加引擎事件触发钩子")

        # 保存原始方法的引用
        if hasattr(self.engine, 'run'):
            original_run = self.engine.run

            # 创建新的run方法
            def patched_run(*args, **kwargs):
                # 触发引擎启动事件
                self.trigger_event('engine_start')

                # 调用原始的run方法
                result = original_run(*args, **kwargs)

                # 触发引擎停止事件
                self.trigger_event('engine_stop')

                return result

            # 替换引擎的run方法
            self.engine.run = patched_run
            self.logger.info("已添加引擎run方法事件钩子")

        # 还可以添加其他引擎方法的钩子...

    def _on_engine_start(self, *args, **kwargs):
        """引擎启动事件处理"""
        self.logger.info("引擎启动事件")

    def _on_engine_stop(self, *args, **kwargs):
        """引擎停止事件处理"""
        self.logger.info("引擎停止事件")

    def _on_strategy_signal(self, symbol: str, signal: int, *args, **kwargs):
        """策略信号事件处理"""
        signal_type = "买入" if signal == 1 else "卖出" if signal == -1 else "空仓"
        self.logger.info(f"策略信号: {symbol} {signal_type}")

    def _on_trade_executed(self, trade: Dict[str, Any], *args, **kwargs):
        """交易执行事件处理"""
        self.logger.info(f"交易执行: {trade}")

    def _on_order_submitted(self, order: Dict[str, Any], *args, **kwargs):
        """订单提交事件处理"""
        self.logger.info(f"订单提交: {order}")

    def _on_error(self, error: str, *args, **kwargs):
        """错误事件处理"""
        self.logger.error(f"错误: {error}")

    def _on_data_ready(self, *args, **kwargs):
        """数据准备就绪事件处理"""
        self.logger.info("数据准备就绪")

    def _process_event(self, event_type: str, *args, **kwargs):
        """处理事件，内部方法"""
        self.trigger_event(event_type, *args, **kwargs)
