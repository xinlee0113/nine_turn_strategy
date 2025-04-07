"""
老虎证券客户端实现
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import logging
import time
import os
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.consts import Language, BarPeriod, Market
from tigeropen.common.util.signature_utils import read_private_key


class TigerClient:
    """老虎证券客户端类"""

    def __init__(self):
        """初始化客户端"""
        self.logger = logging.getLogger(__name__)
        self.connected = False
        self._api_client: QuoteClient = None
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
            '1m': BarPeriod.ONE_MINUTE,
            '5m': BarPeriod.FIVE_MINUTES,
            '15m': BarPeriod.FIFTEEN_MINUTES,
            '30m': BarPeriod.HALF_HOUR,
            '1h': BarPeriod.ONE_HOUR,
            '1d': BarPeriod.DAY,
            '1w': BarPeriod.WEEK,
            '1M': BarPeriod.MONTH
        }
        return period_map.get(period, BarPeriod.ONE_MINUTE)

    def get_historical_data(self, symbol: str, start_date: datetime,
                            end_date: datetime, interval: str) -> pd.DataFrame:
        """获取历史数据，通过分块查询处理长时间范围"""
        if not self.connected:
            raise ConnectionError("客户端未连接")

        try:
            begin_time = start_date

            start_date = pd.Timestamp(begin_time).tz_convert('US/Eastern')
            end_date = pd.Timestamp(end_date).tz_convert('US/Eastern')

            time_interval = 2  # 每次数据的时间间隔
            # 转换为Tiger API所需的周期
            period = self._convert_period(interval)
            data = self._api_client.get_bars_by_page(symbol, period=period,
                                                     begin_time=start_date.value // 10 ** 6,
                                                     end_time=end_date.value // 10 ** 6,
                                                     time_interval=time_interval)

            data['cn_date'] = pd.to_datetime(data['time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai')
            data['us_date'] = pd.to_datetime(data['time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('US/Eastern')
            data['utc_date'] = pd.to_datetime(data['time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('UTC')

            if data.empty:
                return pd.DataFrame()

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

            required_columns = ['open', 'high', 'low', 'close', 'volume']
            data = data[required_columns]

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
            # 修正：获取实时行情应该使用 get_real_time_quotes 而不是 get_market_status
            quotes_data = self._api_client.get_real_time_quotes(symbols=symbols)

            if not quotes_data:  # 检查返回是否为空列表
                return {}

            # quotes_data 是一个 list of dicts
            result = {}
            for quote in quotes_data:
                symbol = quote.get('symbol')
                if symbol:
                    result[symbol] = {
                        'symbol': symbol,
                        'last_price': quote.get('latest_price'),
                        'volume': quote.get('volume'),
                        # 注意：时间戳字段名可能需要确认，这里假设是 'timestamp' 或类似字段
                        # 'timestamp': quote.get('timestamp') 
                        'timestamp': quote.get('latest_time')  # 根据API文档或实际返回调整
                    }
            return result

        except Exception as e:
            self.logger.error(f"获取实时行情失败: {str(e)}")
            raise
