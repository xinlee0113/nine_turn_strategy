from typing import Dict, Any, Optional, List
from ibapi.order import Order
from ibapi.contract import Contract
from src.brokers.ib.client import IBClientManager
from src.brokers.ib.contract import IBContractManager

class IBOrderExecutor:
    """Interactive Brokers订单执行类"""
    
    def __init__(self, client: IBClientManager, contract_manager: IBContractManager):
        """
        初始化订单执行
        
        Args:
            client: IB客户端
            contract_manager: 合约管理
        """
        self.client = client
        self.contract_manager = contract_manager
        self.order_cache = {}
    
    def place_order(self, symbol: str, side: str, quantity: int, 
                   price: Optional[float] = None) -> Dict[str, Any]:
        """
        下单
        
        Args:
            symbol: 交易标的
            side: 交易方向（BUY/SELL）
            quantity: 交易数量
            price: 交易价格（限价单必填）
            
        Returns:
            订单信息
        """
        contract = self.contract_manager._create_contract(symbol)
        order = self._create_order(side, quantity, price)
        
        order_info = self.client.place_order(contract, order)
        self.order_cache[order_info['order_id']] = order_info
        
        return order_info
    
    def cancel_order(self, order_id: int) -> Dict[str, Any]:
        """
        撤单
        
        Args:
            order_id: 订单ID
            
        Returns:
            撤单结果
        """
        return self.client.cancel_order(order_id)
    
    def get_order_status(self, order_id: int) -> Dict[str, Any]:
        """
        获取订单状态
        
        Args:
            order_id: 订单ID
            
        Returns:
            订单状态
        """
        if order_id in self.order_cache:
            return self.order_cache[order_id]
        
        return self.client.get_order_status(order_id)
    
    def get_open_orders(self) -> List[Dict[str, Any]]:
        """
        获取未完成订单
        
        Returns:
            未完成订单列表
        """
        return self.client.get_open_orders()
    
    def get_order_history(self) -> List[Dict[str, Any]]:
        """
        获取订单历史
        
        Returns:
            订单历史列表
        """
        return self.client.get_order_history()
    
    def _create_order(self, side: str, quantity: int, 
                     price: Optional[float] = None) -> Order:
        """创建订单对象"""
        order = Order()
        order.action = side
        order.totalQuantity = quantity
        order.orderType = 'LMT' if price else 'MKT'
        if price:
            order.lmtPrice = price
        return order 