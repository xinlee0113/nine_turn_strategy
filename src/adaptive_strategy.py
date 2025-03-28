import backtrader as bt
import numpy as np
from datetime import datetime, timedelta
import logging
from collections import defaultdict

from .strategy_selector import StrategyType
from .indicators import MagicNine, RSIBundle, KDJBundle

logger = logging.getLogger(__name__)

class AdaptiveStrategy(bt.Strategy):
    """
    自适应策略类：根据市场情况动态切换不同的交易策略模式
    直接实现多种策略逻辑，而不是嵌套实例化其他策略
    """
    
    params = (
        ('magic_period', 2),  # 神奇九转比较周期
        ('magic_count', 5),   # 神奇九转信号触发计数
        ('strategy_selector', None),  # 策略选择器
        ('market_analyzer', None),  # 市场分析器
        ('switch_delay', 3),  # 策略切换延迟（天数）
        
        # 止损参数 (用于各种止损策略)
        ('atr_period', 14),  # ATR周期
        ('atr_multiplier', 2.5),  # ATR乘数
        ('stop_loss_pct', 3.0),  # 最大止损百分比
        ('min_profit_pct', 1.0),  # 启动追踪止损的最小盈利百分比
        ('trailing_stop', True),  # 是否启用追踪止损
        ('risk_aversion', 1.0),  # 风险规避系数
        ('volatility_adjust', True),  # 是否使用波动性自适应调整
        ('market_aware', True),  # 是否使用市场环境感知
        ('time_decay', True),  # 是否使用时间衰减
        ('time_decay_days', 3),  # 时间衰减开始的天数
    )
    
    def __init__(self):
        """初始化自适应策略"""
        # 订单和交易状态
        self.order = None
        self.buy_price = {}  # 按标的存储买入价格
        self.buy_comm = {}  # 按标的存储买入佣金
        self.position_size = {}  # 按标的存储持仓数量
        self.stop_loss_price = {}  # 按标的存储止损价格
        self.highest_price = {}  # 按标的存储最高价格
        self.holding_days = {}  # 按标的存储持有天数
        
        # 当前策略状态
        self.current_strategy = {}  # 当前激活的策略类型（按标的存储）
        self.strategy_switch_time = {}  # 上次策略切换时间（按标的存储）
        self.strategy_switches = []  # 策略切换记录
        self.strategy_usage_count = defaultdict(int)  # 策略使用计数
        
        # 检查策略选择器和市场分析器是否已提供
        if self.p.strategy_selector is None:
            raise ValueError("必须提供策略选择器")
        
        # 为每个数据源创建指标和初始化状态
        for i, d in enumerate(self.datas):
            symbol = d._name
            
            # 计算神奇九转指标
            setattr(self, f'magic_nine_{i}', MagicNine(d, period=self.p.magic_period))
            
            # 计算ATR指标，用于动态止损
            setattr(self, f'atr_{i}', bt.indicators.ATR(d, period=self.p.atr_period))
            
            # 其他辅助指标（不强制用于信号决策）
            setattr(self, f'rsi_{i}', RSIBundle(d))
            setattr(self, f'kdj_{i}', KDJBundle(d))
            setattr(self, f'macd_{i}', bt.indicators.MACD(d, period_me1=12, period_me2=26, period_signal=9))
            
            # 初始化状态
            self.buy_price[symbol] = None
            self.buy_comm[symbol] = None
            self.position_size[symbol] = 0
            self.stop_loss_price[symbol] = None
            self.highest_price[symbol] = None
            self.holding_days[symbol] = 0
            
            # 初始情况下，使用原始策略
            self.current_strategy[symbol] = StrategyType.ORIGINAL
            self.strategy_switch_time[symbol] = datetime.now() - timedelta(days=self.p.switch_delay + 1)
            
            # 记录初始策略使用
            self.strategy_usage_count[StrategyType.ORIGINAL] += 1
        
        logger.info(f"自适应策略初始化完成 (比较周期:{self.p.magic_period}, 信号触发计数:{self.p.magic_count})")
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        # 获取标的名称
        symbol = order.data._name
        
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(f'{order.data.datetime.datetime(0).isoformat()} 买入执行: 价格: {order.executed.price:.2f}, '
                         f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                self.buy_price[symbol] = order.executed.price
                self.buy_comm[symbol] = order.executed.comm
                
                # 设置初始止损价格（如果使用止损策略）
                active_strategy_type = self.current_strategy[symbol]
                if active_strategy_type in [StrategyType.ADVANCED_STOP_LOSS, StrategyType.SMART_STOP_LOSS]:
                    self._set_initial_stop_loss(order.data)
                
            elif order.issell():
                logger.info(f'{order.data.datetime.datetime(0).isoformat()} 卖出执行: 价格: {order.executed.price:.2f}, '
                         f'成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                
                if self.buy_price[symbol] is not None:
                    profit = (order.executed.price - self.buy_price[symbol]) * order.executed.size
                    profit_pct = (order.executed.price / self.buy_price[symbol] - 1) * 100
                    logger.info(f'{order.data.datetime.datetime(0).isoformat()} 交易利润: {profit:.2f} ({profit_pct:.2f}%)')
                
                # 重置止损和最高价格
                self.stop_loss_price[symbol] = None
                self.highest_price[symbol] = None
                self.holding_days[symbol] = 0
        
        self.order = None
    
    def notify_trade(self, trade):
        """交易结果通知"""
        if trade.isclosed:
            logger.info(f'{trade.data.datetime.datetime(0).isoformat()} 交易利润, 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')
    
    def next(self):
        """每个K线触发的主要逻辑"""
        current_date = self.datetime.date()
        
        for i, d in enumerate(self.datas):
            symbol = d._name
            
            # 如果有未完成的订单，跳过该标的
            if self.order:
                continue
            
            # 检查是否应该切换策略
            self._check_strategy_switch(symbol, d, i)
            
            # 获取当前激活的策略
            active_strategy_type = self.current_strategy[symbol]
            
            # 获取当前价格
            current_price = d.close[0]
            
            # 更新持有天数
            if self.getposition(d).size > 0:
                self.holding_days[symbol] += 1
            
            # 获取当前指标值
            magic_nine = getattr(self, f'magic_nine_{i}')
            atr = getattr(self, f'atr_{i}')
            
            # 检查是否有仓位
            if self.getposition(d).size == 0:
                # 没有仓位，检查买入信号
                if magic_nine.lines.buy_setup[0] >= self.p.magic_count:
                    # 买入信号
                    value = self.broker.get_value()
                    size = int(value * 0.95 / current_price)  # 使用95%资金
                    
                    if size > 0:
                        logger.info(f'{d.datetime.datetime(0).isoformat()} 买入信号! 神奇九转计数: {magic_nine.lines.buy_setup[0]}, '
                                 f'价格: {current_price:.2f}, 数量: {size}, 策略类型: {active_strategy_type.value}')
                        
                        # 下买入订单
                        self.order = self.buy(data=d, size=size)
                        self.position_size[symbol] = size
            
            else:
                # 已有仓位，更新追踪止损
                if self.highest_price[symbol] is None or current_price > self.highest_price[symbol]:
                    self.highest_price[symbol] = current_price
                    
                    # 如果使用高级或智能止损，更新止损价格
                    if active_strategy_type in [StrategyType.ADVANCED_STOP_LOSS, StrategyType.SMART_STOP_LOSS]:
                        self._update_stop_loss(d, i)
                
                # 检查止损条件
                if active_strategy_type in [StrategyType.ADVANCED_STOP_LOSS, StrategyType.SMART_STOP_LOSS]:
                    if self.stop_loss_price[symbol] is not None and current_price <= self.stop_loss_price[symbol]:
                        # 触发止损
                        pos_size = self.getposition(d).size
                        loss_pct = (self.buy_price[symbol] - current_price) / self.buy_price[symbol] * 100.0
                        logger.info(f'{d.datetime.datetime(0).isoformat()} 止损触发! 亏损: {loss_pct:.2f}%, '
                                 f'价格: {current_price:.2f}, 止损价: {self.stop_loss_price[symbol]:.2f}, '
                                 f'数量: {pos_size}, 策略类型: {active_strategy_type.value}')
                        
                        # 下卖出订单
                        self.order = self.sell(data=d, size=pos_size)
                        self.position_size[symbol] = 0
                        continue  # 执行止损后跳过其他卖出信号检查
                
                # 检查卖出信号
                if magic_nine.lines.sell_setup[0] >= self.p.magic_count:
                    # 卖出信号
                    pos_size = self.getposition(d).size
                    logger.info(f'{d.datetime.datetime(0).isoformat()} 卖出信号! 神奇九转计数: {magic_nine.lines.sell_setup[0]}, '
                             f'价格: {current_price:.2f}, 数量: {pos_size}, 策略类型: {active_strategy_type.value}')
                    
                    # 下卖出订单
                    self.order = self.sell(data=d, size=pos_size)
                    self.position_size[symbol] = 0
            
            # 记录策略使用
            self.strategy_usage_count[active_strategy_type] += 1
    
    def _set_initial_stop_loss(self, data):
        """设置初始止损价格"""
        symbol = data._name
        i = [d._name for d in self.datas].index(symbol)
        
        atr_value = getattr(self, f'atr_{i}')[0]
        current_price = self.buy_price[symbol]
        active_strategy_type = self.current_strategy[symbol]
        
        # 计算止损距离
        stop_loss_distance = atr_value * self.p.atr_multiplier
        
        # 确保止损不超过最大止损百分比
        max_loss_distance = current_price * self.p.stop_loss_pct / 100
        stop_loss_distance = min(stop_loss_distance, max_loss_distance)
        
        # 根据不同策略类型调整止损距离
        if active_strategy_type == StrategyType.SMART_STOP_LOSS:
            # 智能止损根据风险规避系数调整
            stop_loss_distance = stop_loss_distance * self.p.risk_aversion
            
            # 如果启用波动性自适应调整
            if self.p.volatility_adjust:
                # 获取历史价格计算波动率
                prices = np.array(data.close.get(size=self.p.market_analyzer.lookback_window))
                volatility = self.p.market_analyzer.calculate_volatility(prices)
                
                # 根据波动率调整止损距离
                vol_ratio = volatility / 0.01  # 与基准波动率比较
                stop_loss_distance = stop_loss_distance * min(max(vol_ratio, 0.8), 1.2)  # 限制调整范围在0.8-1.2之间
        
        # 设置止损价格
        self.stop_loss_price[symbol] = current_price - stop_loss_distance
        self.highest_price[symbol] = current_price
        
        logger.info(f'{data.datetime.datetime(0).isoformat()} 设置初始止损: {self.stop_loss_price[symbol]:.2f} '
                 f'(ATR: {atr_value:.2f}, 距离: {stop_loss_distance:.2f}, 策略: {active_strategy_type.value})')
    
    def _update_stop_loss(self, data, idx):
        """更新止损价格"""
        symbol = data._name
        active_strategy_type = self.current_strategy[symbol]
        current_price = data.close[0]
        
        # 如果止损价格或买入价格未设置，则跳过
        if self.stop_loss_price[symbol] is None or self.buy_price[symbol] is None:
            return
        
        # 计算当前盈利百分比
        profit_pct = (current_price / self.buy_price[symbol] - 1) * 100
        
        # 如果盈利超过最小盈利百分比，更新止损价格
        if profit_pct >= self.p.min_profit_pct and self.p.trailing_stop:
            atr_value = getattr(self, f'atr_{idx}')[0]
            
            # 基础止损距离
            stop_loss_distance = atr_value * self.p.atr_multiplier
            
            if active_strategy_type == StrategyType.SMART_STOP_LOSS:
                # 智能止损根据更复杂的逻辑调整
                
                # 风险规避系数调整
                stop_loss_distance = stop_loss_distance * self.p.risk_aversion
                
                # 时间衰减调整：随着持有时间增加，降低止损距离
                if self.p.time_decay and self.holding_days[symbol] > self.p.time_decay_days:
                    decay_factor = max(0.8, 1.0 - (self.holding_days[symbol] - self.p.time_decay_days) * 0.02)
                    stop_loss_distance = stop_loss_distance * decay_factor
                
                # 市场感知调整：根据市场状态调整止损距离
                if self.p.market_aware:
                    prices = np.array(data.close.get(size=self.p.market_analyzer.lookback_window))
                    market_regime = self.p.market_analyzer.get_market_regime(prices)
                    
                    if market_regime['regime'] == 'volatile':
                        # 高波动市场，收紧止损
                        stop_loss_distance = stop_loss_distance * 0.9
                    elif market_regime['regime'] == 'strong_uptrend':
                        # 强上升趋势，放宽止损
                        stop_loss_distance = stop_loss_distance * 1.1
            
            # 计算新的止损价格
            new_stop_loss = self.highest_price[symbol] - stop_loss_distance
            
            # 只有当新止损价格高于原止损价格时才更新
            if new_stop_loss > self.stop_loss_price[symbol]:
                old_stop_loss = self.stop_loss_price[symbol]
                self.stop_loss_price[symbol] = new_stop_loss
                logger.info(f'{data.datetime.datetime(0).isoformat()} 更新追踪止损: {old_stop_loss:.2f} -> {new_stop_loss:.2f} '
                         f'(最高价: {self.highest_price[symbol]:.2f}, 盈利: {profit_pct:.2f}%, 策略: {active_strategy_type.value})')
    
    def _check_strategy_switch(self, symbol, data, idx):
        """检查是否应该切换策略"""
        current_date = self.datetime.date()
        
        # 检查是否满足切换延迟
        last_switch_time = self.strategy_switch_time[symbol]
        days_since_last_switch = (datetime.now() - last_switch_time).days
        
        if days_since_last_switch < self.p.switch_delay:
            return
        
        # 获取历史收盘价
        prices = np.array(data.close.get(size=self.p.market_analyzer.lookback_window*2))
        
        if len(prices) < self.p.market_analyzer.lookback_window:
            return  # 数据不足，不切换
        
        # 获取当前激活的策略
        current_strategy_type = self.current_strategy[symbol]
        
        # 使用策略选择器确定最佳策略
        new_strategy_type, params = self.p.strategy_selector.select_strategy(symbol, prices)
        
        # 如果策略需要切换
        if new_strategy_type != current_strategy_type:
            # 获取市场状态作为切换原因
            market_regime = self.p.market_analyzer.get_market_regime(prices)
            regime_type = market_regime.get('regime', 'unknown')
            
            # 记录策略切换
            switch_info = {
                'date': current_date,
                'from': current_strategy_type,
                'to': new_strategy_type,
                'reason': f"市场状态: {regime_type}, 波动率: {market_regime.get('volatility', 0):.4f}, 趋势强度: {market_regime.get('trend_strength', 0):.4f}"
            }
            self.strategy_switches.append(switch_info)
            
            # 更新当前策略和切换时间
            self.current_strategy[symbol] = new_strategy_type
            self.strategy_switch_time[symbol] = datetime.now()
            
            # 记录日志
            logger.info(f"{current_date} - {symbol}: 策略切换从 {current_strategy_type.value} 到 {new_strategy_type.value}，原因: {switch_info['reason']}")
            
            # 更新策略参数（如果需要）
            if params:
                if new_strategy_type == StrategyType.SMART_STOP_LOSS and 'risk_aversion' in params:
                    self.p.risk_aversion = params['risk_aversion']
                    logger.info(f"更新 {symbol} 的智能止损风险规避系数为 {params['risk_aversion']}")
                    
                elif new_strategy_type == StrategyType.ADVANCED_STOP_LOSS and 'atr_multiplier' in params:
                    self.p.atr_multiplier = params['atr_multiplier']
                    logger.info(f"更新 {symbol} 的高级止损ATR乘数为 {params['atr_multiplier']}") 