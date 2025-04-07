"""
老虎证券数据类型定义和数据获取实现
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
from tigeropen.common.consts import BarPeriod
from .tiger_client import TigerClient

@dataclass
class BarData:
    """K线数据"""
    
    # 基本信息
    symbol: str
    datetime: datetime
    interval: str
    
    # 价格数据
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    # 其他数据
    open_interest: float = 0.0
    turnover: float = 0.0

@dataclass
class TickData:
    """Tick数据"""
    
    # 基本信息
    symbol: str
    datetime: datetime
    
    # 价格数据
    last_price: float
    last_volume: float
    bid_price_1: float
    bid_volume_1: float
    ask_price_1: float
    ask_volume_1: float
    
    # 其他数据
    open_interest: float = 0.0
    turnover: float = 0.0

class TigerData:
    """老虎证券数据获取类"""
    
    def __init__(self, client: TigerClient):
        """
        初始化数据获取
        
        Args:
            client: Tiger客户端
        """
        self.client = client
        self.data_cache = {}
    
    def get_historical_data(self, symbol: str, start_date: datetime, 
                          end_date: datetime, period: str = '1m') -> Optional[pd.DataFrame]:
        """
        获取历史数据
        
        Args:
            symbol: 交易标的
            start_date: 开始日期
            end_date: 结束日期
            period: K线周期
            
        Returns:
            历史数据
        """
        try:
            # 转换周期字符串为Tiger API枚举值
            tiger_period = self._convert_period(period)
            
            # 转换时间戳
            begin_timestamp = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000)
            
            # 获取数据
            bars = self.client.get_bars(
                symbols=[symbol],
                period=tiger_period,
                begin_time=begin_timestamp,
                end_time=end_timestamp,
                limit=5000
            )
            
            if isinstance(bars, pd.DataFrame) and not bars.empty:
                df = bars.copy()
                df['datetime'] = pd.to_datetime(df['time'], unit='ms')
                df.set_index('datetime', inplace=True)
                df.sort_index(inplace=True)
                return df
            
            return None
        except Exception as e:
            print(f"获取历史数据失败: {str(e)}")
            return None
    
    def get_realtime_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        获取实时行情
        
        Args:
            symbols: 交易标的列表
            
        Returns:
            实时行情
        """
        try:
            quotes = {}
            for symbol in symbols:
                quote = self.client.get_market_data(symbol)
                if quote:
                    quotes[symbol] = quote
            return quotes
        except Exception as e:
            print(f"获取实时行情失败: {str(e)}")
            return {}
    
    def _convert_period(self, period: str) -> BarPeriod:
        """转换周期字符串为Tiger API枚举值"""
        period_map = {
            '1m': BarPeriod.ONE_MINUTE,
            '5m': BarPeriod.FIVE_MINUTES,
            '15m': BarPeriod.FIFTEEN_MINUTES,
            '30m': BarPeriod.HALF_HOUR,
            '60m': BarPeriod.ONE_HOUR,
            '1h': BarPeriod.ONE_HOUR,
            'day': BarPeriod.DAY,
            'week': BarPeriod.WEEK,
            'month': BarPeriod.MONTH,
            'year': BarPeriod.YEAR
        }
        return period_map.get(period, BarPeriod.ONE_MINUTE) 