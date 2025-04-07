"""
TigerClient测试类
"""
import unittest
import pandas as pd
import time
from datetime import datetime, timedelta
import pytz
from src.interface.broker.tiger.tiger_client import TigerClient

class TestTigerClient(unittest.TestCase):
    """TigerClient测试类"""
    
    def setUp(self):
        """测试初始化"""
        # 创建TigerClient实例
        self.client = TigerClient()
        
        # 等待API限流重置
        time.sleep(10)
        
    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.client)
        self.assertFalse(self.client.connected)
        
    def test_get_historical_data(self):
        """测试获取30天1分钟K线数据"""
        # 先连接
        self.client.connect()
        
        # 设置时区
        utc_tz = pytz.UTC
        
        # 获取当前UTC时间
        now_utc = datetime.now(utc_tz)
        
        # 设置结束时间为当前UTC时间
        end_time = now_utc
        
        # 设置开始时间为30天前
        begin_time = end_time - timedelta(days=30)
        
        print(f"\n测试参数信息:")
        print(f"UTC当前时间: {now_utc}")
        print(f"开始时间(UTC): {begin_time}")
        print(f"结束时间(UTC): {end_time}")
        print(f"股票代码: AAPL")
        print(f"周期: 1m")
        
        # 获取数据
        data = self.client.get_historical_data("AAPL", begin_time, end_time, "1m")
        
        # 基本数据验证
        self.assertIsNotNone(data)
        self.assertIsInstance(data, pd.DataFrame)
        self.assertFalse(data.empty)
        
        # 打印数据信息用于调试
        print("\n获取到的30天数据信息:")
        print(f"数据条数: {len(data)}")
        print(f"时间范围: {data.index.min()} 到 {data.index.max()}")
        print(f"数据列: {data.columns.tolist()}")
        print("\n数据样例:")
        print(data.head())
        
        # 验证数据结构
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            self.assertIn(col, data.columns)
        self.assertEqual(data.index.name, 'datetime')
        
        # 验证数据类型
        self.assertEqual(data['open'].dtype, float)
        self.assertEqual(data['high'].dtype, float)
        self.assertEqual(data['low'].dtype, float)
        self.assertEqual(data['close'].dtype, float)
        self.assertTrue(data['volume'].dtype in (float, 'int64'))
        
        # 验证数据有效性
        self.assertTrue((data['high'] >= data['low']).all())
        self.assertTrue((data['high'] >= data['open']).all())
        self.assertTrue((data['high'] >= data['close']).all())
        self.assertTrue((data['low'] <= data['open']).all())
        self.assertTrue((data['low'] <= data['close']).all())
        self.assertTrue((data['volume'] >= 0).all())
        
        # 验证数据跨度
        data_begin = pd.to_datetime(data.index.min())
        data_end = pd.to_datetime(data.index.max())
        days_diff = (data_end - data_begin).days
        print(f"\n数据跨度: {days_diff}天")
        self.assertGreaterEqual(days_diff, 20)
        
        # 验证数据连续性
        time_diff = pd.to_datetime(data.index).to_series().diff()
        non_zero_diff = time_diff[time_diff > pd.Timedelta(0)]
        if not non_zero_diff.empty:
            min_diff = non_zero_diff.min()
            print(f"最小时间间隔: {min_diff}")
            self.assertGreaterEqual(min_diff.total_seconds() / 60, 1)
        
        # 验证每个交易日的数据
        dates = pd.to_datetime(data.index).date
        unique_dates = pd.Series(dates).unique()
        print(f"\n总交易日数: {len(unique_dates)}")
        
        # 计算每个交易日的数据点数量
        for date in unique_dates:
            day_data = data[pd.to_datetime(data.index).date == date]
            points_count = len(day_data)
            
            # 获取当天的第一个和最后一个数据点
            first_point = pd.to_datetime(day_data.index.min())
            last_point = pd.to_datetime(day_data.index.max())
            
            # 计算交易时间（分钟）
            trading_minutes = (last_point - first_point).total_seconds() / 60
            
            print(f"\n交易日 {date} 数据统计:")
            print(f"数据点数量: {points_count}")
            print(f"交易时间范围: {first_point} 到 {last_point}")
            print(f"交易时长: {trading_minutes:.1f} 分钟")
            
            # 验证数据点数量
            expected_points = 390  # 6.5小时 * 60分钟 = 390分钟
            min_points = int(expected_points * 0.9)  # 允许90%的完整度
            if points_count < min_points:
                print(f"警告: 交易日 {date} 数据点数量不足（期望至少{min_points}个点，实际{points_count}个点）")
        
if __name__ == '__main__':
    unittest.main() 