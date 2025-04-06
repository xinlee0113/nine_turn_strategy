from typing import Dict, List, Callable

class EventManager:
    """事件管理器"""
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        
    def register_event(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        
    def unregister_event(self, event_type: str, handler: Callable):
        """注销事件处理器"""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
            
    def trigger_event(self, event_type: str, *args, **kwargs):
        """触发事件"""
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                handler(*args, **kwargs)
                
    def _process_event(self, event_type: str, *args, **kwargs):
        """处理事件"""
        self.trigger_event(event_type, *args, **kwargs) 