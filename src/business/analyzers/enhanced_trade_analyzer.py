#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
增强版交易分析器
继承backtrader的TradeAnalyzer，添加平均每天交易次数计算
"""
from datetime import datetime, timedelta
import backtrader as bt
from backtrader.analyzers.tradeanalyzer import TradeAnalyzer
from backtrader.utils import AutoOrderedDict


class EnhancedTradeAnalyzer(bt.Analyzer):
    """
    增强版交易分析器
    添加平均每天交易次数的计算功能
    完全重写避免backtrader内部错误
    """
    
    def create_analysis(self):
        """初始化分析器"""
        self.rets = AutoOrderedDict()
        self.rets.total.total = 0
        self.rets.total.open = 0
        self.rets.total.closed = 0
        
        # 交易相关数据
        self.rets.pnl.gross.total = 0.0
        self.rets.pnl.gross.average = 0.0
        self.rets.pnl.net.total = 0.0
        self.rets.pnl.net.average = 0.0
        
        # 胜负
        self.rets.won.total = 0
        self.rets.won.pnl.total = 0.0
        self.rets.won.pnl.average = 0.0
        self.rets.won.pnl.max = 0.0
        
        self.rets.lost.total = 0
        self.rets.lost.pnl.total = 0.0
        self.rets.lost.pnl.average = 0.0
        self.rets.lost.pnl.max = 0.0
        
        # 连续记录
        self.rets.streak.won.current = 0
        self.rets.streak.won.longest = 0
        self.rets.streak.lost.current = 0
        self.rets.streak.lost.longest = 0
        
        # 多空
        self.rets.long.total = 0
        self.rets.long.pnl.total = 0.0
        self.rets.long.pnl.average = 0.0
        self.rets.long.pnl.won.total = 0.0
        self.rets.long.pnl.won.average = 0.0
        self.rets.long.pnl.won.max = 0.0
        self.rets.long.pnl.lost.total = 0.0
        self.rets.long.pnl.lost.average = 0.0
        self.rets.long.pnl.lost.max = 0.0
        self.rets.long.won = 0
        self.rets.long.lost = 0
        
        self.rets.short.total = 0
        self.rets.short.pnl.total = 0.0
        self.rets.short.pnl.average = 0.0
        self.rets.short.pnl.won.total = 0.0
        self.rets.short.pnl.won.average = 0.0
        self.rets.short.pnl.won.max = 0.0
        self.rets.short.pnl.lost.total = 0.0
        self.rets.short.pnl.lost.average = 0.0
        self.rets.short.pnl.lost.max = 0.0
        self.rets.short.won = 0
        self.rets.short.lost = 0
        
        # 我们的自定义扩展
        self.rets.avg_trades_per_day = 0.0
        self.rets.trading_days = 0
        
        # 用于记录交易日的集合
        self._trading_days = set()

    def stop(self):
        """停止分析器并计算统计数据"""
        super(EnhancedTradeAnalyzer, self).stop()
        
        # 计算交易天数
        self.rets.trading_days = len(self._trading_days) if self._trading_days else 1
        
        # 计算平均每天交易次数
        total_closed = self.rets.total.closed
        self.rets.avg_trades_per_day = total_closed / self.rets.trading_days

    def next(self):
        """每根bar调用的方法，用于记录交易日期"""
        # 记录当前交易日期
        dt = self.strategy.datetime.date(0)
        if dt not in self._trading_days:
            self._trading_days.add(dt)
    
    def notify_trade(self, trade):
        """
        交易通知函数，会在交易开启、关闭时调用
        
        Args:
            trade: 交易对象
        """
        if trade.justopened:
            # 新开仓交易
            self.rets.total.total += 1
            self.rets.total.open += 1
            
            # 记录交易日期
            dt = self.strategy.datetime.date(0)
            if dt not in self._trading_days:
                self._trading_days.add(dt)
            
        elif trade.status == trade.Closed:
            # 平仓交易
            self.rets.total.open -= 1
            self.rets.total.closed += 1
            
            # 记录交易日期
            dt = self.strategy.datetime.date(0)
            if dt not in self._trading_days:
                self._trading_days.add(dt)
            
            # 判断盈亏
            is_win = trade.pnlcomm >= 0.0
            is_long = trade.long
            
            # 更新总体盈亏
            self.rets.pnl.gross.total += trade.pnl
            self.rets.pnl.net.total += trade.pnlcomm
            
            if self.rets.total.closed > 0:
                self.rets.pnl.gross.average = self.rets.pnl.gross.total / self.rets.total.closed
                self.rets.pnl.net.average = self.rets.pnl.net.total / self.rets.total.closed
            
            # 更新胜负统计
            if is_win:
                self.rets.won.total += 1
                self.rets.won.pnl.total += trade.pnlcomm
                
                if self.rets.won.total > 0:
                    self.rets.won.pnl.average = self.rets.won.pnl.total / self.rets.won.total
                
                self.rets.won.pnl.max = max(self.rets.won.pnl.max, trade.pnlcomm)
                
                # 连胜记录
                self.rets.streak.won.current += 1
                self.rets.streak.lost.current = 0
                self.rets.streak.won.longest = max(self.rets.streak.won.longest, self.rets.streak.won.current)
            else:
                self.rets.lost.total += 1
                self.rets.lost.pnl.total += trade.pnlcomm
                
                if self.rets.lost.total > 0:
                    self.rets.lost.pnl.average = self.rets.lost.pnl.total / self.rets.lost.total
                
                self.rets.lost.pnl.max = min(self.rets.lost.pnl.max, trade.pnlcomm)
                
                # 连败记录
                self.rets.streak.lost.current += 1
                self.rets.streak.won.current = 0
                self.rets.streak.lost.longest = max(self.rets.streak.lost.longest, self.rets.streak.lost.current)
            
            # 更新多空统计
            if is_long:
                self.rets.long.total += 1
                self.rets.long.pnl.total += trade.pnlcomm
                
                if self.rets.long.total > 0:
                    self.rets.long.pnl.average = self.rets.long.pnl.total / self.rets.long.total
                
                if is_win:
                    self.rets.long.won += 1
                    self.rets.long.pnl.won.total += trade.pnlcomm
                    
                    if self.rets.long.won > 0:
                        self.rets.long.pnl.won.average = self.rets.long.pnl.won.total / self.rets.long.won
                    
                    self.rets.long.pnl.won.max = max(self.rets.long.pnl.won.max, trade.pnlcomm)
                else:
                    self.rets.long.lost += 1
                    self.rets.long.pnl.lost.total += trade.pnlcomm
                    
                    if self.rets.long.lost > 0:
                        self.rets.long.pnl.lost.average = self.rets.long.pnl.lost.total / self.rets.long.lost
                    
                    self.rets.long.pnl.lost.max = min(self.rets.long.pnl.lost.max, trade.pnlcomm)
            else:
                self.rets.short.total += 1
                self.rets.short.pnl.total += trade.pnlcomm
                
                if self.rets.short.total > 0:
                    self.rets.short.pnl.average = self.rets.short.pnl.total / self.rets.short.total
                
                if is_win:
                    self.rets.short.won += 1
                    self.rets.short.pnl.won.total += trade.pnlcomm
                    
                    if self.rets.short.won > 0:
                        self.rets.short.pnl.won.average = self.rets.short.pnl.won.total / self.rets.short.won
                    
                    self.rets.short.pnl.won.max = max(self.rets.short.pnl.won.max, trade.pnlcomm)
                else:
                    self.rets.short.lost += 1
                    self.rets.short.pnl.lost.total += trade.pnlcomm
                    
                    if self.rets.short.lost > 0:
                        self.rets.short.pnl.lost.average = self.rets.short.pnl.lost.total / self.rets.short.lost
                    
                    self.rets.short.pnl.lost.max = min(self.rets.short.pnl.lost.max, trade.pnlcomm) 