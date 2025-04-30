"""
优化脚本
负责策略参数优化流程的控制
"""
import itertools
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

import pandas as pd

from src.application.scripts.base_script import BaseScript
from src.business.strategy.magic_nine_strategy import MagicNineStrategy
from src.interface import TigerCsvData
from src.interface.tiger.tiger_store import TigerStore
from src.infrastructure.utils.file_utils import ensure_directory_exists


class OptimizeScript(BaseScript):
    """
    优化脚本类
    实现策略参数优化流程，包括:
    1. 定义参数网格
    2. 针对多个标的进行参数优化
    3. 生成优化报告
    4. 更新策略配置
    
    每次优化都应该:
    1. 生成一份优化报告
    2. 一条优化结果记录到CSV
    3. 一次对magic_nine.yaml的参数覆盖
    """

    def __init__(self):
        """初始化优化脚本"""
        # 调用父类初始化
        super().__init__()

        # 优化结果路径
        self.output_dir = "outputs/optimize"

        # 历史优化记录文件
        self.history_file = f"{self.output_dir}/optimization_history.csv"

        # 确保输出目录存在
        ensure_directory_exists(self.output_dir)

        # 可优化的参数定义 - 确保使用策略支持的参数
        self.param_definitions = {
            # 神奇九转参数
            "magic_period": {"min": 2, "max": 5, "step": 1, "type": "int"},
            "magic_count": {"min": 3, "max": 7, "step": 1, "type": "int"},
            
            # RSI参数
            "rsi_period": {"min": 8, "max": 16, "step": 2, "type": "int"},
            "rsi_overbought": {"min": 65, "max": 80, "step": 5, "type": "int"},
            "rsi_oversold": {"min": 20, "max": 35, "step": 5, "type": "int"},
            
            # ATR参数
            "atr_period": {"min": 10, "max": 20, "step": 2, "type": "int"},
            "atr_multiplier": {"min": 1.5, "max": 3.5, "step": 0.5, "type": "float"},
            
            # 交易控制参数
            "trailing_pct": {"min": 0.5, "max": 2.0, "step": 0.5, "type": "float"},
            "profit_target_pct": {"min": 1.0, "max": 3.0, "step": 0.5, "type": "float"},
            "stop_loss_pct": {"min": 0.5, "max": 1.5, "step": 0.5, "type": "float"}
        }
        
        # 默认的参数网格，较小的配置用于测试
        self.default_param_grid = {
            # 神奇九转参数
            "magic_period": [3, 4],
            "magic_count": [4, 5],
            
            # RSI参数
            "rsi_period": [10, 14],
            "rsi_overbought": [70, 75],
            "rsi_oversold": [25, 30],
            
            # ATR参数
            "atr_period": [12, 14],
            "atr_multiplier": [2.0, 2.5],
            
            # 交易控制参数
            "trailing_pct": [1.0, 1.5],
            "profit_target_pct": [1.5, 2.0],
            "stop_loss_pct": [0.8, 1.0]
        }

        # 优化目标和权重
        self.optimization_targets = {
            "win_rate": 0.4,  # 胜率权重 40%
            "sharpe_ratio": 0.3,  # 夏普比率权重 30%
            "total_return": 0.2,  # 总收益率权重 20%
            "drawdown": 0.1  # 最大回撤权重 10%（负向指标）
        }

        # 设定目标改进阈值
        self.improvement_threshold = 0.05  # 5%

    def run(self, symbol: Optional[str] = None, param_grid: Optional[Dict[str, List[Any]]] = None) -> Dict[str, Any]:
        """
        运行优化流程
        
        Args:
            symbol: 指定要优化的交易标的，如果为None则使用所有配置的标的
            param_grid: 自定义参数网格，如果为None则使用默认网格
            
        Returns:
            Dict: 包含各个标的优化结果的字典
        """
        self.logger.info("开始参数优化流程")

        # 1. 加载配置
        config = self.load_config()

        # 2. 确定要优化的标的
        symbols = []  # 初始化为空列表
        if symbol:
            symbols = [symbol]
            self.logger.info(f"将对指定标的 {symbol} 进行参数优化")
        else:
            # 确保从config中获取的target_symbols不为None
            config_symbols = config.get('target_symbols')
            if config_symbols and isinstance(config_symbols, list):
                symbols = config_symbols
            else:
                # 默认使用QQQ作为标的
                symbols = ['QQQ']
            self.logger.info(f"将对以下标的进行参数优化: {symbols}")

        # 3. 确定参数网格
        if param_grid is None:
            param_grid = self.default_param_grid
            self.logger.info("使用默认参数网格进行优化")
        else:
            self.logger.info("使用自定义参数网格进行优化")

        # 4. 初始化结果容器
        results = {}

        # 5. 为每个标的执行优化
        for sym in symbols:
            self.logger.info(f"开始优化标的 {sym} 的参数")

            # 执行优化
            optimize_result = self._optimize_for_symbol(sym, param_grid)

            # 存储结果
            results[sym] = optimize_result

            # 日志输出优化结果
            best_params = optimize_result.get('best_params', {})
            best_metrics = optimize_result.get('best_metrics', {})

            self.logger.info(f"标的 {sym} 的最优参数: {best_params}")
            self.logger.info(f"标的 {sym} 的最优指标:")
            self.logger.info(f"- 胜率: {best_metrics.get('胜率', 0) * 100:.2f}%")
            self.logger.info(f"- 总收益率: {best_metrics.get('总收益率', 0) * 100:.2f}%")
            self.logger.info(f"- 夏普比率: {best_metrics.get('夏普比率', 0):.2f}")
            self.logger.info(f"- 最大回撤: {best_metrics.get('最大回撤', 0) * 100:.2f}%")

        # 6. 更新策略配置
        self._update_strategy_config(results)

        # 7. 保存优化历史
        self._save_optimization_history(results)

        self.logger.info("参数优化流程完成")
        return results

    def _optimize_for_symbol(self, symbol: str, param_grid: Dict[str, List[Any]]) -> Dict[str, Any]:
        """
        对单个标的进行参数优化
        
        Args:
            symbol: 交易标的
            param_grid: 参数网格
            
        Returns:
            Dict: 优化结果
        """
        self.logger.info(f"为标的 {symbol} 生成参数组合")

        # 1. 获取所有参数组合
        param_combinations = self._generate_parameter_combinations(param_grid)
        total_combinations = len(param_combinations)
        self.logger.info(f"共生成 {total_combinations} 种参数组合待评估")

        # 2. 初始化最佳结果跟踪
        best_score = -float('inf')
        best_params = {}  # 初始化为空字典而不是None
        best_metrics = {}  # 初始化为空字典而不是None

        # 3. 初始化结果记录
        results_log = []

        # 记录开始时间
        start_time = datetime.now()

        # 4. 评估每种参数组合
        for i, params in enumerate(param_combinations):
            self.logger.info(f"评估参数组合 {i + 1}/{total_combinations}")

            # 评估参数
            metrics = self._evaluate_parameters(symbol, params)

            # 计算组合得分
            score = self._calculate_optimization_score(metrics)

            # 记录结果
            result_entry = {
                "params": params,
                "metrics": metrics,
                "score": score
            }
            results_log.append(result_entry)

            # 更新最佳结果
            if score > best_score:
                best_score = score
                best_params = params.copy()
                best_metrics = metrics.copy()
                self.logger.info(f"发现新的最佳参数组合，得分: {best_score:.4f}")

        # 记录结束时间
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 5. 生成优化报告
        report_file = self._generate_optimization_report(
            symbol,
            param_combinations,
            results_log,
            best_params,
            best_metrics,
            duration
        )

        # 6. 构建返回结果
        result = {
            "symbol": symbol,
            "best_params": best_params,
            "best_metrics": best_metrics,
            "best_score": best_score,
            "total_combinations": total_combinations,
            "output_files": {
                "report": report_file,
            },
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": duration
        }

        return result

    def _generate_parameter_combinations(self, param_grid: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        生成所有参数组合
        
        Args:
            param_grid: 参数网格
            
        Returns:
            List[Dict]: 参数组合列表
        """
        # 获取参数名和值列表
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())

        # 使用itertools.product生成所有组合
        combinations = list(itertools.product(*param_values))

        # 转换为字典列表
        param_combinations = []
        for combo in combinations:
            param_dict = dict(zip(param_names, combo))

            # 验证MACD参数：fast < slow
            if 'macd_fast' in param_dict and 'macd_slow' in param_dict:
                if param_dict['macd_fast'] >= param_dict['macd_slow']:
                    continue

            # 验证RSI上下限：upper > lower
            if 'rsi_upper' in param_dict and 'rsi_lower' in param_dict:
                if param_dict['rsi_upper'] <= param_dict['rsi_lower']:
                    continue

            param_combinations.append(param_dict)

        return param_combinations

    def _evaluate_parameters(self, symbol: str, params: Dict[str, Any]) -> Dict[str, float]:
        """
        评估特定参数组合的性能
        
        Args:
            symbol: 交易标的
            params: 参数组合
            
        Returns:
            Dict: 评估指标
        """
        # 创建回测引擎
        self.create_cerebro()

        # 设置引擎现金
        self.setup_broker(10000.0)

        # 添加分析器
        self.add_analyzers()

        # 创建数据源
        store = TigerStore()
        data = TigerCsvData()
        data.p.store = store
        data.p.dataname = symbol

        # 添加数据
        self.cerebro.adddata(data)
        
        # 动态获取策略支持的参数
        # 从MagicNineStrategy参数中提取所有参数名
        supported_params = {key for key, _ in MagicNineStrategy.params._getitems()}
        self.logger.info(f"策略支持的参数: {supported_params}")
        
        # 只保留支持的参数
        strategy_params = {k: v for k, v in params.items() if k in supported_params}
        
        # 记录实际使用的参数
        self.logger.info(f"使用以下参数: {strategy_params}")
        
        # 添加策略
        self.cerebro.addstrategy(MagicNineStrategy, **strategy_params)

        # 运行回测
        results = self.cerebro.run()

        # 如果运行失败或没有策略实例
        if not results or len(results) == 0:
            self.logger.warning(f"参数 {params} 的回测执行失败")
            return {
                "胜率": 0,
                "总收益率": 0,
                "夏普比率": 0,
                "最大回撤": 1.0  # 最坏情况
            }

        # 提取分析结果
        analysis = self.extract_analyzer_results(results[0])

        # 提取关键指标
        metrics = {}

        # 从交易分析器中获取胜率
        if 'trades' in analysis and hasattr(analysis['trades'], 'total') and analysis['trades'].total.total > 0:
            win_rate = analysis['trades'].won.total / analysis['trades'].total.total
            metrics["胜率"] = win_rate
        else:
            metrics["胜率"] = 0

        # 从性能分析器中获取总收益率
        if 'performance' in analysis:
            metrics["总收益率"] = analysis['performance'].get('total_return', 0)
            metrics["夏普比率"] = float(analysis['performance'].get('sharpe_ratio', 0)) if analysis['performance'].get(
                'sharpe_ratio') is not None else 0
        else:
            metrics["总收益率"] = 0
            metrics["夏普比率"] = 0

        # 从风险分析器中获取最大回撤
        if 'risk' in analysis:
            metrics["最大回撤"] = analysis['risk'].get('max_drawdown', 1.0)
        else:
            metrics["最大回撤"] = 1.0

        return metrics

    def _filter_strategy_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理参数（不再过滤参数，而是全量传入）
        
        Args:
            params: 原始参数字典
            
        Returns:
            Dict: 所有参数字典
        """
        # 直接返回所有参数，不再过滤
        # 由策略自行处理需要的参数
        return params

    def _calculate_optimization_score(self, metrics: Dict[str, float]) -> float:
        """
        计算参数组合的优化得分
        
        Args:
            metrics: 评估指标
            
        Returns:
            float: 优化得分
        """
        score = 0.0

        # 胜率 (0-1)
        if "胜率" in metrics:
            score += metrics["胜率"] * self.optimization_targets["win_rate"]

        # 夏普比率 (通常从负值到正值，需要归一化)
        if "夏普比率" in metrics:
            # 将夏普比率限制在[-2, 5]范围内，然后归一化到[0, 1]
            normalized_sharpe = min(max(metrics["夏普比率"], -2), 5)
            normalized_sharpe = (normalized_sharpe + 2) / 7
            score += normalized_sharpe * self.optimization_targets["sharpe_ratio"]

        # 总收益率 (通常是-1到正无穷，需要归一化)
        if "总收益率" in metrics:
            # 将总收益率限制在[-1, 2]范围内，然后归一化到[0, 1]
            normalized_return = min(max(metrics["总收益率"], -1), 2)
            normalized_return = (normalized_return + 1) / 3
            score += normalized_return * self.optimization_targets["total_return"]

        # 最大回撤 (0-1，越小越好，需要反转)
        if "最大回撤" in metrics:
            # 回撤是0到1，1表示100%回撤（最差），反转为1-回撤使其与其他指标方向一致
            inverted_drawdown = 1 - min(metrics["最大回撤"], 1)
            score += inverted_drawdown * self.optimization_targets["drawdown"]

        return score

    def _generate_optimization_report(
            self,
            symbol: str,
            param_combinations: List[Dict[str, Any]],
            results: List[Dict[str, Any]],
            best_params: Dict[str, Any],
            best_metrics: Dict[str, float],
            duration: float
    ) -> str:
        """
        生成优化报告
        
        Args:
            symbol: 交易标的
            param_combinations: 参数组合列表
            results: 评估结果列表
            best_params: 最佳参数
            best_metrics: 最佳指标
            duration: 优化耗时（秒）
            
        Returns:
            str: 报告文件路径
        """
        # 创建报告目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = f"{self.output_dir}/{timestamp}_{symbol}"
        ensure_directory_exists(report_dir)

        # 创建报告文件
        report_file = f"{report_dir}/optimization_report.csv"

        # 准备报告数据
        report_data = []
        for result in results:
            entry = {}
            # 添加参数
            for param_name, param_value in result["params"].items():
                entry[f"param_{param_name}"] = param_value

            # 添加指标
            for metric_name, metric_value in result["metrics"].items():
                entry[f"metric_{metric_name}"] = metric_value

            # 添加得分
            entry["score"] = result["score"]

            report_data.append(entry)

        # 创建DataFrame并保存为CSV
        df = pd.DataFrame(report_data)

        # 按得分排序
        df = df.sort_values(by="score", ascending=False)

        # 保存到CSV
        df.to_csv(report_file, index=False)

        # 创建汇总报告
        summary_file = f"{report_dir}/summary.txt"

        with open(summary_file, "w") as f:
            f.write(f"优化报告 - 标的: {symbol}\n")
            f.write(f"时间: {timestamp}\n")
            f.write(f"参数组合数: {len(param_combinations)}\n")
            f.write(f"优化耗时: {duration:.2f} 秒\n\n")

            f.write("最佳参数组合:\n")
            for param_name, param_value in best_params.items():
                f.write(f"- {param_name}: {param_value}\n")

            f.write("\n最佳性能指标:\n")
            for metric_name, metric_value in best_metrics.items():
                if metric_name in ["胜率", "总收益率", "最大回撤"]:
                    f.write(f"- {metric_name}: {metric_value * 100:.2f}%\n")
                else:
                    f.write(f"- {metric_name}: {metric_value:.4f}\n")

        self.logger.info(f"优化报告已保存至 {report_file}")
        self.logger.info(f"优化汇总已保存至 {summary_file}")

        return report_file

    def _update_strategy_config(self, results: Dict[str, Dict[str, Any]]):
        """
        更新策略配置文件
        
        Args:
            results: 优化结果字典
        """
        self.logger.info("更新策略配置文件")

        # 加载当前配置
        config = self.strategy_config.get_config()

        # 更新配置
        for symbol, result in results.items():
            best_params = result.get('best_params', {})

            # 检查是否存在symbol的配置
            if 'symbols' not in config:
                config['symbols'] = {}

            if symbol not in config['symbols']:
                config['symbols'][symbol] = {}

            # 更新symbol的参数
            for param_name, param_value in best_params.items():
                config['symbols'][symbol][param_name] = param_value

        # 保存配置
        try:
            # 先更新内存中的配置
            self.strategy_config.save(config)
            # 然后保存到文件（使用正确的配置文件路径）
            config_path = 'configs/strategy/magic_nine.yaml'
            self.strategy_config.save_config(config_path)
            self.logger.info(f"配置文件更新成功: {config_path}")
        except Exception as e:
            self.logger.error(f"配置文件更新失败: {str(e)}")

    def _save_optimization_history(self, results: Dict[str, Dict[str, Any]]):
        """
        保存优化历史记录
        
        Args:
            results: 优化结果字典
        """
        self.logger.info("保存优化历史记录")

        # 生成历史记录
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for symbol, result in results.items():
            best_params = result.get('best_params', {})
            best_metrics = result.get('best_metrics', {})

            # 准备记录数据
            record = {
                "优化时间": timestamp,
                "标的": symbol,
                "得分": result.get('best_score', 0),
                "胜率": best_metrics.get('胜率', 0) * 100,
                "总收益率": best_metrics.get('总收益率', 0) * 100,
                "夏普比率": best_metrics.get('夏普比率', 0),
                "最大回撤": best_metrics.get('最大回撤', 0) * 100,
                "优化耗时": result.get('duration', 0),
                "参数组合数": result.get('total_combinations', 0)
            }

            # 添加参数
            for param_name, param_value in best_params.items():
                record[f"param_{param_name}"] = param_value

            # 检查历史文件是否存在
            try:
                if os.path.exists(self.history_file):
                    # 如果存在，追加记录
                    df = pd.read_csv(self.history_file)
                    df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
                else:
                    # 如果不存在，创建新文件
                    df = pd.DataFrame([record])

                # 保存历史记录
                df.to_csv(self.history_file, index=False)
                self.logger.info(f"优化历史记录已保存至 {self.history_file}")

            except Exception as e:
                self.logger.error(f"保存优化历史记录失败: {str(e)}")
