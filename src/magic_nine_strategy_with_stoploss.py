import backtrader as bt
import logging
from src.indicators import MagicNine, KDJBundle

logger = logging.getLogger(__name__)

class MagicNineStrategyWithStopLoss(bt.Strategy):
    """神奇九转交易策略 - 带止损版本，支持双向交易（多空）"""
    params = (
        ('magic_period', 2),    # 神奇九转比较周期，默认改为2使信号更频繁
        ('magic_count', 5),     # 神奇九转信号触发计数，默认改为5增加交易次数
        ('rsi_period', 14),     # RSI周期
        ('rsi_oversold', 30),   # RSI超卖值
        ('rsi_overbought', 70), # RSI超买值
        ('kdj_oversold', 20),   # KDJ超卖值
        ('kdj_overbought', 80), # KDJ超买值
        ('macd_signal', 0),     # MACD信号线
        ('stop_loss_pct', 3.0), # 止损百分比，默认3%
        ('enable_short', True), # 是否允许做空
    )
    
    def __init__(self):
        """初始化策略"""
        # 订单和交易状态
        self.order = None
        self.buy_price = None
        self.buy_comm = None
        self.position_size = 0
        self.stop_loss = None
        self.is_short = False  # 标记当前是否为空头仓位
        
        # 计算指标 - 只关注神奇九转
        self.magic_nine = MagicNine(self.data, period=self.p.magic_period)
        
        # 趋势指标
        self.ema20 = bt.indicators.EMA(self.data, period=20)
        self.ema50 = bt.indicators.EMA(self.data, period=50)
        
        # RSI指标
        self.rsi = bt.indicators.RSI(self.data, period=self.p.rsi_period)
        
        # 保留这些指标以便观察，但不用于信号判断
        self.kdj = KDJBundle(self.data)
        self.macd = bt.indicators.MACDHisto(self.data,
                                      period_me1=12, 
                                      period_me2=26, 
                                      period_signal=9)
        
        logger.info(f"策略初始化完成 - 带止损的双向神奇九转模式 (比较周期:{self.p.magic_period}, 信号触发计数:{self.p.magic_count}, 止损比例:{self.p.stop_loss_pct}%)")
    
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
                
                # 如果是平空仓
                if self.is_short:
                    self.is_short = False
                    self.stop_loss = None
                    
            elif order.issell():
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖出执行: 价格: {order.executed.price:.2f}, '
                         f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                
                if self.buy_price is not None and not self.is_short:
                    # 多头仓位平仓
                    profit = (order.executed.price - self.buy_price) * order.executed.size
                    profit_pct = (order.executed.price / self.buy_price - 1) * 100
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 多头交易利润: {profit:.2f}, 收益率: {profit_pct:.2f}%')
                elif not self.is_short:
                    # 建立空头仓位
                    self.buy_price = order.executed.price
                    self.buy_comm = order.executed.comm
                    self.is_short = True
                    
                    # 设置空头止损价格
                    self.stop_loss = self.buy_price * (1 + self.p.stop_loss_pct / 100)
        
        self.order = None
    
    def notify_trade(self, trade):
        """交易结果通知"""
        if trade.isclosed:
            if self.is_short:
                # 计算空头交易利润
                profit = (self.buy_price - trade.price) * trade.size
                profit_pct = (self.buy_price / trade.price - 1) * 100
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 空头交易利润: {profit:.2f}, 收益率: {profit_pct:.2f}%')
                
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
            # 没有仓位，检查买入或卖空信号
            
            # 多头信号条件：买入计数达标且EMA20>EMA50（上升趋势）且RSI不超买
            if self.magic_nine.buy_count >= self.p.magic_count:
                # 确认趋势方向 (EMA20 > EMA50 为上升趋势)
                trend_up = self.ema20[0] > self.ema50[0]
                
                # RSI不在超买区域
                current_rsi = self.rsi[0]
                rsi_ok = current_rsi < self.p.rsi_overbought
                
                # 同时满足条件时买入
                if trend_up and rsi_ok:
                    # 神奇九转买入信号 - 无需其他指标确认
                    value = self.broker.get_value()
                    size = int(value * 0.95 / current_price)  # 使用95%资金
                    
                    if size > 0:
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 买入信号! 神奇九转计数: {self.magic_nine.buy_count}, '
                                 f'价格: {current_price:.2f}, 数量: {size}')
                        
                        # 下买入订单
                        self.order = self.buy(size=size)
                        self.position_size = size
                        
                        # 设置多头止损价格
                        self.stop_loss = current_price * (1 - self.p.stop_loss_pct / 100)
            
            # 空头信号条件：卖出计数达标且EMA20<EMA50（下降趋势）且RSI不超卖
            elif self.magic_nine.sell_count >= self.p.magic_count and self.p.enable_short:
                # 确认趋势方向 (EMA20 < EMA50 为下降趋势)
                trend_down = self.ema20[0] < self.ema50[0]
                
                # RSI不在超卖区域
                current_rsi = self.rsi[0]
                rsi_ok = current_rsi > self.p.rsi_oversold
                
                # 同时满足条件时卖空
                if trend_down and rsi_ok:
                    # 神奇九转卖空信号
                    value = self.broker.get_value()
                    size = int(value * 0.95 / current_price)  # 使用95%资金
                    
                    if size > 0:
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖空信号! 神奇九转计数: {self.magic_nine.sell_count}, '
                                 f'价格: {current_price:.2f}, 数量: {size}')
                        
                        # 下卖空订单
                        self.order = self.sell(size=size)
                        self.position_size = size
                        self.is_short = True
                        
                        # 设置空头止损价格
                        self.stop_loss = current_price * (1 + self.p.stop_loss_pct / 100)
        
        else:
            # 已有仓位，首先检查止损条件
            if self.stop_loss is not None:
                if not self.is_short and current_price <= self.stop_loss:
                    # 多头止损触发
                    loss_pct = (self.buy_price - current_price) / self.buy_price * 100.0
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 多头止损触发! 亏损: {loss_pct:.2f}%, 价格: {current_price:.2f}, 数量: {self.position_size}')
                    
                    # 下卖出订单
                    self.order = self.sell(size=self.position_size)
                    self.position_size = 0
                    return  # 执行止损后直接返回，不检查其他卖出信号
                
                elif self.is_short and current_price >= self.stop_loss:
                    # 空头止损触发
                    loss_pct = (current_price - self.buy_price) / self.buy_price * 100.0
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 空头止损触发! 亏损: {loss_pct:.2f}%, 价格: {current_price:.2f}, 数量: {self.position_size}')
                    
                    # 下买入订单平空仓
                    self.order = self.buy(size=self.position_size)
                    self.position_size = 0
                    self.is_short = False
                    return  # 执行止损后直接返回
            
            # 检查常规平仓信号
            if not self.is_short and self.magic_nine.sell_count >= self.p.magic_count:
                # 多头仓位，检查卖出信号
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖出信号! 神奇九转计数: {self.magic_nine.sell_count}, '
                         f'价格: {current_price:.2f}, 数量: {self.position_size}')
                
                # 下卖出订单
                self.order = self.sell(size=self.position_size)
                self.position_size = 0
                self.stop_loss = None
            
            elif self.is_short and self.magic_nine.buy_count >= self.p.magic_count:
                # 空头仓位，检查买入信号
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 买入信号! 神奇九转计数: {self.magic_nine.buy_count}, '
                         f'价格: {current_price:.2f}, 数量: {self.position_size}')
                
                # 下买入订单平空仓
                self.order = self.buy(size=self.position_size)
                self.position_size = 0
                self.is_short = False
                self.stop_loss = None 