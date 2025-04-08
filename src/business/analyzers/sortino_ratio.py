#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
自定义Sortino比率分析器
计算交易策略的Sortino比率，该比率仅考虑下行偏差
"""
import backtrader as bt
import numpy as np
from collections import deque
import logging

logger = logging.getLogger(__name__)

class SortinoRatio(bt.Analyzer):
    """
    计算Sortino比率分析器
    
    Sortino比率是对Sharpe比率的改进，它只考虑下行波动，
    即只有低于某个最低可接受收益率的回报才会被视为风险。
    
    公式: (平均收益率 - 无风险收益率) / 下行标准差
    
    参数:
        timeframe: 收益的时间段类型 (day, week, month, year)
        compression: 用于计算的周期数
        target_return: 最低可接受收益率，低于此值的收益被视为负面波动 (默认为0)
        riskfreerate: 无风险利率 (默认为0.01, 即1%)
        annualize: 是否计算年化Sortino比率 (默认为True)
        factor: 年化因子，None表示自动选择 (252=日, 52=周, 12=月)
    """
    params = (
        ('timeframe', bt.TimeFrame.Days),
        ('compression', 1),
        ('target_return', 0.0),
        ('riskfreerate', 0.01),
        ('annualize', True),
        ('factor', None),
    )
    
    def __init__(self):
        self.returns = []
        self.annualized_returns = deque()
        
        # 决定年化因子
        if self.p.factor is None:
            if self.p.timeframe == bt.TimeFrame.Days:
                self.factor = 252.0
            elif self.p.timeframe == bt.TimeFrame.Weeks:
                self.factor = 52.0
            elif self.p.timeframe == bt.TimeFrame.Months:
                self.factor = 12.0
            elif self.p.timeframe == bt.TimeFrame.Years:
                self.factor = 1.0
            else:
                self.factor = 252.0  # 默认使用日度数据的年化因子
        else:
            self.factor = float(self.p.factor)
        
        # 跟踪策略的价值
        self.value = self.strategy.broker.getvalue()
        self.target_return = self.p.target_return / self.factor if self.p.annualize else self.p.target_return
    
    def next(self):
        """每个bar都会调用此方法来计算当天的收益率"""
        # 获取当前价值
        current_value = self.strategy.broker.getvalue()
        
        # 计算简单回报率
        r = (current_value / self.value) - 1.0
        
        # 记录回报
        self.returns.append(r)
        
        # 更新当前价值作为下一周期的基线
        self.value = current_value
    
    def stop(self):
        """回测结束时计算最终的Sortino比率"""
        # 如果没有足够的数据，无法计算或返回0
        if not self.returns or len(self.returns) < 2:
            self.ratio = 0.0
            self.downside_deviation = 0.0
            return
        
        # 将日度回报转换为numpy数组方便计算
        returns = np.array(self.returns)
        
        # 计算平均回报率
        avg_return = np.mean(returns)
        
        # 计算目标收益率，将日度目标收益率转换为相应周期的收益率
        target_return = self.target_return
        
        # 计算下行偏差 - 只考虑低于目标收益率的回报
        downside_returns = returns[returns < target_return]
        
        if len(downside_returns) == 0:
            # 如果没有下行回报，设置下行标准差为0.001以避免除以0
            downside_deviation = 0.001
        else:
            # 计算目标下行偏差 (TDD)
            squared_downside = np.square(target_return - downside_returns)
            downside_deviation = np.sqrt(np.mean(squared_downside))
        
        # 计算无风险利率
        risk_free = self.p.riskfreerate / self.factor if self.p.annualize else self.p.riskfreerate
        
        # 计算超额收益
        excess_return = avg_return - risk_free
        
        # 计算Sortino比率
        self.ratio = excess_return / downside_deviation
        
        # 如果需要年化且收益周期非年度，则进行年化
        if self.p.annualize and self.factor != 1.0:
            self.ratio = self.ratio * np.sqrt(self.factor)
        
        self.downside_deviation = downside_deviation
        
        # 记录计算信息
        logger.debug(f"Sortino比率计算: 平均回报={avg_return:.6f}, 下行标准差={downside_deviation:.6f}, 比率={self.ratio:.6f}")
    
    def get_analysis(self):
        """返回分析结果，包含Sortino比率"""
        # 返回与键名'sortinoratio'对应的比率，便于外部访问
        return {
            'sortinoratio': self.ratio,
            'downside_deviation': getattr(self, 'downside_deviation', 0.0),
            'annualized': self.p.annualize
        } 