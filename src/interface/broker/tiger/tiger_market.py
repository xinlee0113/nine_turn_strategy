from typing import List, Optional

from .tiger_contract import TigerContract
from .tiger_data import BarData, TickData


class TigerMarket:
    """老虎证券市场"""

    def __init__(self):
        """初始化市场"""
        self.contracts = {}
        self.bars = {}
        self.ticks = {}

    def add_contract(self, contract: TigerContract):
        """添加合约
        
        Args:
            contract: 合约对象
        """
        self.contracts[contract.symbol] = contract

    def get_contract(self, symbol: str) -> Optional[TigerContract]:
        """获取合约
        
        Args:
            symbol: 交易品种
        """
        return self.contracts.get(symbol)

    def update_bar(self, bar: BarData):
        """更新K线数据
        
        Args:
            bar: K线数据
        """
        if bar.symbol not in self.bars:
            self.bars[bar.symbol] = []
        self.bars[bar.symbol].append(bar)

    def get_bars(self, symbol: str, count: int = 1) -> List[BarData]:
        """获取K线数据
        
        Args:
            symbol: 交易品种
            count: 数量
        """
        if symbol not in self.bars:
            return []
        return self.bars[symbol][-count:]

    def update_tick(self, tick: TickData):
        """更新Tick数据
        
        Args:
            tick: Tick数据
        """
        self.ticks[tick.symbol] = tick

    def get_tick(self, symbol: str) -> Optional[TickData]:
        """获取Tick数据
        
        Args:
            symbol: 交易品种
        """
        return self.ticks.get(symbol)
