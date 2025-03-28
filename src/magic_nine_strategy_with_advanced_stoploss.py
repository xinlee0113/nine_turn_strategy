import backtrader as bt
import logging
from src.indicators import MagicNine, RSIBundle, KDJBundle

logger = logging.getLogger(__name__)

class MagicNineStrategyWithAdvancedStopLoss(bt.Strategy):
    """神奇九转交易策略 - 高级止损版本，包含ATR止损和追踪止损"""
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
    )
    
    def __init__(self):
        """初始化策略"""
        # 订单和交易状态
        self.order = None
        self.buy_price = None
        self.buy_comm = None
        self.position_size = 0
        self.stop_loss_price = None
        self.highest_price = None  # 用于追踪止损
        
        # 计算指标 - 神奇九转
        self.magic_nine = MagicNine(self.data, period=self.p.magic_period)
        
        # ATR指标，用于动态止损
        self.atr = bt.indicators.ATR(self.data, period=self.p.atr_period)
        
        # 保留这些指标以便观察，但不用于信号判断
        self.rsi = RSIBundle(self.data)
        self.kdj = KDJBundle(self.data)
        self.macd = bt.indicators.MACDHisto(self.data,
                                      period_me1=12, 
                                      period_me2=26, 
                                      period_signal=9)
        
        logger.info(f"策略初始化完成 - 高级止损的神奇九转模式 (比较周期:{self.p.magic_period}, "
                  f"信号触发计数:{self.p.magic_count}, ATR周期:{self.p.atr_period}, "
                  f"ATR乘数:{self.p.atr_multiplier}, 追踪止损:{self.p.trailing_stop})")
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 买入执行: 价格: {order.executed.price:.2f}, '
                         f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
                
                # 设置初始止损价格
                atr_value = self.atr[0]
                stop_loss_distance = atr_value * self.p.atr_multiplier
                
                # 确保止损不超过最大止损百分比
                max_loss_distance = self.buy_price * self.p.max_loss_pct / 100
                stop_loss_distance = min(stop_loss_distance, max_loss_distance)
                
                self.stop_loss_price = self.buy_price - stop_loss_distance
                self.highest_price = self.buy_price
                
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 设置初始止损: {self.stop_loss_price:.2f} '
                         f'(ATR: {atr_value:.2f}, 距离: {stop_loss_distance:.2f})')
                
            elif order.issell():
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖出执行: 价格: {order.executed.price:.2f}, '
                         f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                
                if self.buy_price is not None:
                    profit = (order.executed.price - self.buy_price) * order.executed.size
                    profit_pct = (order.executed.price / self.buy_price - 1) * 100
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 交易利润: {profit:.2f} ({profit_pct:.2f}%)')
                    
                # 重置止损价格
                self.stop_loss_price = None
                self.highest_price = None
        
        self.order = None
    
    def notify_trade(self, trade):
        """交易结果通知"""
        if trade.isclosed:
            logger.info(f'{self.data.datetime.datetime(0).isoformat()} 交易利润, 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')
    
    def next(self):
        """主策略逻辑"""
        # 如果有未完成的订单，不进行操作
        if self.order:
            return
            
        # 获取当前价格
        current_price = self.data.close[0]
        
        # 检查是否有仓位
        if not self.position:
            # 没有仓位，检查买入信号
            # 修改为当连续信号数量>=magic_count时触发买入
            if self.magic_nine.lines.buy_setup[0] >= self.p.magic_count:
                # 神奇九转买入信号 - 无需其他指标确认
                value = self.broker.get_value()
                size = int(value * 0.95 / current_price)  # 使用95%资金
                
                if size > 0:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 买入信号! 神奇九转计数: {self.magic_nine.buy_count}, '
                             f'价格: {current_price:.2f}, 数量: {size}')
                    
                    # 下买入订单
                    self.order = self.buy(size=size)
                    self.position_size = size
        
        else:
            # 已有仓位，首先更新追踪止损
            if self.p.trailing_stop and self.highest_price is not None and self.stop_loss_price is not None:
                # 更新最高价
                if current_price > self.highest_price:
                    self.highest_price = current_price
                    
                    # 计算当前盈利百分比
                    profit_pct = (current_price / self.buy_price - 1) * 100
                    
                    # 如果盈利超过最小盈利百分比，更新止损价格
                    if profit_pct >= self.p.min_profit_pct:
                        # 计算新的止损价格
                        atr_value = self.atr[0]
                        stop_loss_distance = atr_value * self.p.atr_multiplier
                        new_stop_loss = self.highest_price - stop_loss_distance
                        
                        # 只有当新止损价格高于原止损价格时才更新
                        if new_stop_loss > self.stop_loss_price:
                            old_stop_loss = self.stop_loss_price
                            self.stop_loss_price = new_stop_loss
                            logger.info(f'{self.data.datetime.datetime(0).isoformat()} 更新追踪止损: {old_stop_loss:.2f} -> {new_stop_loss:.2f} '
                                     f'(最高价: {self.highest_price:.2f}, 盈利: {profit_pct:.2f}%)')
            
            # 检查止损条件
            if self.stop_loss_price is not None and current_price <= self.stop_loss_price:
                # 触发止损
                loss_pct = (self.buy_price - current_price) / self.buy_price * 100.0
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 止损触发! 亏损: {loss_pct:.2f}%, '
                         f'价格: {current_price:.2f}, 止损价: {self.stop_loss_price:.2f}, 数量: {self.position_size}')
                
                # 下卖出订单
                self.order = self.sell(size=self.position_size)
                self.position_size = 0
                return  # 执行止损后直接返回，不检查其他卖出信号
            
            # 检查常规卖出信号
            if self.magic_nine.lines.sell_setup[0] >= self.p.magic_count:
                # 神奇九转卖出信号 - 无需其他指标确认
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖出信号! 神奇九转计数: {self.magic_nine.sell_count}, '
                         f'价格: {current_price:.2f}, 数量: {self.position_size}')
                
                # 下卖出订单
                self.order = self.sell(size=self.position_size)
                self.position_size = 0 