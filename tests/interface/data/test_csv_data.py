"""
CSVData测试类
"""
import os
import shutil
import unittest
from datetime import datetime

import pandas as pd

from src.infrastructure.config import DataConfig
from src.interface.data.csv_data import CSVData


class TestCSVData(unittest.TestCase):
    """CSVData测试类"""

    def setUp(self):
        """测试初始化"""
        # 创建测试用的临时目录
        self.test_dir = "test_cache"
        os.makedirs(self.test_dir, exist_ok=True)

        # 创建测试配置
        self.config = DataConfig()
        self.config.set("cache_dir", self.test_dir)

        # 创建测试数据
        self.test_data = pd.DataFrame({
            'open': [100.0, 101.0, 102.0],
            'high': [101.0, 102.0, 103.0],
            'low': [99.0, 100.0, 101.0],
            'close': [100.5, 101.5, 102.5],
            'volume': [1000, 2000, 3000]
        }, index=pd.date_range(start='2023-01-01', periods=3, freq='D'))

        self.data_source = CSVData(self.test_dir)

    def tearDown(self):
        """测试清理"""
        # 删除测试目录
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.data_source)
        self.assertEqual(self.data_source.cache_dir, self.test_dir)

    def test_save_and_load_data(self):
        """测试保存和加载数据"""
        # 测试数据
        symbol = "AAPL"
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 3)
        interval = "1d"

        # 保存数据
        self.data_source.save_data(self.test_data, symbol, start_date, end_date, interval)

        # 检查文件是否存在
        cache_file = os.path.join(self.test_dir,
                                  f"{symbol}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{interval}.csv")
        self.assertTrue(os.path.exists(cache_file))

        # 加载数据
        loaded_data = self.data_source.load_data(symbol, start_date, end_date, interval)

        # 验证数据
        self.assertIsNotNone(loaded_data)
        self.assertIsInstance(loaded_data, pd.DataFrame)
        pd.testing.assert_frame_equal(self.test_data, loaded_data)

    def test_check_cache(self):
        """测试检查缓存"""
        # 测试数据
        symbol = "AAPL"
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 3)
        interval = "1d"

        # 先保存数据
        self.data_source.save_data(self.test_data, symbol, start_date, end_date, interval)

        # 检查缓存
        cache_data = self.data_source.check_cache(symbol, start_date, end_date, interval)
        self.assertIsNotNone(cache_data)
        self.assertIsInstance(cache_data, pd.DataFrame)
        pd.testing.assert_frame_equal(self.test_data, cache_data)

    def test_get_cache_file_path(self):
        """测试获取缓存文件路径"""
        # 测试数据
        symbol = "AAPL"
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 3)
        interval = "1d"

        # 获取文件路径
        cache_file = self.data_source.get_cache_file_path(symbol, start_date, end_date, interval)

        # 验证路径格式
        expected_path = os.path.join(self.test_dir,
                                     f"{symbol}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{interval}.csv")
        self.assertEqual(cache_file, expected_path)

    def test_cache_miss(self):
        """测试缓存未命中"""
        # 测试数据
        symbol = "AAPL"
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 3)
        interval = "1d"

        # 检查不存在的缓存
        cache_data = self.data_source.check_cache(symbol, start_date, end_date, interval)
        self.assertIsNone(cache_data)


if __name__ == '__main__':
    unittest.main()
