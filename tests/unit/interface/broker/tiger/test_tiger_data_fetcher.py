"""
测试老虎证券数据获取功能
"""
import pytest
import os
import pandas as pd
import time
from datetime import datetime, timedelta
from src.interface.broker.tiger.tiger_data_fetcher import DataFetcher
from tigeropen.common.consts import BarPeriod
import pytz

class TestTigerDataFetcher:
    @pytest.fixture(scope="class")
    def data_fetcher(self, tmp_path_factory):
        """创建测试用的 DataFetcher 实例，使用类级别的fixture"""
        # 创建临时缓存目录
        cache_dir = str(tmp_path_factory.mktemp("cache"))
        os.makedirs(cache_dir, exist_ok=True)
        
        # 获取项目根目录的绝对路径
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
        config_path = os.path.join(base_dir, "configs", "tiger", "tiger_openapi_config.properties")
        private_key_path = os.path.join(base_dir, "configs", "tiger", "private_key.pem")
        
        # 验证文件是否存在
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        if not os.path.exists(private_key_path):
            raise FileNotFoundError(f"私钥文件不存在: {private_key_path}")
        
        # 创建DataFetcher实例
        fetcher = DataFetcher(
            config_path=config_path,
            private_key_path=private_key_path,
            cache_dir=cache_dir
        )
        
        # 基本验证
        assert fetcher.cache_dir == cache_dir, "缓存目录设置错误"
        assert os.path.exists(cache_dir), "缓存目录未创建"
        assert os.path.isdir(cache_dir), "缓存目录不是一个有效的目录"
        assert fetcher.quote_client is not None, "API客户端初始化失败"
        
        # 等待API限流重置
        time.sleep(10)
        
        return fetcher
    
    def test_data_fetcher_initialization(self, tmp_path_factory):
        """测试DataFetcher实例的构建"""
        # 创建临时缓存目录
        cache_dir = str(tmp_path_factory.mktemp("test_init"))
        
        # 获取配置文件路径
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
        config_path = os.path.join(base_dir, "configs", "tiger", "tiger_openapi_config.properties")
        private_key_path = os.path.join(base_dir, "configs", "tiger", "private_key.pem")
        
        # 测试正常构建
        fetcher = DataFetcher(
            config_path=config_path,
            private_key_path=private_key_path,
            cache_dir=cache_dir
        )
        
        # 验证基本属性
        assert fetcher.cache_dir == cache_dir, "缓存目录设置错误"
        assert os.path.exists(cache_dir), "缓存目录未创建"
        assert os.path.isdir(cache_dir), "缓存目录不是一个有效的目录"
        assert fetcher.quote_client is not None, "API客户端初始化失败"
        
        # 测试缓存目录创建
        test_cache_dir = os.path.join(cache_dir, "test_subdir")
        fetcher2 = DataFetcher(
            config_path=config_path,
            private_key_path=private_key_path,
            cache_dir=test_cache_dir
        )
        assert os.path.exists(test_cache_dir), "子缓存目录未创建"
        assert os.path.isdir(test_cache_dir), "子缓存目录不是一个有效的目录"
    
    def test_basic_bar_data_fetch(self, data_fetcher):
        """测试基本的K线数据获取功能"""
        # 准备测试参数
        symbol = "US.AAPL"  # 使用正确的股票代码格式
        period = "1m"
        
        # 使用美股最近的交易日
        end_time = datetime.now()
        # 获取最近1小时的数据
        begin_time = end_time - timedelta(hours=1)
        
        # 直接从API获取数据（不使用缓存）
        df = data_fetcher.get_bar_data(
            symbol=symbol,
            period=period,
            begin_time=begin_time,
            end_time=end_time,
            use_cache=False
        )
        
        # 基本数据验证
        assert isinstance(df, pd.DataFrame), "返回数据类型应该是DataFrame"
        
        # 打印数据信息用于调试
        print("\n获取到的数据信息:")
        print(f"数据条数: {len(df)}")
        if not df.empty:
            print(f"时间范围: {df.index.min()} 到 {df.index.max()}")
            print(f"数据列: {df.columns.tolist()}")
            print("\n数据样例:")
            print(df.head())
        else:
            print("未获取到数据，可能是非交易时间")
            return
        
        # 如果获取到数据，进行更详细的验证
        if not df.empty:
            # 验证数据结构
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            assert all(col in df.columns for col in required_columns), "数据应该包含所有必需的列"
            assert df.index.name == 'datetime', "索引名称应该是datetime"
            
            # 验证数据类型
            assert df['open'].dtype == float, "open列应该是float类型"
            assert df['high'].dtype == float, "high列应该是float类型"
            assert df['low'].dtype == float, "low列应该是float类型"
            assert df['close'].dtype == float, "close列应该是float类型"
            assert df['volume'].dtype == float, "volume列应该是float类型"
            
            # 验证数据有效性
            assert (df['high'] >= df['low']).all(), "high应该大于等于low"
            assert (df['high'] >= df['open']).all(), "high应该大于等于open"
            assert (df['high'] >= df['close']).all(), "high应该大于等于close"
            assert (df['low'] <= df['open']).all(), "low应该小于等于open"
            assert (df['low'] <= df['close']).all(), "low应该小于等于close"
            assert (df['volume'] >= 0).all(), "volume应该大于等于0"
    
    def test_30_days_bar_data_fetch(self, data_fetcher):
        """测试获取30天的1分钟K线数据"""
        # 准备测试参数
        symbol = "AAPL"  # 使用基本股票代码
        period = "1m"
        
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
        print(f"股票代码: {symbol}")
        print(f"周期: {period}")
        
        # 直接从API获取数据（不使用缓存）
        df = data_fetcher.get_bar_data(
            symbol=symbol,
            period=period,
            begin_time=begin_time,
            end_time=end_time,
            use_cache=False
        )
        
        # 基本数据验证
        assert isinstance(df, pd.DataFrame), "返回数据类型应该是DataFrame"
        assert not df.empty, "应该获取到数据"
        
        # 打印数据信息用于调试
        print("\n获取到的30天数据信息:")
        print(f"数据条数: {len(df)}")
        print(f"时间范围: {df.index.min()} 到 {df.index.max()}")
        print(f"数据列: {df.columns.tolist()}")
        print("\n数据样例:")
        print(df.head())
        
        # 验证数据结构
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        assert all(col in df.columns for col in required_columns), "数据应该包含所有必需的列"
        assert df.index.name == 'datetime', "索引名称应该是datetime"
        
        # 验证数据类型
        assert df['open'].dtype == float, "open列应该是float类型"
        assert df['high'].dtype == float, "high列应该是float类型"
        assert df['low'].dtype == float, "low列应该是float类型"
        assert df['close'].dtype == float, "close列应该是float类型"
        assert df['volume'].dtype in (float, 'int64'), "volume列应该是数值类型"
        
        # 验证数据有效性
        assert (df['high'] >= df['low']).all(), "high应该大于等于low"
        assert (df['high'] >= df['open']).all(), "high应该大于等于open"
        assert (df['high'] >= df['close']).all(), "high应该大于等于close"
        assert (df['low'] <= df['open']).all(), "low应该小于等于open"
        assert (df['low'] <= df['close']).all(), "low应该小于等于close"
        assert (df['volume'] >= 0).all(), "volume应该大于等于0"
        
        # 验证数据跨度
        data_begin = df.index.min()
        data_end = df.index.max()
        days_diff = (data_end - data_begin).days
        print(f"\n数据跨度: {days_diff}天")
        assert days_diff >= 20, "数据应该至少跨越20个交易日"
        
        # 验证数据连续性
        time_diff = df.index.to_series().diff()
        non_zero_diff = time_diff[time_diff > pd.Timedelta(0)]
        if not non_zero_diff.empty:
            min_diff = non_zero_diff.min()
            print(f"最小时间间隔: {min_diff}")
            assert min_diff >= pd.Timedelta(minutes=1), "数据间隔应该至少为1分钟"
        
        # 验证每个交易日的数据
        dates = pd.Series(df.index.to_pydatetime()).dt.date.unique()
        print(f"\n总交易日数: {len(dates)}")
        
        # 计算每个交易日的数据点数量
        date_points = {}
        for date in dates:
            day_data = df[pd.to_datetime(df.index.date) == pd.to_datetime(date)]
            points_count = len(day_data)
            date_points[date] = points_count
            
            # 获取当天的第一个和最后一个数据点
            first_point = day_data.index.min()
            last_point = day_data.index.max()
            
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
        
        # 计算数据完整性统计
        total_points = sum(date_points.values())
        avg_points = total_points / len(dates)
        print(f"\n数据完整性统计:")
        print(f"平均每日数据点数: {avg_points:.2f}")
        print(f"最大数据点数: {max(date_points.values())}")
        print(f"最小数据点数: {min(date_points.values())}")
        print(f"期望数据点数: 390 (6.5小时 * 60分钟)")
        
        # 验证数据完整性
        expected_days = 20  # 至少20个交易日
        assert len(dates) >= expected_days, f"交易日数量不足（期望至少{expected_days}天，实际{len(dates)}天）"
        
        # 验证大部分交易日的数据点数量是否合理
        incomplete_days = sum(1 for points in date_points.values() if points < 351)  # 允许90%的完整度
        max_allowed_incomplete = len(dates) * 0.1  # 允许10%的交易日数据不完整
        assert incomplete_days <= max_allowed_incomplete, \
            f"不完整交易日数量过多（{incomplete_days}天超过阈值{max_allowed_incomplete:.1f}天）" 