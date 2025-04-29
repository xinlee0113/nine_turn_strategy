import collections
from datetime import datetime, timezone
import time
import logging

import backtrader
from backtrader import Order

# 订单状态映射
ORDER_STATUS_MAP = {
    'NEW': Order.Accepted,
    'PARTIALLY_FILLED': Order.Partial,
    'FILLED': Order.Completed,
    'PENDING_CANCEL': Order.Cancelled,
    'CANCELLED': Order.Cancelled,
    'REJECTED': Order.Rejected,
    'EXPIRED': Order.Expired
}


class TigerBroker(backtrader.BrokerBase):
    '''
    老虎证券实盘交易Broker
    '''

    params = (
        ('store', None),  # 存储引用
    )

    def __init__(self):
        super().__init__()
        
        # 初始化日志
        self.logger = logging.getLogger(__name__)
        
        # 保存store引用
        self.store = self.p.store

        if self.store is None:
            raise ValueError("必须提供store参数")

        # 初始化交易客户端
        self.trade_client = self.store.trade_client

        # 初始化订单字典
        self.orders = collections.OrderedDict()  # 订单管理
        self.notifs = collections.deque()  # 通知队列
        
        # 初始化买卖订单列表
        self.buy_orders = []
        self.sell_orders = []
        
        # 初始化订单ID计数器
        self.orderid = 0

        # 获取资金信息
        self.startingcash = self.cash = self.store.getcash()
        self.startingvalue = self.value = self.store.getvalue()

        # 当前持仓
        self.positions = {}
        self._load_positions()
        
        self.logger.info("TigerBroker初始化完成")

    def _load_positions(self):
        """加载当前持仓"""
        positions = self.store.get_positions()
        for position in positions:
            # 保存持仓信息
            if hasattr(position, 'symbol'):
                self.positions[position.symbol] = position

    def getcash(self):
        """获取现金"""
        # 从store获取最新现金
        self.cash = self.store.getcash()
        return self.cash

    def getvalue(self, datas=None):
        """获取账户价值"""
        # 从store获取最新账户价值
        self.value = self.store.getvalue()
        return self.value

    def getposition(self, data):
        """获取特定数据的持仓"""
        symbol = data._name
        if symbol in self.positions:
            position = self.positions[symbol]
            size = position.quantity if hasattr(position, 'quantity') else 0
            price = position.average_cost if hasattr(position, 'average_cost') else 0
            return backtrader.Position(size, price)
        return backtrader.Position()

    def buy(self, owner, data, size, price=None, plimit=None, exectype=None, valid=None, tradeid=0, **kwargs):
        """买入订单"""
        order = self._create_order(owner, data, size, price, exectype, valid, 'BUY', **kwargs)
        self.orders[order.ref] = order
        return self.submit(order)

    def sell(self, owner, data, size, price=None, plimit=None, exectype=None, valid=None, tradeid=0, **kwargs):
        """卖出订单"""
        order = self._create_order(owner, data, size, price, exectype, valid, 'SELL', **kwargs)
        self.orders[order.ref] = order
        return self.submit(order)

    def _create_order(self, owner, data, size, price, exectype, valid, action, **kwargs):
        """创建订单"""
        # 重写Order类，确保ordtype在初始化前就存在
        # 这种方式可以避免在Order.__init__中调用isbuy()时的属性错误
        class PatchedOrder(Order):
            def __init__(self, *args, **kwargs):
                self.ordtype = Order.Buy if action == 'BUY' else Order.Sell
                super().__init__(*args, **kwargs)
        
        # 使用补丁后的Order类
        order = PatchedOrder(
            owner=owner, data=data, 
            size=size if action == 'BUY' else -size,
            price=price if price is not None else 0.0,
            pricelimit=None, 
            exectype=exectype if exectype is not None else Order.Market,
            valid=valid,
            tradeid=0
        )
        
        # 设置订单编号
        order.ref = self.orderid
        self.orderid += 1
        
        # 记录日志
        if action == 'BUY':
            self.logger.info(f"创建买入订单 - Ref: {order.ref}, 标的: {data._name}, 数量: {size}")
        else:
            self.logger.info(f"创建卖出订单 - Ref: {order.ref}, 标的: {data._name}, 数量: {size}")
        
        # 添加额外信息和佣金
        order.info['action'] = action
        order.addinfo(**kwargs)
        order.addcomminfo(self.getcommissioninfo(data))
        
        # 将订单添加到对应列表
        if action == 'BUY':
            self.buy_orders.append(order)
        else:
            self.sell_orders.append(order)
        
        return order

    def submit(self, order):
        """提交订单"""
        # 标记订单为已提交状态
        order.submit(self)
        self.notify(order)

        # 通过Store提交订单到交易所
        tiger_order_id = self.store.submit_order(order)

        # 保存老虎订单ID到backtrader订单的info对象中
        order.info.tiger_order_id = tiger_order_id
        # 更新订单状态为已接受
        order.accept()
        # 通知订单状态更新
        self.notify(order)
        self.logger.info(f"订单提交成功，订单ID: {tiger_order_id}")

        # 返回订单引用ID，而不是订单对象
        return order.ref

    def cancel(self, order):
        """取消订单"""
        # 获取Tiger订单ID
        tiger_order_id = order.info.tiger_order_id

        # 通过Store发送取消请求
        result = self.store.cancel_order(tiger_order_id)
        
        # 取消成功，将订单状态设置为等待取消确认
        order.status = Order.Cancelled
        self.notify(order)

        return order

    def _process_order_update(self, tiger_order):
        """处理订单状态更新
        
        将tiger API返回的订单状态更新应用到backtrader订单对象
        """
        # 获取Tiger订单ID
        order_id = tiger_order.id
            
        # 在订单字典中查找对应的backtrader订单
        matched_order = None
        for order in self.orders.values():
            if order.info.tiger_order_id == order_id:
                matched_order = order
                break
                
        self.logger.warning(f"未找到对应的Backtrader订单，Tiger订单ID: {order_id}")
            
        # 获取订单状态
        status = tiger_order.status
        self.logger.info(f"订单状态更新: {order_id}, 状态: {status}")
        
        # 映射到backtrader订单状态
        bt_status = ORDER_STATUS_MAP.get(status, matched_order.status)
        
        # 已成交或部分成交时更新成交信息
        if status in ['FILLED', 'PARTIALLY_FILLED']:
            # 获取成交信息
            executed_price = tiger_order.avg_fill_price
            executed_size = tiger_order.filled
            
            # 更新订单成交信息
            self.logger.info(f"订单成交: {order_id}, 价格: {executed_price}, 数量: {executed_size}")
            matched_order.execute(dt=datetime.now(timezone.utc), 
                           size=executed_size, 
                           price=executed_price)
        
        # 更新订单状态
        matched_order.status = bt_status
        
        # 通知状态更新
        self.notify(matched_order)
        
        return matched_order

    def _process_position_update(self, position):
        """处理持仓更新
        
        将Tiger API返回的持仓更新应用到broker的持仓记录
        """
        # 获取持仓标识
        symbol = position.symbol
        
        # 更新持仓信息
        self.positions[symbol] = position
        
        # 记录持仓数量信息
        quantity = position.quantity 
        avg_cost = position.average_cost
        
        self.logger.info(f"持仓更新: {symbol}, 数量: {quantity}, 平均成本: {avg_cost}")
        
        # 通知cerebro进行持仓更新 - 具体实现取决于backtrader架构

    def get_notification(self):
        """获取通知"""
        if not self.notifs:
            return None

        return self.notifs.popleft()

    def notify(self, order):
        """通知订单状态"""
        self.notifs.append(order.clone())

    def next(self):
        """处理每个时间点的操作
        
        在每个bar更新时调用，用于处理订单和持仓更新
        """
        self.logger.debug("处理bar更新")
        
        # 从store获取最新账户信息
        old_cash = self.cash
        old_value = self.value
        
        self.cash = self.store.getcash()
        self.value = self.store.getvalue()
        
        if old_cash != self.cash or old_value != self.value:
            self.logger.info(f"账户更新 - 现金: {self.cash}, 总资产: {self.value}")
        
        # 处理订单状态更新 - 遍历store中缓存的订单
        order_updates = 0
        for order_id, cached_order in self.store.order_cache.items():
            result = self._process_order_update(cached_order)
            if result:
                order_updates += 1
        
        if order_updates > 0:
            self.logger.debug(f"已处理{order_updates}个订单更新")
        
        # 处理持仓更新 - 遍历store中缓存的持仓
        position_updates = 0
        # 直接将position_cache作为列表处理
        for position in self.store.position_cache:
            self._process_position_update(position)
            position_updates += 1
            
        if position_updates > 0:
            self.logger.debug(f"已处理{position_updates}个持仓更新")
