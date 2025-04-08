"""
持仓分析器
分析策略持仓情况、持仓时间分布等
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

import numpy as np

from .base_analyzer import BaseAnalyzer


class Position:
    """持仓记录类"""
    
    def __init__(self, symbol, size, direction, entry_time, entry_price):
        """初始化持仓记录
        
        Args:
            symbol: 交易标的
            size: 持仓大小
            direction: 方向，'long'或'short'
            entry_time: 建仓时间
            entry_price: 建仓价格
        """
        self.symbol = symbol
        self.size = size
        self.direction = direction
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.exit_time = None
        self.exit_price = None
        self.exit_reason = None
        self.pnl = 0.0
        self.duration = 0  # 持仓时长(分钟)
        self.status = 'open'
        
    def close(self, exit_time, exit_price, reason=None):
        """平仓
        
        Args:
            exit_time: 平仓时间
            exit_price: 平仓价格
            reason: 平仓原因
        """
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = reason
        
        # 计算盈亏
        if self.direction == 'long':
            self.pnl = (exit_price - self.entry_price) * self.size
        else:  # short
            self.pnl = (self.entry_price - exit_price) * self.size
            
        # 计算持仓时长
        if isinstance(exit_time, datetime) and isinstance(self.entry_time, datetime):
            delta = exit_time - self.entry_time
            self.duration = delta.total_seconds() // 60  # 分钟
            
        self.status = 'closed'
        
    def is_profitable(self):
        """是否盈利"""
        return self.pnl > 0
    
    def get_duration_days(self):
        """获取持仓天数"""
        if self.status == 'open':
            return 0
        
        if isinstance(self.exit_time, datetime) and isinstance(self.entry_time, datetime):
            delta = self.exit_time - self.entry_time
            return delta.days + (1 if delta.seconds > 0 else 0)
        
        return 0


class PositionAnalyzer(BaseAnalyzer):
    """持仓分析器，分析策略持仓情况"""
    
    def __init__(self):
        """初始化持仓分析器"""
        self.logger = logging.getLogger(__name__)
        self.reset()
        
    def reset(self):
        """重置分析器状态"""
        self.current_positions = {}  # 当前持仓，按symbol索引
        self.closed_positions = []  # 已平仓的持仓记录
        self.position_start_times = {}  # 记录每个持仓的开始时间
        
        # 统计数据
        self.long_positions = 0  # 多头持仓次数
        self.short_positions = 0  # 空头持仓次数
        self.avg_holding_period = 0  # 平均持仓周期(分钟)
        self.max_holding_period = 0  # 最长持仓周期(分钟)
        self.min_holding_period = float('inf')  # 最短持仓周期(分钟)
        
        # 持仓时间分布
        self.holding_periods = []  # 持仓时间列表(分钟)
        
    def initialize(self):
        """初始化分析器"""
        self.logger.info("初始化持仓分析器")
        self.reset()
        
    def update(self, timestamp, strategy, broker):
        """更新分析数据
        
        Args:
            timestamp: 当前时间戳
            strategy: 策略实例
            broker: 经纪商实例
        """
        # 记录持仓变化
        # 这里可以监控策略的持仓情况
        pass
        
    def next(self):
        """处理下一个数据点"""
        # 为了兼容旧接口，保留该方法
        pass
        
    def on_trade(self, trade):
        """处理交易事件
        
        Args:
            trade: 交易对象
        """
        self.logger.debug(f"收到交易: {trade}")
        
        # 根据交易信息更新持仓记录
        if 'action' in trade:
            symbol = trade.get('symbol', 'unknown')
            size = trade.get('size', 0)
            price = trade.get('price', 0)
            timestamp = trade.get('timestamp', datetime.now())
            
            if trade['action'] == 'buy':
                # 开多仓
                self.long_positions += 1
                position = Position(symbol, size, 'long', timestamp, price)
                self.current_positions[symbol] = position
                self.position_start_times[symbol] = timestamp
                
            elif trade['action'] == 'sell' and symbol in self.current_positions:
                # 平多仓
                position = self.current_positions[symbol]
                if position.direction == 'long':
                    position.close(timestamp, price, 'sell')
                    self.closed_positions.append(position)
                    self._update_stats(position)
                    del self.current_positions[symbol]
                    
            elif trade['action'] == 'short':
                # 开空仓
                self.short_positions += 1
                position = Position(symbol, size, 'short', timestamp, price)
                self.current_positions[symbol] = position
                self.position_start_times[symbol] = timestamp
                
            elif trade['action'] == 'cover' and symbol in self.current_positions:
                # 平空仓
                position = self.current_positions[symbol]
                if position.direction == 'short':
                    position.close(timestamp, price, 'cover')
                    self.closed_positions.append(position)
                    self._update_stats(position)
                    del self.current_positions[symbol]
        
    def _update_stats(self, position):
        """更新统计数据
        
        Args:
            position: 持仓记录
        """
        # 更新持仓时间统计
        duration = position.duration
        self.holding_periods.append(duration)
        
        # 更新最长/最短持仓周期
        if duration > self.max_holding_period:
            self.max_holding_period = duration
            
        if duration < self.min_holding_period:
            self.min_holding_period = duration
            
        # 更新平均持仓周期
        if self.holding_periods:
            self.avg_holding_period = np.mean(self.holding_periods)
            
    def get_analysis(self):
        """获取分析结果
        
        Returns:
            Dict: 包含持仓分析的字典
        """
        return self.get_results()
        
    def analyze(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析回测结果
        
        Args:
            results: 回测引擎返回的原始结果
            
        Returns:
            Dict[str, Any]: 经过分析的回测结果
        """
        self.logger.info("分析持仓情况")
        
        # 计算持仓统计
        position_stats = self.get_results()
        
        # 将持仓统计添加到结果中
        results['position_stats'] = position_stats
        
        self.logger.info("完成持仓分析")
        return results
        
    def get_results(self) -> Dict[str, Any]:
        """获取持仓分析结果
        
        Returns:
            Dict: 包含持仓统计的字典
        """
        # 确保有持仓数据
        if not self.closed_positions:
            self.logger.warning("没有已平仓的持仓记录")
            return {}
            
        # 计算持仓分布统计
        holding_periods_array = np.array(self.holding_periods)
        
        # 持仓时间分布
        holding_time_percentiles = {}
        percentiles = [10, 25, 50, 75, 90]
        for p in percentiles:
            if len(holding_periods_array) > 0:
                holding_time_percentiles[f"p{p}"] = np.percentile(holding_periods_array, p)
            else:
                holding_time_percentiles[f"p{p}"] = 0
                
        # 按方向分类持仓
        long_positions = [p for p in self.closed_positions if p.direction == 'long']
        short_positions = [p for p in self.closed_positions if p.direction == 'short']
        
        # 计算每个方向的盈亏
        long_pnl = sum(p.pnl for p in long_positions)
        short_pnl = sum(p.pnl for p in short_positions)
        
        # 计算每个方向的胜率
        long_win_rate = len([p for p in long_positions if p.is_profitable()]) / len(long_positions) if long_positions else 0
        short_win_rate = len([p for p in short_positions if p.is_profitable()]) / len(short_positions) if short_positions else 0
        
        # 返回结果
        return {
            'total_positions': len(self.closed_positions),
            'long_positions': len(long_positions),
            'short_positions': len(short_positions),
            'long_pnl': long_pnl,
            'short_pnl': short_pnl,
            'long_win_rate': long_win_rate,
            'short_win_rate': short_win_rate,
            'avg_holding_period': self.avg_holding_period,
            'max_holding_period': self.max_holding_period,
            'min_holding_period': self.min_holding_period if self.min_holding_period != float('inf') else 0,
            'holding_time_percentiles': holding_time_percentiles
        } 