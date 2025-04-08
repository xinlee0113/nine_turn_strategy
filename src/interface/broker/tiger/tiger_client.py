"""
老虎证券客户端实现
"""
import logging
import os
from datetime import datetime
from typing import Dict, List

import pandas as pd
from tigeropen.common.consts import Language, BarPeriod
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig

from src.infrastructure.constants.const import TimeInterval, TimeZone, MAX_1MIN_DATA_DAYS, DATA_REQUIRED_COLUMNS


class TigerClient:
    """老虎证券客户端类"""

    def __init__(self):
        """初始化客户端"""
        self.logger = logging.getLogger(__name__)
        self.connected = False
        self._api_client = None
        self._initialize_api_client()

    def _get_config_paths(self) -> tuple[str, str]:
        """获取配置文件路径
        
        Returns:
            tuple[str, str]: (配置文件路径, 私钥文件路径)
        
        Raises:
            FileNotFoundError: 配置文件不存在时抛出
        """
        # 获取项目根目录的绝对路径
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        config_path = os.path.join(base_dir, "configs", "tiger", "tiger_openapi_config.properties")
        private_key_path = os.path.join(base_dir, "configs", "tiger", "private_key.pem")

        # 验证文件是否存在
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        if not os.path.exists(private_key_path):
            raise FileNotFoundError(f"私钥文件不存在: {private_key_path}")

        return config_path, private_key_path

    def _initialize_api_client(self):
        """初始化API客户端"""
        try:
            # 获取配置文件路径
            config_path, private_key_path = self._get_config_paths()

            # 初始化Tiger API客户端
            self.tiger_client_config = TigerOpenClientConfig(sandbox_debug=False,
                                                             props_path=config_path)
            self.tiger_client_config.private_key = read_private_key(private_key_path)
            self.tiger_client_config.language = Language.zh_CN
            self.tiger_client_config.timeout = 60

            self._api_client = QuoteClient(self.tiger_client_config)
            self._api_client.grab_quote_permission()
            self.logger.info("Tiger API客户端初始化成功")
        except Exception as e:
            self.logger.error(f"Tiger API客户端初始化失败: {str(e)}")
            raise

    def connect(self) -> bool:
        """连接服务器"""
        try:
            if self._api_client is None:
                raise ValueError("API客户端未初始化")
            self.connected = True
            return True
        except Exception as e:
            self.logger.error(f"连接服务器失败: {str(e)}")
            return False

    def disconnect(self) -> bool:
        """断开连接"""
        try:
            self.connected = False
            return True
        except Exception as e:
            self.logger.error(f"断开连接失败: {str(e)}")
            return False

    def _convert_period(self, period: str) -> BarPeriod:
        """转换周期字符串为Tiger API枚举值"""
        period_map = {
            TimeInterval.ONE_MINUTE.value: BarPeriod.ONE_MINUTE,
            TimeInterval.FIVE_MINUTES.value: BarPeriod.FIVE_MINUTES,
            TimeInterval.FIFTEEN_MINUTES.value: BarPeriod.FIFTEEN_MINUTES,
            TimeInterval.THIRTY_MINUTES.value: BarPeriod.HALF_HOUR,
            TimeInterval.ONE_HOUR.value: BarPeriod.ONE_HOUR,
            TimeInterval.ONE_DAY.value: BarPeriod.DAY,
            TimeInterval.ONE_WEEK.value: BarPeriod.WEEK,
            TimeInterval.ONE_MONTH.value: BarPeriod.MONTH
        }
        return period_map.get(period, BarPeriod.ONE_MINUTE)

    def get_historical_data(self, symbol: str, start_date: datetime,
                            end_date: datetime, interval: str) -> pd.DataFrame:
        """获取历史数据，通过分块查询处理长时间范围"""
        if not self.connected:
            raise ConnectionError("客户端未连接")

        try:
            # 确保日期对象有一致的时区信息
            # 转换为pandas Timestamp并确保具有时区信息
            start_date_ts = pd.Timestamp(start_date)
            end_date_ts = pd.Timestamp(end_date)

            # 如果没有时区信息，则添加UTC时区
            if start_date_ts.tz is None:
                start_date_ts = start_date_ts.tz_localize(TimeZone.UTC.value)
            if end_date_ts.tz is None:
                end_date_ts = end_date_ts.tz_localize(TimeZone.UTC.value)

            # 确保都是同一个时区
            start_date_eastern = start_date_ts.tz_convert(TimeZone.US_EASTERN.value)
            end_date_eastern = end_date_ts.tz_convert(TimeZone.US_EASTERN.value)

            # 计算日期差异时使用tz-aware的时间戳
            date_diff = (end_date_eastern - start_date_eastern).days

            # 对于1分钟K线，老虎证券API限制最多只能获取30天数据
            if interval == TimeInterval.ONE_MINUTE.value and date_diff > MAX_1MIN_DATA_DAYS:
                self.logger.warning(f"1分钟K线只能获取最近{MAX_1MIN_DATA_DAYS}天的数据，当前请求时间范围：{date_diff}天")
                self.logger.warning(
                    f"将起始日期从 {start_date_eastern} 调整为 {end_date_eastern - pd.Timedelta(days=MAX_1MIN_DATA_DAYS)}")
                start_date_eastern = end_date_eastern - pd.Timedelta(days=MAX_1MIN_DATA_DAYS)

            time_interval = 2  # 每次数据的时间间隔
            # 转换为Tiger API所需的周期
            period = self._convert_period(interval)
            data = self._api_client.get_bars_by_page(symbol, period=period,
                                                     begin_time=start_date_eastern.value // 10 ** 6,
                                                     end_time=end_date_eastern.value // 10 ** 6,
                                                     time_interval=time_interval)

            if data.empty:
                return pd.DataFrame()

            # 添加中国时间、美国东部时间和UTC时间
            data['cn_date'] = pd.to_datetime(data['time'], unit='ms').dt.tz_localize(TimeZone.UTC.value).dt.tz_convert(
                TimeZone.CHINA.value)
            data['us_date'] = pd.to_datetime(data['time'], unit='ms').dt.tz_localize(TimeZone.UTC.value).dt.tz_convert(
                TimeZone.US_EASTERN.value)
            data['utc_date'] = pd.to_datetime(data['time'], unit='ms').dt.tz_localize(TimeZone.UTC.value)

            # 数据清洗和格式化
            if 'next_page_token' in data.columns:
                data = data.drop(columns=['next_page_token'])

            data['time'] = pd.to_datetime(data['time'], unit='ms')
            data.set_index('time', inplace=True)
            data.index.name = 'datetime'

            data = data.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })

            # 只保留必要的列
            data = data[DATA_REQUIRED_COLUMNS]

            # 去重并排序，因为分块获取可能导致重叠或顺序问题
            data = data[~data.index.duplicated(keep='first')]
            data.sort_index(inplace=True)

            self.logger.info(f"Successfully fetched and concatenated {len(data)} unique records for {symbol}.")
            return data

        except Exception as e:
            self.logger.error(f"获取历史数据失败: {str(e)}")
            raise

    def get_realtime_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """获取实时行情"""
        if not self.connected:
            raise ConnectionError("客户端未连接")

        try:
            # 使用正确的Tiger API方法获取实时行情
            quotes_data = {}
            for symbol in symbols:
                try:
                    # 使用get_stock_briefs方法获取行情数据
                    briefs_df = self._api_client.get_stock_briefs(symbols=[symbol])

                    # 正确处理DataFrame返回值
                    if briefs_df is not None and not briefs_df.empty:
                        # 从DataFrame提取第一行
                        brief = briefs_df.iloc[0]
                        quotes_data[symbol] = {
                            'symbol': symbol,
                            'last_price': float(brief.get('latest_price', 0)),
                            'volume': int(brief.get('volume', 0)) if 'volume' in brief else 0,
                            'open': float(brief.get('open', 0)) if 'open' in brief else 0,
                            'high': float(brief.get('high', 0)) if 'high' in brief else 0,
                            'low': float(brief.get('low', 0)) if 'low' in brief else 0,
                            'timestamp': datetime.now(),
                            'change': float(brief.get('change', 0)) if 'change' in brief else 0,
                            'change_rate': float(brief.get('change_rate', 0)) if 'change_rate' in brief else 0
                        }
                        self.logger.info(f"成功获取 {symbol} 的实时行情")
                except Exception as e:
                    self.logger.warning(f"获取 {symbol} 的实时行情失败: {str(e)}")
                    # 尝试使用备用方法：market_status
                    try:
                        # 修复：get_market_status方法返回的可能是字典，但也可能是其他格式
                        status = self._api_client.get_market_status()
                        # 修复：确保status是字典类型，并且symbol是其中的键
                        if status and isinstance(status, dict):
                            # 使用get方法避免KeyError
                            symbol_status = status.get(symbol)
                            if symbol_status is not None:
                                quotes_data[symbol] = {
                                    'symbol': symbol,
                                    'status': symbol_status,
                                    'timestamp': datetime.now(),
                                }
                                self.logger.info(f"使用市场状态方法获取 {symbol} 的状态: {symbol_status}")
                    except Exception as ex:
                        self.logger.warning(f"备用方法获取 {symbol} 的状态也失败: {str(ex)}")

            return quotes_data

        except Exception as e:
            self.logger.error(f"获取实时行情失败: {str(e)}")
            raise
