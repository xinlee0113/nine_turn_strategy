"""
常量定义
包含系统中使用的各种常量和枚举，以避免在代码中使用硬编码的字符串和数字
"""
from enum import Enum


# 数据周期
class TimeInterval(str, Enum):
    """数据时间周期"""
    ONE_MINUTE = "1m"  # 1分钟
    FIVE_MINUTES = "5m"  # 5分钟
    FIFTEEN_MINUTES = "15m"  # 15分钟
    THIRTY_MINUTES = "30m"  # 30分钟
    ONE_HOUR = "1h"  # 1小时
    FOUR_HOURS = "4h"  # 4小时
    ONE_DAY = "1d"  # 1天
    ONE_WEEK = "1w"  # 1周
    ONE_MONTH = "1M"  # 1月

    @classmethod
    def get_all_values(cls):
        """获取所有时间周期的值"""
        return [e.value for e in cls]


# 市场类型
class MarketType(str, Enum):
    """市场类型"""
    US = "US"  # 美国市场
    HK = "HK"  # 香港市场
    CN = "CN"  # 中国市场

    @classmethod
    def get_all_values(cls):
        """获取所有市场类型的值"""
        return [e.value for e in cls]


# 交易方向
class TradeDirection(str, Enum):
    """交易方向"""
    BUY = "BUY"  # 买入
    SELL = "SELL"  # 卖出


# 数据源类型
class DataSourceType(str, Enum):
    """数据源类型"""
    TIGER = "TIGER"  # 老虎证券
    PANDAS = "PANDAS"  # Pandas数据
    CSV = "CSV"  # CSV文件
    DATABASE = "DB"  # 数据库


# 时区常量
class TimeZone(str, Enum):
    """时区常量"""
    UTC = "UTC"  # 协调世界时
    US_EASTERN = "US/Eastern"  # 美国东部时间（纽约）
    CHINA = "Asia/Shanghai"  # 中国时间
    HONGKONG = "Asia/Hong_Kong"  # 香港时间


# 交易所常量
class Exchange(str, Enum):
    """交易所常量"""
    NYSE = "NYSE"  # 纽约证券交易所
    NASDAQ = "NASDAQ"  # 纳斯达克
    AMEX = "AMEX"  # 美国证券交易所
    SSE = "SSE"  # 上海证券交易所
    SZSE = "SZSE"  # 深圳证券交易所
    HKEX = "HKEX"  # 香港交易所


# 数据相关常量
DATA_REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]  # 必需的数据列
US_MARKET_MINUTES_PER_DAY = 390  # 美股每个交易日的分钟数 (6.5小时 = 390分钟)
MAX_1MIN_DATA_DAYS = 30  # 1分钟K线数据最大请求天数（老虎证券API限制）

# 回测相关常量
DEFAULT_INITIAL_CAPITAL = 1000000  # 默认初始资金：100万
DEFAULT_COMMISSION_RATE = 0.0000  # 默认佣金率：万分之三
