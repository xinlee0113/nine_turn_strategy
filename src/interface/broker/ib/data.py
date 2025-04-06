from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime, timedelta
from ibapi.contract import Contract
from src.brokers.ib.client import IBClientManager
from src.brokers.ib.contract import IBContractManager

class IBData:
    """Interactive Brokers数据获取类"""
    
    def __init__(self, client: IBClientManager, contract_manager: IBContractManager):
        """
        初始化数据获取
        
        Args:
            client: IB客户端
            contract_manager: 合约管理
        """
        self.client = client
        self.contract_manager = contract_manager
        self.data_cache = {}
    
    def get_historical_data(self, symbol: str, start_date: str, 
                          end_date: str, bar_size: str = '1d') -> pd.DataFrame:
        """
        获取历史数据
        
        Args:
            symbol: 交易标的
            start_date: 开始日期
            end_date: 结束日期
            bar_size: K线周期
            
        Returns:
            历史数据
        """
        contract = self.contract_manager._create_contract(symbol)
        data = self.client.get_historical_data(
            contract,
            end_date,
            f'{self._calculate_duration(start_date, end_date)} D',
            bar_size
        )
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        return df
    
    def get_realtime_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        获取实时行情
        
        Args:
            symbols: 交易标的列表
            
        Returns:
            实时行情
        """
        quotes = {}
        for symbol in symbols:
            contract = self.contract_manager._create_contract(symbol)
            quotes[symbol] = self.client.get_market_data(contract)
        
        return quotes
    
    def get_orderbook(self, symbol: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取订单簿
        
        Args:
            symbol: 交易标的
            
        Returns:
            订单簿
        """
        contract = self.contract_manager._create_contract(symbol)
        return self.client.get_orderbook(contract)
    
    def get_trades(self, symbol: str) -> List[Dict[str, Any]]:
        """
        获取成交记录
        
        Args:
            symbol: 交易标的
            
        Returns:
            成交记录
        """
        contract = self.contract_manager._create_contract(symbol)
        return self.client.get_trades(contract)
    
    def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """
        获取基本面数据
        
        Args:
            symbol: 交易标的
            
        Returns:
            基本面数据
        """
        contract = self.contract_manager._create_contract(symbol)
        return self.client.get_fundamentals(contract)
    
    def get_company_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取公司信息
        
        Args:
            symbol: 交易标的
            
        Returns:
            公司信息
        """
        contract = self.contract_manager._create_contract(symbol)
        return self.client.get_company_info(contract)
    
    def get_news(self, symbol: str) -> List[Dict[str, Any]]:
        """
        获取新闻
        
        Args:
            symbol: 交易标的
            
        Returns:
            新闻列表
        """
        contract = self.contract_manager._create_contract(symbol)
        return self.client.get_news(contract)
    
    def _calculate_duration(self, start_date: str, end_date: str) -> int:
        """计算日期差"""
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        return (end - start).days 