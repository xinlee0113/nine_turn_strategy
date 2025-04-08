"""
分析器基类
定义分析器接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAnalyzer(ABC):
    """基础分析器基类"""

    @abstractmethod
    def initialize(self):
        """初始化分析器"""
        pass

    @abstractmethod
    def update(self, timestamp, strategy, broker):
        """更新分析数据
        
        Args:
            timestamp: 当前时间戳
            strategy: 策略实例
            broker: 经纪商实例
        """
        pass

    @abstractmethod
    def next(self):
        """处理下一个数据点（为兼容旧版本保留）"""
        pass

    @abstractmethod
    def get_analysis(self):
        """获取分析结果"""
        pass

    @abstractmethod
    def get_results(self) -> Dict[str, Any]:
        """获取最终分析结果"""
        pass
