import os
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

def ensure_directory_exists(directory_path: str) -> None:
    """确保目录存在，如果不存在则创建"""
    os.makedirs(directory_path, exist_ok=True)

def save_backtest_results(results: Dict[str, Any], symbol: str, strategy_name: str, 
                           start_date: str, end_date: str, period: str = "1m") -> str:
    """
    保存回测结果到CSV文件中，采用纵向排列方式（指标在第一列，值在第二列）
    单个回测结果保存为纵向排列，历史记录文件采用横向排列（每次回测为一列）
    
    Args:
        results: 回测结果字典（包含performance, risk, trades等分析器结果）
        symbol: 交易标的符号
        strategy_name: 策略名称
        start_date: 回测开始日期
        end_date: 回测结束日期
        period: 回测周期
        
    Returns:
        保存的文件路径
    """
    # 确保目录存在
    results_dir = Path("results/backtest/records")
    ensure_directory_exists(str(results_dir))
    
    # 生成文件名（包含时间戳、标的和策略名称）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{symbol}_{strategy_name}_{start_date}_{end_date}_{period}.csv"
    filepath = results_dir / filename
    
    # 计算胜率和每日交易次数
    win_rate = 0
    
    if 'trades' in results and 'won' in results['trades'] and 'total' in results['trades']:
        if results['trades']['total']['total'] > 0:
            win_rate = results['trades']['won']['total'] / results['trades']['total']['total'] * 100
    
    # 从分析器结果中提取指标
    metrics = {
        "执行时间": timestamp,
        "交易标的": symbol,
        "策略名称": strategy_name,
        "开始日期": start_date,
        "结束日期": end_date,
        "周期": period,
        # 交易时间信息
        "交易开始时间": results.get('start_time', ''),
        "交易结束时间": results.get('end_time', ''),
        # 从performance分析器中提取
        "总收益率": round(results.get('performance', {}).get('total_return', 0) * 100, 3),
        "年化收益率": round(results.get('performance', {}).get('annual_return', 0) * 100, 3),
        "夏普比率": round(float(results.get('performance', {}).get('sharpe_ratio', 0) or 0), 4),
        # 从risk分析器中提取
        "最大回撤": round(results.get('risk', {}).get('max_drawdown', 0) * 100, 3),
        "最大回撤持续时间": results.get('risk', {}).get('max_drawdown_duration', 0),
        "波动率": round(float(results.get('risk', {}).get('volatility', 0) or 0) * 100, 3),
        # 从trades分析器中提取
        "胜率": round(win_rate, 2),
        "总交易次数": results.get('trades', {}).get('total', {}).get('total', 0),
        "盈利交易次数": results.get('trades', {}).get('won', {}).get('total', 0),
        "亏损交易次数": results.get('trades', {}).get('lost', {}).get('total', 0),
        "平均每天交易次数": round(results.get('trades', {}).get('avg_trades_per_day', 0), 2),
        "交易天数": results.get('trades', {}).get('trading_days', 0),
        "总净利润": round(results.get('trades', {}).get('pnl', {}).get('net', {}).get('total', 0), 4),
        "平均净利润": round(results.get('trades', {}).get('pnl', {}).get('net', {}).get('average', 0), 4),
        "多头总盈亏": round(results.get('trades', {}).get('long', {}).get('pnl', {}).get('total', 0), 4),
        "空头总盈亏": round(results.get('trades', {}).get('short', {}).get('pnl', {}).get('total', 0), 4),
        "最大连续盈利次数": results.get('trades', {}).get('streak', {}).get('won', {}).get('longest', 0),
        "最大连续亏损次数": results.get('trades', {}).get('streak', {}).get('lost', {}).get('longest', 0),
        # SQN系统质量指标
        "系统质量指标(SQN)": round(results.get('sqn', {}).get('sqn', 0), 4),
    }
    
    # 保存详细结果（纵向排列）
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["指标", "值"])
        for metric, value in metrics.items():
            writer.writerow([metric, value])
    
    # 历史记录文件采用横向排列（回测ID作为列标题）
    history_file = results_dir / "backtest_history.csv"
    
    # 生成唯一的回测ID
    backtest_id = f"{timestamp}_{symbol}_{period}"
    
    # 准备要写入的指标和新的回测结果
    metrics_list = list(metrics.keys())
    values_list = list(metrics.values())
    
    if not history_file.exists():
        # 如果历史文件不存在，创建它并写入表头
        with open(history_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ["指标", backtest_id]
            writer.writerow(header)
            # 写入每个指标的值
            for i, metric in enumerate(metrics_list):
                writer.writerow([metric, values_list[i]])
    else:
        # 文件已存在，需要读取现有内容，添加新列
        rows = []
        with open(history_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # 更新表头添加新的回测ID
        if rows:
            rows[0].append(backtest_id)
            
            # 更新每一行添加新回测的值
            for i, metric in enumerate(metrics_list):
                # 确保每个指标都在行列表中
                metric_found = False
                for j, row in enumerate(rows[1:], 1):
                    if row[0] == metric:
                        row.append(values_list[i])
                        metric_found = True
                        break
                
                # 如果指标不在现有行中，添加新行
                if not metric_found:
                    new_row = [metric] + [""] * (len(rows[0]) - 2) + [values_list[i]]
                    rows.append(new_row)
        
        # 写入更新后的数据
        with open(history_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
    
    logger.info(f"回测结果已保存到: {filepath}")
    logger.info(f"历史记录已更新: {history_file}")
    
    return str(filepath) 

def save_optimization_results(
    optimization_id: str,
    symbol: str,
    original_params: Dict[str, Any],
    optimized_params: Dict[str, Any],
    metrics: Dict[str, Any],
    comparison: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """
    保存优化结果到CSV文件，并更新优化历史记录
    
    Args:
        optimization_id: 优化ID（时间戳）
        symbol: 交易标的
        original_params: 原始参数
        optimized_params: 优化后的参数
        metrics: 优化后的性能指标
        comparison: 与原始参数的性能比较
        
    Returns:
        Dict: 包含保存文件路径的字典
    """
    # 确保输出目录存在
    output_dir = Path("results/optimization")
    ensure_directory_exists(str(output_dir))
    
    # 创建时间戳，如果未提供则生成新的
    if not optimization_id:
        optimization_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 生成优化报告
    report_file = output_dir / f"{optimization_id}_{symbol}_optimization_report.csv"
    
    # 将原始参数和优化参数并排展示
    with open(report_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # 写入报告标题
        writer.writerow([f"{symbol} 策略参数优化报告", f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""])
        writer.writerow(["", "", ""])
        
        # 写入参数对比部分
        writer.writerow(["参数名称", "原始值", "优化后值", "变化"])
        for param_name in sorted(set(list(original_params.keys()) + list(optimized_params.keys()))):
            original_value = original_params.get(param_name, "N/A")
            optimized_value = optimized_params.get(param_name, "N/A")
            
            # 计算变化
            change = ""
            if original_value != "N/A" and optimized_value != "N/A":
                try:
                    if isinstance(original_value, (int, float)) and isinstance(optimized_value, (int, float)):
                        change = f"{optimized_value - original_value:+.2f}"
                except:
                    change = "无法计算"
            
            writer.writerow([param_name, original_value, optimized_value, change])
        
        # 空行
        writer.writerow(["", "", ""])
        
        # 写入性能指标部分
        writer.writerow(["性能指标", "优化后值", "原始值", "改进"])
        
        # 排序性能指标，确保关键指标在前面
        key_metrics = ["总收益率", "胜率", "夏普比率", "最大回撤", "盈利因子"]
        other_metrics = [m for m in metrics if m not in key_metrics]
        sorted_metrics = key_metrics + sorted(other_metrics)
        
        for metric_name in sorted_metrics:
            if metric_name in metrics:
                optimized_value = metrics[metric_name]
                original_value = comparison.get(metric_name, "N/A") if comparison else "N/A"
                
                # 计算改进
                improvement = ""
                if original_value != "N/A" and not isinstance(original_value, str):
                    try:
                        if isinstance(optimized_value, (int, float)) and isinstance(original_value, (int, float)):
                            if metric_name == "最大回撤":  # 回撤越小越好
                                improvement = f"{original_value - optimized_value:+.2f}"
                            else:  # 其他指标越大越好
                                improvement = f"{optimized_value - original_value:+.2f}"
                    except:
                        improvement = "无法计算"
                
                writer.writerow([metric_name, optimized_value, original_value, improvement])
        
        # 写入拟合风险评估
        writer.writerow(["", "", ""])
        writer.writerow(["拟合风险评估", "", ""])
        
        # 简单的拟合风险评估逻辑
        overfitting_risk = "低"
        if "总收益率" in metrics and "样本外收益率" in metrics:
            in_sample = metrics["总收益率"]
            out_sample = metrics.get("样本外收益率", 0)
            if isinstance(in_sample, (int, float)) and isinstance(out_sample, (int, float)):
                if in_sample > 0 and out_sample <= 0:
                    overfitting_risk = "高"
                elif in_sample > 0 and out_sample > 0 and out_sample < in_sample * 0.5:
                    overfitting_risk = "中"
        
        writer.writerow(["过拟合风险评估", overfitting_risk, ""])
        writer.writerow(["参数数量", len(optimized_params), "参数过多可能增加过拟合风险"])
        
        # 写入建议
        writer.writerow(["", "", ""])
        writer.writerow(["建议", "", ""])
        if "胜率" in metrics and "总收益率" in metrics:
            win_rate = metrics["胜率"] if isinstance(metrics["胜率"], (int, float)) else 0
            return_rate = metrics["总收益率"] if isinstance(metrics["总收益率"], (int, float)) else 0
            
            if win_rate >= 0.65 and return_rate >= 0.04:  # 符合目标
                writer.writerow(["参数评估", "推荐采用", "参数符合目标要求"])
            elif win_rate >= 0.60 and return_rate >= 0.03:  # 接近目标
                writer.writerow(["参数评估", "可以考虑", "参数接近目标要求"])
            else:  # 不达标
                writer.writerow(["参数评估", "需要改进", "参数未达到目标要求"])
    
    # 2. 将优化结果记录添加到历史CSV
    history_file = output_dir / "optimization_history.csv"
    
    # 准备要记录的关键指标
    key_row = {
        "优化ID": optimization_id,
        "标的": symbol,
        "执行时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "胜率": metrics.get("胜率", "N/A"),
        "总收益率": metrics.get("总收益率", "N/A"),
        "夏普比率": metrics.get("夏普比率", "N/A"),
        "最大回撤": metrics.get("最大回撤", "N/A"),
        "盈利因子": metrics.get("盈利因子", "N/A")
    }
    
    # 添加关键参数
    for param, value in optimized_params.items():
        key_row[f"{param}"] = value
    
    # 如果历史文件不存在，创建并写入表头
    if not history_file.exists():
        with open(history_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=key_row.keys())
            writer.writeheader()
            writer.writerow(key_row)
    else:
        # 读取现有历史，追加新行
        rows = []
        with open(history_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []  # 处理可能为None的情况
            rows = list(reader)
        
        # 合并字段名，确保包含所有字段
        all_fieldnames = list(set(list(fieldnames) + list(key_row.keys())))
        
        # 追加新行并写回
        rows.append(key_row)
        with open(history_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    
    # 3. 生成参数配置表（横向排列不同标的的参数）
    params_file = output_dir / "symbol_params.csv"
    
    # 如果参数配置表不存在，创建它
    if not params_file.exists():
        with open(params_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["参数名称", symbol])  # 写入表头
            
            # 写入参数
            for param_name, param_value in sorted(optimized_params.items()):
                writer.writerow([param_name, param_value])
    else:
        # 读取现有参数表
        rows = []
        with open(params_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # 获取表头，检查是否已包含当前标的
        headers = rows[0]
        if symbol in headers:
            # 如果标的已存在，更新对应列
            symbol_col_idx = headers.index(symbol)
            
            # 更新参数值
            for param_name, param_value in sorted(optimized_params.items()):
                # 查找参数行
                param_found = False
                for i, row in enumerate(rows[1:], 1):
                    if row[0] == param_name:
                        # 确保行长度足够
                        while len(row) <= symbol_col_idx:
                            row.append("")
                        row[symbol_col_idx] = param_value
                        param_found = True
                        break
                
                # 如果没找到参数，添加新行
                if not param_found:
                    new_row = [""] * len(headers)
                    new_row[0] = param_name
                    new_row[symbol_col_idx] = param_value
                    rows.append(new_row)
        else:
            # 如果标的不存在，添加新列
            headers.append(symbol)
            
            # 更新每一行添加新列
            for i, row in enumerate(rows[1:], 1):
                row.append("")  # 为每行添加空值
            
            # 添加新参数
            for param_name, param_value in sorted(optimized_params.items()):
                # 查找参数行
                param_found = False
                for i, row in enumerate(rows[1:], 1):
                    if row[0] == param_name:
                        row[-1] = param_value  # 更新最后一列
                        param_found = True
                        break
                
                # 如果没找到参数，添加新行
                if not param_found:
                    new_row = [""] * len(headers)
                    new_row[0] = param_name
                    new_row[-1] = param_value
                    rows.append(new_row)
        
        # 写回更新后的表格
        with open(params_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
    
    logger.info(f"优化报告已保存到: {report_file}")
    logger.info(f"优化历史记录已更新: {history_file}")
    logger.info(f"参数配置表已更新: {params_file}")
    
    return {
        "report": str(report_file),
        "history": str(history_file),
        "params": str(params_file)
    } 