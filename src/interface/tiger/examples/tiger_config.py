import os

from tigeropen.common.consts import Language
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.tiger_open_config import TigerOpenClientConfig


def get_client_config() -> TigerOpenClientConfig:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    config_path = os.path.join(base_dir, "configs", "tiger", "tiger_openapi_config.properties")
    private_key_path = os.path.join(base_dir, "configs", "tiger", "private_key.pem")
    """创建默认的Tiger API配置"""
    client_config = TigerOpenClientConfig(sandbox_debug=False, props_path=config_path)
    client_config.private_key = read_private_key(private_key_path)
    client_config.language = Language.zh_CN
    client_config.timeout = 60
    return client_config
