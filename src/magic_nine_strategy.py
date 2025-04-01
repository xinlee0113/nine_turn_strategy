import backtrader as bt
import logging
from src.indicators import MagicNine, RSIBundle, KDJBundle

logger = logging.getLogger(__name__)

class MagicNineStrategy(bt.Strategy):
    """神奇九转交易策略 - 优化版本"""
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
        
        # 指标初始化
        self.magic_nine = MagicNine(self.data, period=self.p.magic_period)
        self.rsi = bt.indicators.RSI(self.data, period=self.p.rsi_period)
        self.ema20 = bt.indicators.EMA(self.data, period=20)
        self.ema50 = bt.indicators.EMA(self.data, period=50)
        
        logger.info(f"策略初始化完成 - 优化的神奇九转模式 (比较周期:{self.p.magic_period}, 信号触发计数:{self.p.magic_count})")
    
    def notify_order(self, order):
        """订单状态通知回调"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交或已接受，等待执行
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 买入执行: 价格: {order.executed.price:.2f}, '
                         f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
                
                # 设置止损价格
                self.stop_loss = self.buy_price * (1 - self.p.stop_loss_pct / 100)
                self.trailing_activated = False
                
            elif order.issell():
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖出执行: 价格: {order.executed.price:.2f}, '
                         f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                
                if self.buy_price:
                    profit = (order.executed.price - self.buy_price) * order.executed.size
                    profit_pct = (order.executed.price / self.buy_price - 1) * 100
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 交易利润: {profit:.2f}, 收益率: {profit_pct:.2f}%')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f'{self.data.datetime.datetime(0).isoformat()} 订单被取消/拒绝/保证金不足')
        
        # 重置订单
        self.order = None
    
    def notify_trade(self, trade):
        """交易结果通知回调"""
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
            if self.magic_nine.lines.buy_setup[0] >= self.p.magic_count:
                # 确认趋势方向 (EMA20 > EMA50 为上升趋势)
                trend_ok = self.ema20[0] > self.ema50[0]
                
                # RSI不在超买区域 (避免在高点买入)
                rsi_ok = self.rsi[0] < self.p.rsi_overbought
                
                # 同时满足条件时买入
                if trend_ok and rsi_ok:
                    # 计算仓位大小
                    value = self.broker.get_value()
                    size = int(value * self.p.position_size / current_price)
                    
                    if size > 0:
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 买入信号! 计数: {self.magic_nine.buy_count}, '
                                 f'价格: {current_price:.2f}, 数量: {size}, RSI: {self.rsi[0]:.2f}')
                        
                        # 下买入订单
                        self.order = self.buy(size=size)
                        self.position_size = size
        
        else:
            # 已有仓位，检查卖出条件
            
            # 1. 检查止损
            if self.stop_loss is not None and current_price <= self.stop_loss:
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 止损触发! 价格: {current_price:.2f}, '
                         f'止损价: {self.stop_loss:.2f}, 亏损: {(current_price/self.buy_price-1)*100:.2f}%')
                self.order = self.sell(size=self.position_size)
                self.position_size = 0
                self.stop_loss = None
                return
            
            # 2. 移动止损逻辑
            if self.buy_price is not None:
                # 计算当前利润百分比
                profit_pct = (current_price / self.buy_price - 1) * 100
                
                # 如果利润超过激活阈值且尚未激活移动止损
                if profit_pct >= self.p.trailing_pct and not self.trailing_activated:
                    # 激活移动止损
                    self.trailing_activated = True
                    # 设置移动止损价格为盈亏平衡点或更高
                    new_stop = max(self.buy_price, current_price * 0.98)  # 保留2%回撤空间
                    self.stop_loss = new_stop
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 激活移动止损! 新止损价: {self.stop_loss:.2f}')
                
                # 如果移动止损已激活，继续抬高止损价
                elif self.trailing_activated:
                    # 不断抬高止损价，但保留一定回撤空间
                    potential_stop = current_price * 0.98  # 保留2%回撤空间
                    if potential_stop > self.stop_loss:
                        old_stop = self.stop_loss
                        self.stop_loss = potential_stop
                        logger.info(f'{self.data.datetime.datetime(0).isoformat()} 更新移动止损! 旧止损: {old_stop:.2f}, '
                                  f'新止损: {self.stop_loss:.2f}')
                
                # 3. 检查利润目标
                if profit_pct >= self.p.profit_target_pct:
                    logger.info(f'{self.data.datetime.datetime(0).isoformat()} 达到利润目标! 价格: {current_price:.2f}, '
                             f'买入价: {self.buy_price:.2f}, 利润: {profit_pct:.2f}%')
                    self.order = self.sell(size=self.position_size)
                    self.position_size = 0
                    self.stop_loss = None
                    return
            
            # 4. 检查卖出信号
            if self.magic_nine.lines.sell_setup[0] >= self.p.magic_count:
                logger.info(f'{self.data.datetime.datetime(0).isoformat()} 卖出信号! 计数: {self.magic_nine.sell_count}, '
                         f'价格: {current_price:.2f}, 数量: {self.position_size}')
                
                # 下卖出订单
                self.order = self.sell(size=self.position_size)
                self.position_size = 0
                self.stop_loss = None
                self.trailing_activated = False 