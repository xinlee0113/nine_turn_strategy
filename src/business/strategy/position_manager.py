"""
持仓管理器模块
负责管理策略的持仓状态，协调开平仓操作
"""
import logging

logger = logging.getLogger(__name__)


class PositionManager:
    """持仓管理器类
    
    负责管理策略的持仓状态，协调开平仓操作
    """
    
    def __init__(self, strategy, order_manager, position_sizer, risk_manager=None):
        """初始化持仓管理器
        
        Args:
            strategy: 策略对象，用于访问持仓和价格数据
            order_manager: 订单管理器，用于执行订单操作
            position_sizer: 仓位计算器，用于计算仓位大小
            risk_manager: 风险管理器，用于管理风险
        """
        self.strategy = strategy
        self.order_manager = order_manager
        self.position_sizer = position_sizer
        self.risk_manager = risk_manager
    
    def get_position_type(self):
        """获取当前持仓类型
        
        Returns:
            int: 1表示多头, -1表示空头, 0表示无持仓
        """
        if self.strategy.position.size > 0:
            return 1
        elif self.strategy.position.size < 0:
            return -1
        return 0
    
    def has_position(self):
        """检查是否有持仓
        
        Returns:
            bool: 是否有持仓
        """
        return self.strategy.position.size != 0
    
    def is_long(self):
        """检查是否是多头持仓
        
        Returns:
            bool: 是否是多头持仓
        """
        return self.strategy.position.size > 0
    
    def is_short(self):
        """检查是否是空头持仓
        
        Returns:
            bool: 是否是空头持仓
        """
        return self.strategy.position.size < 0
    
    def calculate_position_size(self, is_long=True, current_price=None):
        """计算仓位大小
        
        Args:
            is_long: 是否为多头仓位
            current_price: 当前价格，如果为None则使用策略的当前价格
            
        Returns:
            float: 计算得到的仓位大小
        """
        if current_price is None:
            current_price = self.strategy.data.close[0]
            
        # 获取账户价值
        value = self.strategy.broker.get_value()
        
        # 根据方向计算仓位大小
        if is_long:
            size = self.position_sizer.calculate_long_position_size(value, current_price)
        else:
            size = self.position_sizer.calculate_short_position_size(value, current_price)
            
        # 如果策略支持波动率调整，则进行调整
        if hasattr(self.strategy, "p") and hasattr(self.strategy.p, "volatility_adjust") and self.strategy.p.volatility_adjust:
            if hasattr(self.strategy, "atr"):
                atr_value = self.strategy.atr[0]
                size = self.position_sizer.adjust_position_size_by_volatility(
                    size, atr_value, is_short=(not is_long))
                
        return size
    
    def open_long(self, current_price=None, reason="多头开仓"):
        """开多头仓位
        
        Args:
            current_price: 当前价格，如果为None则使用策略的当前价格
            reason: 开仓原因
            
        Returns:
            bool: 是否成功开仓
        """
        # 如果已有仓位，则不能开仓
        if self.has_position():
            return False
            
        # 计算开仓大小
        size = self.calculate_position_size(is_long=True, current_price=current_price)
        
        # 如果数量太小，则不开仓
        if size <= 0:
            return False
            
        # 执行买入操作
        self.order_manager.buy_long(size)
        
        # 记录到日志
        current_price = current_price or self.strategy.data.close[0]
        logger.info(f"开多头仓位: 价格={current_price:.2f}, 数量={size}, 原因={reason}")
        
        return True
        
    def open_short(self, current_price=None, reason="空头开仓"):
        """开空头仓位
        
        Args:
            current_price: 当前价格，如果为None则使用策略的当前价格
            reason: 开仓原因
            
        Returns:
            bool: 是否成功开仓
        """
        # 如果已有仓位，则不能开仓
        if self.has_position():
            return False
            
        # 计算开仓大小
        size = self.calculate_position_size(is_long=False, current_price=current_price)
        
        # 如果数量太小，则不开仓
        if size <= 0:
            return False
            
        # 执行卖空操作
        self.order_manager.sell_short(size)
        
        # 设置止损价格
        if self.risk_manager and current_price:
            self.risk_manager.stop_loss = self.risk_manager.calculate_short_stop_loss(current_price)
            
        # 记录到日志
        current_price = current_price or self.strategy.data.close[0]
        logger.info(f"开空头仓位: 价格={current_price:.2f}, 数量={size}, 原因={reason}")
        
        return True
        
    def close_long(self, reason="多头平仓"):
        """平多头仓位
        
        Args:
            reason: 平仓原因
            
        Returns:
            bool: 是否成功平仓
        """
        # 如果没有多头仓位，则不能平仓
        if not self.is_long():
            return False
            
        # 执行卖出操作
        self.order_manager.close_long(reason)
        
        # 记录到日志
        current_price = self.strategy.data.close[0]
        logger.info(f"平多头仓位: 价格={current_price:.2f}, 原因={reason}")
        
        # 重置风险管理器
        if self.risk_manager:
            self.risk_manager.reset()
            
        return True
        
    def close_short(self, reason="空头平仓"):
        """平空头仓位
        
        Args:
            reason: 平仓原因
            
        Returns:
            bool: 是否成功平仓
        """
        # 如果没有空头仓位，则不能平仓
        if not self.is_short():
            return False
            
        # 执行买入操作平空头
        self.order_manager.close_short(reason)
        
        # 记录到日志
        current_price = self.strategy.data.close[0]
        logger.info(f"平空头仓位: 价格={current_price:.2f}, 原因={reason}")
        
        # 重置风险管理器
        if self.risk_manager:
            self.risk_manager.reset()
            
        return True
        
    def close_position(self, reason="平仓"):
        """平当前仓位
        
        Args:
            reason: 平仓原因
            
        Returns:
            bool: 是否成功平仓
        """
        if self.is_long():
            return self.close_long(reason)
        elif self.is_short():
            return self.close_short(reason)
        return False
        
    def handle_long_position(self, current_price=None):
        """处理多头持仓的止损和平仓
        
        Args:
            current_price: 当前价格，如果为None则使用策略的当前价格
            
        Returns:
            bool: 是否执行了平仓操作
        """
        if not self.is_long() or not self.risk_manager:
            return False
            
        current_price = current_price or self.strategy.data.close[0]
        buy_price = self.order_manager.get_buy_price()
        
        # 更新移动止损价格
        self.risk_manager.update_long_trailing_stop(current_price, buy_price)

        # 1. 多头止损检查
        if self.risk_manager.check_long_stop_loss(current_price):
            self.close_long("多头止损触发")
            return True

        # 2. 获利目标检查
        if self.risk_manager.check_long_profit_target(current_price, buy_price):
            self.close_long("达到多头利润目标")
            return True
            
        return False
        
    def handle_short_position(self, current_price=None):
        """处理空头持仓的止损和平仓
        
        Args:
            current_price: 当前价格，如果为None则使用策略的当前价格
            
        Returns:
            bool: 是否执行了平仓操作
        """
        if not self.is_short() or not self.risk_manager:
            return False
            
        current_price = current_price or self.strategy.data.close[0]
        sell_price = self.order_manager.get_buy_price()  # 对于空头，这是卖空价格
        
        # 1. 空头止损检查
        if self.risk_manager.check_short_stop_loss(current_price):
            self.close_short("空头止损触发")
            return True

        # 2. 移动止损更新
        self.risk_manager.update_short_trailing_stop(current_price, sell_price)

        # 3. 检查空头利润目标
        if self.risk_manager.check_short_profit_target(current_price, sell_price):
            self.close_short("达到空头利润目标")
            return True
            
        return False
        
    def handle_signal_exit(self, signal, magic_nine):
        """处理信号平仓
        
        Args:
            signal: 信号值
            magic_nine: MagicNine指标对象
            
        Returns:
            bool: 是否执行了平仓操作
        """
        # 如果信号不是0，则不处理
        if signal != 0:
            return False
            
        signal_generator = self.strategy.signal_generator
        
        # 根据持仓类型检查是否需要平仓
        if self.is_long() and signal_generator.check_long_exit_signal(magic_nine):
            self.close_long("多头平仓信号")
            return True
        elif self.is_short() and signal_generator.check_short_exit_signal(magic_nine):
            self.close_short("空头平仓信号")
            return True
            
        return False
        
    def force_close_at_end_of_day(self, current_time, time_info):
        """收盘前强制平仓
        
        Args:
            current_time: 当前时间
            time_info: 时间信息字典
            
        Returns:
            bool: 是否执行了平仓操作
        """
        if not self.has_position():
            return False
            
        # 构建日志信息
        position_type = "多头" if self.is_long() else "空头"
        current_price = self.strategy.data.close[0]
        
        logger.info(
            f'{current_time.isoformat()} 收盘前强制平仓{position_type}! 价格: {current_price:.2f}, '
            f'ET时间约: {time_info["et_hour"]}:{time_info["et_minute"]:02d}')
            
        # 平仓
        return self.close_position("收盘前强制平仓")