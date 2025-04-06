from typing import Dict, Any, Optional
import requests
from .config import TigerConfig

class TigerClient:
    """老虎证券客户端管理类"""
    
    def __init__(self, config: Optional[TigerConfig] = None):
        """
        初始化客户端
        
        Args:
            config: 配置对象，默认为None表示使用默认配置
        """
        self.config = config or TigerConfig()
        self.session = requests.Session()
        self.session.timeout = self.config.get_config()['timeout']
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        config = self.config.get_config()
        return {
            'Content-Type': 'application/json',
            'X-API-KEY': config['api_key'],
            'X-API-SIGN': self._generate_sign()
        }
    
    def _generate_sign(self) -> str:
        """生成签名"""
        # TODO: 实现签名生成逻辑
        return ''
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        发送请求
        
        Args:
            method: 请求方法
            endpoint: API端点
            **kwargs: 请求参数
            
        Returns:
            响应数据
        """
        url = f"{self.config.get_config()['server']}{endpoint}"
        headers = self._get_headers()
        
        for _ in range(self.config.get_config()['retry_times']):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if _ == self.config.get_config()['retry_times'] - 1:
                    raise
                time.sleep(self.config.get_config()['retry_interval'])
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        return self._request('GET', '/account/info')
    
    def get_positions(self) -> Dict[str, Any]:
        """获取持仓信息"""
        return self._request('GET', '/position/list')
    
    def place_order(self, symbol: str, side: str, quantity: int, 
                   price: Optional[float] = None) -> Dict[str, Any]:
        """
        下单
        
        Args:
            symbol: 交易标的
            side: 交易方向（BUY/SELL）
            quantity: 数量
            price: 价格，None表示市价单
            
        Returns:
            订单信息
        """
        data = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity
        }
        if price is not None:
            data['price'] = price
            
        return self._request('POST', '/order/place', json=data)
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        撤单
        
        Args:
            order_id: 订单ID
            
        Returns:
            撤单结果
        """
        return self._request('POST', f'/order/cancel/{order_id}')
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        获取订单状态
        
        Args:
            order_id: 订单ID
            
        Returns:
            订单状态
        """
        return self._request('GET', f'/order/status/{order_id}') 