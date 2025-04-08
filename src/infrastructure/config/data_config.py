"""
数据配置类
"""
import logging
import os
from typing import Any, Dict, Optional

import yaml

from .base_config import Config


class DataConfig(Config):
    """数据配置类"""

    def __init__(self):
        self.config = {}
        self.logger = logging.getLogger(__name__)

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """加载YAML配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Dict: 配置字典
        """
        self.logger.info(f"加载数据配置: {config_path}")
        try:
            # 如果配置文件不存在，则使用默认配置
            if not os.path.exists(config_path):
                self.logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
                # 设置默认配置
                self.config = {
                    'cache_dir': 'data/cache',
                    'data_source': 'tiger',
                    'use_cache': True,
                    'symbols': ['AAPL', 'MSFT', 'GOOGL'],
                    'interval': '1m',
                    'tiger': {
                        'client_config': 'configs/tiger/tiger_openapi_config.properties'
                    }
                }
                return self.config

            # 读取YAML配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
                self.logger.info(f"成功加载数据配置: {config_path}")
                return self.config
        except Exception as e:
            self.logger.error(f"加载数据配置失败: {str(e)}")
            # 设置默认配置
            self.config = {
                'cache_dir': 'data/cache',
                'data_source': 'tiger',
                'use_cache': True,
                'symbols': ['AAPL', 'MSFT', 'GOOGL'],
                'interval': '1m',
                'tiger': {
                    'client_config': 'configs/tiger/tiger_openapi_config.properties'
                }
            }
            return self.config

    def load(self) -> Dict[str, Any]:
        """加载配置"""
        return self.config

    def save(self, config: Dict[str, Any]) -> bool:
        """保存配置"""
        self.config = config
        return True

    def get(self, key: str, default=None) -> Optional[Any]:
        """获取配置项
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """设置配置项"""
        self.config[key] = value
        return True

    def validate(self) -> bool:
        """验证配置"""
        # 实现配置验证逻辑
        required_keys = ['data_source', 'symbols', 'interval']
        for key in required_keys:
            if key not in self.config:
                self.logger.error(f"缺少必要的配置项: {key}")
                return False
        return True

    def get_params(self) -> Dict[str, Any]:
        """获取所有配置参数
        
        Returns:
            Dict: 配置参数
        """
        return self.config
