import os
from datetime import datetime, timedelta

import backtrader as bt
import pandas as pd
from tigeropen.common.consts import BarPeriod


class TigerCsvData(bt.CSVDataBase):
    """CSV数据接口，用于从CSV文件加载历史数据"""
    params = (
        ('symbol', 'QQQ'),  # 标的符号
        ('timeframe', bt.TimeFrame.Minutes),
        ('todate', datetime.now()),
        ('fromdate', datetime.now() - timedelta(days=30)),
        ('period', BarPeriod.ONE_MINUTE),
        ('desc', '老虎证券最近30天的k线数据'),
        ('store', None)
    )

    def __init__(self):
        print(f'初始化 TigerCsvData，标的: {self.p.symbol}')

        # 确保数据缓存目录存在
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

        # 使用当前symbol参数构建文件路径
        symbol = self.p.symbol
        self.tmp_csv_data_path = os.path.join(base_dir, "data", "cache", 'tiger', symbol, f'tiger_30days_1min_k_line.csv')

        # 确保数据目录存在
        data_dir = os.path.dirname(self.tmp_csv_data_path)
        os.makedirs(data_dir, exist_ok=True)

        # 设置数据文件路径
        self.p.dataname = self.tmp_csv_data_path
        print(f"设置数据文件路径: {self.p.dataname}")

    def start(self):
        print(f"开始加载 {self.p.symbol} 数据")

        # 如果csv数据文件不存在，则从 Tiger API 获取数据并保存到 CSV 文件
        if not os.path.exists(self.p.dataname):
            print(f"获取 {self.p.symbol} 数据并保存到 {self.p.dataname}")
            df = self.p.store.get_bar_data(symbol=self.p.symbol,
                                           begin_time=self.p.fromdate,
                                           end_time=self.p.todate,
                                           period=self.p.period)
            # 确保数据按时间排序
            df.set_index('utc_date', inplace=True)
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)
            # 保存到CSV文件
            df.to_csv(self.p.dataname)
            print(f'{self.p.symbol} 数据形状: {df.shape}')

        # 调用父类的start方法进行数据加载
        super(TigerCsvData, self).start()

    def _loadline(self, linetokens):
        # 解析日期时间
        dt = pd.to_datetime(linetokens[0])
        self.lines.datetime[0] = bt.date2num(dt)
        # 解析开盘价
        self.lines.open[0] = float(linetokens[3])
        # 解析最高价
        self.lines.high[0] = float(linetokens[4])
        # 解析最低价
        self.lines.low[0] = float(linetokens[5])
        # 解析收盘价
        self.lines.close[0] = float(linetokens[6])
        # 解析成交量
        self.lines.volume[0] = float(linetokens[7])
        return True
