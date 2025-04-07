"""
老虎证券数据类
"""
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from dataclasses import dataclass
from src.interface.data.base_data import BaseData
from src.interface.broker.tiger.tiger_client import TigerClient

@dataclass
class BarData:
    """K线数据"""
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    datetime: datetime

@dataclass
class TickData:
    """Tick数据"""
    symbol: str
    last_price: float
    volume: float
    datetime: datetime
    bid_price_1: float = 0.0
    bid_volume_1: float = 0.0
    ask_price_1: float = 0.0
    ask_volume_1: float = 0.0

class TigerData(BaseData):
    """老虎证券数据类"""
    
    def __init__(self, client: TigerClient):
        super().__init__()
        self.client = client
        
    def start(self) -> bool:
        """启动数据源"""
        return self.client.connect()
        
    def stop(self) -> bool:
        """停止数据源"""
        return self.client.disconnect()
        
    def get_historical_data(self, symbol: str, start_date: datetime, 
                          end_date: datetime, interval: str = "1m") -> pd.DataFrame:
        """获取历史数据"""
        return self.client.get_historical_data(symbol, start_date, end_date, interval)
        
    def get_realtime_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """获取实时行情"""
        return self.client.get_realtime_quotes(symbols) 