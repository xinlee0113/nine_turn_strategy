import logging
import os
from datetime import datetime
from typing import Optional, Dict, List

import pandas as pd

from .base_data import BaseData


class CSVData(BaseData):
    """CSV数据接口，用于从CSV文件加载历史数据"""

    def __init__(self, file_path: str):
        """初始化CSV数据源
        
        Args:
            file_path: CSV文件路径，可以是目录或单个文件
        """
        super().__init__()
        self.file_path = file_path
        self.logger = logging.getLogger(__name__)
        self.dataframe = None
        self.started = False
        self.data_cache = {}  # 内存缓存

    def start(self) -> bool:
        """启动数据源"""
        try:
            if not self.started:
                self.logger.info(f"启动CSV数据源: {self.file_path}")
                self.started = True
            return True
        except Exception as e:
            self.logger.error(f"启动CSV数据源失败: {str(e)}")
            return False

    def stop(self) -> bool:
        """停止数据源"""
        try:
            if self.started:
                self.logger.info("停止CSV数据源")
                self.dataframe = None
                self.started = False
            return True
        except Exception as e:
            self.logger.error(f"停止CSV数据源失败: {str(e)}")
            return False

    def get_data(self, symbol: str, start_date: datetime,
                 end_date: datetime, interval: str = "1m") -> Optional[pd.DataFrame]:
        """从CSV文件获取数据
        
        Args:
            symbol: 交易标的代码
            start_date: 开始时间
            end_date: 结束时间
            interval: 时间间隔
            
        Returns:
            DataFrame: 包含OHLCV数据的DataFrame
        """
        if not self.started:
            self.logger.warning("数据源未启动，尝试自动启动")
            if not self.start():
                raise ConnectionError("CSV数据源启动失败")

        # 生成缓存键
        cache_key = f"{symbol}_{start_date.isoformat()}_{end_date.isoformat()}_{interval}"

        # 检查内存缓存
        if cache_key in self.data_cache:
            self.logger.info(f"从内存缓存获取数据: {cache_key}")
            return self.data_cache[cache_key]

        try:
            self.logger.info(f"从CSV加载数据: {symbol}, {start_date} - {end_date}, {interval}")

            # 确定要加载的文件
            if os.path.isdir(self.file_path):
                # 如果是目录，查找匹配的文件
                file_pattern = f"{symbol}_{interval}.csv"
                # 构建完整路径
                csv_file = os.path.join(self.file_path, file_pattern)

                # 检查文件是否存在
                if not os.path.exists(csv_file):
                    # 尝试其他可能的文件名格式
                    alternative_patterns = [
                        f"{symbol}.csv",
                        f"{symbol}_{start_date.strftime('%Y%m%d')}_{interval}.csv",
                        f"{symbol}_{interval}_{start_date.strftime('%Y%m%d')}.csv"
                    ]

                    for pattern in alternative_patterns:
                        alt_file = os.path.join(self.file_path, pattern)
                        if os.path.exists(alt_file):
                            csv_file = alt_file
                            self.logger.info(f"找到匹配的CSV文件: {csv_file}")
                            break
                    else:
                        self.logger.warning(f"未找到匹配的CSV文件: {symbol}, {interval}")
                        return pd.DataFrame()
            else:
                # 如果是文件路径，直接使用
                csv_file = self.file_path
                if not os.path.exists(csv_file):
                    self.logger.warning(f"CSV文件不存在: {csv_file}")
                    return pd.DataFrame()

            # 读取CSV文件
            self.logger.info(f"读取CSV文件: {csv_file}")
            df = pd.read_csv(csv_file, parse_dates=True)

            # 设置日期索引
            datetime_columns = ['datetime', 'time', 'date']
            for col in datetime_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
                    df.set_index(col, inplace=True)
                    df.index.name = 'datetime'
                    break

            # 过滤时间范围
            if isinstance(df.index, pd.DatetimeIndex):
                mask = (df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))
                df = df.loc[mask]

            # 确保有必要的列
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    self.logger.warning(f"CSV数据缺少必要的列: {col}")

            # 验证数据
            self._validate_data(df, symbol, start_date, end_date, interval)

            # 缓存数据
            if not df.empty:
                self.data_cache[cache_key] = df
                self.logger.info(f"CSV数据加载成功: {symbol}, 数据点数: {len(df)}")
            else:
                self.logger.warning(f"未找到匹配时间范围的CSV数据: {symbol}, {start_date} - {end_date}")

            return df

        except Exception as e:
            self.logger.error(f"从CSV获取数据失败: {str(e)}")
            raise

    def get_realtime_quotes(self, symbols: List[str]) -> Optional[Dict]:
        """获取实时行情（CSV数据源不支持实时行情）"""
        self.logger.warning("CSV数据源不支持实时行情")
        raise NotImplementedError("CSV数据源不支持实时行情")

    def get_historical_data(self, symbol: str, start_date: datetime,
                            end_date: datetime, interval: str = "1m") -> Optional[pd.DataFrame]:
        """获取历史数据（与get_data保持一致，符合BaseData接口）"""
        return self.get_data(symbol, start_date, end_date, interval)

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
            self.logger.warning(f"CSV数据为空: {symbol}")
            return

        # 检查必要的列
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            self.logger.warning(f"CSV数据缺少必要的列: {missing_columns}")

        # 检查时间索引
        if not isinstance(df.index, pd.DatetimeIndex):
            self.logger.warning(f"CSV数据索引不是DatetimeIndex类型")

        # 检查数据连续性 (对于1分钟数据，交易日应有连续的数据点)
        if interval == "1m":
            # 按天分组计数
            if isinstance(df.index, pd.DatetimeIndex):
                daily_counts = df.groupby(df.index.date).size()

                # 对于CSV数据，不检查精确的数据点数量，只记录信息
                for date, count in daily_counts.items():
                    self.logger.info(f"CSV数据日期 {date} 的数据点数量: {count}")

        # 记录数据范围信息
        if not df.empty:
            self.logger.info(f"CSV数据时间范围: {df.index.min()} - {df.index.max()}")
            self.logger.info(f"CSV数据点数量: {len(df)}")
