"""
风险管理器模块
用于评估交易风险并提供风险控制功能
"""
import logging
from typing import Dict, Any, Tuple, Optional


class RiskManager:
    """风险管理器类
    
    负责评估交易风险并决定是否允许交易执行
    """

    def __init__(self, params: Dict[str, Any] = None):
        """初始化风险管理器
        
        Args:
            params: 参数字典，包含风险管理所需参数
        """
        self.params = params or {}
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"风险管理器初始化，参数: {self.params}")

        # 设置默认风险限制参数
        self.max_position_pct = self.params.get('max_position_pct', 0.95)  # 最大仓位比例
        self.max_drawdown = self.params.get('max_drawdown', 0.20)  # 最大回撤限制
        self.max_daily_trades = self.params.get('max_daily_trades', 5)  # 每日最大交易次数

        # 止损和移动止损参数
        self.stop_loss_pct = self.params.get('stop_loss_pct', 0.8)  # 止损百分比
        self.profit_target_pct = self.params.get('profit_target_pct', 2.0)  # 利润目标百分比
        self.trailing_pct = self.params.get('trailing_pct', 1.0)  # 移动止损激活百分比

    def check_risk(self, signal: int, data: Dict[str, Any]) -> Tuple[bool, str]:
        """检查交易风险
        
        Args:
            signal: 交易信号 (1=买入, 0=无信号, -1=卖出)
            data: 包含风险评估所需数据的字典
                cash: 可用资金
                equity: 账户总权益
                current_position: 当前持仓数量
                drawdown: 当前回撤
                daily_trades: 当日交易次数
                其他可能的决策数据...
                
        Returns:
            Tuple[bool, str]: (是否通过风险检查, 原因说明)
        """
        # 如果没有信号，不需要风险检查
        if signal == 0:
            return True, "无交易信号"

        # 获取风险相关数据
        equity = data.get('equity', 0)
        cash = data.get('cash', 0)
        current_position = data.get('current_position', 0)
        drawdown = data.get('drawdown', 0)
        daily_trades = data.get('daily_trades', 0)

        # 检查每日交易次数是否超限
        if daily_trades >= self.max_daily_trades:
            return False, f"超过每日最大交易次数限制 ({self.max_daily_trades})"

        # 检查最大回撤是否超限
        if drawdown > self.max_drawdown:
            return False, f"超过最大回撤限制 ({self.max_drawdown:.2%})"

        # 买入信号的风险检查
        if signal > 0:
            # 检查当前仓位比例是否已经超限
            if equity > 0:
                position_value = (equity - cash)
                position_pct = position_value / equity

                if position_pct >= self.max_position_pct:
                    return False, f"超过最大仓位比例限制 ({self.max_position_pct:.2%})"

        # 通过所有风险检查
        return True, "通过风险检查"

    def check_risk_management(self, data: Dict[str, Any]) -> Tuple[int, Optional[float], Optional[bool]]:
        """检查持仓的风险管理策略，包括止损、获利目标和移动止损
        
        Args:
            data: 包含风险管理所需数据的字典
                current_position: 当前持仓方向 (1=多头, -1=空头, 0=无持仓)
                buy_price: 买入/卖空价格
                current_price: 当前价格
                trailing_activated: 移动止损是否已激活
                stop_loss: 当前止损价格
                time_info: 市场时间信息
                
        Returns:
            Tuple[int, Optional[float], Optional[bool]]: 
                - 风险管理动作 (1=平空头, -1=平多头, 0=无动作)
                - 新的止损价格 (如有更新)
                - 移动止损激活状态 (如有更新)
        """
        # 如果没有持仓，不需要风险管理
        current_position = data.get('current_position', 0)
        if current_position == 0:
            return 0, None, None

        # 获取价格和止损相关数据
        buy_price = data.get('buy_price', 0)
        current_price = data.get('current_price', 0)
        trailing_activated = data.get('trailing_activated', False)
        stop_loss = data.get('stop_loss', None)

        # 返回值初始化
        action = 0  # 0=无动作，-1=平多头，1=平空头
        new_stop_loss = None
        new_trailing_activated = None

        # 多头仓位风险管理
        if current_position > 0:
            # 1. 移动止损处理
            if trailing_activated:
                # 已激活移动止损，更新止损价格
                trail_price = current_price * (1 - self.trailing_pct / 100)
                if stop_loss is None or trail_price > stop_loss:
                    new_stop_loss = trail_price
                    old_stop_str = "0" if stop_loss is None else f"{stop_loss:.2f}"
                    self.logger.info(f"更新多头移动止损: {old_stop_str} -> {trail_price:.2f}")
            else:
                # 检查是否达到移动止损激活条件
                if buy_price > 0:
                    profit_pct = (current_price / buy_price - 1) * 100
                    if profit_pct >= self.trailing_pct:
                        new_trailing_activated = True
                        trail_price = current_price * (1 - self.trailing_pct / 100)
                        if stop_loss is None or trail_price > stop_loss:
                            new_stop_loss = trail_price
                            old_stop_str = "0" if stop_loss is None else f"{stop_loss:.2f}"
                            self.logger.info(f"激活多头移动止损: {old_stop_str} -> {trail_price:.2f}")

            # 2. 止损检查
            if stop_loss is not None and current_price <= stop_loss:
                self.logger.info(f"多头止损触发! 价格: {current_price:.2f}, 止损价: {stop_loss:.2f}")
                action = -1  # 平多头
                return action, None, None

            # 3. 获利目标检查
            if buy_price > 0:
                profit_pct = (current_price / buy_price - 1) * 100
                if profit_pct >= self.profit_target_pct:
                    self.logger.info(
                        f"达到多头利润目标! 价格: {current_price:.2f}, 买入价: {buy_price:.2f}, 利润: {profit_pct:.2f}%")
                    action = -1  # 平多头
                    return action, None, None

        # 空头仓位风险管理
        elif current_position < 0:
            # 1. 止损检查
            if stop_loss is not None and current_price >= stop_loss:
                self.logger.info(f"空头止损触发! 价格: {current_price:.2f}, 止损价: {stop_loss:.2f}")
                action = 1  # 平空头
                return action, None, None

            # 2. 移动止损处理
            if trailing_activated:
                # 已激活移动止损，更新止损价格
                trail_price = current_price * (1 + self.trailing_pct / 100)
                if stop_loss is None or trail_price < stop_loss:
                    new_stop_loss = trail_price
                    old_stop_str = "0" if stop_loss is None else f"{stop_loss:.2f}"
                    self.logger.info(f"更新空头移动止损: {old_stop_str} -> {trail_price:.2f}")
            else:
                # 检查是否达到移动止损激活条件
                if buy_price > 0:
                    profit_pct = (buy_price / current_price - 1) * 100
                    if profit_pct >= self.trailing_pct:
                        new_trailing_activated = True
                        trail_price = current_price * (1 + self.trailing_pct / 100)
                        if stop_loss is None or trail_price < stop_loss:
                            new_stop_loss = trail_price
                            old_stop_str = "0" if stop_loss is None else f"{stop_loss:.2f}"
                            self.logger.info(f"激活空头移动止损: {old_stop_str} -> {trail_price:.2f}")

            # 3. 获利目标检查
            if buy_price > 0:
                profit_pct = (buy_price / current_price - 1) * 100
                if profit_pct >= self.profit_target_pct:
                    self.logger.info(
                        f"达到空头利润目标! 价格: {current_price:.2f}, 卖出价: {buy_price:.2f}, 利润: {profit_pct:.2f}%")
                    action = 1  # 平空头
                    return action, None, None

        return action, new_stop_loss, new_trailing_activated
