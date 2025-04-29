import logging

import backtrader as bt
from datetime import datetime, timedelta
import pandas as pd

from src.infrastructure import Logger
from src.interface.tiger.tiger_utils import adjust_price_to_tick_size


class TestStrategy(bt.Strategy):
    '''
    实盘交易测试类,极简的策略,进入next后就下单,单只下一次单,用于测试下单是策略与broker的交互情况
    '''
    params = (
        ('symbol', 'AAPL'),  # 交易标的
        ('quantity', 1),     # 交易数量
    )

    def __init__(self):
        self.logger = Logger()
        self.logger.info("TestStrategy初始化")
        self._place_order_done = False  # 下单标记
        self._close_order_done = False  # 平仓标记
        self.order = None  # 当前活跃订单
        self.close_order = None  # 平仓订单
        self.order_ref = None  # 保存开仓订单引用号
        self.close_order_ref = None  # 保存平仓订单引用号
        self.buy_fill_time = None  # 买入订单成交时间
        self.live_mode = False  # 是否处于实时模式
        self.historical_data_end_time = None  # 历史数据结束时间
        
        # 计算历史数据结束时间点
        if self.data.hist_data is not None and not self.data.hist_data.empty:
            last_hist_date = self.data.hist_data.iloc[-1]['utc_date']
            self.historical_data_end_time = pd.to_datetime(last_hist_date)
            self.logger.info(f"历史数据结束时间: {self.historical_data_end_time}")

    def next(self):
        """每个bar调用一次"""
        current_time = self.datetime.datetime()
        current_price = self.data.close[0]
        
        self.logger.info(f'next: time={current_time}, price={current_price}')
        
        # 检查是否是历史数据
        if not self.live_mode:
            # 检查是否已经到达实时数据
            if hasattr(self.data, 'live_mode') and self.data.live_mode:
                self.live_mode = True
                self.logger.info("已切换到实时数据模式")
            else:
                self.logger.info("仍在历史数据阶段，跳过下单")
                return
        
        # 检查是否已经下过单，确保只下单一次
        if self._place_order_done or self.order is not None:
            # 开仓已完成，检查是否需要平仓
            if self.buy_fill_time and not self._close_order_done and self.close_order is None:
                # 检查是否已经过了10秒
                if (current_time - self.buy_fill_time).total_seconds() >= 10:
                    self.logger.info(f"已过10秒，准备平仓 {self.p.symbol}, 当前时间: {current_time}, 买入时间: {self.buy_fill_time}")
                    
                    # 调整价格为符合最小变动单位的值
                    adjusted_price = adjust_price_to_tick_size(current_price, self.p.symbol)
                    
                    # 创建平仓限价单
                    self.close_order = self.sell(size=self.p.quantity, price=adjusted_price)
                    self.close_order_ref = self.close_order
                    self._close_order_done = True
                    self.logger.info(f"已提交平仓订单: {self.close_order}")
            return
        
        # 调整价格为符合最小变动单位的值
        adjusted_price = adjust_price_to_tick_size(current_price, self.p.symbol)
        
        # 下单交易
        self.logger.info(f"准备下单买入 {self.p.symbol}, 数量: {self.p.quantity}, 原始价格: {current_price}, 调整后价格: {adjusted_price}")
        
        # 创建限价单并标记已下单
        self.order = self.buy(size=self.p.quantity, price=adjusted_price)
        self.order_ref = self.order
        self._place_order_done = True
        self.logger.info(f"已提交订单: {self.order}")

    def notify_order(self, order):
        """订单状态更新通知"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交或已接受
            self.logger.info(f'订单已提交/接受: {order.ref}')
            return
            
        if order.status in [order.Completed]:
            # 订单已完成
            if order.isbuy():
                self.logger.info(
                    f'买入委托已成交: 价格: {order.executed.price:.2f}, '
                    f'成本: {order.executed.value:.2f}, '
                    f'手续费: {order.executed.comm:.2f}'
                )
                # 记录买入成交时间
                self.buy_fill_time = self.datetime.datetime()
                self.logger.info(f"买入成交时间: {self.buy_fill_time}")
            else:
                self.logger.info(
                    f'卖出委托已成交: 价格: {order.executed.price:.2f}, '
                    f'收入: {order.executed.value:.2f}, '
                    f'手续费: {order.executed.comm:.2f}'
                )
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # 订单被取消/拒绝或资金不足
            status_map = {
                order.Canceled: '已取消',
                order.Margin: '资金不足',
                order.Rejected: '已拒绝'
            }
            status_text = status_map.get(order.status, '未知状态')
            self.logger.info(f'订单{status_text}: {order.ref}')
            
        # 重置订单引用 - 通过比较订单引用号
        if self.order_ref is not None and order.ref == self.order_ref:
            self.order = None
        elif self.close_order_ref is not None and order.ref == self.close_order_ref:
            self.close_order = None

    def notify_trade(self, trade):
        """交易更新通知"""
        if not trade.isclosed:
            return
            
        self.logger.info(f'交易结束: 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')

    def stop(self):
        """策略结束时调用"""
        # 输出最终结果
        self.logger.info(f'策略结束: 期初资金: {self.broker.startingcash:.2f}, '
                         f'期末资金: {self.broker.getvalue():.2f}, '
                         f'收益: {self.broker.getvalue() - self.broker.startingcash:.2f}')
