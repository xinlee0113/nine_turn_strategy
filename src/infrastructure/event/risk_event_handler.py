from .event_handler import EventHandler


class RiskEventHandler(EventHandler):
    """风险事件处理器"""

    def handle_event(self, event):
        """处理风险事件"""
        if event.type == 'RISK':
            self.process_event(event)

    def process_event(self, event):
        """处理风险事件的具体逻辑"""
        self._process_risk(event)

    def _process_risk(self, event):
        """处理具体的风险"""
        # 具体的风险处理逻辑
        pass
