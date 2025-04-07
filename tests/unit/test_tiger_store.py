"""
测试老虎证券数据获取功能
"""
import pytest
from datetime import datetime, timedelta
from src.interface.store.tiger_store import TigerStore

class TestTigerStore:
    @pytest.fixture
    def tiger_store(self):
        """创建TigerStore实例"""
        return TigerStore()
    
    def test_get_historical_data(self, tiger_store):
        """测试获取历史数据"""
        # 准备测试数据
        symbol = 'QQQ'
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # 获取数据
        data = tiger_store.get_historical_data(symbol, start_date, end_date)
        
        # 验证数据
        assert data is not None
        assert len(data) > 0
        assert 'open' in data.columns
        assert 'high' in data.columns
        assert 'low' in data.columns
        assert 'close' in data.columns
        assert 'volume' in data.columns
        
    def test_get_realtime_quotes(self, tiger_store):
        """测试获取实时行情"""
        # 准备测试数据
        symbol = 'QQQ'
        
        # 获取实时行情
        quote = tiger_store.get_realtime_quotes(symbol)
        
        # 验证数据
        assert quote is not None
        assert 'last_price' in quote
        assert 'bid_price' in quote
        assert 'ask_price' in quote
        assert 'volume' in quote 