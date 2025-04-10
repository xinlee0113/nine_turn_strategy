"""
数据接口模块包，包含各种数据源的实现。
用于提供市场数据获取功能。
"""

from .base_data import BaseData
from .tiger_csv_data import TigerCsvData
from .pandas_data import PandasData
from .realtime_data import RealtimeData

__all__ = [
    'BaseData',
    'PandasData',
    'TigerCsvData',
    'RealtimeData'
]
