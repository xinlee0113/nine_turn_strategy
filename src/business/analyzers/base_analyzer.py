from abc import ABC, abstractmethod

class BaseAnalyzer(ABC):
    """基础分析器基类"""
    
    @abstractmethod
    def __init__(self):
        """初始化分析器"""
        pass
    
    @abstractmethod
    def next(self):
        """处理下一个数据点"""
        pass
    
    @abstractmethod
    def get_analysis(self):
        """获取分析结果"""
        pass 