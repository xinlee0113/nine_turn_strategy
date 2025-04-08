"""
自定义Pandas数据源适配器
解决不同版本Backtrader PandasData参数不一致的问题
"""
import logging
import pandas as pd
import backtrader as bt

logger = logging.getLogger(__name__)


class CustomPandasData(bt.feeds.PandasData):
    """
    自定义Pandas数据源适配器
    
    用于解决不同版本Backtrader PandasData参数不匹配的问题，
    确保能够正确加载pandas DataFrame数据。
    """
    
    def __init__(self, df=None, **kwargs):
        """
        初始化自定义Pandas数据源
        
        参数:
            df: pandas DataFrame数据源
            **kwargs: 其他参数，将透传给底层PandasData
        """
        self.logger = logging.getLogger(__name__)
        
        if df is None:
            self.logger.error("未提供数据源DataFrame")
            raise ValueError("必须提供pandas DataFrame作为数据源")
            
        # 确保DataFrame索引是日期时间类型
        if not isinstance(df.index, pd.DatetimeIndex):
            self.logger.warning("数据索引不是DatetimeIndex类型，尝试转换")
            df.index = pd.to_datetime(df.index)
        
        # 检查必要的列是否存在
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                self.logger.error(f"数据源缺少必要的列: {col}")
                raise ValueError(f"DataFrame必须包含列: {col}")
                
        # 尝试使用兼容的方式初始化PandasData
        try:
            # 尝试第一种参数形式
            super().__init__(
                dataname=df,
                datetime=None,  # 使用索引作为日期时间
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
                openinterest=-1  # 不使用持仓量
            )
            self.logger.info("使用标准参数形式初始化PandasData成功")
        except Exception as e1:
            self.logger.warning(f"使用标准参数形式初始化PandasData失败: {e1}")
            try:
                # 尝试第二种参数形式
                super().__init__(data=df)
                self.logger.info("使用data参数形式初始化PandasData成功")
            except Exception as e2:
                self.logger.warning(f"使用data参数形式初始化PandasData也失败: {e2}")
                try:
                    # 尝试第三种形式，直接传递数据帧
                    super().__init__(df)
                    self.logger.info("使用直接传递数据帧形式初始化PandasData成功")
                except Exception as e3:
                    self.logger.error(f"所有初始化PandasData尝试均失败: {e3}")
                    raise ValueError(f"无法初始化PandasData: {e1}, {e2}, {e3}") 