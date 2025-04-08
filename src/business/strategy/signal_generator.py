"""
信号生成器模块
用于生成交易信号的组件
"""
import logging
from typing import Dict, Any

import numpy as np


class SignalGenerator:
    """信号生成器类
    
    根据传入的数据和参数生成交易信号：
    1 = 买入信号
    0 = 无信号
    -1 = 卖出信号
    """

    def __init__(self, params: Dict[str, Any]):
        """初始化信号生成器
        
        Args:
            params: 参数字典，包含信号生成所需参数
        """
        self.params = params
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"信号生成器初始化，参数: {params}")

    def generate_signal(self, data: Dict[str, Any]) -> int:
        """生成交易信号
        
        Args:
            data: 包含决策所需数据的字典
                magic_nine_buy: MagicNine买入计数
                magic_nine_sell: MagicNine卖出计数
                rsi: RSI指标值
                ema_fast: 快速EMA
                ema_slow: 慢速EMA
                macd_histo: MACD直方图值
                kdj_k: KDJ指标K值
                kdj_d: KDJ指标D值
                kdj_j: KDJ指标J值
                current_position: 当前持仓 (1=多头, -1=空头, 0=无持仓)
                price: 当前价格
                time_info: 市场时间信息
                
        Returns:
            int: 交易信号 (1=买入, 0=无信号, -1=卖出)
        """
        # 获取神奇九转计数
        magic_nine_buy = data.get('magic_nine_buy', 0)
        magic_nine_sell = data.get('magic_nine_sell', 0)

        # 获取RSI和EMA指标
        rsi = data.get('rsi', 50)
        ema_fast = data.get('ema_fast', 0)
        ema_slow = data.get('ema_slow', 0)

        # 获取MACD和KDJ指标
        macd_histo = data.get('macd_histo', 0)
        kdj_k = data.get('kdj_k', 50)
        kdj_d = data.get('kdj_d', 50)
        kdj_j = data.get('kdj_j', 50)

        # 获取当前持仓状态
        current_position = data.get('current_position', 0)

        # 获取参数
        magic_count = self.params.get('magic_count', 5)
        rsi_overbought = self.params.get('rsi_overbought', 70)
        rsi_oversold = self.params.get('rsi_oversold', 30)
        kdj_overbought = self.params.get('kdj_overbought', 80)
        kdj_oversold = self.params.get('kdj_oversold', 20)
        enable_short = self.params.get('enable_short', True)

        # 初始化信号
        signal = 0

        # 生成交易信号

        # 如果已有持仓，检查平仓信号
        if current_position > 0:  # 多头持仓
            # 检查是否有卖出信号
            if not np.isnan(magic_nine_sell) and magic_nine_sell >= magic_count:
                # 使用MACD直方图和KDJ确认卖出信号
                macd_confirm = macd_histo < 0  # MACD柱状图为负，确认下行动能
                kdj_confirm = kdj_j > kdj_overbought or (kdj_k < kdj_d)  # KDJ超买或K线下穿D线

                # 当主要信号出现时，如果有至少一个确认指标支持，则生成卖出信号
                if macd_confirm or kdj_confirm:
                    signal = -1
                    self.logger.info(
                        f"生成卖出信号: 多头平仓 (MagicNine卖出计数={magic_nine_sell}, MACD柱状图={macd_histo:.2f}, KDJ_J={kdj_j:.1f})")
                else:
                    self.logger.info(f"卖出信号被过滤: 确认指标不支持 (MACD柱状图={macd_histo:.2f}, KDJ_J={kdj_j:.1f})")

        elif current_position < 0:  # 空头持仓
            # 检查是否有买入信号
            if not np.isnan(magic_nine_buy) and magic_nine_buy >= magic_count:
                # 使用MACD直方图和KDJ确认买入信号
                macd_confirm = macd_histo > 0  # MACD柱状图为正，确认上行动能
                kdj_confirm = kdj_j < kdj_oversold or (kdj_k > kdj_d)  # KDJ超卖或K线上穿D线

                # 当主要信号出现时，如果有至少一个确认指标支持，则生成买入信号
                if macd_confirm or kdj_confirm:
                    signal = 1
                    self.logger.info(
                        f"生成买入信号: 空头平仓 (MagicNine买入计数={magic_nine_buy}, MACD柱状图={macd_histo:.2f}, KDJ_J={kdj_j:.1f})")
                else:
                    self.logger.info(f"买入信号被过滤: 确认指标不支持 (MACD柱状图={macd_histo:.2f}, KDJ_J={kdj_j:.1f})")

        else:  # 无持仓，检查开仓信号
            # 多头信号条件：买入计数达标且EMA快线>EMA慢线（上升趋势）且RSI不超买
            if not np.isnan(magic_nine_buy) and magic_nine_buy >= magic_count:
                # 确认趋势方向 (EMA快线 > EMA慢线 为上升趋势)
                trend_up = ema_fast > ema_slow

                # RSI不在超买区域 (避免在高点买入)
                rsi_ok = rsi < rsi_overbought

                # MACD和KDJ确认 - 移除对历史值的访问
                macd_confirm = macd_histo > 0  # MACD柱状图为正
                kdj_confirm = (kdj_k > kdj_d)  # K线上穿D线

                # 综合判断：趋势向上，RSI合理，且至少有一个确认指标支持
                if trend_up and rsi_ok and (macd_confirm or kdj_confirm):
                    signal = 1
                    self.logger.info(
                        f"生成买入信号: 新建多头 (MagicNine买入计数={magic_nine_buy}, RSI={rsi:.1f}, MACD柱状图={macd_histo:.2f}, KDJ_K={kdj_k:.1f})")
                else:
                    self.logger.info(
                        f"买入信号被过滤: 确认指标不支持 (趋势={trend_up}, RSI={rsi:.1f}, MACD={macd_confirm}, KDJ={kdj_confirm})")

            # 空头信号条件：卖出计数达标且EMA快线<EMA慢线（下降趋势）且RSI不超卖
            elif enable_short and not np.isnan(magic_nine_sell) and magic_nine_sell >= magic_count:
                # 确认趋势方向 (EMA快线 < EMA慢线 为下降趋势)
                trend_down = ema_fast < ema_slow

                # RSI不在超卖区域 (避免在低点卖空)
                rsi_ok = rsi > rsi_oversold

                # MACD和KDJ确认 - 移除对历史值的访问
                macd_confirm = macd_histo < 0  # MACD柱状图为负
                kdj_confirm = (kdj_k < kdj_d)  # K线下穿D线

                # 综合判断：趋势向下，RSI合理，且至少有一个确认指标支持
                if trend_down and rsi_ok and (macd_confirm or kdj_confirm):
                    signal = -1
                    self.logger.info(
                        f"生成卖出信号: 新建空头 (MagicNine卖出计数={magic_nine_sell}, RSI={rsi:.1f}, MACD柱状图={macd_histo:.2f}, KDJ_K={kdj_k:.1f})")
                else:
                    self.logger.info(
                        f"卖出信号被过滤: 确认指标不支持 (趋势={trend_down}, RSI={rsi:.1f}, MACD={macd_confirm}, KDJ={kdj_confirm})")

        return signal
