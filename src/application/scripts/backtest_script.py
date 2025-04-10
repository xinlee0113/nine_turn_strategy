"""
回测脚本
负责回测流程的控制，按照架构图中的回测流程实现
"""
import logging
from datetime import datetime

from src.business.engines.backtest.backtest_engine import BacktestEngine
from src.business.strategy.magic_nine_strategy import MagicNineStrategy
from src.infrastructure.config.data_config import DataConfig
from src.infrastructure.config.strategy_config import StrategyConfig
from src.infrastructure.event.event_manager import EventManager
from src.infrastructure.logging.logger import Logger
from src.infrastructure.utils.file_utils import save_backtest_results
from src.interface import TigerCsvData


class BacktestScript:
    """
    回测脚本类
    实现架构图中定义的回测流程，包括:
    1. 初始化回测配置
    2. 创建回测引擎
    3. 创建策略
    4. 加载数据
    5. 运行回测
    6. 分析结果
    """

    def __init__(self):
        """
        初始化回测脚本
        """
        # 初始化日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger_manager = Logger()

        # 初始化配置
        self.data_config = DataConfig()
        self.strategy_config = StrategyConfig()

        # 初始化事件管理器
        self.event_manager = EventManager()

        # 初始化引擎和组件
        self.engine = None
        self.strategy = None
        self.data_source = None
        self.analyzer = None
        self.broker = None
        self.analyzers = []

    def run(self, enable_plot=False):
        self.logger.info("开始回测流程")

        # 1. 加载配置
        self.logger.info("1. 加载回测配置")
        config_file = 'configs/strategy/magic_nine.yaml'
        self.strategy_config.load_config(config_file)
        self.data_config.load_config('configs/data/data_config.yaml')

        # 2. 创建回测引擎
        self.logger.info("2. 创建回测引擎")
        self.engine = BacktestEngine(self.strategy_config)

        # 3. 创建策略实例
        self.logger.info("3. 创建神奇九转策略实例")
        self.strategy = MagicNineStrategy

        # 4. 创建数据源
        data = TigerCsvData()

        # 5. 创建Broker并设置

        # 6. 添加分析器
        self.logger.info("6. 添加分析器")
        from src.business.analyzers.performance_analyzer import PerformanceAnalyzer
        from src.business.analyzers.risk_analyzer import RiskAnalyzer

        # 添加分析器类（而不是实例）
        self.engine.add_analyzer(PerformanceAnalyzer)
        self.engine.add_analyzer(RiskAnalyzer)

        # 记录
        self.logger.info("成功添加基本分析器")

        # 7. 设置引擎组件
        self.logger.info("7. 向回测引擎添加组件")
        # 添加策略
        self.engine.set_strategy(self.strategy)
        # 添加数据源
        self.engine.set_data(data)
        # 设置Broker
        self.engine.set_broker(self.broker)

        # 设置绘图选项
        if enable_plot:
            self.engine.set_plot_options(enabled=True)
            self.logger.info("启用绘图功能")

        # 8. 注册事件监听
        self.logger.info("8. 注册事件监听")
        self.event_manager.register_listeners(self.engine, self.strategy, self.broker)
        self.logger.info("开始事件监听")

        # 9. 开始回测
        self.logger.info("执行回测引擎")
        results = self.engine.run()
        self.logger.info("回测执行完成")

        # 10. 分析回测结果
        self.logger.info("10. 分析回测结果")

        # 构建分析结果字典
        analysis_results = {
            'performance': results.get('performanceanalyzer', {}),
            'risk': results.get('riskanalyzer', {})
        }

        # 确保从calmarratio分析器中获取卡尔玛比率
        if 'calmarratio' in results:
            calmar_results = results.get('calmarratio', {})
            if 'calmar_ratio' in calmar_results:
                if 'risk' not in analysis_results:
                    analysis_results['risk'] = {}
                analysis_results['risk']['calmar_ratio'] = calmar_results['calmar_ratio']
                self.logger.info(f"从calmarratio分析器获取卡尔玛比率: {calmar_results['calmar_ratio']}")

            # 添加交易统计
            analysis_results['trades'] = results.get('trades', {})
            # 确保从tradeanalyzer中获取平均每天交易次数
            if 'tradeanalyzer' in results:
                trade_analyzer_results = results.get('tradeanalyzer', {})
                if 'trades' not in analysis_results:
                    analysis_results['trades'] = {}

                # 从tradeanalyzer中获取平均每天交易次数
                if 'trades' in trade_analyzer_results and 'avg_trades_per_day' in trade_analyzer_results['trades']:
                    analysis_results['trades']['avg_trades_per_day'] = trade_analyzer_results['trades'][
                        'avg_trades_per_day']
                    self.logger.info(
                        f"从tradeanalyzer.trades获取平均每天交易次数: {trade_analyzer_results['trades']['avg_trades_per_day']}")

            self.logger.info(f"已从回测引擎中提取分析结果: {analysis_results.keys()}")

        # 11. 记录回测报告
        self.logger.info("11. 生成回测报告")
        self._log_results(analysis_results)

        # 返回回测结果
        return analysis_results

    def _log_results(self, results):
        """记录回测结果"""
        if not results:
            self.logger.warning("没有回测结果可记录")
            return

        self.logger.info("=" * 50)
        self.logger.info("回测结果摘要")
        self.logger.info("=" * 50)

        # 记录性能指标
        if 'performance' in results:
            perf = results['performance']
            self.logger.info("性能指标:")
            # 确保值不为None再进行格式化
            total_return = perf.get('total_return', 0) or 0
            annual_return = perf.get('annual_return', 0) or 0
            sharpe_ratio = perf.get('sharpe_ratio', 0) or 0

            self.logger.info(f"- 总收益率: {total_return * 100:.2f}%")
            self.logger.info(f"- 年化收益率: {annual_return * 100:.2f}%")
            self.logger.info(f"- 夏普比率: {sharpe_ratio:.4f}")

            # 如果有索提诺比率，也输出
            if 'sortino_ratio' in perf:
                sortino_ratio = perf.get('sortino_ratio', 0) or 0
                self.logger.info(f"- 索提诺比率: {sortino_ratio:.4f}")

        # 记录风险指标
        if 'risk' in results:
            risk = results['risk']
            self.logger.info("风险指标:")
            # 确保值不为None再进行格式化
            max_drawdown = risk.get('max_drawdown', 0) or 0
            max_drawdown_length = risk.get('max_drawdown_length', 0) or 0
            volatility = risk.get('volatility', 0) or 0

            # 确保最大回撤值在合理范围内 [0, 1]，然后转换为百分比显示
            max_drawdown = max(0, min(max_drawdown, 1.0))
            self.logger.info(f"- 最大回撤: {max_drawdown * 100:.2f}%")

            # 直接输出原始回撤长度，不做任何修正
            self.logger.info(f"- 最大回撤持续时间: {max_drawdown_length} 个数据点")

            # 如果有回撤日期信息，显示具体日期
            if 'max_drawdown_start' in risk and 'max_drawdown_end' in risk:
                start_date = risk.get('max_drawdown_start')
                end_date = risk.get('max_drawdown_end')
                self.logger.info(f"- 最大回撤起止时间: {start_date} 至 {end_date}")

                # 计算实际日历天数
                if isinstance(start_date, datetime) and isinstance(end_date, datetime):
                    delta = end_date - start_date
                    days = delta.days + (1 if delta.seconds > 0 else 0)
                    self.logger.info(f"- 最大回撤持续天数: {days} 天")

            # 分析回撤历史
            if 'drawdowns' in risk and risk['drawdowns']:
                drawdowns = risk['drawdowns']
                # 取前5个最大回撤
                top_drawdowns = sorted(drawdowns, key=lambda x: x[2], reverse=True)[:5]

                self.logger.info("回撤历史(Top 5):")
                for i, (start_date, end_date, dd_value, points) in enumerate(top_drawdowns, 1):
                    dd_days = (end_date - start_date).days + (1 if (end_date - start_date).seconds > 0 else 0)
                    self.logger.info(
                        f"  {i}. {start_date} 至 {end_date}: {dd_value * 100:.2f}%, 持续{points}个点 ({dd_days}天)")

            self.logger.info(f"- 波动率: {volatility * 100:.2f}%")

            # 计算卡尔玛比率 (Calmar Ratio) = 年化收益率 / 最大回撤
            if max_drawdown > 0 and annual_return:
                calmar_ratio = annual_return / max_drawdown
                self.logger.info(f"- 卡尔玛比率: {calmar_ratio:.4f}")
            else:
                self.logger.info(f"- 卡尔玛比率: 0.0000")

        # 记录交易统计
        if 'trades' in results:
            trades = results['trades']
            self.logger.info("交易统计:")
            # 确保值不为None再进行格式化
            total = trades.get('total', 0) or 0
            won = trades.get('won', 0) or 0
            lost = trades.get('lost', 0) or 0
            win_rate = trades.get('win_rate', 0) or 0

            # 基础交易统计
            self.logger.info(f"- 总交易次数: {total}")
            self.logger.info(f"- 盈利交易: {won}")
            self.logger.info(f"- 亏损交易: {lost}")
            self.logger.info(f"- 胜率: {win_rate * 100:.2f}%")

            # 如果有平均每天交易次数，输出它
            if 'avg_trades_per_day' in trades:
                avg_trades_per_day = trades.get('avg_trades_per_day', 0) or 0
                self.logger.info(f"- 平均每天交易次数: {avg_trades_per_day:.2f}")

            # 如果有更多高级指标，也输出它们
            if 'avg_profit' in trades and 'avg_loss' in trades:
                avg_profit = trades.get('avg_profit', 0) or 0
                avg_loss = trades.get('avg_loss', 0) or 0

                # 计算平均盈亏比
                win_loss_ratio = trades.get('win_loss_ratio', 0) or 0
                if win_loss_ratio == 0 and avg_loss != 0:
                    win_loss_ratio = abs(avg_profit / avg_loss)

                self.logger.info(f"- 平均盈亏比: {win_loss_ratio:.2f}")

            # 盈利因子 = 总盈利 / 总亏损
            profit_factor = trades.get('profit_factor', 0) or 0
            self.logger.info(f"- 盈利因子: {profit_factor:.2f}")

            # 平均每笔交易收益
            expectancy = trades.get('expectancy', 0) or 0
            self.logger.info(f"- 每笔交易期望收益: {expectancy:.2f}")

            # 最大连续盈亏次数
            max_consecutive_wins = trades.get('max_consecutive_wins', 0) or 0
            max_consecutive_losses = trades.get('max_consecutive_losses', 0) or 0

            self.logger.info(f"- 最大连续盈利次数: {max_consecutive_wins}")
            self.logger.info(f"- 最大连续亏损次数: {max_consecutive_losses}")

            # 系统质量指标 (SQN)
            sqn = trades.get('sqn', 0) or 0
            self.logger.info(f"- 系统质量指标(SQN): {sqn:.4f}")

            # 平均收益和总收益
            pnl_avg = trades.get('avg_trade', 0) or trades.get('pnl_avg', 0) or 0
            pnl_net = trades.get('net_profit', 0) or trades.get('pnl_net', 0) or 0

            self.logger.info(f"- 平均收益: {pnl_avg:.4f}")
            self.logger.info(f"- 总净利润: {pnl_net:.4f}")

            # 平均每天交易次数
            if hasattr(self, 'start_date') and hasattr(self, 'end_date'):
                delta = self.end_date - self.start_date
                days = max(1, delta.days)
                trades_per_day = total / days
                self.logger.info(f"- 平均每天交易次数: {trades_per_day:.2f}")

                # 确保trades_per_day被添加到formatted_results中
                # 将在后面构建formatted_results时使用

        # 记录持仓分析结果
        if 'positions' in results and results['positions']:
            positions = results['positions']
            self.logger.info("持仓统计:")

            # 总持仓数量
            total_positions = positions.get('total_positions', 0)
            long_positions = positions.get('long_positions', 0)
            short_positions = positions.get('short_positions', 0)

            self.logger.info(f"- 总持仓数量: {total_positions}")
            self.logger.info(f"- 多头持仓: {long_positions}")
            self.logger.info(f"- 空头持仓: {short_positions}")

            # 多空盈亏
            long_pnl = positions.get('long_pnl', 0)
            short_pnl = positions.get('short_pnl', 0)

            self.logger.info(f"- 多头总盈亏: {long_pnl:.2f}")
            self.logger.info(f"- 空头总盈亏: {short_pnl:.2f}")

            # 多空胜率
            long_win_rate = positions.get('long_win_rate', 0)
            short_win_rate = positions.get('short_win_rate', 0)

            self.logger.info(f"- 多头胜率: {long_win_rate * 100:.2f}%")
            self.logger.info(f"- 空头胜率: {short_win_rate * 100:.2f}%")

            # 持仓时间统计
            avg_holding_period = positions.get('avg_holding_period', 0)
            max_holding_period = positions.get('max_holding_period', 0)
            min_holding_period = positions.get('min_holding_period', 0)

            # 将分钟转换为小时和天，便于阅读
            avg_hours = avg_holding_period / 60
            max_hours = max_holding_period / 60
            min_hours = min_holding_period / 60

            avg_days = avg_hours / 24
            max_days = max_hours / 24
            min_days = min_hours / 24

            self.logger.info(f"- 平均持仓时间: {avg_holding_period:.0f}分钟 ({avg_hours:.2f}小时, {avg_days:.2f}天)")
            self.logger.info(f"- 最长持仓时间: {max_holding_period:.0f}分钟 ({max_hours:.2f}小时, {max_days:.2f}天)")
            self.logger.info(f"- 最短持仓时间: {min_holding_period:.0f}分钟 ({min_hours:.2f}小时, {min_days:.2f}天)")

            # 持仓时间分布
            if 'holding_time_percentiles' in positions:
                percentiles = positions['holding_time_percentiles']
                self.logger.info("- 持仓时间分布(分钟):")
                for p, value in percentiles.items():
                    if p.startswith('p'):
                        percentile = p[1:]  # 去掉'p'前缀
                        hours = value / 60
                        days = hours / 24
                        self.logger.info(
                            f"  - {percentile}%的持仓时间小于: {value:.0f}分钟 ({hours:.2f}小时, {days:.2f}天)")

        self.logger.info("=" * 50)

        # 保存回测结果到文件
        try:
            # 准备保存回测结果需要的参数
            symbol = getattr(self, 'symbol', 'unknown')
            strategy_name = "MagicNine"

            # 格式化日期
            start_date_str = self.start_date.strftime('%Y%m%d') if hasattr(self,
                                                                           'start_date') and self.start_date else 'unknown'
            end_date_str = self.end_date.strftime('%Y%m%d') if hasattr(self,
                                                                       'end_date') and self.end_date else 'unknown'

            # 周期
            period_str = getattr(self, 'period', '1m')

            # 从trades数据中获取平均每天交易次数
            avg_trades_per_day = results.get('trades', {}).get('avg_trades_per_day', 0)
            if not avg_trades_per_day and 'trades' in results and 'total' in results['trades']:
                # 如果avg_trades_per_day为0或不存在，但有交易总数，则计算平均每天交易次数
                if hasattr(self, 'start_date') and hasattr(self, 'end_date') and self.start_date and self.end_date:
                    delta = self.end_date - self.start_date
                    days = max(1, delta.days + 1)  # 加1是为了包括开始日期
                    avg_trades_per_day = results['trades']['total'] / days
                    self.logger.info(f"计算得到平均每天交易次数: {avg_trades_per_day:.2f}")

            # 提取关键指标并保留3位小数
            formatted_results = {
                "performance": {
                    "total_return": round(results.get('performance', {}).get('total_return', 0) or 0, 3),
                    "annual_return": round(results.get('performance', {}).get('annual_return', 0) or 0, 3),
                    "sharpe_ratio": round(results.get('performance', {}).get('sharpe_ratio', 0) or 0, 3),
                },
                "risk": {
                    "max_drawdown": round(results.get('risk', {}).get('max_drawdown', 0) or 0, 3),
                    "volatility": round(results.get('risk', {}).get('volatility', 0) or 0, 3),
                    "calmar_ratio": round(results.get('risk', {}).get('calmar_ratio', 0) or 0, 3),
                },
                "trades": {
                    "total_trades": results.get('trades', {}).get('total', 0),
                    "profitable_trades": results.get('trades', {}).get('won', 0),
                    "losing_trades": results.get('trades', {}).get('lost', 0),
                    "win_rate": round(results.get('trades', {}).get('win_rate', 0) or 0, 3),
                    "profit_loss_ratio": round(results.get('trades', {}).get('win_loss_ratio', 0) or 0, 3),
                    "profit_factor": round(results.get('trades', {}).get('profit_factor', 0) or 0, 3),
                    "expected_payoff": round(results.get('trades', {}).get('expectancy', 0) or 0, 3),
                    "max_consecutive_wins": results.get('trades', {}).get('max_consecutive_wins', 0),
                    "max_consecutive_losses": results.get('trades', {}).get('max_consecutive_losses', 0),
                    "total_net_profit": round(results.get('trades', {}).get('pnl_net', 0) or 0, 3),
                    "avg_trades_per_day": round(avg_trades_per_day, 3),  # 使用计算或获取的avg_trades_per_day值
                    "sqn": round(results.get('trades', {}).get('sqn', 0) or 0, 3),  # 添加SQN指标
                }
            }

            # 保存回测结果
            result_file = save_backtest_results(
                formatted_results,
                symbol,
                strategy_name,
                start_date_str,
                end_date_str,
                period_str
            )
            self.logger.info(f"回测结果已保存到文件: {result_file}")

        except Exception as e:
            self.logger.error(f"保存回测结果失败: {str(e)}")
            import traceback
            self.logger.error(f"错误详情: {traceback.format_exc()}")

    def stop(self):
        """
        停止回测
        """
        self.logger.info("停止回测")
        if self.data_source:
            self.data_source.stop()
        if self.engine:
            self.engine.stop()
        self.logger.info("回测停止完成")
