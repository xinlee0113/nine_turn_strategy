"""
老虎证券订单类
"""
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderType(Enum):
    """订单类型枚举"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """订单方向枚举"""
    BUY = "buy"
    SELL = "sell"


class TigerOrder:
    """老虎证券订单类"""

    def __init__(self,
                 symbol: str,
                 quantity: int,
                 side: OrderSide,
                 order_type: OrderType,
                 price: Optional[float] = None,
                 stop_price: Optional[float] = None,
                 order_id: Optional[str] = None,
                 status: OrderStatus = OrderStatus.PENDING,
                 created_at: Optional[datetime] = None,
                 filled_at: Optional[datetime] = None,
                 filled_price: Optional[float] = None,
                 filled_quantity: int = 0):
        self.symbol = symbol
        self.quantity = quantity
        self.side = side
        self.order_type = order_type
        self.price = price
        self.stop_price = stop_price
        self.order_id = order_id
        self.status = status
        self.created_at = created_at or datetime.now()
        self.filled_at = filled_at
        self.filled_price = filled_price
        self.filled_quantity = filled_quantity

    def __str__(self) -> str:
        return (f"TigerOrder(symbol={self.symbol}, quantity={self.quantity}, "
                f"side={self.side.value}, type={self.order_type.value}, "
                f"price={self.price}, status={self.status.value})")

    def __repr__(self) -> str:
        return self.__str__()

    def is_filled(self) -> bool:
        """检查订单是否已完全成交"""
        return self.status == OrderStatus.FILLED and self.filled_quantity == self.quantity

    def is_cancelled(self) -> bool:
        """检查订单是否已取消"""
        return self.status == OrderStatus.CANCELLED

    def is_rejected(self) -> bool:
        """检查订单是否被拒绝"""
        return self.status == OrderStatus.REJECTED
