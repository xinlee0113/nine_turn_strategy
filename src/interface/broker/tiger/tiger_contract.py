from dataclasses import dataclass
from enum import Enum


class ContractType(Enum):
    """合约类型"""
    STOCK = "STOCK"
    OPTION = "OPTION"
    FUTURE = "FUTURE"
    FOREX = "FOREX"


@dataclass
class TigerContract:
    """老虎证券合约"""

    # 合约基本信息
    symbol: str
    contract_type: ContractType
    exchange: str
    currency: str

    # 合约规格
    multiplier: float = 1.0
    min_tick: float = 0.01
    lot_size: int = 100

    # 交易时间
    trading_hours: str = "09:30-16:00"
    timezone: str = "America/New_York"
