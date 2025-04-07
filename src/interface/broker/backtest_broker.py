"""
回测经纪商实现
"""
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Dict, Any, List

from .base_broker import BaseBroker

class BacktestBroker(BaseBroker):
    """回测经纪商，实现回测环境下的模拟交易功能"""
    
    def __init__(self, initial_capital=1000000):
        """初始化回测经纪商
        
        Args:
            initial_capital: 初始资金
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}  # 持仓，格式：{symbol: quantity}
        self.position_value = 0.0  # 持仓市值
        self.cash = initial_capital  # 可用资金
        self.equity = initial_capital  # 总资产
        self.orders = {}  # 订单，格式：{order_id: order}
        self.trades = []  # 交易记录
        self.commission_rate = 0.0003  # 手续费率
        self.slippage = 0.0001  # 滑点率
        
        # 回测状态
        self.current_datetime = None
        self.current_prices = {}  # 当前价格，格式：{symbol: price}
        
        self.logger.info(f"初始化回测经纪商，初始资金: {initial_capital}")
        
    def set_cash(self, cash: float):
        """设置初始资金
        
        Args:
            cash: 初始资金
        """
        self.initial_capital = cash
        self.current_capital = cash
        self.cash = cash
        self.equity = cash
        self.logger.info(f"设置初始资金: {cash}")
        
    def set_commission(self, commission_rate: float):
        """设置手续费率
        
        Args:
            commission_rate: 手续费率
        """
        self.commission_rate = commission_rate
        self.logger.info(f"设置手续费率: {commission_rate}")
        
    def set_slippage(self, slippage: float):
        """设置滑点率
        
        Args:
            slippage: 滑点率
        """
        self.slippage = slippage
        self.logger.info(f"设置滑点率: {slippage}")
        
    def connect(self):
        """连接经纪商"""
        self.logger.info("连接回测经纪商")
        return True
    
    def disconnect(self):
        """断开连接"""
        self.logger.info("断开回测经纪商连接")
        return True
    
    def update(self, timestamp: datetime, position: float, bar_data: pd.Series):
        """更新回测经纪商状态
        
        Args:
            timestamp: 当前时间戳
            position: 目标仓位比例，1.0表示满仓多头，-1.0表示满仓空头，0表示空仓
            bar_data: 当前K线数据，包含open, high, low, close, volume等信息
        """
        # 更新当前时间
        self.current_datetime = timestamp
        
        # 获取当前价格
        current_price = bar_data.get('close', 0)
        if current_price <= 0:
            self.logger.warning(f"无效价格: {current_price}, 使用上一个有效价格")
            return
            
        # 更新当前价格
        symbol = bar_data.name if hasattr(bar_data, 'name') else 'default'
        self.current_prices[symbol] = current_price
        
        # 获取当前持仓
        current_position = self.positions.get(symbol, 0)
        
        # 计算目标持仓数量
        target_position_value = self.equity * position
        target_position = target_position_value / current_price if current_price > 0 else 0
        
        # 计算需要调整的持仓数量
        position_delta = target_position - current_position
        
        # 如果需要调整持仓
        if abs(position_delta) > 0.01:  # 忽略极小的调整
            # 计算交易成本
            trade_value = abs(position_delta) * current_price
            commission = trade_value * self.commission_rate
            slippage_cost = trade_value * self.slippage
            total_cost = commission + slippage_cost
            
            # 更新资金
            self.cash -= (position_delta * current_price + total_cost)
            
            # 更新持仓
            self.positions[symbol] = target_position
            
            # 记录交易
            trade = {
                'datetime': timestamp,
                'symbol': symbol,
                'quantity': position_delta,
                'price': current_price,
                'commission': commission,
                'slippage': slippage_cost,
                'value': trade_value
            }
            self.trades.append(trade)
            
            trade_type = "买入" if position_delta > 0 else "卖出"
            self.logger.info(f"{trade_type} {symbol}: {abs(position_delta):.2f}股, 价格: {current_price}, 成本: {total_cost:.2f}")
        
        # 更新持仓市值
        self.position_value = sum(self.positions.get(s, 0) * self.current_prices.get(s, 0) for s in self.positions)
        
        # 更新总资产
        self.equity = self.cash + self.position_value
        
        # 更新当前资金
        self.current_capital = self.equity
    
    def place_order(self, order):
        """下单
        
        Args:
            order: 订单对象
        """
        self.orders[order.order_id] = order
        self.logger.info(f"下单: {order}")
        
    def cancel_order(self, order_id):
        """撤单
        
        Args:
            order_id: 订单ID
        """
        if order_id in self.orders:
            order = self.orders[order_id]
            del self.orders[order_id]
            self.logger.info(f"撤单: {order_id}")
    
    def get_position(self, symbol):
        """获取持仓
        
        Args:
            symbol: 交易品种
            
        Returns:
            float: 持仓数量
        """
        return self.positions.get(symbol, 0)
    
    def get_equity(self):
        """获取总资产
        
        Returns:
            float: 总资产
        """
        return self.equity
    
    def get_account(self):
        """获取账户信息
        
        Returns:
            Dict: 账户信息
        """
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'cash': self.cash,
            'position_value': self.position_value,
            'equity': self.equity,
            'positions': self.positions,
            'orders': self.orders,
            'trades': self.trades
        } 