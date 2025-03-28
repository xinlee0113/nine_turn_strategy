import numpy as np
import pandas as pd
from enum import Enum

class StrategyType(Enum):
    """策略类型枚举"""
    ORIGINAL = "原始策略"
    ADVANCED_STOP_LOSS = "高级止损策略" 
    SMART_STOP_LOSS = "智能止损策略"

class StrategySelector:
    """
    策略选择器：根据市场状态和资产特性选择最优策略
    """
    
    def __init__(self, market_analyzer, lookback_window=20, volatility_threshold=0.015, trend_threshold=0.3):
        """
        初始化策略选择器
        
        参数:
            market_analyzer: 市场分析器实例
            lookback_window: 回看窗口大小
            volatility_threshold: 波动率阈值，超过此值视为高波动
            trend_threshold: 趋势强度阈值，超过此值视为强趋势
        """
        self.market_analyzer = market_analyzer
        self.lookback_window = lookback_window
        self.volatility_threshold = volatility_threshold
        self.trend_threshold = trend_threshold
        
        # 特定资产的最优策略映射
        self.asset_strategy_map = {
            'QQQ': {
                'volatile': StrategyType.SMART_STOP_LOSS,
                'trending': StrategyType.ORIGINAL,
                'range_bound': StrategyType.ADVANCED_STOP_LOSS,
                'default': StrategyType.SMART_STOP_LOSS
            },
            'SPY': {
                'volatile': StrategyType.ADVANCED_STOP_LOSS,
                'trending': StrategyType.ORIGINAL,
                'range_bound': StrategyType.ADVANCED_STOP_LOSS,
                'default': StrategyType.ADVANCED_STOP_LOSS
            },
            'TSLA': {
                'volatile': StrategyType.SMART_STOP_LOSS,
                'trending': StrategyType.ORIGINAL,
                'range_bound': StrategyType.ADVANCED_STOP_LOSS,
                'default': StrategyType.ORIGINAL
            }
        }
        
        # 默认策略映射（适用于未特别配置的资产）
        self.default_strategy_map = {
            'volatile': StrategyType.SMART_STOP_LOSS,
            'trending': StrategyType.ORIGINAL,
            'range_bound': StrategyType.ADVANCED_STOP_LOSS,
            'default': StrategyType.SMART_STOP_LOSS
        }
        
        # 特定资产的参数调整
        self.asset_params_map = {
            'QQQ': {
                StrategyType.SMART_STOP_LOSS: {'risk_aversion': 1.5},
                StrategyType.ADVANCED_STOP_LOSS: {'atr_multiplier': 2.0}
            },
            'SPY': {
                StrategyType.SMART_STOP_LOSS: {'risk_aversion': 1.2},
                StrategyType.ADVANCED_STOP_LOSS: {'atr_multiplier': 2.5}
            },
            'TSLA': {
                StrategyType.SMART_STOP_LOSS: {'risk_aversion': 1.3},
                StrategyType.ADVANCED_STOP_LOSS: {'atr_multiplier': 2.2}
            }
        }
    
    def calculate_volatility(self, prices):
        """计算波动率"""
        returns = np.diff(prices) / prices[:-1]
        return np.std(returns) * np.sqrt(252)  # 年化波动率
    
    def calculate_trend(self, prices):
        """计算趋势强度（使用线性回归的R平方值）"""
        x = np.arange(len(prices))
        y = prices
        
        # 计算均值
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        
        # 计算线性回归参数
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        
        if denominator == 0:
            return 0
            
        # 计算斜率和截距
        slope = numerator / denominator
        intercept = y_mean - (slope * x_mean)
        
        # 预测值
        y_pred = intercept + slope * x
        
        # 计算R平方值
        ss_total = np.sum((y - y_mean) ** 2)
        ss_residual = np.sum((y - y_pred) ** 2)
        
        if ss_total == 0:
            return 0
            
        r_squared = 1 - (ss_residual / ss_total)
        return r_squared
    
    def get_market_regime(self, prices):
        """确定市场状态"""
        # 使用market_analyzer已经实现的函数
        return self.market_analyzer.get_market_regime(prices)
    
    def select_strategy(self, symbol, prices):
        """
        为特定资产选择最优策略
        
        参数:
            symbol: 资产代码
            prices: 价格数据
            
        返回:
            strategy_type: 选择的策略类型
            params: 策略参数调整（如果有）
        """
        # 获取市场状态
        market_regime = self.get_market_regime(prices)
        regime_type = market_regime.get('regime', 'unknown')
        
        # 获取资产特定策略映射，如果没有则使用默认映射
        asset_map = self.asset_strategy_map.get(symbol, self.default_strategy_map)
        
        # 根据市场状态选择策略
        if regime_type == 'volatile' or market_regime.get('volatility', 0) > self.volatility_threshold:
            strategy_type = asset_map.get('volatile', asset_map.get('default'))
        elif regime_type == 'strong_uptrend' or market_regime.get('trend_strength', 0) > self.trend_threshold:
            strategy_type = asset_map.get('trending', asset_map.get('default'))
        elif regime_type == 'range_bound':
            strategy_type = asset_map.get('range_bound', asset_map.get('default'))
        elif regime_type == 'overbought' or regime_type == 'oversold':
            strategy_type = StrategyType.SMART_STOP_LOSS  # 过度买入或卖出状态，使用智能止损
        else:
            strategy_type = asset_map.get('default', StrategyType.SMART_STOP_LOSS)
        
        # 获取策略参数调整
        params = {}
        asset_params = self.asset_params_map.get(symbol, {})
        if strategy_type in asset_params:
            params = asset_params[strategy_type]
        
        return strategy_type, params
    
    def adjust_params_based_on_performance(self, symbol, strategy_type, performance_metric):
        """
        根据表现调整策略参数（简化版）
        
        参数:
        symbol (str): 交易标的
        strategy_type (StrategyType): 策略类型
        performance_metric (float): 性能指标（例如夏普比率或回测收益）
        """
        # 这里可以实现更复杂的参数调整逻辑
        # 当前仅为示例，实际实现可以基于强化学习或其他优化算法
        if strategy_type == StrategyType.SMART_STOP_LOSS:
            current_param = self.asset_params_map.get(symbol, {}).get(strategy_type, {}).get("risk_aversion", 1.2)
            
            # 简单调整：如果表现好则减小风险规避参数，反之增加
            if performance_metric > 0.05:  # 假设5%为好的表现
                new_param = max(0.8, current_param - 0.1)
            elif performance_metric < 0.01:  # 假设1%为差的表现
                new_param = min(2.0, current_param + 0.1)
            else:
                new_param = current_param
                
            # 更新参数
            if symbol not in self.asset_params_map:
                self.asset_params_map[symbol] = {}
            if strategy_type not in self.asset_params_map[symbol]:
                self.asset_params_map[symbol][strategy_type] = {}
            
            self.asset_params_map[symbol][strategy_type]["risk_aversion"] = new_param 