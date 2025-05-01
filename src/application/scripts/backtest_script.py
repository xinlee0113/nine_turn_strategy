"""
回测脚本
负责回测流程的控制，按照架构图中的回测流程实现
"""
import logging
import os
from datetime import datetime, timedelta
import csv

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
        data = TigerCsvData(symbol=symbol)
        data.p.store = store
        
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
        self.log_results(analysis_results)
        
        # 保存回测结果
        result_file = self._save_results(analysis_results, symbol)
        
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
            try:
                # 运行单个标的回测
                result = self.run_single_symbol(symbol, enable_plot)
                
                # 保存结果
                self.all_results[symbol] = result
                
                self.logger.info(f"标的 {symbol} 回测完成")
            except Exception as e:
                self.logger.error(f"标的 {symbol} 回测失败: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
        
        # 生成多标的汇总报告
        self._generate_summary_report()
        
        return self.all_results

    def _plot_results(self, symbol, results):
        """绘制回测结果图表
        
        Args:
            symbol: 标的
            results: 回测结果
        """
        try:
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
        except Exception as e:
            self.logger.error(f"绘制 {symbol} 图表失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())

    def _save_results(self, results, symbol=None):
        """
        保存回测结果到CSV文件
        
        Args:
            results: 回测结果
            symbol: 标的，如果为None则使用self.symbol
            
        Returns:
            保存的文件路径
        """
        try:
            # 创建结果目录
            os.makedirs('results/backtest', exist_ok=True)

            # 获取基本参数
            symbol = symbol or getattr(self, 'symbol', 'unknown')
            strategy_name = self.strategy.__name__ if hasattr(self.strategy, '__name__') else 'unknown'
            start_date_str = getattr(self, 'start_date', 'unknown')
            end_date_str = getattr(self, 'end_date', 'unknown')
            period = getattr(self, 'period', 'unknown')

            if isinstance(start_date_str, datetime):
                start_date_str = start_date_str.strftime("%Y%m%d")
            if isinstance(end_date_str, datetime):
                end_date_str = end_date_str.strftime("%Y%m%d")
                
            # 添加交易开始和结束时间信息
            if hasattr(self, 'start_time'):
                results['start_time'] = self.start_time.strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(self, 'end_time'):
                results['end_time'] = self.end_time.strftime("%Y-%m-%d %H:%M:%S")

            # 添加标的信息
            results['symbol'] = symbol

            # 直接将results传递给save_backtest_results函数
            result_file = save_backtest_results(
                results,
                symbol,
                strategy_name,
                start_date_str,
                end_date_str,
                period
            )
            
            self.logger.info(f"{symbol} 回测结果已保存到文件: {result_file}")
            return result_file

        except Exception as e:
            self.logger.error(f"保存 {symbol} 回测结果失败: {str(e)}")
            import traceback
            self.logger.error(f"错误详情: {traceback.format_exc()}")
            return None

    def _generate_summary_report(self):
        """生成多标的回测结果汇总报告"""
        if not self.all_results:
            self.logger.warning("没有回测结果，无法生成汇总报告")
            return
        
        try:
            # 创建结果目录
            summary_dir = "results/backtest/summary"
            os.makedirs(summary_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_filename = f"{timestamp}_multi_symbol_summary.csv"
            summary_path = os.path.join(summary_dir, summary_filename)
            
            # 准备汇总数据
            summary_data = []
            
            # 关键指标列表 - 扩展包含更多指标
            key_metrics = [
                # 性能指标
                "总收益率", "年化收益率", "夏普比率", 
                # 系统质量指标
                "SQN值", "系统质量评级", 
                # 风险指标
                "最大回撤", "最大回撤持续时间", "波动率", "索提诺比率", "卡尔玛比率",
                # 交易统计
                "总交易次数", "盈利交易", "亏损交易", "胜率", "交易天数", "平均每天交易次数", 
                "平均盈亏比", "盈利因子", "最大连续盈利次数", "最大连续亏损次数", 
                "平均收益", "总净利润"
            ]
            
            # 收集所有标的的关键指标
            for symbol, results in self.all_results.items():
                symbol_data = {"标的": symbol}
                
                # 提取性能指标
                perf = results.get('performance', {})
                symbol_data["总收益率"] = f"{perf.get('total_return', 0) * 100:.2f}%"
                symbol_data["年化收益率"] = f"{perf.get('annual_return', 0) * 100:.2f}%"
                symbol_data["夏普比率"] = f"{float(perf.get('sharpe_ratio', 0) or 0):.4f}"
                
                # 提取系统质量指标
                sqn = results.get('sqn', {})
                symbol_data["SQN值"] = f"{sqn.get('sqn', 0):.4f}"
                symbol_data["系统质量评级"] = sqn.get('system_quality', '未评级')
                
                # 提取风险指标
                risk = results.get('risk', {})
                symbol_data["最大回撤"] = f"{risk.get('max_drawdown', 0) * 100:.2f}%"
                symbol_data["最大回撤持续时间"] = risk.get('max_drawdown_duration', 0)
                symbol_data["波动率"] = f"{risk.get('volatility', 0) * 100:.2f}%"
                symbol_data["索提诺比率"] = f"{risk.get('sortino_ratio', 0):.4f}"
                symbol_data["卡尔玛比率"] = f"{risk.get('calmar_ratio', 0):.4f}"
                
                # 提取交易指标
                trades = results.get('trades', {})
                
                # 基础交易数量统计
                total_trades = trades.get('total', {}).get('total', 0)
                symbol_data["总交易次数"] = total_trades
                
                won_trades = trades.get('won', {}).get('total', 0)
                lost_trades = trades.get('lost', {}).get('total', 0)
                symbol_data["盈利交易"] = won_trades
                symbol_data["亏损交易"] = lost_trades
                
                # 胜率计算
                win_rate = won_trades / total_trades * 100 if total_trades > 0 else 0
                symbol_data["胜率"] = f"{win_rate:.2f}%"
                
                # 交易频率统计
                symbol_data["交易天数"] = trades.get('trading_days', 0)
                symbol_data["平均每天交易次数"] = f"{trades.get('avg_trades_per_day', 0):.2f}"
                
                # 盈亏统计
                pnl_won = trades.get('won', {}).get('pnl', {}).get('total', 0)
                pnl_lost = abs(trades.get('lost', {}).get('pnl', {}).get('total', 0))
                
                # 计算盈亏比
                win_loss_ratio = pnl_won / pnl_lost if pnl_lost > 0 else float('inf')
                symbol_data["平均盈亏比"] = f"{win_loss_ratio:.2f}"
                
                # 计算盈利因子
                profit_factor = pnl_won / pnl_lost if pnl_lost > 0 else float('inf')
                symbol_data["盈利因子"] = f"{profit_factor:.2f}"
                
                # 连续盈亏记录
                symbol_data["最大连续盈利次数"] = trades.get('streak', {}).get('won', {}).get('longest', 0)
                symbol_data["最大连续亏损次数"] = trades.get('streak', {}).get('lost', {}).get('longest', 0)
                
                # 平均收益和总净利润
                symbol_data["平均收益"] = f"{trades.get('pnl', {}).get('net', {}).get('average', 0):.4f}"
                symbol_data["总净利润"] = f"{trades.get('pnl', {}).get('net', {}).get('total', 0):.4f}"
                
                # 添加到汇总数据
                summary_data.append(symbol_data)
            
            # 写入CSV文件
            with open(summary_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["标的"] + key_metrics)
                writer.writeheader()
                writer.writerows(summary_data)
            
            self.logger.info(f"多标的回测汇总报告已保存至: {summary_path}")
            
            # 打印汇总结果 - 扩展显示更多指标
            self.logger.info("==================================================")
            for symbol_data in summary_data:
                self.logger.info(f"标的: {symbol_data['标的']}")
                
                # 性能指标
                self.logger.info("性能指标:")
                self.logger.info(f"- 总收益率: {symbol_data['总收益率']}")
                self.logger.info(f"- 年化收益率: {symbol_data['年化收益率']}")
                self.logger.info(f"- 夏普比率: {symbol_data['夏普比率']}")
                
                # 系统质量指标
                self.logger.info("系统质量指标:")
                self.logger.info(f"- SQN值: {symbol_data['SQN值']}")
                self.logger.info(f"- 系统质量评级: {symbol_data['系统质量评级']}")
                self.logger.info(f"- 总交易次数: {symbol_data['总交易次数']}")
                
                # 风险指标
                self.logger.info("风险指标:")
                self.logger.info(f"- 最大回撤: {symbol_data['最大回撤']}")
                self.logger.info(f"- 最大回撤持续时间: {symbol_data['最大回撤持续时间']} 个数据点")
                self.logger.info(f"- 波动率: {symbol_data['波动率']}")
                self.logger.info(f"- 索提诺比率: {symbol_data['索提诺比率']}")
                self.logger.info(f"- 卡尔玛比率: {symbol_data['卡尔玛比率']}")
                
                # 交易统计
                self.logger.info("交易统计:")
                self.logger.info(f"- 总交易次数: {symbol_data['总交易次数']}")
                self.logger.info(f"- 盈利交易: {symbol_data['盈利交易']}")
                self.logger.info(f"- 亏损交易: {symbol_data['亏损交易']}")
                self.logger.info(f"- 胜率: {symbol_data['胜率']}")
                self.logger.info(f"- 交易天数: {symbol_data['交易天数']} 天")
                self.logger.info(f"- 平均每天交易次数: {symbol_data['平均每天交易次数']}")
                self.logger.info(f"- 平均盈亏比: {symbol_data['平均盈亏比']}")
                self.logger.info(f"- 盈利因子: {symbol_data['盈利因子']}")
                self.logger.info(f"- 最大连续盈利次数: {symbol_data['最大连续盈利次数']}")
                self.logger.info(f"- 最大连续亏损次数: {symbol_data['最大连续亏损次数']}")
                self.logger.info(f"- 平均收益: {symbol_data['平均收益']}")
                self.logger.info(f"- 总净利润: {symbol_data['总净利润']}")
                
                self.logger.info("==================================================")
            
        except Exception as e:
            self.logger.error(f"生成多标的回测汇总报告失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())

    def stop(self):
        """停止回测"""
        self.logger.info("停止回测")
        if self.data_source:
            self.data_source.stop()
        if self.cerebro:
            self.cerebro.stop()
        self.logger.info("回测停止完成")
