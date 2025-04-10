import json
import os

class ConfigManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConfigManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            # 初始化配置管理器的其他属性
            self.load_config()

    def load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), '../../configs/data/data_config.json')
        with open(config_path, 'r') as file:
            self.config = json.load(file)

# 使用示例
config_manager = ConfigManager()
# 现在可以访问或设置配置管理器的属性
# 例如：config_manager.config['some_key']