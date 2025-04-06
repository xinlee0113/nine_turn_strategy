from typing import Dict, Any
import pandas as pd
import numpy as np
from src.strategy.base import BaseStrategy

class MagicNineStrategy(BaseStrategy):
    """神奇九转策略"""
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化策略
        
        Args:
            params: 策略参数
        """
        super().__init__(params)
        self.n = params.get('n', 9)  # 九转周期
        self.threshold = params.get('threshold', 0.02)  # 阈值
        self.sma_fast = params.get('sma_fast', 5)  # 快速均线周期
        self.sma_slow = params.get('sma_slow', 20)  # 慢速均线周期
        self.rsi_period = params.get('rsi_period', 14)  # RSI周期
        self.kdj_period = params.get('kdj_period', 9)  # KDJ周期
        self.macd_fast = params.get('macd_fast', 12)  # MACD快线
        self.macd_slow = params.get('macd_slow', 26)  # MACD慢线
        self.macd_signal = params.get('macd_signal', 9)  # MACD信号线
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        生成交易信号
        
        Args:
            data: 市场数据
            
        Returns:
            交易信号序列
        """
        # 计算九转序列
        high_sequence, low_sequence = self._calculate_nine_sequence(data)
        
        # 计算均线
        sma_fast = data['close'].rolling(self.sma_fast).mean()
        sma_slow = data['close'].rolling(self.sma_slow).mean()
        
        # 计算RSI
        rsi = self._calculate_rsi(data)
        
        # 计算KDJ
        k, d, j = self._calculate_kdj(data)
        
        # 计算MACD
        macd, signal, hist = self._calculate_macd(data)
        
        # 生成信号
        signals = pd.Series(0, index=data.index)
        
        # 买入条件：
        # 1. 低九转序列达到9
        # 2. 价格在20日均线上方
        # 3. RSI超卖（<30）
        # 4. KDJ金叉（K从下向上穿过D）
        # 5. MACD金叉（MACD从下向上穿过信号线）
        buy_condition = (
            (low_sequence == self.n) &
            (data['close'] > sma_slow) &
            (rsi < 30) &
            (k > d) & (k.shift(1) <= d.shift(1)) &
            (macd > signal) & (macd.shift(1) <= signal.shift(1))
        )
        
        # 卖出条件：
        # 1. 高九转序列达到9
        # 2. 价格在20日均线下方
        # 3. RSI超买（>70）
        # 4. KDJ死叉（K从上向下穿过D）
        # 5. MACD死叉（MACD从上向下穿过信号线）
        sell_condition = (
            (high_sequence == self.n) &
            (data['close'] < sma_slow) &
            (rsi > 70) &
            (k < d) & (k.shift(1) >= d.shift(1)) &
            (macd < signal) & (macd.shift(1) >= signal.shift(1))
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals
    
    def calculate_position(self, signals: pd.Series, data: pd.DataFrame) -> pd.Series:
        """
        计算仓位大小
        
        Args:
            signals: 交易信号
            data: 市场数据
            
        Returns:
            仓位大小序列
        """
        # 计算波动率
        volatility = data['close'].pct_change().rolling(20).std()
        
        # 计算RSI
        rsi = self._calculate_rsi(data)
        
        # 计算MACD
        macd, signal, hist = self._calculate_macd(data)
        
        # 根据多个指标调整仓位
        position = pd.Series(0, index=signals.index)
        
        # 买入信号
        buy_mask = signals == 1
        position[buy_mask] = (
            1 / (1 + volatility[buy_mask]) *  # 波动率调整
            (1 - abs(rsi[buy_mask] - 50) / 50) *  # RSI调整
            (1 + (macd[buy_mask] - signal[buy_mask]) / signal[buy_mask])  # MACD调整
        )
        
        # 卖出信号
        position[signals == -1] = 0
        
        # 限制仓位在0-1之间
        position = position.clip(0, 1)
        
        return position
    
    def calculate_stop_loss(self, data: pd.DataFrame) -> pd.Series:
        """
        计算止损价格
        
        Args:
            data: 市场数据
            
        Returns:
            止损价格序列
        """
        # 使用ATR计算止损
        atr = self._calculate_atr(data)
        stop_loss = data['close'] - 2 * atr
        return stop_loss
    
    def calculate_take_profit(self, data: pd.DataFrame) -> pd.Series:
        """
        计算止盈价格
        
        Args:
            data: 市场数据
            
        Returns:
            止盈价格序列
        """
        # 使用ATR计算止盈
        atr = self._calculate_atr(data)
        take_profit = data['close'] + 3 * atr
        return take_profit
    
    def _calculate_nine_sequence(self, data: pd.DataFrame) -> tuple:
        """计算九转序列"""
        high_sequence = pd.Series(0, index=data.index)
        low_sequence = pd.Series(0, index=data.index)
        
        for i in range(1, len(data)):
            # 计算高九转
            if data['high'].iloc[i] > data['high'].iloc[i-1]:
                high_sequence.iloc[i] = high_sequence.iloc[i-1] + 1 if high_sequence.iloc[i-1] > 0 else 1
            elif data['high'].iloc[i] < data['high'].iloc[i-1]:
                high_sequence.iloc[i] = high_sequence.iloc[i-1] - 1 if high_sequence.iloc[i-1] < 0 else -1
                
            # 计算低九转
            if data['low'].iloc[i] > data['low'].iloc[i-1]:
                low_sequence.iloc[i] = low_sequence.iloc[i-1] + 1 if low_sequence.iloc[i-1] > 0 else 1
            elif data['low'].iloc[i] < data['low'].iloc[i-1]:
                low_sequence.iloc[i] = low_sequence.iloc[i-1] - 1 if low_sequence.iloc[i-1] < 0 else -1
        
        return high_sequence, low_sequence
    
    def _calculate_rsi(self, data: pd.DataFrame) -> pd.Series:
        """计算RSI指标"""
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_kdj(self, data: pd.DataFrame) -> tuple:
        """计算KDJ指标"""
        low_min = data['low'].rolling(window=self.kdj_period).min()
        high_max = data['high'].rolling(window=self.kdj_period).max()
        
        rsv = (data['close'] - low_min) / (high_max - low_min) * 100
        k = rsv.ewm(alpha=1/3).mean()
        d = k.ewm(alpha=1/3).mean()
        j = 3 * k - 2 * d
        
        return k, d, j
    
    def _calculate_macd(self, data: pd.DataFrame) -> tuple:
        """计算MACD指标"""
        exp1 = data['close'].ewm(span=self.macd_fast, adjust=False).mean()
        exp2 = data['close'].ewm(span=self.macd_slow, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=self.macd_signal, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算ATR指标"""
        high = data['high']
        low = data['low']
        close = data['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        return atr 