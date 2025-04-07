"""
老虎证券数据存储类
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import os
import logging
from src.interface.store.base_store import DataStoreBase
import glob
import numpy as np
from src.interface.broker.tiger.tiger_client import TigerClient
from src.infrastructure.constants.const import TimeInterval, MAX_1MIN_DATA_DAYS


class TigerStore(DataStoreBase):
    """老虎证券数据存储类"""

    def __init__(self, client: Optional[TigerClient] = None):
        super().__init__()
        self.client = client
        self.logger = logging.getLogger(__name__)
        self.cache_dir = os.path.join("data", "cache", "tiger")
        os.makedirs(self.cache_dir, exist_ok=True)

    def start(self) -> bool:
        """启动数据存储"""
        return True

    def stop(self) -> bool:
        """停止数据存储"""
        return True

    def get_historical_data(self, symbol: str, start_time: datetime, end_time: datetime, period: str = TimeInterval.ONE_MINUTE.value) -> pd.DataFrame:
        """获取历史数据
        
        Args:
            symbol: 股票代码
            start_time: 开始时间
            end_time: 结束时间
            period: 数据周期，默认为1分钟
            
        Returns:
            DataFrame: 历史数据
        """
        self.logger.info(f"获取历史数据: {symbol}, {start_time} - {end_time}, {period}")
        
        if self.client is None:
            raise ValueError("客户端未初始化")
            
        # 检查1分钟K线的时间限制
        if period == TimeInterval.ONE_MINUTE.value:
            date_diff = (end_time - start_time).days
            if date_diff > MAX_1MIN_DATA_DAYS:
                self.logger.warning(f"1分钟K线数据只能获取最近{MAX_1MIN_DATA_DAYS}天的数据，当前请求时间范围：{date_diff}天")
                self.logger.warning(f"将起始日期从 {start_time} 调整为 {end_time - timedelta(days=MAX_1MIN_DATA_DAYS)}")
                start_time = end_time - timedelta(days=MAX_1MIN_DATA_DAYS)
            
        # 确保时间值没有时区信息，以统一处理
        start_time_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
        end_time_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time
        
        # 构建缓存key
        cache_key = f"{symbol}, {start_time} - {end_time}, {period}"
        self.logger.info(f"查找缓存文件: {cache_key}")
        
        # 构建缓存目录
        cache_dir = os.path.join(self.cache_dir, symbol)
        os.makedirs(cache_dir, exist_ok=True)
        
        # 查找缓存文件
        cache_files = glob.glob(os.path.join(cache_dir, f"*_{period}.csv"))
        
        if not cache_files:
            self.logger.info("未找到缓存文件")
            self.logger.info("尝试智能合并缓存和API数据")
            self.logger.info("没有任何缓存文件，直接从API获取所有数据")
            # 没有缓存，从API获取
            df = self._get_from_api(symbol, start_time, end_time, period)
            self.logger.info(f"从API获取到数据: {symbol}, 数据点数: {len(df)}")
            
            # 保存到缓存
            self._save_to_cache(df, symbol, period)
            
            # 格式化返回数据
            return self._format_output_data(df)
        
        self.logger.info(f"找到缓存文件: {len(cache_files)}")
        
        # 记录存在的缓存文件
        for cache_file in cache_files:
            self.logger.info(f"发现缓存文件: {cache_file}")
        
        # 先尝试直接从单个缓存文件读取
        matching_cache_data = []
        available_date_ranges = []
        
        # 解析所有缓存文件的日期范围
        for cache_file in cache_files:
            try:
                # 尝试读取每个文件
                self.logger.info(f"尝试从单个文件读取: {cache_file}")
                df_cache = pd.read_csv(cache_file, parse_dates=['time'])
                self.logger.info(f"成功读取文件数据，点数: {len(df_cache)}")
                
                # 记录缓存的时间范围
                df_min_time = df_cache['time'].min()
                df_max_time = df_cache['time'].max()
                self.logger.info(f"数据时间范围: {df_min_time} - {df_max_time}")
                self.logger.info(f"请求时间范围: {start_time} - {end_time}")
                
                # 保存缓存文件的日期范围
                matching_cache_data.append(df_cache)
                available_date_ranges.append((cache_file, df_min_time, df_max_time))
            except Exception as e:
                self.logger.warning(f"读取缓存文件失败: {cache_file}, 错误: {str(e)}")
                
        # 尝试通过合并多个缓存文件来获取完整数据
        self.logger.info("尝试合并多个缓存文件")
        
        # 确定需要的日期
        start_date = pd.Timestamp(start_time_naive).date()
        end_date = pd.Timestamp(end_time_naive).date()
        requested_dates = pd.date_range(start=start_date, end=end_date).date
        
        # 确定缓存覆盖的日期
        relevant_cache_files = []
        for file_path, _, _ in available_date_ranges:
            # 从文件名提取日期
            file_name = os.path.basename(file_path)
            date_str = file_name.split('_')[0]
            if len(date_str) == 8:  # YYYYMMDD 格式
                try:
                    file_date = datetime.strptime(date_str, '%Y%m%d').date()
                    if start_date <= file_date <= end_date:
                        relevant_cache_files.append(file_path)
                except ValueError:
                    pass
        
        self.logger.info(f"找到相关缓存文件: {len(relevant_cache_files)}")
        
        # 合并所有相关的缓存文件
        merged_cache_df = None
        if relevant_cache_files:
            dfs = []
            for cache_file in relevant_cache_files:
                try:
                    self.logger.info(f"读取缓存文件: {cache_file}")
                    df = pd.read_csv(cache_file, parse_dates=['time'])
                    self.logger.info(f"文件包含 {len(df)} 个数据点")
                    dfs.append(df)
                except Exception as e:
                    self.logger.warning(f"读取缓存文件失败: {cache_file}, 错误: {str(e)}")
            
            if dfs:
                merged_cache_df = pd.concat(dfs, ignore_index=True)
                merged_cache_df = merged_cache_df.sort_values('time')
                self.logger.info(f"合并 {len(dfs)} 个缓存文件的数据")
                self.logger.info(f"合并后数据点数: {len(merged_cache_df)}")
                
                # 记录合并后的时间范围
                cache_min_time = merged_cache_df['time'].min()
                cache_max_time = merged_cache_df['time'].max()
                self.logger.info(f"合并后数据时间范围: {cache_min_time} - {cache_max_time}")
                
                # 确保时间戳是naive的，以便正确比较
                start_ts = pd.Timestamp(start_time_naive)
                end_ts = pd.Timestamp(end_time_naive)
                
                # 检查缓存是否完全覆盖请求时间范围
                if cache_min_time <= start_ts and cache_max_time >= end_ts:
                    # 缓存完全覆盖请求时间范围
                    self.logger.info("缓存完全覆盖请求时间范围")
                    # 过滤出请求的时间范围
                    result_df = merged_cache_df[(merged_cache_df['time'] >= start_ts) & 
                                              (merged_cache_df['time'] <= end_ts)]
                    self.logger.info(f"成功从缓存获取数据: {len(result_df)} 个数据点")
                    self.logger.info(f"成功从缓存中获取数据: {symbol}, 数据点数: {len(result_df)}")
                    return self._format_output_data(result_df)
                else:
                    # 缓存不完全覆盖
                    self.logger.info("缓存数据不完全覆盖请求时间范围")
                    self.logger.info(f"缓存: {cache_min_time} - {cache_max_time}")
                    self.logger.info(f"请求: {start_time} - {end_time}")
                    
                    # 尝试智能合并缓存和API数据
                    self.logger.info("尝试智能合并缓存和API数据")
                    
                    # 计算缓存中存在的日期和缺失的日期
                    cache_dates = set(merged_cache_df['time'].dt.date.unique())
                    requested_dates_set = set(requested_dates)
                    missing_dates = requested_dates_set - cache_dates
                    
                    if not missing_dates:
                        # 如果没有缺失的日期（可能是缓存覆盖了所有请求的日期，但时间范围不完全匹配）
                        self.logger.info("缓存包含所有请求日期的数据，但时间范围不完全匹配")
                        # 过滤出请求的时间范围内的数据
                        result_df = merged_cache_df[(merged_cache_df['time'] >= start_ts) & 
                                                  (merged_cache_df['time'] <= end_ts)]
                        self.logger.info(f"从缓存筛选出符合时间范围的数据: {len(result_df)} 个数据点")
                        return self._format_output_data(result_df)
                    
                    # 有缺失的日期，需要分段获取API数据
                    self.logger.info(f"需要从API获取 {len(missing_dates)} 个缺失日期的数据")
                    
                    # 策略1: 如果缺失日期很多，直接重新获取所有数据
                    if len(missing_dates) > len(requested_dates_set) / 2:
                        self.logger.info(f"缺失日期过多，直接从API获取完整数据: {symbol}, {start_time} - {end_time}")
                        df = self._get_from_api(symbol, start_time, end_time, period)
                        self.logger.info(f"从API获取到数据: {symbol}, 数据点数: {len(df)}")
                        self._save_to_cache(df, symbol, period)
                        return self._format_output_data(df)
                    
                    # 策略2: 仅获取缺失日期的数据，然后与缓存合并
                    missing_segments = self._get_date_segments(sorted(missing_dates))
                    self.logger.info(f"缺失日期分段: {missing_segments}")
                    
                    # 获取各个缺失段的数据
                    api_dfs = []
                    for seg_start, seg_end in missing_segments:
                        # 转换为datetime对象
                        seg_start_dt = datetime.combine(seg_start, datetime.min.time())
                        seg_end_dt = datetime.combine(seg_end, datetime.max.time())
                        
                        # 调整为请求的开始和结束时间
                        if seg_start == start_date:
                            seg_start_dt = start_time
                        if seg_end == end_date:
                            seg_end_dt = end_time
                            
                        self.logger.info(f"获取缺失段数据: {symbol}, {seg_start_dt} - {seg_end_dt}")
                        seg_df = self._get_from_api(symbol, seg_start_dt, seg_end_dt, period)
                        self.logger.info(f"获取到缺失段数据: {len(seg_df)} 个数据点")
                        api_dfs.append(seg_df)
                        # 保存到缓存
                        self._save_to_cache(seg_df, symbol, period)
                    
                    # 合并API数据和缓存数据
                    if api_dfs:
                        api_data = pd.concat(api_dfs, ignore_index=True)
                        self.logger.info(f"合并所有API获取的数据: {len(api_data)} 个数据点")
                        
                        # 合并缓存和API数据
                        final_df = pd.concat([merged_cache_df, api_data], ignore_index=True)
                        # 去重并排序
                        final_df = final_df.drop_duplicates(subset=['time']).sort_values('time')
                        self.logger.info(f"与缓存合并后总数据点: {len(final_df)} 个")
                        
                        # 过滤出请求的时间范围
                        result_df = final_df[(final_df['time'] >= start_ts) & 
                                           (final_df['time'] <= end_ts)]
                        self.logger.info(f"最终返回符合时间范围的数据: {len(result_df)} 个数据点")
                        return self._format_output_data(result_df)
        
        # 如果到这里，说明缓存无法满足请求，从API获取完整数据
        self.logger.info(f"缓存中无法获取完整数据，从API获取: {symbol}, {start_time} - {end_time}")
        df = self._get_from_api(symbol, start_time, end_time, period)
        self.logger.info(f"从API获取到数据: {symbol}, 数据点数: {len(df)}")
        
        # 保存到缓存
        self._save_to_cache(df, symbol, period)
        
        # 格式化返回数据
        return self._format_output_data(df)
        
    def _format_output_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """格式化输出数据，确保符合预期的格式
        
        Args:
            df: 输入数据
            
        Returns:
            DataFrame: 格式化后的数据
        """
        if df is None or df.empty:
            return pd.DataFrame()
            
        # 复制一份避免修改原始数据
        result_df = df.copy()
        
        # 确保包含所需的所有列
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        
        # 检查是否有额外的列需要删除
        columns_to_drop = []
        for col in result_df.columns:
            if col not in required_columns and col != 'datetime':
                columns_to_drop.append(col)
                
        # 删除额外的列
        if columns_to_drop:
            self.logger.info(f"从输出中删除额外的列: {columns_to_drop}")
            result_df = result_df.drop(columns=columns_to_drop)
        
        # 确保 datetime 是索引
        if 'time' in result_df.columns:
            self.logger.info(f"将 'time' 列设置为索引")
            result_df.set_index('time', inplace=True)
            result_df.index.name = 'datetime'
        
        # 确保索引名称是 datetime
        if result_df.index.name is None or result_df.index.name != 'datetime':
            self.logger.info(f"设置索引名称为 'datetime'")
            result_df.index.name = 'datetime'
            
        # 确保索引是升序排列的
        result_df = result_df.sort_index()
            
        return result_df

    def _get_date_segments(self, dates):
        """将日期列表转换为连续日期段"""
        if not dates:
            return []
        
        segments = []
        start_date = dates[0]
        prev_date = dates[0]
        
        for i in range(1, len(dates)):
            current_date = dates[i]
            # 如果当前日期与前一日期不连续
            if (current_date - prev_date).days > 1:
                segments.append((start_date, prev_date))
                start_date = current_date
            prev_date = current_date
            
        # 添加最后一个段
        segments.append((start_date, prev_date))
            
        return segments

    def get_realtime_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """获取实时行情"""
        if self.client is None:
            raise ValueError("客户端未初始化")

        return self.client.get_realtime_quotes(symbols)

    def _get_cached_data(self, symbol: str, start_date: datetime,
                         end_date: datetime, interval: str) -> Optional[pd.DataFrame]:
        """智能获取缓存数据，支持部分缓存"""
        try:
            # 确保时区一致性
            start_date_naive = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
            end_date_naive = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
            
            self.logger.info(f"查找缓存文件: {symbol}, {start_date_naive} - {end_date_naive}, {interval}")
            
            # 获取所有可用的缓存文件
            cache_files = self._find_cache_files(symbol, interval)
            if not cache_files:
                self.logger.info(f"未找到缓存文件")
                return None
            
            self.logger.info(f"找到缓存文件: {len(cache_files)}")
            for cache_file in cache_files:
                self.logger.info(f"发现缓存文件: {cache_file}")
            
            # 首先尝试只从一个缓存文件获取数据
            # 通常按天存储，如果时间范围小，可能只需要一个文件
            for cache_file in cache_files:
                try:
                    # 从文件名中提取日期信息
                    filename = os.path.basename(cache_file)
                    if '_' not in filename:
                        continue
                    
                    date_str = filename.split('_')[0]
                    if not date_str.isdigit() or len(date_str) != 8:
                        continue
                    
                    file_date = datetime.strptime(date_str, "%Y%m%d").date()
                    
                    # 检查该文件是否有可能包含所需数据
                    if (file_date >= start_date_naive.date() and 
                        file_date <= end_date_naive.date()):
                    
                        # 读取单个文件数据
                        self.logger.info(f"尝试从单个文件读取: {cache_file}")
                        data = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
                        
                        # 检查数据是否完全覆盖请求的时间范围
                        if not data.empty:
                            self.logger.info(f"成功读取文件数据，点数: {len(data)}")
                            self.logger.info(f"数据时间范围: {data.index.min()} - {data.index.max()}")
                            self.logger.info(f"请求时间范围: {start_date_naive} - {end_date_naive}")
                            
                            # 如果是单天数据，可能不会覆盖整个请求范围，所以我们应该合并多个文件
                            '''
                            if (data.index.min() <= start_date_naive and
                                    data.index.max() >= end_date_naive):
                                # 返回请求的时间范围内的数据
                                return data[start_date_naive:end_date_naive]
                            '''
                except Exception as e:
                    self.logger.debug(f"从单个缓存文件读取失败: {str(e)}")
                    continue

            # 合并所有覆盖时间范围的缓存文件
            self.logger.info(f"尝试合并多个缓存文件")
            cached_data = []
            
            # 找出所有可能包含所需时间范围数据的文件
            relevant_files = []
            for cache_file in cache_files:
                try:
                    filename = os.path.basename(cache_file)
                    if '_' not in filename:
                        continue
                    
                    date_str = filename.split('_')[0]
                    if not date_str.isdigit() or len(date_str) != 8:
                        continue
                    
                    file_date = datetime.strptime(date_str, "%Y%m%d").date()
                    
                    # 如果文件日期在请求范围内，或者紧邻请求范围，则包含
                    # 这是为了处理跨天请求的情况
                    date_diff_start = abs((file_date - start_date_naive.date()).days)
                    date_diff_end = abs((file_date - end_date_naive.date()).days)
                    
                    if (file_date >= start_date_naive.date() and file_date <= end_date_naive.date()) or \
                       date_diff_start <= 1 or date_diff_end <= 1:
                        relevant_files.append(cache_file)
                except Exception as e:
                    self.logger.warning(f"处理缓存文件 {cache_file} 失败: {str(e)}")
                
            self.logger.info(f"找到相关缓存文件: {len(relevant_files)}")
            
            # 读取并合并数据
            for cache_file in relevant_files:
                try:
                    self.logger.info(f"读取缓存文件: {cache_file}")
                    data = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
                    if not data.empty:
                        self.logger.info(f"文件包含 {len(data)} 个数据点")
                        cached_data.append(data)
                except Exception as e:
                    self.logger.warning(f"读取缓存文件 {cache_file} 失败: {str(e)}")
                    continue

            if not cached_data:
                self.logger.info(f"没有读取到任何缓存数据")
                return None

            # 合并所有缓存数据
            self.logger.info(f"合并 {len(cached_data)} 个缓存文件的数据")
            all_data = pd.concat(cached_data)
            all_data = all_data[~all_data.index.duplicated(keep='first')]
            all_data.sort_index(inplace=True)
            self.logger.info(f"合并后数据点数: {len(all_data)}")
            self.logger.info(f"合并后数据时间范围: {all_data.index.min()} - {all_data.index.max()}")
            
            # 检查是否完全覆盖请求的时间范围，允许一定的误差
            # 由于交易日的关系，可能不是每一天都有数据
            if all_data.empty:
                self.logger.info(f"合并后数据为空")
                return None
            
            if (all_data.index.min().date() <= start_date_naive.date() and
                    all_data.index.max().date() >= end_date_naive.date()):
                # 筛选请求的时间范围内的数据
                # 使用日期比较而不是精确的时间戳，因为交易开始和结束时间可能有细微差别
                result = all_data[(all_data.index.date >= start_date_naive.date()) & 
                                 (all_data.index.date <= end_date_naive.date())]
                
                if not result.empty:
                    self.logger.info(f"成功从缓存获取数据: {len(result)} 个数据点")
                    return result
                else:
                    self.logger.info(f"筛选后数据为空")
                    return None
            else:
                self.logger.info(f"缓存数据不完全覆盖请求时间范围")
                self.logger.info(f"缓存: {all_data.index.min()} - {all_data.index.max()}")
                self.logger.info(f"请求: {start_date_naive} - {end_date_naive}")
                return None

        except Exception as e:
            self.logger.error(f"获取缓存数据失败: {str(e)}", exc_info=True)
            return None

    def _save_to_daily_cache(self, data: pd.DataFrame, symbol: str, interval: str):
        """按天保存数据到缓存"""
        try:
            self.logger.info(f"开始保存缓存数据: {symbol}, 数据点数: {len(data)}")
            # 按天分组
            grouped_data = data.groupby(data.index.date)
            group_count = len(grouped_data)
            self.logger.info(f"数据按天分组，共 {group_count} 个分组")
            
            for date, day_data in grouped_data:
                cache_file = self._get_daily_cache_path(symbol, date, interval)
                self.logger.info(f"处理缓存文件: {cache_file}, 数据点数: {len(day_data)}")

                # 如果文件已存在，合并数据
                if os.path.exists(cache_file):
                    try:
                        self.logger.info(f"缓存文件已存在，正在合并数据: {cache_file}")
                        existing_data = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
                        day_data = pd.concat([existing_data, day_data])
                        day_data = day_data[~day_data.index.duplicated(keep='first')]
                        day_data.sort_index(inplace=True)
                        self.logger.info(f"合并后数据点数: {len(day_data)}")
                    except Exception as e:
                        self.logger.warning(f"合并缓存数据失败: {str(e)}")

                # 保存到缓存文件
                try:
                    # 确保目录存在
                    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                    day_data.to_csv(cache_file)
                    self.logger.info(f"成功保存数据到缓存: {cache_file}")
                    # 验证文件是否实际创建
                    if os.path.exists(cache_file):
                        file_size = os.path.getsize(cache_file)
                        self.logger.info(f"缓存文件已创建: {cache_file}, 大小: {file_size} 字节")
                    else:
                        self.logger.warning(f"缓存文件未成功创建: {cache_file}")
                except Exception as e:
                    self.logger.error(f"保存缓存失败: {str(e)}", exc_info=True)

        except Exception as e:
            self.logger.error(f"保存数据到缓存失败: {str(e)}", exc_info=True)

    def _get_daily_cache_path(self, symbol: str, date: datetime.date, interval: str) -> str:
        """获取每日缓存文件路径"""
        date_str = date.strftime("%Y%m%d")
        symbol_dir = os.path.join(self.cache_dir, symbol)
        os.makedirs(symbol_dir, exist_ok=True)
        return os.path.join(symbol_dir, f"{date_str}_{interval}.csv")

    def _find_cache_files(self, symbol: str, interval: str) -> List[str]:
        """查找符合条件的缓存文件"""
        symbol_dir = os.path.join(self.cache_dir, symbol)
        if not os.path.exists(symbol_dir):
            return []

        cache_files = []
        for file in os.listdir(symbol_dir):
            if file.endswith(f"_{interval}.csv"):
                cache_files.append(os.path.join(symbol_dir, file))

        return sorted(cache_files)  # 按文件名排序

    def get_data(self, **kwargs):
        """获取数据"""
        symbol = kwargs.get('symbol')
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        interval = kwargs.get('interval', '1m')

        if not all([symbol, start_date, end_date]):
            raise ValueError("get_data 需要 'symbol', 'start_date', 'end_date' 参数")

        return self.get_historical_data(symbol=symbol,
                                        start_time=start_date,
                                        end_time=end_date,
                                        period=interval)

    def _handle_response(self):
        """处理响应"""
        # 实现响应处理逻辑
        pass

    def _get_from_api(self, symbol: str, start_time: datetime, end_time: datetime, period: str) -> pd.DataFrame:
        """从API获取数据

        Args:
            symbol: 股票代码
            start_time: 开始时间
            end_time: 结束时间
            period: 周期

        Returns:
            DataFrame: 历史数据
        """
        if self.client is None:
            raise ValueError("客户端未初始化")

        try:
            data = self.client.get_historical_data(symbol=symbol, start_date=start_time, end_date=end_time,
                                                 interval=period)
            
            # 统一数据格式：确保数据有一个time列
            if data.index.name == 'datetime' or isinstance(data.index, pd.DatetimeIndex):
                data = data.reset_index()
                if 'datetime' in data.columns:
                    data = data.rename(columns={'datetime': 'time'})
                else:
                    data['time'] = data.index
            
            return data
        except Exception as e:
            self.logger.error(f"从API获取历史数据失败: {str(e)}", exc_info=True)
            raise

    def _save_to_cache(self, df: pd.DataFrame, symbol: str, period: str) -> None:
        """将数据保存到缓存

        Args:
            df: 数据
            symbol: 股票代码
            period: 周期
        """
        if df.empty:
            self.logger.warning(f"数据为空，不保存缓存")
            return

        # 按天分组保存
        self.logger.info(f"开始保存缓存数据: {symbol}, 数据点数: {len(df)}")
        
        # 确保缓存目录存在
        cache_dir = os.path.join(self.cache_dir, symbol)
        os.makedirs(cache_dir, exist_ok=True)
        
        # 检查数据格式并转换
        if 'time' not in df.columns:
            # 如果数据帧使用datetime作为索引，将其转换为列
            if df.index.name == 'datetime' or isinstance(df.index, pd.DatetimeIndex):
                self.logger.info("数据使用索引存储日期时间，转换为列格式")
                df = df.reset_index()
                if df.index.name == 'datetime':
                    df = df.rename(columns={'datetime': 'time'})
                else:
                    df['time'] = df.index
        
        # 按日期分组
        if 'time' not in df.columns:
            # 如果仍然没有time列，尝试其他可能的列名
            possible_time_cols = ['datetime', 'date', 'time']
            for col in possible_time_cols:
                if col in df.columns:
                    self.logger.info(f"使用 '{col}' 列作为时间列")
                    df = df.rename(columns={col: 'time'})
                    break
            
            if 'time' not in df.columns:
                self.logger.error(f"无法识别数据中的时间列: {df.columns}")
                return
        
        # 确保时间列是日期时间类型
        if not pd.api.types.is_datetime64_any_dtype(df['time']):
            self.logger.info("将时间列转换为日期时间类型")
            df['time'] = pd.to_datetime(df['time'])
        
        # 添加日期列用于分组
        df['date'] = df['time'].dt.date
        date_groups = df.groupby('date')
        
        self.logger.info(f"数据按天分组，共 {len(date_groups)} 个分组")
        
        for date, group in date_groups:
            # 格式化日期为YYYYMMDD
            date_str = date.strftime("%Y%m%d")
            cache_file = os.path.join(cache_dir, f"{date_str}_{period}.csv")
            
            # 删除辅助列
            group_save = group.drop(columns=['date'])
            
            self.logger.info(f"处理缓存文件: {cache_file}, 数据点数: {len(group_save)}")
            
            # 检查文件是否已存在，如果存在则合并
            if os.path.exists(cache_file):
                self.logger.info(f"缓存文件已存在，正在合并数据: {cache_file}")
                try:
                    existing_df = pd.read_csv(cache_file, parse_dates=['time'])
                    # 合并并去重
                    merged_df = pd.concat([existing_df, group_save], ignore_index=True)
                    merged_df = merged_df.drop_duplicates(subset=['time']).sort_values('time')
                    self.logger.info(f"合并后数据点数: {len(merged_df)}")
                    merged_df.to_csv(cache_file, index=False)
                    self.logger.info(f"成功保存数据到缓存: {cache_file}")
                except Exception as e:
                    self.logger.error(f"合并缓存文件失败: {cache_file}, 错误: {str(e)}")
                    # 如果合并失败，覆盖写入
                    group_save.to_csv(cache_file, index=False)
                    self.logger.info(f"覆盖保存数据到缓存: {cache_file}")
            else:
                # 直接写入
                group_save.to_csv(cache_file, index=False)
                self.logger.info(f"成功保存数据到缓存: {cache_file}")
            
            # 记录文件大小
            file_size = os.path.getsize(cache_file)
            self.logger.info(f"缓存文件已创建: {cache_file}, 大小: {file_size} 字节")
