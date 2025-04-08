"""
配置管理基类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class Config(ABC):
    """配置基类"""

    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """加载配置"""
        pass

    @abstractmethod
    def save(self, config: Dict[str, Any]) -> bool:
        """保存配置"""
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取配置项"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> bool:
        """设置配置项"""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """验证配置"""
        pass
