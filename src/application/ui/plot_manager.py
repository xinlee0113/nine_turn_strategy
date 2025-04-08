"""
绘图管理器
负责管理图表绘制、配置和显示
将绘图逻辑从引擎中分离，实现单一职责
"""
import logging
from typing import Dict, Any, Tuple, Optional, List

import matplotlib.pyplot as plt
import matplotlib as mpl
import backtrader as bt
import pandas as pd
import numpy as np


class PlotManager:
    """
    绘图管理器类
    负责管理绘图相关的功能，包括配置、样式和显示控制
    单例模式，确保全局只有一个绘图管理器实例
    """

    # 单例实例
    _instance = None

    def __new__(cls, *args, **kwargs):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super(PlotManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化绘图管理器"""
        # 避免重复初始化
        if self._initialized:
            return
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("初始化绘图管理器")
        
        # 绘图配置
        self.default_figsize = (20, 10)
        self.default_dpi = 100
        self.default_style = 'candle'
        self.barup_color = '#27A59A'  # 上涨柱状图颜色
        self.bardown_color = '#EF534F'  # 下跌柱状图颜色
        
        # 当前图表追踪
        self.current_figures = []
        self.cerebro_instances = []

        # 默认绘图选项
        self.default_plot_options = {
            'style': 'candle',      # 默认使用蜡烛图
            'volume': True,         # 默认显示成交量
            'show': True,           # 立即显示图表
            'figsize': (20, 10),    # 图表尺寸设置为更大值
            'dpi': 100,             # 分辨率100DPI
            'use': None,            # 使用指定的绘图后端，None表示自动选择
            'barup': '#27A59A',     # 上涨柱状图颜色
            'bardown': '#EF534F',   # 下跌柱状图颜色
            'plotdist': 0.0,        # 子图之间的间距
            'linevalues': True,     # 显示线条数值
            'show_trades': True,    # 默认显示交易观察器
            'show_broker': True,    # 默认显示资金曲线
            'show_buysell': True,   # 默认显示买卖点标记
        }
        
        # 标记为已初始化
        self._initialized = True

    def configure_matplotlib(self, figsize: Tuple[int, int] = None, 
                            dpi: int = None) -> None:
        """
        配置matplotlib全局设置
        
        Args:
            figsize: 图表尺寸(宽, 高)，以英寸为单位
            dpi: 图表分辨率
        """
        figsize = figsize or self.default_figsize
        dpi = dpi or self.default_dpi
        
        # 配置matplotlib
        mpl.rcParams['figure.figsize'] = figsize
        mpl.rcParams['figure.dpi'] = dpi
        mpl.rcParams['savefig.dpi'] = dpi
        
        # 记录配置
        self.logger.info(f"配置matplotlib: figsize={figsize}, dpi={dpi}")

    def get_default_plot_options(self, symbol=None, period=None, start_date=None, end_date=None) -> Dict[str, Any]:
        """
        获取默认绘图选项，可以根据传入的交易对和时间范围自定义图表标题
        
        Args:
            symbol: 交易对代码
            period: 时间周期
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            绘图选项字典
        """
        options = self.default_plot_options.copy()
        
        # 如果提供了交易对和时间信息，设置图表标题
        if symbol and period and start_date and end_date:
            # 格式化日期为字符串
            if hasattr(start_date, 'strftime'):
                start_str = start_date.strftime('%Y-%m-%d')
            else:
                start_str = str(start_date)
                
            if hasattr(end_date, 'strftime'):
                end_str = end_date.strftime('%Y-%m-%d')
            else:
                end_str = str(end_date)
                
            options['plotname'] = f"{symbol} {period} {start_str} to {end_str}"
            
        return options

    def plot_cerebro(self, cerebro: bt.Cerebro, **kwargs) -> Optional[List]:
        """
        使用backtrader的cerebro绘制图表
        
        Args:
            cerebro: Backtrader cerebro实例
            **kwargs: 绘图选项
            
        Returns:
            图表列表，如果绘图失败则返回None
        """
        self.logger.info("开始绘制回测图表")
        
        try:
            # 记录cerebro实例
            self.cerebro_instances.append(cerebro)
            
            # 提取绘图选项
            figsize = kwargs.pop('figsize', self.default_figsize)
            dpi = kwargs.pop('dpi', self.default_dpi)
            style = kwargs.pop('style', self.default_style)
            volume = kwargs.pop('volume', True)
            barup = kwargs.pop('barup', self.barup_color)
            bardown = kwargs.pop('bardown', self.bardown_color)
            
            # 配置matplotlib
            self.configure_matplotlib(figsize, dpi)
            
            # 构建绘图选项
            plot_options = {
                'style': style,
                'volume': volume,
                'barup': barup,
                'bardown': bardown,
            }
            
            # 合并自定义选项
            plot_options.update({k: v for k, v in kwargs.items() 
                                if k not in ['figsize', 'dpi']})
            
            # 绘制图表
            self.logger.info(f"使用参数绘制: style={style}, volume={volume}")
            figures = cerebro.plot(**plot_options)
            
            # 记录当前图表
            if figures:
                self.current_figures.extend(figures)
                self.logger.info(f"成功创建{len(figures)}个图表")
            else:
                self.logger.warning("未创建任何图表")
            
            return figures
            
        except Exception as e:
            self.logger.error(f"绘图失败: {str(e)}")
            import traceback
            self.logger.error(f"错误详情: {traceback.format_exc()}")
            return None

    def set_engine_plot_options(self, engine, enabled=True, symbol=None, period=None, 
                              start_date=None, end_date=None, **custom_options) -> None:
        """
        设置引擎的绘图选项
        
        Args:
            engine: 回测引擎实例
            enabled: 是否启用绘图
            symbol: 交易对代码，用于图表标题
            period: 时间周期，用于图表标题
            start_date: 开始日期，用于图表标题
            end_date: 结束日期，用于图表标题
            **custom_options: 自定义绘图选项
        """
        if not hasattr(engine, 'set_plot_options'):
            self.logger.warning("引擎不支持设置绘图选项")
            return
        
        # 获取默认选项
        options = self.get_default_plot_options(symbol, period, start_date, end_date)
        
        # 更新自定义选项
        options.update(custom_options)
        
        # 设置引擎绘图选项
        engine.set_plot_options(enabled=enabled, **options)
        self.logger.info(f"{'启用' if enabled else '禁用'}引擎绘图功能")
        if enabled:
            option_info = {k: v for k, v in options.items() if k not in ['figsize', 'barup', 'bardown']}
            self.logger.debug(f"设置引擎绘图选项: {option_info}")
            self.logger.info(f"图表尺寸: {options.get('figsize')}, 分辨率: {options.get('dpi')}")
            self.logger.info(f"图表标题: {options.get('plotname', '未设置')}")

    def plot_dataframe(self, df: pd.DataFrame, title: str = None, 
                      **kwargs) -> Optional[plt.Figure]:
        """
        绘制pandas DataFrame数据
        
        Args:
            df: 包含价格数据的DataFrame
            title: 图表标题
            **kwargs: 绘图选项
            
        Returns:
            matplotlib Figure对象，绘图失败则返回None
        """
        try:
            # 提取绘图选项
            figsize = kwargs.pop('figsize', self.default_figsize)
            dpi = kwargs.pop('dpi', self.default_dpi)
            
            # 配置matplotlib
            self.configure_matplotlib(figsize, dpi)
            
            # 创建图表
            fig, axes = plt.subplots(nrows=2, ncols=1, figsize=figsize, dpi=dpi,
                                    gridspec_kw={'height_ratios': [3, 1]})
            
            # 绘制价格图
            ax_price = axes[0]
            if 'close' in df.columns:
                df['close'].plot(ax=ax_price, color='blue', linewidth=1.5, label='收盘价')
            
            # 添加移动平均线（如果有）
            for col in df.columns:
                if col.startswith('ma') or col.startswith('ema'):
                    df[col].plot(ax=ax_price, linewidth=1, label=col)
            
            # 设置轴标签和图例
            ax_price.set_ylabel('价格')
            ax_price.legend(loc='best')
            ax_price.grid(True, alpha=0.3)
            
            # 绘制成交量图
            ax_volume = axes[1]
            if 'volume' in df.columns:
                df['volume'].plot(ax=ax_volume, kind='bar', color='gray', alpha=0.5)
                ax_volume.set_ylabel('成交量')
                ax_volume.grid(True, alpha=0.3)
            
            # 设置图表标题
            if title:
                fig.suptitle(title)
                
            # 调整布局
            fig.tight_layout()
            
            # 记录当前图表
            self.current_figures.append(fig)
            
            return fig
            
        except Exception as e:
            self.logger.error(f"绘制DataFrame失败: {str(e)}")
            import traceback
            self.logger.error(f"错误详情: {traceback.format_exc()}")
            return None

    def save_current_figure(self, filename: str, dpi: int = None) -> bool:
        """
        保存当前图表到文件
        
        Args:
            filename: 文件路径
            dpi: 图像分辨率
            
        Returns:
            保存成功返回True，否则返回False
        """
        try:
            if not self.current_figures:
                self.logger.warning("没有可保存的图表")
                return False
                
            # 获取最新的图表
            fig = self.current_figures[-1]
            
            # 保存图表
            fig.savefig(filename, dpi=dpi or self.default_dpi)
            self.logger.info(f"保存图表到: {filename}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"保存图表失败: {str(e)}")
            return False

    def close_all_figures(self) -> None:
        """关闭所有打开的图表"""
        plt.close('all')
        self.current_figures.clear()
        self.logger.info("关闭所有图表")

    def shutdown(self) -> None:
        """关闭绘图管理器，清理资源"""
        self.logger.info("关闭绘图管理器")
        self.close_all_figures()
        self.cerebro_instances.clear() 