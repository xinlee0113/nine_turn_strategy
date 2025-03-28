import backtrader as bt
import logging
from src.indicators import MagicNine, RSIBundle, KDJBundle

logger = logging.getLogger(__name__)

class MagicNineStrategyWithStopLoss(bt.Strategy):
    """神奇九转交易策略 - 带止损版本"""
    params = (
        ('magic_period', 2),    # 神奇九转比较周期，默认改为2使信号更频繁
        ('magic_count', 5),     # 神奇九转信号触发计数，默认改为5增加交易次数
        ('rsi_oversold', 30),   # RSI超卖值
        ('rsi_overbought', 70), # RSI超买值
        ('kdj_oversold', 20),   # KDJ超卖值
        ('kdj_overbought', 80), # KDJ超买值
        ('macd_signal', 0),     # MACD信号线
        ('stop_loss_pct', 3.0), # 止损百分比，默认3%
    )
    
    def __init__(self):
        """初始化策略"""
        # 订单和交易状态
        self.order = None
        self.buy_price = None
        self.buy_comm = None
        self.position_size = 0
        
        # 计算指标 - 只关注神奇九转
        self.magic_nine = MagicNine(self.data, period=self.p.magic_period)
        
        # 保留这些指标以便观察，但不用于信号判断
        self.rsi = RSIBundle(self.data)
        self.kdj = KDJBundle(self.data)
        self.macd = bt.indicators.MACDHisto(self.data,
                                      period_me1=12, 
                                      period_me2=26, 
                                      period_signal=9)
        
        logger.info(f"策略初始化完成 - 带止损的神奇九转模式 (比较周期:{self.p.magic_period}, 信号触发计数:{self.p.magic_count}, 止损比例:{self.p.stop_loss_pct}%)")
    
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
            elif order.issell():
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖出执行: 价格: {order.executed.price:.2f}, '
                         f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                
                if self.buy_price is not None:
                    profit = (order.executed.price - self.buy_price) * order.executed.size
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 交易利润: {profit:.2f}')
        
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
            # 已有仓位，首先检查止损条件
            if self.buy_price is not None:
                # 计算当前亏损百分比
                loss_pct = (self.buy_price - current_price) / self.buy_price * 100.0
                
                # 如果亏损超过止损比例，触发止损
                if loss_pct >= self.p.stop_loss_pct:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 止损触发! 亏损: {loss_pct:.2f}%, 价格: {current_price:.2f}, 数量: {self.position_size}')
                    
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