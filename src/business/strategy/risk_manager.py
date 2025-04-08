"""
风险管理器模块
用于评估交易风险并提供风险控制功能
"""
import logging

logger = logging.getLogger(__name__)


class RiskManager:
    """风险管理器类
    
    负责评估交易风险并决定是否允许交易执行
    """
    
    def __init__(self, params=None):
        """初始化风险管理器
        
        Args:
            params: 风险参数字典，包含各种风险控制参数
        """
        # 默认参数
        self.params = {
            'stop_loss_pct': 0.8,        # 止损百分比
            'profit_target_pct': 2.0,    # 利润目标百分比
            'trailing_pct': 1.0,         # 移动止损激活百分比
            'max_loss_pct': 3.0,         # 最大损失百分比
            'min_profit_pct': 1.0,       # 最小利润百分比
            'trailing_stop': True,       # 是否启用移动止损
            'short_max_loss_pct': 3.5,   # 空头最大损失百分比
            'short_min_profit_pct': 1.2  # 空头最小利润百分比
        }
        
        # 如果提供了参数，则更新默认参数
        if params:
            self.params.update(params)
            
        # 跟踪状态
        self.stop_loss = None
        self.trailing_activated = False
    
    def calculate_long_stop_loss(self, entry_price):
        """计算多头止损价格
        
        Args:
            entry_price: 入场价格
            
        Returns:
            float: 止损价格
        """
        return entry_price * (1 - self.params['stop_loss_pct'] / 100)
    
    def calculate_short_stop_loss(self, entry_price):
        """计算空头止损价格
        
        Args:
            entry_price: 入场价格
            
        Returns:
            float: 止损价格
        """
        return entry_price * (1 + self.params['stop_loss_pct'] / 100)
    
    def check_long_stop_loss(self, current_price):
        """检查多头是否触发止损
        
        Args:
            current_price: 当前价格
            
        Returns:
            bool: 是否触发止损
        """
        if self.stop_loss is not None and current_price <= self.stop_loss:
            logger.info(f'多头止损触发! 价格: {current_price:.2f}, 止损价: {self.stop_loss:.2f}')
            return True
        return False
    
    def check_short_stop_loss(self, current_price):
        """检查空头是否触发止损
        
        Args:
            current_price: 当前价格
            
        Returns:
            bool: 是否触发止损
        """
        if self.stop_loss is not None and current_price >= self.stop_loss:
            logger.info(f'空头止损触发! 价格: {current_price:.2f}, 止损价: {self.stop_loss:.2f}')
            return True
        return False
    
    def update_long_trailing_stop(self, current_price, entry_price):
        """更新多头移动止损
        
        Args:
            current_price: 当前价格
            entry_price: 入场价格
            
        Returns:
            bool: 移动止损是否被激活或更新
        """
        updated = False
        
        # 如果没有启用移动止损，直接返回
        if not self.params['trailing_stop']:
            return updated
            
        if self.trailing_activated:
            # 已激活移动止损
            trail_price = current_price * (1 - self.params['trailing_pct'] / 100)
            if trail_price > self.stop_loss:
                old_stop = self.stop_loss
                self.stop_loss = trail_price
                logger.info(f'更新移动止损: {old_stop:.2f} -> {trail_price:.2f}')
                updated = True
        else:
            # 判断是否达到移动止损激活条件
            profit_pct = (current_price / entry_price - 1) * 100
            if profit_pct >= self.params['trailing_pct']:
                self.trailing_activated = True
                trail_price = current_price * (1 - self.params['trailing_pct'] / 100)
                if self.stop_loss is None or trail_price > self.stop_loss:
                    old_stop = self.stop_loss if self.stop_loss is not None else 0
                    self.stop_loss = trail_price
                    logger.info(f'激活移动止损: {old_stop:.2f} -> {trail_price:.2f}')
                    updated = True
                    
        return updated
    
    def update_short_trailing_stop(self, current_price, entry_price):
        """更新空头移动止损
        
        Args:
            current_price: 当前价格
            entry_price: 入场价格
            
        Returns:
            bool: 移动止损是否被激活或更新
        """
        updated = False
        
        # 如果没有启用移动止损，直接返回
        if not self.params['trailing_stop']:
            return updated
            
        if self.trailing_activated:
            # 已激活移动止损
            trail_price = current_price * (1 + self.params['trailing_pct'] / 100)
            if trail_price < self.stop_loss:
                old_stop = self.stop_loss
                self.stop_loss = trail_price
                logger.info(f'更新空头移动止损: {old_stop:.2f} -> {trail_price:.2f}')
                updated = True
        else:
            # 判断是否达到移动止损激活条件
            profit_pct = (entry_price / current_price - 1) * 100
            if profit_pct >= self.params['trailing_pct']:
                self.trailing_activated = True
                trail_price = current_price * (1 + self.params['trailing_pct'] / 100)
                if trail_price < self.stop_loss:
                    old_stop = self.stop_loss
                    self.stop_loss = trail_price
                    logger.info(f'激活空头移动止损: {old_stop:.2f} -> {trail_price:.2f}')
                    updated = True
                    
        return updated
    
    def check_long_profit_target(self, current_price, entry_price):
        """检查多头是否达到利润目标
        
        Args:
            current_price: 当前价格
            entry_price: 入场价格
            
        Returns:
            bool: 是否达到利润目标
        """
        profit_pct = (current_price / entry_price - 1) * 100
        if profit_pct >= self.params['profit_target_pct']:
            logger.info(f'达到多头利润目标! 价格: {current_price:.2f}, 买入价: {entry_price:.2f}, 利润: {profit_pct:.2f}%')
            return True
        return False
    
    def check_short_profit_target(self, current_price, entry_price):
        """检查空头是否达到利润目标
        
        Args:
            current_price: 当前价格
            entry_price: 入场价格
            
        Returns:
            bool: 是否达到利润目标
        """
        profit_pct = (entry_price / current_price - 1) * 100
        if profit_pct >= self.params['profit_target_pct']:
            logger.info(f'达到空头利润目标! 价格: {current_price:.2f}, 卖出价: {entry_price:.2f}, 利润: {profit_pct:.2f}%')
            return True
        return False
    
    def reset(self):
        """重置风险管理器状态"""
        self.stop_loss = None
        self.trailing_activated = False
