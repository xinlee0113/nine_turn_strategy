"""
数据接口模块包，包含各种数据源的实现。
用于提供市场数据获取功能。
"""

from .tiger_csv_data import TigerCsvData

__all__ = [
    'TigerCsvData',
]
