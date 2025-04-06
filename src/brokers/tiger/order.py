from typing import Dict, Any, Optional, List
from .client import TigerClient
from .market import MarketStatus
from .contract import ContractManager

class OrderExecutor:
    """订单执行类"""
    
    def __init__(self, client: TigerClient):
        """
        初始化订单执行器
        
        Args:
            client: 老虎证券客户端
        """
        self.client = client
        self.market_status = MarketStatus(client)
        self.contract_manager = ContractManager(client)
        self._order_cache = {}
    
    def place_order(self, symbol: str, side: str, quantity: int, 
                   price: Optional[float] = None, order_type: str = 'LIMIT') -> Dict[str, Any]:
        """
        下单
        
        Args:
            symbol: 交易标的
            side: 交易方向（BUY/SELL）
            quantity: 数量
            price: 价格，None表示市价单
            order_type: 订单类型（LIMIT/MARKET）
            
        Returns:
            订单信息
        """
        # 检查市场状态
        if not self.market_status.is_trading_time(symbol):
            raise ValueError(f"Market is not open for {symbol}")
        
        # 检查合约信息
        contract_info = self.contract_manager.get_contract_info(symbol)
        if not contract_info:
            raise ValueError(f"Invalid symbol: {symbol}")
        
        # 检查数量是否合法
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        # 检查价格是否合法
        if order_type == 'LIMIT' and price is not None:
            if price <= 0:
                raise ValueError("Price must be positive")
        
        # 执行下单
        order = self.client.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price
        )
        
        # 缓存订单信息
        self._order_cache[order['order_id']] = order
        return order
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        撤单
        
        Args:
            order_id: 订单ID
            
        Returns:
            撤单结果
        """
        if order_id not in self._order_cache:
            raise ValueError(f"Order {order_id} not found")
        
        result = self.client.cancel_order(order_id)
        if result['success']:
            del self._order_cache[order_id]
        return result
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        获取订单状态
        
        Args:
            order_id: 订单ID
            
        Returns:
            订单状态
        """
        if order_id in self._order_cache:
            return self._order_cache[order_id]
        
        status = self.client.get_order_status(order_id)
        self._order_cache[order_id] = status
        return status
    
    def get_open_orders(self) -> List[Dict[str, Any]]:
        """
        获取未完成订单
        
        Returns:
            未完成订单列表
        """
        return [
            order for order in self._order_cache.values()
            if order['status'] in ['NEW', 'PARTIALLY_FILLED']
        ]
    
    def get_order_history(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取订单历史
        
        Args:
            symbol: 交易标的，None表示所有标的
            
        Returns:
            订单历史列表
        """
        if symbol:
            return [
                order for order in self._order_cache.values()
                if order['symbol'] == symbol
            ]
        return list(self._order_cache.values()) 