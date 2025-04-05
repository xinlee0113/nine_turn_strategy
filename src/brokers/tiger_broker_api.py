from setuptools.command.setopt import config_file
from tigeropen.common.consts import Language
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.push.push_client import PushClient
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.trade.domain.profile import AccountProfile
from tigeropen.trade.trade_client import TradeClient


class TigerBrokerAPI:
    def __init__(self):
        print('init')
        config_path = 'config'
        private_key_path='config/private_key.pem'
        tiger_client_config = TigerOpenClientConfig(sandbox_debug=False, props_path=config_path)
        tiger_client_config.private_key = read_private_key(private_key_path)
        tiger_client_config.language = Language.zh_CN
        tiger_client_config.timeout = 60

        self.quote_client = QuoteClient(tiger_client_config)
        self.trade_client = TradeClient(tiger_client_config)

        protocol, host, port = tiger_client_config.socket_host_port
        self.push_client = PushClient(host, port, use_ssl=(protocol == 'ssl'))

    def get_pager_account(self):
        accounts:AccountProfile = self.trade_client.get_managed_accounts()

        return