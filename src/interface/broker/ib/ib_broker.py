"""
Interactive Brokers接口实现
"""
from typing import Dict, Any, Optional

from .client import IBClient
from .config import IBConfig
from .order import IBOrder
from ..base_broker import BaseBroker


class IBBroker(BaseBroker):
    """Interactive Brokers接口类"""

    def __init__(self, config: IBConfig):
        """初始化IB接口
        
        Args:
            config: IB配置对象
        """
        super().__init__()
        self.config = config
        self.client = IBClient(config)
        self.connected = False
        self.order = IBOrder(self.client)

    def connect(self) -> bool:
        """连接到IB服务器
        
        Returns:
            连接是否成功
        """
        try:
            if not self.connected:
                self.client.connect()
                self.connected = True
            return True
        except Exception as e:
            print(f"连接失败: {str(e)}")
            return False

    def disconnect(self) -> bool:
        """断开连接
        
        Returns:
            断开连接是否成功
        """
        try:
            if self.connected:
                self.client.disconnect()
                self.connected = False
            return True
        except Exception as e:
            print(f"断开连接失败: {str(e)}")
            return False

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
        try:
            if not self.connected:
                raise Exception("未连接到交易服务器")
            return self.order.create_order(order_type, quantity, action, price)
        except Exception as e:
            print(f"下单失败: {str(e)}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """撤单
        
        Args:
            order_id: 订单ID
            
        Returns:
            撤单是否成功
        """
        try:
            if not self.connected:
                raise Exception("未连接到交易服务器")
            self.client.cancel_order(int(order_id))
            return True
        except Exception as e:
            print(f"撤单失败: {str(e)}")
            return False

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取持仓
        
        Args:
            symbol: 交易品种
            
        Returns:
            持仓信息字典,无持仓返回None
        """
        try:
            if not self.connected:
                raise Exception("未连接到交易服务器")
            # TODO: 实现获取持仓功能
            return None
        except Exception as e:
            print(f"获取持仓失败: {str(e)}")
            return None

    def get_account(self) -> Dict[str, Any]:
        """获取账户信息
        
        Returns:
            账户信息字典
        """
        try:
            if not self.connected:
                raise Exception("未连接到交易服务器")
            # TODO: 实现获取账户信息功能
            return {}
        except Exception as e:
            print(f"获取账户信息失败: {str(e)}")
            return {}
