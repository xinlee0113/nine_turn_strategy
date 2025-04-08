import logging
import os
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from .tiger_client import TigerClient
from .tiger_config import TigerConfig
from ..store.base_store import DataStoreBase


class TigerStore(DataStoreBase):
    def __init__(self, config: TigerConfig):
        super().__init__()
        self.config = config
        self.client = TigerClient(config)
        self.logger = logging.getLogger(__name__)

    def start(self) -> bool:
        """启动数据存储"""
        try:
            self.client.connect()
            return True
        except Exception as e:
            self.logger.error(f"启动数据存储失败: {str(e)}")
            return False

    def stop(self) -> bool:
        """停止数据存储"""
        try:
            self.client.disconnect()
            return True
        except Exception as e:
            self.logger.error(f"停止数据存储失败: {str(e)}")
            return False

    def _check_cache(self, symbol: str, start_date: datetime,
                     end_date: datetime, interval: str) -> Optional[pd.DataFrame]:
        """
        检查缓存是否存在
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            interval: 数据间隔
            
        Returns:
            DataFrame: 如果缓存存在则返回数据，否则返回None
        """
        cache_file = self._get_cache_file_path(symbol, start_date, end_date, interval)
        if os.path.exists(cache_file):
            try:
                return pd.read_csv(cache_file, index_col=0, parse_dates=True)
            except Exception as e:
                self.logger.warning(f"读取缓存文件失败: {str(e)}")
        return None

    def _save_to_cache(self, data: pd.DataFrame, symbol: str,
                       start_date: datetime, end_date: datetime, interval: str):
        """
        保存数据到缓存
        
        Args:
            data: 要保存的数据
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            interval: 数据间隔
        """
        cache_file = self._get_cache_file_path(symbol, start_date, end_date, interval)
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        data.to_csv(cache_file)

    def _get_cache_file_path(self, symbol: str, start_date: datetime,
                             end_date: datetime, interval: str) -> str:
        """
        获取缓存文件路径
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            interval: 数据间隔
            
        Returns:
            str: 缓存文件路径
        """
        cache_dir = os.path.join(self.config.cache_dir, "historical_data")
        filename = f"{symbol}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{interval}.csv"
        return os.path.join(cache_dir, filename)

    def get_historical_data(self, symbol: str, start_date: datetime,
                            end_date: datetime) -> Optional[pd.DataFrame]:
        """
        获取历史数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame: 包含OHLCV数据的DataFrame
        """
        try:
            # 检查缓存
            cache_data = self._check_cache(symbol, start_date, end_date, "1m")
            if cache_data is not None:
                return cache_data

            # 从API获取数据
            data = self.client.get_historical_data(symbol, start_date, end_date, "1m")

            # 保存到缓存
            self._save_to_cache(data, symbol, start_date, end_date, "1m")

            return data
        except Exception as e:
            self.logger.error(f"获取历史数据失败: {str(e)}")
            raise

    def get_realtime_quotes(self, symbol: str) -> Optional[Dict]:
        """
        获取实时行情
        
        Args:
            symbol: 股票代码
            
        Returns:
            Dict: 实时行情数据
        """
        try:
            quotes = self.client.get_realtime_quotes([symbol])
            return quotes.get(symbol)
        except Exception as e:
            self.logger.error(f"获取实时行情失败: {str(e)}")
            raise

    def get_account_info(self) -> Dict:
        """
        获取账户信息
        
        Returns:
            Dict: 账户信息
        """
        try:
            return self.client.get_account_info()
        except Exception as e:
            self.logger.error(f"获取账户信息失败: {str(e)}")
            raise

    def place_order(self, symbol: str, quantity: int, order_type: str,
                    price: float, side: str) -> str:
        """
        下单
        
        Args:
            symbol: 股票代码
            quantity: 数量
            order_type: 订单类型
            price: 价格
            side: 买卖方向
            
        Returns:
            str: 订单ID
        """
        try:
            return self.client.place_order(symbol, quantity, order_type, price, side)
        except Exception as e:
            self.logger.error(f"下单失败: {str(e)}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        """
        撤单
        
        Args:
            order_id: 订单ID
            
        Returns:
            bool: 是否成功
        """
        try:
            return self.client.cancel_order(order_id)
        except Exception as e:
            self.logger.error(f"撤单失败: {str(e)}")
            raise

    def get_order_status(self, order_id: str) -> Dict:
        """
        获取订单状态
        
        Args:
            order_id: 订单ID
            
        Returns:
            Dict: 订单状态信息
        """
        try:
            return self.client.get_order_status(order_id)
        except Exception as e:
            self.logger.error(f"获取订单状态失败: {str(e)}")
            raise
