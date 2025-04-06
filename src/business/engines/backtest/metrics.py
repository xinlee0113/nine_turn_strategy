from typing import Dict, Any, List
import pandas as pd
import numpy as np

class PerformanceMetrics:
    """性能指标计算器"""
    
    def __init__(self, equity: List[float], trades: List[Dict[str, Any]]):
        """
        初始化性能指标计算器
        
        Args:
            equity: 权益曲线
            trades: 交易记录
        """
        self.equity = pd.Series(equity)
        self.trades = pd.DataFrame(trades)
    
    def calculate(self) -> Dict[str, float]:
        """
        计算性能指标
        
        Returns:
            性能指标
        """
        metrics = {
            'returns': self._calculate_returns(),
            'risk': self._calculate_risk(),
            'trades': self._calculate_trade_metrics()
        }
        
        return metrics
    
    def _calculate_returns(self) -> Dict[str, float]:
        """计算收益指标"""
        returns = self.equity.pct_change()
        
        return {
            'total_return': (self.equity.iloc[-1] / self.equity.iloc[0]) - 1,
            'annual_return': (1 + returns.mean()) ** 252 - 1,
            'daily_return_mean': returns.mean(),
            'daily_return_std': returns.std()
        }
    
    def _calculate_risk(self) -> Dict[str, float]:
        """计算风险指标"""
        returns = self.equity.pct_change()
        
        return {
            'annual_volatility': returns.std() * np.sqrt(252),
            'sharpe_ratio': self._calculate_sharpe_ratio(returns),
            'sortino_ratio': self._calculate_sortino_ratio(returns),
            'max_drawdown': self._calculate_max_drawdown()
        }
    
    def _calculate_trade_metrics(self) -> Dict[str, float]:
        """计算交易指标"""
        if self.trades.empty:
            return {}
            
        return {
            'total_trades': len(self.trades),
            'winning_trades': len(self.trades[self.trades['profit'] > 0]),
            'losing_trades': len(self.trades[self.trades['profit'] < 0]),
            'win_rate': len(self.trades[self.trades['profit'] > 0]) / len(self.trades),
            'profit_factor': self._calculate_profit_factor()
        }
    
    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """计算夏普比率"""
        excess_returns = returns - 0.02/252  # 假设无风险利率为2%
        return np.sqrt(252) * excess_returns.mean() / excess_returns.std()
    
    def _calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """计算索提诺比率"""
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return np.nan
        downside_std = downside_returns.std()
        if downside_std == 0:
            return np.nan
        return (returns.mean() * 252) / (downside_std * np.sqrt(252))
    
    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        cummax = self.equity.expanding().max()
        drawdown = (self.equity - cummax) / cummax
        return drawdown.min()
    
    def _calculate_profit_factor(self) -> float:
        """计算盈亏比"""
        if self.trades.empty:
            return 0.0
            
        winning_trades = self.trades[self.trades['profit'] > 0]['profit'].sum()
        losing_trades = abs(self.trades[self.trades['profit'] < 0]['profit'].sum())
        
        if losing_trades == 0:
            return np.inf
            
        return winning_trades / losing_trades

def calculate_metrics(trades: List[Dict[str, Any]], equity_curve: pd.DataFrame) -> Dict[str, Any]:
    """计算回测指标
    
    Args:
        trades: 交易记录列表
        equity_curve: 权益曲线数据框
        
    Returns:
        包含各项指标的字典
    """
    if equity_curve.empty:
        return {}
        
    # 计算收益率
    equity = equity_curve['equity']
    total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
    
    # 计算年化收益率
    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0
    
    # 计算日收益率
    daily_returns = equity.pct_change().dropna()
    daily_return_mean = daily_returns.mean()
    daily_return_std = daily_returns.std()
    
    # 计算年化波动率
    annual_volatility = daily_return_std * np.sqrt(252)
    
    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'daily_return_mean': daily_return_mean,
        'daily_return_std': daily_return_std,
        'annual_volatility': annual_volatility
    } 