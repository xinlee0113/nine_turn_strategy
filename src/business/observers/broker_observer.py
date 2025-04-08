"""
自定义Broker观察器
用于显示资金曲线
"""
import backtrader as bt
import logging

logger = logging.getLogger(__name__)


class BrokerObserver(bt.Observer):
    """
    自定义资金曲线观察器，替代BrokerValue
    
    显示账户价值的变化，与Backtrader的Broker观察器功能相同，
    但确保与所有版本的Backtrader兼容。
    """
    
    lines = ('broker', 'cash')
    
    plotinfo = dict(
        plot=True,
        subplot=True,
        plotname='账户价值',
        plotlinelabels=True,
        plotlinevalues=True,
        plotvaluetags=True,
    )
    
    plotlines = dict(
        broker=dict(
            _name='价值',
            color='blue',
            linewidth=1.0,
        ),
        cash=dict(
            _name='现金',
            color='green',
            linewidth=1.0,
        ),
    )
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("初始化自定义Broker观察器")
    
    def next(self):
        # 记录当前时间点的账户价值和现金
        self.lines.broker[0] = self._owner.broker.getvalue()
        self.lines.cash[0] = self._owner.broker.getcash() 