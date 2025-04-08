"""
Interactive Brokers市场状态实现
"""
import time
from datetime import datetime
from typing import Dict, Any, List

from ibapi.contract import Contract

from .client import IBClient


class IBMarket:
    """Interactive Brokers市场状态类"""

    def __init__(self, client: IBClient):
        """
        初始化市场状态
        
        Args:
            client: IB客户端
        """
        self.client = client
        self.market_status_cache = {}
        self.cache_timeout = 300  # 缓存超时时间（秒）

    def is_market_open(self, symbol: str) -> bool:
        """
        检查市场是否开放
        
        Args:
            symbol: 交易标的
            
        Returns:
            市场是否开放
        """
        if symbol in self.market_status_cache:
            cache_time, status = self.market_status_cache[symbol]
            if time.time() - cache_time < self.cache_timeout:
                return status

        # 获取市场状态
        contract = self._create_contract(symbol)
        market_status = self.client.get_market_data(contract)

        # 更新缓存
        self.market_status_cache[symbol] = (time.time(), market_status['is_open'])

        return market_status['is_open']

    def get_trading_hours(self, symbol: str) -> Dict[str, Any]:
        """
        获取交易时间
        
        Args:
            symbol: 交易标的
            
        Returns:
            交易时间信息
        """
        contract = self._create_contract(symbol)
        return self.client.get_contract_details(contract)['trading_hours']

    def get_holidays(self, symbol: str) -> List[str]:
        """
        获取节假日
        
        Args:
            symbol: 交易标的
            
        Returns:
            节假日列表
        """
        contract = self._create_contract(symbol)
        return self.client.get_contract_details(contract)['holidays']

    def is_trading_time(self, symbol: str) -> bool:
        """
        检查是否在交易时间
        
        Args:
            symbol: 交易标的
            
        Returns:
            是否在交易时间
        """
        if not self.is_market_open(symbol):
            return False

        trading_hours = self.get_trading_hours(symbol)
        now = datetime.now()

        for session in trading_hours['sessions']:
            start_time = datetime.strptime(session['start'], '%H:%M').time()
            end_time = datetime.strptime(session['end'], '%H:%M').time()

            if start_time <= now.time() <= end_time:
                return True

        return False

    def _create_contract(self, symbol: str) -> Contract:
        """创建合约对象"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = 'STK'
        contract.exchange = 'SMART'
        contract.currency = 'USD'
        return contract
