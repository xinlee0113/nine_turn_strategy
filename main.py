import os
import argparse
import backtrader as bt
from datetime import datetime, timedelta
import logging
import json

from src.data_fetcher import DataFetcher
from src.magic_nine_strategy import MagicNineStrategy
from src.magic_nine_strategy_with_stoploss import MagicNineStrategyWithStopLoss
from src.magic_nine_strategy_with_advanced_stoploss import MagicNineStrategyWithAdvancedStopLoss
from src.magic_nine_strategy_with_smart_stoploss import MagicNineStrategyWithSmartStopLoss
from src.multi_asset_strategy import MultiAssetStrategy

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='神奇九转策略回测')
    parser.add_argument('--symbols', nargs='+', default=['QQQ', 'SPY'], help='要交易的股票代码')
    parser.add_argument('--days', type=int, default=30, help='回测天数')
    parser.add_argument('--cash', type=float, default=100000.0, help='初始资金')
    parser.add_argument('--commission', type=float, default=0.0, help='佣金率(默认0，不计费用)')
    parser.add_argument('--config', type=str, default='config', help='API配置文件路径')
    parser.add_argument('--key', type=str, default='config/private_key.pem', help='API私钥路径')
    parser.add_argument('--use-cache', action='store_true', help='使用缓存数据')
    parser.add_argument('--magic-period', type=int, default=2, help='神奇九转比较周期(默认2)')
    parser.add_argument('--multi-asset', action='store_true', help='使用多资产独立交易策略')
    
    # 止损策略选项
    stoploss_group = parser.add_argument_group('止损策略选项')
    stoploss_group.add_argument('--stop-loss', action='store_true', help='使用普通止损策略')
    stoploss_group.add_argument('--advanced-stop-loss', action='store_true', help='使用高级止损策略(基于ATR和追踪止损)')
    stoploss_group.add_argument('--smart-stop-loss', action='store_true', help='使用智能止损策略(自适应波动性、市场感知和时间衰减)')
    stoploss_group.add_argument('--stop-loss-pct', type=float, default=3.0, help='止损百分比(默认3%)')
    stoploss_group.add_argument('--atr-period', type=int, default=14, help='ATR周期(默认14)')
    stoploss_group.add_argument('--atr-multiplier', type=float, default=2.5, help='ATR乘数(默认2.5)')
    stoploss_group.add_argument('--min-profit-pct', type=float, default=1.0, help='启动追踪止损的最小盈利百分比(默认1%)')
    stoploss_group.add_argument('--no-trailing', action='store_true', help='禁用追踪止损功能')
    stoploss_group.add_argument('--risk-aversion', type=float, default=1.0, help='风险规避系数(0.5-2.0)，较高值增加止损紧密度')
    stoploss_group.add_argument('--time-decay-days', type=int, default=3, help='时间衰减开始的天数(默认3天)')
    stoploss_group.add_argument('--no-volatility-adjust', action='store_true', help='禁用波动性自适应调整')
    stoploss_group.add_argument('--no-market-aware', action='store_true', help='禁用市场环境感知')
    stoploss_group.add_argument('--no-time-decay', action='store_true', help='禁用时间衰减功能')
    
    parser.add_argument('--weights', type=str, default=None, 
                        help='资产权重，JSON格式，例如：\'{"QQQ": 0.6, "SPY": 0.4}\'')
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    # 创建缓存目录
    cache_dir = 'data/cache'
    os.makedirs(cache_dir, exist_ok=True)
    
    # 初始化数据获取器和回测引擎
    data_fetcher = DataFetcher(config_path=args.config, private_key_path=args.key, cache_dir=cache_dir)
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(args.cash)
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
    
    # 添加数据
    for symbol in args.symbols:
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
        
        # 获取数据并添加到回测引擎
        df = data_fetcher.get_bar_data(symbol, begin_time=start_date, end_time=end_date, use_cache=args.use_cache)
        data_file = data_fetcher.prepare_backtrader_data(symbol, df)
        
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
        cerebro.adddata(data, name=symbol)
    
    # 添加策略和分析器
    if args.multi_asset:
        logger.info("使用多资产独立交易策略")
        cerebro.addstrategy(MultiAssetStrategy, magic_period=args.magic_period, weights=weights)
    elif args.smart_stop_loss:
        logger.info(f"使用智能止损的神奇九转策略 (ATR周期: {args.atr_period}, ATR乘数: {args.atr_multiplier}, " 
                 f"最大止损: {args.stop_loss_pct}%, 追踪止损: {not args.no_trailing}, "
                 f"风险规避系数: {args.risk_aversion}, "
                 f"波动性自适应: {not args.no_volatility_adjust}, "
                 f"市场感知: {not args.no_market_aware}, "
                 f"时间衰减: {not args.no_time_decay})")
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
                         time_decay_days=args.time_decay_days)
    elif args.advanced_stop_loss:
        logger.info(f"使用高级止损的神奇九转策略 (ATR周期: {args.atr_period}, ATR乘数: {args.atr_multiplier}, " 
                 f"最大止损: {args.stop_loss_pct}%, 追踪止损: {not args.no_trailing})")
        cerebro.addstrategy(MagicNineStrategyWithAdvancedStopLoss, 
                         magic_period=args.magic_period,
                         atr_period=args.atr_period,
                         atr_multiplier=args.atr_multiplier,
                         max_loss_pct=args.stop_loss_pct,
                         min_profit_pct=args.min_profit_pct,
                         trailing_stop=not args.no_trailing)
    elif args.stop_loss:
        logger.info(f"使用普通止损的神奇九转策略 (止损比例: {args.stop_loss_pct}%)")
        cerebro.addstrategy(MagicNineStrategyWithStopLoss, magic_period=args.magic_period, stop_loss_pct=args.stop_loss_pct)
    else:
        logger.info("使用原始神奇九转策略")
        cerebro.addstrategy(MagicNineStrategy, magic_period=args.magic_period)
    
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    
    # 运行回测
    logger.info(f"初始资金: {cerebro.broker.getvalue():.2f}")
    results = cerebro.run()
    strategy = results[0]
    
    # 输出结果
    final_value = cerebro.broker.getvalue()
    logger.info(f"最终资金: {final_value:.2f}")
    logger.info(f"总收益率: {(final_value / args.cash - 1) * 100:.2f}%")
    
    # 输出交易分析
    trade_analyzer = strategy.analyzers.trade_analyzer.get_analysis()
    if hasattr(trade_analyzer, 'total'):
        total_trades = trade_analyzer.total.closed
        days = args.days
        logger.info(f"总交易次数: {total_trades}")
        logger.info(f"平均每天交易次数: {total_trades / days:.2f}")
        
        if hasattr(trade_analyzer, 'won') and hasattr(trade_analyzer.won, 'total'):
            winning_trades = trade_analyzer.won.total
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            logger.info(f"盈利交易次数: {winning_trades}")
            logger.info(f"胜率: {win_rate:.2f}%")
    
    # 绘制结果
    if len(args.symbols) <= 2:  # 只有少量标的时绘图，避免图表过于复杂
        from matplotlib import rcParams
        rcParams['figure.figsize'] = 20, 10
        rcParams['font.size'] = 12
        rcParams['lines.linewidth'] = 2
        
        # cerebro.plot(style='candlestick', barup='red', bardown='green', 
        #              grid=True, plotdist=1.0, volume=True)

if __name__ == '__main__':
    main() 