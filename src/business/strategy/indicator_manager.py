"""
指标管理器模块
用于统一管理和初始化策略中使用的各种指标
"""
import backtrader as bt

from src.business.indicators import MagicNine


class IndicatorManager:
    """指标管理器类
    
    负责初始化和管理策略中使用的各种指标
    """
    
    def __init__(self, strategy, params=None):
        """初始化指标管理器
        
        Args:
            strategy: 策略对象，用于访问数据和参数
            params: 指标参数字典，如果为None则使用策略参数
        """
        self.strategy = strategy
        self.params = params or strategy.p
        self.data = strategy.data
        
        # 存储指标的字典
        self.indicators = {}
        
        # 初始化指标
        self._init_indicators()
        
    def _init_indicators(self):
        """初始化各种指标"""
        # 初始化神奇九转指标
        self.indicators['magic_nine'] = MagicNine(self.data, lookback=self.params.magic_period)
        
        # 初始化RSI指标
        self.indicators['rsi'] = bt.indicators.RSI(
            self.data,
            period=self.params.rsi_period
        )
        
        # 初始化EMA指标
        self.indicators['ema20'] = bt.indicators.EMA(self.data, period=20)
        self.indicators['ema50'] = bt.indicators.EMA(self.data, period=50)
        
        # 初始化ATR指标
        self.indicators['atr'] = bt.indicators.ATR(
            self.data,
            period=self.params.atr_period
        )
        
    def get(self, name):
        """获取指定名称的指标
        
        Args:
            name: 指标名称
            
        Returns:
            指标对象，如果不存在则返回None
        """
        return self.indicators.get(name)
        
    def get_magic_nine(self):
        """获取神奇九转指标
        
        Returns:
            MagicNine: 神奇九转指标对象
        """
        return self.indicators['magic_nine']
        
    def get_rsi(self):
        """获取RSI指标
        
        Returns:
            RSI: RSI指标对象
        """
        return self.indicators['rsi']
        
    def get_ema20(self):
        """获取20周期EMA指标
        
        Returns:
            EMA: 20周期EMA指标对象
        """
        return self.indicators['ema20']
        
    def get_ema50(self):
        """获取50周期EMA指标
        
        Returns:
            EMA: 50周期EMA指标对象
        """
        return self.indicators['ema50']
        
    def get_atr(self):
        """获取ATR指标
        
        Returns:
            ATR: ATR指标对象
        """
        return self.indicators['atr']
        
    def __getattr__(self, name):
        """通过属性访问指标
        
        当尝试访问不存在的属性时，尝试从indicators字典中获取
        
        Args:
            name: 属性名
            
        Returns:
            指标对象
            
        Raises:
            AttributeError: 如果指标不存在
        """
        if name in self.indicators:
            return self.indicators[name]
        raise AttributeError(f"'IndicatorManager' has no attribute '{name}'")