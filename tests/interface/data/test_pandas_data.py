"""
PandasData测试类
"""
import unittest
from datetime import datetime, timedelta

import pandas as pd

from src.infrastructure.config import DataConfig
from src.interface.data.pandas_data import PandasData


class TestPandasData(unittest.TestCase):
    """PandasData测试类"""

    def setUp(self):
        """测试初始化"""
        self.config = DataConfig()
        self.data_source = PandasData()

    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.data_source)
        self.assertFalse(self.data_source.started)

    def test_start_stop(self):
        """测试启动和停止"""
        # 测试启动
        result = self.data_source.start()
        self.assertTrue(result)
        self.assertTrue(self.data_source.started)

        # 测试停止
        result = self.data_source.stop()
        self.assertTrue(result)
        self.assertFalse(self.data_source.started)

    def test_get_data(self):
        """测试获取数据"""
        # 先启动
        self.data_source.start()

        # 测试获取数据
        symbol = "AAPL"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        data = self.data_source.get_data(symbol, start_date, end_date)
        self.assertIsNotNone(data)
        self.assertIsInstance(data, pd.DataFrame)

    def test_get_realtime_quotes(self):
        """测试获取实时行情"""
        # 先启动
        self.data_source.start()

        # 测试获取行情
        symbol = "AAPL"
        quote = self.data_source.get_realtime_quotes(symbol)

        self.assertIsNotNone(quote)
        self.assertIsInstance(quote, dict)


if __name__ == '__main__':
    unittest.main()
