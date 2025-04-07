from typing import Dict, Any, List
import pandas as pd
import numpy as np
from src.business.strategy.base_strategy import BaseStrategy
from src.interface.broker.tiger.tiger_client import TigerClient

class LiveEngine:
    """实盘引擎"""
    
    def __init__(self, strategy: BaseStrategy, client: TigerClient, 
                symbols: List[str], initial_capital: float):
        """
        初始化实盘引擎
        
        Args:
            strategy: 交易策略
            client: 交易客户端
            symbols: 交易标的
            initial_capital: 初始资金
        """
        self.strategy = strategy
        self.client = client
        self.symbols = symbols
        self.initial_capital = initial_capital
        
        self.positions = {symbol: 0 for symbol in symbols}
        self.cash = initial_capital
        self.trades = []
        
    def start(self) -> None:
        """启动实盘"""
        # 获取账户信息
        account_info = self.client.get_account_info()
        self.cash = account_info['cash']
        
        # 获取持仓信息
        positions = self.client.get_positions()
        for position in positions:
            symbol = position['symbol']
            if symbol in self.symbols:
                self.positions[symbol] = position['quantity']
        
        # 开始交易循环
        while True:
            try:
                # 获取市场数据
                data = self._get_market_data()
                
                # 生成信号
                signals = self.strategy.generate_signals(data)
                
                # 计算仓位
                target_positions = self.strategy.calculate_position(signals, data)
                
                # 执行交易
                self._execute_trades(target_positions, data)
                
                # 更新策略状态
                self._update_strategy_state(data)
                
            except Exception as e:
                print(f"Error in trading loop: {e}")
                continue
    
    def stop(self) -> None:
        """停止实盘"""
        # 平掉所有持仓
        for symbol, position in self.positions.items():
            if position != 0:
                self.client.place_order(
                    symbol=symbol,
                    side='SELL' if position > 0 else 'BUY',
                    quantity=abs(position),
                    price=0  # 市价单
                )
    
    def _get_market_data(self) -> Dict[str, pd.DataFrame]:
        """获取市场数据"""
        data = {}
        for symbol in self.symbols:
            # 获取历史数据
            history = self.client.get_historical_data(
                symbol=symbol,
                period='1d',
                interval='1m',
                limit=100
            )
            
            # 获取实时报价
            quote = self.client.get_realtime_quotes([symbol])
            
            # 合并数据
            df = pd.DataFrame(history)
            df = df.append(quote, ignore_index=True)
            data[symbol] = df
            
        return data
    
    def _execute_trades(self, target_positions: Dict[str, float], 
                       data: Dict[str, pd.DataFrame]) -> None:
        """执行交易"""
        for symbol, target_position in target_positions.items():
            current_position = self.positions[symbol]
            
            # 检查是否需要调整仓位
            if target_position != current_position:
                # 计算交易数量
                quantity = target_position - current_position
                
                # 确定交易方向
                side = 'BUY' if quantity > 0 else 'SELL'
                
                # 获取当前价格
                current_price = data[symbol]['close'].iloc[-1]
                
                # 计算交易金额
                amount = abs(quantity * current_price)
                
                # 检查资金是否足够
                if side == 'BUY' and amount > self.cash:
                    print(f"Insufficient cash to buy {symbol}")
                    continue
                
                # 执行交易
                order = self.client.place_order(
                    symbol=symbol,
                    side=side,
                    quantity=abs(quantity),
                    price=0  # 市价单
                )
                
                # 更新持仓和现金
                if order['status'] == 'FILLED':
                    self.positions[symbol] = target_position
                    self.cash -= amount if side == 'BUY' else -amount
                    
                    # 记录交易
                    self.trades.append({
                        'symbol': symbol,
                        'timestamp': pd.Timestamp.now(),
                        'side': side,
                        'quantity': abs(quantity),
                        'price': current_price,
                        'amount': amount
                    })
    
    def _update_strategy_state(self, data: Dict[str, pd.DataFrame]) -> None:
        """更新策略状态"""
        for symbol in self.symbols:
            current_price = data[symbol]['close'].iloc[-1]
            position = self.positions[symbol]
            self.strategy.update_state(current_price, position, self.cash) 