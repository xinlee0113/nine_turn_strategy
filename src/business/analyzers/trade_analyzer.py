"""
交易分析器
用于分析交易数据，生成交易统计
"""
import logging
from typing import Dict, Any

from .base_analyzer import BaseAnalyzer


class TradeAnalyzer(BaseAnalyzer):
    """交易分析器，分析交易数据，生成交易统计"""

    def __init__(self):
        """初始化交易分析器"""
        self.logger = logging.getLogger(__name__)
        self.reset()

    def reset(self):
        """重置分析器状态"""
        self.trades = []  # 交易列表
        self.trade_stats = {
            'total': 0,  # 总交易数
            'won': 0,  # 盈利交易数
            'lost': 0,  # 亏损交易数
            'win_rate': 0.0,  # 胜率
            'avg_profit': 0.0,  # 平均利润
            'avg_loss': 0.0,  # 平均亏损
            'profit_factor': 0.0,  # 利润因子
            'expectancy': 0.0,  # 期望收益
            'largest_win': 0.0,  # 最大盈利
            'largest_loss': 0.0,  # 最大亏损
            'average_trade': 0.0,  # 平均交易
            'gross_profit': 0.0,  # 毛利
            'gross_loss': 0.0,  # 毛损
            'net_profit': 0.0  # 净利润
        }

    def initialize(self):
        """初始化分析器"""
        self.logger.info("初始化交易分析器")
        self.reset()

    def update(self, timestamp, strategy, broker):
        """更新分析数据
        
        Args:
            timestamp: 当前时间戳
            strategy: 策略实例
            broker: 经纪商实例
        """
        # 在这里，我们不做任何事情，因为我们只在有交易时才记录数据
        pass

    def next(self):
        """处理下一个数据点"""
        # 为了兼容旧接口，保留该方法
        pass

    def get_analysis(self):
        """获取分析结果
        
        Returns:
            Dict: 包含交易统计的字典
        """
        return self.get_results()

    def addindicator(self, indicator_name, indicator_value):
        """
        添加自定义指标
        
        Args:
            indicator_name: 指标名称
            indicator_value: 指标值
        """
        # 这是一个空方法，用于兼容可能的调用
        self.logger.debug(f"接收到指标: {indicator_name}={indicator_value}")
        # 在这里可以实现自定义指标的处理逻辑
        return

    def on_trade(self, trade):
        """处理交易事件
        
        Args:
            trade: 交易对象
        """
        self.logger.debug(f"收到交易: {trade}")
        self.trades.append(trade)

    def analyze(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析交易结果，符合回测流程图中的设计
        
        Args:
            results: 回测引擎返回的原始结果
            
        Returns:
            Dict[str, Any]: 经过分析的回测结果
        """
        self.logger.info("分析交易结果")

        # 计算交易统计
        analysis_results = self.get_results()

        # 合并原始回测结果和新的分析结果
        if 'trades' not in results:
            results['trades'] = analysis_results.get('trades', {})

        self.logger.info("完成交易结果分析")
        return results

    def get_results(self) -> Dict[str, Any]:
        """获取交易分析结果
        
        Returns:
            Dict: 包含交易统计的字典
        """
        results = {}

        # 确保有足够的数据
        if not self.trades:
            self.logger.warning("没有交易数据进行分析")
            return {'trades': self.trade_stats}

        # 提取交易统计
        total_trades = len(self.trades)
        profitable_trades = [t for t in self.trades if t.profit > 0]
        losing_trades = [t for t in self.trades if t.profit <= 0]

        won = len(profitable_trades)
        lost = len(losing_trades)
        win_rate = won / total_trades if total_trades > 0 else 0

        gross_profit = sum(t.profit for t in profitable_trades)
        gross_loss = sum(t.profit for t in losing_trades)
        net_profit = gross_profit + gross_loss

        avg_profit = gross_profit / won if won > 0 else 0
        avg_loss = gross_loss / lost if lost > 0 else 0

        largest_win = max(t.profit for t in profitable_trades) if profitable_trades else 0
        largest_loss = min(t.profit for t in losing_trades) if losing_trades else 0

        average_trade = net_profit / total_trades if total_trades > 0 else 0

        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else 0

        # 预期收益 = 胜率 * 平均盈利 + (1 - 胜率) * 平均亏损
        expectancy = (win_rate * avg_profit) + ((1 - win_rate) * avg_loss)

        # 更新交易统计
        self.trade_stats = {
            'total': total_trades,
            'won': won,
            'lost': lost,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'average_trade': average_trade,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'net_profit': net_profit
        }

        # 记录日志
        self.logger.info(
            f"交易分析: 总交易={total_trades}, 盈利={won}, 亏损={lost}, 胜率={win_rate * 100:.2f}%, 利润因子={profit_factor:.2f}")

        results['trades'] = self.trade_stats
        return results
