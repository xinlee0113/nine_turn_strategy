"""
策略基类
定义策略的接口规范，继承自backtrader的Strategy类
"""
import logging
from typing import Dict, Any

import backtrader as bt


class BaseStrategy(bt.Strategy):
    """
    策略基类
    继承自backtrader的Strategy类，并实现了基本方法
    """

    def __init__(self):
        """初始化策略"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.position_size = 0  # 仓位大小
        self.params = {}

    def log(self, txt, dt=None):
        """日志函数"""
        dt = dt or self.datas[0].datetime.datetime(0)  # 使用datetime而不是date
        self.logger.info(f'{dt.isoformat()} {txt}')

    def set_params(self, params: Dict[str, Any]):
        """设置策略参数
        
        Args:
            params: 策略参数字典
        """
        for key, value in params.items():
            setattr(self.params, key, value)
        self.logger.info(f"更新策略参数: {params}")

    def notify_order(self, order):
        """订单状态更新通知"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单提交或接受状态，不做任何处理
            return

        # 检查订单是否完成
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'买入执行: 价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
            else:  # 卖出
                self.log(
                    f'卖出执行: 价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')

    def notify_trade(self, trade):
        """交易更新通知"""
        if not trade.isclosed:
            return

        self.log(f'交易利润, 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')

    def next(self):
        """策略主循环，在每个bar上调用一次"""
        pass
