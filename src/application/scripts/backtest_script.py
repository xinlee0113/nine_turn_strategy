"""
回测脚本
负责回测流程的控制，按照架构图中的回测流程实现
"""
import logging
import os
from datetime import datetime, timedelta

from backtrader import Cerebro

from src.business.strategy.magic_nine_strategy import MagicNineStrategy
from src.infrastructure.config.strategy_config import StrategyConfig
from src.infrastructure.event.event_manager import EventManager
from src.infrastructure.logging.logger import Logger
from src.infrastructure.utils.file_utils import save_backtest_results
from src.interface import TigerCsvData
from src.interface.tiger.tiger_store import TigerStore
from src.application.scripts.base_script import BaseScript


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
    """

    def __init__(self):
        """
        初始化回测脚本
        """
        # 调用父类初始化
        super().__init__()
        
        # 初始化事件管理器
        self.event_manager = EventManager()

        # 交易标的和时间范围
        self.symbol = "QQQ"
        self.start_date = datetime.now() - timedelta(days=30)
        self.end_date = datetime.now()
        self.period = "1m"

    def run(self, enable_plot=False):
        self.logger.info("开始回测流程")

        # 1. 加载配置
        self.logger.info("1. 加载回测配置")
        config_file = 'configs/strategy/magic_nine.yaml'
        self.load_config(config_file)

        # 2. 创建回测引擎
        self.logger.info("2. 创建回测引擎")
        self.create_cerebro()

        # 3. 创建策略实例
        self.logger.info("3. 创建神奇九转策略实例")
        self.strategy = MagicNineStrategy

        # 4. 创建数据源
        self.logger.info("4. 创建数据源")
        store = TigerStore()
        data = TigerCsvData()
        data.p.store = store

        # 5. 配置Broker
        self.logger.info("5. 配置Broker")
        self.setup_broker(10000.0)

        # 6. 添加分析器
        self.logger.info("6. 添加分析器")
        self.add_analyzers()

        # 7. 设置引擎组件
        self.logger.info("7. 向回测引擎添加组件")
        self.cerebro.addstrategy(self.strategy)
        self.cerebro.adddata(data)

        # 设置绘图选项
        if enable_plot:
            self.logger.info("启用绘图功能")
            # 正确设置Cerebro的绘图选项
            self.cerebro.stdstats = True
            # 添加默认的统计指标
            from backtrader import bt
            self.cerebro.addobserver(bt.observers.Broker)
            self.cerebro.addobserver(bt.observers.BuySell)
            self.cerebro.addobserver(bt.observers.Value)
            self.cerebro.addobserver(bt.observers.DrawDown)
            self.cerebro.addobserver(bt.observers.Trades)

        # 8. 注册事件监听
        self.logger.info("8. 注册事件监听")
        self.event_manager.register_listeners(self.cerebro, self.strategy, self.broker)
        self.logger.info("开始事件监听")

        # 记录回测开始时间
        self.start_time = datetime.now()

        # 9. 开始回测
        self.logger.info("执行回测引擎")
        results = self.cerebro.run()
        self.logger.info("回测执行完成")

        # 记录回测结束时间
        self.end_time = datetime.now()

        # 10. 分析回测结果
        self.logger.info("10. 分析回测结果")

        # 从策略实例中提取分析器结果
        analysis_results = self.extract_analyzer_results(results[0])

        # 11. 记录回测报告
        self.logger.info("11. 生成回测报告")
        self.log_results(analysis_results)

        # 12. 保存回测结果
        self._save_results(analysis_results)

        # 13. 如果启用绘图，则显示图表
        if enable_plot:
            self.logger.info("12. 生成并显示回测图表")
            try:
                # 创建输出目录
                plot_dir = "results/plots"
                os.makedirs(plot_dir, exist_ok=True)

                # 生成文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_filename = f"{timestamp}_{self.symbol}_{self.strategy.__name__}.png"
                plot_path = os.path.join(plot_dir, plot_filename)

                # 绘制并保存图表
                # backtrader的plot方法返回的是figure对象
                figs = self.cerebro.plot(barup='red', bardown='green',
                                         valuetags=True, volume=True, grid=True)

                # 保存第一个图表(总览图)
                if figs and len(figs) > 0 and len(figs[0]) > 0:
                    fig = figs[0][0]  # 获取第一个图表
                    fig.savefig(plot_path, dpi=300, bbox_inches='tight')
                    self.logger.info(f"回测图表已保存至: {plot_path}")
                else:
                    self.logger.warning("没有生成图表，可能是数据量太少")
            except Exception as e:
                self.logger.error(f"绘制图表失败: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())

        # 返回回测结果
        return analysis_results

    def _save_results(self, results):
        """
        保存回测结果到CSV文件
        """
        try:
            # 创建结果目录
            os.makedirs('results/backtest', exist_ok=True)

            # 构建文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            symbol = getattr(self, 'symbol', 'unknown')
            strategy_name = self.strategy.__name__ if hasattr(self.strategy, '__name__') else 'unknown'
            period = getattr(self, 'period', 'unknown')
            start_date_str = getattr(self, 'start_date', 'unknown')
            end_date_str = getattr(self, 'end_date', 'unknown')

            if isinstance(start_date_str, datetime):
                start_date_str = start_date_str.strftime("%Y%m%d")
            if isinstance(end_date_str, datetime):
                end_date_str = end_date_str.strftime("%Y%m%d")

            filename = f"results/backtest/{timestamp}_{symbol}_{strategy_name}_{start_date_str}_{end_date_str}_{period}.csv"

            # 计算附加指标
            win_rate = results['trades']['won']['total'] / results['trades']['total']['total'] * 100

            # 从trades数据中获取平均每天交易次数
            avg_trades_per_day = 0
            if hasattr(self, 'start_date') and hasattr(self, 'end_date') and self.start_date and self.end_date:
                delta = self.end_date - self.start_date
                days = max(1, delta.days + 1)  # 加1是为了包括开始日期
                avg_trades_per_day = results['trades']['total']['total'] / days

            # 准备数据
            data = {
                "回测ID": timestamp,
                "标的": symbol,
                "策略": strategy_name,
                "开始日期": start_date_str,
                "结束日期": end_date_str,
                "周期": period,
                "总收益率": round(results['performance']['total_return'] * 100, 3),
                "年化收益率": round(results['performance']['annual_return'] * 100, 3),
                "夏普比率": 0.0 if results['performance']['sharpe_ratio'] is None else round(
                    float(results['performance']['sharpe_ratio']), 3),
                "最大回撤": round(results['risk']['max_drawdown'] * 100, 3),
                "最大回撤持续时间": results['risk']['max_drawdown_duration'],
                "波动率": round(float(results['risk']['volatility']) * 100, 3),
                "胜率": round(win_rate, 2),
                "总交易次数": results['trades']['total']['total'],
                "盈利交易次数": results['trades']['won']['total'],
                "亏损交易次数": results['trades']['lost']['total'],
                "平均每天交易次数": round(avg_trades_per_day, 2),
                "总净利润": round(results['trades']['pnl']['net']['total'], 4),
                "平均净利润": round(results['trades']['pnl']['net']['average'], 4),
                "多头总盈亏": round(results['trades']['long']['pnl']['total'], 4),
                "空头总盈亏": round(results['trades']['short']['pnl']['total'], 4),
                "最大连续盈利次数": results['trades']['streak']['won']['longest'],
                "最大连续亏损次数": results['trades']['streak']['lost']['longest'],
                "交易开始时间": self.start_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(self, 'start_time') else "",
                "交易结束时间": self.end_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(self, 'end_time') else ""
            }

            # 保存回测结果
            result_file = save_backtest_results(
                data,
                symbol,
                strategy_name,
                start_date_str,
                end_date_str,
                period
            )
            self.logger.info(f"回测结果已保存到文件: {result_file}")

        except Exception as e:
            self.logger.error(f"保存回测结果失败: {str(e)}")
            import traceback
            self.logger.error(f"错误详情: {traceback.format_exc()}")

    def stop(self):
        """停止回测"""
        self.logger.info("停止回测")
        if self.data_source:
            self.data_source.stop()
        if self.cerebro:
            self.cerebro.stop()
        self.logger.info("回测停止完成")
