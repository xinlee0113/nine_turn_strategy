"""
Interactive Brokers客户端实现
"""
from typing import Dict, Optional, Any

from ibapi.client import EClient
from ibapi.wrapper import EWrapper

from .config import IBConfig


class IBClient(EWrapper, EClient):
    """Interactive Brokers客户端类"""

    def __init__(self, config: IBConfig):
        """初始化客户端
        
        Args:
            config: IB配置对象
        """
        EWrapper.__init__(self)
        EClient.__init__(self, wrapper=self)
        self.config = config
        self.data: Dict = {}
        self.error_messages: list = []
        self.connected = False

    def connect(self) -> None:
        """连接到IB服务器"""
        if not self.connected:
            cfg = self.config.get_config()
            super().connect(cfg['host'], cfg['port'], cfg['client_id'])
            self.run()
            self.connected = True

    def disconnect(self) -> None:
        """断开连接"""
        if self.connected:
            super().disconnect()
            self.connected = False

    def error(self, reqId: int, errorCode: int, errorString: str) -> None:
        """错误回调
        
        Args:
            reqId: 请求ID
            errorCode: 错误代码
            errorString: 错误信息
        """
        error_msg = f"Error {errorCode}: {errorString}"
        self.error_messages.append(error_msg)
        print(error_msg)

    def get_data(self) -> Optional[Dict[str, Any]]:
        """获取数据
        
        Returns:
            数据字典,无数据返回None
        """
        return self.data if self.data else None

    def place_order(self, order_id: int, contract: Any, order: Any) -> None:
        """下单
        
        Args:
            order_id: 订单ID
            contract: 合约对象
            order: 订单对象
        """
        if not self.connected:
            raise Exception("未连接到交易服务器")
        super().placeOrder(order_id, contract, order)

    def cancel_order(self, order_id: int) -> None:
        """撤单
        
        Args:
            order_id: 订单ID
        """
        if not self.connected:
            raise Exception("未连接到交易服务器")
        super().cancelOrder(order_id)
