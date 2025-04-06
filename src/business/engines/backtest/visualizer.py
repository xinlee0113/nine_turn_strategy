from typing import Dict, Any, List
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

class BacktestVisualizer:
    """回测结果可视化器"""
    
    def __init__(self, equity: List[float], trades: List[Dict[str, Any]]):
        """
        初始化可视化器
        
        Args:
            equity: 权益曲线
            trades: 交易记录
        """
        self.equity = pd.Series(equity)
        self.trades = pd.DataFrame(trades)
        
        # 设置绘图风格
        plt.style.use('seaborn')
        sns.set_palette('husl')
    
    def plot_equity_curve(self, save_path: str = None) -> None:
        """
        绘制权益曲线
        
        Args:
            save_path: 保存路径，如果为None则显示图像
        """
        plt.figure(figsize=(12, 6))
        plt.plot(self.equity.index, self.equity.values, label='Equity')
        plt.title('Equity Curve')
        plt.xlabel('Date')
        plt.ylabel('Equity')
        plt.legend()
        plt.grid(True)
        
        if save_path:
            plt.savefig(save_path)
            plt.close()
        else:
            plt.show()
    
    def plot_drawdown(self, save_path: str = None) -> None:
        """
        绘制回撤曲线
        
        Args:
            save_path: 保存路径，如果为None则显示图像
        """
        cummax = self.equity.expanding().max()
        drawdown = (self.equity - cummax) / cummax
        
        plt.figure(figsize=(12, 6))
        plt.plot(drawdown.index, drawdown.values, label='Drawdown')
        plt.title('Drawdown Curve')
        plt.xlabel('Date')
        plt.ylabel('Drawdown')
        plt.legend()
        plt.grid(True)
        
        if save_path:
            plt.savefig(save_path)
            plt.close()
        else:
            plt.show()
    
    def plot_monthly_returns(self, save_path: str = None) -> None:
        """
        绘制月度收益热力图
        
        Args:
            save_path: 保存路径，如果为None则显示图像
        """
        returns = self.equity.pct_change()
        monthly_returns = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
        monthly_returns = monthly_returns.unstack()
        
        plt.figure(figsize=(12, 6))
        sns.heatmap(monthly_returns, annot=True, fmt='.2%', cmap='RdYlGn')
        plt.title('Monthly Returns Heatmap')
        plt.xlabel('Month')
        plt.ylabel('Year')
        
        if save_path:
            plt.savefig(save_path)
            plt.close()
        else:
            plt.show()
    
    def plot_trade_distribution(self, save_path: str = None) -> None:
        """
        绘制交易分布图
        
        Args:
            save_path: 保存路径，如果为None则显示图像
        """
        if self.trades.empty:
            return
            
        plt.figure(figsize=(12, 6))
        sns.histplot(self.trades['profit'], bins=50)
        plt.title('Trade Profit Distribution')
        plt.xlabel('Profit')
        plt.ylabel('Count')
        plt.grid(True)
        
        if save_path:
            plt.savefig(save_path)
            plt.close()
        else:
            plt.show()
    
    def plot_all(self, save_dir: str = None) -> None:
        """
        绘制所有图表
        
        Args:
            save_dir: 保存目录，如果为None则显示图像
        """
        if save_dir:
            self.plot_equity_curve(f'{save_dir}/equity_curve.png')
            self.plot_drawdown(f'{save_dir}/drawdown.png')
            self.plot_monthly_returns(f'{save_dir}/monthly_returns.png')
            self.plot_trade_distribution(f'{save_dir}/trade_distribution.png')
        else:
            self.plot_equity_curve()
            self.plot_drawdown()
            self.plot_monthly_returns()
            self.plot_trade_distribution() 