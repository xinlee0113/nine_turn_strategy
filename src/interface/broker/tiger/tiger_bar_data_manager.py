import os
import time

import pandas as pd
import pytz
from tigeropen.common.consts import BarPeriod, QuoteRight
from tigeropen.common.exceptions import ApiException
from tigeropen.quote.quote_client import QuoteClient


class TigerBarDataManager:
    def __init__(self, quote_client: QuoteClient):
        self.quote_client = quote_client


    def get_bar_data(self, symbol, begin_time, end_time, period):
        # 确保时间是naive的（没有时区信息）
        if begin_time.tzinfo is not None:
            begin_time = begin_time.replace(tzinfo=None)
        if end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)

        # 正确处理时区转换，使用当前时间而不是未来时间
        begin_time = pd.Timestamp(begin_time).tz_localize('US/Eastern').value // 10 ** 6
        end_time = pd.Timestamp(end_time).tz_localize('US/Eastern').value // 10 ** 6

        print(begin_time, end_time)
        return self.get_bars_by_page(symbol=symbol,
                                     begin_time=begin_time,
                                     end_time=end_time,
                                     period=period,
                                     time_interval=1,
                                     )

    def get_bars_by_page(self, symbol, period=BarPeriod.DAY, begin_time=-1, end_time=-1, total=10000, page_size=1000,
                         right=QuoteRight.BR, time_interval=2, lang=None, trade_session=None):
        """
        request bats by page
        :param symbol: symbol of stock.
        :param period:
        :param begin_time:
        :param end_time: time of the latest bar, excluded
        :param total: Total bars number
        :param page_size: Bars number of each request
        :param right:
        :param time_interval: Time interval between requests
        :param lang:
        :return:
        """
        if begin_time == -1 and end_time == -1:
            raise ApiException(400, 'One of the begin_time or end_time must be specified')
        if isinstance(symbol, list) and len(symbol) != 1:
            raise ApiException(400, 'Paging queries support only one symbol at each request')
        current = 0
        next_page_token = None
        result = list()
        result_df = None
        while current < total:
            if current + page_size >= total:
                page_size = total - current
            current += page_size
            bars = self.quote_client.get_bars(symbols=symbol, period=period, begin_time=begin_time,
                                              end_time=end_time,
                                              right=right,
                                              limit=page_size, lang=lang, trade_session=trade_session,
                                              page_token=next_page_token)
            bars['utc_date'] = pd.to_datetime(bars['time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('UTC')
            print(f'loading data from {bars["utc_date"].iloc[0]} to {bars["utc_date"].iloc[-1]}')
            if bars.empty:
                result_df = bars
                break
            next_page_token = bars['next_page_token'].iloc[0]
            result.append(bars)
            if not next_page_token:
                break
            time.sleep(time_interval)
        return pd.concat(result).sort_values('time').reset_index(drop=True) if result else result_df
