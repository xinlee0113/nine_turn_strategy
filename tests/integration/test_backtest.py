import unittest
import pandas as pd
from src.backtest.engine import BacktestEngine
from src.strategies.magic_nine.base import MagicNineStrategy

class TestBacktestEngine(unittest.TestCase):
    """测试回测引擎"""
    
    def setUp(self):
        """设置测试数据"""
        self.data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
            'high': [105, 106, 107, 108, 109, 110, 111, 112, 113, 114],
            'low': [95, 96, 97, 98, 99, 100, 101, 102, 103, 104],
            'close': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
            'volume': [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
        })
        
        self.engine = BacktestEngine(
            initial_capital=100000,
            commission=0.001,
            slippage=0.001
        )
    
    def test_backtest_engine(self):
        """测试回测引擎"""
        strategy = MagicNineStrategy()
        results = self.engine.run(strategy, self.data)
        
        # 检查回测结果
        self.assertIn('final_equity', results)
        self.assertIn('returns', results)
        self.assertIn('trades', results)
        
        # 检查最终权益
        self.assertGreater(results['final_equity'], 0)
        
        # 检查收益率
        self.assertIsInstance(results['returns'], float)
        
        # 检查交易记录
        self.assertIsInstance(results['trades'], list)
        
        # 检查交易数量
        self.assertGreater(len(results['trades']), 0)

if __name__ == '__main__':
    unittest.main() 