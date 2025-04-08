"""
仓位计算器模块
用于根据交易信号计算合适的仓位大小
"""
import logging
from typing import Dict, Any


class PositionSizer:
    """仓位计算器类
    
    根据交易信号和账户状态计算合适的仓位大小
    """

    def __init__(self, params: Dict[str, Any] = None):
        """初始化仓位计算器
        
        Args:
            params: 参数字典，包含仓位计算所需参数
        """
        self.params = params or {}
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"仓位计算器初始化，参数: {self.params}")

    def calculate_position(self, signal: int, data: Dict[str, Any]) -> int:
        """计算仓位大小
        
        Args:
            signal: 交易信号 (1=买入, 0=无信号, -1=卖出)
            data: 包含决策所需数据的字典
                cash: 可用资金
                equity: 账户总权益
                price: 当前价格
                current_position: 当前持仓数量
                其他可能的决策数据...
                
        Returns:
            int: 建议仓位大小（正数表示买入数量，负数表示卖出数量）
        """
        # 如果没有信号，不调整仓位
        if signal == 0:
            return 0

        # 获取当前持仓和资金状况
        current_position = data.get('current_position', 0)
        cash = data.get('cash', 0)
        equity = data.get('equity', 0)
        price = data.get('price', 0)

        # 默认仓位比例（资金的百分比）
        position_pct = self.params.get('position_pct', 1.0)

        # 计算目标仓位
        if signal > 0:  # 买入信号
            # 如果已有多头仓位，不增加
            if current_position > 0:
                return 0

            # 计算可买入数量
            if price <= 0:
                return 0

            # 使用fixed_size参数时，买入固定数量
            if 'fixed_size' in self.params:
                target_position = self.params['fixed_size']
            else:
                # 根据资金比例计算买入数量
                available_cash = cash * position_pct
                target_position = int(available_cash / price)

            self.logger.info(f"计算买入仓位: {target_position} 股")
            return target_position

        elif signal < 0:  # 卖出信号
            # 如果没有多头仓位，不卖出
            if current_position <= 0:
                return 0

            # 计算卖出数量（全部平仓）
            target_position = -current_position

            self.logger.info(f"计算卖出仓位: {-target_position} 股")
            return target_position

        return 0
