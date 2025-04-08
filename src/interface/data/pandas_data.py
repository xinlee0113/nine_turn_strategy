"""
Pandas数据源实现
"""
import logging
from datetime import datetime
from typing import Dict, Optional, List

import pandas as pd

from src.infrastructure.constants.const import TimeInterval, DATA_REQUIRED_COLUMNS, US_MARKET_MINUTES_PER_DAY
from src.interface.broker.tiger.tiger_client import TigerClient
from src.interface.store.tiger_store import TigerStore
from .base_data import BaseData


class PandasData(BaseData):
    """Pandas数据源类"""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        try:
            client = TigerClient()
            client.connect()
            self.store = TigerStore(client=client)
            self.logger.info("初始化PandasData成功：TigerClient和TigerStore已连接")
        except Exception as e:
            self.logger.error(f"初始化TigerStore失败: {e}")
            self.store = None
            raise

        self.started = False
        self.data_cache = {}  # 内存缓存，用于存储已加载的数据

    def start(self) -> bool:
        """启动数据源"""
        if self.store is None:
            self.logger.error("数据存储未成功初始化，无法启动")
            return False
        try:
            if not self.started:
                self.started = self.store.start()
                self.logger.info("数据源启动成功")
            return self.started
        except Exception as e:
            self.logger.error(f"启动数据源失败: {str(e)}")
            return False

    def stop(self) -> bool:
        """停止数据源"""
        if self.store is None:
            self.logger.warning("数据存储未初始化，无需停止")
            return True
        try:
            if self.started:
                self.started = not self.store.stop()
                self.logger.info("数据源停止成功")
            return not self.started
        except Exception as e:
            self.logger.error(f"停止数据源失败: {str(e)}")
            return False

    def get_data(self, symbol: str, start_date: datetime,
                 end_date: datetime, interval: str = TimeInterval.ONE_MINUTE.value) -> Optional[pd.DataFrame]:
        """获取历史数据，遵循架构图中的数据加载流程
        
        Args:
            symbol: 交易标的代码
            start_date: 开始时间
            end_date: 结束时间
            interval: 时间间隔，默认为1分钟
            
        Returns:
            DataFrame: 包含OHLCV数据的DataFrame
        """
        if not self.started:
            self.logger.warning("数据源未启动，尝试自动启动")
            if not self.start():
                raise ConnectionError("数据源启动失败")

        if self.store is None:
            raise RuntimeError("数据存储未成功初始化")

        # 生成缓存键
        cache_key = f"{symbol}_{start_date.isoformat()}_{end_date.isoformat()}_{interval}"

        # 检查内存缓存
        if cache_key in self.data_cache:
            self.logger.info(f"从内存缓存获取数据: {cache_key}")
            return self.data_cache[cache_key]

        try:
            self.logger.info(f"请求历史数据: {symbol}, {start_date} - {end_date}, {interval}")
            # 从数据存储中获取数据
            df = self.store.get_data(symbol=symbol,
                                     start_date=start_date,
                                     end_date=end_date,
                                     interval=interval)

            if df is not None and not df.empty:
                # 确保数据有datetime索引
                if not isinstance(df.index, pd.DatetimeIndex):
                    self.logger.info("转换数据索引为DatetimeIndex")
                    # 检查是否有datetime列
                    if 'time' in df.columns:
                        # 将time列转换为datetime索引
                        df['time'] = pd.to_datetime(df['time'])
                        df.set_index('time', inplace=True)
                        df.index.name = 'datetime'
                    elif 'datetime' in df.columns:
                        df.set_index('datetime', inplace=True)
                    elif df.index.name == 'datetime':
                        # 如果索引名称已经是datetime，但不是DatetimeIndex类型
                        df.index = pd.to_datetime(df.index)
                    else:
                        # 如果没有time或datetime列，记录警告，但继续处理
                        self.logger.warning("无法找到time或datetime列，将使用数据的原始索引")

                # 验证数据的完整性
                self._validate_data(df, symbol, start_date, end_date, interval)

                # 缓存数据到内存
                self.data_cache[cache_key] = df

                self.logger.info(f"数据加载成功: {symbol}, 数据点数: {len(df)}")
                return df
            else:
                self.logger.warning(f"未获取到数据: {symbol}, {start_date} - {end_date}")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"获取数据失败: {str(e)}")
            raise

    def get_historical_data(self, symbol: str, start_date: datetime,
                            end_date: datetime, interval: str = TimeInterval.ONE_MINUTE.value) -> Optional[
        pd.DataFrame]:
        """获取历史数据 (与get_data保持一致，为了符合BaseData接口)"""
        return self.get_data(symbol, start_date, end_date, interval)

    def get_realtime_quotes(self, symbols: List[str]) -> Optional[Dict]:
        """获取实时行情"""
        if not self.started:
            self.logger.warning("数据源未启动，尝试自动启动")
            if not self.start():
                raise ConnectionError("数据源启动失败")

        if self.store is None:
            raise RuntimeError("数据存储未成功初始化")

        try:
            self.logger.info(f"请求实时行情: {symbols}")
            quotes = self.store.get_realtime_quotes(symbols)
            self.logger.info(f"获取实时行情成功: {len(quotes)} 个标的")
            return quotes
        except Exception as e:
            self.logger.error(f"获取实时行情失败: {str(e)}")
            raise

    def _validate_data(self, df: pd.DataFrame, symbol: str,
                       start_date: datetime, end_date: datetime, interval: str) -> None:
        """验证数据完整性
        
        Args:
            df: 数据DataFrame
            symbol: 交易标的代码
            start_date: 开始时间
            end_date: 结束时间
            interval: 时间间隔
        """
        if df.empty:
            self.logger.warning(f"数据为空: {symbol}")
            return

        # 检查必要的列
        missing_columns = [col for col in DATA_REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            self.logger.warning(f"数据缺少必要的列: {missing_columns}")

        # 检查时间索引
        if not isinstance(df.index, pd.DatetimeIndex):
            self.logger.warning(f"数据索引不是DatetimeIndex类型")

        # 检查数据连续性 (对于1分钟数据，每个交易日应有390个数据点)
        if interval == TimeInterval.ONE_MINUTE.value:
            # 按天分组计数
            if isinstance(df.index, pd.DatetimeIndex):
                daily_counts = df.groupby(df.index.date).size()
                expected_points = US_MARKET_MINUTES_PER_DAY  # 美股一个交易日有390分钟

                # 检查每天的数据点数量
                for date, count in daily_counts.items():
                    completeness = count / expected_points * 100
                    if count < expected_points * 0.9:  # 允许90%的完整度
                        self.logger.warning(
                            f"日期 {date} 的数据点数量不足: {count}/{expected_points} ({completeness:.1f}%)")

        # 记录数据范围信息
        self.logger.info(f"数据时间范围: {df.index.min()} - {df.index.max()}")
        self.logger.info(f"数据点数量: {len(df)}")

    def analyze_data_continuity(self, data: pd.DataFrame, interval: str = TimeInterval.ONE_MINUTE.value) -> dict:
        """分析数据连续性
        
        Args:
            data: 数据DataFrame
            interval: 时间间隔，默认为1分钟
            
        Returns:
            dict: 连续性分析结果
        """
        result = {
            "data_points": len(data),
            "missing_points": 0,
            "gaps": [],
            "completeness": 100.0
        }

        if data.empty:
            return result

        # 确保索引是DatetimeIndex类型
        if not isinstance(data.index, pd.DatetimeIndex):
            return result

        # 创建期望的日期范围
        if interval == TimeInterval.ONE_MINUTE.value:
            expected_freq = TimeInterval.ONE_MINUTE.value
            expected_points_per_day = US_MARKET_MINUTES_PER_DAY
        elif interval == TimeInterval.FIVE_MINUTES.value:
            expected_freq = TimeInterval.FIVE_MINUTES.value
            expected_points_per_day = US_MARKET_MINUTES_PER_DAY // 5
        elif interval == TimeInterval.FIFTEEN_MINUTES.value:
            expected_freq = TimeInterval.FIFTEEN_MINUTES.value
            expected_points_per_day = US_MARKET_MINUTES_PER_DAY // 15
        elif interval == TimeInterval.THIRTY_MINUTES.value:
            expected_freq = TimeInterval.THIRTY_MINUTES.value
            expected_points_per_day = US_MARKET_MINUTES_PER_DAY // 30
        elif interval == TimeInterval.ONE_HOUR.value:
            expected_freq = TimeInterval.ONE_HOUR.value
            expected_points_per_day = US_MARKET_MINUTES_PER_DAY // 60
        else:
            # 对于日线及以上周期，返回简化的结果
            return result

        # 计算每个交易日的数据点数量
        daily_counts = data.groupby(data.index.date).size()

        # 计算缺失的数据点
        missing_points = 0
        for date, count in daily_counts.items():
            if count < expected_points_per_day:
                missing_points += (expected_points_per_day - count)

        # 计算完整性
        total_expected_points = len(daily_counts) * expected_points_per_day
        completeness = (
                                   total_expected_points - missing_points) / total_expected_points * 100 if total_expected_points > 0 else 100

        # 寻找时间间隔中的大间隔
        gaps = []
        if len(data) > 1:
            # 计算相邻时间点之间的差值
            time_diffs = data.index.to_series().diff().dropna()

            # 计算预期的正常间隔
            if interval == TimeInterval.ONE_MINUTE.value:
                normal_diff = pd.Timedelta(minutes=1)
            elif interval == TimeInterval.FIVE_MINUTES.value:
                normal_diff = pd.Timedelta(minutes=5)
            elif interval == TimeInterval.FIFTEEN_MINUTES.value:
                normal_diff = pd.Timedelta(minutes=15)
            elif interval == TimeInterval.THIRTY_MINUTES.value:
                normal_diff = pd.Timedelta(minutes=30)
            elif interval == TimeInterval.ONE_HOUR.value:
                normal_diff = pd.Timedelta(hours=1)
            else:
                normal_diff = pd.Timedelta(days=1)

            # 找出明显大于正常间隔的差值
            large_gaps = time_diffs[time_diffs > normal_diff * 2]

            for idx, gap in large_gaps.items():
                # 修复：使用时间戳的索引位置而不是直接计算
                idx_position = data.index.get_indexer([idx])[0]
                if idx_position > 0:
                    start_time = data.index[idx_position - 1]
                    end_time = idx
                    # 修复：确保都是datetime类型再调用strftime
                    gaps.append({
                        "start": start_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(start_time, 'strftime') else str(
                            start_time),
                        "end": end_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(end_time, 'strftime') else str(
                            end_time),
                        "duration": str(gap)
                    })

        # 更新结果
        result["missing_points"] = missing_points
        result["gaps"] = gaps
        result["completeness"] = completeness

        return result
