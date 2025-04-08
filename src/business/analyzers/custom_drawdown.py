"""
自定义回撤分析器
用于正确计算回测过程中的最大回撤和持续时间
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

import backtrader as bt


class CustomDrawDown(bt.Analyzer):
    """
    自定义回撤分析器，确保计算正确的回撤值和持续时间
    
    提供比标准分析器更详细的回撤信息，包括：
    - 最大回撤百分比
    - 回撤持续的数据点数
    - 回撤开始和结束日期
    - 实际日历天数
    - 回撤历史记录
    """

    params = (
        ('timeframe', None),  # 可选：数据的时间周期，用于计算实际天数
    )

    def __init__(self):
        """初始化回撤分析器"""
        self.logger = logging.getLogger(__name__)
        self.peak = 0.0  # 峰值
        self.max_dd = 0.0  # 最大回撤
        self.max_dd_points = 0  # 最大回撤持续时间（数据点个数）
        self.current_dd_points = 0  # 当前回撤持续时间（数据点个数）
        self.dd_start_point = 0  # 当前回撤开始的数据点索引
        self.points_count = 0  # 总数据点计数
        
        # 初始化日期信息
        self.peak_date = None  # 峰值出现日期
        self.bottom_date = None  # 谷值出现日期
        self.max_dd_start_date = None  # 最大回撤开始日期
        self.max_dd_end_date = None  # 最大回撤结束日期
        
        # 历史回撤序列，用于更精确的分析
        self.drawdowns = []  # 格式: [(开始日期, 结束日期, 回撤值, 持续点数)]

    def start(self):
        """策略开始时初始化"""
        # 重置计数器
        self.points_count = 0
        self.logger.info("初始化自定义回撤分析器")

    def next(self):
        """处理下一个数据点"""
        # 更新计数器
        self.points_count += 1
        
        # 获取当前资金曲线值和日期
        value = self.strategy.broker.getvalue()
        date = self.strategy.datetime.datetime()
        
        # 第一个数据点
        if self.peak == 0.0:
            self.peak = value
            self.peak_date = date
            self.dd_start_point = self.points_count
            return
            
        # 新高，更新峰值
        if value > self.peak:
            # 如果之前有回撤，记录完整的回撤周期
            if self.current_dd_points > 0 and self.peak_date is not None:
                dd = (self.peak - value) / self.peak if self.peak > 0 else 0
                self.drawdowns.append((
                    self.peak_date,  # 开始日期
                    date,  # 结束日期
                    dd,  # 回撤值
                    self.current_dd_points  # 持续点数
                ))
            
            self.peak = value
            self.peak_date = date
            self.current_dd_points = 0  # 重置当前回撤持续点数
            self.dd_start_point = self.points_count  # 更新回撤开始点
        else:
            # 当前值低于峰值，处于回撤中
            self.current_dd_points += 1
            
            # 计算当前回撤比例
            dd = (self.peak - value) / self.peak if self.peak > 0 else 0
            dd = max(0.0, min(dd, 1.0))  # 回撤限制在[0,1]范围
            
            # 如果是更大的回撤，记录
            if dd > self.max_dd:
                self.max_dd = dd
                self.max_dd_points = self.current_dd_points
                self.max_dd_start_date = self.peak_date
                self.max_dd_end_date = date
                self.bottom_date = date
                self.logger.debug(f"更新最大回撤: {dd*100:.2f}%, 持续: {self.max_dd_points}个点, 从{self.max_dd_start_date}到{self.max_dd_end_date}")

    def stop(self):
        """策略结束时完成计算"""
        # 添加最后一个回撤周期(如果有)
        if self.current_dd_points > 0 and self.peak_date is not None:
            last_value = self.strategy.broker.getvalue()
            last_date = self.strategy.datetime.datetime()
            dd = (self.peak - last_value) / self.peak if self.peak > 0 else 0
            self.drawdowns.append((self.peak_date, last_date, dd, self.current_dd_points))
            
        # 记录最终结果
        self.logger.info(f"回撤分析完成: 最大回撤 {self.max_dd*100:.2f}%, 持续 {self.max_dd_points}个点")
        if self.max_dd_start_date and self.max_dd_end_date:
            delta = self.max_dd_end_date - self.max_dd_start_date
            days = delta.days + (1 if delta.seconds > 0 else 0)
            self.logger.info(f"最大回撤期间: {self.max_dd_start_date} 至 {self.max_dd_end_date}, 持续 {days} 天")

    def get_analysis(self) -> Dict[str, Any]:
        """获取分析结果
        
        Returns:
            Dict[str, Any]: 回撤分析结果
        """
        # 标准返回结构，包含回撤值和持续点数
        result = {
            'max': {
                'drawdown': self.max_dd,
                'len': self.max_dd_points,
                'points': self.max_dd_points  # 原始点数
            }
        }
        
        # 如果有日期信息，添加到结果中
        if self.max_dd_start_date and self.max_dd_end_date:
            result['max']['start_date'] = self.max_dd_start_date
            result['max']['end_date'] = self.max_dd_end_date
            
            # 计算实际天数
            delta = self.max_dd_end_date - self.max_dd_start_date
            days = delta.days + (1 if delta.seconds > 0 else 0)
            result['max']['days'] = days
            
        # 添加回撤历史记录
        result['drawdowns'] = self.drawdowns
        
        # 添加总数据点数，用于后续分析
        result['total_points'] = self.points_count
            
        return result 