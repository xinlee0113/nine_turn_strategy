"""
测试 TigerStore 的数据获取和缓存功能
"""
import unittest
from datetime import datetime, timedelta
import pandas as pd
import os
import shutil
from src.interface.store.tiger_store import TigerStore
from src.interface.broker.tiger.tiger_client import TigerClient
import time
import pytz

class TestTigerStore(unittest.TestCase):
    """测试 TigerStore 类"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        # 初始化 TigerClient
        cls.client = TigerClient()
        cls.client.connect()
        
        # 初始化 TigerStore
        cls.store = TigerStore(cls.client)
        
        # 设置测试参数 - 使用过去30天的数据（使用NYC时区，与美股交易时间一致）
        cls.symbol = "US.AAPL"
        ny_tz = pytz.timezone('America/New_York')
        cls.end_time = datetime.now(ny_tz)
        cls.start_time = cls.end_time - timedelta(days=10)  # 减少为10天，加快测试速度
        cls.interval = "1m"
        
        # 打印测试参数
        print(f"\n测试参数信息:")
        print(f"开始时间(NYC): {cls.start_time}")
        print(f"结束时间(NYC): {cls.end_time}")
        print(f"股票代码: {cls.symbol}")
        print(f"周期: {cls.interval}")
        
        # 确保缓存目录存在
        symbol_dir = os.path.join(cls.store.cache_dir, cls.symbol)
        os.makedirs(symbol_dir, exist_ok=True)
        
    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        cls.store.stop()
        # 清理缓存目录
        if os.path.exists(cls.store.cache_dir):
            shutil.rmtree(cls.store.cache_dir)
            
    def setUp(self):
        """每个测试用例开始前执行"""
        # 确保缓存目录存在
        os.makedirs(self.store.cache_dir, exist_ok=True)
        
    def tearDown(self):
        """每个测试用例结束后执行"""
        # 清理缓存文件
        if os.path.exists(self.store.cache_dir):
            shutil.rmtree(self.store.cache_dir)
            
    def test_get_historical_data_no_cache(self):
        """测试无缓存时获取历史数据"""
        # 获取数据
        data = self.store.get_historical_data(
            symbol=self.symbol,
            start_date=self.start_time,
            end_date=self.end_time,
            interval=self.interval
        )
        
        # 验证数据
        self.assertIsNotNone(data)
        self.assertIsInstance(data, pd.DataFrame)
        self.assertFalse(data.empty)
        
        # 验证数据列
        expected_columns = ['open', 'high', 'low', 'close', 'volume']
        self.assertListEqual(list(data.columns), expected_columns)
        
        # 验证数据时间范围
        data_start = data.index.min()
        data_end = data.index.max()
        days_diff = (data_end - data_start).days
        self.assertGreaterEqual(days_diff, 5)  # 至少应该有5个交易日的数据（工作日）
        
        # 验证是否为分钟级数据
        time_diffs = data.index.to_series().diff().dropna()
        self.assertEqual(time_diffs.min(), pd.Timedelta(minutes=1))
        
    def test_cache_creation(self):
        """测试数据缓存创建"""
        # 获取数据（会创建缓存）
        data = self.store.get_historical_data(
            symbol=self.symbol,
            start_date=self.start_time,
            end_date=self.end_time,
            interval=self.interval
        )
        
        # 验证缓存目录结构
        symbol_dir = os.path.join(self.store.cache_dir, self.symbol)
        self.assertTrue(os.path.exists(symbol_dir))
        
        # 验证是否创建了缓存文件
        cache_files = self.store._find_cache_files(self.symbol, self.interval)
        self.assertGreater(len(cache_files), 0)
        
        # 验证缓存文件内容
        all_cached_data = []
        for cache_file in cache_files:
            cached_data = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
            all_cached_data.append(cached_data)
            
        # 合并所有缓存数据
        cached_data = pd.concat(all_cached_data)
        cached_data = cached_data[~cached_data.index.duplicated(keep='first')]
        cached_data.sort_index(inplace=True)
        
        # 验证缓存的数据与原始数据匹配
        pd.testing.assert_frame_equal(
            data.sort_index(),
            cached_data[data.index.min():data.index.max()].sort_index()
        )
        
    def test_cache_usage(self):
        """测试使用缓存数据"""
        # 首次获取数据（创建缓存）
        data1 = self.store.get_historical_data(
            symbol=self.symbol,
            start_date=self.start_time,
            end_date=self.end_time,
            interval=self.interval
        )
        
        # 再次获取相同时间范围的数据（应该使用缓存）
        data2 = self.store.get_historical_data(
            symbol=self.symbol,
            start_date=self.start_time,
            end_date=self.end_time,
            interval=self.interval
        )
        
        # 验证两次获取的数据相同
        pd.testing.assert_frame_equal(data1, data2)
        
    def test_overlapping_cache(self):
        """测试重叠时间范围的缓存处理"""
        # 获取前20天的数据
        mid_date = self.end_time - timedelta(days=10)
        
        # 获取前半段数据
        data1 = self.store.get_historical_data(
            symbol=self.symbol,
            start_date=self.start_time,
            end_date=mid_date,
            interval=self.interval
        )
        
        # 获取后半段数据
        data2 = self.store.get_historical_data(
            symbol=self.symbol,
            start_date=mid_date,
            end_date=self.end_time,
            interval=self.interval
        )
        
        # 获取完整时间范围的数据
        data_full = self.store.get_historical_data(
            symbol=self.symbol,
            start_date=self.start_time,
            end_date=self.end_time,
            interval=self.interval
        )
        
        # 验证数据连续性
        self.assertGreaterEqual(len(data_full), len(data1) + len(data2) - 390)  # 减去一天的重叠数据
        
    def test_data_validation(self):
        """测试数据验证"""
        data = self.store.get_historical_data(
            symbol=self.symbol,
            start_date=self.start_time,
            end_date=self.end_time,
            interval=self.interval
        )
        
        # 打印数据统计信息
        print("\n获取到的30天数据信息:")
        print(f"数据条数: {len(data)}")
        print(f"时间范围: {data.index.min()} 到 {data.index.max()}")
        print(f"数据列: {list(data.columns)}")
        print("\n数据样例:")
        print(data.head())
        
        # 计算每个交易日的统计信息
        daily_stats = []
        for date, group in data.groupby(data.index.to_series().dt.date):
            stats = {
                'date': date,
                'count': len(group),
                'start_time': group.index.min(),
                'end_time': group.index.max(),
                'duration_minutes': (group.index.max() - group.index.min()).total_seconds() / 60
            }
            daily_stats.append(stats)
            
            print(f"\n交易日 {date} 数据统计:")
            print(f"数据点数量: {stats['count']}")
            print(f"交易时间范围: {stats['start_time']} 到 {stats['end_time']}")
            print(f"交易时长: {stats['duration_minutes']} 分钟")
            
            # 验证每个交易日的数据点数量（美股通常每天390个数据点）
            if stats['count'] < 351:  # 允许一定的数据缺失
                print(f"警告: 交易日 {date} 数据点数量不足（期望至少351个点，实际{stats['count']}个点）")
                
        # 计算交易日数量
        trading_days = len(daily_stats)
        print(f"\n总交易日数: {trading_days}")
        
        # 验证数据质量
        self.assertGreaterEqual(trading_days, 20)  # 至少应该有20个交易日
        
if __name__ == '__main__':
    unittest.main() 