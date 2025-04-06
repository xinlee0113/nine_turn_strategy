from typing import Dict, Any, List, Optional
from .client import TigerClient

class ContractManager:
    """合约管理类"""
    
    def __init__(self, client: TigerClient):
        """
        初始化合约管理器
        
        Args:
            client: 老虎证券客户端
        """
        self.client = client
        self._contract_cache = {}
    
    def get_contract_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取合约信息
        
        Args:
            symbol: 交易标的
            
        Returns:
            合约信息
        """
        if symbol in self._contract_cache:
            return self._contract_cache[symbol]
        
        info = self.client._request('GET', f'/contract/info/{symbol}')
        self._contract_cache[symbol] = info
        return info
    
    def get_contract_list(self, exchange: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取合约列表
        
        Args:
            exchange: 交易所，None表示所有交易所
            
        Returns:
            合约列表
        """
        endpoint = '/contract/list'
        if exchange:
            endpoint += f'?exchange={exchange}'
        response = self.client._request('GET', endpoint)
        return response.get('contracts', [])
    
    def get_contract_specs(self, symbol: str) -> Dict[str, Any]:
        """
        获取合约规格
        
        Args:
            symbol: 交易标的
            
        Returns:
            合约规格
        """
        return self.client._request('GET', f'/contract/specs/{symbol}')
    
    def get_margin_requirements(self, symbol: str) -> Dict[str, Any]:
        """
        获取保证金要求
        
        Args:
            symbol: 交易标的
            
        Returns:
            保证金要求
        """
        return self.client._request('GET', f'/contract/margin/{symbol}')
    
    def get_commission_rate(self, symbol: str) -> Dict[str, Any]:
        """
        获取佣金费率
        
        Args:
            symbol: 交易标的
            
        Returns:
            佣金费率
        """
        return self.client._request('GET', f'/contract/commission/{symbol}')
    
    def get_option_chain(self, symbol: str, expiry: Optional[str] = None) -> Dict[str, Any]:
        """
        获取期权链
        
        Args:
            symbol: 标的股票
            expiry: 到期日，None表示所有到期日
            
        Returns:
            期权链信息
        """
        endpoint = f'/contract/option/chain/{symbol}'
        if expiry:
            endpoint += f'?expiry={expiry}'
        return self.client._request('GET', endpoint) 