"""
数据存储基类
定义标准接口
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional
import pandas as pd

class DataStoreBase(ABC):
    @abstractmethod
    def start(self) -> bool:
        """启动数据存储"""
        pass
        
    @abstractmethod
    def stop(self) -> bool:
        """停止数据存储"""
        pass
        
    @abstractmethod
    def get_historical_data(self, symbol: str, start_date: datetime, 
                          end_date: datetime) -> Optional[pd.DataFrame]:
        """获取历史数据"""
        pass
        
    @abstractmethod
    def get_realtime_quotes(self, symbol: str) -> Optional[Dict]:
        """获取实时行情"""
        pass
        
    def get_data(self, symbol: str, start_date: datetime = None, 
                end_date: datetime = None) -> Optional[pd.DataFrame]:
        """获取数据（历史或实时）"""
        if start_date and end_date:
            return self.get_historical_data(symbol, start_date, end_date)
        else:
            quote = self.get_realtime_quotes(symbol)
            if quote:
                return pd.DataFrame([quote])
            return None 