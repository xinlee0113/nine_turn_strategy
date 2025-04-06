import backtrader as bt
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from src.strategy.base import BaseStrategy

class BacktestEngine:
    """回测引擎 (基于backtrader)"""
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化回测引擎
        
        Args:
            params: 回测参数
        """
        self.params = params or {}
        self.initial_capital = params.get('initial_capital', 1000000)
        self.commission = params.get('commission', 0.0003)
        self.slippage = params.get('slippage', 0.0001)
        
        # 创建回测引擎
        self.cerebro = bt.Cerebro()
        
        # 设置初始资金
        self.cerebro.broker.setcash(self.initial_capital)
        
        # 设置手续费
        self.cerebro.broker.setcommission(commission=self.commission)
        
        # 设置滑点
        self.cerebro.broker.set_slippage_perc(self.slippage)
        
        # 添加分析器
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    def run(self, strategy: BaseStrategy, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            strategy: 交易策略
            data: 市场数据
            
        Returns:
            回测结果
        """
        # 添加数据
        for symbol, df in data.items():
            # 转换数据格式
            data_feed = bt.feeds.PandasData(
                dataname=df,
                datetime='datetime',
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
                openinterest=-1
            )
            self.cerebro.adddata(data_feed, name=symbol)
        
        # 添加策略
        self.cerebro.addstrategy(strategy)
        
        # 运行回测
        results = self.cerebro.run()
        
        # 获取回测结果
        strat = results[0]
        
        # 计算回测指标
        returns = strat.analyzers.returns.get_analysis()
        sharpe = strat.analyzers.sharpe.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        trades = strat.analyzers.trades.get_analysis()
        
        # 整理结果
        backtest_results = {
            'returns': {
                'total_return': returns['rtot'],
                'annual_return': returns['rnorm100'],
                'daily_return_mean': returns['ravg'],
                'daily_return_std': returns['rnorm100']
            },
            'risk': {
                'sharpe_ratio': sharpe['sharperatio'],
                'max_drawdown': drawdown['max']['drawdown'],
                'max_drawdown_length': drawdown['max']['len']
            },
            'trades': {
                'total': trades['total']['total'],
                'won': trades['won']['total'],
                'lost': trades['lost']['total'],
                'win_rate': trades['won']['total'] / trades['total']['total'] if trades['total']['total'] > 0 else 0,
                'pnl_net': trades['pnl']['net']['total'],
                'pnl_avg': trades['pnl']['net']['average']
            }
        }
        
        return backtest_results
    
    def plot(self) -> None:
        """绘制回测结果"""
        self.cerebro.plot() 