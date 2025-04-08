"""
UI模块
负责图形界面相关的组件和管理
遵循单一职责原则，将视图相关的逻辑从业务逻辑中分离
"""

# 将UI管理器导出，便于直接通过模块导入
from .plot_manager import PlotManager

__all__ = [
    'PlotManager'
] 