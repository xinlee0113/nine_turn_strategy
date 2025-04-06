from typing import Dict, Any, List, Optional
import time
from ibapi.client import IBClient
from ibapi.wrapper import IBWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from src.brokers.ib.config import IBConfig

class IBClientManager:
    """Interactive Brokers客户端管理类"""
    
    def __init__(self, config: IBConfig):
        """
        初始化客户端
        
        Args:
            config: IB配置
        """
        self.config = config
        self.client = IBClient()
        self.wrapper = IBWrapper()
        self.client.connect(
            self.config.get_config()['host'],
            self.config.get_config()['port'],
            self.config.get_config()['client_id']
        )
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        return self.wrapper.get_account_info()
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """获取持仓信息"""
        return self.wrapper.get_positions()
    
    def place_order(self, contract: Contract, order: Order) -> Dict[str, Any]:
        """下单"""
        return self.client.placeOrder(
            self.client.get_next_order_id(),
            contract,
            order
        )
    
    def cancel_order(self, order_id: int) -> Dict[str, Any]:
        """撤单"""
        return self.client.cancelOrder(order_id)
    
    def get_order_status(self, order_id: int) -> Dict[str, Any]:
        """获取订单状态"""
        return self.wrapper.get_order_status(order_id)
    
    def get_open_orders(self) -> List[Dict[str, Any]]:
        """获取未完成订单"""
        return self.wrapper.get_open_orders()
    
    def get_order_history(self) -> List[Dict[str, Any]]:
        """获取订单历史"""
        return self.wrapper.get_order_history()
    
    def get_contract_details(self, contract: Contract) -> Dict[str, Any]:
        """获取合约详情"""
        return self.client.get_contract_details(contract)
    
    def get_market_data(self, contract: Contract) -> Dict[str, Any]:
        """获取市场数据"""
        return self.client.get_market_data(contract)
    
    def get_historical_data(self, contract: Contract, 
                          end_date: str, duration: str, 
                          bar_size: str) -> List[Dict[str, Any]]:
        """获取历史数据"""
        return self.client.get_historical_data(
            contract,
            end_date,
            duration,
            bar_size
        )
    
    def disconnect(self) -> None:
        """断开连接"""
        self.client.disconnect() 