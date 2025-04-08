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
        results: 回测结果字典
        symbol: 交易标的符号
        strategy_name: 策略名称
        start_date: 回测开始日期
        end_date: 回测结束日期
        period: 回测周期
        
    Returns:
        保存的文件路径
    """
    # 确保目录存在
    results_dir = Path("results/backtest")
    ensure_directory_exists(str(results_dir))
    
    # 生成文件名（包含时间戳、标的和策略名称）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{symbol}_{strategy_name}_{start_date}_{end_date}_{period}.csv"
    filepath = results_dir / filename
    
    # 提取需要保存的指标
    metrics = {
        "执行时间": timestamp,
        "交易标的": symbol,
        "策略名称": strategy_name,
        "开始日期": start_date,
        "结束日期": end_date,
        "周期": period,
        "总收益率": results.get("performance", {}).get("total_return", 0),
        "年化收益率": results.get("performance", {}).get("annual_return", 0),
        "夏普比率": results.get("performance", {}).get("sharpe_ratio", 0),
        "最大回撤": results.get("risk", {}).get("max_drawdown", 0),
        "波动率": results.get("risk", {}).get("volatility", 0),
        "卡尔玛比率": results.get("risk", {}).get("calmar_ratio", 0),
        "总交易次数": results.get("trades", {}).get("total_trades", 0),
        "盈利交易": results.get("trades", {}).get("profitable_trades", 0),
        "亏损交易": results.get("trades", {}).get("losing_trades", 0),
        "胜率": results.get("trades", {}).get("win_rate", 0),
        "平均盈亏比": results.get("trades", {}).get("profit_loss_ratio", 0),
        "盈利因子": results.get("trades", {}).get("profit_factor", 0),
        "每笔交易期望收益": results.get("trades", {}).get("expected_payoff", 0),
        "最大连续盈利次数": results.get("trades", {}).get("max_consecutive_wins", 0),
        "最大连续亏损次数": results.get("trades", {}).get("max_consecutive_losses", 0),
        "总净利润": results.get("trades", {}).get("total_net_profit", 0),
        "平均每天交易次数": results.get("trades", {}).get("avg_trades_per_day", 0),
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