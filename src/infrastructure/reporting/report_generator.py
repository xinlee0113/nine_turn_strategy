"""
报告生成器模块
负责生成各类回测和优化报告，集中处理报告生成的逻辑
"""
import csv
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.infrastructure.utils.file_utils import ensure_directory_exists, save_backtest_results


class ReportGenerator:
    """
    报告生成器类
    负责生成各类回测和优化报告，包括：
    1. 单标的回测报告
    2. 多标的汇总报告
    3. 回测结果日志输出

    集中管理回测脚本和基础脚本中的报告生成逻辑
    """

    def __init__(self):
        """初始化报告生成器"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("初始化报告生成器")

    def log_results(self, results: Dict[str, Any]) -> None:
        """
        将回测结果记录到日志
        
        Args:
            results: 分析结果字典
        """
        self.logger.info("=" * 50)
        self.logger.info("结果摘要")
        self.logger.info("=" * 50)

        # 记录性能指标
        if 'performance' in results:
            perf = results['performance']
            self.logger.info("性能指标:")
            self.logger.info(f"- 总收益率: {perf.get('total_return', 0) * 100:.2f}%")
            self.logger.info(f"- 年化收益率: {perf.get('annual_return', 0) * 100:.2f}%")

            # 将numpy值转换为Python标准值
            sharpe_ratio = float(perf.get('sharpe_ratio', 0)) if perf.get('sharpe_ratio') is not None else 0.0
            self.logger.info(f"- 夏普比率: {sharpe_ratio:.4f}")
        
        # 记录系统质量指标
        if 'sqn' in results:
            sqn = results['sqn']
            self.logger.info("系统质量指标:")
            self.logger.info(f"- SQN值: {sqn.get('sqn', 0):.4f}")
            self.logger.info(f"- 系统质量评级: {sqn.get('system_quality', '未评级')}")
            self.logger.info(f"- 总交易次数: {sqn.get('total_trades', 0)}")

        # 记录风险指标
        if 'risk' in results:
            risk = results['risk']
            self.logger.info("风险指标:")
            self.logger.info(f"- 最大回撤: {risk.get('max_drawdown', 0) * 100:.2f}%")
            self.logger.info(f"- 最大回撤持续时间: {risk.get('max_drawdown_duration', 0)} 个数据点")
            self.logger.info(f"- 波动率: {risk.get('volatility', 0) * 100:.2f}%")
            
            # 添加索提诺比率
            sortino_ratio = risk.get('sortino_ratio', 0)
            self.logger.info(f"- 索提诺比率: {sortino_ratio:.4f}")

            # 计算卡尔玛比率
            calmar_ratio = risk.get('calmar_ratio', 0)
            self.logger.info(f"- 卡尔玛比率: {calmar_ratio:.4f}")

        # 记录交易统计
        if 'trades' in results and hasattr(results['trades'], 'total'):
            trades = results['trades']
            total = trades.total.total
            won = trades.won.total
            lost = trades.lost.total
            win_rate = won / total if total > 0 else 0

            # 基础交易统计
            self.logger.info("交易统计:")
            self.logger.info(f"- 总交易次数: {total}")
            self.logger.info(f"- 盈利交易: {won}")
            self.logger.info(f"- 亏损交易: {lost}")
            self.logger.info(f"- 胜率: {win_rate * 100:.2f}%")
            
            # 添加平均每天交易次数
            if hasattr(trades, 'avg_trades_per_day'):
                self.logger.info(f"- 交易天数: {trades.trading_days} 天")
                self.logger.info(f"- 平均每天交易次数: {trades.avg_trades_per_day:.2f}")

            # 计算盈亏比
            pnl_won = trades.won.pnl.total
            pnl_lost = abs(trades.lost.pnl.total)
            win_loss_ratio = pnl_won / pnl_lost if pnl_lost > 0 else float('inf')
            self.logger.info(f"- 平均盈亏比: {win_loss_ratio:.2f}")

            # 盈利因子
            profit_factor = pnl_won / pnl_lost if pnl_lost > 0 else float('inf')
            self.logger.info(f"- 盈利因子: {profit_factor:.2f}")

            # 连续盈亏次数
            self.logger.info(f"- 最大连续盈利次数: {trades.streak.won.longest}")
            self.logger.info(f"- 最大连续亏损次数: {trades.streak.lost.longest}")

            # 平均收益和总收益
            self.logger.info(f"- 平均收益: {trades.pnl.net.average:.4f}")
            self.logger.info(f"- 总净利润: {trades.pnl.net.total:.4f}")

        self.logger.info("=" * 50)

    def save_results(self, results: Dict[str, Any], symbol: str, strategy_name: str, 
                    start_date: str, end_date: str, period: str = "1m", 
                    start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> str:
        """
        保存回测结果到CSV文件
        
        Args:
            results: 回测结果
            symbol: 标的
            strategy_name: 策略名称
            start_date: 开始日期
            end_date: 结束日期
            period: 回测周期
            start_time: 回测开始时间
            end_time: 回测结束时间
            
        Returns:
            保存的文件路径
        """
        try:
            # 创建结果目录
            os.makedirs('results/backtest', exist_ok=True)

            # 处理日期格式
            if isinstance(start_date, datetime):
                start_date = start_date.strftime("%Y%m%d")
            if isinstance(end_date, datetime):
                end_date = end_date.strftime("%Y%m%d")
                
            # 添加交易开始和结束时间信息
            if start_time:
                results['start_time'] = start_time.strftime("%Y-%m-%d %H:%M:%S")
            if end_time:
                results['end_time'] = end_time.strftime("%Y-%m-%d %H:%M:%S")

            # 添加标的信息
            results['symbol'] = symbol

            # 调用文件工具函数保存结果
            result_file = save_backtest_results(
                results,
                symbol,
                strategy_name,
                start_date,
                end_date,
                period
            )
            
            self.logger.info(f"{symbol} 回测结果已保存到文件: {result_file}")
            return result_file

        except Exception as e:
            self.logger.error(f"保存 {symbol} 回测结果失败: {str(e)}")
            import traceback
            self.logger.error(f"错误详情: {traceback.format_exc()}")
            return ""

    def generate_summary_report(self, all_results: Dict[str, Dict[str, Any]]) -> str:
        """
        生成多标的回测结果汇总报告
        
        Args:
            all_results: 所有标的的回测结果字典
            
        Returns:
            生成的报告文件路径
        """
        if not all_results:
            self.logger.warning("没有回测结果，无法生成汇总报告")
            return ""
        
        try:
            # 创建结果目录
            summary_dir = "results/backtest/summary"
            os.makedirs(summary_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_filename = f"{timestamp}_multi_symbol_summary.csv"
            summary_path = os.path.join(summary_dir, summary_filename)
            
            # 准备汇总数据
            summary_data = []
            
            # 关键指标列表
            key_metrics = [
                # 性能指标
                "总收益率", "年化收益率", "夏普比率", 
                # 系统质量指标
                "SQN值", "系统质量评级", 
                # 风险指标
                "最大回撤", "最大回撤持续时间", "波动率", "索提诺比率", "卡尔玛比率",
                # 交易统计
                "总交易次数", "盈利交易", "亏损交易", "胜率", "交易天数", "平均每天交易次数", 
                "平均盈亏比", "盈利因子", "最大连续盈利次数", "最大连续亏损次数", 
                "平均收益", "总净利润"
            ]
            
            # 收集所有标的的关键指标
            for symbol, results in all_results.items():
                symbol_data = {"标的": symbol}
                
                # 提取性能指标
                perf = results.get('performance', {})
                symbol_data["总收益率"] = f"{perf.get('total_return', 0) * 100:.2f}%"
                symbol_data["年化收益率"] = f"{perf.get('annual_return', 0) * 100:.2f}%"
                symbol_data["夏普比率"] = f"{float(perf.get('sharpe_ratio', 0) or 0):.4f}"
                
                # 提取系统质量指标
                sqn = results.get('sqn', {})
                symbol_data["SQN值"] = f"{sqn.get('sqn', 0):.4f}"
                symbol_data["系统质量评级"] = sqn.get('system_quality', '未评级')
                
                # 提取风险指标
                risk = results.get('risk', {})
                symbol_data["最大回撤"] = f"{risk.get('max_drawdown', 0) * 100:.2f}%"
                symbol_data["最大回撤持续时间"] = risk.get('max_drawdown_duration', 0)
                symbol_data["波动率"] = f"{risk.get('volatility', 0) * 100:.2f}%"
                symbol_data["索提诺比率"] = f"{risk.get('sortino_ratio', 0):.4f}"
                symbol_data["卡尔玛比率"] = f"{risk.get('calmar_ratio', 0):.4f}"
                
                # 提取交易指标
                trades = results.get('trades', {})
                
                # 基础交易数量统计
                total_trades = trades.get('total', {}).get('total', 0)
                symbol_data["总交易次数"] = total_trades
                
                won_trades = trades.get('won', {}).get('total', 0)
                lost_trades = trades.get('lost', {}).get('total', 0)
                symbol_data["盈利交易"] = won_trades
                symbol_data["亏损交易"] = lost_trades
                
                # 胜率计算
                win_rate = won_trades / total_trades * 100 if total_trades > 0 else 0
                symbol_data["胜率"] = f"{win_rate:.2f}%"
                
                # 交易频率统计
                symbol_data["交易天数"] = trades.get('trading_days', 0)
                symbol_data["平均每天交易次数"] = f"{trades.get('avg_trades_per_day', 0):.2f}"
                
                # 盈亏统计
                pnl_won = trades.get('won', {}).get('pnl', {}).get('total', 0)
                pnl_lost = abs(trades.get('lost', {}).get('pnl', {}).get('total', 0))
                
                # 计算盈亏比
                win_loss_ratio = pnl_won / pnl_lost if pnl_lost > 0 else float('inf')
                symbol_data["平均盈亏比"] = f"{win_loss_ratio:.2f}"
                
                # 计算盈利因子
                profit_factor = pnl_won / pnl_lost if pnl_lost > 0 else float('inf')
                symbol_data["盈利因子"] = f"{profit_factor:.2f}"
                
                # 连续盈亏记录
                symbol_data["最大连续盈利次数"] = trades.get('streak', {}).get('won', {}).get('longest', 0)
                symbol_data["最大连续亏损次数"] = trades.get('streak', {}).get('lost', {}).get('longest', 0)
                
                # 平均收益和总净利润
                symbol_data["平均收益"] = f"{trades.get('pnl', {}).get('net', {}).get('average', 0):.4f}"
                symbol_data["总净利润"] = f"{trades.get('pnl', {}).get('net', {}).get('total', 0):.4f}"
                
                # 添加到汇总数据
                summary_data.append(symbol_data)
            
            # 写入CSV文件
            with open(summary_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["标的"] + key_metrics)
                writer.writeheader()
                writer.writerows(summary_data)
            
            self.logger.info(f"多标的回测汇总报告已保存至: {summary_path}")
            
            # 打印汇总结果
            self.log_summary(summary_data)
            
            return summary_path
            
        except Exception as e:
            self.logger.error(f"生成多标的回测汇总报告失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return ""
    
    def log_summary(self, summary_data: List[Dict[str, Any]]) -> None:
        """
        打印汇总结果到日志
        
        Args:
            summary_data: 汇总数据列表
        """
        self.logger.info("==================================================")
        for symbol_data in summary_data:
            self.logger.info(f"标的: {symbol_data['标的']}")
            
            # 性能指标
            self.logger.info("性能指标:")
            self.logger.info(f"- 总收益率: {symbol_data['总收益率']}")
            self.logger.info(f"- 年化收益率: {symbol_data['年化收益率']}")
            self.logger.info(f"- 夏普比率: {symbol_data['夏普比率']}")
            
            # 系统质量指标
            self.logger.info("系统质量指标:")
            self.logger.info(f"- SQN值: {symbol_data['SQN值']}")
            self.logger.info(f"- 系统质量评级: {symbol_data['系统质量评级']}")
            self.logger.info(f"- 总交易次数: {symbol_data['总交易次数']}")
            
            # 风险指标
            self.logger.info("风险指标:")
            self.logger.info(f"- 最大回撤: {symbol_data['最大回撤']}")
            self.logger.info(f"- 最大回撤持续时间: {symbol_data['最大回撤持续时间']} 个数据点")
            self.logger.info(f"- 波动率: {symbol_data['波动率']}")
            self.logger.info(f"- 索提诺比率: {symbol_data['索提诺比率']}")
            self.logger.info(f"- 卡尔玛比率: {symbol_data['卡尔玛比率']}")
            
            # 交易统计
            self.logger.info("交易统计:")
            self.logger.info(f"- 总交易次数: {symbol_data['总交易次数']}")
            self.logger.info(f"- 盈利交易: {symbol_data['盈利交易']}")
            self.logger.info(f"- 亏损交易: {symbol_data['亏损交易']}")
            self.logger.info(f"- 胜率: {symbol_data['胜率']}")
            self.logger.info(f"- 交易天数: {symbol_data['交易天数']} 天")
            self.logger.info(f"- 平均每天交易次数: {symbol_data['平均每天交易次数']}")
            self.logger.info(f"- 平均盈亏比: {symbol_data['平均盈亏比']}")
            self.logger.info(f"- 盈利因子: {symbol_data['盈利因子']}")
            self.logger.info(f"- 最大连续盈利次数: {symbol_data['最大连续盈利次数']}")
            self.logger.info(f"- 最大连续亏损次数: {symbol_data['最大连续亏损次数']}")
            self.logger.info(f"- 平均收益: {symbol_data['平均收益']}")
            self.logger.info(f"- 总净利润: {symbol_data['总净利润']}")
            
            self.logger.info("==================================================") 