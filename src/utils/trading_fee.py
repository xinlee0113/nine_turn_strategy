"""
交易费用计算工具类，支持不同券商的费用计算模型
包括老虎证券(Tiger)和盈透证券(Interactive Brokers)的费用计算
"""

class TradingFeeUtil:
    """交易费用计算工具类"""
    
    @staticmethod
    def calculate_tiger_fee(price, quantity, is_buy=True):
        """
        计算老虎证券的交易费用
        
        参数:
        price (float): 股票价格
        quantity (int): 交易数量
        is_buy (bool): 是否为买入操作，默认为True
        
        返回:
        float: 总交易费用
        """
        trade_value = price * quantity
        
        # 老虎证券佣金费用
        commission = max(0.0039 * quantity, 0.99)
        commission = min(commission, trade_value * 0.005)  # 最高为交易额的0.5%
        
        # 老虎证券平台费
        platform_fee = max(0.004 * quantity, 1.0)
        platform_fee = min(platform_fee, trade_value * 0.005)  # 最高为交易额的0.5%
        
        # 第三方费用
        third_party_fees = 0.003 * quantity  # 结算费
        
        # 只针对卖单的费用
        if not is_buy:
            sec_fee = max(0.0000278 * trade_value, 0.01)  # SEC费用
            finra_fee = min(max(0.000166 * quantity, 0.01), 8.3)  # FINRA交易活动费
            third_party_fees += sec_fee + finra_fee
        
        total_fee = commission + platform_fee + third_party_fees
        return total_fee
    
    @staticmethod
    def calculate_ib_fee(price, quantity, monthly_volume=0, is_buy=True):
        """
        计算盈透证券(Interactive Brokers)的交易费用
        
        参数:
        price (float): 股票价格
        quantity (int): 交易数量
        monthly_volume (int): 当月累计交易量，用于分层费率，默认为0
        is_buy (bool): 是否为买入操作，默认为True
        
        返回:
        float: 总交易费用
        """
        trade_value = price * quantity
        
        # 根据月交易量确定分层费率
        if monthly_volume <= 300000:
            commission_rate = 0.0035
        elif monthly_volume <= 3000000:
            commission_rate = 0.0020
        elif monthly_volume <= 20000000:
            commission_rate = 0.0015
        elif monthly_volume <= 100000000:
            commission_rate = 0.0010
        else:
            commission_rate = 0.0005
        
        # 计算佣金
        commission = commission_rate * quantity
        commission = max(commission, 0.35)  # 最低每笔订单0.35美元
        commission = min(commission, trade_value * 0.01)  # 最高为交易额的1%
        
        # 第三方费用
        third_party_fees = 0.0002 * quantity  # NSCC, DTC结算费
        
        # 只针对卖单的费用
        if not is_buy:
            sec_fee = max(0.0000218 * trade_value, 0.01)  # SEC费用(费率略低于老虎)
            finra_fee = min(max(0.000119 * quantity, 0.01), 5.95)  # FINRA交易活动费(费率略低于老虎)
            third_party_fees += sec_fee + finra_fee
        
        total_fee = commission + third_party_fees
        return total_fee
    
    @staticmethod
    def get_fee_calculator(broker_type="tiger"):
        """
        获取特定券商的费用计算函数
        
        参数:
        broker_type (str): 券商类型，"tiger"或"ib"
        
        返回:
        function: 对应券商的费用计算函数
        """
        if broker_type.lower() == "ib":
            return TradingFeeUtil.calculate_ib_fee
        else:
            return TradingFeeUtil.calculate_tiger_fee 