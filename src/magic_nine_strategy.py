import backtrader as bt
import logging
import pytz
from datetime import datetime, timedelta
from src.indicators import MagicNine, RSIBundle, KDJBundle

logger = logging.getLogger(__name__)

class MagicNineStrategy(bt.Strategy):
    """神奇九转交易策略 - 优化版本，支持双向交易（多空）"""
    params = (
        ('magic_period', 3),    # 神奇九转比较周期
        ('magic_count', 5),     # 神奇九转信号触发计数
        ('rsi_period', 14),     # RSI周期
        ('rsi_overbought', 70), # RSI超买值
        ('rsi_oversold', 30),   # RSI超卖值
        ('stop_loss_pct', 0.8), # 止损百分比
        ('profit_target_pct', 2.0), # 利润目标百分比
        ('trailing_pct', 1.0),  # 移动止损激活百分比
        ('position_size', 0.95), # 仓位大小(占总资金比例)
        ('enable_short', True),  # 是否允许做空
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
        self.stop_loss = None
        self.trailing_activated = False
        self.is_short = False  # 标记当前是否为空头仓位
        
        # 指标初始化
        self.magic_nine = MagicNine(self.data, period=self.p.magic_period)
        self.rsi = bt.indicators.RSI(self.data, period=self.p.rsi_period)
        self.ema20 = bt.indicators.EMA(self.data, period=20)
        self.ema50 = bt.indicators.EMA(self.data, period=50)
        
        logger.info(f"策略初始化完成 - 双向交易神奇九转模式 (比较周期:{self.p.magic_period}, 信号触发计数:{self.p.magic_count})")
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
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 空头交易利润: {profit:.2f}, 收益率: {profit_pct:.2f}%')
                self.is_short = False
            
            logger.info(f'{self.data.datetime.datetime(0).isoformat()} 交易利润, 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')
    
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
                logger.info(f'{current_time.isoformat()} 收盘前强制平仓多头! 价格: {self.data.close[0]:.2f}, ET时间约: {et_hour}:{et_minute:02d}')
                self.order = self.sell(size=self.position_size)
                self.position_size = 0
                self.stop_loss = None
                return
            elif self.position.size < 0:  # 空头持仓
                logger.info(f'{current_time.isoformat()} 收盘前强制平仓空头! 价格: {self.data.close[0]:.2f}, ET时间约: {et_hour}:{et_minute:02d}')
                self.order = self.buy(size=self.position_size)
                self.position_size = 0
                self.stop_loss = None
                self.is_short = False
                return
        
        # 获取当前价格
        current_price = self.data.close[0]
        
        # 检查是否有仓位
        if not self.position:
            # 没有仓位，检查买入或卖空信号
            
            # 多头信号条件：买入计数达标且EMA20>EMA50（上升趋势）且RSI不超买
            if self.magic_nine.lines.buy_setup[0] >= self.p.magic_count:
                # 确认趋势方向 (EMA20 > EMA50 为上升趋势)
                trend_up = self.ema20[0] > self.ema50[0]
                
                # RSI不在超买区域 (避免在高点买入)
                rsi_ok = self.rsi[0] < self.p.rsi_overbought
                
                # 同时满足条件时买入，但不在收盘前建立新仓位，同时避开开盘和收盘的30分钟
                if trend_up and rsi_ok and is_safe_trading_time and not is_near_close:
                    # 计算仓位大小
                    value = self.broker.get_value()
                    size = int(value * self.p.position_size / current_price)
                    
                    if size > 0:
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 买入信号! 计数: {self.magic_nine.buy_count}, '
                                 f'价格: {current_price:.2f}, 数量: {size}, RSI: {self.rsi[0]:.2f}')
                        
                        # 下买入订单
                        self.order = self.buy(size=size)
                        self.position_size = size
                        self.is_short = False
            
            # 空头信号条件：卖出计数达标且EMA20<EMA50（下降趋势）且RSI不超卖
            elif self.magic_nine.lines.sell_setup[0] >= self.p.magic_count and self.p.enable_short:
                # 确认趋势方向 (EMA20 < EMA50 为下降趋势)
                trend_down = self.ema20[0] < self.ema50[0]
                
                # RSI不在超卖区域 (避免在低点卖空)
                rsi_ok = self.rsi[0] > self.p.rsi_oversold
                
                # 同时满足条件时卖空，但不在收盘前建立新仓位，同时避开开盘和收盘的30分钟
                if trend_down and rsi_ok and is_safe_trading_time and not is_near_close:
                    # 计算仓位大小
                    value = self.broker.get_value()
                    size = int(value * self.p.position_size / current_price)
                    
                    if size > 0:
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖空信号! 计数: {self.magic_nine.sell_count}, '
                                 f'价格: {current_price:.2f}, 数量: {size}, RSI: {self.rsi[0]:.2f}')
                        
                        # 下卖空订单
                        self.order = self.sell(size=size)
                        self.position_size = size
                        self.is_short = True
                        
                        # 记录卖空价格用于计算止损
                        self.stop_loss = current_price * (1 + self.p.stop_loss_pct / 100)
        
        else:
            # 已有仓位，检查止损或平仓条件
            
            # 检查多头仓位
            if self.position.size > 0:
                # 计算移动止损价格
                if self.trailing_activated:
                    # 已激活移动止损
                    trail_price = current_price * (1 - self.p.trailing_pct / 100)
                    if trail_price > self.stop_loss:
                        old_stop = self.stop_loss
                        self.stop_loss = trail_price
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 更新移动止损: {old_stop:.2f} -> {trail_price:.2f}')
                else:
                    # 判断是否达到移动止损激活条件
                    profit_pct = (current_price / self.buy_price - 1) * 100
                    if profit_pct >= self.p.trailing_pct:
                        self.trailing_activated = True
                        trail_price = current_price * (1 - self.p.trailing_pct / 100)
                        if self.stop_loss is None or trail_price > self.stop_loss:
                            old_stop = self.stop_loss if self.stop_loss is not None else 0
                            self.stop_loss = trail_price
                            logger.info(f'{self.data.datetime.datetime(0).isoformat()} 激活移动止损: {old_stop:.2f} -> {trail_price:.2f}')
                
                # 1. 多头止损检查
                if self.stop_loss is not None and current_price <= self.stop_loss:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 多头止损触发! 价格: {current_price:.2f}, 止损价: {self.stop_loss:.2f}')
                    self.order = self.sell(size=self.position_size)
                    self.position_size = 0
                    self.stop_loss = None
                    self.trailing_activated = False
                    return
                
                # 2. 获利目标检查
                profit_pct = (current_price / self.buy_price - 1) * 100
                if profit_pct >= self.p.profit_target_pct:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 达到多头利润目标! 价格: {current_price:.2f}, '
                             f'买入价: {self.buy_price:.2f}, 利润: {profit_pct:.2f}%')
                    self.order = self.sell(size=self.position_size)
                    self.position_size = 0
                    self.stop_loss = None
                    self.trailing_activated = False
                    return
                
                # 3. 检查卖出信号作为多头平仓条件
                if self.magic_nine.lines.sell_setup[0] >= self.p.magic_count:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖出信号! 计数: {self.magic_nine.sell_count}, '
                             f'价格: {current_price:.2f}, 数量: {self.position_size}')
                    
                    # 下卖出订单
                    self.order = self.sell(size=self.position_size)
                    self.position_size = 0
                    self.stop_loss = None
                    self.trailing_activated = False
            
            # 检查空头仓位
            elif self.position.size < 0:
                # 1. 空头止损检查
                if self.stop_loss is not None and current_price >= self.stop_loss:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 空头止损触发! 价格: {current_price:.2f}, 止损价: {self.stop_loss:.2f}')
                    self.order = self.buy(size=self.position_size)
                    self.position_size = 0
                    self.stop_loss = None
                    self.is_short = False
                    return
                
                # 2. 移动止损更新
                if self.trailing_activated:
                    # 已激活移动止损
                    trail_price = current_price * (1 + self.p.trailing_pct / 100)
                    if trail_price < self.stop_loss:
                        old_stop = self.stop_loss
                        self.stop_loss = trail_price
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 更新空头移动止损: {old_stop:.2f} -> {trail_price:.2f}')
                else:
                    # 判断是否达到移动止损激活条件
                    profit_pct = (self.buy_price / current_price - 1) * 100
                    if profit_pct >= self.p.trailing_pct:
                        self.trailing_activated = True
                        trail_price = current_price * (1 + self.p.trailing_pct / 100)
                        if trail_price < self.stop_loss:
                            old_stop = self.stop_loss
                            self.stop_loss = trail_price
                            logger.info(f'{self.data.datetime.datetime(0).isoformat()} 激活空头移动止损: {old_stop:.2f} -> {trail_price:.2f}')
                
                # 3. 检查空头利润目标
                profit_pct = (self.buy_price / current_price - 1) * 100
                if profit_pct >= self.p.profit_target_pct:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 达到空头利润目标! 价格: {current_price:.2f}, '
                             f'卖出价: {self.buy_price:.2f}, 利润: {profit_pct:.2f}%')
                    self.order = self.buy(size=self.position_size)
                    self.position_size = 0
                    self.stop_loss = None
                    self.is_short = False
                    return
                
                # 4. 检查买入信号作为空头平仓条件
                if self.magic_nine.lines.buy_setup[0] >= self.p.magic_count:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 买入信号! 计数: {self.magic_nine.buy_count}, '
                             f'价格: {current_price:.2f}, 数量: {self.position_size}')
                    
                    # 下买入订单平空头仓位
                    self.order = self.buy(size=self.position_size)
                    self.position_size = 0
                    self.stop_loss = None
                    self.trailing_activated = False
                    self.is_short = False 