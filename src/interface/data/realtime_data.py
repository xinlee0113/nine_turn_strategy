"""
实时数据源实现，用于获取实时行情数据
"""
import logging
from datetime import datetime
from typing import Dict, Optional, List

import pandas as pd

from src.interface.broker.tiger.tiger_client import TigerClient
from src.interface.store.tiger_store import TigerStore
from .base_data import BaseData


class RealtimeData(BaseData):
    """实时数据接口，用于获取实时行情数据"""

    def __init__(self, symbols: List[str] = None):
        """初始化实时数据源
        
        Args:
            symbols: 需要订阅的交易标的列表
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.symbols = symbols or []
        self.connected = False
        self.last_data = {}  # 存储最新数据
        self.last_update_time = None
        self.subscription_active = False

        try:
            client = TigerClient()
            client.connect()
            self.store = TigerStore(client=client)
            self.logger.info("实时数据源初始化成功")
        except Exception as e:
            self.logger.error(f"初始化实时数据源失败: {e}")
            self.store = None
            raise

    def start(self) -> bool:
        """启动数据源"""
        if self.store is None:
            self.logger.error("数据存储未成功初始化，无法启动")
            return False

        try:
            if not self.connected:
                success = self.store.start()
                if success:
                    self.connected = True
                    self.logger.info("实时数据源启动成功")

                    # 订阅行情（如果有）
                    if self.symbols:
                        self._subscribe_quotes(self.symbols)
                return success
            return True
        except Exception as e:
            self.logger.error(f"启动实时数据源失败: {str(e)}")
            return False

    def stop(self) -> bool:
        """停止数据源"""
        if self.store is None:
            self.logger.warning("数据存储未初始化，无需停止")
            return True

        try:
            if self.connected:
                # 取消订阅
                if self.subscription_active and self.symbols:
                    self._unsubscribe_quotes(self.symbols)

                # 停止存储
                success = self.store.stop()
                if success:
                    self.connected = False
                    self.last_data = {}
                    self.last_update_time = None
                    self.logger.info("实时数据源停止成功")
                return success
            return True
        except Exception as e:
            self.logger.error(f"停止实时数据源失败: {str(e)}")
            return False

    def get_data(self, symbol: str = None, **kwargs) -> Optional[pd.DataFrame]:
        """获取最新实时数据
        
        Args:
            symbol: 交易标的代码，如果为None则返回所有订阅的数据
            
        Returns:
            DataFrame: 包含最新实时数据的DataFrame
        """
        # 直接使用get_realtime_quotes获取实时行情
        quotes = self.get_realtime_quotes([symbol] if symbol else self.symbols)

        if not quotes:
            return pd.DataFrame()

        # 将字典转换为DataFrame
        df_rows = []
        for sym, quote in quotes.items():
            if quote:
                row = {
                    'symbol': sym,
                    'datetime': quote.get('timestamp', datetime.now()),
                    'last_price': quote.get('last_price'),
                    'open': quote.get('open'),
                    'high': quote.get('high'),
                    'low': quote.get('low'),
                    'close': quote.get('last_price'),  # 使用最新价格作为收盘价
                    'volume': quote.get('volume'),
                    'bid': quote.get('bid'),
                    'ask': quote.get('ask'),
                    'bid_size': quote.get('bid_size'),
                    'ask_size': quote.get('ask_size')
                }
                df_rows.append(row)

        if not df_rows:
            return pd.DataFrame()

        df = pd.DataFrame(df_rows)

        # 根据需要设置索引
        if 'datetime' in df.columns:
            df.set_index('datetime', inplace=True)

        return df

    def get_realtime_quotes(self, symbols: List[str] = None) -> Optional[Dict]:
        """获取实时行情
        
        Args:
            symbols: 交易标的代码列表，如果为None则使用订阅的标的
            
        Returns:
            Dict: 包含实时行情的字典，格式为 {symbol: quote_data}
        """
        if not self.connected:
            self.logger.warning("实时数据源未连接，尝试自动连接")
            if not self.start():
                raise ConnectionError("实时数据源启动失败")

        if self.store is None:
            raise RuntimeError("数据存储未成功初始化")

        try:
            # 使用传入的symbols或已订阅的symbols
            target_symbols = symbols if symbols is not None else self.symbols

            if not target_symbols:
                self.logger.warning("未指定要获取的交易标的")
                return {}

            self.logger.info(f"获取实时行情: {target_symbols}")
            quotes = self.store.get_realtime_quotes(target_symbols)

            # 更新缓存的最后数据
            if quotes:
                self.last_data.update(quotes)
                self.last_update_time = datetime.now()

            self.logger.info(f"获取实时行情成功，共 {len(quotes)} 个标的")
            return quotes
        except Exception as e:
            self.logger.error(f"获取实时行情失败: {str(e)}")
            raise

    def get_historical_data(self, symbol: str, start_date: datetime,
                            end_date: datetime, interval: str = "1m") -> Optional[pd.DataFrame]:
        """获取历史数据（实时数据源不支持历史数据）"""
        self.logger.warning("实时数据源不支持获取历史数据")
        raise NotImplementedError("实时数据源不支持获取历史数据")

    def add_symbols(self, symbols: List[str]) -> bool:
        """添加要订阅的交易标的
        
        Args:
            symbols: 要添加的交易标的列表
            
        Returns:
            bool: 添加是否成功
        """
        try:
            # 去重并添加新的标的
            new_symbols = [sym for sym in symbols if sym not in self.symbols]
            if not new_symbols:
                self.logger.info("没有新的交易标的需要添加")
                return True

            self.logger.info(f"添加交易标的: {new_symbols}")
            self.symbols.extend(new_symbols)

            # 如果已连接，订阅新标的
            if self.connected:
                return self._subscribe_quotes(new_symbols)

            return True
        except Exception as e:
            self.logger.error(f"添加交易标的失败: {str(e)}")
            return False

    def remove_symbols(self, symbols: List[str]) -> bool:
        """移除已订阅的交易标的
        
        Args:
            symbols: 要移除的交易标的列表
            
        Returns:
            bool: 移除是否成功
        """
        try:
            # 找出存在于当前订阅中的标的
            to_remove = [sym for sym in symbols if sym in self.symbols]
            if not to_remove:
                self.logger.info("没有要移除的交易标的")
                return True

            self.logger.info(f"移除交易标的: {to_remove}")

            # 如果已连接，取消订阅
            if self.connected and self.subscription_active:
                self._unsubscribe_quotes(to_remove)

            # 从列表中移除
            self.symbols = [sym for sym in self.symbols if sym not in to_remove]

            # 从最后数据中移除
            for sym in to_remove:
                if sym in self.last_data:
                    del self.last_data[sym]

            return True
        except Exception as e:
            self.logger.error(f"移除交易标的失败: {str(e)}")
            return False

    def _subscribe_quotes(self, symbols: List[str]) -> bool:
        """订阅实时行情
        
        Args:
            symbols: 要订阅的交易标的列表
            
        Returns:
            bool: 订阅是否成功
        """
        try:
            if not symbols:
                return True

            self.logger.info(f"订阅实时行情: {symbols}")

            # 注意：这里实际上是通过get_realtime_quotes来模拟订阅
            # 因为Tiger API的Python SDK不直接支持推送订阅模式
            # 实际应用中，你可能需要配合Tiger API的推送功能
            self.get_realtime_quotes(symbols)

            self.subscription_active = True
            return True
        except Exception as e:
            self.logger.error(f"订阅实时行情失败: {str(e)}")
            return False

    def _unsubscribe_quotes(self, symbols: List[str]) -> bool:
        """取消订阅实时行情
        
        Args:
            symbols: 要取消订阅的交易标的列表
            
        Returns:
            bool: 取消订阅是否成功
        """
        try:
            if not symbols:
                return True

            self.logger.info(f"取消订阅实时行情: {symbols}")

            # 注意：因为没有真正的推送订阅，所以这里只是记录日志
            # 实际应用中，你需要调用Tiger API的取消订阅方法

            return True
        except Exception as e:
            self.logger.error(f"取消订阅实时行情失败: {str(e)}")
            return False
