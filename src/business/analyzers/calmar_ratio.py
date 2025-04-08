"""
卡尔玛比率分析器
计算策略的卡尔玛比率（Calmar Ratio）
卡尔玛比率 = 年化收益率 / 最大回撤
"""
import logging
from typing import Dict, Any

from .base_analyzer import BaseAnalyzer


class CalmarRatio(BaseAnalyzer):
    """卡尔玛比率分析器"""

    # 定义参数
    params = (
        ('period', 252),  # 年化周期，默认252个交易日
    )

    def initialize(self):
        """初始化分析器"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("初始化卡尔玛比率分析器")
        self.reset()

    def reset(self):
        """重置分析器状态"""
        self.equity_curve = []  # 权益曲线
        self.timestamps = []  # 时间戳
        self.drawdowns = []  # 回撤序列
        self.current_peak = 0.0  # 当前峰值
        self.max_drawdown = 0.0  # 最大回撤
        self.annual_return = 0.0  # 年化收益率
        self.calmar_ratio = 0.0  # 卡尔玛比率

    def start(self):
        """策略开始时的处理 - 兼容backtrader"""
        super().start()
        # 记录初始值
        self.current_peak = self.strategy.broker.getvalue()
        self.logger.info(f"卡尔玛比率分析器 - 开始回测，初始值: {self.current_peak:.2f}")

    def stop(self):
        """策略结束时的处理 - 兼容backtrader"""
        # 计算卡尔玛比率
        self._calculate_calmar_ratio()
        
        # 记录最终结果
        self.logger.info(f"卡尔玛比率分析器 - 结束回测，卡尔玛比率: {self.calmar_ratio:.4f}")

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

    def _calculate_calmar_ratio(self):
        """计算卡尔玛比率"""
        # 检查是否有足够的数据
        if not self.equity_curve or len(self.equity_curve) < 2:
            self.calmar_ratio = 0.0
            return
            
        # 如果性能分析器可用，优先使用其年化收益率
        if hasattr(self.strategy, 'analyzers') and hasattr(self.strategy.analyzers, 'performanceanalyzer'):
            perf_analyzer = self.strategy.analyzers.performanceanalyzer
            self.annual_return = perf_analyzer.get_analysis().get('annual_return', 0)
        else:
            # 手动计算年化收益率
            initial_value = self.equity_curve[0]
            final_value = self.equity_curve[-1]
            
            # 总收益率
            total_return = (final_value / initial_value) - 1 if initial_value > 0 else 0
            
            # 换算为年化收益率
            # 假设周期单位是天，转换为年化
            periods = len(self.equity_curve)
            years = periods / self.p.period if periods > 0 else 1  # 避免除以零
            
            # 年化收益率计算公式：(1+r)^(1/t) - 1
            self.annual_return = (1 + total_return) ** (1 / max(years, 0.01)) - 1
            
        # 计算卡尔玛比率
        if self.max_drawdown > 0:
            self.calmar_ratio = self.annual_return / self.max_drawdown
        else:
            # 如果最大回撤为0，卡尔玛比率为无穷大，设为一个较大的数
            self.calmar_ratio = 100.0 if self.annual_return > 0 else 0.0

    def get_analysis(self):
        """获取分析结果 - 兼容backtrader接口
        
        Returns:
            Dict: 包含卡尔玛比率的字典
        """
        # 确保卡尔玛比率已计算
        if self.calmar_ratio == 0 and len(self.equity_curve) > 1:
            self._calculate_calmar_ratio()
            
        return {
            'calmar_ratio': self.calmar_ratio,
            'max_drawdown': self.max_drawdown,
            'annual_return': self.annual_return
        }

    def get_results(self) -> Dict[str, Any]:
        """获取卡尔玛比率分析结果
        
        Returns:
            Dict: 包含卡尔玛比率的字典
        """
        # 获取基本分析结果
        basic_results = self.get_analysis()
        
        # 记录日志
        calmar_ratio = basic_results.get('calmar_ratio', 0)
        max_drawdown = basic_results.get('max_drawdown', 0)
        annual_return = basic_results.get('annual_return', 0)
        
        self.logger.info(
            f"卡尔玛比率分析: 卡尔玛比率={calmar_ratio:.4f}, "
            f"最大回撤={max_drawdown * 100:.2f}%, "
            f"年化收益率={annual_return * 100:.2f}%")

        return {
            'risk': {
                'calmar_ratio': calmar_ratio,
                'max_drawdown': max_drawdown
            },
            'performance': {
                'annual_return': annual_return
            }
        }

    def analyze(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """分析回测结果，符合回测流程图中的设计
        
        Args:
            results: 回测引擎返回的原始结果
            
        Returns:
            Dict[str, Any]: 经过分析的回测结果
        """
        self.logger.info("分析卡尔玛比率")

        # 获取分析结果
        analysis_results = self.get_results()
        
        # 合并到现有结果中
        if 'risk' not in results:
            results['risk'] = {}
            
        results['risk']['calmar_ratio'] = analysis_results['risk']['calmar_ratio']
        
        self.logger.info("完成卡尔玛比率分析")
        return results 