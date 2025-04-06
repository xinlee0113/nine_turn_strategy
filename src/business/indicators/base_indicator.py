from abc import ABC, abstractmethod

class BaseIndicator(ABC):
    """基础指标类"""
    
    @abstractmethod
    def __init__(self):
        """初始化指标"""
        pass
    
    @abstractmethod
    def next(self):
        """计算下一个值"""
        pass
    
    @abstractmethod
    def get_value(self):
        """获取当前值"""
        pass 