from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
import random
from .optimizer import BaseOptimizer

class GeneticOptimizer(BaseOptimizer):
    """遗传算法优化器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.population_size = config.get('population_size', 50)
        self.generations = config.get('generations', 20)
        self.mutation_rate = config.get('mutation_rate', 0.1)
        self.elite_size = config.get('elite_size', 5)
        
    def optimize(self, strategy_class, data: pd.DataFrame, 
                param_space: Dict[str, List[Any]]) -> Tuple[Dict[str, Any], float]:
        """执行遗传算法优化"""
        # 初始化种群
        population = self._initialize_population(param_space)
        
        # 进化过程
        for generation in range(self.generations):
            # 评估适应度
            fitness_scores = self._evaluate_population(strategy_class, data, population)
            
            # 选择精英
            elite_indices = np.argsort(fitness_scores)[-self.elite_size:]
            elite = [population[i] for i in elite_indices]
            
            # 更新最佳参数
            best_idx = elite_indices[-1]
            if fitness_scores[best_idx] > self.best_score:
                self.best_score = fitness_scores[best_idx]
                self.best_params = population[best_idx]
                
            # 记录历史
            self.history.append({
                'generation': generation,
                'best_score': self.best_score,
                'best_params': self.best_params
            })
            
            # 生成新一代
            new_population = elite.copy()
            while len(new_population) < self.population_size:
                # 选择父代
                parent1 = self._select_parent(population, fitness_scores)
                parent2 = self._select_parent(population, fitness_scores)
                
                # 交叉
                child = self._crossover(parent1, parent2)
                
                # 变异
                child = self._mutate(child, param_space)
                
                new_population.append(child)
                
            population = new_population
            
        return self.best_params, self.best_score
        
    def _initialize_population(self, param_space: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """初始化种群"""
        population = []
        for _ in range(self.population_size):
            params = {}
            for param, values in param_space.items():
                params[param] = random.choice(values)
            population.append(params)
        return population
        
    def _evaluate_population(self, strategy_class, data: pd.DataFrame, 
                           population: List[Dict[str, Any]]) -> np.ndarray:
        """评估种群适应度"""
        scores = []
        for params in population:
            score = self.evaluate(strategy_class, data, params)
            scores.append(score)
        return np.array(scores)
        
    def _select_parent(self, population: List[Dict[str, Any]], 
                      fitness_scores: np.ndarray) -> Dict[str, Any]:
        """选择父代"""
        # 轮盘赌选择
        probs = fitness_scores / fitness_scores.sum()
        idx = np.random.choice(len(population), p=probs)
        return population[idx]
        
    def _crossover(self, parent1: Dict[str, Any], 
                  parent2: Dict[str, Any]) -> Dict[str, Any]:
        """交叉操作"""
        child = {}
        for param in parent1.keys():
            if random.random() < 0.5:
                child[param] = parent1[param]
            else:
                child[param] = parent2[param]
        return child
        
    def _mutate(self, child: Dict[str, Any], 
               param_space: Dict[str, List[Any]]) -> Dict[str, Any]:
        """变异操作"""
        for param in child.keys():
            if random.random() < self.mutation_rate:
                child[param] = random.choice(param_space[param])
        return child 