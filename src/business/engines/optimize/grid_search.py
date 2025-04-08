import itertools
from typing import Dict, Any, List

from .optimizer import BaseOptimizer


class GridSearchOptimizer(BaseOptimizer):
    """网格搜索优化器"""

    def __init__(self, config: Dict[str, Any] = None):
        """初始化优化器
        
        Args:
            config: 优化器配置
        """
        super().__init__(config)

    def optimize(self, strategy_class: type, data: Any,
                 param_space: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """执行网格搜索优化
        
        Args:
            strategy_class: 策略类
            data: 市场数据
            param_space: 参数空间
            
        Returns:
            优化结果列表
        """
        # 生成参数组合
        param_names = list(param_space.keys())
        param_values = list(param_space.values())
        param_combinations = list(itertools.product(*param_values))

        results = []
        for params in param_combinations:
            # 创建参数字典
            param_dict = dict(zip(param_names, params))

            # 评估参数组合
            score = self.evaluate(strategy_class, data, param_dict)

            # 记录结果
            result = {
                'params': param_dict,
                'score': score
            }
            results.append(result)

        # 按分数排序
        results.sort(key=lambda x: x['score'], reverse=True)

        return results
