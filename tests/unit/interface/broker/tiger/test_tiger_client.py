import pytest
from datetime import datetime, timedelta
import pandas as pd
from src.interface.broker.tiger.tiger_client import TigerClient
from src.interface.broker.tiger.tiger_config import TigerConfig

class TestTigerClient:
    @pytest.fixture
    def client(self):
        config = TigerConfig()
        return TigerClient(config)

    def test_client_initialization(self, client):
        """测试客户端初始化"""
        assert client is not None
        assert client.config is not None
        assert client._api_client is not None

    def test_get_historical_data(self, client):
        """测试获取历史数据"""
        symbol = "AAPL"
        start_date = datetime.now() - timedelta(days=5)
        end_date = datetime.now()
        interval = "1m"

        data = client.get_historical_data(symbol, start_date, end_date, interval)
        
        assert isinstance(data, pd.DataFrame)
        assert not data.empty
        assert all(col in data.columns for col in ['open', 'high', 'low', 'close', 'volume'])
        assert isinstance(data.index, pd.DatetimeIndex)

    def test_get_historical_data_with_cache(self, client):
        """测试带缓存的历史数据获取"""
        symbol = "AAPL"
        start_date = datetime.now() - timedelta(days=5)
        end_date = datetime.now()
        interval = "1m"

        # 第一次获取数据
        data1 = client.get_historical_data(symbol, start_date, end_date, interval)
        
        # 第二次获取相同数据
        data2 = client.get_historical_data(symbol, start_date, end_date, interval)
        
        # 验证两次获取的数据相同
        pd.testing.assert_frame_equal(data1, data2)

    def test_get_historical_data_segmentation(self, client):
        """测试数据分段获取"""
        symbol = "AAPL"
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        interval = "1m"

        data = client.get_historical_data(symbol, start_date, end_date, interval)
        
        # 验证数据完整性
        assert len(data) > 0
        assert data.index.min() <= pd.Timestamp(start_date)
        assert data.index.max() >= pd.Timestamp(end_date)

    def test_get_historical_data_error_handling(self, client):
        """测试错误处理"""
        symbol = "INVALID_SYMBOL"
        start_date = datetime.now() - timedelta(days=5)
        end_date = datetime.now()
        interval = "1m"

        with pytest.raises(Exception):
            client.get_historical_data(symbol, start_date, end_date, interval)

    def test_get_realtime_quotes(self, client):
        """测试获取实时行情"""
        symbols = ["AAPL", "GOOGL"]
        
        quotes = client.get_realtime_quotes(symbols)
        
        assert isinstance(quotes, dict)
        assert all(symbol in quotes for symbol in symbols)
        assert all(isinstance(quote, dict) for quote in quotes.values())

    def test_get_account_info(self, client):
        """测试获取账户信息"""
        account_info = client.get_account_info()
        
        assert isinstance(account_info, dict)
        assert 'account_id' in account_info
        assert 'currency' in account_info
        assert 'balance' in account_info

    def test_place_order(self, client):
        """测试下单"""
        symbol = "AAPL"
        quantity = 1
        order_type = "LMT"
        price = 150.0
        side = "BUY"
        
        order_id = client.place_order(symbol, quantity, order_type, price, side)
        
        assert isinstance(order_id, str)
        assert len(order_id) > 0

    def test_cancel_order(self, client):
        """测试撤单"""
        symbol = "AAPL"
        quantity = 1
        order_type = "LMT"
        price = 150.0
        side = "BUY"
        
        order_id = client.place_order(symbol, quantity, order_type, price, side)
        result = client.cancel_order(order_id)
        
        assert result is True

    def test_get_order_status(self, client):
        """测试获取订单状态"""
        symbol = "AAPL"
        quantity = 1
        order_type = "LMT"
        price = 150.0
        side = "BUY"
        
        order_id = client.place_order(symbol, quantity, order_type, price, side)
        status = client.get_order_status(order_id)
        
        assert isinstance(status, dict)
        assert 'order_id' in status
        assert 'status' in status
        assert 'filled_quantity' in status 