"""
回测引擎实现
"""
import logging
from typing import Dict, Any
from datetime import datetime

import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

from src.infrastructure.constants.const import DEFAULT_INITIAL_CAPITAL, DEFAULT_COMMISSION_RATE
from ..base_engine import BaseEngine
from ...analyzers.calmar_ratio import CalmarRatio
from ...analyzers.performance_analyzer import PerformanceAnalyzer
from ...analyzers.risk_analyzer import RiskAnalyzer
from ...analyzers.custom_drawdown import CustomDrawDown
from ...analyzers.trade_analyzer import TradeAnalyzer
from ...analyzers.position_analyzer import PositionAnalyzer
from ...analyzers.sortino_ratio import SortinoRatio  # 导入自定义的SortinoRatio分析器


class BacktestEngine(BaseEngine):
    """回测引擎"""

    def __init__(self, config):
        """初始化回测引擎"""
        super().__init__(config)
        self.logger = logging.getLogger(__name__)

        # 创建backtrader的cerebro引擎
        self.cerebro = bt.Cerebro()

        # 回测组件
        self.strategy = None
        self.data = None
        self.broker = None

        # 分析器列表
        self.analyzers = []
        self.analyzer_classes = [
            PerformanceAnalyzer,
            RiskAnalyzer,
            TradeAnalyzer,
            PositionAnalyzer,
            CustomDrawDown,
            CalmarRatio
        ]

        # 回测状态
        self.is_running = False
        self.current_datetime = None
        self.results = {}
        
        # 绘图设置
        self.plot_enabled = False
        self.plot_options = {}

    def set_strategy(self, strategy_class) -> None:
        """设置策略类
        
        Args:
            strategy_class: 策略类（不是实例）
        """
        self.strategy = strategy_class
        self.logger.info(f"设置策略: {strategy_class.__name__}")

    def set_data(self, data: pd.DataFrame) -> None:
        """设置数据源"""
        self.data = data
        if data is not None:
            self.logger.info(f"设置数据源: {len(data)} 个数据点")

            # 将pandas数据转换为backtrader的数据格式
            data_feed = self._convert_data_to_bt_feed(data)
            self.cerebro.adddata(data_feed)
        else:
            self.logger.warning("设置了空数据源")

    def _convert_data_to_bt_feed(self, data: pd.DataFrame) -> bt.feeds.PandasData:
        """将pandas数据转换为backtrader的数据格式"""
        # 确保数据索引是日期时间
        if not isinstance(data.index, pd.DatetimeIndex):
            self.logger.warning("数据索引不是DatetimeIndex类型，尝试转换")
            data.index = pd.to_datetime(data.index)

        # 创建backtrader的数据源
        try:
            data_feed = bt.feeds.PandasData(
                dataname=data,
                datetime=None,  # 使用索引作为日期时间
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
                openinterest=-1  # 不使用持仓量
            )
            return data_feed
        except TypeError:
            # 适配不同版本的backtrader
            self.logger.info("使用替代方法创建PandasData")
            return bt.feeds.PandasData(data=data)

    def set_broker(self, broker) -> None:
        """设置回测Broker"""
        self.broker = broker
        self.logger.info(f"设置Broker: {broker.__class__.__name__}")

        # 设置backtrader的broker参数
        initial_capital = DEFAULT_INITIAL_CAPITAL
        commission = DEFAULT_COMMISSION_RATE
        
        # 尝试从配置中获取参数
        if hasattr(self.config, 'get_params'):
            params = self.config.get_params()
            initial_capital = params.get('initial_capital', DEFAULT_INITIAL_CAPITAL)
            commission = params.get('commission', DEFAULT_COMMISSION_RATE)
        elif isinstance(self.config, dict):
            initial_capital = self.config.get('initial_capital', DEFAULT_INITIAL_CAPITAL)
            commission = self.config.get('commission', DEFAULT_COMMISSION_RATE)
            
        self.cerebro.broker.setcash(initial_capital)
        self.cerebro.broker.setcommission(commission=commission)

    def add_analyzer(self, analyzer_class) -> None:
        """添加分析器类
        
        Args:
            analyzer_class: 分析器类（不是实例）
        """
        if analyzer_class not in self.analyzer_classes:
            self.analyzer_classes.append(analyzer_class)
            self.logger.info(f"添加分析器类: {analyzer_class.__name__}")

    def _add_bt_analyzers(self):
        """添加backtrader分析器 - 在策略添加后调用"""
        # 确保策略已经添加
        if not hasattr(self, 'strategy') or self.strategy is None:
            self.logger.warning("策略未设置，无法添加分析器")
            return

        # 添加自定义分析器类
        for analyzer_class in self.analyzer_classes:
            analyzer_name = analyzer_class.__name__.lower()
            try:
                self.cerebro.addanalyzer(analyzer_class, _name=analyzer_name)
            except Exception as e:
                self.logger.error(f"添加分析器 {analyzer_class.__name__} 失败: {e}")

        # 添加backtrader内置分析器
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
        self.cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        
        # 添加自定义的索提诺比率分析器
        try:
            self.cerebro.addanalyzer(SortinoRatio, _name='sortino', 
                                  riskfreerate=0.0, annualize=True)
        except Exception as e:
            self.logger.warning(f"无法添加索提诺比率分析器: {e}")

    def set_plot_options(self, enabled=True, **kwargs):
        """设置绘图选项
        
        Args:
            enabled: 是否启用绘图
            **kwargs: 绘图选项，如style、width、barup等
        """
        self.plot_enabled = enabled
        self.plot_options = kwargs
        self.logger.info(f"{'启用' if enabled else '禁用'}绘图功能")
        if enabled and kwargs:
            self.logger.info(f"设置绘图选项: {kwargs}")
            
    def run(self) -> Dict[str, Any]:
        """运行回测"""
        self.logger.info("开始运行回测")
        self.is_running = True

        # 检查组件是否齐全
        if not self._check_components():
            self.is_running = False
            return {}

        # 设置cerebro选项，控制标准观察器
        show_trades = self.plot_options.get('show_trades', False)
        if not show_trades:
            self.cerebro.stdstats = False
            # 手动添加需要的观察器
            self.cerebro.addobserver(bt.observers.Broker)
            self.cerebro.addobserver(bt.observers.BuySell)

        # 添加策略到cerebro
        strategy_params = {}
        if hasattr(self.config, 'get') and callable(self.config.get):
            strategy_params = self.config.get('strategy', {})

        self.cerebro.addstrategy(self.strategy, **strategy_params)
        
        # 添加分析器 - 必须在添加策略后调用
        self._add_bt_analyzers()

        # 运行回测
        self.logger.info("开始执行backtrader回测")
        bt_results = self.cerebro.run()

        # 提取回测结果
        if len(bt_results) > 0:
            bt_strategy = bt_results[0]
            self.results = self._extract_results(bt_strategy)

        # 如果启用了绘图功能，则绘制图表
        if self.plot_enabled:
            self.logger.info("生成回测图表")
            try:
                # 过滤掉非绘图相关的选项
                plot_options = {k: v for k, v in self.plot_options.items() 
                             if k not in ['show_trades']}
                
                # 使用绘图管理器绘制图表
                from src.application.ui.plot_manager import PlotManager
                plot_manager = PlotManager()
                plot_manager.plot_cerebro(self.cerebro, **plot_options)
                self.logger.info("图表生成成功")
            except Exception as e:
                self.logger.error(f"图表生成失败: {str(e)}")

        # 完成回测
        self.is_running = False

        # 返回结果
        return self.results

    def _check_components(self) -> bool:
        """检查回测组件是否齐全"""
        if self.strategy is None:
            self.logger.error("策略未设置")
            return False

        if self.data is None or self.data.empty:
            self.logger.error("数据未设置或为空")
            return False

        return True

    def _extract_results(self, strategy) -> Dict[str, Any]:
        """从backtrader策略中提取结果"""
        results = {}

        # 获取收益率和夏普比率
        returns = strategy.analyzers.returns.get_analysis()
        sharpe = strategy.analyzers.sharpe.get_analysis()

        # 获取自定义分析器结果
        for analyzer_class in self.analyzer_classes:
            analyzer_name = analyzer_class.__name__.lower()
            if hasattr(strategy.analyzers, analyzer_name):
                analyzer = getattr(strategy.analyzers, analyzer_name)
                try:
                    analyzer_results = analyzer.get_analysis()
                    results[analyzer_name] = analyzer_results
                except Exception as e:
                    self.logger.error(f"获取分析器 {analyzer_name} 结果失败: {e}")

        # 获取交易分析
        trades = strategy.analyzers.trade_analyzer.get_analysis()
        
        # 获取SQN和Sortino比率
        sqn_result = {}
        sortino_result = {}
        try:
            sqn_result = strategy.analyzers.sqn.get_analysis()
            sortino_result = strategy.analyzers.sortino.get_analysis()
        except Exception as e:
            self.logger.warning(f"获取SQN或Sortino分析结果失败: {e}")

        # 提取基本交易统计
        trade_stats = self._extract_trade_stats(trades)
        
        # 从自定义交易分析器中获取平均每天交易次数
        if 'tradeanalyzer' in results:
            tradeanalyzer_results = results['tradeanalyzer']
            # 检查自定义交易分析器结果中是否包含avg_trades_per_day
            if 'avg_trades_per_day' in tradeanalyzer_results:
                trade_stats['avg_trades_per_day'] = tradeanalyzer_results['avg_trades_per_day']
            # 如果自定义分析器结果嵌套在trades字段中
            elif 'trades' in tradeanalyzer_results and 'avg_trades_per_day' in tradeanalyzer_results['trades']:
                trade_stats['avg_trades_per_day'] = tradeanalyzer_results['trades']['avg_trades_per_day']

        # 组织结果
        results.update({
            'returns': returns,
            'sharpe': sharpe,
            'trades': trade_stats,
            'sqn': sqn_result,
            'sortino': sortino_result
        })

        # 记录摘要信息
        self._log_summary(returns, sharpe, trades, sqn_result, sortino_result)

        return results

    def _extract_trade_stats(self, trades) -> Dict[str, Any]:
        """从交易分析结果中提取详细的交易统计"""
        # 基础交易统计
        trade_stats = {
            'total': trades.get('total', {}).get('total', 0),
            'won': trades.get('won', {}).get('total', 0),
            'lost': trades.get('lost', {}).get('total', 0),
            'pnl_net': trades.get('pnl', {}).get('net', {}).get('total', 0),
            'pnl_avg': trades.get('pnl', {}).get('net', {}).get('average', 0),
        }
        
        # 计算胜率
        if trade_stats['total'] > 0:
            trade_stats['win_rate'] = trade_stats['won'] / trade_stats['total']
        else:
            trade_stats['win_rate'] = 0
            
        # 提取更多详细指标(如果有)
        # 最大盈亏
        if 'pnl' in trades and 'net' in trades['pnl']:
            net_pnl = trades['pnl']['net']
            if 'max' in net_pnl:
                trade_stats['max_profit'] = net_pnl.get('max', 0)
            if 'min' in net_pnl:
                trade_stats['max_loss'] = net_pnl.get('min', 0)
                
        # 平均盈亏
        if 'won' in trades and 'pnl' in trades.get('won', {}):
            trade_stats['avg_profit'] = trades['won'].get('pnl', {}).get('average', 0)
        
        if 'lost' in trades and 'pnl' in trades.get('lost', {}):
            trade_stats['avg_loss'] = trades['lost'].get('pnl', {}).get('average', 0)
        
        # 盈亏比和盈利因子
        if trade_stats.get('avg_loss', 0) != 0:
            avg_profit = trade_stats.get('avg_profit', 0)
            avg_loss = abs(trade_stats.get('avg_loss', 0))
            if avg_loss > 0:
                trade_stats['win_loss_ratio'] = avg_profit / avg_loss
            else:
                trade_stats['win_loss_ratio'] = 0
                
        gross_profit = trades.get('won', {}).get('pnl', {}).get('total', 0)
        gross_loss = abs(trades.get('lost', {}).get('pnl', {}).get('total', 0))
        
        if gross_loss > 0:
            trade_stats['profit_factor'] = gross_profit / gross_loss
        else:
            trade_stats['profit_factor'] = 0
            
        # 连续盈亏
        if 'streak' in trades:
            streak = trades['streak']
            if 'won' in streak:
                trade_stats['max_consecutive_wins'] = streak['won'].get('longest', 0)
            if 'lost' in streak:
                trade_stats['max_consecutive_losses'] = streak['lost'].get('longest', 0)
                
        # 期望值
        if (trade_stats.get('win_rate', 0) > 0 and 
            'avg_profit' in trade_stats and 
            'avg_loss' in trade_stats):
            win_rate = trade_stats['win_rate']
            avg_profit = trade_stats['avg_profit']
            avg_loss = trade_stats['avg_loss']
            trade_stats['expectancy'] = (win_rate * avg_profit) + ((1 - win_rate) * avg_loss)
            
        return trade_stats

    def analyze(self) -> Dict[str, Any]:
        """分析回测结果"""
        self.logger.info("分析回测结果")
        return self.results

    def _log_summary(self, returns, sharpe, trades, sqn_result, sortino_result) -> None:
        """记录回测摘要"""
        if not self.results:
            self.logger.warning("没有回测结果可记录")
            return

        self.logger.info("=" * 30)
        self.logger.info("回测摘要")
        self.logger.info("=" * 30)

        # 提取关键指标
        if 'returns' in self.results:
            perf = self.results['returns']
            self.logger.info("性能指标:")
            # 确保值不为None再进行格式化
            total_return = perf.get('rtot', 0) or 0
            annual_return = perf.get('rnorm', 0) or 0

            self.logger.info(f"- 总收益率: {total_return * 100:.2f}%")
            self.logger.info(f"- 年化收益率: {annual_return * 100:.2f}%")

        if 'sharpe' in self.results:
            risk = self.results['sharpe']
            self.logger.info("风险指标:")
            # 确保值不为None再进行格式化
            sharpe_ratio = risk.get('sharperatio', 0) or 0

            self.logger.info(f"- 夏普比率: {sharpe_ratio:.4f}")
            
        # 记录卡尔玛比率
        if 'calmarratio' in self.results:
            calmar = self.results['calmarratio']
            # 确保值不为None再进行格式化
            calmar_ratio = calmar.get('calmar_ratio', 0) or 0
            self.logger.info(f"- 卡尔玛比率: {calmar_ratio:.4f}")

        if 'trades' in self.results:
            trades = self.results['trades']
            self.logger.info("交易统计:")
            # 确保值不为None再进行格式化
            total = trades.get('total', 0) or 0
            won = trades.get('won', 0) or 0
            lost = trades.get('lost', 0) or 0
            win_rate = trades.get('win_rate', 0) or 0
            pnl_avg = trades.get('pnl_avg', 0) or 0
            pnl_net = trades.get('pnl_net', 0) or 0
            avg_trades_per_day = trades.get('avg_trades_per_day', 0) or 0

            self.logger.info(f"- 总交易次数: {total}")
            self.logger.info(f"- 盈利交易: {won}")
            self.logger.info(f"- 亏损交易: {lost}")
            self.logger.info(f"- 胜率: {win_rate * 100:.2f}%")
            self.logger.info(f"- 平均收益: {pnl_avg:.4f}")
            self.logger.info(f"- 总净利润: {pnl_net:.4f}")
            self.logger.info(f"- 平均每天交易次数: {avg_trades_per_day:.2f}")

        if 'sqn' in self.results:
            sqn = self.results['sqn']
            self.logger.info("SQN指标:")
            # 确保值不为None再进行格式化
            sqn_value = sqn.get('sqn', 0) or 0

            self.logger.info(f"- SQN: {sqn_value}")

        if 'sortino' in self.results:
            sortino = self.results['sortino']
            self.logger.info("Sortino比率:")
            # 确保值不为None再进行格式化
            sortino_value = sortino.get('sortinoratio', 0) or 0

            self.logger.info(f"- Sortino比率: {sortino_value:.4f}")

        self.logger.info("=" * 30)

    def stop(self):
        """停止回测"""
        self.logger.info("停止回测")
        self.is_running = False
