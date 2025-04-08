"""
性能分析器
用于计算回测性能指标
"""
import logging
from typing import Dict, Any

import numpy as np

from .base_analyzer import BaseAnalyzer


class PerformanceAnalyzer(BaseAnalyzer):
    """性能分析器，计算策略性能指标"""

    def __init__(self):
        """初始化性能分析器"""
        self.logger = logging.getLogger(__name__)
        self.reset()

    def reset(self):
        """重置分析器状态"""
        self.equity_curve = []  # 权益曲线
        self.returns = []  # 收益率序列
        self.timestamps = []  # 时间戳
        self.initial_capital = 0.0  # 初始资金
        self.final_capital = 0.0  # 最终资金
        self.days_in_market = 0  # 市场天数

    def initialize(self):
        """初始化分析器"""
        self.logger.info("初始化性能分析器")
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

        # 首次更新时记录初始资金
        if len(self.equity_curve) == 1:
            self.initial_capital = current_equity

        # 计算收益率
        if len(self.equity_curve) > 1:
            daily_return = (self.equity_curve[-1] / self.equity_curve[-2]) - 1
            self.returns.append(daily_return)

        # 更新在市场的天数
        self.days_in_market += 1

    def next(self):
        """处理下一个数据点"""
        # 为了兼容旧接口，保留该方法
        pass

    def get_analysis(self):
        """获取分析结果
        
        Returns:
            Dict: 包含性能指标的字典
        """
        # 计算最终资金
        if self.equity_curve:
            self.final_capital = self.equity_curve[-1]

        return self.get_results()

    def analyze(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析回测结果，符合回测流程图中的设计
        
        Args:
            results: 回测引擎返回的原始结果
            
        Returns:
            Dict[str, Any]: 经过分析的回测结果
        """
        self.logger.info("分析回测结果")

        # 如果已有性能指标，优先使用原始结果中的性能指标
        if 'performance' in results:
            performance = results['performance']
            self.logger.info(f"使用原始结果中的性能指标: {performance}")
        else:
            # 否则自己计算性能指标
            analysis_results = self.get_results()
            performance = analysis_results.get('performance', {})
            self.logger.info(f"计算性能指标: {performance}")

        # 合并原始回测结果和新的分析结果
        analysis_results = {
            'performance': performance
        }

        # 如果原始结果中有风险指标，保留
        if 'risk' in results:
            analysis_results['risk'] = results['risk']

        # 如果原始结果中有交易统计，保留
        if 'trades' in results:
            analysis_results['trades'] = results['trades']

        self.logger.info("完成回测结果分析")
        return analysis_results

    def get_results(self) -> Dict[str, Any]:
        """获取性能分析结果
        
        Returns:
            Dict: 包含性能指标的字典
        """
        results = {}

        # 确保有足够的数据
        if not self.equity_curve or len(self.equity_curve) < 2:
            self.logger.warning("没有足够的数据进行分析")
            return {'performance': {
                'total_return': 0.0,
                'annual_return': 0.0,
                'sharpe_ratio': 0.0,
                'daily_return_mean': 0.0,
                'daily_return_std': 0.0
            }}

        # 计算总收益率
        total_return = (self.final_capital / self.initial_capital) - 1

        # 计算年化收益率
        years = self.days_in_market / 252  # 假设一年252个交易日
        annual_return = (1 + total_return) ** (1 / max(years, 0.01)) - 1

        # 计算日收益率统计
        returns_array = np.array(self.returns)
        daily_return_mean = np.mean(returns_array) if len(returns_array) > 0 else 0
        daily_return_std = np.std(returns_array) if len(returns_array) > 1 else 0

        # 计算夏普比率
        risk_free_rate = 0.02 / 252  # 假设无风险利率为2%/年
        sharpe_ratio = 0.0
        if daily_return_std > 0 and len(returns_array) > 0:
            sharpe_ratio = (daily_return_mean - risk_free_rate) / daily_return_std
            # 转换为年化夏普比率
            sharpe_ratio *= np.sqrt(252)

        # 组织结果
        results['performance'] = {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'daily_return_mean': daily_return_mean,
            'daily_return_std': daily_return_std
        }

        # 记录日志
        self.logger.info(
            f"性能分析: 总收益率={total_return * 100:.2f}%, 年化收益率={annual_return * 100:.2f}%, 夏普比率={sharpe_ratio:.4f}")

        return results
