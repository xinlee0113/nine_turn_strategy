import backtrader as bt
import logging
import numpy as np
from src.indicators import MagicNine, RSIBundle, KDJBundle

logger = logging.getLogger(__name__)

class MagicNineStrategyWithSmartStopLoss(bt.Strategy):
    """神奇九转交易策略 - 智能止损版本，包含波动性自适应、市场环境感知和时间衰减等功能，支持多空双向交易"""
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
        ('trailing_stop', True), # 是否启用追踪止损
        ('max_loss_pct', 3.0),   # 最大止损百分比，作为上限
        ('min_profit_pct', 1.0), # 追踪止损启动的最小盈利百分比
        ('time_decay', True),    # 是否启用时间衰减
        ('time_decay_days', 3),  # 时间衰减开始的天数(以5分钟k线计算，一天约有78个5分钟k线)
        ('volatility_adjust', True), # 是否根据波动性调整止损
        ('market_aware', True),  # 是否感知市场环境
        ('risk_aversion', 1.0),  # 风险规避系数(0.5-2.0)，较高的值增加止损紧密度
        ('enable_short', True),  # 是否允许做空交易
        ('position_pct', 0.95),  # 使用资金的百分比，默认95%
        ('short_atr_multiplier', 2.8), # 空头ATR乘数，默认略大于多头以提供更宽松的止损
        ('short_max_loss_pct', 3.5),   # 空头最大止损百分比，默认略大于多头
        ('short_min_profit_pct', 1.2),  # 空头追踪止损启动的最小盈利百分比，默认略大于多头
        ('short_volatility_factor', 1.2),  # 空头波动因子，用于进一步调整空头止损计算
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
        self.entry_time = None     # 入场时间
        self.bars_since_entry = 0  # 入场后经过的K线数量
        self.is_short = False      # 标记是否为空头仓位
        
        # 交易统计
        self.trade_count = 0
        self.long_trades = 0
        self.short_trades = 0
        self.profitable_trades = 0
        self.losing_trades = 0
        
        # 计算指标 - 神奇九转
        self.magic_nine = MagicNine(self.data, period=self.p.magic_period)
        
        # ATR指标，用于动态止损
        self.atr = bt.indicators.ATR(self.data, period=self.p.atr_period)
        
        # 波动率评估 - 使用ROC(变化率)指标的标准差来衡量
        self.price_roc = bt.indicators.ROC(self.data.close, period=1)  # 1周期的价格变化率
        self.volatility = bt.indicators.StdDev(self.price_roc, period=50, movav=bt.indicators.MovAv.EMA)
        
        # 市场趋势 - 使用两个不同周期的EMA的差值来判断
        self.ema20 = bt.indicators.EMA(self.data.close, period=20)
        self.ema50 = bt.indicators.EMA(self.data.close, period=50)
        self.market_trend = self.ema20 - self.ema50
        
        # 保留这些指标以便观察和进行条件判断
        self.rsi = RSIBundle(self.data)
        self.kdj = KDJBundle(self.data)
        self.macd = bt.indicators.MACDHisto(self.data,
                                      period_me1=12, 
                                      period_me2=26, 
                                      period_signal=9)
        
        logger.info(f"策略初始化完成 - 智能止损的神奇九转模式 (比较周期:{self.p.magic_period}, "
                  f"信号触发计数:{self.p.magic_count}, ATR周期:{self.p.atr_period}, "
                  f"多头ATR乘数:{self.p.atr_multiplier}, 空头ATR乘数:{self.p.short_atr_multiplier}, "
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
                self.entry_time = self.data.datetime.datetime(0)
                self.bars_since_entry = 0
                
                # 如果是买入平空仓
                if self.is_short:
                    # 计算交易利润
                    if self.buy_price and self.lowest_price is not None:  # 确保最低价不为None
                        profit = (self.lowest_price - order.executed.price) * order.executed.size
                        profit_pct = (self.lowest_price / order.executed.price - 1) * 100
                        
                        # 记录交易结果
                        if profit > 0:
                            self.profitable_trades += 1
                            logger.info(f'{self.data.datetime.datetime(0).isoformat()} 空头交易盈利: {profit:.2f} ({profit_pct:.2f}%)')
                        else:
                            self.losing_trades += 1
                            logger.info(f'{self.data.datetime.datetime(0).isoformat()} 空头交易亏损: {profit:.2f} ({profit_pct:.2f}%)')
                    else:
                        # 如果没有记录最低价或买入价，使用当前价格作为参考
                        logger.warning(f'{self.data.datetime.datetime(0).isoformat()} 空头平仓但无法计算收益: 最低价记录缺失')
                    
                    # 平仓后重置标志和止损
                    self.is_short = False
                    self.stop_loss_price = None
                    self.lowest_price = None
                else:
                    # 多头入场
                    self.long_trades += 1
                    
                    # 设置多头初始止损价格
                    self._set_initial_stop_loss()
                
            elif order.issell():
                sell_or_short = "卖出" if not self.is_short else "卖空"
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} {sell_or_short}执行: 价格: {order.executed.price:.2f}, '
                         f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}, 交易#: {self.trade_count}')
                
                # 如果是卖出平多仓
                if not self.is_short and self.buy_price is not None:
                    profit = (order.executed.price - self.buy_price) * order.executed.size
                    profit_pct = (order.executed.price / self.buy_price - 1) * 100
                    
                    # 记录交易结果
                    if profit > 0:
                        self.profitable_trades += 1
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 多头交易盈利: {profit:.2f} ({profit_pct:.2f}%)')
                    else:
                        self.losing_trades += 1
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 多头交易亏损: {profit:.2f} ({profit_pct:.2f}%)')
                    
                    # 重置止损价格和相关状态
                    self.stop_loss_price = None
                    self.highest_price = None
                    self.entry_time = None
                    self.bars_since_entry = 0
                elif not self.is_short:
                    # 新建空头仓位
                    self.is_short = True
                    self.short_trades += 1
                    self.entry_time = self.data.datetime.datetime(0)
                    self.bars_since_entry = 0
                    self.buy_price = order.executed.price
                    self.buy_comm = order.executed.comm
                    
                    # 设置空头初始止损价格
                    self._set_initial_stop_loss_short()
        
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
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 交易统计 - '
                         f'胜率: {win_rate:.2f}%, 交易数: {self.trade_count}, '
                         f'多/空比: {self.long_trades}/{self.short_trades}')
    
    def _set_initial_stop_loss(self):
        """设置多头初始止损价格，考虑波动性和市场环境"""
        atr_value = self.atr[0]
        multiplier = self.p.atr_multiplier
        
        # 1. 波动性自适应调整
        if self.p.volatility_adjust and len(self.volatility) > 50:  # 确保有足够的数据
            # 获取最新的波动率
            current_vol = self.volatility[0]
            
            # 计算过去50个周期波动率的均值作为参考
            vol_avg = 0
            for i in range(1, 50):
                vol_avg += self.volatility[-i]
            vol_avg /= 49  # 使用除0索引外的49个周期
            
            if vol_avg > 0:  # 防止除零错误
                # 相对于历史波动率的平均值的比例
                vol_ratio = current_vol / vol_avg
                # 根据波动率调整乘数，波动大时放宽止损，波动小时收紧止损
                vol_adjust = np.clip(vol_ratio, 0.8, 1.5)  # 限制调整范围
                multiplier *= vol_adjust
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 波动率调整: 当前:{current_vol:.4f}, '
                         f'平均:{vol_avg:.4f}, 比率:{vol_ratio:.2f}, 调整因子:{vol_adjust:.2f}')
        
        # 2. 市场环境感知调整
        if self.p.market_aware and len(self.market_trend) > 20:  # 确保有足够的数据
            # 当市场趋势向上（EMA20 > EMA50）时，收紧止损；反之放宽
            trend_value = self.market_trend[0]
            if trend_value > 0:  # 上升趋势
                # 上涨趋势中，收紧止损以保护利润
                trend_adjust = 0.9  # 减少10%的止损距离
            else:  # 下降趋势
                # 下跌趋势中，放宽止损以避免震荡出局
                trend_adjust = 1.1  # 增加10%的止损距离
            multiplier *= trend_adjust
            logger.info(f'{self.data.datetime.datetime(0).isoformat()} 趋势调整: 趋势值:{trend_value:.4f}, '
                      f'调整因子:{trend_adjust:.2f}')
        
        # 3. 应用风险规避系数
        multiplier *= self.p.risk_aversion
        
        # 计算止损距离
        stop_loss_distance = atr_value * multiplier
        
        # 确保止损不超过最大止损百分比
        max_loss_distance = self.buy_price * self.p.max_loss_pct / 100
        stop_loss_distance = min(stop_loss_distance, max_loss_distance)
        
        # 设置止损价格
        self.stop_loss_price = self.buy_price - stop_loss_distance
        self.highest_price = self.buy_price
        
        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 设置多头智能初始止损: {self.stop_loss_price:.2f} '
                 f'(ATR: {atr_value:.2f}, 调整后乘数: {multiplier:.2f}, 距离: {stop_loss_distance:.2f})')
    
    def _set_initial_stop_loss_short(self):
        """设置空头初始止损价格，考虑波动性和市场环境"""
        atr_value = self.atr[0]
        # 空头使用专门的乘数和波动因子
        multiplier = self.p.short_atr_multiplier
        atr_value = atr_value * self.p.short_volatility_factor  # 应用空头波动因子
        
        # 1. 波动性自适应调整
        if self.p.volatility_adjust and len(self.volatility) > 50:
            current_vol = self.volatility[0]
            
            vol_avg = 0
            for i in range(1, 50):
                vol_avg += self.volatility[-i]
            vol_avg /= 49
            
            if vol_avg > 0:
                vol_ratio = current_vol / vol_avg
                # 空头波动调整与多头方向相反
                # 波动大时稍微放宽止损但幅度小于多头，波动小时大幅收紧止损
                vol_adjust = np.clip(vol_ratio, 0.85, 1.4)
                multiplier *= vol_adjust
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 空头波动率调整: 当前:{current_vol:.4f}, '
                         f'平均:{vol_avg:.4f}, 比率:{vol_ratio:.2f}, 调整因子:{vol_adjust:.2f}')
        
        # 2. 市场环境感知调整 - 空头与多头相反
        if self.p.market_aware and len(self.market_trend) > 20:
            trend_value = self.market_trend[0]
            if trend_value < 0:  # 下降趋势
                # 下跌趋势中，收紧止损以保护空头利润
                trend_adjust = 0.9
            else:  # 上升趋势
                # 上涨趋势中，放宽止损以避免震荡出局
                trend_adjust = 1.1
            multiplier *= trend_adjust
            logger.info(f'{self.data.datetime.datetime(0).isoformat()} 空头趋势调整: 趋势值:{trend_value:.4f}, '
                      f'调整因子:{trend_adjust:.2f}')
        
        # 3. 应用风险规避系数
        multiplier *= self.p.risk_aversion
        
        # 计算止损距离
        stop_loss_distance = atr_value * multiplier
        
        # 确保止损不超过空头最大止损百分比
        max_loss_distance = self.buy_price * self.p.short_max_loss_pct / 100
        stop_loss_distance = min(stop_loss_distance, max_loss_distance)
        
        # 设置空头止损价格 (注意空头止损是向上的)
        self.stop_loss_price = self.buy_price + stop_loss_distance
        self.lowest_price = self.buy_price  # 确保lowest_price有初始值
        
        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 设置空头智能初始止损: {self.stop_loss_price:.2f} '
                 f'(ATR: {atr_value:.2f}, 调整后乘数: {multiplier:.2f}, 距离: {stop_loss_distance:.2f})')
        
    def _update_stop_loss(self):
        """更新多头止损价格，考虑追踪止损和时间衰减"""
        current_price = self.data.close[0]
        
        # 更新入场后的K线计数
        self.bars_since_entry += 1
        
        # 只有启用追踪止损且当前价格创新高时才考虑更新止损
        if self.p.trailing_stop and current_price > self.highest_price:
            self.highest_price = current_price
            
            # 计算当前盈利百分比
            profit_pct = (current_price / self.buy_price - 1) * 100
            
            # 如果盈利超过最小盈利百分比，更新止损价格
            if profit_pct >= self.p.min_profit_pct:
                # 基本ATR止损距离
                atr_value = self.atr[0]
                stop_loss_distance = atr_value * self.p.atr_multiplier
                
                # 时间衰减调整 - 持仓时间越长，止损越收紧
                decay_factor = 1.0
                if self.p.time_decay:
                    time_decay_bars = self.p.time_decay_days * 78  # 约78个5分钟K线/天
                    if self.bars_since_entry > time_decay_bars:
                        # 计算时间衰减因子(0.8-1.0)
                        decay_factor = max(0.8, 1.0 - (self.bars_since_entry - time_decay_bars) / 1000)
                        stop_loss_distance *= decay_factor
                
                # 盈利越多，止损越紧
                profit_factor = 1.0
                if profit_pct > 3.0:  # 盈利大于3%时
                    profit_factor = max(0.7, 1.0 - (profit_pct - 3.0) / 20)  # 最多减少30%的止损距离
                    stop_loss_distance *= profit_factor
                
                # 计算新的止损价格
                new_stop_loss = self.highest_price - stop_loss_distance
                
                # 只有当新止损价格高于原止损价格时才更新
                if new_stop_loss > self.stop_loss_price:
                    old_stop_loss = self.stop_loss_price
                    self.stop_loss_price = new_stop_loss
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 更新多头智能追踪止损: {old_stop_loss:.2f} -> {new_stop_loss:.2f} '
                             f'(最高价: {self.highest_price:.2f}, 盈利: {profit_pct:.2f}%, 持仓K线数: {self.bars_since_entry}, '
                             f'时间因子: {decay_factor:.2f}, 盈利因子: {profit_factor:.2f})')

    def _update_stop_loss_short(self):
        """更新空头止损价格，考虑追踪止损和时间衰减"""
        current_price = self.data.close[0]
        
        # 更新入场后的K线计数
        self.bars_since_entry += 1
        
        # 确保最低价已初始化
        if self.lowest_price is None:
            self.lowest_price = current_price
            logger.warning(f'{self.data.datetime.datetime(0).isoformat()} 初始化空头最低价: {current_price:.2f}')
        
        # 只有启用追踪止损且当前价格创新低时才考虑更新止损
        if self.p.trailing_stop and current_price < self.lowest_price:
            self.lowest_price = current_price
            
            # 计算当前盈利百分比（空头是反向的）
            profit_pct = (self.buy_price / current_price - 1) * 100
            
            # 如果盈利超过空头最小盈利百分比，更新止损价格
            if profit_pct >= self.p.short_min_profit_pct:
                # 基本ATR止损距离，应用空头专用乘数和波动因子
                atr_value = self.atr[0] * self.p.short_volatility_factor
                stop_loss_distance = atr_value * self.p.short_atr_multiplier
                
                # 时间衰减调整
                decay_factor = 1.0
                if self.p.time_decay:
                    time_decay_bars = self.p.time_decay_days * 78
                    if self.bars_since_entry > time_decay_bars:
                        decay_factor = max(0.8, 1.0 - (self.bars_since_entry - time_decay_bars) / 1000)
                        stop_loss_distance *= decay_factor
                
                # 盈利调整 - 空头盈利越多，止损越紧
                profit_factor = 1.0
                if profit_pct > 3.5:  # 空头盈利阈值略高于多头
                    profit_factor = max(0.7, 1.0 - (profit_pct - 3.5) / 22)
                    stop_loss_distance *= profit_factor
                
                # 计算新的空头止损价格 (注意是向上的止损)
                new_stop_loss = self.lowest_price + stop_loss_distance
                
                # 只有当新止损价格低于原止损价格时才更新
                if new_stop_loss < self.stop_loss_price:
                    old_stop_loss = self.stop_loss_price
                    self.stop_loss_price = new_stop_loss
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 更新空头智能追踪止损: {old_stop_loss:.2f} -> {new_stop_loss:.2f} '
                             f'(最低价: {self.lowest_price:.2f}, 盈利: {profit_pct:.2f}%, 持仓K线数: {self.bars_since_entry}, '
                             f'时间因子: {decay_factor:.2f}, 盈利因子: {profit_factor:.2f})')
    
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
        
        # 检查是否有仓位
        if not self.position:
            # 没有仓位，检查买入或卖空信号
            
            # 检查多头买入信号
            if self.magic_nine.lines.buy_setup[0] >= self.p.magic_count:
                value = self.broker.get_value()
                size = int(value * self.p.position_pct / current_price)
                
                if size > 0:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 买入信号! 神奇九转计数: {self.magic_nine.lines.buy_setup[0]}, '
                             f'价格: {current_price:.2f}, 数量: {size}')
                    
                    # 下买入订单
                    self.order = self.buy(size=size)
                    self.position_size = size
                    self.is_short = False
            
            # 检查空头卖出信号
            elif self.magic_nine.lines.sell_setup[0] >= self.p.magic_count and self.p.enable_short:
                value = self.broker.get_value()
                size = int(value * self.p.position_pct / current_price)
                
                if size > 0:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖空信号! 神奇九转计数: {self.magic_nine.lines.sell_setup[0]}, '
                             f'价格: {current_price:.2f}, 数量: {size}')
                    
                    # 下卖空订单
                    self.order = self.sell(size=size)
                    self.position_size = size
                    self.is_short = True
        
        else:
            # 更新入场后的K线计数
            self.bars_since_entry += 1
            
            # 检查是多头还是空头
            if not self.is_short:  # 多头仓位
                # 更新多头追踪止损
                if self.highest_price is not None and self.stop_loss_price is not None:
                    self._update_stop_loss()
                
                # 检查多头止损条件
                if self.stop_loss_price is not None and current_price <= self.stop_loss_price:
                    # 触发多头止损
                    loss_pct = (current_price / self.buy_price - 1) * 100
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 多头智能止损触发! 盈亏: {loss_pct:.2f}%, '
                             f'价格: {current_price:.2f}, 止损价: {self.stop_loss_price:.2f}, 数量: {self.position_size}, 持仓K线数: {self.bars_since_entry}')
                    
                    # 下卖出订单
                    self.order = self.sell(size=self.position_size)
                    self.position_size = 0
                    return
                
                # 时间止损 - 持仓超过7天且没有足够利润
                if self.bars_since_entry > 546:  # 约每天78个5分钟K线，7天大约为546个K线
                    # 计算当前盈利百分比
                    profit_pct = (current_price / self.buy_price - 1) * 100
                    # 如果持仓7天后盈利低于2%，考虑退出
                    if profit_pct < 2.0:
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 多头时间止损触发! 持仓时间过长且收益低: {profit_pct:.2f}%, '
                                f'价格: {current_price:.2f}, 持仓K线数: {self.bars_since_entry}')
                        # 下卖出订单
                        self.order = self.sell(size=self.position_size)
                        self.position_size = 0
                        return
                
                # 检查多头卖出信号
                if self.magic_nine.lines.sell_setup[0] >= self.p.magic_count:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖出信号! 神奇九转计数: {self.magic_nine.lines.sell_setup[0]}, '
                             f'价格: {current_price:.2f}, 数量: {self.position_size}')
                    
                    # 下卖出订单
                    self.order = self.sell(size=self.position_size)
                    self.position_size = 0
                    
            else:  # 空头仓位
                # 更新空头追踪止损
                if self.stop_loss_price is not None:  # 只检查止损价是否存在，不依赖最低价
                    self._update_stop_loss_short()
                
                # 检查空头止损条件
                if self.stop_loss_price is not None and current_price >= self.stop_loss_price:
                    # 触发空头止损
                    loss_pct = (self.buy_price / current_price - 1) * 100
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 空头智能止损触发! 盈亏: {loss_pct:.2f}%, '
                             f'价格: {current_price:.2f}, 止损价: {self.stop_loss_price:.2f}, 数量: {self.position_size}, 持仓K线数: {self.bars_since_entry}')
                    
                    # 下买入订单平空仓
                    self.order = self.buy(size=self.position_size)
                    self.position_size = 0
                    return
                
                # 空头时间止损
                if self.bars_since_entry > 546:
                    # 计算当前空头盈利百分比（与多头相反）
                    profit_pct = (self.buy_price / current_price - 1) * 100
                    if profit_pct < 2.0:
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 空头时间止损触发! 持仓时间过长且收益低: {profit_pct:.2f}%, '
                                f'价格: {current_price:.2f}, 持仓K线数: {self.bars_since_entry}')
                        # 下买入订单平空仓
                        self.order = self.buy(size=self.position_size)
                        self.position_size = 0
                        return
                
                # 检查空头平仓信号
                if self.magic_nine.lines.buy_setup[0] >= self.p.magic_count:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 买入信号! 神奇九转计数: {self.magic_nine.lines.buy_setup[0]}, '
                             f'价格: {current_price:.2f}, 数量: {self.position_size}')
                    
                    # 下买入订单平空仓
                    self.order = self.buy(size=self.position_size)
                    self.position_size = 0 