from typing import Dict, Any, List, Optional
import pandas as pd
from .client import TigerClient

class TigerData:
    """数据获取类"""
    
    def __init__(self, client: TigerClient):
        """
        初始化数据获取器
        
        Args:
            client: 老虎证券客户端
        """
        self.client = client
    
    def get_historical_data(self, symbol: str, start_date: str, end_date: str,
                          interval: str = '1d') -> pd.DataFrame:
        """
        获取历史数据
        
        Args:
            symbol: 交易标的
            start_date: 开始日期
            end_date: 结束日期
            interval: 时间间隔（1m/5m/15m/30m/1h/1d）
            
        Returns:
            历史数据DataFrame
        """
        data = self.client._request('GET', '/market/history', params={
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date,
            'interval': interval
        })
        
        df = pd.DataFrame(data.get('data', []))
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df
    
    def get_realtime_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        获取实时行情
        
        Args:
            symbols: 交易标的列表
            
        Returns:
            实时行情数据
        """
        return self.client._request('GET', '/market/quotes', params={
            'symbols': ','.join(symbols)
        })
    
    def get_orderbook(self, symbol: str, depth: int = 10) -> Dict[str, Any]:
        """
        获取订单簿
        
        Args:
            symbol: 交易标的
            depth: 深度
            
        Returns:
            订单簿数据
        """
        return self.client._request('GET', '/market/orderbook', params={
            'symbol': symbol,
            'depth': depth
        })
    
    def get_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取成交记录
        
        Args:
            symbol: 交易标的
            limit: 限制数量
            
        Returns:
            成交记录列表
        """
        response = self.client._request('GET', '/market/trades', params={
            'symbol': symbol,
            'limit': limit
        })
        return response.get('trades', [])
    
    def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """
        获取基本面数据
        
        Args:
            symbol: 交易标的
            
        Returns:
            基本面数据
        """
        return self.client._request('GET', f'/market/fundamentals/{symbol}')
    
    def get_company_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取公司信息
        
        Args:
            symbol: 交易标的
            
        Returns:
            公司信息
        """
        return self.client._request('GET', f'/market/company/{symbol}')
    
    def get_news(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取新闻
        
        Args:
            symbol: 交易标的
            limit: 限制数量
            
        Returns:
            新闻列表
        """
        response = self.client._request('GET', '/market/news', params={
            'symbol': symbol,
            'limit': limit
        })
        return response.get('news', []) 