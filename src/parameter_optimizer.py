import backtrader as bt
import pandas as pd
import logging
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
import os
import itertools
from datetime import datetime, timedelta

from src.config_system import SymbolConfig
from src.magic_nine_strategy import MagicNineStrategy
from src.magic_nine_strategy_with_advanced_stoploss import MagicNineStrategyWithAdvancedStopLoss
from src.magic_nine_strategy_with_smart_stoploss import MagicNineStrategyWithSmartStopLoss
from src.data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

class ParameterOptimizer:
    """参数优化器，用于优化策略参数"""
    
    def __init__(self, 
                 days: int = 30, 
                 cash: float = 10000.0,
                 commission: float = 0.0001,
                 use_cache: bool = True,
                 config_path: str = 'config/symbol_params.json',
                 optimize_metrics: str = 'sharpe_ratio',
                 output_dir: str = 'logs/optimization',
                 api_config_path: str = 'config',
                 api_key_path: str = 'config/private_key.pem'):
        """初始化参数优化器
        
        Args:
            days: 回测天数
            cash: 初始资金
            commission: 佣金率
            use_cache: 是否使用缓存数据
            config_path: 配置文件路径
            optimize_metrics: 优化指标，可选值: 'return', 'sharpe_ratio', 'sortino_ratio'
            output_dir: 优化结果输出目录
            api_config_path: Tiger API 配置文件路径
            api_key_path: Tiger API 私钥路径
        """
        self.days = days
        self.cash = cash
        self.commission = commission
        self.use_cache = use_cache
        self.config_path = config_path
        self.optimize_metrics = optimize_metrics
        self.output_dir = output_dir
        self.api_config_path = api_config_path
        self.api_key_path = api_key_path
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 加载配置
        self.symbol_config = SymbolConfig.load_config(config_path)
        
        # 创建数据获取器
        cache_dir = 'data/cache'
        os.makedirs(cache_dir, exist_ok=True)
        self.data_fetcher = DataFetcher(config_path=api_config_path, 
                                      private_key_path=api_key_path, 
                                      cache_dir=cache_dir)
        
        logger.info(f"参数优化器初始化完成，优化指标: {optimize_metrics}")

    def optimize_strategy_params(self, 
                               symbol: str, 
                               strategy_type: str = None, 
                               param_ranges: Dict[str, List[Any]] = None) -> Dict[str, Any]:
        """优化指定标的的策略参数
        
        Args:
            symbol: 标的代码
            strategy_type: 策略类型，如果为None则使用配置中的策略类型
            param_ranges: 参数范围字典，如果为None则使用默认范围
            
        Returns:
            最优参数字典
        """
        logger.info(f"开始优化 {symbol} 的策略参数")
        
        # 获取当前标的配置
        current_params = self.symbol_config.get_params(symbol)
        
        # 如果未指定策略类型，使用配置中的策略类型
        if strategy_type is None:
            strategy_type = current_params.get('strategy_type', 'smart_stoploss')
        
        # 选择策略类
        if strategy_type == 'original':
            strategy_class = MagicNineStrategy
        elif strategy_type == 'advanced_stoploss':
            strategy_class = MagicNineStrategyWithAdvancedStopLoss
        elif strategy_type == 'smart_stoploss':
            strategy_class = MagicNineStrategyWithSmartStopLoss
        else:
            raise ValueError(f"不支持的策略类型: {strategy_type}")
        
        # 如果未指定参数范围，使用默认范围
        if param_ranges is None:
            param_ranges = self._get_default_param_ranges(strategy_type)
        
        # 数据准备
        logger.info(f"正在准备 {symbol} 的数据...")
        data = self._prepare_data(symbol)
        
        # 创建Cerebro引擎用于优化
        cerebro = bt.Cerebro(stdstats=False, maxcpus=None)
        
        # 添加数据
        cerebro.adddata(data)
        
        # 设置初始资金
        cerebro.broker.setcash(self.cash)
        
        # 设置佣金
        cerebro.broker.setcommission(commission=self.commission)
        
        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        cerebro.addanalyzer(bt.analyzers.SharpeRatio_A, _name='sortino')
        
        # 创建参数组合
        param_combinations = self._generate_param_combinations(param_ranges)
        logger.info(f"共生成 {len(param_combinations)} 种参数组合进行测试")
        
        # 保存优化结果
        optimization_results = []
        
        # 遍历参数组合
        for param_idx, params in enumerate(param_combinations):
            # 重置Cerebro引擎
            cerebro = bt.Cerebro(stdstats=False, maxcpus=None)
            cerebro.adddata(data)
            cerebro.broker.setcash(self.cash)
            cerebro.broker.setcommission(commission=self.commission)
            
            # 添加分析器
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
            cerebro.addanalyzer(bt.analyzers.SharpeRatio_A, _name='sortino')
            
            # 添加策略，设置参数
            cerebro.addstrategy(strategy_class, **params)
            
            # 运行回测
            logger.debug(f"测试参数组合 {param_idx+1}/{len(param_combinations)}: {params}")
            results = cerebro.run()
            strat = results[0]
            
            # 收集分析结果
            sharpe = strat.analyzers.sharpe.get_analysis()
            drawdown = strat.analyzers.drawdown.get_analysis()
            returns = strat.analyzers.returns.get_analysis()
            trades = strat.analyzers.trades.get_analysis()
            sqn = strat.analyzers.sqn.get_analysis()
            sortino = strat.analyzers.sortino.get_analysis()
            
            # 计算指标
            total_return = returns.get('rtot', 0.0) * 100.0
            sharpe_ratio = sharpe.get('sharperatio', 0.0)
            if not sharpe_ratio or not np.isfinite(sharpe_ratio):
                sharpe_ratio = 0.0
                
            sortino_ratio = sortino.get('sortino', 0.0)
            if not sortino_ratio or not np.isfinite(sortino_ratio):
                sortino_ratio = 0.0
                
            max_drawdown = drawdown.get('max', {}).get('drawdown', 0.0) * 100.0
            
            trade_count = trades.get('total', {}).get('total', 0)
            win_rate = 0.0
            if trade_count > 0:
                won = trades.get('won', {}).get('total', 0)
                win_rate = (won / trade_count) * 100.0
            
            # 保存结果
            result = {
                'params': params,
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'max_drawdown': max_drawdown,
                'trade_count': trade_count,
                'win_rate': win_rate,
                'sqn': sqn.get('sqn', 0.0)
            }
            optimization_results.append(result)
            
            # 进度报告
            if (param_idx + 1) % 10 == 0 or param_idx == len(param_combinations) - 1:
                logger.info(f"已完成 {param_idx+1}/{len(param_combinations)} 组参数测试")
        
        # 根据优化指标排序
        if self.optimize_metrics == 'return':
            sorted_results = sorted(optimization_results, key=lambda x: (x['total_return'], x['sharpe_ratio']), reverse=True)
        elif self.optimize_metrics == 'sharpe_ratio':
            sorted_results = sorted(optimization_results, key=lambda x: (x['sharpe_ratio'], x['total_return']), reverse=True)
        elif self.optimize_metrics == 'sortino_ratio':
            sorted_results = sorted(optimization_results, key=lambda x: (x['sortino_ratio'], x['total_return']), reverse=True)
        else:
            # 默认使用夏普比率
            sorted_results = sorted(optimization_results, key=lambda x: (x['sharpe_ratio'], x['total_return']), reverse=True)
        
        # 获取最优参数
        best_result = sorted_results[0]
        best_params = best_result['params']
        
        # 保存完整优化结果
        self._save_optimization_results(symbol, strategy_type, sorted_results)
        
        # 显示最优结果
        logger.info(f"优化完成! 最优参数: {best_params}")
        logger.info(f"最优指标: 收益率 = {best_result['total_return']:.2f}%, 夏普比率 = {best_result['sharpe_ratio']:.4f}, "
                  f"最大回撤 = {best_result['max_drawdown']:.2f}%, 交易次数 = {best_result['trade_count']}, 胜率 = {best_result['win_rate']:.2f}%")
        
        # 更新配置
        best_params_with_strategy = {**best_params, 'strategy_type': strategy_type}
        self.symbol_config.update_params(symbol, best_params_with_strategy)
        self.symbol_config.save_config(self.config_path)
        
        return best_params_with_strategy
    
    def optimize_all_symbols(self, symbols: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """优化所有（或指定）标的的策略参数
        
        Args:
            symbols: 要优化的标的列表，如果为None则优化所有已配置的标的
            
        Returns:
            标的到最优参数的映射
        """
        # 如果未指定标的，优化所有已配置的标的
        if symbols is None:
            symbols = self.symbol_config.get_all_symbols()
        
        results = {}
        for symbol in symbols:
            try:
                # 获取当前标的的策略类型
                current_params = self.symbol_config.get_params(symbol)
                strategy_type = current_params.get('strategy_type', 'smart_stoploss')
                
                # 优化参数
                best_params = self.optimize_strategy_params(symbol, strategy_type)
                results[symbol] = best_params
            except Exception as e:
                logger.error(f"优化 {symbol} 的参数时出错: {e}")
        
        return results
    
    def optimize_strategy_types(self, symbol: str) -> Dict[str, Any]:
        """优化指定标的的策略类型和参数
        
        Args:
            symbol: 标的代码
            
        Returns:
            最优策略类型和参数
        """
        logger.info(f"开始优化 {symbol} 的策略类型和参数")
        
        # 存储各策略类型的最优结果
        strategy_results = {}
        
        # 测试所有策略类型
        for strategy_type in ['original', 'advanced_stoploss', 'smart_stoploss']:
            try:
                logger.info(f"测试策略类型: {strategy_type}")
                best_params = self.optimize_strategy_params(symbol, strategy_type)
                
                # 获取最优参数的性能指标
                metrics = self._evaluate_strategy(symbol, strategy_type, best_params)
                strategy_results[strategy_type] = {
                    'params': best_params,
                    'metrics': metrics
                }
            except Exception as e:
                logger.error(f"优化 {symbol} 的 {strategy_type} 策略时出错: {e}")
        
        # 根据优化指标选择最佳策略类型
        best_strategy_type = None
        best_metrics = None
        
        for strategy_type, result in strategy_results.items():
            metrics = result['metrics']
            
            if best_metrics is None:
                best_strategy_type = strategy_type
                best_metrics = metrics
                continue
            
            # 比较指标
            if self.optimize_metrics == 'return':
                if metrics['total_return'] > best_metrics['total_return']:
                    best_strategy_type = strategy_type
                    best_metrics = metrics
            elif self.optimize_metrics == 'sharpe_ratio':
                if metrics['sharpe_ratio'] > best_metrics['sharpe_ratio']:
                    best_strategy_type = strategy_type
                    best_metrics = metrics
            elif self.optimize_metrics == 'sortino_ratio':
                if metrics['sortino_ratio'] > best_metrics['sortino_ratio']:
                    best_strategy_type = strategy_type
                    best_metrics = metrics
        
        # 获取最优策略的参数
        if best_strategy_type:
            best_params = strategy_results[best_strategy_type]['params']
            
            # 更新配置
            best_params_with_strategy = {**best_params, 'strategy_type': best_strategy_type}
            self.symbol_config.update_params(symbol, best_params_with_strategy)
            self.symbol_config.save_config(self.config_path)
            
            logger.info(f"最优策略类型: {best_strategy_type}, 参数: {best_params}")
            logger.info(f"最优指标: 收益率 = {best_metrics['total_return']:.2f}%, 夏普比率 = {best_metrics['sharpe_ratio']:.4f}, "
                      f"最大回撤 = {best_metrics['max_drawdown']:.2f}%, 交易次数 = {best_metrics['trade_count']}, 胜率 = {best_metrics['win_rate']:.2f}%")
            
            return best_params_with_strategy
        else:
            logger.warning(f"未找到 {symbol} 的最优策略")
            return None
    
    def _prepare_data(self, symbol: str) -> bt.feeds.PandasData:
        """准备回测数据
        
        Args:
            symbol: 标的代码
            
        Returns:
            bt.feeds.PandasData实例
        """
        # 获取数据
        logger.info(f"获取 {symbol} 的历史数据，天数: {self.days}, 使用缓存: {self.use_cache}")
        
        # 计算时间范围
        end_date = datetime.now()
        begin_date = end_date - timedelta(days=self.days)
        
        # 获取数据并准备backtrader文件
        df = self.data_fetcher.get_bar_data(symbol, begin_time=begin_date, end_time=end_date, use_cache=self.use_cache)
        data_file = self.data_fetcher.prepare_backtrader_data(symbol, df)
        
        if data_file is None:
            raise ValueError(f"无法获取或准备 {symbol} 的数据")
        
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
    
    def _evaluate_strategy(self, 
                         symbol: str, 
                         strategy_type: str, 
                         params: Dict[str, Any]) -> Dict[str, float]:
        """评估特定参数的策略性能
        
        Args:
            symbol: 标的代码
            strategy_type: 策略类型
            params: 策略参数
            
        Returns:
            性能指标字典
        """
        # 选择策略类
        if strategy_type == 'original':
            strategy_class = MagicNineStrategy
        elif strategy_type == 'advanced_stoploss':
            strategy_class = MagicNineStrategyWithAdvancedStopLoss
        elif strategy_type == 'smart_stoploss':
            strategy_class = MagicNineStrategyWithSmartStopLoss
        else:
            raise ValueError(f"不支持的策略类型: {strategy_type}")
        
        # 数据准备
        data = self._prepare_data(symbol)
        
        # 创建Cerebro引擎
        cerebro = bt.Cerebro(stdstats=False)
        cerebro.adddata(data)
        cerebro.broker.setcash(self.cash)
        cerebro.broker.setcommission(commission=self.commission)
        
        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        cerebro.addanalyzer(bt.analyzers.SharpeRatio_A, _name='sortino')
        
        # 添加策略
        cerebro.addstrategy(strategy_class, **params)
        
        # 运行回测
        results = cerebro.run()
        strat = results[0]
        
        # 收集分析结果
        sharpe = strat.analyzers.sharpe.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        returns = strat.analyzers.returns.get_analysis()
        trades = strat.analyzers.trades.get_analysis()
        sqn = strat.analyzers.sqn.get_analysis()
        sortino = strat.analyzers.sortino.get_analysis()
        
        # 计算指标
        total_return = returns.get('rtot', 0.0) * 100.0
        sharpe_ratio = sharpe.get('sharperatio', 0.0)
        if not sharpe_ratio or not np.isfinite(sharpe_ratio):
            sharpe_ratio = 0.0
            
        sortino_ratio = sortino.get('sortino', 0.0)
        if not sortino_ratio or not np.isfinite(sortino_ratio):
            sortino_ratio = 0.0
            
        max_drawdown = drawdown.get('max', {}).get('drawdown', 0.0) * 100.0
        
        trade_count = trades.get('total', {}).get('total', 0)
        win_rate = 0.0
        if trade_count > 0:
            won = trades.get('won', {}).get('total', 0)
            win_rate = (won / trade_count) * 100.0
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'trade_count': trade_count,
            'win_rate': win_rate,
            'sqn': sqn.get('sqn', 0.0)
        }
    
    def _get_default_param_ranges(self, strategy_type: str) -> Dict[str, List[Any]]:
        """获取默认参数范围
        
        Args:
            strategy_type: 策略类型
            
        Returns:
            参数范围字典
        """
        # 核心参数范围
        core_params = {
            'magic_period': [2, 3, 4],
            'magic_count': [4, 5, 6, 7]
        }
        
        # 根据策略类型设置特定参数范围
        if strategy_type == 'original':
            return {
                **core_params,
                'rsi_period': [14],
                'rsi_overbought': [70],
                'rsi_oversold': [30],
                'stop_loss_pct': [0.8, 1.0, 1.5],
                'profit_target_pct': [1.5, 2.0, 2.5],
                'trailing_pct': [0.8, 1.0, 1.2],
                'position_size': [0.95],
                'enable_short': [True]
            }
        elif strategy_type == 'advanced_stoploss':
            return {
                **core_params,
                'rsi_oversold': [30],
                'rsi_overbought': [70],
                'atr_period': [14],
                'atr_multiplier': [2.0, 2.5, 3.0, 3.5],
                'long_atr_multiplier': [2.0, 2.5, 3.0],
                'short_atr_multiplier': [2.5, 3.0, 3.5],
                'trailing_stop': [True],
                'max_loss_pct': [2.5, 3.0, 3.5],
                'long_max_loss_pct': [2.5, 3.0, 3.5],
                'short_max_loss_pct': [3.0, 3.5, 4.0],
                'min_profit_pct': [0.8, 1.0, 1.2],
                'long_min_profit_pct': [0.8, 1.0, 1.2],
                'short_min_profit_pct': [1.0, 1.2, 1.5],
                'enable_short': [True],
                'position_pct': [0.95],
                'short_volatility_factor': [1.1, 1.2, 1.3]
            }
        elif strategy_type == 'smart_stoploss':
            return {
                **core_params,
                'rsi_oversold': [30],
                'rsi_overbought': [70],
                'atr_period': [14],
                'atr_multiplier': [2.0, 2.5, 3.0, 3.5],
                'trailing_stop': [True],
                'max_loss_pct': [2.5, 3.0, 3.5],
                'min_profit_pct': [0.8, 1.0, 1.2],
                'time_decay': [True],
                'time_decay_days': [2, 3, 4],
                'volatility_adjust': [True],
                'market_aware': [True],
                'risk_aversion': [0.8, 1.0, 1.2],
                'enable_short': [True],
                'position_pct': [0.95],
                'short_atr_multiplier': [2.5, 2.8, 3.0],
                'short_max_loss_pct': [3.0, 3.5, 4.0],
                'short_min_profit_pct': [1.0, 1.2, 1.5],
                'short_volatility_factor': [1.1, 1.2, 1.3]
            }
        else:
            raise ValueError(f"不支持的策略类型: {strategy_type}")
    
    def _generate_param_combinations(self, param_ranges: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """生成参数组合
        
        Args:
            param_ranges: 参数范围字典
            
        Returns:
            参数组合列表
        """
        # 要测试的参数名和取值
        param_names = list(param_ranges.keys())
        param_values = [param_ranges[name] for name in param_names]
        
        # 如果组合数过多，进行随机采样
        total_combinations = np.prod([len(values) for values in param_values])
        
        if total_combinations > 100:
            logger.warning(f"参数组合总数 {total_combinations} 过多，将随机采样最多100组")
            combinations = []
            for _ in range(min(100, total_combinations)):
                params = {}
                for name, values in param_ranges.items():
                    params[name] = np.random.choice(values)
                combinations.append(params)
            return combinations
        
        # 生成所有组合
        combinations = []
        for values in itertools.product(*param_values):
            params = {name: value for name, value in zip(param_names, values)}
            combinations.append(params)
        
        return combinations
    
    def _save_optimization_results(self, 
                                symbol: str, 
                                strategy_type: str, 
                                results: List[Dict[str, Any]]) -> str:
        """保存优化结果
        
        Args:
            symbol: 标的代码
            strategy_type: 策略类型
            results: 优化结果列表
            
        Returns:
            保存的文件路径
        """
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(self.output_dir, f"{symbol}_{strategy_type}_optimization_{timestamp}.csv")
        
        # 将结果转换为DataFrame
        rows = []
        for result in results:
            row = {
                'total_return': result['total_return'],
                'sharpe_ratio': result['sharpe_ratio'],
                'sortino_ratio': result['sortino_ratio'],
                'max_drawdown': result['max_drawdown'],
                'trade_count': result['trade_count'],
                'win_rate': result['win_rate'],
                'sqn': result['sqn']
            }
            # 添加参数
            for param_name, param_value in result['params'].items():
                row[param_name] = param_value
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # 保存为CSV
        df.to_csv(file_path, index=False)
        logger.info(f"优化结果已保存到: {file_path}")
        
        return file_path 