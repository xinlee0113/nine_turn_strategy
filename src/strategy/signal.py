from typing import Dict, Any
import pandas as pd
import numpy as np

class SignalGenerator:
    """信号生成器"""
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化信号生成器
        
        Args:
            params: 参数配置
        """
        self.params = params or {}
    
    def generate_buy_signal(self, data: pd.DataFrame) -> pd.Series:
        """
        生成买入信号
        
        Args:
            data: 市场数据
            
        Returns:
            买入信号序列
        """
        raise NotImplementedError
    
    def generate_sell_signal(self, data: pd.DataFrame) -> pd.Series:
        """
        生成卖出信号
        
        Args:
            data: 市场数据
            
        Returns:
            卖出信号序列
        """
        raise NotImplementedError
    
    def generate_hold_signal(self, data: pd.DataFrame) -> pd.Series:
        """
        生成持仓信号
        
        Args:
            data: 市场数据
            
        Returns:
            持仓信号序列
        """
        raise NotImplementedError

class MagicNineSignal(SignalGenerator):
    """神奇九转信号生成器"""
    
    def generate(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成神奇九转信号"""
        df = data.copy()
        
        # 计算九转序列
        df['high_sequence'] = self._calculate_sequence(df['high'])
        df['low_sequence'] = self._calculate_sequence(df['low'])
        
        # 生成信号
        df['signal'] = 0
        df.loc[df['high_sequence'] == self.params['period'], 'signal'] = -1  # 卖出信号
        df.loc[df['low_sequence'] == self.params['period'], 'signal'] = 1    # 买入信号
        
        return df
        
    def _calculate_sequence(self, series: pd.Series) -> pd.Series:
        """计算九转序列"""
        sequence = pd.Series(0, index=series.index)
        for i in range(1, len(series)):
            if series[i] > series[i-1]:
                sequence[i] = sequence[i-1] + 1 if sequence[i-1] > 0 else 1
            elif series[i] < series[i-1]:
                sequence[i] = sequence[i-1] - 1 if sequence[i-1] < 0 else -1
        return sequence 