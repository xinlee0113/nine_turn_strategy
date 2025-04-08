from typing import Dict, Any, List

import numpy as np
import pandas as pd

from .metrics import calculate_metrics


class BacktestAnalyzer:
    """回测分析器，用于分析回测结果"""

    def __init__(self, trades: List[Dict[str, Any]], equity_curve: pd.DataFrame):
        """初始化分析器
        
        Args:
            trades: 交易记录列表
            equity_curve: 权益曲线数据框
        """
        self.trades = trades
        self.equity_curve = equity_curve

    def analyze(self) -> Dict[str, Any]:
        """分析回测结果
        
        Returns:
            包含各项分析指标的字典
        """
        # 计算基本指标
        metrics = calculate_metrics(self.trades, self.equity_curve)

        # 计算交易统计
        trade_stats = self._calculate_trade_stats()

        # 计算风险指标
        risk_metrics = self._calculate_risk_metrics()

        # 合并所有指标
        results = {
            **metrics,
            **trade_stats,
            **risk_metrics
        }

        return results

    def _calculate_trade_stats(self) -> Dict[str, Any]:
        """计算交易统计指标"""
        if not self.trades:
            return {}

        # 计算胜率
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        win_rate = len(winning_trades) / len(self.trades)

        # 计算平均盈亏
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0

        # 计算盈亏比
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')

        return {
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades)
        }

    def _calculate_risk_metrics(self) -> Dict[str, Any]:
        """计算风险指标"""
        if self.equity_curve.empty:
            return {}

        # 计算最大回撤
        equity = self.equity_curve['equity']
        rolling_max = equity.expanding().max()
        drawdowns = (equity - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()

        # 计算夏普比率
        returns = equity.pct_change().dropna()
        sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std() if len(returns) > 0 else 0

        # 计算索提诺比率
        downside_returns = returns[returns < 0]
        sortino_ratio = np.sqrt(252) * returns.mean() / downside_returns.std() if len(downside_returns) > 0 else 0

        return {
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio
        }
