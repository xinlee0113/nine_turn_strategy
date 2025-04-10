import os
import sys
import backtrader as bt

# 将项目根目录添加到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from src.interface.data.tiger_csv_data import TigerCsvData


class RSIStrategy(bt.Strategy):
    params = (
        ('rsi_period_short', 6),
        ('rsi_period_medium', 12),
        ('rsi_period_long', 24),
        ('rsi_overbought', 70),
        ('rsi_oversold', 30),
    )

    def __init__(self):
        print('init')

        # 添加RSI指标，使用SMA方法计算
        self.rsi_short = bt.indicators.RSI(self.data.close, period=self.p.rsi_period_short,
                                              plot=True, plotname='RSI_Short')
        self.rsi_medium = bt.indicators.RSI(self.data.close, period=self.p.rsi_period_medium,
                                               plot=True, plotname='RSI_Medium')
        self.rsi_long = bt.indicators.RSI(self.data.close, period=self.p.rsi_period_long,
                                               plot=True, plotname='RSI_Long')

        # 记录交易结果
        self.trades = []

    def next(self):

        # 确保RSI指标已经计算好并且有有效值
        rsi_short_ = self.rsi_short[0]
        print(f'rsi_short_: {rsi_short_}')
        if rsi_short_ is None or self.rsi_medium[0] is None or self.rsi_long[0] is None:
            print("RSI指标计算中，请稍等...")
            return

        # 添加非空验证
        if not self.position:
            print("当前没有仓位，开始交易。")
            # 买入条件：短期 RSI 超卖且长期 RSI 超买
            if rsi_short_ < self.p.rsi_oversold and self.rsi_long[0] > self.p.rsi_overbought:
                print("买入条件满足，开始买入。")
                self.buy()
        else:
            print("当前有仓位，开始交易。")
            # 卖出条件：短期 RSI 超买且长期 RSI 超卖
            if rsi_short_ > self.p.rsi_overbought and self.rsi_long[0] < self.p.rsi_oversold:
                print("卖出条件满足，开始卖出。")
                self.sell()

    def notify_trade(self, trade):
        if trade.isclosed:
            profit = trade.pnlcomm
            self.trades.append(profit)

    def stop(self):
        total_trades = len(self.trades)
        if total_trades == 0:
            print("没有进行交易，无法计算胜率和盈亏比。")
            return

        winning_trades = sum(1 for profit in self.trades if profit > 0)
        losing_trades = total_trades - winning_trades

        win_rate = winning_trades / total_trades * 100

        total_winning_profit = sum(profit for profit in self.trades if profit > 0)
        total_losing_profit = abs(sum(profit for profit in self.trades if profit < 0))

        if losing_trades == 0:
            risk_reward_ratio = float('inf')
        else:
            average_winning_profit = total_winning_profit / winning_trades
            average_losing_profit = total_losing_profit / losing_trades
            risk_reward_ratio = average_winning_profit / average_losing_profit

        print(f"胜率: {win_rate:.2f}%")
        print(f"盈亏比: {risk_reward_ratio:.2f}")


if __name__ == '__main__':
    cerebro = bt.Cerebro()

    cerebro.addstrategy(RSIStrategy)

    data = TigerCsvData()

    cerebro.adddata(data)
    cerebro.broker.setcash(100000.0)

    print('初始资金: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('最终资金: %.2f' % cerebro.broker.getvalue())
