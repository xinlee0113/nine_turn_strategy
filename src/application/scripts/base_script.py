"""
基础脚本模块
为所有脚本类提供基础功能
"""
import logging
from typing import Dict, Any

import backtrader as bt
from backtrader import Cerebro
from backtrader.analyzers import SharpeRatio, DrawDown

from src.infrastructure.config.strategy_config import StrategyConfig
from src.infrastructure.logging.logger import Logger
from src.infrastructure.reporting.report_generator import ReportGenerator


class BaseScript:
    """
    脚本基础类
    提供所有脚本共用的基础功能，包括：
    1. 日志记录
    2. 配置加载
    3. 引擎创建
    4. 分析器添加
    5. 结果提取
    """

    def __init__(self):
        """初始化基础脚本"""
        # 初始化日志
        self.logger_manager = Logger()
        self.logger_manager.setup_basic_logging()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"初始化{self.__class__.__name__}")
        
        # 初始化基础组件
        self.cerebro = None
        self.broker = None
        self.strategy = None
        self.data_source = None
        self.store = None
        
        # 初始化报告生成器
        self.report_generator = ReportGenerator()
        
        # 初始化配置
        self.config = None
    
    def load_config(self, config_file: str = 'configs/strategy/magic_nine.yaml'):
        """加载配置
        
        Args:
            config_file: 配置文件路径
        """
        self.logger.info(f"加载配置: {config_file}")
        
        self.config = StrategyConfig()
        self.config.load_config(config_file)
        self.logger.info(f"配置加载完成: {config_file}")
    
    def create_cerebro(self) -> Cerebro:
        """创建引擎
        
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