import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Any

import backtrader as bt
import pandas as pd
from tigeropen.common.consts import Market, SecurityType, Currency, BarPeriod
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.trade.trade_client import TradeClient

from src.interface.broker.tiger import TigerClientManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class TigerRealtimeData(bt.feeds.DataBase):
    """老虎证券实时数据源"""

    lines = ('open', 'high', 'low', 'close', 'volume')
    params = (
        ('symbol', 'QQQ'),
        ('market', Market.US),
        ('sec_type', SecurityType.STK),
        ('interval', 5),  # 数据更新间隔（秒）
        ('historical_days', 5),  # 加载的历史数据天数
    )

    def __init__(self, trade_client, quote_client, contract_manager):
        super().__init__()
        self.trade_client = trade_client
        self.quote_client = quote_client
        self.contract_manager = contract_manager
        self.bar_data_manager = TigerClientManager().tiger_bar_data_manager
        self.last_time = time.time()
        self.live_mode = False
        self.data_loaded = False

        # 获取合约
        self.contract = self.contract_manager.get_contract(self.p.symbol)
        logging.info(f'初始化数据源，合约={self.contract}')

        # 检查市场状态
        self.market_open = self._check_market_open()
        logging.info(f'市场开盘状态: {"开盘" if self.market_open else "休市"}')

        # 加载历史数据
        self.hist_data = self._load_historical_data()
        self.hist_index = 0

    def _check_market_open(self):
        """检查市场是否开盘"""
        try:
            status = self.quote_client.get_market_status(self.p.market)[0]
            return status.trading_status != 'MARKET_CLOSED'
        except Exception as e:
            logging.error(f"检查市场状态出错: {e}")
            return False

    def _load_historical_data(self):
        """加载历史数据"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.p.historical_days)

            logging.info(f"正在加载{self.p.symbol}的历史数据，从{start_date}到{end_date}")

            # 使用老虎证券API获取历史数据
            bars = self.bar_data_manager.get_bar_data(
                symbol=self.p.symbol,
                begin_time=start_date,
                end_time=end_date,
                period=BarPeriod.ONE_MINUTE
            )

            if bars is None or bars.empty:
                logging.warning("未获取到历史数据，将使用空数据帧")
                return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])

            logging.info(f"成功加载{len(bars)}条历史数据")
            return bars

        except Exception as e:
            logging.error(f"加载历史数据出错: {e}")
            # 返回空数据帧
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])

    def start(self):
        """启动数据源"""
        super().start()
        logging.info("启动数据源")

    def _load(self):
        """加载数据"""
        # 首先传递历史数据
        if not self.data_loaded and self.hist_data is not None and not self.hist_data.empty:
            if self.hist_index < len(self.hist_data):
                bar = self.hist_data.iloc[self.hist_index]

                # 更新数据线
                self.lines.open[0] = float(bar['open'])
                self.lines.high[0] = float(bar['high'])
                self.lines.low[0] = float(bar['low'])
                self.lines.close[0] = float(bar['close'])
                self.lines.volume[0] = float(bar['volume'] if 'volume' in bar else 0)

                # 设置日期
                dt = pd.to_datetime(bar['utc_date'])
                self.lines.datetime[0] = bt.date2num(dt)
                self.hist_index += 1
                return True
            else:
                self.data_loaded = True
                logging.info("历史数据加载完成，切换到实时数据模式")
                self.live_mode = True

        # 历史数据加载完后，切换到实时数据模式
        if self.live_mode:
            return self._load_realtime_data()

        # 如果没有历史数据，直接切换到实时模式
        if not self.data_loaded and (self.hist_data is None or self.hist_data.empty):
            self.data_loaded = True
            self.live_mode = True
            return self._load_realtime_data()

        return False

    def _load_realtime_data(self):
        """加载实时数据"""
        # 检查市场状态
        if not self.market_open:
            self.market_open = self._check_market_open()
            if not self.market_open:
                time.sleep(1)  # 市场未开盘时，短暂休眠
                return False

        # 控制数据获取频率
        current_time = time.time()
        if current_time - self.last_time < self.p.interval:
            time.sleep(0.1)  # 短暂休眠，避免CPU占用过高
            return False

        self.last_time = current_time

        try:
            # 获取实时行情
            quote = self.quote_client.get_stock_briefs([self.p.symbol])

            if quote is None or quote.empty:
                logging.warning(f"获取行情数据失败，将在{self.p.interval}秒后重试")
                return False

            # 更新数据线
            self.lines.open[0] = float(quote['open'][0])
            self.lines.high[0] = float(quote['high'][0])
            self.lines.low[0] = float(quote['low'][0])
            self.lines.close[0] = float(quote['close'][0])
            self.lines.volume[0] = float(quote['volume'][0])

            # 更新时间戳
            self.lines.datetime[0] = bt.date2num(datetime.now())

            logging.info(f'获取实时数据成功: {self.p.symbol}, 价格={self.lines.close[0]}')
            return True

        except Exception as e:
            logging.error(f"获取实时数据出错: {e}")
            return False


