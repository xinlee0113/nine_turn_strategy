from .tiger_client import TigerClient
from .tiger_config import TigerConfig
from .tiger_order import TigerOrder
from ..base_broker import BaseBroker


class TigerBroker(BaseBroker):
    """老虎证券经纪商"""

    def __init__(self, config: TigerConfig):
        """初始化老虎证券经纪商
        
        Args:
            config: 配置对象
        """
        super().__init__()
        self.config = config
        self.client = TigerClient(config)
        self.connected = False

    def connect(self):
        """连接经纪商"""
        if not self.connected:
            self.client.connect()
            self.connected = True

    def disconnect(self):
        """断开连接"""
        if self.connected:
            self.client.disconnect()
            self.connected = False

    def place_order(self, order: TigerOrder):
        """下单
        
        Args:
            order: 订单对象
        """
        if not self.connected:
            raise Exception("Not connected to broker")
        return self.client.place_order(order)

    def cancel_order(self, order_id):
        """撤单
        
        Args:
            order_id: 订单ID
        """
        if not self.connected:
            raise Exception("Not connected to broker")
        return self.client.cancel_order(order_id)

    def get_position(self, symbol):
        """获取持仓
        
        Args:
            symbol: 交易品种
        """
        if not self.connected:
            raise Exception("Not connected to broker")
        return self.client.get_position(symbol)

    def get_account(self):
        """获取账户信息"""
        if not self.connected:
            raise Exception("Not connected to broker")
        return self.client.get_account()
