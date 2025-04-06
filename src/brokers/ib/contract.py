from typing import Dict, Any, List
from ibapi.contract import Contract
from src.brokers.ib.client import IBClientManager

class IBContractManager:
    """Interactive Brokers合约管理类"""
    
    def __init__(self, client: IBClientManager):
        """
        初始化合约管理
        
        Args:
            client: IB客户端
        """
        self.client = client
        self.contract_cache = {}
    
    def get_contract_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取合约信息
        
        Args:
            symbol: 交易标的
            
        Returns:
            合约信息
        """
        if symbol in self.contract_cache:
            return self.contract_cache[symbol]
        
        contract = self._create_contract(symbol)
        contract_info = self.client.get_contract_details(contract)
        
        self.contract_cache[symbol] = contract_info
        return contract_info
    
    def get_contract_list(self) -> List[Dict[str, Any]]:
        """
        获取合约列表
        
        Returns:
            合约列表
        """
        return self.client.get_contract_list()
    
    def get_contract_specs(self, symbol: str) -> Dict[str, Any]:
        """
        获取合约规格
        
        Args:
            symbol: 交易标的
            
        Returns:
            合约规格
        """
        contract_info = self.get_contract_info(symbol)
        return contract_info['specs']
    
    def get_margin_requirements(self, symbol: str) -> Dict[str, Any]:
        """
        获取保证金要求
        
        Args:
            symbol: 交易标的
            
        Returns:
            保证金要求
        """
        contract_info = self.get_contract_info(symbol)
        return contract_info['margin_requirements']
    
    def get_commission_rates(self, symbol: str) -> Dict[str, Any]:
        """
        获取佣金费率
        
        Args:
            symbol: 交易标的
            
        Returns:
            佣金费率
        """
        contract_info = self.get_contract_info(symbol)
        return contract_info['commission_rates']
    
    def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """
        获取期权链
        
        Args:
            symbol: 交易标的
            
        Returns:
            期权链
        """
        contract_info = self.get_contract_info(symbol)
        return contract_info['option_chain']
    
    def _create_contract(self, symbol: str) -> Contract:
        """创建合约对象"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = 'STK'
        contract.exchange = 'SMART'
        contract.currency = 'USD'
        return contract 