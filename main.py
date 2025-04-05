import os
import argparse
import backtrader as bt
from datetime import datetime, timedelta
import logging
import json
import sys
import numpy as np

from backtrader.observers import BuySell

from src.data_fetcher import DataFetcher
from src.magic_nine_strategy import MagicNineStrategy
from src.magic_nine_strategy_with_stoploss import MagicNineStrategyWithStopLoss
from src.magic_nine_strategy_with_advanced_stoploss import MagicNineStrategyWithAdvancedStopLoss
from src.magic_nine_strategy_with_smart_stoploss import MagicNineStrategyWithSmartStopLoss
from src.multi_asset_strategy import MultiAssetStrategy
from src.strategy_selector import StrategySelector, StrategyType
from src.market_analyzer import MarketAnalyzer
from src.adaptive_strategy import AdaptiveStrategy
from src.trading_fee_util import TradingFeeUtil
# 导入配置系统和参数优化器
from src.config_system import SymbolConfig, StrategyFactory
from src.parameter_optimizer import ParameterOptimizer
# 导入自定义分析器
from src.analyzers.sortino_ratio import SortinoRatio

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 自定义回撤分析器
class CustomDrawDown(bt.Analyzer):
    """自定义回撤分析器，确保计算正确的回撤值"""
    
    def __init__(self):
        self.peak = 0.0
        self.valley = float('inf')
        self.max_dd = 0.0
        self.max_dd_len = 0
        self.dd_len = 0
        
    def next(self):
        # 获取当前资金曲线值
        value = self.strategy.broker.getvalue()
        
        # 更新峰值
        if value > self.peak:
            self.peak = value
            self.dd_len = 0
        else:
            self.dd_len += 1
            
        # 计算回撤
        if self.peak > 0:
            dd = (self.peak - value) / self.peak
            if dd > self.max_dd:
                self.max_dd = dd
                self.max_dd_len = self.dd_len
        
    def get_analysis(self):
        return {'max': {'drawdown': self.max_dd, 'len': self.max_dd_len}}

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='神奇九转策略回测')
    parser.add_argument('--symbols', nargs='+', default=['QQQ'], help='要交易的股票代码')
    parser.add_argument('--days', type=int, default=30, help='回测天数')
    parser.add_argument('--cash', type=float, default=10000.0, help='初始资金')
    parser.add_argument('--commission', type=float, default=0.0000, help='佣金率(默认0，不计费用)')
    parser.add_argument('--config', type=str, default='config', help='API配置文件路径')
    parser.add_argument('--key', type=str, default='config/private_key.pem', help='API私钥路径')
    parser.add_argument('--use-cache', action='store_true', help='使用缓存数据，如果缓存存在直接使用缓存，不会调用API',default=True)
    parser.add_argument('--magic-period', type=int, default=3, help='神奇九转比较周期(默认2)')
    parser.add_argument('--multi-asset', action='store_true', help='使用多资产独立交易策略')
    parser.add_argument('--enable-short', action='store_true', help='启用做空交易',default=True)
    parser.add_argument('--no-plot', action='store_true', help='不显示回测图表',default=True)
    parser.add_argument('--verbose', action='store_true', help='显示详细日志')
    
    # 交易成本选项
    cost_group = parser.add_argument_group('交易成本选项')
    cost_group.add_argument('--real-costs', action='store_true', help='使用真实交易成本(佣金和滑点)')
    cost_group.add_argument('--broker-type', type=str, default='tiger', choices=['tiger', 'ib'], 
                           help='券商类型: tiger(老虎证券) or ib(盈透证券)')
    cost_group.add_argument('--monthly-volume', type=int, default=0, help='月度交易量(用于盈透证券分层佣金)')
    cost_group.add_argument('--commission-per-share', type=float, default=0.0039, help='每股佣金(美元)')
    cost_group.add_argument('--min-commission', type=float, default=0.99, help='最低佣金(美元)')
    cost_group.add_argument('--platform-fee-per-share', type=float, default=0.004, help='每股平台费(美元)')
    cost_group.add_argument('--min-platform-fee', type=float, default=1.0, help='最低平台费(美元)')
    cost_group.add_argument('--other-fees-per-share', type=float, default=0.00396, help='每股其他费用(美元)')
    cost_group.add_argument('--min-other-fees', type=float, default=0.99, help='最低其他费用(美元)')
    cost_group.add_argument('--slippage', type=float, default=0.0005, help='滑点(价格百分比)')
    
    # 止损策略选项
    stoploss_group = parser.add_argument_group('止损策略选项')
    stoploss_group.add_argument('--stop-loss', action='store_true', help='使用普通止损策略')
    stoploss_group.add_argument('--advanced-stop-loss', action='store_true', help='使用高级止损策略[基于ATR和追踪止损]')
    stoploss_group.add_argument('--smart-stop-loss', action='store_true', help='使用智能止损策略[自适应波动性、市场感知和时间衰减]')
    stoploss_group.add_argument('--stop-loss-pct', type=float, default=3.0, help='止损百分比[默认3%%]')
    stoploss_group.add_argument('--atr-period', type=int, default=14, help='ATR周期[默认14]')
    stoploss_group.add_argument('--atr-multiplier', type=float, default=2.5, help='ATR乘数[默认2.5]')
    stoploss_group.add_argument('--min-profit-pct', type=float, default=1.0, help='启动追踪止损的最小盈利百分比[默认1%%]')
    stoploss_group.add_argument('--no-trailing', action='store_true', help='禁用追踪止损功能')
    stoploss_group.add_argument('--risk-aversion', type=float, default=1.0, help='风险规避系数[0.5-2.0]，较高值增加止损紧密度')
    stoploss_group.add_argument('--time-decay-days', type=int, default=3, help='时间衰减开始的天数[默认3天]')
    stoploss_group.add_argument('--no-volatility-adjust', action='store_true', help='禁用波动性自适应调整')
    stoploss_group.add_argument('--no-market-aware', action='store_true', help='禁用市场环境感知')
    stoploss_group.add_argument('--no-time-decay', action='store_true', help='禁用时间衰减功能')
    
    # 自适应策略选项
    adaptive_group = parser.add_argument_group('自适应策略选项')
    adaptive_group.add_argument('--adaptive', action='store_true', help='使用自适应策略(动态切换原始、高级和智能止损策略)')
    adaptive_group.add_argument('--lookback-window', type=int, default=20, help='用于分析市场状态的回溯窗口')
    adaptive_group.add_argument('--volatility-threshold', type=float, default=0.015, help='波动率阈值，高于此值视为高波动')
    adaptive_group.add_argument('--trend-threshold', type=float, default=0.03, help='趋势强度阈值，高于此值视为强趋势')
    adaptive_group.add_argument('--rsi-threshold', type=int, default=70, help='RSI阈值，用于判断超买超卖')
    adaptive_group.add_argument('--strategy-switch-delay', type=int, default=3, help='策略切换延迟(防止频繁切换)')
    
    parser.add_argument('--weights', type=str, default=None, 
                        help='资产权重，JSON格式，例如：\'{"QQQ": 0.6, "SPY": 0.4}\'')
    
    # 配置系统相关参数
    config_group = parser.add_argument_group('配置选项')
    config_group.add_argument('--symbol-config', type=str, default='config/symbol_params.json',
                          help='标的参数配置文件路径(JSON格式)')
    config_group.add_argument('--generate-default-config', action='store_true',
                          help='生成默认配置文件并退出')
    config_group.add_argument('--use-config', action='store_true',
                          help='使用配置文件中的参数覆盖命令行参数')
    
    # 参数优化选项
    optimize_group = parser.add_argument_group('参数优化选项')
    optimize_group.add_argument('--optimize-params', action='store_true',
                             help='对指定标的进行参数优化')
    optimize_group.add_argument('--optimize-all', action='store_true',
                             help='优化所有标的的参数')
    optimize_group.add_argument('--optimize-strategy-types', action='store_true',
                             help='优化标的的策略类型')
    optimize_group.add_argument('--optimize-metrics', type=str, default='sharpe_ratio',
                             choices=['return', 'sharpe_ratio', 'sortino_ratio', 'drawdown', 'win_rate'],
                             help='优化指标 (默认: 夏普比率)')
    optimize_group.add_argument('--param-sets', type=int, default=20,
                             help='参数优化时测试的参数组合数量')
    optimize_group.add_argument('--optimization-output', type=str, default='logs/optimization',
                             help='优化结果输出目录')
    
    return parser.parse_args()

# 辅助函数：获取数据
def fetch_data(symbol, days, use_cache, data_fetcher):
    """获取回测数据"""
    # 计算日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # 如果使用缓存，输出使用缓存的信息
    if use_cache:
        logger.info(f"使用缓存模式获取数据: {symbol}")
    
    # 获取数据并准备用于backtrader
    df = data_fetcher.get_bar_data(symbol, begin_time=start_date, end_time=end_date, use_cache=use_cache)
    data_file = data_fetcher.prepare_backtrader_data(symbol, df)
    
    if data_file is None:
        logger.error(f"无法获取或准备 {symbol} 的数据")
        return None
    
    # 创建backtrader数据源
    data = bt.feeds.GenericCSVData(
        dataname=data_file,
        datetime=0,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        openinterest=-1,
        dtformat='%Y-%m-%d %H:%M:%S',
        timeframe=bt.TimeFrame.Minutes
    )
    return data

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
        
    # 确保日志目录存在
    os.makedirs("logs", exist_ok=True)
    
    # 添加文件处理器，以便记录日志到文件
    log_path = f"logs/backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)
    
    logger.info(f"日志将保存到: {log_path}")
    
    # 处理生成默认配置的情况
    if args.generate_default_config:
        config_path = args.symbol_config
        config = SymbolConfig()
        saved_path = config.save_config(config_path)
        logger.info(f"已生成默认配置文件: {saved_path}")
        sys.exit(0)
    
    # 创建缓存目录
    cache_dir = 'data/cache'
    os.makedirs(cache_dir, exist_ok=True)
    
    # 初始化数据获取器
    data_fetcher = DataFetcher(config_path=args.config, private_key_path=args.key, cache_dir=cache_dir)
    
    # 处理参数优化
    if args.optimize_params or args.optimize_all or args.optimize_strategy_types:
        optimizer = ParameterOptimizer(
            days=args.days,
            cash=args.cash,
            commission=args.commission,
            use_cache=args.use_cache,
            config_path=args.symbol_config,
            optimize_metrics=args.optimize_metrics,
            output_dir=args.optimization_output,
            api_config_path=args.config,
            api_key_path=args.key
        )
        
        if args.optimize_params:
            logger.info(f"开始为指定标的优化参数...")
            for symbol in args.symbols:
                optimizer.optimize_strategy_params(symbol)
        elif args.optimize_strategy_types:
            logger.info(f"开始为指定标的优化策略类型...")
            for symbol in args.symbols:
                optimizer.optimize_strategy_types(symbol)
        elif args.optimize_all:
            logger.info(f"开始为所有支持的标的优化参数...")
            optimizer.optimize_all_symbols()
        
        logger.info("参数优化完成")
        sys.exit(0)
    
    # 显示初始资金
    logger.info(f"初始资金: {args.cash:.2f}")
    
    # 创建Cerebro实例
    cerebro = bt.Cerebro(oldbuysell=True)
    
    # 设置初始资金
    cerebro.broker.setcash(args.cash)
    
    # 设置交易费用和滑点
    if args.real_costs:
        logger.info(f"使用真实交易成本(券商: {args.broker_type}, 滑点: {args.slippage})")
        
        # 创建自定义佣金计算类
        class CustomCommissionInfo(bt.CommInfoBase):
            params = (
                ('commission', 0.0),  # 我们将在comminfo方法中计算佣金
                ('broker_type', args.broker_type),
                ('monthly_volume', args.monthly_volume),
                ('commission_per_share', args.commission_per_share),
                ('min_commission', args.min_commission),
                ('platform_fee_per_share', args.platform_fee_per_share),
                ('min_platform_fee', args.min_platform_fee),
                ('other_fees_per_share', args.other_fees_per_share),
                ('min_other_fees', args.min_other_fees),
                ('stocklike', True),
                ('commtype', bt.CommInfoBase.COMM_FIXED),
                ('percabs', True),  # 使用绝对值计算
            )
            
            def _getcommission(self, size, price, pseudoexec):
                """计算总交易成本"""
                # 使用TradingFeeUtil计算交易费用
                if self.p.broker_type == 'ib':
                    return TradingFeeUtil.calculate_ib_fee(
                        price=price, 
                        quantity=abs(size), 
                        monthly_volume=self.p.monthly_volume,
                        is_buy=(size > 0)
                    )
                else:  # 默认使用老虎证券
                    return TradingFeeUtil.calculate_tiger_fee(
                        price=price, 
                        quantity=abs(size), 
                        is_buy=(size > 0)
                    )
        
        # 设置自定义佣金模型
        cerebro.broker.addcommissioninfo(CustomCommissionInfo())
        
        # 设置滑点
        cerebro.broker.set_slippage_perc(args.slippage)
        
    else:
        # 使用简单佣金模型
        cerebro.broker.setcommission(commission=args.commission)
        # 设置滑点为0
        cerebro.broker.set_slippage_perc(0.0)
    
    # 解析权重参数
    weights = None
    if args.weights:
        try:
            weights = json.loads(args.weights)
            logger.info(f"使用自定义资产权重: {weights}")
        except json.JSONDecodeError:
            logger.error(f"权重解析错误，请使用正确的JSON格式。使用平均权重。")
    
    # 加载配置
    symbol_config = SymbolConfig.load_config(args.symbol_config)
    strategy_factory = StrategyFactory(symbol_config)
    
    # 处理回测
    if args.adaptive:
        logger.info("使用自适应策略(动态策略选择)")
        
        # 添加数据
        for symbol in args.symbols:
            data = fetch_data(symbol, args.days, args.use_cache, data_fetcher)
            if data is None:
                continue
            cerebro.adddata(data, name=symbol)
        
        # 初始化市场分析器
        market_analyzer = MarketAnalyzer(
            lookback_window=args.lookback_window,
            rsi_threshold=args.rsi_threshold,
            vix_threshold=args.volatility_threshold * 100  # 转换为百分比
        )
        
        # 初始化策略选择器，将市场分析器传入
        strategy_selector = StrategySelector(
            market_analyzer=market_analyzer,
            lookback_window=args.lookback_window,
            volatility_threshold=args.volatility_threshold,
            trend_threshold=args.trend_threshold
        )
        
        # 添加自适应策略
        cerebro.addstrategy(
            AdaptiveStrategy,
            magic_period=args.magic_period,
            strategy_selector=strategy_selector,
            market_analyzer=market_analyzer,
            switch_delay=args.strategy_switch_delay,
            # 止损参数
            atr_period=args.atr_period,
            atr_multiplier=args.atr_multiplier,
            stop_loss_pct=args.stop_loss_pct,
            min_profit_pct=args.min_profit_pct,
            trailing_stop=not args.no_trailing,
            risk_aversion=args.risk_aversion,
            volatility_adjust=not args.no_volatility_adjust,
            market_aware=not args.no_market_aware,
            time_decay=not args.no_time_decay,
            time_decay_days=args.time_decay_days,
            enable_short=args.enable_short
        )
    elif args.multi_asset and len(args.symbols) > 1:
        # 多资产模式 - 为每个标的创建独立的策略实例
        logger.info("使用多资产独立交易策略(基于配置)")
        
        for symbol in args.symbols:
            # 获取数据
            data = fetch_data(symbol, args.days, args.use_cache, data_fetcher)
            if data is None:
                continue
            
            # 添加数据
            data_feed = cerebro.adddata(data, name=symbol)
            
            # 获取标的特定的策略和参数
            strategy_class, strategy_params = strategy_factory.create_strategy(symbol)
            
            # 命令行参数可以覆盖配置文件中的参数
            if args.magic_period and not args.use_config:
                strategy_params['magic_period'] = args.magic_period
                
            # 根据命令行选项设置策略
            if args.advanced_stop_loss and not args.use_config:
                strategy_params['strategy_type'] = 'advanced_stoploss'
            elif args.smart_stop_loss and not args.use_config:
                strategy_params['strategy_type'] = 'smart_stoploss'
            elif args.stop_loss and not args.use_config:
                strategy_params['strategy_type'] = 'stoploss'
            
            # 设置做空选项
            if not args.use_config:
                strategy_params['enable_short'] = args.enable_short
            
            # 设置追踪止损选项
            if args.no_trailing and not args.use_config:
                strategy_params['trailing_stop'] = False
            
            # 再次过滤参数以确保兼容性
            for key in list(strategy_params.keys()):
                try:
                    # 尝试访问参数，如果不存在会抛出异常
                    getattr(strategy_class.params, key)
                except AttributeError:
                    logger.debug(f"参数 {key} 不适用于策略类 {strategy_class.__name__}，将被忽略")
                    strategy_params.pop(key, None)
            
            # 创建策略并关联特定的数据
            cerebro.addstrategy(strategy_class, data=data_feed, **strategy_params)
            
            logger.info(f"已添加标的 {symbol} 使用 {strategy_class.__name__} 参数: {strategy_params}")
    else:
        # 添加数据
        for symbol in args.symbols:
            data = fetch_data(symbol, args.days, args.use_cache, data_fetcher)
            if data is None:
                continue
            cerebro.adddata(data, name=symbol)
                
        # 单资产或简单多资产模式
        if len(args.symbols) == 1 and (args.use_config or not (args.advanced_stop_loss or args.smart_stop_loss or args.stop_loss)):
            # 使用配置文件中的参数
            symbol = args.symbols[0]
            strategy_class, strategy_params = strategy_factory.create_strategy(symbol)
            
            # 命令行参数可以覆盖配置文件中的参数
            if not args.use_config:
                if args.magic_period:
                    strategy_params['magic_period'] = args.magic_period
                if args.atr_period:
                    strategy_params['atr_period'] = args.atr_period
                if args.atr_multiplier:
                    strategy_params['atr_multiplier'] = args.atr_multiplier
                if args.stop_loss_pct:
                    strategy_params['max_loss_pct'] = args.stop_loss_pct
                
                # 设置做空选项
                strategy_params['enable_short'] = args.enable_short
                
                # 设置追踪止损选项
                if args.no_trailing:
                    strategy_params['trailing_stop'] = False
            
            # 再次过滤参数以确保兼容性
            for key in list(strategy_params.keys()):
                try:
                    # 尝试访问参数，如果不存在会抛出异常
                    getattr(strategy_class.params, key)
                except AttributeError:
                    logger.debug(f"参数 {key} 不适用于策略类 {strategy_class.__name__}，将被忽略")
                    strategy_params.pop(key, None)
            
            # 添加策略
            cerebro.addstrategy(strategy_class, **strategy_params)
            
            logger.info(f"使用策略 {strategy_class.__name__} 参数: {strategy_params}")
        else:
            # 使用命令行指定的策略参数
            if args.smart_stop_loss:
                logger.info(f"使用智能止损的神奇九转策略 [ATR周期: {args.atr_period}, ATR乘数: {args.atr_multiplier}, " 
                        f"最大止损: {args.stop_loss_pct}%%, 追踪止损: {not args.no_trailing}, "
                        f"风险规避系数: {args.risk_aversion}, "
                        f"波动性自适应: {not args.no_volatility_adjust}, "
                        f"市场感知: {not args.no_market_aware}, "
                        f"时间衰减: {not args.no_time_decay}, "
                        f"做空交易: {args.enable_short}]")
                cerebro.addstrategy(MagicNineStrategyWithSmartStopLoss, 
                                magic_period=args.magic_period,
                                atr_period=args.atr_period,
                                atr_multiplier=args.atr_multiplier,
                                max_loss_pct=args.stop_loss_pct,
                                min_profit_pct=args.min_profit_pct,
                                trailing_stop=not args.no_trailing,
                                risk_aversion=args.risk_aversion,
                                volatility_adjust=not args.no_volatility_adjust,
                                market_aware=not args.no_market_aware,
                                time_decay=not args.no_time_decay,
                                time_decay_days=args.time_decay_days,
                                enable_short=args.enable_short)
            elif args.advanced_stop_loss:
                logger.info(f"使用高级止损的神奇九转策略 [ATR周期: {args.atr_period}, ATR乘数: {args.atr_multiplier}, " 
                        f"最大止损: {args.stop_loss_pct}%%, 追踪止损: {not args.no_trailing}, "
                        f"做空交易: {args.enable_short}]")
                cerebro.addstrategy(MagicNineStrategyWithAdvancedStopLoss, 
                                magic_period=args.magic_period,
                                atr_period=args.atr_period,
                                atr_multiplier=args.atr_multiplier,
                                max_loss_pct=args.stop_loss_pct,
                                min_profit_pct=args.min_profit_pct,
                                trailing_stop=not args.no_trailing,
                                enable_short=args.enable_short)
            elif args.stop_loss:
                logger.info(f"使用普通止损的神奇九转策略 [止损比例: {args.stop_loss_pct}%%, 做空交易: {args.enable_short}]")
                cerebro.addstrategy(MagicNineStrategyWithStopLoss, 
                               magic_period=args.magic_period, 
                               stop_loss_pct=args.stop_loss_pct, 
                               enable_short=args.enable_short)
            else:
                # 原始策略
                logger.info(f"使用原始神奇九转策略 [做空交易: {args.enable_short}]")
                cerebro.addstrategy(MagicNineStrategy, 
                                magic_period=args.magic_period, 
                                stop_loss_pct=args.stop_loss_pct,
                                enable_short=args.enable_short)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio', 
                        riskfreerate=0.0, 
                        annualize=True, 
                        timeframe=bt.TimeFrame.Days,
                        compression=1440)
    cerebro.addanalyzer(SortinoRatio, _name='sortino_ratio',
                        riskfreerate=0.0,
                        annualize=True,
                        timeframe=bt.TimeFrame.Days)  # 使用自定义索提诺比率分析器
    cerebro.addanalyzer(bt.analyzers.Calmar, _name='calmar',
                        timeframe=bt.TimeFrame.Days)  # 卡尔玛比率
    cerebro.addanalyzer(CustomDrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')  # 用于计算各种收益率指标
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual')  # 年化收益率
    cerebro.addanalyzer(bt.analyzers.PeriodStats, _name='period_stats')  # 周期统计
    cerebro.addobserver(BuySell)
    
    # 运行回测
    logger.info(f"初始资金: {cerebro.broker.getvalue():.2f}")
    results = cerebro.run()
    strategy = results[0]
    
    # 输出结果
    final_value = cerebro.broker.getvalue()
    total_return_pct = (final_value / args.cash - 1) * 100
    
    logger.info(f"最终资金: {final_value:.2f}")
    logger.info(f"总收益率: {total_return_pct:.2f}%")
    
    # 获取分析结果
    sharpe = strategy.analyzers.sharpe_ratio.get_analysis()
    if sharpe:
        sharpe_ratio = sharpe.get('sharperatio', 0.0)
        if sharpe_ratio is not None and np.isfinite(sharpe_ratio):
            logger.info(f"夏普比率: {sharpe_ratio:.4f}")
        else:
            logger.info("夏普比率: 无效")
            
    # 添加索提诺比率
    sortino = strategy.analyzers.sortino_ratio.get_analysis()
    if sortino:
        sortino_ratio = sortino.get('sortinoratio', 0.0)  # 使用正确的键名'sortinoratio'
        if sortino_ratio is not None and np.isfinite(sortino_ratio):
            logger.info(f"索提诺比率: {sortino_ratio:.4f}")
        else:
            logger.info("索提诺比率: 无效")
    
    # 使用自定义回撤分析器结果
    drawdown = strategy.analyzers.drawdown.get_analysis()
    if drawdown:
        raw_drawdown = drawdown.get('max', {}).get('drawdown', 0.0)
        max_drawdown = raw_drawdown * 100  # 正确转换为百分比
        max_dd_len = drawdown.get('max', {}).get('len', 0)
        logger.info(f"最大回撤: {max_drawdown:.2f}%，持续周期: {max_dd_len}")
            
    # 添加卡尔玛比率
    calmar = strategy.analyzers.calmar.get_analysis()
    if calmar:
        calmar_ratio = calmar.get('calmar', 0.0)
        if calmar_ratio is not None and np.isfinite(calmar_ratio):
            logger.info(f"卡尔玛比率: {calmar_ratio:.4f}")
        else:
            logger.info("卡尔玛比率: 无效")
            
    # 添加年化收益率
    annual = strategy.analyzers.annual.get_analysis()
    if annual:
        # 显示最近一年的年化收益率，或者整个回测期间的平均年化收益率
        years = list(annual.keys())
        if years:
            latest_year = max(years)
            annual_return = annual[latest_year] * 100
            logger.info(f"年化收益率: {annual_return:.2f}%")
                
    # 获取周期统计数据
    period_stats = strategy.analyzers.period_stats.get_analysis()
    if period_stats:
        if 'rnorm100' in period_stats:
            norm_return = period_stats['rnorm100']
            logger.info(f"标准化百日收益率: {norm_return:.2f}%")
        if 'volatility' in period_stats:
            volatility = period_stats['volatility'] * 100
            logger.info(f"价格波动率: {volatility:.2f}%")

    trade_analyzer = strategy.analyzers.trade_analyzer.get_analysis()
    
    # 简单检查是否有交易发生（更安全的方式）
    if trade_analyzer:  # 如果有分析结果
        if 'total' in trade_analyzer and 'closed' in trade_analyzer.total:
            total_trades = trade_analyzer.total.closed
            days = args.days
            logger.info(f"总交易次数: {total_trades}")
            logger.info(f"平均每天交易次数: {total_trades / days:.2f}")
            
            if 'won' in trade_analyzer and 'total' in trade_analyzer.won:
                winning_trades = trade_analyzer.won.total
                win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
                logger.info(f"盈利交易次数: {winning_trades}")
                logger.info(f"胜率: {win_rate:.2f}%")
                
                # 添加平均盈亏比
                avg_won = trade_analyzer.won.pnl.average if hasattr(trade_analyzer.won, 'pnl') and hasattr(trade_analyzer.won.pnl, 'average') else 0
                avg_lost = trade_analyzer.lost.pnl.average if hasattr(trade_analyzer.lost, 'pnl') and hasattr(trade_analyzer.lost.pnl, 'average') else 0
                if avg_lost < 0:  # 确保分母为负数转为正数
                    profit_loss_ratio = abs(avg_won / avg_lost) if avg_lost != 0 else float('inf')
                    logger.info(f"平均盈亏比: {profit_loss_ratio:.2f}")
                
                # 添加盈利因子
                gross_won = trade_analyzer.won.pnl.total if hasattr(trade_analyzer.won, 'pnl') and hasattr(trade_analyzer.won.pnl, 'total') else 0
                gross_lost = trade_analyzer.lost.pnl.total if hasattr(trade_analyzer.lost, 'pnl') and hasattr(trade_analyzer.lost.pnl, 'total') else 0
                if gross_lost < 0:  # 确保分母为负数转为正数
                    profit_factor = abs(gross_won / gross_lost) if gross_lost != 0 else float('inf')
                    logger.info(f"盈利因子: {profit_factor:.2f}")
                
                # 添加期望收益
                expected_return = (win_rate/100 * avg_won) + ((100-win_rate)/100 * avg_lost)
                logger.info(f"每笔交易期望收益: {expected_return:.2f}")
                
                # 添加最大连续盈利和亏损次数
                max_win_streak = trade_analyzer.streak.won.longest if hasattr(trade_analyzer, 'streak') and hasattr(trade_analyzer.streak, 'won') and hasattr(trade_analyzer.streak.won, 'longest') else 0
                max_loss_streak = trade_analyzer.streak.lost.longest if hasattr(trade_analyzer, 'streak') and hasattr(trade_analyzer.streak, 'lost') and hasattr(trade_analyzer.streak.lost, 'longest') else 0
                logger.info(f"最大连续盈利次数: {max_win_streak}")
                logger.info(f"最大连续亏损次数: {max_loss_streak}")
        else:
            logger.info("没有交易发生")
    else:
        logger.info("没有交易分析数据")
    
    # 输出SQN
    sqn_analyzer = strategy.analyzers.sqn.get_analysis()
    if sqn_analyzer:
        sqn_value = sqn_analyzer.get('sqn', 0.0)
        if np.isfinite(sqn_value):
            logger.info(f"系统质量指标(SQN): {sqn_value:.4f}")
    
    # 如果使用了自适应策略，输出策略切换统计信息
    if args.adaptive and hasattr(strategy, 'strategy_switches'):
        strategy_switches = strategy.strategy_switches
        logger.info(f"策略切换次数: {len(strategy_switches)}")
        strategy_usage = strategy.strategy_usage_count
        total_bars = sum(strategy_usage.values())
        
        for strategy_type, count in strategy_usage.items():
            usage_pct = (count / total_bars) * 100 if total_bars > 0 else 0
            logger.info(f"策略 {strategy_type.value} 使用比例: {usage_pct:.2f}%")
        
        logger.info("策略切换详情:")
        for i, switch in enumerate(strategy_switches[:10]):  # 只显示前10个切换
            logger.info(f"  {i+1}. 日期: {switch['date']} 从 {switch['from'].value} 切换到 {switch['to'].value} 原因: {switch['reason']}")
        
        if len(strategy_switches) > 10:
            logger.info(f"  ... 共 {len(strategy_switches)} 次切换")
    
    # 绘制结果
    if len(args.symbols) <= 2 and not args.no_plot:  # 只有少量标的且不禁用绘图时才绘图
        from matplotlib import rcParams
        rcParams['figure.figsize'] = 20, 10
        rcParams['font.size'] = 12
        rcParams['lines.linewidth'] = 2

        cerebro.plot(barup='red', bardown='green',
                     grid=True, plotdist=1.0, volume=True)

if __name__ == '__main__':
    main() 