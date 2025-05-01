"""
SQN分析器 - 系统质量指标(System Quality Number)
用于计算Van Tharp提出的交易系统质量指标
"""
import logging
from typing import Dict, Any
import math

import numpy as np
import backtrader as bt

from .base_analyzer import BaseAnalyzer


class SQNAnalyzer(BaseAnalyzer):
    """系统质量指标(SQN)分析器
    
    计算公式：SQN = (平均交易收益 / 交易收益标准差) * √交易次数
    """
    
    def initialize(self):
        """初始化分析器"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("初始化SQN分析器")
        self.reset()
    
    def reset(self):
        """重置分析器状态"""
        self.trades = []  # 所有交易记录的收益
        self.total_trades = 0  # 总交易次数
        self.sqn = 0.0  # System Quality Number
    
    def notify_trade(self, trade):
        """交易通知回调
        
        Args:
            trade: 交易对象
        """
        if trade.isclosed:  # 只在交易关闭时记录
            # 记录交易净收益
            self.trades.append(trade.pnlcomm)
            self.total_trades += 1
            self.logger.debug(f"SQN分析器记录交易: {trade.pnlcomm:.2f}")
    
    def update(self, timestamp, strategy, broker):
        """更新分析数据
        
        Args:
            timestamp: 当前时间戳
            strategy: 策略实例
            broker: 经纪商实例
        """
        # 在这个分析器中不需要每个数据点的更新
        pass
    
    def _calculate_sqn(self):
        """计算SQN指标"""
        if len(self.trades) > 1:  # 至少需要两个交易才能计算标准差
            avg_trade = np.mean(self.trades)
            std_trade = np.std(self.trades, ddof=1)  # 使用样本标准差
            
            if std_trade > 0:
                self.sqn = (avg_trade / std_trade) * math.sqrt(len(self.trades))
            else:
                self.sqn = 0.0  # 如果标准差为0，SQN无法计算
                
            self.logger.debug(f"计算SQN: 平均收益={avg_trade:.2f}, 标准差={std_trade:.2f}, 交易数={len(self.trades)}, SQN={self.sqn:.4f}")
        else:
            self.sqn = 0.0
    
    def get_analysis(self):
        """获取分析结果
        
        Returns:
            Dict: 包含SQN指标的字典
        """
        self._calculate_sqn()
        
        # 根据SQN值评估系统质量
        quality = self._evaluate_system_quality()
        
        return {
            'sqn': self.sqn,
            'total_trades': self.total_trades,
            'system_quality': quality
        }
    
    def _evaluate_system_quality(self):
        """根据SQN值评估系统质量
        
        Returns:
            str: 系统质量评价
        """
        if self.sqn < 1.0:
            return "较差"
        elif self.sqn < 2.0:
            return "一般"
        elif self.sqn < 3.0:
            return "良好"
        elif self.sqn < 5.0:
            return "优秀"
        else:
            return "卓越"
    
    def get_results(self) -> Dict[str, Any]:
        """获取分析结果
        
        Returns:
            Dict: 包含SQN指标的字典
        """
        analysis = self.get_analysis()
        
        # 记录日志
        self.logger.info(f"SQN分析: 系统质量指标={analysis['sqn']:.4f}, 总交易数={analysis['total_trades']}, 系统质量={analysis['system_quality']}")
        
        return {
            'sqn': analysis
        }
    
    def stop(self):
        """策略结束时的处理"""
        super().stop()
        self._calculate_sqn()
        self.logger.info(f"SQN分析器 - 最终SQN值: {self.sqn:.4f}, 系统质量: {self._evaluate_system_quality()}") 