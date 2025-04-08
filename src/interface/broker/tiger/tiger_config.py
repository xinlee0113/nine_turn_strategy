from dataclasses import dataclass


@dataclass
class TigerConfig:
    """老虎证券配置"""

    # API配置
    api_key: str
    api_secret: str
    api_endpoint: str

    # 交易配置
    account_id: str
    currency: str = "USD"
    market: str = "US"

    # 连接配置
    timeout: int = 30
    retry_times: int = 3
    retry_interval: int = 1
