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
        self.current_peak = 0.0  # 当前峰值
        self.max_drawdown = 0.0  # 最大回撤
        self.max_drawdown_duration = 0  # 最大回撤持续时间
        self.peak_idx = 0  # 峰值索引
        self.volatility = 0.0  # 波动率

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
                'volatility': 0.0
            }

        # 计算波动率 (如果有日收益率)
        if len(self.equity_curve) > 1:
            # 计算日收益率
            returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
            # 计算波动率 (年化)
            self.volatility = np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0

        # 返回 backtrader 预期的结果格式
        return {
            'max_drawdown': self.max_drawdown,
            'max_drawdown_duration': self.max_drawdown_duration,
            'volatility': self.volatility
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
