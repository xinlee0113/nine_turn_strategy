from .event_handler import EventHandler


class DataEventHandler(EventHandler):
    """数据事件处理器"""

    def handle_event(self, event):
        """处理数据事件"""
        if event.type == 'DATA':
            self.process_event(event)

    def process_event(self, event):
        """处理数据事件的具体逻辑"""
        self._process_data(event)

    def _process_data(self, event):
        """处理具体的数据"""
        # 具体的数据处理逻辑
        pass
