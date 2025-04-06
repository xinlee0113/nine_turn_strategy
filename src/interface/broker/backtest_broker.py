from .base_broker import BaseBroker

class BacktestBroker(BaseBroker):
    """回测经纪商"""
    
    def __init__(self, initial_capital=1000000):
        """初始化回测经纪商
        
        Args:
            initial_capital: 初始资金
        """
        super().__init__()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}
        self.orders = {}
        self.trades = []
        
    def connect(self):
        """连接经纪商"""
        pass
    
    def disconnect(self):
        """断开连接"""
        pass
    
    def place_order(self, order):
        """下单
        
        Args:
            order: 订单对象
        """
        self.orders[order.order_id] = order
        
    def cancel_order(self, order_id):
        """撤单
        
        Args:
            order_id: 订单ID
        """
        if order_id in self.orders:
            del self.orders[order_id]
    
    def get_position(self, symbol):
        """获取持仓
        
        Args:
            symbol: 交易品种
        """
        return self.positions.get(symbol, 0)
    
    def get_account(self):
        """获取账户信息"""
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'positions': self.positions,
            'orders': self.orders,
            'trades': self.trades
        } 