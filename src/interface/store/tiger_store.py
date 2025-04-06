from .base_store import BaseStore

class TigerStore(BaseStore):
    """Tiger存储接口"""
    
    def __init__(self):
        self.connected = False
        
    def start(self):
        """启动存储服务"""
        self._connect_api()
        self.connected = True
    
    def stop(self):
        """停止存储服务"""
        self.connected = False
    
    def get_data(self):
        """获取数据"""
        return self.get_historical_data()
    
    def get_realtime_quotes(self):
        """获取实时行情"""
        if not self.connected:
            raise ConnectionError("存储服务未连接")
        # 实现实时行情获取逻辑
        pass
    
    def get_historical_data(self):
        """获取历史数据"""
        if not self.connected:
            raise ConnectionError("存储服务未连接")
        # 实现历史数据获取逻辑
        pass
    
    def _connect_api(self):
        """连接API"""
        # 实现API连接逻辑
        pass
    
    def _handle_response(self):
        """处理响应"""
        # 实现响应处理逻辑
        pass 