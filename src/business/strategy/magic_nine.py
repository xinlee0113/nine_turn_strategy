import backtrader as bt
import logging
import pytz
from datetime import datetime, timedelta

from src.business.indicators import MagicNine
from src.business.indicators.kdj_bundle import KDJBundle
from src.business.strategy.signal_generator import SignalGenerator
from src.business.strategy.position_sizer import PositionSizer
from src.business.strategy.risk_manager import RiskManager

logger = logging.getLogger(__name__)

class MagicNineStrategy(bt.Strategy):
    """神奇九转交易策略 - 优化版本，支持双向交易（多空）"""
    params = (
        ('magic_period', 3),    # 神奇九转比较周期
        ('magic_count', 5),     # 神奇九转信号触发计数
        ('rsi_period', 14),     # RSI周期
        ('rsi_overbought', 70), # RSI超买值
        ('rsi_oversold', 30),   # RSI超卖值
        ('kdj_period', 9),      # KDJ指标周期
        ('kdj_fast', 3),        # KDJ快速线周期
        ('kdj_slow', 3),        # KDJ慢速线周期
        ('kdj_overbought', 80), # KDJ超买值
        ('kdj_oversold', 20),   # KDJ超卖值
        ('macd_fast', 12),      # MACD快线周期
        ('macd_slow', 26),      # MACD慢线周期
        ('macd_signal', 9),     # MACD信号线周期
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
        
        # 使用MACDHisto指标替换MACD - 直接提供柱状图数据
        self.macd = bt.indicators.MACDHisto(
            self.data, 
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow, 
            period_signal=self.p.macd_signal
        )
        
        # 添加KDJ指标
        self.kdj = KDJBundle(
            self.data,
            period=self.p.kdj_period,
            period_dfast=self.p.kdj_fast,
            period_dslow=self.p.kdj_slow
        )
        
        # 策略组件初始化
        self.signal_generator = SignalGenerator({
            'rsi_overbought': self.p.rsi_overbought,
            'rsi_oversold': self.p.rsi_oversold,
            'kdj_overbought': self.p.kdj_overbought,
            'kdj_oversold': self.p.kdj_oversold,
            'magic_count': self.p.magic_count,
            'enable_short': self.p.enable_short
        })
        
        self.position_sizer = PositionSizer({
            'position_pct': self.p.position_size
        })
        
        self.risk_manager = RiskManager({
            'stop_loss_pct': self.p.stop_loss_pct,
            'profit_target_pct': self.p.profit_target_pct,
            'trailing_pct': self.p.trailing_pct,
            'avoid_open_minutes': self.p.avoid_open_minutes,
            'avoid_close_minutes': self.p.avoid_close_minutes
        })
        
        logger.info(f"策略初始化完成 - 双向交易神奇九转模式 (比较周期:{self.p.magic_period}, 信号触发计数:{self.p.magic_count})")
        logger.info(f"添加MACD直方图和KDJ指标作为信号确认")
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
        
        # 处理市场交易时间
        market_time_info = self._get_market_time_info(current_time)
        et_hour = market_time_info['et_hour']
        et_minute = market_time_info['et_minute']
        is_trading_time = market_time_info['is_trading_time']
        is_safe_trading_time = market_time_info['is_safe_trading_time']
        is_near_close = market_time_info['is_near_close']
        minutes_since_open = market_time_info['minutes_since_open']
        minutes_before_close = market_time_info['minutes_before_close']
        
        # 记录详细的时间信息用于调试
        if len(self) % 100 == 0 or is_near_close:  # 每100个bar记录一次或接近收盘时记录
            time_format = "UTC" if market_time_info['is_utc_time'] else "ET"
            logger.info(f"时间检查: 原始时间={current_time.isoformat()}, 计算为美东时间:{et_hour}:{et_minute:02d}, "
                       f"时间格式:{time_format}, 交易时段:{is_trading_time}, 安全交易时段:{is_safe_trading_time}, "
                       f"开盘后分钟数:{minutes_since_open}, 收盘前分钟数:{minutes_before_close}, "
                       f"接近收盘:{is_near_close}, 夏令时:{market_time_info['is_dst']}")
        
        # 关闭前强制平仓检查
        if is_near_close and self.position:
            self._handle_force_close(current_time, et_hour, et_minute)
            return
        
        # 获取当前价格
        current_price = self.data.close[0]
        
        # 准备信号生成所需的数据
        signal_data = {
            'magic_nine_buy': self.magic_nine.lines.buy_setup[0],
            'magic_nine_sell': self.magic_nine.lines.sell_setup[0],
            'rsi': self.rsi[0],
            'ema20': self.ema20[0],
            'ema50': self.ema50[0],
            # 直接使用MACDHisto的histo线而不是计算差值
            'macd_histo': self.macd.lines.histo[0],  # 直接获取直方图数据
            'kdj_k': self.kdj.lines.K[0],
            'kdj_d': self.kdj.lines.D[0],
            'kdj_j': self.kdj.lines.J[0],
            'current_position': 1 if self.position.size > 0 else (-1 if self.position.size < 0 else 0),
            'price': current_price,
            'time_info': market_time_info
        }
        
        # 生成交易信号
        signal = self.signal_generator.generate_signal(signal_data)
        
        # 如果没有信号，检查风险管理
        if signal == 0 and self.position:
            # 准备风险管理所需的数据
            risk_data = {
                'current_position': 1 if self.position.size > 0 else (-1 if self.position.size < 0 else 0),
                'buy_price': self.buy_price,
                'current_price': current_price,
                'trailing_activated': self.trailing_activated,
                'stop_loss': self.stop_loss,
                'time_info': market_time_info
            }
            
            # 进行风险管理
            risk_action, new_stop_loss, trailing_activated = self.risk_manager.check_risk_management(risk_data)
            
            # 更新止损和移动止损状态
            if new_stop_loss is not None:
                self.stop_loss = new_stop_loss
            if trailing_activated is not None:
                self.trailing_activated = trailing_activated
            
            # 执行风险管理动作
            if risk_action == -1 and self.position.size > 0:  # 平多头仓位
                logger.info(f'{current_time.isoformat()} 风险管理触发平仓多头! 价格: {current_price:.2f}')
                self.order = self.sell(size=self.position.size)
                self.position_size = 0
                self.stop_loss = None
                return
            elif risk_action == 1 and self.position.size < 0:  # 平空头仓位
                logger.info(f'{current_time.isoformat()} 风险管理触发平仓空头! 价格: {current_price:.2f}')
                self.order = self.buy(size=-self.position.size)
                self.position_size = 0
                self.stop_loss = None
                self.is_short = False
                return
        
        # 如果没有持仓且有信号，计算仓位并执行
        if not self.position and signal != 0 and is_safe_trading_time and not is_near_close:
            # 准备仓位计算所需的数据
            position_data = {
                'cash': self.broker.get_cash(),
                'equity': self.broker.get_value(),
                'price': current_price,
                'current_position': 0
            }
            
            # 计算仓位大小
            size = self.position_sizer.calculate_position(signal, position_data)
            
            if size > 0:  # 买入信号
                logger.info(f'{current_time.isoformat()} 买入信号! 计数: {self.magic_nine.buy_count}, '
                         f'价格: {current_price:.2f}, 数量: {size}, RSI: {self.rsi[0]:.2f}')
                
                # 下买入订单
                self.order = self.buy(size=size)
                self.position_size = size
                self.is_short = False
                self.stop_loss = current_price * (1 - self.p.stop_loss_pct / 100)
                
            elif size < 0 and self.p.enable_short:  # 卖空信号
                size = abs(size)  # 转为正数
                logger.info(f'{current_time.isoformat()} 卖空信号! 计数: {self.magic_nine.sell_count}, '
                         f'价格: {current_price:.2f}, 数量: {size}, RSI: {self.rsi[0]:.2f}')
                
                # 下卖空订单
                self.order = self.sell(size=size)
                self.position_size = size
                self.is_short = True
                self.stop_loss = current_price * (1 + self.p.stop_loss_pct / 100)
    
    def _get_market_time_info(self, current_time):
        """处理市场交易时间相关信息"""
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
        
        # 判断是否在交易时段 (美东时间9:30-16:00)，并避开开盘和收盘的指定分钟
        is_trading_time = (9 < et_hour < 16) or (et_hour == 9 and et_minute >= 30) or (et_hour == 16 and et_minute == 0)
        is_safe_trading_time = is_trading_time and minutes_since_open >= self.p.avoid_open_minutes and minutes_before_close >= self.p.avoid_close_minutes
        
        # 判断是否接近美股收盘时间 (美东时间15:45-16:00)
        is_near_close = (et_hour == 15 and et_minute >= 45) or et_hour == 16
        
        return {
            'et_hour': et_hour,
            'et_minute': et_minute,
            'is_utc_time': is_utc_time,
            'is_dst': is_dst,
            'is_trading_time': is_trading_time,
            'is_safe_trading_time': is_safe_trading_time,
            'is_near_close': is_near_close,
            'minutes_since_open': minutes_since_open,
            'minutes_before_close': minutes_before_close
        }
    
    def _handle_force_close(self, current_time, et_hour, et_minute):
        """收盘前强制平仓处理"""
        if self.position.size > 0:  # 多头持仓
            logger.info(f'{current_time.isoformat()} 收盘前强制平仓多头! 价格: {self.data.close[0]:.2f}, ET时间约: {et_hour}:{et_minute:02d}')
            self.order = self.sell(size=self.position.size)
            self.position_size = 0
            self.stop_loss = None
        elif self.position.size < 0:  # 空头持仓
            logger.info(f'{current_time.isoformat()} 收盘前强制平仓空头! 价格: {self.data.close[0]:.2f}, ET时间约: {et_hour}:{et_minute:02d}')
            self.order = self.buy(size=-self.position.size)
            self.position_size = 0
            self.stop_loss = None
            self.is_short = False 