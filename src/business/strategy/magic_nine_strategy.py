import logging

import backtrader as bt

from src.business.indicators import MagicNine
from src.business.strategy.risk_manager import RiskManager
from src.business.strategy.signal_generator import SignalGenerator
from src.business.strategy.position_sizer import PositionSizer
from src.business.strategy.order_manager import OrderManager
from src.business.strategy.time_manager import TimeManager
from src.business.strategy.position_manager import PositionManager
from src.business.strategy.indicator_manager import IndicatorManager

logger = logging.getLogger(__name__)


class MagicNineStrategy(bt.Strategy):
    """神奇九转交易策略 - 优化版本，支持双向交易（多空）"""
    params = (
        ('magic_period', 3),  # 神奇九转比较周期
        ('magic_count', 5),  # 神奇九转信号触发计数
        ('rsi_period', 14),  # RSI周期
        ('rsi_overbought', 70),  # RSI超买值
        ('rsi_oversold', 30),  # RSI超卖值
        ('kdj_overbought', 80),  # KDJ超买值
        ('kdj_oversold', 20),  # KDJ超卖值
        ('atr_period', 14),  # ATR周期
        ('atr_multiplier', 2.5),  # ATR乘数
        ('stop_loss_pct', 0.8),  # 止损百分比
        ('profit_target_pct', 2.0),  # 利润目标百分比
        ('trailing_pct', 1.0),  # 移动止损激活百分比
        ('max_loss_pct', 3.0),  # 最大损失百分比
        ('min_profit_pct', 1.0),  # 最小利润百分比
        ('position_size', 0.95),  # 仓位大小(占总资金比例)
        ('trailing_stop', True),  # 是否启用移动止损
        ('enable_short', True),  # 是否允许做空
        ('short_atr_multiplier', 2.8),  # 空头ATR乘数
        ('short_max_loss_pct', 3.5),  # 空头最大损失百分比
        ('short_min_profit_pct', 1.2),  # 空头最小利润百分比
        ('volatility_adjust', True),  # 是否启用波动率调整
        ('market_aware', True),  # 是否启用市场意识
        ('time_decay', True),  # 是否启用时间衰减
        ('time_decay_days', 3),  # 时间衰减天数
        ('risk_aversion', 1.0),  # 风险厌恶系数
        ('avoid_open_minutes', 30),  # 避开开盘后的分钟数
        ('avoid_close_minutes', 30),  # 避开收盘前的分钟数
    )

    def __init__(self):
        """初始化策略"""
        # 初始化订单管理器
        self.order_manager = OrderManager(self)

        # 初始化风险管理器
        risk_params = {
            'stop_loss_pct': self.p.stop_loss_pct,
            'profit_target_pct': self.p.profit_target_pct,
            'trailing_pct': self.p.trailing_pct,
            'max_loss_pct': self.p.max_loss_pct,
            'min_profit_pct': self.p.min_profit_pct,
            'trailing_stop': self.p.trailing_stop,
            'short_max_loss_pct': self.p.short_max_loss_pct,
            'short_min_profit_pct': self.p.short_min_profit_pct
        }
        self.risk_manager = RiskManager(risk_params)
        
        # 初始化信号生成器
        signal_params = {
            'magic_count': self.p.magic_count,
            'rsi_overbought': self.p.rsi_overbought,
            'rsi_oversold': self.p.rsi_oversold,
            'enable_short': self.p.enable_short
        }
        self.signal_generator = SignalGenerator(signal_params)
        
        # 初始化仓位计算器
        position_params = {
            'position_size': self.p.position_size,
            'atr_period': self.p.atr_period,
            'atr_multiplier': self.p.atr_multiplier,
            'short_atr_multiplier': self.p.short_atr_multiplier,
            'volatility_adjust': self.p.volatility_adjust
        }
        self.position_sizer = PositionSizer(position_params)
        
        # 初始化时间管理器
        time_params = {
            'avoid_open_minutes': self.p.avoid_open_minutes,
            'avoid_close_minutes': self.p.avoid_close_minutes,
            'close_approach_minutes': 15  # 接近收盘的分钟数，默认为15分钟
        }
        self.time_manager = TimeManager(time_params)
        
        # 初始化持仓管理器
        self.position_manager = PositionManager(
            self, self.order_manager, self.position_sizer, self.risk_manager
        )
        
        # 初始化指标管理器
        self.indicators = IndicatorManager(self)

        logger.info(
            f"策略初始化完成 - 双向交易神奇九转模式 (比较周期:{self.p.magic_period}, 信号触发计数:{self.p.magic_count})")
        logger.info(f"避开开盘后{self.p.avoid_open_minutes}分钟和收盘前{self.p.avoid_close_minutes}分钟的交易")
        
    @property
    def magic_nine(self):
        """获取神奇九转指标"""
        return self.indicators.get_magic_nine()
        
    @property
    def rsi(self):
        """获取RSI指标"""
        return self.indicators.get_rsi()
        
    @property
    def ema20(self):
        """获取20周期EMA指标"""
        return self.indicators.get_ema20()
        
    @property
    def ema50(self):
        """获取50周期EMA指标"""
        return self.indicators.get_ema50()
        
    @property
    def atr(self):
        """获取ATR指标"""
        return self.indicators.get_atr()

    def notify_order(self, order):
        """订单状态通知回调"""
        # 委托给订单管理器处理
        self.order_manager.notify_order(order)

    def notify_trade(self, trade):
        """交易结果通知回调"""
        # 委托给订单管理器处理
        self.order_manager.notify_trade(trade)

    def next(self):
        """主策略逻辑"""
        # 如果有未完成的订单，不进行操作
        if self.order_manager.has_pending_order():
            return

        # 获取当前时间和价格
        current_time = self.data.datetime.datetime(0)
        current_price = self.data.close[0]
        
        # 使用时间管理器分析当前时间
        time_info = self.time_manager.analyze_time(current_time)
        
        # 每100个bar记录一次时间信息或在接近收盘时记录
        self.time_manager.log_time_info(current_time, time_info, log_interval=100, counter=len(self))
        
        # 处理接近收盘时的强制平仓
        if self.time_manager.is_near_close(time_info):
            if self.position_manager.force_close_at_end_of_day(current_time, time_info):
                return

        # 计算当前持仓状态用于信号生成
        current_position = self.position_manager.get_position_type()

        # 使用信号生成器获取交易信号
        signal, signal_desc = self.signal_generator.generate_signal(
            self.magic_nine, self.rsi, self.ema20, self.ema50, current_position
        )

        # 检查是否有仓位
        if not self.position_manager.has_position():
            # 没有仓位，检查买入或卖空信号
            if signal == 1 and self.time_manager.is_safe_trading_time(time_info) and not self.time_manager.is_near_close(time_info):
                # 多头开仓信号
                self.position_manager.open_long(current_price, "多头信号")

            elif signal == -1 and self.time_manager.is_safe_trading_time(time_info) and not self.time_manager.is_near_close(time_info):
                # 空头开仓信号
                self.position_manager.open_short(current_price, "空头信号")
        else:
            # 已有仓位，检查止损或平仓条件
            
            # 1. 处理止损和获利目标
            if self.position_manager.is_long():
                if self.position_manager.handle_long_position(current_price):
                    return
            elif self.position_manager.is_short():
                if self.position_manager.handle_short_position(current_price):
                    return
                    
            # 2. 检查信号平仓
            self.position_manager.handle_signal_exit(signal, self.magic_nine)
