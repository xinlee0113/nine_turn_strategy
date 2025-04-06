from typing import Dict, Any
import os
from pathlib import Path
import yaml

class IBConfig:
    """Interactive Brokers配置管理类"""
    
    def __init__(self, config_path: str = None):
        """
        初始化配置
        
        Args:
            config_path: 配置文件路径，默认为None表示使用默认路径
        """
        self.config_path = config_path or os.path.join(
            Path.home(), '.ib', 'config.yaml'
        )
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            return self._get_default_config()
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'host': '127.0.0.1',
            'port': 7497,
            'client_id': 1,
            'timeout': 30,
            'retry_times': 3,
            'retry_interval': 1,
            'account': '',
            'currency': 'USD',
            'order_type': 'LMT',
            'time_in_force': 'DAY',
            'use_rth': True,
            'max_position_size': 1000,
            'max_order_value': 100000,
            'max_daily_loss': 0.05,
            'log_level': 'INFO',
            'log_file': 'logs/ib/trading.log'
        }
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """保存配置到文件"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config, f)
        self.config = config
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self.config.copy()
    
    def update_config(self, **kwargs) -> None:
        """更新配置"""
        self.config.update(kwargs)
        self.save_config(self.config) 