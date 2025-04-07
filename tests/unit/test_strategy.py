import unittest
import pandas as pd
from src.strategy.base import BaseStrategy
from src.strategies.magic_nine.base import MagicNineStrategy

class TestBaseStrategy(unittest.TestCase):
    """测试基础策略类"""
    
    def setUp(self):
        """设置测试数据"""
        self.data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [95, 96, 97, 98, 99],
            'close': [101, 102, 103, 104, 105],
            'volume': [1000, 2000, 3000, 4000, 5000]
        })
    
    def test_base_strategy(self):
        """测试基础策略"""
        strategy = BaseStrategy()
        signals = strategy.generate_signals(self.data)
        self.assertIsInstance(signals, pd.Series)
        self.assertEqual(len(signals), len(self.data))

class TestMagicNineStrategy(unittest.TestCase):
    """测试神奇九转策略"""
    
    def setUp(self):
        """设置测试数据"""
        self.data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
            'high': [105, 106, 107, 108, 109, 110, 111, 112, 113, 114],
            'low': [95, 96, 97, 98, 99, 100, 101, 102, 103, 104],
            'close': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
            'volume': [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
        })
    
    def test_magic_nine_strategy(self):
        """测试神奇九转策略"""
        strategy = MagicNineStrategy()
        signals = strategy.generate_signals(self.data)
        self.assertIsInstance(signals, pd.Series)
        self.assertEqual(len(signals), len(self.data))
        
        # 测试信号生成
        self.assertIn(1, signals.unique())  # 买入信号
        self.assertIn(-1, signals.unique())  # 卖出信号
        self.assertIn(0, signals.unique())  # 无信号

if __name__ == '__main__':
    unittest.main() 