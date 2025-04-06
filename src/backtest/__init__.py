"""
回测模块包，包含回测结果分析和报告生成。
用于分析回测结果并生成报告。
"""

from .engine import BacktestEngine
from .analyzer import BacktestAnalyzer
from .metrics import PerformanceMetrics
from .visualizer import BacktestVisualizer

__all__ = [
    'BacktestEngine',
    'BacktestAnalyzer',
    'PerformanceMetrics',
    'BacktestVisualizer'
] 