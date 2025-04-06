import yaml
import pandas as pd
from src.strategies.magic_nine.base import MagicNineBaseStrategy
from src.backtest.engine import BacktestEngine

def load_config(config_path: str) -> dict:
    """加载配置文件"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def load_data(data_path: str) -> pd.DataFrame:
    """加载市场数据"""
    return pd.read_csv(data_path, index_col=0, parse_dates=True)

def main():
    # 加载配置
    config = load_config('configs/strategy/magic_nine.yaml')
    
    # 加载数据
    data = load_data('data/market_data/000001.SZ.csv')
    
    # 创建策略实例
    strategy = MagicNineBaseStrategy(config)
    
    # 创建回测引擎
    engine = BacktestEngine(strategy, data)
    
    # 运行回测
    results = engine.run()
    
    # 输出结果
    print(f"总收益率: {results['total_return']:.2f}%")
    print(f"年化收益率: {results['annual_return']:.2f}%")
    print(f"最大回撤: {results['max_drawdown']:.2f}%")
    print(f"夏普比率: {results['sharpe_ratio']:.2f}")
    print(f"交易次数: {len(results['trades'])}")

if __name__ == '__main__':
    main() 