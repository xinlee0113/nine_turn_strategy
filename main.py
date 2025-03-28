import os
import argparse
import backtrader as bt
from datetime import datetime, timedelta
import logging

from src.data_fetcher import DataFetcher
from src.magic_nine_strategy import MagicNineStrategy

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
        days = args.days if args.days <= 5 else 5  # 使用实际回测天数或最多5天
        logger.info(f"总交易次数: {total_trades}")
        logger.info(f"平均每天交易次数: {total_trades / days:.2f}")
        
        if hasattr(trade_analyzer, 'won') and hasattr(trade_analyzer.won, 'total'):
            winning_trades = trade_analyzer.won.total
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            logger.info(f"盈利交易次数: {winning_trades}")
            logger.info(f"胜率: {win_rate:.2f}%")
    
    # 绘制结果
    from matplotlib import rcParams
    rcParams['figure.figsize'] = 20, 10
    rcParams['font.size'] = 12
    rcParams['lines.linewidth'] = 2
    
    cerebro.plot(style='candlestick', barup='red', bardown='green', 
                 grid=True, plotdist=1.0, volume=True)

if __name__ == '__main__':
    main() 