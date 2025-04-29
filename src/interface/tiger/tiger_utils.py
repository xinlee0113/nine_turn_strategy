import backtrader.order
from tigeropen.common.util.order_utils import limit_order, market_order, stop_order, stop_limit_order
from tigeropen.trade.domain.order import OrderStatus
import logging


def backtrader_order_to_tiger_order(order: backtrader.order.Order):
    """
    将backtrader订单转换为tiger订单
    
    Args:
        order: backtrader.Order对象
        
    Returns:
        tiger order对象
    """
    logger = logging.getLogger(__name__)
    
    # 获取订单数据
    data = order.data
    symbol = data._name
    logger.info(f"转换订单 - 标的: {symbol}, 类型: {'买入' if order.isbuy() else '卖出'}, 数量: {abs(order.size)}")
    
    # 获取买卖方向
    action = order.info.get('action', 'BUY' if order.isbuy() else 'SELL')
    
    # 获取store和合约信息
    store = order.owner._broker.store
    contract = store.get_contract(symbol)
    logger.info(f"从store获取合约信息: {contract}")
    
    # 获取账户ID
    account = store.account
    
    # 如果没有直接账户，从账户类型获取
    if not account:
        account = store.get_account(store.p.account_type)
    
    logger.info(f"创建Tiger订单 - 账户: {account}, 标的: {symbol}, 动作: {action}, 数量: {abs(order.size)}")
    
    # 根据订单类型创建不同的订单
    tiger_order = None
    # 市价单
    if order.exectype == order.Market:
        logger.info("创建市价单")
        tiger_order = market_order(
            account=account,
            contract=contract,
            action=action,
            quantity=abs(order.size)
        )
    # 限价单
    elif order.exectype == order.Limit:
        logger.info(f"创建限价单，价格: {order.price}")
        tiger_order = limit_order(
            account=account,
            contract=contract,
            action=action,
            quantity=abs(order.size),
            limit_price=order.price
        )
    # 止损单
    elif order.exectype == order.Stop:
        logger.info(f"创建止损单，价格: {order.price}")
        tiger_order = stop_order(
            account=account,
            contract=contract,
            action=action,
            quantity=abs(order.size),
            aux_price=order.price
        )
    # 止损限价单
    elif order.exectype == order.StopLimit:
        logger.info(f"创建止损限价单，止损价: {order.price}，限价: {order.pricelimit}")
        tiger_order = stop_limit_order(
            account=account,
            contract=contract,
            action=action,
            quantity=abs(order.size),
            limit_price=order.pricelimit,
            aux_price=order.price
        )
    # 默认使用限价单
    else:
        logger.info(f"创建默认限价单，价格: {order.price if order.price else '市价'}")
        tiger_order = limit_order(
            account=account,
            contract=contract,
            action=action,
            quantity=abs(order.size),
            limit_price=order.price if order.price else 0
        )
    
    # 设置有效期
    if order.valid:
        # 设置为当日有效
        tiger_order.time_in_force = 'DAY'
        logger.info("设置订单有效期: 当日有效")
    
    # 允许盘前盘后交易
    tiger_order.outside_rth = True
    
    logger.info(f"Tiger订单创建成功: {tiger_order}, BT订单引用: {order.ref}")
    return tiger_order

def tiger_order_to_backtrader_order(tiger_order):
    """
    将Tiger订单转换为backtrader订单信息，用于状态更新
    
    Args:
        tiger_order: Tiger API的订单对象
        
    Returns:
        dict: 包含订单状态信息的字典
    """
    logger = logging.getLogger(__name__)
    
    # 获取订单ID
    order_id = tiger_order.id
    
    # 获取订单状态
    status = tiger_order.status
    
    # 获取成交信息
    filled = tiger_order.filled
    remaining = tiger_order.remaining
    
    # 获取成交均价
    avg_fill_price = tiger_order.avg_fill_price
    
    # 获取合约信息
    contract = tiger_order.contract
    symbol = contract.symbol
    
    logger.info(f"解析Tiger订单 - ID: {order_id}, 状态: {status}, 已成交: {filled}, 均价: {avg_fill_price}")
    
    # 构建订单信息字典
    order_info = {
        'id': order_id,
        'status': status,
        'filled': filled,
        'remaining': remaining,
        'avg_fill_price': avg_fill_price,
        'commission': tiger_order.commission,
        'reason': tiger_order.reason,
        'symbol': symbol,
        'bt_ref': tiger_order.bt_ref,
        # 添加更多信息
        'creation_time': tiger_order.create_time,
        'update_time': tiger_order.update_time,
        'order_type': tiger_order.order_type,
        'time_in_force': tiger_order.time_in_force,
        'account': tiger_order.account,
    }
    
    return order_info