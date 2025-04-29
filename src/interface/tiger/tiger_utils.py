import backtrader.order
from backtrader import Order
from tigeropen.common.util.order_utils import limit_order, market_order, stop_order, stop_limit_order
from tigeropen.trade.domain.order import OrderStatus
import logging
import math

# 统一订单状态映射：将老虎证券的状态字符串直接映射到backtrader的Order状态
STATUS_MAP = {
    'PENDING_NEW': Order.Submitted,  # 待处理 -> 已提交
    'NEW': Order.Accepted,           # 初始状态 -> 已接受
    'HELD': Order.Submitted,         # 已提交 -> 已提交
    'PARTIALLY_FILLED': Order.Partial,    # 部分成交 -> 部分成交
    'FILLED': Order.Completed,       # 完全成交 -> 已完成
    'PENDING_CANCEL': Order.Canceled,  # 待取消 -> 已取消
    'CANCELLED': Order.Canceled,     # 已取消 -> 已取消
    'REJECTED': Order.Rejected,      # 已拒绝 -> 已拒绝
    'EXPIRED': Order.Expired         # 已过期 -> 已过期
}

# 快速状态映射：将状态字符串直接映射到枚举值
STATUS_STRING_TO_ENUM = {
    'FILLED': OrderStatus.FILLED.value,
    'CANCELLED': OrderStatus.CANCELLED.value,
    'REJECTED': OrderStatus.REJECTED.value,
    'EXPIRED': OrderStatus.EXPIRED.value,
    'PENDING_NEW': OrderStatus.PENDING_NEW.value,
    'NEW': OrderStatus.NEW.value,
    'HELD': OrderStatus.HELD.value,
    'PARTIALLY_FILLED': OrderStatus.PARTIALLY_FILLED.value,
    'PENDING_CANCEL': OrderStatus.PENDING_CANCEL.value
}

# 各证券的最小价格变动单位
PRICE_TICK_SIZE = {
    'default': 0.01,  # 默认为0.01
    'QQQ': 0.01,
    'SPY': 0.01,
    'AAPL': 0.01,
    'TSLA': 0.01,
    'GOOGL': 0.01,
    'META': 0.01,
    'NVDA': 0.01,
    'AMZN': 0.01,
    'MSFT': 0.01
}

def adjust_price_to_tick_size(price, symbol):
    """
    调整价格以符合证券的最小价格变动单位
    
    Args:
        price: 原始价格
        symbol: 证券代码
        
    Returns:
        调整后的价格
    """
    tick_size = PRICE_TICK_SIZE.get(symbol, PRICE_TICK_SIZE['default'])
    # 对价格四舍五入到最近的tick_size的倍数
    return round(price / tick_size) * tick_size

def convert_tiger_status_to_bt(status):
    """
    将Tiger订单状态转换为backtrader订单状态
    
    Args:
        status: 字符串形式的Tiger订单状态
        
    Returns:
        backtrader.Order状态枚举值
    """
    return STATUS_MAP.get(status, Order.Accepted)

def is_order_complete(status):
    """
    判断订单是否完成（完全成交或已取消）
    
    Args:
        status: 字符串形式的Tiger订单状态
        
    Returns:
        bool: 订单是否完成
    """
    return status in ['FILLED', 'CANCELLED', 'REJECTED', 'EXPIRED']

def is_order_active(status):
    """
    判断订单是否活跃（未成交或部分成交）
    
    Args:
        status: 字符串形式的Tiger订单状态
        
    Returns:
        bool: 订单是否活跃
    """
    return status in ['PENDING_NEW', 'NEW', 'HELD', 'PARTIALLY_FILLED']

def process_tiger_order(tiger_order, bt_order=None):
    """
    处理Tiger订单，提取关键信息并更新backtrader订单
    
    Args:
        tiger_order: Tiger API的订单对象
        bt_order: 可选的backtrader订单对象，如果提供则更新其状态
        
    Returns:
        dict: 包含订单处理结果的字典
    """
    # 获取订单状态和基本信息
    status = tiger_order.status if hasattr(tiger_order, 'status') else None
    logging.debug(f"处理Tiger订单 - ID: {tiger_order.id}, 状态: {status}")
    
    order_info = {
        'id': tiger_order.id,
        'status': status,
        'symbol': tiger_order.symbol if hasattr(tiger_order, 'symbol') else None
    }
    
    # 添加订单数量和价格信息
    if hasattr(tiger_order, 'totalQuantity'):
        order_info['quantity'] = tiger_order.totalQuantity
    
    if hasattr(tiger_order, 'limitPrice'):
        order_info['limit_price'] = tiger_order.limitPrice
    
    # 添加成交信息
    filled = getattr(tiger_order, 'filledQuantity', 0)
    avg_fill_price = getattr(tiger_order, 'avgFillPrice', 0)
    order_info['filled'] = filled
    order_info['avg_fill_price'] = avg_fill_price
    
    # 添加手续费信息
    commission = getattr(tiger_order, 'commissionAndFee', 0)
    order_info['commission'] = commission
    
    # 转换订单状态
    bt_status = convert_tiger_status_to_bt(status)
    order_info['bt_status'] = bt_status
    
    # 如果提供了backtrader订单，则更新其状态
    if bt_order is not None:
        # 更新状态
        bt_order.status = bt_status
        
        # 优化订单状态判断逻辑
        is_filled = False
        
        # 1. 检查状态字符串
        if status == 'FILLED':
            is_filled = True
        # 2. 检查枚举值（tiger API可能返回枚举而非字符串）
        elif hasattr(tiger_order, 'status') and tiger_order.status == OrderStatus.FILLED.value:
            is_filled = True
        # 3. 通过状态字符串映射来检查 - 安全检查status不为None且在字典中
        elif status is not None and status in STATUS_STRING_TO_ENUM and STATUS_STRING_TO_ENUM[status] == OrderStatus.FILLED.value:
            is_filled = True
            
        logging.debug(f"订单状态判断 - 原始状态: {status}, 是否成交: {is_filled}")
        
        # 处理成交信息
        if is_filled:
            # 对于完全成交的订单，使用实际成交数量和价格
            filled_qty = getattr(tiger_order, 'filledQuantity', getattr(tiger_order, 'totalQuantity', 0))
            avg_price = getattr(tiger_order, 'avgFillPrice', getattr(tiger_order, 'limitPrice', 0))
            
            order_info['execution'] = {
                'size': filled_qty,
                'price': avg_price,
                'commission': commission
            }
            
            logging.info(f"订单已成交 - ID: {tiger_order.id}, 成交数量: {filled_qty}, 成交价格: {avg_price}")
    
    return order_info


def backtrader_order_to_tiger_order(order: backtrader.order.Order):
    """
    将backtrader订单转换为tiger订单
    
    Args:
        order: backtrader.Order对象
        
    Returns:
        tiger order对象
    """
    # 获取订单数据
    data = order.data
    symbol = data._name
    
    # 如果标的为空，则尝试从策略参数获取
    if not symbol:
        symbol = order.owner.p.symbol
    
    # 获取买卖方向
    action = order.info.get('action', 'BUY' if order.isbuy() else 'SELL')
    
    # 获取store和合约信息
    store = order.owner.broker.store
    contract = store.get_contract(symbol)
    
    # 获取账户ID
    account = store.account or store.get_account(store.p.account_type)
    
    # 订单数量
    quantity = abs(order.size)
    
    # 调整价格以符合最小价格变动单位
    adjusted_price = adjust_price_to_tick_size(order.price, symbol) if order.price else 0
    
    # 根据订单类型创建不同的订单
    tiger_order = None
    
    # 市价单
    if order.exectype == order.Market:
        tiger_order = market_order(
            account=account,
            contract=contract,
            action=action,
            quantity=quantity
        )
    # 限价单
    elif order.exectype == order.Limit:
        tiger_order = limit_order(
            account=account,
            contract=contract,
            action=action,
            quantity=quantity,
            limit_price=adjusted_price
        )
    # 止损单
    elif order.exectype == order.Stop:
        tiger_order = stop_order(
            account=account,
            contract=contract,
            action=action,
            quantity=quantity,
            aux_price=adjusted_price
        )
    # 止损限价单
    elif order.exectype == order.StopLimit:
        adjusted_limit_price = adjust_price_to_tick_size(order.pricelimit, symbol)
        tiger_order = stop_limit_order(
            account=account,
            contract=contract,
            action=action,
            quantity=quantity,
            limit_price=adjusted_limit_price,
            aux_price=adjusted_price
        )
    # 默认使用限价单
    else:
        tiger_order = limit_order(
            account=account,
            contract=contract,
            action=action,
            quantity=quantity,
            limit_price=adjusted_price or 0
        )
    
    # 设置有效期
    if order.valid:
        # 设置为当日有效
        tiger_order.time_in_force = 'DAY'
    
    # 允许盘前盘后交易
    tiger_order.outside_rth = True
    
    return tiger_order