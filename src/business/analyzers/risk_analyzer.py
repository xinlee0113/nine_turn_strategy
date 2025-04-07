"""
风险分析器
用于计算策略风险指标
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List
import logging

from .base_analyzer import BaseAnalyzer

class RiskAnalyzer(BaseAnalyzer):
    """风险分析器，计算策略风险指标"""
    
    def __init__(self):
        """初始化风险分析器"""
        self.logger = logging.getLogger(__name__)
        self.reset()
        
    def reset(self):
        """重置分析器状态"""
        self.equity_curve = []      # 权益曲线
        self.timestamps = []        # 时间戳
        self.drawdowns = []         # 回撤序列
        self.current_peak = 0.0     # 当前峰值
        self.max_drawdown = 0.0     # 最大回撤
        self.max_drawdown_duration = 0  # 最大回撤持续时间
        self.peak_idx = 0           # 峰值索引
        self.volatility = 0.0       # 波动率
        
    def initialize(self):
        """初始化分析器"""
        self.logger.info("初始化风险分析器")
        self.reset()
        
    def update(self, timestamp, strategy, broker):
        """更新分析数据
        
        Args:
            timestamp: 当前时间戳
            strategy: 策略实例
            broker: 经纪商实例
        """
        # 记录时间戳
        self.timestamps.append(timestamp)
        
        # 记录资金
        current_equity = broker.get_equity()
        self.equity_curve.append(current_equity)
        
        # 计算回撤
        if len(self.equity_curve) > 0:
            # 更新峰值
            if self.equity_curve[-1] > self.current_peak:
                self.current_peak = self.equity_curve[-1]
                self.peak_idx = len(self.equity_curve) - 1
                
            # 计算当前回撤
            if self.current_peak > 0:
                drawdown = 1 - (self.equity_curve[-1] / self.current_peak)
                self.drawdowns.append(drawdown)
                
                # 更新最大回撤
                if drawdown > self.max_drawdown:
                    self.max_drawdown = drawdown
                    self.max_drawdown_duration = len(self.equity_curve) - self.peak_idx
        
    def next(self):
        """处理下一个数据点"""
        # 为了兼容旧接口，保留该方法
        pass
        
    def get_analysis(self):
        """获取分析结果
        
        Returns:
            Dict: 包含风险指标的字典
        """
        return self.get_results()
        
    def get_results(self) -> Dict[str, Any]:
        """获取风险分析结果
        
        Returns:
            Dict: 包含风险指标的字典
        """
        results = {}
        
        # 确保有足够的数据
        if not self.equity_curve or len(self.equity_curve) < 2:
            self.logger.warning("没有足够的数据进行风险分析")
            return {'risk': {
                'max_drawdown': 0.0,
                'max_drawdown_length': 0,
                'volatility': 0.0,
                'beta': 0.0,
                'alpha': 0.0
            }}
            
        # 计算最终指标
        
        # 计算波动率 (如果有日收益率)
        if len(self.equity_curve) > 1:
            # 计算日收益率
            returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
            # 计算波动率 (年化)
            self.volatility = np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0
        
        # 组织结果
        results['risk'] = {
            'max_drawdown': self.max_drawdown,
            'max_drawdown_length': self.max_drawdown_duration,
            'volatility': self.volatility,
            'beta': 0.0,  # 需要基准数据计算
            'alpha': 0.0   # 需要基准数据计算
        }
        
        # 记录日志
        self.logger.info(f"风险分析: 最大回撤={self.max_drawdown*100:.2f}%, 最大回撤持续期={self.max_drawdown_duration}天, 波动率={self.volatility*100:.2f}%")
        
        return results 