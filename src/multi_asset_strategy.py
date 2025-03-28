import backtrader as bt
import logging
from src.indicators import MagicNine, RSIBundle, KDJBundle
import numpy as np

logger = logging.getLogger(__name__)

class MultiAssetStrategy(bt.Strategy):
    """多资产神奇九转交易策略 - 每个标的独立交易"""
    params = (
        ('magic_period', 1),    # 神奇九转比较周期，降低为1使信号更频繁
        ('magic_count', 3),     # 神奇九转信号触发计数，降低为3增加交易次数
        ('rsi_oversold', 40),   # RSI超卖值，提高到40更容易触发
        ('rsi_overbought', 60), # RSI超买值，降低到60更容易触发
        ('kdj_oversold', 30),   # KDJ超卖值，提高到30更容易触发
        ('kdj_overbought', 70), # KDJ超买值，降低到70更容易触发
        ('macd_signal', 0),     # MACD信号线
        ('weights', None),      # 资产权重字典，如果为None则平均分配
        ('reserve_pct', 0.05),  # 保留资金比例，不参与交易
    )
    
    def __init__(self):
        """初始化策略"""
        # 订单和交易状态
        self.orders = {}  # 每个标的的订单
        self.position_sizes = {}  # 每个标的的持仓数量
        self.buy_prices = {}  # 每个标的的买入价格
        self.buy_comms = {}  # 每个标的的佣金
        self.asset_values = {}  # 每个标的分配的资金
        
        # 计算每个标的的指标
        self.indicators = {}
        
        # 设置资产权重
        self.calculate_weights()
        
        # 初始化每个数据流的指标
        for i, data in enumerate(self.datas):
            symbol = data._name
            
            # 为每个数据流创建指标
            self.indicators[symbol] = {
                'magic_nine': MagicNine(data, period=self.p.magic_period),
                'rsi': RSIBundle(data),
                'kdj': KDJBundle(data),
                'macd': bt.indicators.MACDHisto(data, period_me1=12, period_me2=26, period_signal=9)
            }
            
            # 初始化订单和持仓状态
            self.orders[symbol] = None
            self.position_sizes[symbol] = 0
            self.buy_prices[symbol] = None
            self.buy_comms[symbol] = None
            
            # 分配资金给该标的
            self.asset_values[symbol] = self.broker.get_value() * (1 - self.p.reserve_pct) * self.weights[symbol]
            
        logger.info(f"多资产策略初始化完成 - 共{len(self.datas)}个标的，资金分配如下:")
        for symbol, value in self.asset_values.items():
            logger.info(f"  - {symbol}: {value:.2f} ({self.weights[symbol] * 100:.2f}%)")
        
    def calculate_weights(self):
        """计算每个资产的权重"""
        if self.p.weights is None:
            # 如果没有指定权重，平均分配
            total_assets = len(self.datas)
            self.weights = {data._name: 1.0 / total_assets for data in self.datas}
        else:
            # 使用指定的权重
            self.weights = self.p.weights
            
            # 确保所有标的都有权重
            for data in self.datas:
                symbol = data._name
                if symbol not in self.weights:
                    self.weights[symbol] = 0.0
            
            # 归一化权重确保总和为1
            total_weight = sum(self.weights.values())
            if total_weight != 1.0:
                for symbol in self.weights:
                    self.weights[symbol] /= total_weight
            
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        symbol = order.data._name
        
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(f'{order.data.datetime.datetime(0).isoformat()} {symbol} 买入执行: 价格: {order.executed.price:.2f}, '
                         f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                self.buy_prices[symbol] = order.executed.price
                self.buy_comms[symbol] = order.executed.comm
            elif order.issell():
                logger.info(f'{order.data.datetime.datetime(0).isoformat()} {symbol} 卖出执行: 价格: {order.executed.price:.2f}, '
                         f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                
                if self.buy_prices[symbol] is not None:
                    profit = (order.executed.price - self.buy_prices[symbol]) * order.executed.size
                    logger.info(f'{order.data.datetime.datetime(0).isoformat()} {symbol} 交易利润: {profit:.2f}')
        
        # 清除该标的的订单
        self.orders[symbol] = None
    
    def notify_trade(self, trade):
        """交易结果通知"""
        if trade.isclosed:
            symbol = trade.data._name
            logger.info(f'{trade.data.datetime.datetime(0).isoformat()} {symbol} 交易利润, 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')
    
    def next(self):
        """主策略逻辑 - 每个标的独立处理"""
        # 为每个数据流单独处理策略逻辑
        for i, data in enumerate(self.datas):
            symbol = data._name
            
            # 如果有未完成的订单，跳过该标的
            if self.orders[symbol]:
                continue
                
            # 获取当前价格和指标
            current_price = data.close[0]
            magic_nine = self.indicators[symbol]['magic_nine']
            
            # 检查是否有仓位
            if not self.getposition(data).size:
                # 没有仓位，检查买入信号
                if magic_nine.lines.buy_signal[0]:
                    # 计算可用资金和购买数量
                    available_cash = self.asset_values[symbol]
                    size = int(available_cash * 0.95 / current_price)  # 使用95%的分配资金
                    
                    if size > 0:
                        logger.info(f'{data.datetime.datetime(0).isoformat()} {symbol} 买入信号! 神奇九转计数: {magic_nine.buy_count}, '
                                 f'价格: {current_price:.2f}, 数量: {size}')
                        
                        # 下买入订单
                        self.orders[symbol] = self.buy(data=data, size=size)
                        self.position_sizes[symbol] = size
            
            else:
                # 已有仓位，检查卖出信号
                if magic_nine.lines.sell_signal[0]:
                    position_size = self.getposition(data).size
                    logger.info(f'{data.datetime.datetime(0).isoformat()} {symbol} 卖出信号! 神奇九转计数: {magic_nine.sell_count}, '
                             f'价格: {current_price:.2f}, 数量: {position_size}')
                    
                    # 下卖出订单
                    self.orders[symbol] = self.sell(data=data, size=position_size)
                    self.position_sizes[symbol] = 0
                    
    def stop(self):
        """策略结束时执行"""
        # 计算每个标的的表现
        returns = {}
        for i, data in enumerate(self.datas):
            symbol = data._name
            # 如果还有持仓，计算当前市值
            position = self.getposition(data)
            
            if position.size > 0:
                current_value = position.size * data.close[0]
                initial_value = self.asset_values[symbol]
                returns[symbol] = (current_value / initial_value - 1) * 100
            else:
                # 如果已清仓，计算分配给该标的的资金相对于初始资金的变化
                current_value = self.broker.get_value() * self.weights[symbol]
                initial_value = self.asset_values[symbol]
                returns[symbol] = (current_value / initial_value - 1) * 100
        
        # 输出每个标的的表现
        logger.info("各标的表现:")
        for symbol, ret in returns.items():
            logger.info(f"  - {symbol}: {ret:.2f}%") 