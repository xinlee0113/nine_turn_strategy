"""
基础经纪商接口定义
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseBroker(ABC):
    """基础经纪商接口"""

    @abstractmethod
    def __init__(self):
        """初始化经纪商"""
        pass

    @abstractmethod
    def connect(self) -> bool:
        """连接经纪商
        
        Returns:
            连接是否成功
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """断开连接
        
        Returns:
            断开连接是否成功
        """
        pass

    @abstractmethod
    def place_order(self, order_type: str, quantity: int,
                    action: str, price: float = 0.0) -> Optional[Dict[str, Any]]:
        """下单
        
        Args:
            order_type: 订单类型
            quantity: 数量
            action: 买卖方向
            price: 价格
            
        Returns:
            订单信息字典,下单失败返回None
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """撤单
        
        Args:
            order_id: 订单ID
            
        Returns:
            撤单是否成功
        """
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取持仓
        
        Args:
            symbol: 交易品种
            
        Returns:
            持仓信息字典,无持仓返回None
        """
        pass

    @abstractmethod
    def get_account(self) -> Dict[str, Any]:
        """获取账户信息
        
        Returns:
            账户信息字典
        """
        pass
