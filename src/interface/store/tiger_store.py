"""
老虎证券数据存储类
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import os
import logging
from src.interface.store.base_store import DataStoreBase

class TigerStore(DataStoreBase):
    """老虎证券数据存储类"""
    
    def __init__(self, client=None):
        super().__init__()
        self.client = client
        self.logger = logging.getLogger(__name__)
        self.cache_dir = os.path.join("data", "cache", "tiger")
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def start(self) -> bool:
        """启动数据存储"""
        return True
        
    def stop(self) -> bool:
        """停止数据存储"""
        return True
        
    def get_historical_data(self, symbol: str, start_date: datetime, 
                          end_date: datetime, interval: str = "1m") -> pd.DataFrame:
        """获取历史数据，支持缓存"""
        if self.client is None:
            raise ValueError("客户端未初始化")
            
        try:
            # 检查并获取缓存数据
            cached_data = self._get_cached_data(symbol, start_date, end_date, interval)
            if cached_data is not None:
                self.logger.info("使用缓存数据")
                return cached_data
                
            # 分段获取数据
            all_data = []
            current_start = start_date
            while current_start < end_date:
                # 计算当前段的结束时间（2天后）
                current_end = min(current_start + timedelta(days=2), end_date)
                
                # 从API获取数据 - 在测试环境中不需要等待
                self.logger.info(f"获取数据段: {current_start} 到 {current_end}")
                segment_data = self.client.get_historical_data(symbol, current_start, current_end, interval)
                
                if not segment_data.empty:
                    all_data.append(segment_data)
                    # 保存到缓存
                    self._save_to_daily_cache(segment_data, symbol, interval)
                
                # 更新开始时间
                current_start = current_end
                
            # 合并所有数据段
            if all_data:
                final_data = pd.concat(all_data)
                final_data = final_data[~final_data.index.duplicated(keep='first')]
                final_data.sort_index(inplace=True)
                return final_data
            
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"获取历史数据失败: {str(e)}")
            raise
            
    def get_realtime_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """获取实时行情"""
        if self.client is None:
            raise ValueError("客户端未初始化")
            
        return self.client.get_realtime_quotes(symbols)
        
    def _get_cached_data(self, symbol: str, start_date: datetime, 
                        end_date: datetime, interval: str) -> Optional[pd.DataFrame]:
        """智能获取缓存数据，支持部分缓存"""
        try:
            # 获取所有可用的缓存文件
            cache_files = self._find_cache_files(symbol, interval)
            if not cache_files:
                return None
                
            # 读取并合并缓存数据
            cached_data = []
            for cache_file in cache_files:
                try:
                    data = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
                    if not data.empty:
                        cached_data.append(data)
                except Exception as e:
                    self.logger.warning(f"读取缓存文件 {cache_file} 失败: {str(e)}")
                    continue
                    
            if not cached_data:
                return None
                
            # 合并所有缓存数据
            all_data = pd.concat(cached_data)
            all_data = all_data[~all_data.index.duplicated(keep='first')]
            all_data.sort_index(inplace=True)
            
            # 检查是否完全覆盖请求的时间范围
            if (all_data.index.min() <= start_date and 
                all_data.index.max() >= end_date):
                # 返回请求的时间范围内的数据
                return all_data[start_date:end_date]
                
            return None
            
        except Exception as e:
            self.logger.error(f"获取缓存数据失败: {str(e)}")
            return None
            
    def _save_to_daily_cache(self, data: pd.DataFrame, symbol: str, interval: str):
        """按天保存数据到缓存"""
        try:
            # 按天分组
            for date, day_data in data.groupby(data.index.date):
                cache_file = self._get_daily_cache_path(symbol, date, interval)
                
                # 如果文件已存在，合并数据
                if os.path.exists(cache_file):
                    try:
                        existing_data = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
                        day_data = pd.concat([existing_data, day_data])
                        day_data = day_data[~day_data.index.duplicated(keep='first')]
                        day_data.sort_index(inplace=True)
                    except Exception as e:
                        self.logger.warning(f"合并缓存数据失败: {str(e)}")
                
                # 保存到缓存文件
                try:
                    day_data.to_csv(cache_file)
                    self.logger.info(f"保存数据到缓存: {cache_file}")
                except Exception as e:
                    self.logger.error(f"保存缓存失败: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"保存数据到缓存失败: {str(e)}")
            
    def _get_daily_cache_path(self, symbol: str, date: datetime.date, interval: str) -> str:
        """获取每日缓存文件路径"""
        date_str = date.strftime("%Y%m%d")
        symbol_dir = os.path.join(self.cache_dir, symbol)
        os.makedirs(symbol_dir, exist_ok=True)
        return os.path.join(symbol_dir, f"{date_str}_{interval}.csv")
        
    def _find_cache_files(self, symbol: str, interval: str) -> List[str]:
        """查找符合条件的缓存文件"""
        symbol_dir = os.path.join(self.cache_dir, symbol)
        if not os.path.exists(symbol_dir):
            return []
            
        cache_files = []
        for file in os.listdir(symbol_dir):
            if file.endswith(f"_{interval}.csv"):
                cache_files.append(os.path.join(symbol_dir, file))
                
        return sorted(cache_files)  # 按文件名排序
        
    def get_data(self, **kwargs):
        """获取数据"""
        symbol = kwargs.get('symbol')
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        interval = kwargs.get('interval', '1m')
        
        if not all([symbol, start_date, end_date]):
            raise ValueError("get_data 需要 'symbol', 'start_date', 'end_date' 参数")
            
        return self.get_historical_data(symbol=symbol,
                                      start_date=start_date,
                                      end_date=end_date,
                                      interval=interval)
    
    def _handle_response(self):
        """处理响应"""
        # 实现响应处理逻辑
        pass 