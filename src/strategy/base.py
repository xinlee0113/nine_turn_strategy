import backtrader as bt
from typing import Dict, Any, List
import pandas as pd
import numpy as np

class BaseStrategy(bt.Strategy):
    """策略基类 (基于backtrader)"""
    
    def __init__(self):
        """初始化策略"""
        super(BaseStrategy, self).__init__()
        
        # 保存数据引用
        self.datas = {}
        for i, data in enumerate(self.datas):
            self.datas[data._name] = data
            
        # 初始化指标
        self._init_indicators()
        
        # 初始化状态
        self._init_state()
    
    def _init_indicators(self):
        """初始化技术指标"""
        pass
    
    def _init_state(self):
        """初始化策略状态"""
        self.positions = {symbol: 0 for symbol in self.datas.keys()}
        self.trades = []
        self.equity = [self.broker.getvalue()]
    
    def next(self):
        """策略逻辑"""
        # 获取当前数据
        current_data = {
            symbol: {
                'datetime': data.datetime.datetime(0),
                'open': data.open[0],
                'high': data.high[0],
                'low': data.low[0],
                'close': data.close[0],
                'volume': data.volume[0]
            }
            for symbol, data in self.datas.items()
        }
        
        # 生成信号
        signals = self.generate_signals(current_data)
        
        # 计算仓位
        positions = self.calculate_position(signals, current_data)
        
        # 计算止损止盈
        stop_loss = self.calculate_stop_loss(current_data)
        take_profit = self.calculate_take_profit(current_data)
        
        # 执行交易
        self._execute_trades(positions, current_data, stop_loss, take_profit)
        
        # 更新权益
        self._update_equity()
    
    def generate_signals(self, data: Dict[str, Dict[str, float]]) -> Dict[str, int]:
        """
        生成交易信号
        
        Args:
            data: 市场数据
            
        Returns:
            交易信号字典
        """
        signals = {}
        for symbol in data.keys():
            signals[symbol] = 0  # 默认不交易
        return signals
    
    def calculate_position(self, signals: Dict[str, int], 
                         data: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """
        计算目标仓位
        
        Args:
            signals: 交易信号
            data: 市场数据
            
        Returns:
            目标仓位字典
        """
        positions = {}
        for symbol in signals.keys():
            positions[symbol] = 0.0  # 默认空仓
        return positions
    
    def calculate_stop_loss(self, data: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """
        计算止损价格
        
        Args:
            data: 市场数据
            
        Returns:
            止损价格字典
        """
        stop_loss = {}
        for symbol in data.keys():
            stop_loss[symbol] = 0.0  # 默认无止损
        return stop_loss
    
    def calculate_take_profit(self, data: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """
        计算止盈价格
        
        Args:
            data: 市场数据
            
        Returns:
            止盈价格字典
        """
        take_profit = {}
        for symbol in data.keys():
            take_profit[symbol] = 0.0  # 默认无止盈
        return take_profit
    
    def _execute_trades(self, positions: Dict[str, float], 
                       data: Dict[str, Dict[str, float]],
                       stop_loss: Dict[str, float],
                       take_profit: Dict[str, float]) -> None:
        """执行交易"""
        for symbol, position in positions.items():
            current_position = self.positions[symbol]
            
            # 检查是否需要调整仓位
            if position != current_position:
                # 计算交易数量
                quantity = position - current_position
                
                # 执行交易
                if quantity > 0:
                    self.buy(data=self.datas[symbol], size=abs(quantity))
                elif quantity < 0:
                    self.sell(data=self.datas[symbol], size=abs(quantity))
                
                # 更新持仓
                self.positions[symbol] = position
    
    def _update_equity(self) -> None:
        """更新权益"""
        self.equity.append(self.broker.getvalue())
    
    def notify_trade(self, trade):
        """交易通知"""
        if trade.isclosed:
            self.trades.append({
                'symbol': trade.data._name,
                'datetime': trade.dtopen,
                'quantity': trade.size,
                'price': trade.pnl,
                'pnl': trade.pnl
            }) 