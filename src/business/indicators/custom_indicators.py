from .base_indicator import BaseIndicator

class MovingAverage(BaseIndicator):
    """移动平均线指标"""
    
    def __init__(self, period=20):
        """初始化移动平均线
        
        Args:
            period: 周期
        """
        super().__init__()
        self.period = period
        self.values = []
        self.current_value = 0.0
        
    def next(self, value):
        """计算下一个值
        
        Args:
            value: 新值
        """
        self.values.append(value)
        if len(self.values) > self.period:
            self.values.pop(0)
        self.current_value = sum(self.values) / len(self.values)
        
    def get_value(self):
        """获取当前值"""
        return self.current_value

class RSI(BaseIndicator):
    """相对强弱指标"""
    
    def __init__(self, period=14):
        """初始化RSI指标
        
        Args:
            period: 周期
        """
        super().__init__()
        self.period = period
        self.gains = []
        self.losses = []
        self.current_value = 50.0
        
    def next(self, value):
        """计算下一个值
        
        Args:
            value: 新值
        """
        if len(self.gains) > 0:
            change = value - self.gains[-1]
            if change > 0:
                self.gains.append(change)
                self.losses.append(0)
            else:
                self.gains.append(0)
                self.losses.append(-change)
                
            if len(self.gains) > self.period:
                self.gains.pop(0)
                self.losses.pop(0)
                
            avg_gain = sum(self.gains) / len(self.gains)
            avg_loss = sum(self.losses) / len(self.losses)
            
            if avg_loss == 0:
                self.current_value = 100.0
            else:
                rs = avg_gain / avg_loss
                self.current_value = 100 - (100 / (1 + rs))
        else:
            self.gains.append(value)
            self.losses.append(0)
        
    def get_value(self):
        """获取当前值"""
        return self.current_value 