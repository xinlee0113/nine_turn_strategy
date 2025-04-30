"""
主程序入口
负责初始化日志、配置，启动应用
"""
import argparse
import logging
import os
import sys

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 导入脚本管理器
from src.application.script_manager import ScriptManager
from src.infrastructure.constants.const import (
    DEFAULT_INITIAL_CAPITAL,
    DEFAULT_COMMISSION_RATE
)


def setup_logging(log_level: str = "INFO"):
    """设置日志配置
    
    Args:
        log_level: 日志级别
    """
    # 设置日志级别
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')

    # 配置日志格式
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='九转战略量化交易系统')

    # 运行模式
    parser.add_argument('--mode', type=str, choices=['backtest', 'optimize', 'trade'],
                        default='backtest', help='运行模式')

    # 基本参数
    parser.add_argument('--cash', type=float, default=DEFAULT_INITIAL_CAPITAL, help='初始资金')
    parser.add_argument('--commission', type=float, default=DEFAULT_COMMISSION_RATE, help='佣金率')

    parser.add_argument('--symbols', type=str, default='QQQ', help='标的')

    # 绘图参数
    parser.add_argument('--plot', action='store_true', help='启用绘图功能')

    # 配置参数
    parser.add_argument('--strategy-config', type=str, default='configs/strategy/magic_nine.yaml',
                        help='策略配置文件路径')
    parser.add_argument('--data-config', type=str, default='configs/data/data_config.yaml',
                        help='数据配置文件路径')
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        default='INFO', help='日志级别')

    return parser.parse_args()


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()

    # 设置日志
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    logger.info("九转战略量化交易系统启动")

    # 创建脚本管理器
    script_manager = ScriptManager()

    # 根据运行模式执行不同的操作
    symbols = args.symbols.split(',')
    if args.mode == 'backtest':
        logger.info("运行回测模式")

        # 处理绘图参数
        if args.plot:
            logger.info("将启用绘图功能")

        # 通过脚本管理器运行回测脚本
        results = script_manager.run_backtest(enable_plot=args.plot)

        if not results:
            logger.error("回测执行失败")
            sys.exit(1)

        logger.info("回测完成")

    elif args.mode == 'optimize':
        logger.info("运行参数优化模式")

        # 这里应该添加参数优化逻辑，暂时省略
        logger.warning("参数优化模式尚未实现")
        sys.exit(0)

    elif args.mode == 'trade':
        logger.info("运行实盘交易模式")
        script_manager.run_live_trade(symbols)
        # 这里应该添加实盘交易逻辑，暂时省略
        logger.warning("实盘交易模式尚未实现")
        sys.exit(0)

    else:
        logger.error(f"不支持的运行模式: {args.mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
