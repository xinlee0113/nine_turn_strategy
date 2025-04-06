from typing import Dict, Any, List
import time
from .client import TigerClient

class MarketStatus:
    """市场状态管理类"""
    
    def __init__(self, client: TigerClient):
        """
        初始化市场状态管理器
        
        Args:
            client: 老虎证券客户端
        """
        self.client = client
        self._market_status_cache = {}
        self._last_update_time = 0
        self._cache_ttl = 60  # 缓存有效期（秒）
    
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        return time.time() - self._last_update_time < self._cache_ttl
    
    def get_market_status(self, symbol: str) -> Dict[str, Any]:
        """
        获取市场状态
        
        Args:
            symbol: 交易标的
            
        Returns:
            市场状态信息
        """
        if symbol in self._market_status_cache and self._is_cache_valid():
            return self._market_status_cache[symbol]
        
        status = self.client._request('GET', f'/market/status/{symbol}')
        self._market_status_cache[symbol] = status
        self._last_update_time = time.time()
        return status
    
    def is_market_open(self, symbol: str) -> bool:
        """
        检查市场是否开放
        
        Args:
            symbol: 交易标的
            
        Returns:
            市场是否开放
        """
        status = self.get_market_status(symbol)
        return status.get('is_open', False)
    
    def get_trading_hours(self, symbol: str) -> List[Dict[str, str]]:
        """
        获取交易时间
        
        Args:
            symbol: 交易标的
            
        Returns:
            交易时间段列表
        """
        status = self.get_market_status(symbol)
        return status.get('trading_hours', [])
    
    def get_holidays(self, symbol: str) -> List[str]:
        """
        获取假期列表
        
        Args:
            symbol: 交易标的
            
        Returns:
            假期日期列表
        """
        status = self.get_market_status(symbol)
        return status.get('holidays', [])
    
    def is_trading_time(self, symbol: str) -> bool:
        """
        检查当前是否为交易时间
        
        Args:
            symbol: 交易标的
            
        Returns:
            是否为交易时间
        """
        if not self.is_market_open(symbol):
            return False
        
        trading_hours = self.get_trading_hours(symbol)
        current_time = time.strftime('%H:%M:%S')
        
        for period in trading_hours:
            if period['start'] <= current_time <= period['end']:
                return True
        
        return False 