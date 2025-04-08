"""
回测脚本
负责回测流程的控制，按照架构图中的回测流程实现
"""
import logging
from datetime import datetime, timedelta

import pandas as pd
import pytz

from src.business.analyzers.performance_analyzer import PerformanceAnalyzer
from src.business.analyzers.risk_analyzer import RiskAnalyzer
from src.business.engines.backtest.backtest_engine import BacktestEngine
from src.business.strategy.magic_nine_strategy import MagicNineStrategy
from src.infrastructure.config.data_config import DataConfig
from src.infrastructure.config.strategy_config import StrategyConfig
from src.infrastructure.constants.const import TimeInterval, TimeZone, US_MARKET_MINUTES_PER_DAY, MAX_1MIN_DATA_DAYS
from src.infrastructure.event.event_manager import EventManager
from src.infrastructure.logging.logger import Logger
from src.interface.broker.backtest_broker import BacktestBroker
from src.interface.data.pandas_data import PandasData


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

    def run(self, symbol="AAPL", start_date=None, end_date=None, period=TimeInterval.ONE_MINUTE.value):
        """
        运行回测
        
        Args:
            symbol: 交易标的代码，默认为AAPL
            start_date: 开始日期，默认为当前日期前30天（对于1分钟K线，老虎证券API限制最多30天）
            end_date: 结束日期，默认为当前日期
            period: 数据周期，默认为1m(1分钟)
        """
        self.logger.info("开始回测流程")

        # 设置默认日期
        if end_date is None:
            end_date = datetime.now()

        # 如果是1分钟K线，确保时间范围不超过30天（老虎证券API限制）
        if period == TimeInterval.ONE_MINUTE.value:
            if start_date is None:
                # 自动设置为最近30天
                start_date = end_date - timedelta(days=MAX_1MIN_DATA_DAYS)
            else:
                # 检查时间范围是否超过30天
                if isinstance(start_date, datetime) and isinstance(end_date, datetime):
                    days_diff = (end_date - start_date).days
                    if days_diff > MAX_1MIN_DATA_DAYS:
                        self.logger.warning(
                            f"1分钟K线数据请求时间范围超过{MAX_1MIN_DATA_DAYS}天 ({days_diff}天)，将被截断为{MAX_1MIN_DATA_DAYS}天")
                        start_date = end_date - timedelta(days=MAX_1MIN_DATA_DAYS)
        else:
            # 非1分钟K线，如果未指定开始日期则默认为10天
            if start_date is None:
                start_date = end_date - timedelta(days=10)

        # 设置时区（使用美国东部时间，与美股交易时间一致）
        ny_tz = pytz.timezone(TimeZone.US_EASTERN.value)

        # 确保end_date是datetime对象并具有时区信息
        if not isinstance(end_date, datetime):
            end_date = datetime.combine(end_date, datetime.min.time())
        if hasattr(end_date, 'tzinfo') and end_date.tzinfo is None:
            end_date = ny_tz.localize(end_date)

        # 确保start_date是datetime对象并具有时区信息
        if not isinstance(start_date, datetime):
            start_date = datetime.combine(start_date, datetime.min.time())
        if hasattr(start_date, 'tzinfo') and start_date.tzinfo is None:
            start_date = ny_tz.localize(start_date)

        # 记录回测时间范围
        self.logger.info(
            f"回测时间范围: {start_date.strftime('%Y-%m-%d %H:%M:%S')} - {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
        # 计算时间跨度 - 确保时区一致
        if start_date.tzinfo is not None and end_date.tzinfo is not None:
            days_diff = (end_date - start_date).days
        else:
            # 如果时区不一致或不存在，则使用日期部分计算
            days_diff = (end_date.date() - start_date.date()).days
        self.logger.info(f"回测时间跨度: {days_diff}天")

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
        self.logger.info(
            f"4. 创建数据源: {symbol}, {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}, 周期: {period}")
        try:
            # 创建PandasData实例
            self.data_source = PandasData()
            self.data_source.start()

            # 请求历史数据
            self.logger.info("请求历史数据")
            data = self.data_source.get_historical_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval=period
            )

            if data is None or data.empty:
                self.logger.error(f"未获取到数据: {symbol}, {start_date} - {end_date}")
                return False

            # 输出获取到的数据统计信息
            try:
                if isinstance(data.index, pd.DatetimeIndex):
                    trading_days = len(data.index.date.unique())
                else:
                    # 转换索引为DatetimeIndex
                    self.logger.warning("数据索引不是DatetimeIndex类型，尝试转换")
                    # 创建一个基于当前时间的时间序列
                    date_range = pd.date_range(start=start_date, periods=len(data), freq=TimeInterval.ONE_MINUTE.value)
                    data.index = date_range
                    trading_days = len(data.index.date.unique())

                self.logger.info(f"成功加载数据: {len(data)} 个数据点，{trading_days} 个交易日")
                self.logger.info(f"数据时间范围: {data.index.min()} - {data.index.max()}")

                # 检查数据点数量是否符合预期
                if period == TimeInterval.ONE_MINUTE.value:
                    expected_points_per_day = US_MARKET_MINUTES_PER_DAY  # 美股一个交易日有390分钟
                    expected_total = trading_days * expected_points_per_day
                    completeness = len(data) / expected_total * 100 if expected_total > 0 else 0
                    self.logger.info(f"数据完整度: {completeness:.2f}% (获取 {len(data)}/{expected_total} 个数据点)")
            except Exception as e:
                self.logger.warning(f"处理数据统计信息时出错: {str(e)}")
        except Exception as e:
            self.logger.error(f"加载数据失败: {str(e)}")
            return False

        # 5. 创建Broker并设置
        self.logger.info("5. 创建回测Broker")
        self.broker = BacktestBroker()

        # 6. 添加分析器
        self.logger.info("6. 添加分析器")
        self.analyzer = PerformanceAnalyzer()
        risk_analyzer = RiskAnalyzer()
        self.analyzers = [self.analyzer, risk_analyzer]

        # 7. 设置引擎组件
        self.logger.info("7. 向回测引擎添加组件")
        # 添加策略
        self.engine.set_strategy(self.strategy)
        # 添加数据源
        self.engine.set_data(data)
        # 设置Broker
        self.engine.set_broker(self.broker)
        # 注册分析器
        for analyzer in self.analyzers:
            self.engine.add_analyzer(analyzer)

        # 8. 注册事件监听
        self.logger.info("8. 注册事件监听")
        self.event_manager.register_listeners(self.engine, self.strategy, self.broker)
        self.logger.info("开始事件监听")

        # 9. 开始回测
        self.logger.info("9. 开始运行回测")
        try:
            self.logger.info("执行回测引擎")
            results = self.engine.run()
            self.logger.info("回测执行完成")

            # 10. 分析回测结果
            self.logger.info("10. 分析回测结果")
            analysis_results = self.analyzer.analyze(results)

            # 11. 记录回测报告
            self.logger.info("11. 生成回测报告")
            self._log_results(analysis_results)

            # 返回回测结果
            return analysis_results
        except Exception as e:
            self.logger.error(f"回测执行失败: {str(e)}")
            return False

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

        # 记录风险指标
        if 'risk' in results:
            risk = results['risk']
            self.logger.info("风险指标:")
            # 确保值不为None再进行格式化
            max_drawdown = risk.get('max_drawdown', 0) or 0
            max_drawdown_length = risk.get('max_drawdown_length', 0) or 0
            volatility = risk.get('volatility', 0) or 0

            self.logger.info(f"- 最大回撤: {max_drawdown * 100:.2f}%")
            self.logger.info(f"- 最大回撤期: {max_drawdown_length} 天")
            self.logger.info(f"- 波动率: {volatility * 100:.2f}%")

        # 记录交易统计
        if 'trades' in results:
            trades = results['trades']
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

        self.logger.info("=" * 50)

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
