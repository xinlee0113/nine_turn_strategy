import json
import os
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class SymbolConfig:
    """标的特定参数配置类，管理不同标的的策略参数"""
    
    def __init__(self, symbol_params: Optional[Dict[str, Dict[str, Any]]] = None):
        """初始化配置
        
        Args:
            symbol_params: 字典，键为标的代码，值为参数字典
        """
        self.default_params = {
            # 神奇九转核心参数
            'magic_period': 3,           # 神奇九转比较周期
            'magic_count': 5,            # 神奇九转信号触发计数
            
            # 技术指标参数
            'rsi_period': 14,            # RSI周期
            'rsi_oversold': 30,          # RSI超卖值
            'rsi_overbought': 70,        # RSI超买值
            'kdj_oversold': 20,          # KDJ超卖值
            'kdj_overbought': 80,        # KDJ超买值
            
            # 止损参数
            'atr_period': 14,            # ATR周期
            'atr_multiplier': 2.5,       # ATR乘数
            'max_loss_pct': 3.0,         # 最大止损百分比
            'min_profit_pct': 1.0,       # 追踪止损启动的最小盈利百分比
            
            # 空头参数
            'enable_short': True,        # 是否允许做空
            'short_atr_multiplier': 2.8, # 空头ATR乘数
            'short_max_loss_pct': 3.5,   # 空头最大止损百分比
            'short_min_profit_pct': 1.2, # 空头追踪止损启动的最小盈利百分比
            
            # 其他功能开关
            'trailing_stop': True,       # 是否启用追踪止损
            'risk_aversion': 1.0,        # 风险规避系数
            'volatility_adjust': True,   # 是否根据波动性调整止损
            'market_aware': True,        # 是否感知市场环境
            'time_decay': True,          # 是否启用时间衰减
            'time_decay_days': 3,        # 时间衰减开始的天数
            
            # 策略选择
            'strategy_type': 'smart_stoploss'  # 策略类型: original, advanced_stoploss, smart_stoploss
        }
        
        # 标的特定参数配置 - 基于回测结果初始化默认配置
        self.symbol_params = {
            'NVDA': {
                'magic_period': 3,
                'magic_count': 6,
                'atr_multiplier': 3.0,
                'strategy_type': 'smart_stoploss'  # 根据回测，NVDA在智能止损策略下表现最好
            },
            'TSLA': {
                'magic_period': 3,
                'magic_count': 6,
                'atr_multiplier': 3.2,
                'strategy_type': 'advanced_stoploss'  # 根据回测，TSLA在高级止损策略下表现最好
            },
            'META': {
                'magic_period': 2,
                'magic_count': 5,
                'atr_multiplier': 2.8,
                'strategy_type': 'advanced_stoploss'  # 根据回测，META在高级止损策略下表现最好
            },
            'GOOGL': {
                'magic_period': 2,
                'magic_count': 5,
                'atr_multiplier': 2.8,
                'strategy_type': 'advanced_stoploss'  # 根据回测，GOOGL在高级止损策略下表现最好
            },
            'AMZN': {
                'magic_period': 2,
                'magic_count': 5,
                'atr_multiplier': 2.2,
                'strategy_type': 'original'  # 根据回测，AMZN在原始策略下表现最好
            },
            'QQQ': {
                'magic_period': 2,
                'magic_count': 4,
                'atr_multiplier': 2.5,
                'strategy_type': 'original'  # 根据回测，QQQ在原始策略有做空下表现较好
            },
            'SPY': {
                'magic_period': 2,
                'magic_count': 4,
                'atr_multiplier': 2.2,
                'strategy_type': 'original'  # 根据回测，SPY在原始策略有做空下表现较好
            },
            'MSFT': {
                'magic_period': 2,
                'magic_count': 5,
                'atr_multiplier': 2.8,
                'strategy_type': 'advanced_stoploss'  # 根据回测，MSFT在高级止损策略下表现最好
            },
            'AAPL': {
                'magic_period': 2,
                'magic_count': 5,
                'atr_multiplier': 2.5,
                'strategy_type': 'smart_stoploss'  # 根据回测，AAPL在智能止损策略下表现最好
            }
        }
        
        # 更新用户提供的参数配置
        if symbol_params:
            for symbol, params in symbol_params.items():
                if symbol in self.symbol_params:
                    self.symbol_params[symbol].update(params)
                else:
                    self.symbol_params[symbol] = {**self.default_params, **params}
    
    def get_params(self, symbol: str) -> Dict[str, Any]:
        """获取指定标的的参数配置
        
        Args:
            symbol: 标的代码
            
        Returns:
            包含参数的字典
        """
        # 如果标的存在特定配置，则合并默认配置和特定配置
        if symbol in self.symbol_params:
            return {**self.default_params, **self.symbol_params[symbol]}
        # 否则返回默认配置
        return self.default_params.copy()
    
    def update_params(self, symbol: str, params: Dict[str, Any]) -> None:
        """更新指定标的的参数配置
        
        Args:
            symbol: 标的代码
            params: 新的参数字典
        """
        if symbol in self.symbol_params:
            self.symbol_params[symbol].update(params)
        else:
            self.symbol_params[symbol] = {**self.default_params, **params}
    
    def save_config(self, config_path: str) -> None:
        """将配置保存到JSON文件
        
        Args:
            config_path: 配置文件路径
        """
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # 辅助函数，将NumPy类型转换为Python标准类型
        def convert_numpy_types(obj):
            if hasattr(obj, 'item'):  # 检查是否是NumPy标量
                return obj.item()  # 转换为Python标准类型
            elif isinstance(obj, dict):
                return {k: convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(i) for i in obj]
            else:
                return obj
        
        # 转换数据
        converted_default = convert_numpy_types(self.default_params)
        converted_symbols = {}
        for symbol, params in self.symbol_params.items():
            converted_symbols[symbol] = convert_numpy_types(params)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump({
                "default": converted_default,
                "symbols": converted_symbols
            }, f, indent=4, ensure_ascii=False)
        
        logger.info(f"配置已保存到: {config_path}")
    
    @classmethod
    def load_config(cls, file_path: str = 'config/symbol_params.json') -> 'SymbolConfig':
        """从JSON文件加载配置
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            SymbolConfig实例
        """
        if not os.path.exists(file_path):
            logger.warning(f"配置文件不存在: {file_path}，将使用默认配置")
            return cls()
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            instance = cls()
            if 'default' in data:
                instance.default_params = data['default']
            if 'symbols' in data:
                instance.symbol_params = data['symbols']
                
            logger.info(f"已从 {file_path} 加载配置")
            return instance
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return cls()
    
    def get_all_symbols(self) -> List[str]:
        """获取所有已配置的标的列表
        
        Returns:
            标的列表
        """
        return list(self.symbol_params.keys())


class StrategyFactory:
    """策略工厂，根据配置创建适合的策略实例"""
    
    def __init__(self, symbol_config: Optional[SymbolConfig] = None):
        """初始化策略工厂
        
        Args:
            symbol_config: SymbolConfig实例或None
        """
        self.symbol_config = symbol_config or SymbolConfig()
        
    def create_strategy(self, symbol: str) -> tuple:
        """创建指定标的的策略实例
        
        Args:
            symbol: 标的代码
            
        Returns:
            策略类和参数字典的元组
        """
        # 获取标的特定参数
        params = self.symbol_config.get_params(symbol)
        
        # 获取策略类型
        strategy_type = params.pop('strategy_type', 'smart_stoploss')
        
        # 根据策略类型选择相应的策略类
        if strategy_type == 'original':
            from src.magic_nine_strategy import MagicNineStrategy
            strategy_class = MagicNineStrategy
            # 移除不兼容的参数
            for key in list(params.keys()):
                try:
                    # 尝试访问参数，如果不存在会抛出异常
                    getattr(strategy_class.params, key)
                except AttributeError:
                    logger.debug(f"参数 {key} 不适用于策略类型 {strategy_type}，将被忽略")
                    params.pop(key, None)
        elif strategy_type == 'advanced_stoploss':
            from src.magic_nine_strategy_with_advanced_stoploss import MagicNineStrategyWithAdvancedStopLoss
            strategy_class = MagicNineStrategyWithAdvancedStopLoss
            # 移除不兼容的参数
            for key in list(params.keys()):
                try:
                    # 尝试访问参数，如果不存在会抛出异常
                    getattr(strategy_class.params, key)
                except AttributeError:
                    logger.debug(f"参数 {key} 不适用于策略类型 {strategy_type}，将被忽略")
                    params.pop(key, None)
        elif strategy_type == 'smart_stoploss':
            from src.magic_nine_strategy_with_smart_stoploss import MagicNineStrategyWithSmartStopLoss
            strategy_class = MagicNineStrategyWithSmartStopLoss
            # 移除不兼容的参数
            for key in list(params.keys()):
                try:
                    # 尝试访问参数，如果不存在会抛出异常
                    getattr(strategy_class.params, key)
                except AttributeError:
                    logger.debug(f"参数 {key} 不适用于策略类型 {strategy_type}，将被忽略")
                    params.pop(key, None)
        else:
            raise ValueError(f"不支持的策略类型: {strategy_type}")
        
        return strategy_class, params 