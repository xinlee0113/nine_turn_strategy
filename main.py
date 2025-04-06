import argparse
import logging
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from src.core.backtest_engine import BacktestEngine
from src.config import Config
from src.strategy.strategy_factory import StrategyType

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='神奇九转策略回测系统')
    
    # 基本参数
    parser.add_argument('--symbols', nargs='+', default=['QQQ'], help='要交易的股票代码')
    parser.add_argument('--days', type=int, default=30, help='回测天数')
    parser.add_argument('--cash', type=float, default=10000.0, help='初始资金')
    parser.add_argument('--commission', type=float, default=0.001, help='佣金率')
    parser.add_argument('--use-cache', action='store_true', help='使用缓存数据')
    
    # 策略参数
    parser.add_argument('--strategy-type', type=str, choices=['basic', 'stoploss', 'magic_nine'],
                       default='basic', help='策略类型')
    parser.add_argument('--magic-period', type=int, default=3, help='神奇九转周期')
    parser.add_argument('--enable-short', action='store_true', help='启用做空交易')
    
    # 止损参数
    parser.add_argument('--stop-loss-pct', type=float, default=3.0, help='止损百分比')
    parser.add_argument('--trailing-stop', action='store_true', help='启用追踪止损')
    parser.add_argument('--atr-period', type=int, default=14, help='ATR周期')
    parser.add_argument('--atr-multiplier', type=float, default=2.5, help='ATR乘数')
    
    # 配置参数
    parser.add_argument('--config', type=str, default='config/backtest_config.json',
                       help='配置文件路径')
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='日志级别')
    
    return parser.parse_args()

def setup_logging(log_level: str) -> None:
    """设置日志配置"""
    # 创建日志目录
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # 设置日志文件
    log_file = log_dir / f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 设置日志
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # 加载配置
        config = Config(args.config)
        logger.info(f"已加载配置文件: {args.config}")
        
        # 创建回测引擎
        engine = BacktestEngine(
            symbols=args.symbols,
            initial_cash=args.cash,
            commission=args.commission
        )
        
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
        
        # 添加数据
        for symbol in args.symbols:
            engine.add_data(symbol, start_date, end_date)
        
        # 准备策略参数
        strategy_params = {
            'magic_period': args.magic_period,
            'enable_short': args.enable_short,
            'stop_loss_pct': args.stop_loss_pct,
            'trailing_stop': args.trailing_stop,
            'atr_period': args.atr_period,
            'atr_multiplier': args.atr_multiplier
        }
        
        # 设置策略
        engine.set_strategy(args.strategy_type, **strategy_params)
        
        # 运行回测
        results = engine.run()
        if not results:
            logger.error("回测执行失败")
            sys.exit(1)
            
        logger.info("回测完成")
        
    except Exception as e:
        logger.error(f"程序执行过程中发生错误: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 