"""
符号参数配置类
负责加载和管理股票符号的参数配置
"""
import json
import logging
import os
from typing import Dict, Any, Optional

from .base_config import Config


class SymbolConfig(Config):
    """股票符号参数配置类"""

    def __init__(self):
        self.config = {}
        self.logger = logging.getLogger(__name__)

    def load_config(self, config_path: str = "configs/strategy/magic_nine.json") -> Dict[str, Any]:
        """加载JSON配置文件
        
        Args:
            config_path: 配置文件路径，默认为configs/strategy/magic_nine.json
            
        Returns:
            Dict: 配置字典
        """
        self.logger.info(f"加载符号参数配置: {config_path}")
        try:
            if not os.path.exists(config_path):
                self.logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
                # 设置默认配置
                self.config = self.get_default_config()
                return self.config

            # 读取JSON配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                self.logger.info(f"成功加载符号参数配置: {config_path}")
                return self.config
        except Exception as e:
            self.logger.error(f"加载符号参数配置失败: {str(e)}")
            # 设置默认配置
            self.config = self.get_default_config()
            return self.config

    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置
        
        Returns:
            Dict: 默认配置字典
        """
        return {
            "default": {
                "magic_period": 3,
                "magic_count": 5,
                "rsi_period": 14,
                "rsi_oversold": 30,
                "rsi_overbought": 70,
                "kdj_oversold": 20,
                "kdj_overbought": 80,
                "atr_period": 14,
                "atr_multiplier": 2.5,
                "max_loss_pct": 3.0,
                "min_profit_pct": 1.0,
                "enable_short": True,
                "short_atr_multiplier": 2.0
            }
        }

    def get_symbol_params(self, symbol: str) -> Dict[str, Any]:
        """获取指定股票符号的参数
        如果符号不存在，则使用默认参数
        
        Args:
            symbol: 股票符号
            
        Returns:
            Dict: 股票符号参数字典
        """
        # 如果符号存在于配置中，返回其参数
        if symbol in self.config:
            return self.config[symbol]
        # 否则返回默认参数
        return self.config.get("default", self.get_default_config()["default"])

    def load(self) -> Dict[str, Any]:
        """加载配置"""
        return self.config

    def save(self, config_path: str = "configs/strategy/magic_nine.json") -> bool:
        """保存配置到文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            # 写入JSON配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)

            self.logger.info(f"已保存配置到 {config_path}")
            return True
        except Exception as e:
            self.logger.error(f"保存配置失败: {str(e)}")
            return False

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
        # 确保至少有default配置
        if "default" not in self.config:
            self.logger.error("缺少默认配置项")
            return False
        return True

    def get_params(self) -> Dict[str, Any]:
        """获取所有配置参数
        
        Returns:
            Dict: 配置参数
        """
        return self.config
