"""
回测引擎实现
"""
import logging
from typing import Dict, Any

import backtrader as bt
import pandas as pd

from src.infrastructure.constants.const import DEFAULT_INITIAL_CAPITAL, DEFAULT_COMMISSION_RATE
from ..base_engine import BaseEngine
from ...analyzers.performance_analyzer import PerformanceAnalyzer
from ...analyzers.risk_analyzer import RiskAnalyzer


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

        # 分析器
        self.analyzers = []
        self.performance_analyzer = PerformanceAnalyzer()
        self.risk_analyzer = RiskAnalyzer()
        self.analyzers.extend([self.performance_analyzer, self.risk_analyzer])

        # 回测状态
        self.is_running = False
        self.current_datetime = None
        self.results = {}

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

    def set_broker(self, broker) -> None:
        """设置回测Broker"""
        self.broker = broker
        self.logger.info(f"设置Broker: {broker.__class__.__name__}")

        # 设置backtrader的broker参数
        try:
            initial_capital = self.config.get_params().get('initial_capital', DEFAULT_INITIAL_CAPITAL)
            commission = self.config.get_params().get('commission', DEFAULT_COMMISSION_RATE)
        except AttributeError:
            # 如果config没有get_params方法，尝试直接获取
            initial_capital = self.config.get('initial_capital', DEFAULT_INITIAL_CAPITAL)
            commission = self.config.get('commission', DEFAULT_COMMISSION_RATE)

        self.cerebro.broker.setcash(initial_capital)
        self.cerebro.broker.setcommission(commission=commission)

    def add_analyzer(self, analyzer) -> None:
        """添加分析器"""
        if analyzer not in self.analyzers:
            self.analyzers.append(analyzer)
            self.logger.info(f"添加分析器: {analyzer.__class__.__name__}")

    def _add_bt_analyzers(self):
        """添加backtrader内置分析器"""
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')

    def run(self) -> Dict[str, Any]:
        """运行回测"""
        self.logger.info("开始运行回测")
        self.is_running = True

        # 检查组件是否齐全
        if not self._check_components():
            self.is_running = False
            return {}

        # 添加backtrader内置分析器
        self._add_bt_analyzers()

        # 添加策略到cerebro
        try:
            strategy_params = self.config.get_params().get('strategy', {})
        except AttributeError:
            # 如果config没有get_params方法，尝试直接获取
            strategy_params = self.config.get('strategy', {})

        self.cerebro.addstrategy(self.strategy, **strategy_params)

        # 运行回测
        self.logger.info("开始执行backtrader回测")
        bt_results = self.cerebro.run()

        # 提取回测结果
        if len(bt_results) > 0:
            bt_strategy = bt_results[0]
            self.results = self._extract_results(bt_strategy)

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

        # 获取收益率
        returns = strategy.analyzers.returns.get_analysis()

        # 获取夏普比率
        sharpe = strategy.analyzers.sharpe.get_analysis()

        # 获取回撤
        drawdown = strategy.analyzers.drawdown.get_analysis()

        # 获取交易分析
        trades = strategy.analyzers.trade_analyzer.get_analysis()

        # 整理性能指标
        performance = {
            'total_return': returns.get('rtot', 0),
            'annual_return': returns.get('rnorm', 0),
            'sharpe_ratio': sharpe.get('sharperatio', 0) if hasattr(sharpe, 'get') else 0,
        }

        # 整理风险指标
        risk = {
            'max_drawdown': drawdown.get('max', {}).get('drawdown', 0),
            'max_drawdown_length': drawdown.get('max', {}).get('len', 0),
            'volatility': 0,  # 需要另外计算
        }

        # 整理交易统计
        trade_stats = {
            'total': trades.get('total', {}).get('total', 0),
            'won': trades.get('won', {}).get('total', 0),
            'lost': trades.get('lost', {}).get('total', 0),
            'win_rate': trades.get('won', {}).get('total', 0) / trades.get('total', {}).get('total', 1) if trades.get(
                'total', {}).get('total', 0) > 0 else 0,
            'pnl_net': trades.get('pnl', {}).get('net', {}).get('total', 0),
            'pnl_avg': trades.get('pnl', {}).get('net', {}).get('average', 0),
        }

        results['performance'] = performance
        results['risk'] = risk
        results['trades'] = trade_stats

        return results

    def analyze(self) -> Dict[str, Any]:
        """分析回测结果"""
        self.logger.info("分析回测结果")
        return self.results

    def _log_summary(self) -> None:
        """记录回测摘要"""
        if not self.results:
            self.logger.warning("没有回测结果可记录")
            return

        self.logger.info("=" * 30)
        self.logger.info("回测摘要")
        self.logger.info("=" * 30)

        # 提取关键指标
        if 'performance' in self.results:
            perf = self.results['performance']
            self.logger.info("性能指标:")
            # 确保值不为None再进行格式化
            total_return = perf.get('total_return', 0) or 0
            annual_return = perf.get('annual_return', 0) or 0
            sharpe_ratio = perf.get('sharpe_ratio', 0) or 0

            self.logger.info(f"- 总收益率: {total_return * 100:.2f}%")
            self.logger.info(f"- 年化收益率: {annual_return * 100:.2f}%")
            self.logger.info(f"- 夏普比率: {sharpe_ratio:.4f}")

        if 'risk' in self.results:
            risk = self.results['risk']
            self.logger.info("风险指标:")
            # 确保值不为None再进行格式化
            max_drawdown = risk.get('max_drawdown', 0) or 0
            max_drawdown_length = risk.get('max_drawdown_length', 0) or 0

            self.logger.info(f"- 最大回撤: {max_drawdown * 100:.2f}%")
            self.logger.info(f"- 最大回撤期: {max_drawdown_length} 天")

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

            self.logger.info(f"- 总交易次数: {total}")
            self.logger.info(f"- 盈利交易: {won}")
            self.logger.info(f"- 亏损交易: {lost}")
            self.logger.info(f"- 胜率: {win_rate * 100:.2f}%")
            self.logger.info(f"- 平均收益: {pnl_avg:.4f}")
            self.logger.info(f"- 总净利润: {pnl_net:.4f}")

        self.logger.info("=" * 30)

    def stop(self):
        """停止回测"""
        self.logger.info("停止回测")
        self.is_running = False
