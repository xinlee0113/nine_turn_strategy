from abc import ABC, abstractmethod

class EventHandler(ABC):
    """事件处理器基类"""

    @abstractmethod
    def handle_event(self, event):
        """处理事件"""
        pass

    @abstractmethod
    def process_event(self, event):
        """处理事件的具体逻辑"""
        pass 