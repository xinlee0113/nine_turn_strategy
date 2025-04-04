import backtrader as bt
import logging
from src.indicators import MagicNine, RSIBundle, KDJBundle

logger = logging.getLogger(__name__)

class MagicNineStrategyWithAdvancedStopLoss(bt.Strategy):
    """神奇九转交易策略 - 高级止损版本，包含ATR止损和追踪止损，支持双向交易（多空）"""
    params = (
        ('magic_period', 2),     # 神奇九转比较周期，默认改为2使信号更频繁
        ('magic_count', 5),      # 神奇九转信号触发计数，默认改为5增加交易次数
        ('rsi_oversold', 30),    # RSI超卖值
        ('rsi_overbought', 70),  # RSI超买值
        ('kdj_oversold', 20),    # KDJ超卖值
        ('kdj_overbought', 80),  # KDJ超买值
        ('macd_signal', 0),      # MACD信号线
        ('atr_period', 14),      # ATR周期
        ('atr_multiplier', 2.5), # ATR乘数，用于设置止损距离
        ('long_atr_multiplier', 2.5),  # 多头ATR乘数
        ('short_atr_multiplier', 3.2), # 空头ATR乘数，更大以提供更宽松的止损空间
        ('trailing_stop', True), # 是否启用追踪止损
        ('max_loss_pct', 3.0),   # 最大止损百分比，作为上限
        ('long_max_loss_pct', 3.0),  # 多头最大止损百分比
        ('short_max_loss_pct', 4.0), # 空头最大止损百分比，更大以适应空头波动
        ('min_profit_pct', 1.0), # 追踪止损启动的最小盈利百分比
        ('long_min_profit_pct', 1.0),  # 多头追踪止损启动的最小盈利百分比
        ('short_min_profit_pct', 1.5), # 空头追踪止损启动的最小盈利百分比，更大以确保利润
        ('enable_short', True),  # 是否允许做空
        ('position_pct', 0.95),  # 使用资金的百分比，默认95%
        ('short_volatility_factor', 1.2),  # 空头波动因子，用于调整空头止损计算
        ('max_holding_periods', 20),  # 最大持有周期，超过此期限考虑强制平仓
    )
    
    def __init__(self):
        """初始化策略"""
        # 订单和交易状态
        self.order = None
        self.buy_price = None
        self.buy_comm = None
        self.position_size = 0
        self.stop_loss_price = None
        self.highest_price = None  # 追踪多头止损的最高价
        self.lowest_price = None   # 追踪空头止损的最低价
        self.is_short = False      # 标记是否为空头仓位
        self.trade_count = 0       # 交易计数器
        self.long_trades = 0       # 多头交易计数
        self.short_trades = 0      # 空头交易计数
        self.profitable_trades = 0 # 盈利交易计数
        self.losing_trades = 0     # 亏损交易计数
        self.long_profits = 0.0    # 多头总盈利
        self.long_losses = 0.0     # 多头总亏损
        self.short_profits = 0.0   # 空头总盈利
        self.short_losses = 0.0    # 空头总亏损
        self.total_profit = 0.0    # 总盈利
        self.total_loss = 0.0      # 总亏损
        self.position_entry_bar = 0  # 记录入场时的bar序号，用于跟踪持仓时间
        
        # 计算指标 - 神奇九转
        self.magic_nine = MagicNine(self.data, period=self.p.magic_period)
        
        # ATR指标，用于动态止损
        self.atr = bt.indicators.ATR(self.data, period=self.p.atr_period)
        
        # 趋势指标
        self.ema20 = bt.indicators.ExponentialMovingAverage(self.data.close, period=20)
        self.ema50 = bt.indicators.ExponentialMovingAverage(self.data.close, period=50)
        
        # 保留这些指标以便观察，但不用于信号判断
        self.rsi = RSIBundle(self.data)
        self.kdj = KDJBundle(self.data)
        self.macd = bt.indicators.MACDHisto(self.data,
                                      period_me1=12, 
                                      period_me2=26, 
                                      period_signal=9)
        
        # 使用更详细的多头/空头参数
        # 如果没有特别指定多头/空头的参数，则使用通用参数
        if self.p.long_atr_multiplier == self.p.short_atr_multiplier:
            self.p.long_atr_multiplier = self.p.atr_multiplier
            self.p.short_atr_multiplier = self.p.atr_multiplier
            
        if self.p.long_max_loss_pct == self.p.short_max_loss_pct:
            self.p.long_max_loss_pct = self.p.max_loss_pct
            self.p.short_max_loss_pct = self.p.max_loss_pct
            
        if self.p.long_min_profit_pct == self.p.short_min_profit_pct:
            self.p.long_min_profit_pct = self.p.min_profit_pct
            self.p.short_min_profit_pct = self.p.min_profit_pct
        
        logger.info(f"策略初始化完成 - 高级止损的神奇九转模式 (比较周期:{self.p.magic_period}, "
                  f"信号触发计数:{self.p.magic_count}, ATR周期:{self.p.atr_period}, "
                  f"多头ATR乘数:{self.p.long_atr_multiplier}, 空头ATR乘数:{self.p.short_atr_multiplier}, "
                  f"多头最大止损:{self.p.long_max_loss_pct}%, 空头最大止损:{self.p.short_max_loss_pct}%, "
                  f"空头波动因子:{self.p.short_volatility_factor}, 最大持有周期:{self.p.max_holding_periods}, "
                  f"追踪止损:{self.p.trailing_stop}, 做空交易:{self.p.enable_short})")
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            self.trade_count += 1  # 增加交易计数
            
            if order.isbuy():
                buy_or_cover = "买入" if not self.is_short else "平空买入"
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} {buy_or_cover}执行: 价格: {order.executed.price:.2f}, '
                         f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}, 交易#: {self.trade_count}')
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
                
                # 如果是买入平空仓
                if self.is_short:
                    # 计算交易利润
                    if self.buy_price:
                        profit = (self.buy_price - order.executed.price) * order.executed.size
                        profit_pct = (self.buy_price / order.executed.price - 1) * 100
                        
                        # 记录空头交易结果
                        if profit > 0:
                            self.profitable_trades += 1
                            self.short_profits += profit
                            self.total_profit += profit
                            logger.info(f'{self.data.datetime.datetime(0).isoformat()} 空头交易盈利: {profit:.2f} ({profit_pct:.2f}%)')
                        else:
                            self.losing_trades += 1
                            self.short_losses += abs(profit)
                            self.total_loss += abs(profit)
                            logger.info(f'{self.data.datetime.datetime(0).isoformat()} 空头交易亏损: {profit:.2f} ({profit_pct:.2f}%)')
                    
                    # 平仓后重置标志和止损
                    self.is_short = False
                    self.stop_loss_price = None
                    self.lowest_price = None
                else:
                    # 记录多头入场时间
                    self.position_entry_bar = len(self.data)
                    self.long_trades += 1
                    
                    # 设置多头初始止损价格
                    atr_value = self.atr[0]
                    stop_loss_distance = atr_value * self.p.long_atr_multiplier
                    
                    # 确保止损不超过最大止损百分比
                    max_loss_distance = self.buy_price * self.p.long_max_loss_pct / 100
                    stop_loss_distance = min(stop_loss_distance, max_loss_distance)
                    
                    self.stop_loss_price = self.buy_price - stop_loss_distance
                    self.highest_price = self.buy_price
                    
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 设置多头初始止损: {self.stop_loss_price:.2f} '
                             f'(ATR: {atr_value:.2f}, 距离: {stop_loss_distance:.2f}, 止损幅度: {(stop_loss_distance/self.buy_price*100):.2f}%)')
                
            elif order.issell():
                sell_or_short = "卖出" if not self.is_short else "卖空"
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} {sell_or_short}执行: 价格: {order.executed.price:.2f}, '
                         f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}, 交易#: {self.trade_count}')
                
                # 如果是卖出平多仓
                if not self.is_short and self.buy_price is not None:
                    profit = (order.executed.price - self.buy_price) * order.executed.size
                    profit_pct = (order.executed.price / self.buy_price - 1) * 100
                    
                    # 记录多头交易结果
                    if profit > 0:
                        self.profitable_trades += 1
                        self.long_profits += profit
                        self.total_profit += profit
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 多头交易盈利: {profit:.2f} ({profit_pct:.2f}%)')
                    else:
                        self.losing_trades += 1
                        self.long_losses += abs(profit)
                        self.total_loss += abs(profit)
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 多头交易亏损: {profit:.2f} ({profit_pct:.2f}%)')
                    
                    # 重置止损价格
                    self.stop_loss_price = None
                    self.highest_price = None
                elif not self.is_short:
                    # 新建空头仓位
                    self.is_short = True
                    self.buy_price = order.executed.price
                    self.buy_comm = order.executed.comm
                    self.short_trades += 1
                    
                    # 记录空头入场时间
                    self.position_entry_bar = len(self.data)
                    
                    # 设置空头初始止损价格 - 增加波动性因子
                    atr_value = self.atr[0] * self.p.short_volatility_factor  # 应用波动因子
                    stop_loss_distance = atr_value * self.p.short_atr_multiplier
                    
                    # 确保止损不超过最大止损百分比
                    max_loss_distance = self.buy_price * self.p.short_max_loss_pct / 100
                    stop_loss_distance = min(stop_loss_distance, max_loss_distance)
                    
                    self.stop_loss_price = self.buy_price + stop_loss_distance
                    self.lowest_price = self.buy_price
                    
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 设置空头初始止损: {self.stop_loss_price:.2f} '
                             f'(ATR: {atr_value:.2f}, 距离: {stop_loss_distance:.2f}, 止损幅度: {(stop_loss_distance/self.buy_price*100):.2f}%)')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f'{self.data.datetime.datetime(0).isoformat()} 订单被拒绝/取消/保证金不足: {order.status}')
        
        self.order = None
    
    def notify_trade(self, trade):
        """交易结果通知"""
        if trade.isclosed:
            logger.info(f'{self.data.datetime.datetime(0).isoformat()} 交易利润, 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')
            
            # 统计交易胜率
            if self.trade_count > 0:
                win_rate = (self.profitable_trades / self.trade_count) * 100
                long_win_rate = (self.long_profits / max(1, self.long_trades)) if self.long_trades > 0 else 0
                short_win_rate = (self.short_profits / max(1, self.short_trades)) if self.short_trades > 0 else 0
                
                avg_profit = self.total_profit / max(1, self.profitable_trades)
                avg_loss = self.total_loss / max(1, self.losing_trades)
                profit_factor = self.total_profit / max(0.01, self.total_loss)
                
                # 每10笔交易记录一次统计或在交易结束时记录
                if self.trade_count % 10 == 0 or not self.position:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 交易统计 - '
                             f'胜率: {win_rate:.2f}%, 交易数: {self.trade_count}, '
                             f'多/空比: {self.long_trades}/{self.short_trades}, '
                             f'多头盈利/亏损: {self.long_profits:.2f}/{self.long_losses:.2f}, '
                             f'空头盈利/亏损: {self.short_profits:.2f}/{self.short_losses:.2f}, '
                             f'平均盈利: {avg_profit:.2f}, 平均亏损: {avg_loss:.2f}, 盈亏比: {profit_factor:.2f}')
    
    def next(self):
        """主策略逻辑"""
        # 如果有未完成的订单，不进行操作
        if self.order:
            return
            
        # 获取当前时间
        current_time = self.data.datetime.datetime(0)
        
        # 检查是否接近收盘时间或已过收盘时间
        # 考虑时区差异，将任何时间格式转换为美东时间后再判断
        # UTC比美东时间快4-5小时（取决于是否为夏令时）

        # 判断月份确定是否是夏令时（粗略判断，美国夏令时一般3月至11月）
        is_dst = 3 <= current_time.month <= 11

        # 计算美东时间
        et_hour = current_time.hour
        et_minute = current_time.minute

        # 如果可能是UTC时间，转换为美东时间
        if current_time.hour >= 19:  # 可能是UTC时间
            if is_dst:
                # 夏令时：UTC-4
                et_hour = (current_time.hour - 4) % 24
            else:
                # 标准时：UTC-5
                et_hour = (current_time.hour - 5) % 24

        # 根据转换后的美东时间判断是否接近收盘
        is_near_close = (et_hour == 15 and et_minute >= 45) or et_hour >= 16

        # 如果接近收盘且有持仓，强制平仓
        if is_near_close and self.position:
            if self.position.size > 0:  # 多头持仓
                logger.info(f'{current_time.isoformat()} 收盘前强制平仓多头! 价格: {self.data.close[0]:.2f}, ET时间约: {et_hour}:{et_minute}')
                self.order = self.sell(size=self.position_size)
                self.position_size = 0
                self.stop_loss_price = None
                self.highest_price = None
                return
            elif self.position.size < 0:  # 空头持仓
                logger.info(f'{current_time.isoformat()} 收盘前强制平仓空头! 价格: {self.data.close[0]:.2f}, ET时间约: {et_hour}:{et_minute}')
                self.order = self.buy(size=self.position_size)
                self.position_size = 0
                self.stop_loss_price = None
                self.lowest_price = None
                self.is_short = False
                return
        
        # 获取当前价格
        current_price = self.data.close[0]
        
        # 每50个周期记录一次调试信息（减少日志量）
        if len(self.data) % 50 == 0:
            trend_direction = "上升" if self.ema20[0] > self.ema50[0] else "下降"
            position_type = "空头" if self.is_short else "多头" if self.position else "无持仓"
            current_bar = len(self.data)
            holding_periods = current_bar - self.position_entry_bar if self.position else 0
            
            logger.info(f'{self.data.datetime.datetime(0).isoformat()} 调试信息: '
                     f'价格: {current_price:.2f}, '
                     f'买入信号: {self.magic_nine.lines.buy_signal[0]}, '
                     f'卖出信号: {self.magic_nine.lines.sell_signal[0]}, '
                     f'买入计数: {self.magic_nine.lines.buy_setup[0]}, '
                     f'卖出计数: {self.magic_nine.lines.sell_setup[0]}, '
                     f'趋势: {trend_direction}, '
                     f'RSI: {self.rsi.lines.rsi6[0]:.2f}, '
                     f'持仓类型: {position_type}, '
                     f'持仓大小: {self.position.size if self.position else 0}, '
                     f'持仓周期: {holding_periods}')
        
        # 检查是否有仓位 - 使用position.size更准确地判断仓位状态
        if not self.position or self.position.size == 0:
            # 没有仓位，检查买入或卖空信号
            
            # 多头信号条件：只要有买入信号就交易
            if self.magic_nine.lines.buy_signal[0] >= 1:
                # 记录趋势和RSI信息，但不作为强制条件
                trend_up = self.ema20[0] > self.ema50[0]
                current_rsi = self.rsi.lines.rsi6[0]
                
                # 极度超买时避免买入
                rsi_too_high = current_rsi > 85  # 只在极端情况下禁止买入
                
                # 只有RSI极度超买时才不买入
                if not rsi_too_high:
                    # 计算仓位大小
                    value = self.broker.get_value()
                    size = int(value * self.p.position_pct / current_price)  # 使用设定的资金比例
                    
                    if size > 0:
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 买入执行前检查 - 资金: {value:.2f}, 计算仓位: {size}')
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 买入信号! 神奇九转计数: {self.magic_nine.lines.buy_setup[0]}, '
                                 f'价格: {current_price:.2f}, 数量: {size}, RSI: {current_rsi:.2f}, 趋势上升: {trend_up}')
                        
                        # 确保任何旧的标志被重置
                        self.is_short = False
                        
                        # 下买入订单
                        self.order = self.buy(size=size)
                        self.position_size = size
                    else:
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 买入信号存在但计算的仓位大小为0，资金: {value:.2f}')
                else:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 买入信号存在但RSI过高: {current_rsi:.2f}')
            
            # 空头信号条件：只要有卖出信号就交易
            elif self.magic_nine.lines.sell_signal[0] >= 1 and self.p.enable_short:
                # 记录趋势和RSI信息，但不作为强制条件
                trend_down = self.ema20[0] < self.ema50[0]
                current_rsi = self.rsi.lines.rsi6[0]
                
                # 极度超卖时避免卖空
                rsi_too_low = current_rsi < 15  # 只在极端情况下禁止卖空
                
                # 只有RSI极度超卖时才不卖空
                if not rsi_too_low:
                    # 计算仓位大小
                    value = self.broker.get_value()
                    size = int(value * self.p.position_pct / current_price)  # 使用设定的资金比例
                    
                    if size > 0:
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖空执行前检查 - 资金: {value:.2f}, 计算仓位: {size}')
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖空信号! 神奇九转计数: {self.magic_nine.lines.sell_setup[0]}, '
                                 f'价格: {current_price:.2f}, 数量: {size}, RSI: {current_rsi:.2f}, 趋势下降: {trend_down}')
                        
                        # 确保正确设置空头标志
                        self.is_short = True
                        
                        # 下卖空订单
                        self.order = self.sell(size=size)
                        self.position_size = size
                    else:
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖空信号存在但计算的仓位大小为0，资金: {value:.2f}')
                else:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖空信号存在但RSI过低: {current_rsi:.2f}')
        
        else:
            # 已有仓位，检查是多头还是空头
            current_bar = len(self.data)
            holding_periods = current_bar - self.position_entry_bar
            
            # 检查最大持仓时间限制
            max_holding_reached = holding_periods >= self.p.max_holding_periods
            
            if self.position.size > 0:  # 多头仓位
                # 多头仓位的移动止损逻辑
                if self.p.trailing_stop and self.highest_price is not None and self.stop_loss_price is not None:
                    # 更新最高价
                    if current_price > self.highest_price:
                        old_highest = self.highest_price
                        self.highest_price = current_price
                        
                        # 计算当前盈利百分比
                        profit_pct = (current_price / self.buy_price - 1) * 100
                        
                        # 如果盈利超过最小盈利百分比，更新止损价格
                        if profit_pct >= self.p.long_min_profit_pct:
                            # 计算新的止损价格
                            atr_value = self.atr[0]
                            stop_loss_distance = atr_value * self.p.long_atr_multiplier
                            new_stop_loss = self.highest_price - stop_loss_distance
                            
                            # 只有当新止损价格高于原止损价格时才更新
                            if new_stop_loss > self.stop_loss_price:
                                old_stop_loss = self.stop_loss_price
                                self.stop_loss_price = new_stop_loss
                                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 更新多头追踪止损: {old_stop_loss:.2f} -> {new_stop_loss:.2f} '
                                         f'(最高价: {old_highest:.2f} -> {self.highest_price:.2f}, 盈利: {profit_pct:.2f}%)')
                
                # 检查多头止损条件
                if self.stop_loss_price is not None and current_price <= self.stop_loss_price:
                    # 触发多头止损
                    loss_pct = (self.buy_price - current_price) / self.buy_price * 100.0
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 多头止损触发! 亏损: {loss_pct:.2f}%, '
                             f'价格: {current_price:.2f}, 止损价: {self.stop_loss_price:.2f}, 数量: {self.position_size}, '
                             f'持仓周期: {holding_periods}')
                    
                    # 下卖出订单
                    self.order = self.sell(size=self.position_size)
                    
                    # 重置变量
                    self.position_size = 0
                    self.stop_loss_price = None
                    self.highest_price = None
                    self.buy_price = None
                
                # 检查最大持仓时间限制
                elif max_holding_reached:
                    # 确保buy_price不为None
                    if self.buy_price is not None:
                        # 多头盈利计算: 当前价格/入场价格-1
                        profit_pct = (current_price / self.buy_price - 1) * 100
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 多头最大持仓时间到达! 持仓: {holding_periods}, '
                                f'当前盈亏: {profit_pct:.2f}%, 强制平仓')
                    else:
                        logger.warning(f'{self.data.datetime.datetime(0).isoformat()} 多头最大持仓时间到达但buy_price为None! 持仓: {holding_periods}, 强制平仓')
                    
                    # 下卖出订单
                    self.order = self.sell(size=self.position_size)
                    
                    # 重置变量
                    self.position_size = 0
                    self.stop_loss_price = None
                    self.highest_price = None
                    self.buy_price = None
                
                # 检查多头卖出信号
                elif self.magic_nine.lines.sell_signal[0] >= 1:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖出信号! 神奇九转计数: {self.magic_nine.lines.sell_setup[0]}, '
                             f'价格: {current_price:.2f}, 数量: {self.position_size}')
                    
                    # 下卖出订单
                    self.order = self.sell(size=self.position_size)
                    
                    # 重置变量
                    self.position_size = 0
                    self.stop_loss_price = None
                    self.highest_price = None
                    self.buy_price = None
            
            elif self.position.size < 0:  # 空头仓位
                # 确保空头标志正确设置
                if not self.is_short:
                    logger.warning(f'{self.data.datetime.datetime(0).isoformat()} 修正空头状态标志，发现仓位数量为负但标志未设置')
                    self.is_short = True
                    
                # 空头仓位的移动止损逻辑 - 强化优化
                if self.p.trailing_stop and self.lowest_price is not None and self.stop_loss_price is not None:
                    # 更新最低价
                    if current_price < self.lowest_price:
                        old_lowest = self.lowest_price
                        self.lowest_price = current_price
                        
                        # 计算当前盈利百分比 (空头是反向的)
                        profit_pct = (self.buy_price / current_price - 1) * 100
                        
                        # 如果盈利超过最小盈利百分比，更新止损价格
                        if profit_pct >= self.p.short_min_profit_pct:
                            # 计算新的止损价格，应用波动因子以提供更宽松的空间
                            atr_value = self.atr[0] * self.p.short_volatility_factor
                            stop_loss_distance = atr_value * self.p.short_atr_multiplier
                            new_stop_loss = self.lowest_price + stop_loss_distance
                            
                            # 只有当新止损价格低于原止损价格时才更新
                            if new_stop_loss < self.stop_loss_price:
                                old_stop_loss = self.stop_loss_price
                                self.stop_loss_price = new_stop_loss
                                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 更新空头追踪止损: {old_stop_loss:.2f} -> {new_stop_loss:.2f} '
                                         f'(最低价: {old_lowest:.2f} -> {self.lowest_price:.2f}, 盈利: {profit_pct:.2f}%)')
                
                # 检查空头止损条件
                if self.stop_loss_price is not None and current_price >= self.stop_loss_price:
                    # 触发空头止损
                    loss_pct = (current_price - self.buy_price) / self.buy_price * 100.0
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 空头止损触发! 亏损: {loss_pct:.2f}%, '
                             f'价格: {current_price:.2f}, 止损价: {self.stop_loss_price:.2f}, 数量: {abs(self.position_size)}, '
                             f'持仓周期: {holding_periods}')
                    
                    # 下买入订单平空仓
                    self.order = self.buy(size=abs(self.position_size))
                    
                    # 重置变量
                    self.position_size = 0
                    self.stop_loss_price = None
                    self.lowest_price = None
                    self.buy_price = None
                    self.is_short = False
                
                # 检查最大持仓时间限制
                elif max_holding_reached:
                    # 确保buy_price不为None
                    if self.buy_price is not None:
                        # 空头盈利计算: 入场价格/当前价格-1 (与多头相反)
                        profit_pct = (self.buy_price / current_price - 1) * 100
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 空头最大持仓时间到达! 持仓: {holding_periods}, '
                                f'当前盈亏: {profit_pct:.2f}%, 强制平仓')
                    else:
                        logger.warning(f'{self.data.datetime.datetime(0).isoformat()} 空头最大持仓时间到达但buy_price为None! 持仓: {holding_periods}, 强制平仓')
                    
                    # 下买入订单平空仓
                    self.order = self.buy(size=abs(self.position_size))
                    
                    # 重置变量
                    self.position_size = 0
                    self.stop_loss_price = None
                    self.lowest_price = None
                    self.buy_price = None
                    self.is_short = False
                
                # 检查空头买入信号
                elif self.magic_nine.lines.buy_signal[0] >= 1:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 买入信号! 神奇九转计数: {self.magic_nine.lines.buy_setup[0]}, '
                             f'价格: {current_price:.2f}, 数量: {abs(self.position_size)}')
                    
                    # 下买入订单平空仓
                    self.order = self.buy(size=abs(self.position_size))
                    
                    # 重置变量
                    self.position_size = 0
                    self.stop_loss_price = None
                    self.lowest_price = None
                    self.buy_price = None
                    self.is_short = False
            else:
                # 理论上不会到这里，因为我们前面已经检查了position.size，但为了健壮性添加这个分支
                logger.warning(f'{self.data.datetime.datetime(0).isoformat()} 检测到异常持仓状态: {self.position.size}')
                
                # 重置所有状态变量
                self.position_size = 0
                self.stop_loss_price = None
                self.highest_price = None
                self.lowest_price = None
                self.buy_price = None
                self.is_short = False 