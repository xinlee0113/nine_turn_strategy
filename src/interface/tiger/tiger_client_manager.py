import os

from tigeropen.common.consts import Language
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.push.push_client import PushClient
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.trade.trade_client import TradeClient

from src.interface.tiger.tiger_bar_data_manager import TigerBarDataManager


class TigerClientManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(TigerClientManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            config_path, private_key_path = self._get_config_paths()
            # 初始化Tiger API客户端
            self.client_config = TigerOpenClientConfig(sandbox_debug=False, props_path=config_path)
            self.client_config.private_key = read_private_key(private_key_path)
            self.client_config.language = Language.zh_CN
            self.client_config.timeout = 60

            self.quote_client = QuoteClient(self.client_config)
            self.quote_client.grab_quote_permission()

            self.trade_client = TradeClient(self.client_config)

            protocol, host, port = self.client_config.socket_host_port
            self.push_client = PushClient(host, port, use_ssl=(protocol == 'ssl'))

            self.tiger_bar_data_manager = TigerBarDataManager(self.quote_client)

    def _get_config_paths(self) -> tuple[str, str]:
        # 获取项目根目录的绝对路径
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        config_path = os.path.join(base_dir, "configs", "tiger", "tiger_openapi_config.properties")
        private_key_path = os.path.join(base_dir, "configs", "tiger", "private_key.pem")
        return config_path, private_key_path

    def get_bar_data_manager(self) -> TigerBarDataManager:
        return self.tiger_bar_data_manager
