"""
基础脚本类
为各种脚本提供通用功能，如分析器添加、结果处理等
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from backtrader import Cerebro
from backtrader.analyzers import SharpeRatio, DrawDown, TradeAnalyzer

from src.infrastructure.config.strategy_config import StrategyConfig
from src.infrastructure.logging.logger import Logger


class BaseScript:
    """
    脚本基类
    提供所有脚本共享的基础功能：
    1. 配置加载
    2. 引擎创建与配置 
    3. 分析器管理
    4. 结果处理与日志
    """

    def __init__(self):
        """初始化基础脚本类"""
        # 初始化日志
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        self.logger_manager = Logger()
        
        # 初始化配置
        self.strategy_config = StrategyConfig()
        
        # 初始化引擎和组件
        self.cerebro = None
        self.strategy = None
        self.data_source = None
        self.broker = None
        self.store = None
        
        # 执行时间记录
        self.start_time = None
        self.end_time = None

    def load_config(self, config_file: str = 'configs/strategy/magic_nine.yaml'):
        """加载配置文件
        
        Args:
            config_file: 配置文件路径
        """
        self.logger.info(f"加载配置: {config_file}")
        self.strategy_config.load_config(config_file)
        return self.strategy_config
    
    def create_cerebro(self) -> Cerebro:
        """创建回测/交易引擎
        
        Returns:
            Cerebro: 创建好的引擎实例
        """
        self.logger.info("创建引擎")
        self.cerebro = Cerebro()
        self.cerebro.p.oldbuysell = True
        return self.cerebro
    
    def setup_broker(self, cash: float = 10000.0):
        """设置经纪商
        
        Args:
            cash: 初始资金
        """
        if self.cerebro:
            self.logger.info(f"配置Broker，初始资金: {cash}")
            self.cerebro.broker.setcash(cash)
    
    def add_analyzers(self):
        """添加分析器到引擎"""
        if not self.cerebro:
            self.logger.error("引擎未创建，无法添加分析器")
            return
            
        self.logger.info("添加分析器")
        
        # 导入自定义分析器
        from src.business.analyzers.performance_analyzer import PerformanceAnalyzer
        from src.business.analyzers.risk_analyzer import RiskAnalyzer
        from src.business.analyzers.sqn_analyzer import SQNAnalyzer
        from src.business.analyzers.enhanced_trade_analyzer import EnhancedTradeAnalyzer
        
        # 添加分析器，使用一致的命名
        self.cerebro.addanalyzer(PerformanceAnalyzer, _name='performanceanalyzer')
        self.cerebro.addanalyzer(RiskAnalyzer, _name='riskanalyzer')
        self.cerebro.addanalyzer(SQNAnalyzer, _name='sqnanalyzer')
        
        # 配置SharpeRatio分析器
        # 关键参数: riskfreerate设为0，factor=1让标准差永远>0
        from backtrader import TimeFrame
        self.cerebro.addanalyzer(SharpeRatio, 
                               _name='sharperatio',
                               timeframe=None,  # 不指定timeframe，使用默认值
                               factor=1,  # 添加小额因子避免标准差为零
                               riskfreerate=0.0)
                               
        self.cerebro.addanalyzer(DrawDown, _name='drawdown')
        # 使用增强版交易分析器替代原生TradeAnalyzer
        self.cerebro.addanalyzer(EnhancedTradeAnalyzer, _name='tradeanalyzer')
    
    def extract_analyzer_results(self, strategy) -> Dict[str, Any]:
        """从策略实例中提取分析器结果
        
        Args:
            strategy: 策略实例
            
        Returns:
            Dict: 分析结果字典
        """
        analysis_results = {'performance': {}, 'risk': {}, 'trades': {}, 'sqn': {}}

        # 从性能分析器获取结果
        perf = strategy.analyzers.performanceanalyzer
        analysis_results['performance'] = perf.get_analysis()
        self.logger.info(f"成功提取性能分析器结果")

        # 从风险分析器获取结果
        risk = strategy.analyzers.riskanalyzer
        analysis_results['risk'] = risk.get_analysis()
        self.logger.info(f"成功提取风险分析器结果")

        # 从交易分析器获取结果
        trade = strategy.analyzers.tradeanalyzer
        analysis_results['trades'] = trade.get_analysis()
        self.logger.info(f"成功提取交易分析器结果")
        
        # 从SQN分析器获取结果
        sqn = strategy.analyzers.sqnanalyzer
        analysis_results['sqn'] = sqn.get_analysis()
        self.logger.info(f"成功提取SQN分析器结果")

        # 从sharperatio分析器获取结果
        sharpe = strategy.analyzers.sharperatio
        sharpe_analysis = sharpe.get_analysis()
        # 直接获取夏普比率值，不设默认值
        sharpe_value = sharpe_analysis.get('sharperatio')
        self.logger.info(f"Backtrader夏普比率值: {sharpe_value}")
        
        # 直接将原始夏普比率值赋给结果
        analysis_results['performance']['sharpe_ratio'] = sharpe_value
        
        # 从drawdown分析器获取结果
        dd = strategy.analyzers.drawdown
        dd_analysis = dd.get_analysis()
        analysis_results['risk']['max_drawdown'] = dd_analysis.get('max', {}).get('drawdown', 0.0) / 100.0
        analysis_results['risk']['max_drawdown_length'] = dd_analysis.get('max', {}).get('len', 0)

        self.logger.info(f"已从引擎中提取分析结果: {list(analysis_results.keys())}")

        return analysis_results
        
    def log_results(self, results: Dict[str, Any]):
        """记录结果到日志
        
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
    
    def run(self, **kwargs):
        """运行脚本的抽象方法，需要子类实现"""
        raise NotImplementedError("子类必须实现run方法")
    
    def stop(self):
        """停止脚本执行"""
        self.logger.info("停止脚本执行")
        if self.data_source:
            self.data_source.stop()
        if self.cerebro:
            self.cerebro.stop()
        if self.store:
            self.store.stop()
        self.logger.info("脚本已停止") 