"""
交易分析器
提供详细的交易统计数据
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import numpy as np

from .base_analyzer import BaseAnalyzer


class Trade:
    """交易记录类"""

    def __init__(self, entry_time, entry_price, direction, size):
        """初始化交易记录"""
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.exit_time = None
        self.exit_price = None
        self.direction = direction  # 'long' 或 'short'
        self.size = size
        self.pnl = 0.0
        self.status = 'open'
        self.duration = 0  # 交易持续时间（分钟）

    def close(self, exit_time, exit_price):
        """平仓"""
        self.exit_time = exit_time
        self.exit_price = exit_price
        
        # 计算盈亏
        if self.direction == 'long':
            self.pnl = (exit_price - self.entry_price) * self.size
        else:  # short
            self.pnl = (self.entry_price - exit_price) * self.size
            
        # 计算持续时间
        if isinstance(exit_time, datetime) and isinstance(self.entry_time, datetime):
            delta = exit_time - self.entry_time
            self.duration = delta.total_seconds() // 60  # 分钟
            
        self.status = 'closed'
        
    def is_win(self):
        """是否盈利"""
        return self.pnl > 0
        
    def is_loss(self):
        """是否亏损"""
        return self.pnl < 0


class TradeAnalyzer(BaseAnalyzer):
    """交易分析器，分析交易数据，生成交易统计"""

    def __init__(self):
        """初始化交易分析器"""
        self.logger = logging.getLogger(__name__)
        self.reset()

    def reset(self):
        """重置分析器状态"""
        self.trades = []  # 交易记录
        self.current_trade = None  # 当前进行中的交易
        
        # 统计指标
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.break_even_trades = 0
        self.win_rate = 0.0
        
        self.gross_profit = 0.0
        self.gross_loss = 0.0
        self.net_profit = 0.0
        
        self.avg_profit = 0.0
        self.avg_loss = 0.0
        self.avg_trade = 0.0
        
        self.profit_factor = 0.0
        self.win_loss_ratio = 0.0
        self.expectancy = 0.0
        
        self.max_consecutive_wins = 0
        self.max_consecutive_losses = 0
        self.current_consecutive_wins = 0
        self.current_consecutive_losses = 0
        
        self.avg_trade_duration = 0  # 平均交易持续时间（分钟）
        self.max_trade_duration = 0  # 最长交易持续时间（分钟）
        self.min_trade_duration = float('inf')  # 最短交易持续时间（分钟）
        
        self.max_drawdown = 0.0
        self.max_drawdown_duration = 0
        
        self.sqn = 0.0  # 系统质量指标 (System Quality Number)

    def initialize(self):
        """初始化分析器"""
        self.logger.info("初始化交易分析器")
        self.reset()

    def update(self, timestamp, strategy, broker):
        """更新分析数据
        
        Args:
            timestamp: 当前时间戳
            strategy: 策略实例
            broker: 经纪商实例
        """
        # 此方法可在每个bar结束时调用
        # 可以用于跟踪open trades或者执行实时计算
        pass

    def next(self):
        """处理下一个数据点"""
        # 为了兼容旧接口，保留该方法
        pass

    def addindicator(self, indicator_name, indicator_value):
        """
        添加自定义指标
        
        Args:
            indicator_name: 指标名称
            indicator_value: 指标值
        """
        # 这是一个空方法，用于兼容可能的调用
        self.logger.debug(f"接收到指标: {indicator_name}={indicator_value}")
        # 在这里可以实现自定义指标的处理逻辑
        return

    def on_trade(self, trade):
        """处理交易事件
        
        Args:
            trade: 交易对象
        """
        self.logger.debug(f"收到交易: {trade}")
        self.trades.append(trade)
        
        # 更新连续盈亏次数
        if trade['pnl'] > 0:
            self.current_consecutive_wins += 1
            self.current_consecutive_losses = 0
            if self.current_consecutive_wins > self.max_consecutive_wins:
                self.max_consecutive_wins = self.current_consecutive_wins
        elif trade['pnl'] < 0:
            self.current_consecutive_losses += 1
            self.current_consecutive_wins = 0
            if self.current_consecutive_losses > self.max_consecutive_losses:
                self.max_consecutive_losses = self.current_consecutive_losses
        else:
            # 保持不变
            pass

    def analyze(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析交易结果，符合回测流程图中的设计
        
        Args:
            results: 回测引擎返回的原始结果
            
        Returns:
            Dict[str, Any]: 经过分析的回测结果
        """
        self.logger.info("分析交易结果")

        # 计算交易统计
        analysis_results = self.get_results()

        # 合并原始回测结果和新的分析结果
        if 'trades' not in results:
            results['trades'] = analysis_results.get('trades', {})

        self.logger.info("完成交易结果分析")
        return results

    def get_analysis(self):
        """获取分析结果，兼容Backtrader API
        
        Returns:
            Dict: 包含交易统计的字典
        """
        return self.get_results()

    def get_results(self) -> Dict[str, Any]:
        """获取交易分析结果
        
        Returns:
            Dict: 包含交易统计的字典
        """
        self.logger.info("计算交易统计指标")
        
        # 如果没有交易记录，返回空结果
        if not self.trades:
            self.logger.warning("没有交易记录")
            return {'trades': {}}
        
        # 计算基本指标
        self.total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] < 0]
        break_even_trades = [t for t in self.trades if t['pnl'] == 0]
        
        self.winning_trades = len(winning_trades)
        self.losing_trades = len(losing_trades)
        self.break_even_trades = len(break_even_trades)
        
        # 计算胜率
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        
        # 计算盈亏金额
        self.gross_profit = sum(t['pnl'] for t in winning_trades)
        self.gross_loss = sum(t['pnl'] for t in losing_trades)
        self.net_profit = self.gross_profit + self.gross_loss
        
        # 计算平均盈亏
        self.avg_profit = self.gross_profit / self.winning_trades if self.winning_trades > 0 else 0
        self.avg_loss = self.gross_loss / self.losing_trades if self.losing_trades > 0 else 0
        self.avg_trade = self.net_profit / self.total_trades if self.total_trades > 0 else 0
        
        # 计算盈亏比和盈利因子
        self.win_loss_ratio = abs(self.avg_profit / self.avg_loss) if self.avg_loss != 0 else float('inf')
        self.profit_factor = abs(self.gross_profit / self.gross_loss) if self.gross_loss != 0 else float('inf')
        
        # 计算期望值
        self.expectancy = (self.win_rate * self.avg_profit) + ((1 - self.win_rate) * self.avg_loss)
        
        # 计算系统质量指标 (System Quality Number)
        pnl_values = [t['pnl'] for t in self.trades]
        if len(pnl_values) > 1:
            pnl_std = np.std(pnl_values)
            if pnl_std > 0:
                self.sqn = np.sqrt(self.total_trades) * (self.avg_trade / pnl_std)
        
        # 构建结果字典
        results = {
            'trades': {
                'total': self.total_trades,
                'won': self.winning_trades,
                'lost': self.losing_trades,
                'even': self.break_even_trades,
                'win_rate': self.win_rate,
                
                'gross_profit': self.gross_profit,
                'gross_loss': self.gross_loss,
                'net_profit': self.net_profit,
                
                'avg_profit': self.avg_profit,
                'avg_loss': self.avg_loss,
                'avg_trade': self.avg_trade,
                
                'profit_factor': self.profit_factor,
                'win_loss_ratio': self.win_loss_ratio,
                'expectancy': self.expectancy,
                
                'max_consecutive_wins': self.max_consecutive_wins,
                'max_consecutive_losses': self.max_consecutive_losses,
                
                'sqn': self.sqn
            }
        }
        
        self.logger.info(f"交易统计: 总交易={self.total_trades}, 盈利={self.winning_trades}, "
                        f"亏损={self.losing_trades}, 胜率={self.win_rate*100:.2f}%, "
                        f"盈亏比={self.win_loss_ratio:.2f}, 盈利因子={self.profit_factor:.2f}, "
                        f"SQN={self.sqn:.4f}")
        
        return results
