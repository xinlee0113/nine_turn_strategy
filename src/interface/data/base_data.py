from abc import ABC, abstractmethod


class BaseData(ABC):
    """数据接口基类"""

    @abstractmethod
    def start(self):
        """启动数据源"""
        pass

    @abstractmethod
    def stop(self):
        """停止数据源"""
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
