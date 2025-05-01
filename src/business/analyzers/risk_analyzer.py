"""
风险分析器
用于计算策略风险指标
"""
import logging
from typing import Dict, Any

import numpy as np

from .base_analyzer import BaseAnalyzer


class RiskAnalyzer(BaseAnalyzer):
    """风险分析器，计算策略风险指标"""

    # 定义参数
    params = ()

    def initialize(self):
        """初始化分析器"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("初始化风险分析器")
        self.reset()

    def reset(self):
        """重置分析器状态"""
        self.equity_curve = []  # 权益曲线
        self.timestamps = []  # 时间戳
        self.drawdowns = []  # 回撤序列
        self.returns = []  # 收益率序列
        self.current_peak = 0.0  # 当前峰值
        self.max_drawdown = 0.0  # 最大回撤
        self.max_drawdown_duration = 0  # 最大回撤持续时间
        self.peak_idx = 0  # 峰值索引
        self.trough_idx = 0  # 最大回撤低点索引
        self.volatility = 0.0  # 波动率
        self.sortino_ratio = 0.0  # 索提诺比率
        self.downside_deviation = 0.0  # 下行偏差

    def start(self):
        """策略开始时的处理 - 兼容backtrader"""
        super().start()
        # 记录初始值
        self.current_peak = self.strategy.broker.getvalue()
        self.logger.info(f"风险分析器 - 开始回测，初始值: {self.current_peak:.2f}")

    def stop(self):
        """策略结束时的处理 - 兼容backtrader"""
        # 记录最终结果
        self.logger.info(f"风险分析器 - 结束回测，最大回撤: {self.max_drawdown * 100:.2f}%")
        self.logger.info(f"风险分析器 - 最大回撤持续期: {self.max_drawdown_duration} 个数据点")
        
        # 计算并记录最大回撤的具体时间信息
        if self.max_drawdown > 0 and self.peak_idx < len(self.timestamps) and self.trough_idx < len(self.timestamps):
            peak_time = self.timestamps[self.peak_idx]
            trough_time = self.timestamps[self.trough_idx]
            peak_value = self.equity_curve[self.peak_idx]
            trough_value = self.equity_curve[self.trough_idx]
            
            self.logger.info(f"最大回撤细节:")
            self.logger.info(f"- 峰值时间: {peak_time}, 峰值资金: {peak_value:.2f}")
            self.logger.info(f"- 低点时间: {trough_time}, 低点资金: {trough_value:.2f}")
            self.logger.info(f"- 资金下跌: {peak_value - trough_value:.2f}, 下跌比例: {self.max_drawdown * 100:.2f}%")

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
        current_equity = broker.getvalue()
        self.equity_curve.append(current_equity)

        # 计算收益率
        if len(self.equity_curve) > 1:
            daily_return = (self.equity_curve[-1] / self.equity_curve[-2]) - 1
            self.returns.append(daily_return)

        # 计算回撤
        if len(self.equity_curve) > 0:
            # 更新峰值
            if self.equity_curve[-1] > self.current_peak:
                self.current_peak = self.equity_curve[-1]
                self.peak_idx = len(self.equity_curve) - 1

            # 计算当前回撤
            if self.current_peak > 0:
                # 确保回撤计算正确：(峰值 - 当前值)/峰值
                drawdown = (self.current_peak - self.equity_curve[-1]) / self.current_peak
                
                # 确保回撤值在合理范围内 [0, 1]
                drawdown = max(0, min(drawdown, 1.0))
                
                self.drawdowns.append(drawdown)

                # 更新最大回撤
                if drawdown > self.max_drawdown:
                    self.max_drawdown = drawdown
                    self.max_drawdown_duration = len(self.equity_curve) - self.peak_idx
                    self.trough_idx = len(self.equity_curve) - 1
                    
                    # 记录最大回撤发生位置
                    peak_time = self.timestamps[self.peak_idx]
                    trough_time = self.timestamps[self.trough_idx]
                    self.logger.info(f"新的最大回撤: {self.max_drawdown * 100:.2f}%, 峰值时间: {peak_time}, 低点时间: {trough_time}")
                    
    def get_analysis(self):
        """获取分析结果 - 兼容backtrader接口
        
        Returns:
            Dict: 包含风险指标的字典
        """
        # 确保有足够的数据
        if not self.equity_curve or len(self.equity_curve) < 2:
            return {
                'max_drawdown': 0.0,
                'max_drawdown_duration': 0,
                'volatility': 0.0,
                'sortino_ratio': 0.0,
                'downside_deviation': 0.0,
                'calmar_ratio': 0.0
            }

        # 计算波动率 (如果有日收益率)
        if len(self.equity_curve) > 1:
            # 计算日收益率
            returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
            # 计算波动率 (年化)
            self.volatility = np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0
            
        # 计算索提诺比率（只关注下行风险）
        if len(self.returns) > 10:  # 确保有足够的数据点
            # 计算平均收益率
            avg_return = np.mean(self.returns)
            
            # 计算下行偏差 - 只考虑负收益
            negative_returns = [r for r in self.returns if r < 0]
            if negative_returns:
                self.downside_deviation = np.std(negative_returns) * np.sqrt(252)
                
                # 计算索提诺比率
                if self.downside_deviation > 0:
                    # 使用0作为最小可接受收益率
                    self.sortino_ratio = (avg_return * 252) / self.downside_deviation
                
        # 计算卡尔玛比率 (年化收益率/最大回撤)
        calmar_ratio = 0.0
        if self.max_drawdown > 0:
            # 计算年化收益率
            total_return = (self.equity_curve[-1] / self.equity_curve[0]) - 1
            days = len(self.equity_curve)
            annual_return = ((1 + total_return) ** (252 / days)) - 1
            calmar_ratio = annual_return / self.max_drawdown

        # 返回分析结果
        return {
            'max_drawdown': self.max_drawdown,
            'max_drawdown_duration': self.max_drawdown_duration,
            'volatility': self.volatility,
            'sortino_ratio': self.sortino_ratio,
            'downside_deviation': self.downside_deviation,
            'calmar_ratio': calmar_ratio,
            'peak_idx': self.peak_idx,
            'trough_idx': self.trough_idx
        }

    def get_results(self) -> Dict[str, Any]:
        """获取风险分析结果（扩展版）
        
        Returns:
            Dict: 包含详细风险指标的字典
        """
        # 获取基本分析结果
        basic_results = self.get_analysis()
        
        # 添加更多详细信息
        results = {
            'risk': basic_results,
            'drawdown_series': self.drawdowns,
            'equity_curve': self.equity_curve,
            'timestamps': self.timestamps
        }

        # 记录日志
        max_dd = basic_results.get('max_drawdown', 0)
        max_dd_duration = basic_results.get('max_drawdown_duration', 0)
        volatility = basic_results.get('volatility', 0)
        
        self.logger.info(
            f"风险分析: 最大回撤={max_dd * 100:.2f}%, 最大回撤持续期={max_dd_duration}个点, 波动率={volatility * 100:.2f}%")

        return results
