import os
import pandas as pd
import logging
from datetime import datetime, timedelta
import time

# 简化日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入老虎证券API
try:
    from tigeropen.tiger_open_config import TigerOpenClientConfig
    from tigeropen.common.consts import Language
    from tigeropen.quote.quote_client import QuoteClient
    from tigeropen.common.util.signature_utils import read_private_key
    from tigeropen.common.consts import BarPeriod
    logger.info("成功导入老虎证券API")
except ImportError as e:
    logger.warning(f"无法导入老虎证券API: {e}")

class DataFetcher:
    def __init__(self, config_path, private_key_path, cache_dir):
        """初始化数据获取器"""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # 初始化API客户端
        try:
            self.tiger_client_config = TigerOpenClientConfig(sandbox_debug=False, props_path=config_path)
            self.tiger_client_config.private_key = read_private_key(private_key_path)
            self.tiger_client_config.language = Language.zh_CN
            self.tiger_client_config.timeout = 60
            
            self.quote_client = QuoteClient(self.tiger_client_config)
            self.quote_client.grab_quote_permission()
            logger.info("老虎证券API客户端初始化完成")
        except Exception as e:
            logger.error(f"初始化API客户端失败: {e}")
            self.quote_client = None

    def check_cache_exists(self, symbol, period, begin_time, end_time):
        """检查缓存是否存在
        
        返回:
            (bool, str): 缓存是否存在，存在则返回缓存文件路径
        """
        begin_str = begin_time.strftime("%Y-%m-%d")
        end_str = end_time.strftime("%Y-%m-%d")
        
        # 尝试精确匹配的缓存文件
        exact_cache = f"{self.cache_dir}/{symbol}_{period}_{begin_str}_{end_str}.csv"
        if os.path.exists(exact_cache) and os.path.getsize(exact_cache) > 1000:
            logger.info(f"找到精确匹配的缓存文件: {exact_cache}")
            return True, exact_cache
            
        # 寻找可能包含所需数据范围的缓存文件
        all_cache_files = [f for f in os.listdir(self.cache_dir) 
                           if f.startswith(f"{symbol}_{period}_") and f.endswith(".csv")]
        
        for cache_file in all_cache_files:
            try:
                # 从文件名提取日期范围
                parts = cache_file.replace(f"{symbol}_{period}_", "").replace(".csv", "").split("_")
                if len(parts) == 2:
                    file_begin = datetime.strptime(parts[0], "%Y-%m-%d")
                    file_end = datetime.strptime(parts[1], "%Y-%m-%d")
                    
                    # 检查文件是否覆盖所需日期范围
                    if file_begin <= begin_time and file_end >= end_time:
                        full_path = os.path.join(self.cache_dir, cache_file)
                        if os.path.getsize(full_path) > 1000:
                            logger.info(f"找到覆盖日期范围的缓存文件: {cache_file}")
                            return True, full_path
            except Exception as e:
                logger.debug(f"解析缓存文件名失败: {cache_file}, 错误: {e}")
        
        # 检查backtrader准备好的数据文件
        bt_file = f"{self.cache_dir}/{symbol}_{period}_bt.csv"
        if os.path.exists(bt_file) and os.path.getsize(bt_file) > 1000:
            logger.info(f"找到backtrader数据文件: {bt_file}")
            return True, bt_file
            
        logger.info(f"未找到 {symbol} 的缓存数据")
        return False, None

    def get_bar_data(self, symbol, period='1m', begin_time=None, end_time=None, use_cache=True):
        """获取K线数据，优先使用缓存
        
        参数:
            symbol: 股票代码
            period: 周期，如'1m', '5m'等
            begin_time: 开始时间
            end_time: 结束时间
            use_cache: 是否使用缓存，如果为True且缓存存在，则直接使用缓存不会调用API
        """
        # 默认获取最近一个月数据
        if end_time is None:
            end_time = datetime.now()
        if begin_time is None:
            begin_time = end_time - timedelta(days=30)

        # 首先检查缓存是否存在
        if use_cache:
            cache_exists, cache_file = self.check_cache_exists(symbol, period, begin_time, end_time)
            if cache_exists:
                logger.info(f"使用缓存数据，无需API调用: {cache_file}")
                try:
                    return pd.read_csv(cache_file, index_col=0, parse_dates=True)
                except Exception as e:
                    logger.warning(f"读取缓存文件失败: {e}, 将从API获取数据")
        
        # 如果没有缓存或不使用缓存，则从API获取数据
        logger.info(f"从API获取数据: {symbol}")
        
        # 检查API客户端是否可用
        if self.quote_client is None:
            logger.error("API客户端未初始化，无法获取数据")
            return pd.DataFrame()
        
        # 转换周期字符串为Tiger API枚举值
        tiger_period = self._convert_period(period)
        
        # 分段获取数据
        is_minute_level = isinstance(tiger_period, BarPeriod) and tiger_period in [
            BarPeriod.ONE_MINUTE, BarPeriod.FIVE_MINUTES, 
            BarPeriod.FIFTEEN_MINUTES, BarPeriod.HALF_HOUR,
            BarPeriod.ONE_HOUR
        ]
        
        max_days_per_request = 5 if is_minute_level else 30
        total_days = (end_time - begin_time).days + 1
        segment_count = (total_days + max_days_per_request - 1) // max_days_per_request
        
        # 获取所有数据段
        all_data_frames = []
        current_begin = begin_time
        
        for _ in range(segment_count):
            days_in_segment = min(max_days_per_request, total_days)
            current_end = current_begin + timedelta(days=days_in_segment)
            if current_end > end_time:
                current_end = end_time
            
            begin_timestamp = int(current_begin.timestamp() * 1000)
            end_timestamp = int(current_end.timestamp() * 1000)
            
            # 尝试不同格式的股票代码
            stock_symbols = [symbol, f"US.{symbol}"] if not symbol.startswith('US.') else [symbol]
            
            for stock_code in stock_symbols:
                try:
                    limit_value = 5000 if is_minute_level else 1000
                    logger.info(f"调用Tiger API获取数据: {stock_code} [{current_begin} 至 {current_end}]")
                    bars = self.quote_client.get_bars(
                        symbols=[stock_code],
                        period=tiger_period,
                        begin_time=begin_timestamp,
                        end_time=end_timestamp,
                        limit=limit_value
                    )
                    
                    if isinstance(bars, pd.DataFrame) and not bars.empty:
                        df = bars.copy()
                        df['datetime'] = pd.to_datetime(df['time'], unit='ms')
                        df.set_index('datetime', inplace=True)
                        df.sort_index(inplace=True)
                        all_data_frames.append(df)
                        break
                except Exception as e:
                    logger.warning(f"API调用失败，股票: {stock_code}, 错误: {e}")
                    continue
            
            current_begin = current_end
            total_days -= days_in_segment
            time.sleep(1)  # 避免API限流
        
        # 合并数据并保存缓存
        if not all_data_frames:
            logger.warning(f"无法获取数据: {symbol}")
            return pd.DataFrame()
        
        combined_df = pd.concat(all_data_frames)
        combined_df = combined_df[~combined_df.index.duplicated(keep='first')]
        combined_df.sort_index(inplace=True)
        
        # 保存到缓存
        begin_str = begin_time.strftime("%Y-%m-%d")
        end_str = end_time.strftime("%Y-%m-%d")
        cache_filename = f"{self.cache_dir}/{symbol}_{period}_{begin_str}_{end_str}.csv"
        
        try:
            combined_df.to_csv(cache_filename)
            logger.info(f"数据已保存到缓存: {cache_filename}")
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")
        
        return combined_df
    
    def _convert_period(self, period):
        """转换周期字符串为Tiger API枚举值"""
        if isinstance(period, str):
            period_map = {
                '1m': BarPeriod.ONE_MINUTE,
                '5m': BarPeriod.FIVE_MINUTES,
                '15m': BarPeriod.FIFTEEN_MINUTES,
                '30m': BarPeriod.HALF_HOUR,
                '60m': BarPeriod.ONE_HOUR,
                '1h': BarPeriod.ONE_HOUR,
                'day': BarPeriod.DAY,
                'week': BarPeriod.WEEK,
                'month': BarPeriod.MONTH,
                'year': BarPeriod.YEAR
            }
            return period_map.get(period, BarPeriod.ONE_MINUTE)
        return period

    def prepare_backtrader_data(self, symbol, df=None, period='1m', begin_time=None, end_time=None, use_cache=True):
        """准备用于backtrader的数据"""
        if df is None:
            df = self.get_bar_data(symbol, period, begin_time, end_time, use_cache=use_cache)
        
        if df.empty:
            logger.warning(f"无数据可用于准备Backtrader文件: {symbol}")
            return None
            
        bt_filename = f"{self.cache_dir}/{symbol}_{period}_bt.csv"
        df.to_csv(bt_filename, date_format='%Y-%m-%d %H:%M:%S', 
                  columns=['open', 'high', 'low', 'close', 'volume'])
        
        logger.info(f"已准备Backtrader数据文件: {bt_filename}")
        return bt_filename
