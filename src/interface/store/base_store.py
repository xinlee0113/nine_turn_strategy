from abc import ABC, abstractmethod

class BaseStore(ABC):
    """存储接口基类"""
    
    @abstractmethod
    def start(self):
        """启动存储服务"""
        pass
    
    @abstractmethod
    def stop(self):
        """停止存储服务"""
        pass
    
    @abstractmethod
    def get_data(self):
        """获取数据"""
        pass
    
    @abstractmethod
    def get_realtime_quotes(self):
        """获取实时行情"""
        pass
    
    @abstractmethod
    def get_historical_data(self):
        """获取历史数据"""
        pass 