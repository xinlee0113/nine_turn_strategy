"""
系统质量指标(SQN)分析器
用于计算策略的系统质量指标
"""
import logging
from typing import Dict, Any, List
import numpy as np

from .base_analyzer import BaseAnalyzer


class SQNAnalyzer(BaseAnalyzer):
    """系统质量指标分析器，计算策略的SQN值"""

    def __init__(self):
        """初始化SQN分析器"""
        self.logger = logging.getLogger(__name__)
        self.reset()

    def reset(self):
        """重置分析器状态"""
        self.trades = []  # 交易记录，记录每笔交易的盈亏
        self.sqn = 0.0  # 系统质量指标值

    def initialize(self):
        """初始化分析器"""
        self.logger.info("初始化SQN分析器")
        self.reset()

    def update(self, timestamp, strategy, broker):
        """更新分析数据
        
        Args:
            timestamp: 当前时间戳
            strategy: 策略实例
            broker: 经纪商实例
        """
        # 此方法主要用于接收每个周期的市场数据更新
        # SQN主要基于交易结果计算，此处不需要实现
        pass

    def next(self):
        """处理下一个数据点"""
        # 为了兼容旧接口，保留该方法
        pass

    def on_trade(self, trade):
        """处理交易事件，记录每笔交易的盈亏
        
        Args:
            trade: 交易对象，包含交易盈亏等信息
        """
        if 'pnl' in trade:
            self.trades.append(trade['pnl'])
            self.logger.debug(f"收到交易盈亏: {trade['pnl']}")

    def get_analysis(self):
        """获取分析结果
        
        Returns:
            Dict: 包含SQN值的字典
        """
        return self.get_results()

    def analyze(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析回测结果
        
        Args:
            results: 回测引擎返回的原始结果
            
        Returns:
            Dict[str, Any]: 添加SQN后的结果
        """
        self.logger.info("分析SQN指标")

        # 计算SQN
        analysis_results = self.get_results()
        
        # 将SQN添加到性能指标中
        if 'performance' not in results:
            results['performance'] = {}
        
        results['performance']['sqn'] = analysis_results['sqn']
        
        self.logger.info(f"SQN计算完成: {results['performance']['sqn']:.4f}")
        return results

    def get_results(self) -> Dict[str, Any]:
        """获取SQN分析结果
        
        Returns:
            Dict: 包含SQN值的字典
        """
        results = {'sqn': 0.0}
        
        # 确保有足够的交易记录
        if len(self.trades) < 2:
            self.logger.warning("交易记录不足，无法计算SQN")
            return results
        
        # 计算SQN: sqrt(交易次数) * (平均收益 / 标准差)
        trades_array = np.array(self.trades)
        mean_pnl = np.mean(trades_array)
        std_pnl = np.std(trades_array, ddof=1)  # 使用样本标准差
        
        # 避免除以0
        if std_pnl > 0:
            self.sqn = np.sqrt(len(self.trades)) * (mean_pnl / std_pnl)
            results['sqn'] = self.sqn
        
        self.logger.info(f"SQN: {self.sqn:.4f}, 基于{len(self.trades)}笔交易")
        return results 