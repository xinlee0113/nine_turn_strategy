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

    # 定义参数
    params = (
        ('risk_free_rate', 0.02),  # 年化无风险利率，默认2%
    )

    def initialize(self):
        """初始化分析器"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("初始化性能分析器")
        self.reset()

    def reset(self):
        """重置分析器状态"""
        self.equity_curve = []  # 权益曲线
        self.returns = []  # 收益率序列
        self.timestamps = []  # 时间戳
        self.initial_capital = 0.0  # 初始资金
        self.final_capital = 0.0  # 最终资金
        self.days_in_market = 0  # 市场天数
        self.last_date = None  # 上一个交易日期

    def start(self):
        """策略开始时的处理 - 兼容backtrader"""
        super().start()
        # 记录初始资金
        self.initial_capital = self.strategy.broker.getvalue()
        self.logger.info(f"性能分析器 - 开始回测，初始资金: {self.initial_capital:.2f}")

    def stop(self):
        """策略结束时的处理 - 兼容backtrader"""
        # 记录最终资金
        self.final_capital = self.strategy.broker.getvalue()
        self.logger.info(f"性能分析器 - 结束回测，最终资金: {self.final_capital:.2f}")
        # 计算总收益率
        if self.initial_capital > 0:
            total_return = (self.final_capital / self.initial_capital) - 1
            self.logger.info(f"总收益率: {total_return * 100:.2f}%")

    def update(self, timestamp, strategy, broker):
        """更新分析数据
        
        Args:
            timestamp: 当前时间戳
            strategy: 策略实例
            broker: 经纪商实例
        """
        # 记录时间戳
        self.timestamps.append(timestamp)
        
        # 处理日期，确保同一天只计算一次
        current_date = timestamp.date()
        if self.last_date is None or current_date != self.last_date:
            # 新的交易日
            self.days_in_market += 1
            self.last_date = current_date
            self.logger.debug(f"计入新交易日: {current_date}, 当前交易天数: {self.days_in_market}")

        # 记录资金
        current_equity = broker.getvalue()
        self.equity_curve.append(current_equity)

        # 首次更新时记录初始资金
        if len(self.equity_curve) == 1:
            self.initial_capital = current_equity

        # 计算收益率
        if len(self.equity_curve) > 1:
            daily_return = (self.equity_curve[-1] / self.equity_curve[-2]) - 1
            self.returns.append(daily_return)

    def get_analysis(self):
        """获取分析结果 - 兼容backtrader接口
        
        Returns:
            Dict: 包含性能指标的字典
        """
        # 确保有足够的数据
        if not self.equity_curve or len(self.equity_curve) < 2:
            return {
                'total_return': 0.0,
                'annual_return': 0.0
            }

        # 计算最终资金（如果stop方法尚未运行）
        if self.final_capital == 0.0 and self.equity_curve:
            self.final_capital = self.equity_curve[-1]

        # 计算总收益率
        total_return = (self.final_capital / self.initial_capital) - 1 if self.initial_capital > 0 else 0

        # 计算年化收益率
        # 使用252个交易日作为一年
        trading_days_per_year = 252
        
        # 记录实际天数，避免日历天数和交易天数混淆
        self.logger.info(f"回测天数: {self.days_in_market}个交易日")
        
        # 正确年化计算: (1+r)^(252/天数) - 1
        if self.days_in_market > 0:
            annual_factor = trading_days_per_year / self.days_in_market
            annual_return = ((1 + total_return) ** annual_factor) - 1
        else:
            annual_return = 0.0
        
        self.logger.info(f"使用年化系数: {annual_factor:.2f}, 年化收益率: {annual_return*100:.2f}%")

        # 计算日收益率统计
        returns_array = np.array(self.returns)
        daily_return_mean = np.mean(returns_array) if len(returns_array) > 0 else 0
        daily_return_std = np.std(returns_array) if len(returns_array) > 1 else 0

        # 返回结果 - 不包含夏普比率，由Backtrader的SharpeRatio分析器提供
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'daily_return_mean': daily_return_mean,
            'daily_return_std': daily_return_std
        }

    def get_results(self) -> Dict[str, Any]:
        """获取性能分析结果（扩展版）
        
        Returns:
            Dict: 包含详细性能指标的字典
        """
        # 获取基本分析结果
        basic_results = self.get_analysis()
        
        # 添加更多详细信息
        results = {
            'performance': basic_results,
            'equity_curve': self.equity_curve,
            'returns': self.returns,
            'timestamps': self.timestamps,
            'days_in_market': self.days_in_market
        }

        # 记录日志
        total_return = basic_results.get('total_return', 0)
        annual_return = basic_results.get('annual_return', 0)
        
        self.logger.info(
            f"性能分析: 总收益率={total_return * 100:.2f}%, 年化收益率={annual_return * 100:.2f}%")

        return results

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
