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
    
    # 获取合约信息
    contract = data.contract if hasattr(data, 'contract') else None
    # 如果数据对象没有合约信息，需要从store中获取
    if contract is None and hasattr(order.owner, '_broker') and hasattr(order.owner._broker, 'store'):
        # 获取store对象
        store = order.owner._broker.store
        if hasattr(store, 'get_contract'):
            contract = store.get_contract(symbol)
            logger.info(f"从store获取合约信息: {contract}")
    
    # 获取账户ID
    account = None
    store = None
    if hasattr(order.owner, '_broker') and hasattr(order.owner._broker, 'store'):
        store = order.owner._broker.store
        if hasattr(store, 'account'):
            account = store.account
    
    # 如果没有账户ID，尝试从store.p.account_type获取
    if account is None and store is not None and hasattr(store, 'get_account'):
        account = store.get_account(store.p.account_type)
    
    if not account:
        logger.warning("未找到账户ID，将使用默认账户")
        
    if not contract:
        logger.warning(f"未找到合约信息: {symbol}，可能导致订单提交失败")
    
    # 创建Tiger订单
    quantity = abs(order.size)  # 数量为正数
    
    logger.info(f"创建Tiger订单 - 账户: {account}, 标的: {symbol}, 动作: {action}, 数量: {quantity}")
    
    # 根据订单类型创建不同的订单
    tiger_order = None
    try:
        if order.exectype == order.Market:
            # 市价单
            logger.info("创建市价单")
            tiger_order = market_order(
                account=account,
                contract=contract,
                action=action,
                quantity=quantity
            )
        elif order.exectype == order.Limit:
            # 限价单
            logger.info(f"创建限价单，价格: {order.price}")
            tiger_order = limit_order(
                account=account,
                contract=contract,
                action=action,
                quantity=quantity,
                limit_price=order.price
            )
        elif order.exectype == order.Stop:
            # 止损单
            logger.info(f"创建止损单，价格: {order.price}")
            tiger_order = stop_order(
                account=account,
                contract=contract,
                action=action,
                quantity=quantity,
                aux_price=order.price
            )
        elif order.exectype == order.StopLimit:
            # 止损限价单
            logger.info(f"创建止损限价单，止损价: {order.price}，限价: {order.pricelimit}")
            tiger_order = stop_limit_order(
                account=account,
                contract=contract,
                action=action,
                quantity=quantity,
                limit_price=order.pricelimit,
                aux_price=order.price
            )
        else:
            # 默认使用限价单
            logger.info(f"创建默认限价单，价格: {order.price if order.price else '市价'}")
            tiger_order = limit_order(
                account=account,
                contract=contract,
                action=action,
                quantity=quantity,
                limit_price=order.price if order.price else 0
            )
        
        # 设置有效期
        if order.valid:
            # 如果有设置有效期，转换为Tiger API格式
            if hasattr(tiger_order, 'time_in_force'):
                # 设置为当日有效或GTC (Good Till Cancelled)
                tiger_order.time_in_force = 'DAY'  # 当日有效
                logger.info("设置订单有效期: 当日有效")
        
        # 保存backtrader订单引用ID，便于后续关联
        if hasattr(tiger_order, 'outside_rth'):
            tiger_order.outside_rth = True  # 允许盘前盘后交易
            
        # 添加自定义属性，保存backtrader订单引用
        # 使用本地变量存储，不直接修改tiger_order对象
        bt_ref = order.ref
        
        logger.info(f"Tiger订单创建成功: {tiger_order}, BT订单引用: {bt_ref}")
        return tiger_order
        
    except Exception as e:
        logger.error(f"创建Tiger订单失败: {e}")
        raise

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
    order_id = getattr(tiger_order, 'id', None) or getattr(tiger_order, 'order_id', None)
    
    # 获取订单状态
    status = getattr(tiger_order, 'status', 'Unknown')
    
    # 获取成交信息
    filled = getattr(tiger_order, 'filled', 0)
    remaining = getattr(tiger_order, 'remaining', 0)
    
    # 获取成交均价
    avg_fill_price = getattr(tiger_order, 'avg_fill_price', 0)
    
    # 获取佣金
    commission = getattr(tiger_order, 'commission', 0)
    
    # 获取拒绝原因(如果有)
    reason = getattr(tiger_order, 'reason', None)
    
    # 获取合约信息
    contract = getattr(tiger_order, 'contract', None)
    symbol = None
    if contract:
        symbol = getattr(contract, 'symbol', None)
    
    # 获取backtrader订单引用(如果有)
    bt_ref = getattr(tiger_order, 'bt_ref', None)
    
    logger.info(f"解析Tiger订单 - ID: {order_id}, 状态: {status}, 已成交: {filled}, 均价: {avg_fill_price}")
    
    # 构建订单信息字典
    order_info = {
        'id': order_id,
        'status': status,
        'filled': filled,
        'remaining': remaining,
        'avg_fill_price': avg_fill_price,
        'commission': commission,
        'reason': reason,
        'symbol': symbol,
        'bt_ref': bt_ref,
        # 添加更多可能需要的信息
        'creation_time': getattr(tiger_order, 'create_time', None),
        'update_time': getattr(tiger_order, 'update_time', None),
        'order_type': getattr(tiger_order, 'order_type', None),
        'time_in_force': getattr(tiger_order, 'time_in_force', None),
        'account': getattr(tiger_order, 'account', None),
    }
    
    return order_info