import os
import time

import backtrader
import pandas as pd
from tigeropen.common.consts import Language, BarPeriod, QuoteRight, Currency, SecurityType
from tigeropen.common.exceptions import ApiException
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.push.pb.AssetData_pb2 import AssetData
from tigeropen.push.pb.PositionData_pb2 import PositionData
from tigeropen.push.pb.QuoteBasicData_pb2 import QuoteBasicData
from tigeropen.push.push_client import PushClient
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.trade.domain.position import Position
from tigeropen.trade.trade_client import TradeClient

from src.infrastructure import Logger
from src.interface.tiger.tiger_broker import TigerBroker
from src.interface.tiger.tiger_real_time_data import TigerRealtimeData
from src.interface.tiger.tiger_utils import backtrader_order_to_tiger_order, tiger_order_to_backtrader_order


class TigerStore(backtrader.Store):
    # 根据backtrader约定，参数必须是元组的元组
    params = (
        ('account_type', 'PAPER'),  # 账户类型，默认使用模拟账户
    )

    def __init__(self, symbols=None):
        """初始化Tiger存储
        
        Args:
            symbols: 订阅的股票代码列表
        """
        self.symbols = symbols if symbols else []
        self.logger = Logger()
        self.logger.setup_basic_logging()
        self.logger.info("TigerStore initialized")
        config_path, private_key_path = self._get_config_paths()
        # 初始化Tiger API客户端
        self.client_config = TigerOpenClientConfig(sandbox_debug=False, props_path=config_path)
        self.client_config.private_key = read_private_key(private_key_path)
        self.client_config.language = Language.zh_CN
        self.client_config.timeout = 60

        self.quote_client = QuoteClient(self.client_config)
        self.quote_client.grab_quote_permission()

        self.trade_client = TradeClient(self.client_config)

        protocol, host, port = self.client_config.socket_host_port
        self.push_client = PushClient(host, port, use_ssl=(protocol == 'ssl'))

        self.push_client.quote_changed = self._on_quote_changed
        self.push_client.error_callback = self._on_error_callback
        self.push_client.disconnect_callback = self._on_disconnect_callback
        self.push_client.asset_changed = self._on_asset_changed
        self.push_client.position_changed = self._on_position_changed
        self.push_client.order_changed = self._on_order_changed
        self.push_client.connect(self.client_config.tiger_id, self.client_config.private_key)

        self.push_client.subscribe_quote(self.symbols)

        # 初始化缓存结构
        self.contract_cache = {}
        self.quote_cache = {}
        self.asset_cache = {}
        self.order_cache = {}
        self.position_cache = []
        self.account = None  # 当前活跃账户ID
        self.cash_value = 0
        self.account_value = 0
        # 初始化时主动获取数据填充缓存
        self._init_data_cache()

    def _on_quote_changed(self, quote: QuoteBasicData):
        if quote.symbol not in self.symbols:
            return
        symbol = quote.symbol
        self.quote_cache[symbol] = quote
        self.logger.info(f"Received quote update: {quote}")

    def _on_asset_changed(self, asset: AssetData):
        if asset.account != self.account:
            return
        self.asset_cache = asset
        self.cash_value = asset.cashBalance
        self.account_value = asset.netLiquidation
        self.logger.info(f"Received asset update: {asset}")

    def _on_order_changed(self, order):
        """
        处理订单状态变化的回调
        
        Args:
            order: Tiger API的订单对象
        """
        # 获取订单ID
        order_id = getattr(order, 'id', None) or getattr(order, 'order_id', 'unknown')

        # 获取订单状态
        status = getattr(order, 'status', 'Unknown')

        # 记录详细日志
        self.logger.info(f"订单状态更新回调 - ID: {order_id}, 状态: {status}")

        # 保存订单到缓存
        self.order_cache[order_id] = order

        # 将Tiger订单转换为可用于Backtrader的格式
        bt_order_info = tiger_order_to_backtrader_order(order)

        # 如果需要进一步处理，可以在这里添加额外的逻辑
        if status == 'FILLED':
            self.logger.info(f"订单已完全成交 - ID: {order_id}，成交均价: {bt_order_info['avg_fill_price']}")
        elif status == 'PARTIALLY_FILLED':
            self.logger.info(
                f"订单部分成交 - ID: {order_id}，已成交: {bt_order_info['filled']}, 剩余: {bt_order_info['remaining']}")
        elif status == 'CANCELLED':
            self.logger.info(f"订单已取消 - ID: {order_id}")
        elif status == 'REJECTED':
            self.logger.warning(f"订单被拒绝 - ID: {order_id}, 原因: {bt_order_info['reason']}")

        # 注意：这里不直接向strategy通知，而是通过TigerBroker的next()方法统一处理
        # broker会每个bar周期从order_cache中获取最新状态并更新backtrader订单

    def _on_position_changed(self, position: PositionData):
        if position.account != self.account:
            return
        if position.symbol not in self.symbols:
            return
        '''
        account: "708815"
        symbol: "MIU.HK"
        expiry: "20250429"
        strike: "43.00"
        right: "CALL"
        identifier: "MIU.HK250429C00043000"
        multiplier: 1000
        market: "HK"
        currency: "HKD"
        segType: "S"
        secType: "OPT"
        position: 3
        averageCost: 3.4629
        latestPrice: 2.325
        marketValue: 6975
        unrealizedPnl: -3413.7
        timestamp: 1744642266874
        positionQty: 3
        salableQty: 3
        '''
        self.position_cache = position
        self.logger.info(f"Received position update: {position}")

    def _on_error_callback(self, frame):
        self.logger.error(f"Received error: {frame}")

    def _on_disconnect_callback(self):
        self.logger.info("Disconnected from server")

        # 尝试重新连接
        max_retries = 5
        retry_interval = 5  # 秒

        for attempt in range(max_retries):
            self.logger.info(f"尝试重新连接 (第{attempt + 1}次)")
            protocol, host, port = self.client_config.socket_host_port
            self.push_client = PushClient(host, port, use_ssl=(protocol == 'ssl'))

            self.push_client.quote_changed = self._on_quote_changed
            self.push_client.error_callback = self._on_error_callback
            self.push_client.disconnect_callback = self._on_disconnect_callback
            self.push_client.asset_changed = self._on_asset_changed
            self.push_client.position_changed = self._on_position_changed
            self.push_client.order_changed = self._on_order_changed

            self.push_client.connect(self.client_config.tiger_id, self.client_config.private_key)
            self.push_client.subscribe_quote(self.symbols)

            self.logger.info("重新连接成功")
            return

        self.logger.error(f"重新连接失败，已超过最大尝试次数: {max_retries}")

    def getdata(self, *args, **kwargs):
        """获取数据源
        
        Returns:
            TigerRealtimeData: 实时数据源
        """
        kwargs['store'] = self
        return TigerRealtimeData(**kwargs)

    def getbroker(self, *args, **kwargs):
        """获取交易接口
        
        Returns:
            TigerBroker: 交易接口
        """
        kwargs['store'] = self
        return TigerBroker(**kwargs)

    def _get_config_paths(self) -> tuple[str, str]:
        # 获取项目根目录的绝对路径
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        config_path = os.path.join(base_dir, "configs", "tiger", "tiger_openapi_config.properties")
        private_key_path = os.path.join(base_dir, "configs", "tiger", "private_key.pem")
        return config_path, private_key_path

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
            bars['cn_date'] = pd.to_datetime(bars['time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert(
                'Asia/Shanghai')
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

    def get_contract(self, symbol, currency=Currency.USD, sec_type=SecurityType.STK):
        """获取合约信息"""
        cache_key = f"{symbol}_{currency}_{sec_type}"
        # 检查缓存
        if cache_key in self.contract_cache:
            return self.contract_cache[cache_key]
        # 获取合约
        contracts = self.trade_client.get_contracts(
            symbol=symbol,
            currency=currency,
            sec_type=sec_type
        )
        self.contract_cache[cache_key] = contracts[0]
        return contracts[0]

    def get_stock_briefs(self, symbols):
        return self.quote_client.get_stock_briefs(symbols)

    def get_market_status(self, market):
        return self.quote_client.get_market_status(market)

    def subscribe_quote(self, symbols):
        """订阅行情"""
        self.push_client.subscribe_quote(symbols=symbols)

    def get_managed_accounts(self):
        '''获取账户信息'''
        '''
        [AccountProfile({'account': '708815', 'capability': 'RegTMargin', 'status': 'Funded', 'account_type': 'STANDARD'}), AccountProfile({'account': 'U10015521', 'capability': 'CASH', 'status': 'Funded', 'account_type': 'GLOBAL'}), AccountProfile({'account': '21722764233480907', 'capability': 'RegTMargin', 'status': 'Funded', 'account_type': 'PAPER'})]
        '''
        return self.trade_client.get_managed_accounts()

    def get_account(self, account_type):
        """根据账户类型查找账户ID"""
        # todo 首先从缓存获取,没有则从API获取
        # 获取账户信息
        accounts = self.trade_client.get_managed_accounts()

        # 遍历账户列表，查找指定类型
        for acc in accounts:
            if hasattr(acc, 'account_type') and acc.account_type == account_type:
                acc_account = acc.account
                self.account = acc_account
                return acc_account

        # 如果没找到指定类型，返回第一个账户
        if accounts and len(accounts) > 0:
            self.logger.error(f"未找到{account_type}类型账户")
            # todo 抛出异常
            return self.account
        return None

    def get_asset(self):
        """获取综合账户"""
        assets = self.trade_client.get_assets(account=self.get_account(self.p.account_type))
        summary = assets[0].summary
        self.asset_cache = summary
        return summary

    def submit_order(self, order):
        """
        提交订单到Tiger API
        
        Args:
            order: backtrader.Order对象
            
        Returns:
            str: 订单ID
        """
        self.logger.info(f"提交订单 - Ref: {order.ref}")

        # 将backtrader订单转换为Tiger API接受的格式
        tiger_order = backtrader_order_to_tiger_order(order)

        # 提交订单到Tiger API
        result = self.trade_client.place_order(tiger_order)

        # 获取订单ID
        order_id = getattr(result, 'id', None) or getattr(result, 'order_id', None)

        if order_id:
            self.logger.info(f"订单提交成功 - Tiger订单ID: {order_id}, BT订单Ref: {order.ref}")

            # 记录订单映射关系 - 便于后续查询
            if not hasattr(self, 'bt_order_map'):
                self.bt_order_map = {}
            self.bt_order_map[order.ref] = order_id

            # 保存到订单缓存 - 初始状态为未确认
            # 实际状态会通过推送更新
            return order_id
        else:
            self.logger.error(f"订单提交失败 - 未获取到订单ID")
            return None

    def cancel_order(self, order_id):
        """
        取消订单
        
        Args:
            order_id: Tiger订单ID
            
        Returns:
            bool: 是否成功发送取消请求
        """
        self.logger.info(f"发送订单取消请求 - ID: {order_id}")
        # 发送取消请求到Tiger API
        result = self.trade_client.cancel_order(order_id=order_id)

        # 订单状态更新将通过推送服务的回调处理
        self.logger.info(f"订单取消请求已发送 - ID: {order_id}")
        return True

    def get_order_status(self, order_id):
        """获取订单状态"""
        if order_id in self.order_cache:
            # 如果有缓存，返回缓存的状态
            return getattr(self.order_cache[order_id], 'status', 'Unknown')
        # 从服务器获取最新状态
        order = self.trade_client.get_order(id=order_id)
        if order:
            self.order_cache[order_id] = order
            return order.status
        return 'Not Found'

    def get_positions(self):
        """获取持仓"""
        if self.position_cache:
            # 如果有缓存，直接返回
            return self.position_cache
        # 从服务器获取最新持仓
        positions: [Position] = self.trade_client.get_positions(self.account)
        self.position_cache = positions
        self.logger.info(f"已获取持仓信息: {len(positions)}个持仓")
        return positions

    def getcash(self):
        """获取账户现金"""
        # 使用缓存的现金值
        return self.cash_value

    def getvalue(self):
        """获取账户价值"""
        # 使用缓存的账户价值
        return self.account_value

    def _init_data_cache(self):
        """初始化数据缓存，从Tiger API获取数据"""
        self.logger.info("开始初始化数据缓存...")
        # 1. 获取资产信息
        asset = self.get_asset()
        self.cash_value = asset.cash
        self.account_value = asset.net_liquidation
        self.logger.info(f"账户 {self.client_config.account} 现金: {self.cash_value}, 总资产: {self.account_value}")

        # 2. 获取订单信息
        orders = self.trade_client.get_orders(account=self.account, limit=10)
        if orders is not None and len(orders) > 0:
            # 打印订单信息结构
            self.logger.info(f"订单信息数据结构: {dir(orders[0])}")
            for order in orders:
                order_id = order.id
                self.order_cache[order_id] = order
            self.logger.info(f"已获取订单信息: {len(orders)}个订单")
        else:
            self.logger.info("未获取到订单信息")
        # 4. 获取持仓信息
        self.get_positions()

        # 5. 预先获取合约信息
        for symbol in self.symbols:
            contract = self.get_contract(symbol)
            if contract is not None:
                # 打印合约信息结构
                self.logger.info(f"合约信息数据结构: {dir(contract)}")
                self.logger.info(f"已获取合约信息: {symbol}")
            else:
                self.logger.info(f"未获取到合约信息: {symbol}")

        self.logger.info("数据缓存初始化完成")
