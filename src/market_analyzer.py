import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import talib
from sklearn.linear_model import LinearRegression

class MarketAnalyzer:
    """
    市场分析器：分析市场状态、波动性和趋势，为策略选择提供依据
    """
    
    def __init__(self, lookback_window=20, vix_threshold=20, rsi_threshold=70):
        """
        初始化市场分析器
        
        参数:
            lookback_window: 分析回看窗口大小
            vix_threshold: VIX（波动率指数）阈值，超过此值视为高波动
            rsi_threshold: RSI阈值，超过此值视为超买，低于(100-rsi_threshold)视为超卖
        """
        self.lookback_window = lookback_window
        self.vix_threshold = vix_threshold
        self.rsi_threshold = rsi_threshold
    
    def calculate_atr(self, high, low, close, period=14):
        """计算平均真实范围(ATR)"""
        if len(close) < period:
            return None
        return talib.ATR(high, low, close, timeperiod=period)[-1]
    
    def calculate_rsi(self, prices, period=14):
        """计算相对强弱指数(RSI)"""
        if len(prices) < period + 1:
            return 50  # 数据不足时返回中性值
        rsi = talib.RSI(prices, timeperiod=period)
        return rsi[-1]
    
    def calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """计算布林带"""
        if len(prices) < period:
            return (prices[-1], prices[-1], prices[-1], 0)  # 数据不足时返回默认值
        
        upper, middle, lower = talib.BBANDS(
            prices, 
            timeperiod=period, 
            nbdevup=std_dev, 
            nbdevdn=std_dev, 
            matype=0
        )
        
        # 计算带宽
        bandwidth = (upper[-1] - lower[-1]) / middle[-1] * 100
        
        return (upper[-1], middle[-1], lower[-1], bandwidth)
    
    def calculate_macd(self, prices, fastperiod=12, slowperiod=26, signalperiod=9):
        """计算MACD"""
        if len(prices) < slowperiod + signalperiod:
            return (0, 0, 0)  # 数据不足时返回默认值
        
        macd, signal, hist = talib.MACD(
            prices, 
            fastperiod=fastperiod, 
            slowperiod=slowperiod, 
            signalperiod=signalperiod
        )
        
        return (macd[-1], signal[-1], hist[-1])
    
    def calculate_volatility(self, prices, period=20):
        """计算波动率"""
        if len(prices) < period + 1:
            return 0
        
        returns = np.diff(prices) / prices[:-1]
        return np.std(returns[-period:]) * np.sqrt(252)  # 年化波动率
    
    def calculate_trend_strength(self, prices, period=20):
        """计算趋势强度（使用线性回归的R平方值）"""
        if len(prices) < period:
            return 0
            
        x = np.arange(period).reshape(-1, 1)
        y = prices[-period:].reshape(-1, 1)
        
        model = LinearRegression()
        model.fit(x, y)
        
        y_pred = model.predict(x)
        ss_total = np.sum((y - y.mean()) ** 2)
        ss_residual = np.sum((y - y_pred) ** 2)
        
        if ss_total == 0:
            return 0
            
        r_squared = 1 - (ss_residual / ss_total)
        # 确保r_squared是标量
        if hasattr(r_squared, 'shape') and r_squared.shape:
            r_squared = r_squared.item()
        return r_squared
    
    def get_market_regime(self, prices):
        """
        确定当前的市场状态
        
        参数:
            prices: 价格数据序列
            
        返回:
            dict: 包含市场状态和置信度的字典
        """
        if len(prices) < self.lookback_window:
            return {"regime": "normal", "confidence": 0.5}
        
        # 计算各种指标
        volatility = self.calculate_volatility(prices)
        trend_strength = self.calculate_trend_strength(prices)
        
        # 计算RSI判断超买超卖
        rsi = self.calculate_rsi(prices)
        
        # 计算布林带判断波动性
        _, _, _, bb_width = self.calculate_bollinger_bands(prices)
        
        # 计算MACD判断趋势
        macd_val, macd_signal, macd_hist = self.calculate_macd(prices)
        
        # 判断市场状态
        if trend_strength > 0.7 and macd_val > macd_signal and macd_hist > 0:
            regime = "strong_uptrend"
            confidence = min(0.5 + trend_strength / 2, 0.95)
        elif trend_strength > 0.7 and macd_val < macd_signal and macd_hist < 0:
            regime = "strong_downtrend"
            confidence = min(0.5 + trend_strength / 2, 0.95)
        elif volatility > self.vix_threshold/100 or bb_width > 5:
            regime = "volatile"
            confidence = min(0.5 + volatility * 5, 0.95)
        elif trend_strength < 0.3 and bb_width < 3:
            regime = "range_bound"
            confidence = min(0.7 - trend_strength, 0.9)
        elif rsi > self.rsi_threshold:
            regime = "overbought"
            confidence = min(0.5 + (rsi - self.rsi_threshold) / 30, 0.95)
        elif rsi < (100 - self.rsi_threshold):
            regime = "oversold"
            confidence = min(0.5 + ((100 - self.rsi_threshold) - rsi) / 30, 0.95)
        else:
            regime = "normal"
            confidence = 0.6
        
        # 返回市场状态和相关指标
        return {
            "regime": regime,
            "confidence": confidence,
            "volatility": volatility,
            "trend_strength": trend_strength,
            "rsi": rsi,
            "bb_width": bb_width,
            "macd": macd_val,
            "macd_signal": macd_signal,
            "macd_hist": macd_hist
        }
    
    def map_regime_to_strategy(self, market_regime, confidence_threshold=0.6):
        """
        将市场状态映射到推荐的策略类型
        
        参数:
            market_regime: 市场状态字典
            confidence_threshold: 置信度阈值，超过此值才使用推荐的策略
            
        返回:
            str: 推荐的策略类型
        """
        from .strategy_selector import StrategyType
        
        regime = market_regime.get("regime", "normal")
        confidence = market_regime.get("confidence", 0)
        
        if confidence < confidence_threshold:
            return None  # 置信度不足，不做推荐
        
        # 根据市场状态推荐策略
        if regime == "strong_uptrend" or regime == "strong_downtrend":
            return StrategyType.ORIGINAL  # 强趋势市场使用原始策略
        elif regime == "volatile":
            return StrategyType.SMART_STOP_LOSS  # 波动市场使用智能止损
        elif regime == "range_bound":
            return StrategyType.ADVANCED_STOP_LOSS  # 震荡市场使用高级止损
        elif regime == "overbought" or regime == "oversold":
            return StrategyType.SMART_STOP_LOSS  # 超买超卖使用智能止损
        else:
            return None  # 正常市场不做特别推荐
    
    def recommend_strategy_params(self, market_regime, strategy_type):
        """
        根据市场状态推荐策略参数
        
        参数:
            market_regime: 市场状态字典
            strategy_type: 策略类型
            
        返回:
            dict: 推荐的策略参数
        """
        from .strategy_selector import StrategyType
        
        regime = market_regime.get("regime", "normal")
        volatility = market_regime.get("volatility", 0)
        trend_strength = market_regime.get("trend_strength", 0)
        
        params = {}
        
        if strategy_type == StrategyType.SMART_STOP_LOSS:
            # 智能止损策略参数调整
            if regime == "volatile":
                # 高波动市场，增加风险规避系数
                params["risk_aversion"] = min(1.8, 1.0 + volatility * 10)
            elif regime == "strong_uptrend":
                # 强上升趋势，减小风险规避系数
                params["risk_aversion"] = max(0.8, 1.0 - trend_strength / 2)
            elif regime == "overbought":
                # 超买状态，增加风险规避系数
                params["risk_aversion"] = 1.5
        
        elif strategy_type == StrategyType.ADVANCED_STOP_LOSS:
            # 高级止损策略参数调整
            if regime == "volatile":
                # 高波动市场，增加ATR乘数
                params["atr_multiplier"] = min(3.0, 2.5 + volatility * 5)
            elif regime == "range_bound":
                # 震荡市场，减小ATR乘数
                params["atr_multiplier"] = min(2.2, 2.0 + volatility * 5)
        
        return params 