import unittest
from src.live.engine import LiveEngine
from src.brokers.tiger import TigerClient, TigerConfig
from src.strategies.magic_nine.base import MagicNineStrategy
import pandas as pd

class TestLiveEngine(unittest.TestCase):
    """测试实盘引擎"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建测试配置
        self.config = TigerConfig()
        self.config.update_config(
            api_key='test_key',
            api_secret='test_secret',
            account='test_account'
        )
        
        # 创建测试客户端
        self.client = TigerClient(self.config)
        
        # 创建测试策略
        self.strategy = MagicNineStrategy()
        
        # 创建实盘引擎
        self.engine = LiveEngine(
            strategy=self.strategy,
            client=self.client,
            symbols=['AAPL', 'GOOGL'],
            initial_capital=100000
        )
    
    def test_live_engine(self):
        """测试实盘引擎"""
        # 测试初始化
        self.assertIsNotNone(self.engine.strategy)
        self.assertIsNotNone(self.engine.client)
        self.assertGreater(len(self.engine.symbols), 0)
        self.assertGreater(self.engine.initial_capital, 0)
        
        # 测试启动
        self.engine.start()
        self.assertTrue(self.engine.is_running)
        
        # 测试停止
        self.engine.stop()
        self.assertFalse(self.engine.is_running)
    
    def test_order_management(self):
        """测试订单管理"""
        # 测试下单
        order = self.engine.place_order(
            symbol='AAPL',
            side='BUY',
            quantity=100
        )
        self.assertIsNotNone(order)
        self.assertIn('order_id', order)
        
        # 测试撤单
        result = self.engine.cancel_order(order['order_id'])
        self.assertTrue(result['success'])
    
    def test_position_management(self):
        """测试仓位管理"""
        # 测试获取持仓
        positions = self.engine.get_positions()
        self.assertIsInstance(positions, list)
        
        # 测试获取账户信息
        account_info = self.engine.get_account_info()
        self.assertIsInstance(account_info, dict)
        self.assertIn('equity', account_info)
        self.assertIn('cash', account_info)
    
    def test_market_data(self):
        """测试市场数据"""
        # 测试获取实时行情
        quotes = self.engine.get_quotes(['AAPL', 'GOOGL'])
        self.assertIsInstance(quotes, dict)
        self.assertIn('AAPL', quotes)
        self.assertIn('GOOGL', quotes)
        
        # 测试获取历史数据
        history = self.engine.get_history('AAPL', '2023-01-01', '2023-12-31')
        self.assertIsInstance(history, pd.DataFrame)
        self.assertGreater(len(history), 0)

if __name__ == '__main__':
    unittest.main() 