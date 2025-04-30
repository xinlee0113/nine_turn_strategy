"""
回测脚本
负责回测流程的控制，按照架构图中的回测流程实现
"""
import logging
from datetime import datetime, timedelta
import os

from backtrader import Cerebro

from src.business.strategy.magic_nine_strategy import MagicNineStrategy
from src.infrastructure.config.data_config import DataConfig
from src.infrastructure.config.strategy_config import StrategyConfig
from src.infrastructure.event.event_manager import EventManager
from src.infrastructure.logging.logger import Logger
from src.infrastructure.utils.file_utils import save_backtest_results
from src.interface import TigerCsvData
from src.interface.tiger.tiger_store import TigerStore


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
        self.cerebro = None
        self.strategy = None
        self.data_source = None
        self.analyzer = None
        self.broker = None
        self.analyzers = []
        
        # 交易标的和时间范围
        self.symbol = "QQQ"
        self.start_date = datetime.now() - timedelta(days=30)
        self.end_date = datetime.now()
        self.period = "1m"
        
        # 回测执行时间记录
        self.start_time = None
        self.end_time = None

    def run(self, enable_plot=False):
        self.logger.info("开始回测流程")

        # 1. 加载配置
        self.logger.info("1. 加载回测配置")
        config_file = 'configs/strategy/magic_nine.yaml'
        self.strategy_config.load_config(config_file)
        self.data_config.load_config('configs/data/data_config.yaml')
        
        # 2. 创建回测引擎
        self.logger.info("2. 创建回测引擎")
        self.cerebro = Cerebro()
        self.cerebro.p.oldbuysell= True

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
        self.cerebro.broker.setcash(10000.0)
        
        # 6. 添加分析器
        self.logger.info("6. 添加分析器")
        from src.business.analyzers.performance_analyzer import PerformanceAnalyzer
        from src.business.analyzers.risk_analyzer import RiskAnalyzer
        from backtrader.analyzers import SharpeRatio, DrawDown, TradeAnalyzer

        # 添加分析器，使用一致的命名，以便访问
        self.cerebro.addanalyzer(PerformanceAnalyzer, _name='performanceanalyzer')
        self.cerebro.addanalyzer(RiskAnalyzer, _name='riskanalyzer')
        self.cerebro.addanalyzer(SharpeRatio, _name='sharperatio')
        self.cerebro.addanalyzer(DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(TradeAnalyzer, _name='tradeanalyzer')

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
        # 不需要设置engine.plot属性

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
        analysis_results = self._extract_analyzer_results(results[0])
        
        # 11. 记录回测报告
        self.logger.info("11. 生成回测报告")
        self._log_results(analysis_results)
        
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

    def _extract_analyzer_results(self, strategy):
        """从策略实例中提取分析器结果"""
        analysis_results = {'performance': {}, 'risk': {}, 'trades': {}}
            
        # 从性能分析器获取结果
        perf = strategy.analyzers.performanceanalyzer
        analysis_results['performance'] = perf.get_analysis()
        self.logger.info(f"成功提取性能分析器结果: {analysis_results['performance']}")
        
        # 从风险分析器获取结果
        risk = strategy.analyzers.riskanalyzer
        analysis_results['risk'] = risk.get_analysis()
        self.logger.info(f"成功提取风险分析器结果: {analysis_results['risk']}")
            
        # 从交易分析器获取结果
        trade = strategy.analyzers.tradeanalyzer
        analysis_results['trades'] = trade.get_analysis()
        self.logger.info(f"成功提取交易分析器结果: {analysis_results['trades']}")
            
        # 从sharperatio分析器获取结果
        sharpe = strategy.analyzers.sharperatio
        sharpe_ratio = sharpe.get_analysis()
        analysis_results['performance']['sharpe_ratio'] = sharpe_ratio.get('sharperatio', 0.0)
            
        # 从drawdown分析器获取结果
        dd = strategy.analyzers.drawdown
        dd_analysis = dd.get_analysis()
        analysis_results['risk']['max_drawdown'] = dd_analysis.get('max', {}).get('drawdown', 0.0) / 100.0
        analysis_results['risk']['max_drawdown_length'] = dd_analysis.get('max', {}).get('len', 0)
            
        self.logger.info(f"已从回测引擎中提取分析结果: {analysis_results.keys()}")
        
        return analysis_results

    def _log_results(self, results):
        """记录回测结果"""
        self.logger.info("=" * 50)
        self.logger.info("回测结果摘要")
        self.logger.info("=" * 50)

        # 记录性能指标
        perf = results['performance']
        self.logger.info("性能指标:")
        self.logger.info(f"- 总收益率: {perf['total_return'] * 100:.2f}%")
        self.logger.info(f"- 年化收益率: {perf['annual_return'] * 100:.2f}%")
        
        # 将numpy值转换为Python标准值
        sharpe_ratio = float(perf['sharpe_ratio']) if perf['sharpe_ratio'] is not None else 0.0
        self.logger.info(f"- 夏普比率: {sharpe_ratio:.4f}")

        # 记录风险指标
        risk = results['risk']
        self.logger.info("风险指标:")
        self.logger.info(f"- 最大回撤: {risk['max_drawdown'] * 100:.2f}%")
        self.logger.info(f"- 最大回撤持续时间: {risk['max_drawdown_duration']} 个数据点")
        self.logger.info(f"- 波动率: {risk['volatility'] * 100:.2f}%")

        # 计算卡尔玛比率
        calmar_ratio = perf['annual_return'] / risk['max_drawdown'] if risk['max_drawdown'] > 0 else 0
        self.logger.info(f"- 卡尔玛比率: {calmar_ratio:.4f}")

        # 记录交易统计
        trades = results['trades']
        total = trades.total.total
        won = trades.won.total
        lost = trades.lost.total
        win_rate = won / total if total > 0 else 0
        
        # 基础交易统计
        self.logger.info("交易统计:")
        self.logger.info(f"- 总交易次数: {total}")
        self.logger.info(f"- 盈利交易: {won}")
        self.logger.info(f"- 亏损交易: {lost}")
        self.logger.info(f"- 胜率: {win_rate * 100:.2f}%")

        # 计算平均每天交易次数
        days = max(1, (self.end_date - self.start_date).days + 1)
        avg_trades_per_day = total / days
        self.logger.info(f"- 平均每天交易次数: {avg_trades_per_day:.2f}")

        # 计算盈亏比
        pnl_won = trades.won.pnl.total
        pnl_lost = abs(trades.lost.pnl.total)
        win_loss_ratio = pnl_won / pnl_lost if pnl_lost > 0 else float('inf')
        self.logger.info(f"- 平均盈亏比: {win_loss_ratio:.2f}")

        # 盈利因子
        profit_factor = pnl_won / pnl_lost if pnl_lost > 0 else float('inf')
        self.logger.info(f"- 盈利因子: {profit_factor:.2f}")

        # 连续盈亏次数
        self.logger.info(f"- 最大连续盈利次数: {trades.streak.won.longest}")
        self.logger.info(f"- 最大连续亏损次数: {trades.streak.lost.longest}")

        # 平均收益和总收益
        self.logger.info(f"- 平均收益: {trades.pnl.net.average:.4f}")
        self.logger.info(f"- 总净利润: {trades.pnl.net.total:.4f}")

        self.logger.info("=" * 50)

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
                "夏普比率": 0.0 if results['performance']['sharpe_ratio'] is None else round(float(results['performance']['sharpe_ratio']), 3),
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
