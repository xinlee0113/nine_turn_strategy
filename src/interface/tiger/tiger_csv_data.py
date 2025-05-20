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
        # 构建包含时间范围的文件名
        from_date_str = self.p.fromdate.strftime('%Y%m%d')
        to_date_str = self.p.todate.strftime('%Y%m%d')
        self.tmp_csv_data_path = os.path.join(base_dir, "data", "cache", 'tiger', symbol, 
                                             f'tiger_{from_date_str}_{to_date_str}_{self.p.period.value}_k_line.csv')

        # 确保数据目录存在
        data_dir = os.path.dirname(self.tmp_csv_data_path)
        os.makedirs(data_dir, exist_ok=True)

        # 设置数据文件路径
        self.p.dataname = self.tmp_csv_data_path
        print(f"设置数据文件路径: {self.p.dataname}")

    def start(self):
        print(f"开始加载 {self.p.symbol} 数据")

        # 检查是否需要重新获取数据
        need_refresh = False
        if os.path.exists(self.p.dataname):
            # 读取现有数据的时间范围
            df = pd.read_csv(self.p.dataname)
            df['utc_date'] = pd.to_datetime(df['utc_date'])
            # 确保时间戳是naive datetime
            existing_start = df['utc_date'].min().tz_localize(None)
            existing_end = df['utc_date'].max().tz_localize(None)
            
            # 确保fromdate和todate也是naive datetime
            fromdate = self.p.fromdate.tz_localize(None) if self.p.fromdate.tzinfo else self.p.fromdate
            todate = self.p.todate.tz_localize(None) if self.p.todate.tzinfo else self.p.todate
            
            # 检查时间范围是否匹配
            # 考虑到美股交易时间（美东时间9:30-16:00），我们允许一定的日期误差
            # 将时间转换为日期进行比较
            existing_start_date = existing_start.date()
            existing_end_date = existing_end.date()
            fromdate_date = fromdate.date()
            todate_date = todate.date()
            
            # 如果现有数据的日期范围基本覆盖了请求的日期范围（允许前后各1天的误差），则认为数据满足需求
            if (existing_start_date - fromdate_date).days <= 1 and (todate_date - existing_end_date).days <= 1:
                print(f"现有数据时间范围 ({existing_start} 到 {existing_end}) 满足需求 ({fromdate} 到 {todate})")
            else:
                print(f"现有数据时间范围 ({existing_start} 到 {existing_end}) 与需求时间 ({fromdate} 到 {todate}) 差异过大")
                need_refresh = True
        else:
            need_refresh = True

        # 如果需要刷新数据，则从 Tiger API 获取数据并保存到 CSV 文件
        if need_refresh:
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
