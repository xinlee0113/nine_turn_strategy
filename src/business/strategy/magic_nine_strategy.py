import logging
from datetime import datetime, timedelta

import backtrader as bt
import pytz

from src.business.indicators import MagicNine
from src.business.strategy.risk_manager import RiskManager
from src.business.strategy.signal_generator import SignalGenerator

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
        # 订单和仓位跟踪
        self.order = None
        self.buy_price = None
        self.buy_comm = None
        self.position_size = 0
        self.is_short = False  # 标记当前是否为空头仓位

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

        # 指标初始化
        self.magic_nine = MagicNine(self.data, period=self.p.magic_period)
        self.rsi = bt.indicators.RSI(self.data, period=self.p.rsi_period)
        self.ema20 = bt.indicators.EMA(self.data, period=20)
        self.ema50 = bt.indicators.EMA(self.data, period=50)

        logger.info(
            f"策略初始化完成 - 双向交易神奇九转模式 (比较周期:{self.p.magic_period}, 信号触发计数:{self.p.magic_count})")
        logger.info(f"避开开盘后{self.p.avoid_open_minutes}分钟和收盘前{self.p.avoid_close_minutes}分钟的交易")

    def notify_order(self, order):
        """订单状态通知回调"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交或已接受 - 无需操作
            return

        # 检查订单是否已完成
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(
                    f'{self.data.datetime.datetime(0).isoformat()} 买入执行，价格: {order.executed.price:.2f}, '
                    f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}'
                )
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
            else:  # 卖出
                if self.is_short:
                    logger.info(
                        f'{self.data.datetime.datetime(0).isoformat()} 卖空执行，价格: {order.executed.price:.2f}, '
                        f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}'
                    )
                    self.buy_price = order.executed.price  # 记录卖空价格
                    self.buy_comm = order.executed.comm
                else:
                    logger.info(
                        f'{self.data.datetime.datetime(0).isoformat()} 卖出执行，价格: {order.executed.price:.2f}, '
                        f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}'
                    )
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f'{self.data.datetime.datetime(0).isoformat()} 订单取消/保证金不足/拒绝')

        # 重置订单引用
        self.order = None

    def notify_trade(self, trade):
        """交易结果通知回调"""
        if trade.isclosed:
            if self.is_short:
                # 计算空头交易利润
                profit = (self.buy_price - trade.price) * trade.size
                profit_pct = (self.buy_price / trade.price - 1) * 100
                logger.info(
                    f'{self.data.datetime.datetime(0).isoformat()} 空头交易利润: {profit:.2f}, 收益率: {profit_pct:.2f}%')
                self.is_short = False

            logger.info(
                f'{self.data.datetime.datetime(0).isoformat()} 交易利润, 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')

    def next(self):
        """主策略逻辑"""
        # 如果有未完成的订单，不进行操作
        if self.order:
            return

        # 获取当前时间
        current_time = self.data.datetime.datetime(0)

        # 时区判断与转换 - 证券交易时间处理
        # 美股正常交易时间是美东时间(ET)的9:30-16:00

        # 使用pytz准确判断是否是夏令时
        eastern = pytz.timezone('US/Eastern')
        # 使用当前日期构建一个aware datetime对象
        # backtrader提供的datetime对象是naive的，我们需要假设它是UTC时间
        # 然后验证当前时间对应的美东时间是否在夏令时
        utc_time = pytz.utc.localize(datetime(
            current_time.year, current_time.month, current_time.day,
            current_time.hour, current_time.minute, current_time.second
        ))
        et_time = utc_time.astimezone(eastern)
        is_dst = et_time.dst() != timedelta(0)

        # 初始假设时间是美东时间
        et_hour = current_time.hour
        et_minute = current_time.minute
        is_utc_time = False

        # 判断是否可能是UTC时间格式，根据交易时间合理性判断
        # UTC时间对应美股交易时间：
        # 美东标准时(EST)：UTC-5，交易时间是UTC 14:30-21:00
        # 美东夏令时(EDT)：UTC-4，交易时间是UTC 13:30-20:00
        if is_dst:  # 夏令时
            # 如果时间在UTC交易范围内，可能是UTC时间
            if 13 <= current_time.hour <= 20:
                is_utc_time = True
                et_hour = (current_time.hour - 4) % 24  # UTC-4
        else:  # 标准时
            # 如果时间在UTC交易范围内，可能是UTC时间
            if 14 <= current_time.hour <= 21:
                is_utc_time = True
                et_hour = (current_time.hour - 5) % 24  # UTC-5

        # 计算开盘和收盘时间
        market_open_hour = 9
        market_open_minute = 30
        market_close_hour = 16
        market_close_minute = 0

        # 计算交易时间分钟数（相对于开盘时间）
        minutes_since_open = (et_hour - market_open_hour) * 60 + (et_minute - market_open_minute)
        minutes_before_close = (market_close_hour - et_hour) * 60 + (market_close_minute - et_minute)

        # 判断是否在交易时段 (美东时间9:30-16:00)，并避开开盘和收盘的30分钟
        is_trading_time = (9 < et_hour < 16) or (et_hour == 9 and et_minute >= 30) or (et_hour == 16 and et_minute == 0)
        is_safe_trading_time = is_trading_time and minutes_since_open >= self.p.avoid_open_minutes and minutes_before_close >= self.p.avoid_close_minutes

        # 判断是否接近美股收盘时间 (美东时间15:45-16:00)
        is_near_close = (et_hour == 15 and et_minute >= 45) or et_hour == 16

        # 记录详细的时间信息用于调试
        if len(self) % 100 == 0 or is_near_close:  # 每100个bar记录一次或接近收盘时记录
            time_format = "UTC" if is_utc_time else "ET"
            logger.info(f"时间检查: 原始时间={current_time.isoformat()}, 计算为美东时间:{et_hour}:{et_minute:02d}, "
                        f"时间格式:{time_format}, 交易时段:{is_trading_time}, 安全交易时段:{is_safe_trading_time}, "
                        f"开盘后分钟数:{minutes_since_open}, 收盘前分钟数:{minutes_before_close}, "
                        f"接近收盘:{is_near_close}, 夏令时:{is_dst}")

        # 如果接近收盘且有持仓，强制平仓
        if is_near_close and self.position:
            if self.position.size > 0:  # 多头持仓
                logger.info(
                    f'{current_time.isoformat()} 收盘前强制平仓多头! 价格: {self.data.close[0]:.2f}, ET时间约: {et_hour}:{et_minute:02d}')
                self.order = self.sell(size=self.position_size)
                self.position_size = 0
                self.risk_manager.reset()
                return
            elif self.position.size < 0:  # 空头持仓
                logger.info(
                    f'{current_time.isoformat()} 收盘前强制平仓空头! 价格: {self.data.close[0]:.2f}, ET时间约: {et_hour}:{et_minute:02d}')
                self.order = self.buy(size=self.position_size)
                self.position_size = 0
                self.risk_manager.reset()
                self.is_short = False
                return

        # 获取当前价格
        current_price = self.data.close[0]

        # 计算当前持仓状态用于信号生成
        current_position = 0
        if self.position.size > 0:
            current_position = 1
        elif self.position.size < 0:
            current_position = -1

        # 使用信号生成器获取交易信号
        signal, signal_desc = self.signal_generator.generate_signal(
            self.magic_nine, self.rsi, self.ema20, self.ema50, current_position
        )

        # 检查是否有仓位
        if not self.position:
            # 没有仓位，检查买入或卖空信号
            if signal == 1 and is_safe_trading_time and not is_near_close:
                # 多头开仓信号
                # 计算仓位大小
                value = self.broker.get_value()
                size = int(value * self.p.position_size / current_price)

                if size > 0:
                    logger.info(
                        f'{self.data.datetime.datetime(0).isoformat()} 买入信号! 计数: {self.magic_nine.buy_count}, '
                        f'价格: {current_price:.2f}, 数量: {size}, RSI: {self.rsi[0]:.2f}')

                    # 下买入订单
                    self.order = self.buy(size=size)
                    self.position_size = size
                    self.is_short = False

            elif signal == -1 and is_safe_trading_time and not is_near_close:
                # 空头开仓信号
                # 计算仓位大小
                value = self.broker.get_value()
                size = int(value * self.p.position_size / current_price)

                if size > 0:
                    logger.info(
                        f'{self.data.datetime.datetime(0).isoformat()} 卖空信号! 计数: {self.magic_nine.sell_count}, '
                        f'价格: {current_price:.2f}, 数量: {size}, RSI: {self.rsi[0]:.2f}')

                    # 下卖空订单
                    self.order = self.sell(size=size)
                    self.position_size = size
                    self.is_short = True

                    # 使用风险管理器设置卖空止损价格
                    self.risk_manager.stop_loss = self.risk_manager.calculate_short_stop_loss(current_price)

        else:
            # 已有仓位，检查止损或平仓条件

            # 检查多头仓位
            if self.position.size > 0:
                # 使用风险管理器更新移动止损价格
                self.risk_manager.update_long_trailing_stop(current_price, self.buy_price)

                # 1. 多头止损检查
                if self.risk_manager.check_long_stop_loss(current_price):
                    self.order = self.sell(size=self.position_size)
                    self.position_size = 0
                    self.risk_manager.reset()
                    return

                # 2. 获利目标检查
                if self.risk_manager.check_long_profit_target(current_price, self.buy_price):
                    self.order = self.sell(size=self.position_size)
                    self.position_size = 0
                    self.risk_manager.reset()
                    return

                # 3. 检查多头平仓信号
                if signal == 0 and self.signal_generator.check_long_exit_signal(self.magic_nine):
                    logger.info(
                        f'{self.data.datetime.datetime(0).isoformat()} 卖出信号! 计数: {self.magic_nine.sell_count}, '
                        f'价格: {current_price:.2f}, 数量: {self.position_size}')

                    # 下卖出订单
                    self.order = self.sell(size=self.position_size)
                    self.position_size = 0
                    self.risk_manager.reset()

            # 检查空头仓位
            elif self.position.size < 0:
                # 1. 空头止损检查
                if self.risk_manager.check_short_stop_loss(current_price):
                    self.order = self.buy(size=self.position_size)
                    self.position_size = 0
                    self.risk_manager.reset()
                    self.is_short = False
                    return

                # 2. 移动止损更新
                self.risk_manager.update_short_trailing_stop(current_price, self.buy_price)

                # 3. 检查空头利润目标
                if self.risk_manager.check_short_profit_target(current_price, self.buy_price):
                    self.order = self.buy(size=self.position_size)
                    self.position_size = 0
                    self.risk_manager.reset()
                    self.is_short = False
                    return

                # 4. 检查空头平仓信号
                if signal == 0 and self.signal_generator.check_short_exit_signal(self.magic_nine):
                    logger.info(
                        f'{self.data.datetime.datetime(0).isoformat()} 买入信号! 计数: {self.magic_nine.buy_count}, '
                        f'价格: {current_price:.2f}, 数量: {self.position_size}')

                    # 下买入订单平空头仓位
                    self.order = self.buy(size=self.position_size)
                    self.position_size = 0
                    self.risk_manager.reset()
                    self.is_short = False
