from .event_handler import EventHandler

class TradeEventHandler(EventHandler):
    """交易事件处理器"""

    def handle_event(self, event):
        """处理交易事件"""
        if event.type == 'TRADE':
            self.process_event(event)

    def process_event(self, event):
        """处理交易事件的具体逻辑"""
        self._process_trade(event)

    def _process_trade(self, event):
        """处理具体的交易"""
        # 具体的交易处理逻辑
        pass 