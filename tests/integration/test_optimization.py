import unittest
import pandas as pd
from src.optimization.optimizer import BaseOptimizer
from src.optimization.grid_search import GridSearchOptimizer
from src.strategies.magic_nine.base import MagicNineStrategy

class TestBaseOptimizer(unittest.TestCase):
    """测试基础优化器"""
    
    def setUp(self):
        """设置测试数据"""
        self.data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
            'high': [105, 106, 107, 108, 109, 110, 111, 112, 113, 114],
            'low': [95, 96, 97, 98, 99, 100, 101, 102, 103, 104],
            'close': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
            'volume': [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
        })
        
        self.optimizer = BaseOptimizer(
            strategy_class=MagicNineStrategy,
            data=self.data,
            initial_capital=100000,
            commission=0.001,
            slippage=0.001
        )
    
    def test_base_optimizer(self):
        """测试基础优化器"""
        # 测试参数评估
        params = {'n': 9, 'threshold': 0.02}
        score = self.optimizer.evaluate(params)
        self.assertIsInstance(score, float)
        self.assertGreater(score, 0)

class TestGridSearchOptimizer(unittest.TestCase):
    """测试网格搜索优化器"""
    
    def setUp(self):
        """设置测试数据"""
        self.data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
            'high': [105, 106, 107, 108, 109, 110, 111, 112, 113, 114],
            'low': [95, 96, 97, 98, 99, 100, 101, 102, 103, 104],
            'close': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
            'volume': [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
        })
        
        self.param_grid = {
            'n': [7, 8, 9, 10],
            'threshold': [0.01, 0.02, 0.03]
        }
        
        self.optimizer = GridSearchOptimizer(
            strategy_class=MagicNineStrategy,
            data=self.data,
            param_grid=self.param_grid,
            initial_capital=100000,
            commission=0.001,
            slippage=0.001
        )
    
    def test_grid_search_optimizer(self):
        """测试网格搜索优化器"""
        # 测试参数优化
        best_params, best_score = self.optimizer.optimize()
        
        # 检查最优参数
        self.assertIsInstance(best_params, dict)
        self.assertIn('n', best_params)
        self.assertIn('threshold', best_params)
        
        # 检查最优分数
        self.assertIsInstance(best_score, float)
        self.assertGreater(best_score, 0)
        
        # 检查结果保存
        self.optimizer.save_results('test_results.pkl')
        
        # 检查结果加载
        loaded_results = self.optimizer.load_results('test_results.pkl')
        self.assertIsInstance(loaded_results, dict)
        self.assertIn('best_params', loaded_results)
        self.assertIn('best_score', loaded_results)

if __name__ == '__main__':
    unittest.main() 