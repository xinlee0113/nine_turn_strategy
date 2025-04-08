"""
引擎基类
定义引擎接口
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseEngine(ABC):
    """引擎基类
    
    所有的引擎（回测、优化、实盘）都应该继承自这个基类
    """

    def __init__(self, config=None):
        """
        初始化引擎
        
        Args:
            config: 引擎配置
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.strategy = None
        self.data = None
        self.broker = None
        self.results = {}
        self.analyzers = []

    @abstractmethod
    def set_strategy(self, strategy) -> None:
        """设置策略
        
        Args:
            strategy: 策略实例
        """
        pass

    @abstractmethod
    def set_data(self, data) -> None:
        """设置数据源
        
        Args:
            data: 数据源
        """
        pass

    @abstractmethod
    def set_broker(self, broker) -> None:
        """设置经纪商
        
        Args:
            broker: 经纪商实例
        """
        pass

    @abstractmethod
    def add_analyzer(self, analyzer) -> None:
        """添加分析器
        
        Args:
            analyzer: 分析器实例
        """
        pass

    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """运行引擎
        
        Returns:
            Dict: 运行结果
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """停止引擎"""
        pass
