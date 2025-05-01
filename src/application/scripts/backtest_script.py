"""
回测脚本
负责回测流程的控制，按照架构图中的回测流程实现
"""
import os
from datetime import datetime, timedelta

from src.application.scripts.base_script import BaseScript
from src.business.strategy.magic_nine_strategy import MagicNineStrategy
from src.infrastructure.event.event_manager import EventManager
from src.infrastructure.reporting.report_generator import ReportGenerator
from src.interface import TigerCsvData
from src.interface.tiger.tiger_store import TigerStore


class BacktestScript(BaseScript):
    """
    回测脚本类
    实现架构图中定义的回测流程，包括:
    1. 初始化回测配置
    2. 创建回测引擎
    3. 创建策略
    4. 加载数据
    5. 运行回测
    6. 分析结果
    
    支持单标的和多标的回测
    """

    def __init__(self):
        """
        初始化回测脚本
        """
        # 调用父类初始化
        super().__init__()

        # 初始化事件管理器
        self.event_manager = EventManager()

        # 初始化报告生成器
        self.report_generator = ReportGenerator()

        # 交易标的和时间范围
        self.symbols = ["QQQ"]  # 默认标的
        self.start_date = datetime.now() - timedelta(days=30)
        self.end_date = datetime.now()
        self.period = "1m"

        # 存储多标的回测结果
        self.all_results = {}

    def set_symbols(self, symbols):
        """设置回测标的
        
        Args:
            symbols: 标的列表
        """
        if isinstance(symbols, str):
            self.symbols = [symbols]
        else:
            self.symbols = symbols
        self.logger.info(f"设置回测标的: {self.symbols}")

    def run_single_symbol(self, symbol, enable_plot=False):
        """单标的回测
        
        Args:
            symbol: 回测标的
            enable_plot: 是否启用绘图
            
        Returns:
            分析结果字典
        """
        self.logger.info(f"开始对标的 {symbol} 进行回测")

        # 设置当前标的
        self.symbol = symbol

        # 创建新的cerebro实例
        self.create_cerebro()

        # 创建策略实例
        self.strategy = MagicNineStrategy

        # 创建数据源
        store = TigerStore()
        data = TigerCsvData(symbol=symbol, store=store)

        # 配置Broker
        self.setup_broker(10000.0)

        # 添加分析器
        self.add_analyzers()

        # 设置引擎组件
        self.cerebro.addstrategy(self.strategy)
        self.cerebro.adddata(data)

        # 设置绘图选项
        if enable_plot:
            self.cerebro.stdstats = True
            from backtrader import bt
            self.cerebro.addobserver(bt.observers.Broker)
            self.cerebro.addobserver(bt.observers.BuySell)
            self.cerebro.addobserver(bt.observers.Value)
            self.cerebro.addobserver(bt.observers.DrawDown)
            self.cerebro.addobserver(bt.observers.Trades)

        # 注册事件监听
        self.event_manager.register_listeners(self.cerebro, self.strategy, self.broker)

        # 记录回测开始时间
        self.start_time = datetime.now()

        # 执行回测
        self.logger.info(f"执行 {symbol} 回测引擎")
        results = self.cerebro.run()
        self.logger.info(f"{symbol} 回测执行完成")

        # 记录回测结束时间
        self.end_time = datetime.now()

        # 分析回测结果
        analysis_results = self.extract_analyzer_results(results[0])

        # 记录回测报告
        self.logger.info(f"{symbol} 生成回测报告")
        self.report_generator.log_results(analysis_results)

        # 保存回测结果
        strategy_name = self.strategy.__name__ if hasattr(self.strategy, '__name__') else 'unknown'

        # 将日期转换为字符串
        start_date_str = self.start_date.strftime("%Y%m%d") if isinstance(self.start_date, datetime) else self.start_date
        end_date_str = self.end_date.strftime("%Y%m%d") if isinstance(self.end_date, datetime) else self.end_date

        self.report_generator.save_results(
            analysis_results,
            symbol,
            strategy_name,
            start_date_str,
            end_date_str,
            self.period,
            self.start_time,
            self.end_time
        )

        # 绘制图表
        if enable_plot:
            self._plot_results(symbol, results)

        return analysis_results

    def run(self, enable_plot=False, symbols=None):
        """执行回测
        
        Args:
            enable_plot: 是否启用绘图
            symbols: 标的列表，如果为None则使用self.symbols
            
        Returns:
            所有标的的回测结果汇总
        """
        self.logger.info("开始回测流程")

        # 如果提供了标的列表，则更新
        if symbols:
            self.set_symbols(symbols)

        # 加载配置
        self.logger.info("1. 加载回测配置")
        config_file = 'configs/strategy/magic_nine.yaml'
        self.load_config(config_file)

        # 清空之前的结果
        self.all_results = {}

        # 对每个标的进行回测
        for symbol in self.symbols:
            # 运行单个标的回测
            result = self.run_single_symbol(symbol, enable_plot)

            # 保存结果
            self.all_results[symbol] = result

            self.logger.info(f"标的 {symbol} 回测完成")

        # 生成多标的汇总报告
        self.report_generator.generate_summary_report(self.all_results)

        return self.all_results

    def _plot_results(self, symbol, results):
        """绘制回测结果图表
        
        Args:
            symbol: 标的
            results: 回测结果
        """
        # 创建输出目录
        plot_dir = "results/backtest/plots"
        os.makedirs(plot_dir, exist_ok=True)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plot_filename = f"{timestamp}_{symbol}_{self.strategy.__name__}.png"
        plot_path = os.path.join(plot_dir, plot_filename)

        # 绘制并保存图表
        figs = self.cerebro.plot(barup='red', bardown='green',
                                 valuetags=True, volume=True, grid=True)

        # 保存第一个图表(总览图)
        if figs and len(figs) > 0 and len(figs[0]) > 0:
            fig = figs[0][0]  # 获取第一个图表
            fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"回测图表已保存至: {plot_path}")
        else:
            self.logger.warning(f"标的 {symbol} 没有生成图表，可能是数据量太少")

    def stop(self):
        """停止回测"""
        self.logger.info("停止回测")
        if self.data_source:
            self.data_source.stop()
        if self.cerebro:
            self.cerebro.stop()
        self.logger.info("回测停止完成")
