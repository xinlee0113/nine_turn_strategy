"""
分析器基类
定义分析器接口
"""
from abc import abstractmethod
from typing import Dict, Any

import backtrader as bt


class BaseAnalyzer(bt.Analyzer):
    """基础分析器基类，继承自backtrader的Analyzer"""
    
    # 定义参数
    params = ()
    
    def __init__(self):
        """初始化分析器"""
        super().__init__()
        self.initialize()
    
    @abstractmethod
    def initialize(self):
        """初始化分析器 - 子类必须实现"""
        pass
    
    def start(self):
        """策略开始时调用"""
        # 默认实现，子类可以重写
        pass
    
    def next(self):
        """处理下一个数据点 - backtrader的Analyzer会调用此方法"""
        # 提供默认实现，将在每个数据点上调用update方法
        if hasattr(self, 'update'):
            current_time = self.strategy.datetime.datetime(0)
            self.update(current_time, self.strategy, self.strategy.broker)
    
    def stop(self):
        """策略结束时调用"""
        # 默认实现，子类可以重写
        pass
    
    @abstractmethod
    def update(self, timestamp, strategy, broker):
        """更新分析数据
        
        Args:
            timestamp: 当前时间戳
            strategy: 策略实例
            broker: 经纪商实例
        """
        pass
    
    @abstractmethod
    def get_analysis(self):
        """获取分析结果 - 必须由子类实现
        backtrader会调用此方法获取分析结果
        """
        pass
    
    @abstractmethod
    def get_results(self) -> Dict[str, Any]:
        """获取最终分析结果 - 子类必须实现
        此方法可由外部代码调用，获取更丰富的分析结果
        """
        pass
