"""
时间管理器模块
用于处理交易时间相关的逻辑和判断
"""
import logging
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)


class TimeManager:
    """时间管理器类
    
    负责处理夏令时判断、交易时段判断、收盘时间判断等功能
    """
    
    def __init__(self, params=None):
        """初始化时间管理器
        
        Args:
            params: 时间参数字典，包含时间管理所需的各种参数
        """
        # 默认参数
        self.params = {
            'avoid_open_minutes': 30,  # 避开开盘后的分钟数
            'avoid_close_minutes': 30,  # 避开收盘前的分钟数
            'close_approach_minutes': 15  # 接近收盘的分钟数
        }
        
        # 如果提供了参数，则更新默认参数
        if params:
            self.params.update(params)
            
        # 市场开盘收盘时间（美东时间）
        self.market_open_hour = 9
        self.market_open_minute = 30
        self.market_close_hour = 16
        self.market_close_minute = 0
        
    def analyze_time(self, current_time):
        """分析当前时间，判断交易时段信息
        
        Args:
            current_time: 当前时间对象
            
        Returns:
            dict: 包含交易时间信息的字典
        """
        # 使用pytz准确判断是否是夏令时
        eastern = pytz.timezone('US/Eastern')
        # 使用当前日期构建一个aware datetime对象
        # backtrader提供的datetime对象是naive的，我们需要假设它是UTC时间
        # 然后验证当前时间对应的美东时间是否在夏令时
        utc_time = pytz.utc.localize(datetime(
            current_time.year, current_time.month, current_time.day,
            current_time.hour, current_time.minute, current_time.second
        ))
        et_time = utc_time.astimezone(eastern)
        is_dst = et_time.dst() != timedelta(0)

        # 初始假设时间是美东时间
        et_hour = current_time.hour
        et_minute = current_time.minute
        is_utc_time = False

        # 判断是否可能是UTC时间格式，根据交易时间合理性判断
        # UTC时间对应美股交易时间：
        # 美东标准时(EST)：UTC-5，交易时间是UTC 14:30-21:00
        # 美东夏令时(EDT)：UTC-4，交易时间是UTC 13:30-20:00
        if is_dst:  # 夏令时
            # 如果时间在UTC交易范围内，可能是UTC时间
            if 13 <= current_time.hour <= 20:
                is_utc_time = True
                et_hour = (current_time.hour - 4) % 24  # UTC-4
        else:  # 标准时
            # 如果时间在UTC交易范围内，可能是UTC时间
            if 14 <= current_time.hour <= 21:
                is_utc_time = True
                et_hour = (current_time.hour - 5) % 24  # UTC-5

        # 计算交易时间分钟数（相对于开盘时间）
        minutes_since_open = (et_hour - self.market_open_hour) * 60 + (et_minute - self.market_open_minute)
        minutes_before_close = (self.market_close_hour - et_hour) * 60 + (self.market_close_minute - et_minute)

        # 判断是否在交易时段 (美东时间9:30-16:00)
        is_trading_time = (9 < et_hour < 16) or (et_hour == 9 and et_minute >= 30) or (et_hour == 16 and et_minute == 0)
        
        # 判断是否在安全交易时段（避开开盘和收盘的特定分钟数）
        is_safe_trading_time = is_trading_time and \
                              minutes_since_open >= self.params['avoid_open_minutes'] and \
                              minutes_before_close >= self.params['avoid_close_minutes']

        # 判断是否接近美股收盘时间 (默认美东时间15:45-16:00)
        is_near_close = (et_hour == 15 and et_minute >= (60 - self.params['close_approach_minutes'])) or et_hour == 16
        
        # 返回时间分析结果
        return {
            'is_dst': is_dst,  # 是否夏令时
            'et_hour': et_hour,  # 美东时间小时
            'et_minute': et_minute,  # 美东时间分钟
            'is_utc_time': is_utc_time,  # 是否为UTC时间
            'is_trading_time': is_trading_time,  # 是否在交易时段
            'is_safe_trading_time': is_safe_trading_time,  # 是否在安全交易时段
            'is_near_close': is_near_close,  # 是否接近收盘
            'minutes_since_open': minutes_since_open,  # 开盘后分钟数
            'minutes_before_close': minutes_before_close,  # 收盘前分钟数
            'time_format': "UTC" if is_utc_time else "ET"  # 时间格式
        }
        
    def is_trading_time(self, time_info):
        """是否在交易时段
        
        Args:
            time_info: 时间信息字典
            
        Returns:
            bool: 是否在交易时段
        """
        return time_info['is_trading_time']
    
    def is_safe_trading_time(self, time_info):
        """是否在安全交易时段（避开开盘和收盘的特定分钟数）
        
        Args:
            time_info: 时间信息字典
            
        Returns:
            bool: 是否在安全交易时段
        """
        return time_info['is_safe_trading_time']
    
    def is_near_close(self, time_info):
        """是否接近收盘时间
        
        Args:
            time_info: 时间信息字典
            
        Returns:
            bool: 是否接近收盘
        """
        return time_info['is_near_close']
    
    def log_time_info(self, current_time, time_info, trigger=False, log_interval=100, counter=0):
        """记录时间信息日志
        
        Args:
            current_time: 当前时间对象
            time_info: 时间信息字典
            trigger: 是否强制记录
            log_interval: 日志记录间隔
            counter: 当前计数
            
        Returns:
            bool: 是否记录了日志
        """
        # 每log_interval个bar记录一次或接近收盘时记录或trigger为True时记录
        if counter % log_interval == 0 or time_info['is_near_close'] or trigger:
            logger.info(
                f"时间检查: 原始时间={current_time.isoformat()}, "
                f"计算为美东时间:{time_info['et_hour']}:{time_info['et_minute']:02d}, "
                f"时间格式:{time_info['time_format']}, "
                f"交易时段:{time_info['is_trading_time']}, "
                f"安全交易时段:{time_info['is_safe_trading_time']}, "
                f"开盘后分钟数:{time_info['minutes_since_open']}, "
                f"收盘前分钟数:{time_info['minutes_before_close']}, "
                f"接近收盘:{time_info['is_near_close']}, "
                f"夏令时:{time_info['is_dst']}"
            )
            return True
        return False