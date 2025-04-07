"""
测试神奇九转策略
"""
import pytest
import pandas as pd
from src.business.strategy.magic_nine import MagicNineStrategy

class TestMagicNineStrategy:
    @pytest.fixture
    def strategy(self):
        """创建策略实例"""
        return MagicNineStrategy(period=9)
        
    @pytest.fixture
    def sample_data(self):
        """创建测试数据"""
        return pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
        })
        
    def test_generate_signals(self, strategy, sample_data):
        """测试信号生成"""
        # 生成信号
        signals = strategy.generate_signals(sample_data)
        
        # 验证信号
        assert signals is not None
        assert len(signals) == len(sample_data)
        assert signals.iloc[-1] == 1  # 买入信号
        
    def test_manage_position(self, strategy, sample_data):
        """测试仓位管理"""
        # 设置初始仓位
        strategy.position = 0
        
        # 生成信号
        signals = strategy.generate_signals(sample_data)
        
        # 管理仓位
        position = strategy.manage_position(signals)
        
        # 验证仓位
        assert position is not None
        assert position > 0  # 应该有持仓 