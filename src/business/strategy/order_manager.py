"""
订单管理器模块
用于管理交易订单和执行交易操作
"""
import logging

logger = logging.getLogger(__name__)


class OrderManager:
    """订单管理器类
    
    负责处理订单状态通知、执行买卖操作、订单记录等
    """
    
    def __init__(self, strategy):
        """初始化订单管理器
        
        Args:
            strategy: 策略对象，用于访问策略中的交易接口
        """
        self.strategy = strategy
        self.order = None
        self.buy_price = None
        self.buy_comm = None
        self.position_size = 0
        self.is_short = False
        
    def notify_order(self, order):
        """订单状态通知回调
        
        Args:
            order: 订单对象
        """
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交或已接受 - 无需操作
            return

        # 检查订单是否已完成
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(
                    f'{self.strategy.data.datetime.datetime(0).isoformat()} 买入执行，价格: {order.executed.price:.2f}, '
                    f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}'
                )
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
            else:  # 卖出
                if self.is_short:
                    logger.info(
                        f'{self.strategy.data.datetime.datetime(0).isoformat()} 卖空执行，价格: {order.executed.price:.2f}, '
                        f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}'
                    )
                    self.buy_price = order.executed.price  # 记录卖空价格
                    self.buy_comm = order.executed.comm
                else:
                    logger.info(
                        f'{self.strategy.data.datetime.datetime(0).isoformat()} 卖出执行，价格: {order.executed.price:.2f}, '
                        f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}'
                    )
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f'{self.strategy.data.datetime.datetime(0).isoformat()} 订单取消/保证金不足/拒绝')

        # 重置订单引用
        self.order = None
        
    def notify_trade(self, trade):
        """交易结果通知回调
        
        Args:
            trade: 交易对象
        """
        if trade.isclosed:
            if self.is_short:
                # 计算空头交易利润
                profit = (self.buy_price - trade.price) * trade.size
                profit_pct = (self.buy_price / trade.price - 1) * 100
                logger.info(
                    f'{self.strategy.data.datetime.datetime(0).isoformat()} 空头交易利润: {profit:.2f}, 收益率: {profit_pct:.2f}%')
                self.is_short = False

            logger.info(
                f'{self.strategy.data.datetime.datetime(0).isoformat()} 交易利润, 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')
    
    def buy_long(self, size):
        """执行多头买入操作
        
        Args:
            size: 买入数量
            
        Returns:
            order: 订单对象
        """
        if size <= 0:
            return None
            
        # 记录下单信息
        current_price = self.strategy.data.close[0]
        logger.info(
            f'{self.strategy.data.datetime.datetime(0).isoformat()} 买入信号! '
            f'计数: {self.strategy.magic_nine.buy_count}, 价格: {current_price:.2f}, '
            f'数量: {size}, RSI: {self.strategy.rsi[0]:.2f}')
        
        # 下买入订单
        self.order = self.strategy.buy(size=size)
        self.position_size = size
        self.is_short = False
        return self.order
    
    def sell_short(self, size):
        """执行空头卖出操作
        
        Args:
            size: 卖出数量
            
        Returns:
            order: 订单对象
        """
        if size <= 0:
            return None
            
        # 记录下单信息
        current_price = self.strategy.data.close[0]
        logger.info(
            f'{self.strategy.data.datetime.datetime(0).isoformat()} 卖空信号! '
            f'计数: {self.strategy.magic_nine.sell_count}, 价格: {current_price:.2f}, '
            f'数量: {size}, RSI: {self.strategy.rsi[0]:.2f}')
        
        # 下卖空订单
        self.order = self.strategy.sell(size=size)
        self.position_size = size
        self.is_short = True
        return self.order
    
    def close_long(self, reason=""):
        """平多头仓位
        
        Args:
            reason: 平仓原因
            
        Returns:
            order: 订单对象
        """
        if self.position_size <= 0:
            return None
            
        # 记录平仓信息
        current_price = self.strategy.data.close[0]
        logger.info(
            f'{self.strategy.data.datetime.datetime(0).isoformat()} 卖出平多头! '
            f'原因: {reason}, 价格: {current_price:.2f}, 数量: {self.position_size}')
        
        # 下卖出订单
        self.order = self.strategy.sell(size=self.position_size)
        self.position_size = 0
        return self.order
    
    def close_short(self, reason=""):
        """平空头仓位
        
        Args:
            reason: 平仓原因
            
        Returns:
            order: 订单对象
        """
        if self.position_size <= 0:
            return None
            
        # 记录平仓信息
        current_price = self.strategy.data.close[0]
        logger.info(
            f'{self.strategy.data.datetime.datetime(0).isoformat()} 买入平空头! '
            f'原因: {reason}, 价格: {current_price:.2f}, 数量: {self.position_size}')
        
        # 下买入订单平空头仓位
        self.order = self.strategy.buy(size=self.position_size)
        self.position_size = 0
        self.is_short = False
        return self.order
    
    def has_pending_order(self):
        """检查是否有未完成的订单
        
        Returns:
            bool: 是否有未完成订单
        """
        return self.order is not None
    
    def get_position_size(self):
        """获取当前持仓大小
        
        Returns:
            int: 当前持仓大小
        """
        return self.position_size
    
    def get_buy_price(self):
        """获取买入价格
        
        Returns:
            float: 买入价格
        """
        return self.buy_price
    
    def is_short_position(self):
        """是否为空头持仓
        
        Returns:
            bool: 是否为空头持仓
        """
        return self.is_short
    
    def reset(self):
        """重置订单管理器状态"""
        self.order = None
        self.position_size = 0