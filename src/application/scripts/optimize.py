import yaml
import pandas as pd
from src.optimization.grid_search import GridSearchOptimizer
from src.optimization.genetic import GeneticOptimizer
from src.optimization.bayesian import BayesianOptimizer
from src.optimization.visualizer import OptimizationVisualizer
from src.utils.logging import Logger

def load_config(config_path: str) -> dict:
    """加载配置文件"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)
        
def create_optimizer(config: dict):
    """创建优化器"""
    optimizer_type = config['optimizer']
    if optimizer_type == 'grid_search':
        return GridSearchOptimizer(config)
    elif optimizer_type == 'genetic':
        return GeneticOptimizer(config)
    elif optimizer_type == 'bayesian':
        return BayesianOptimizer(config)
    else:
        raise ValueError(f"Unknown optimizer type: {optimizer_type}")
        
def main():
    # 加载配置
    config = load_config('configs/optimization.yaml')
    
    # 设置日志
    logger = Logger.setup_logger('optimization', config['output_dir'])
    logger.info("启动参数优化")
    
    try:
        # 加载数据
        data = pd.read_csv('data/market_data.csv', index_col=0, parse_dates=True)
        
        # 创建优化器
        optimizer = create_optimizer(config)
        
        # 导入策略类
        from src.strategies.magic_nine.smart import MagicNineSmartStrategy
        
        # 执行优化
        logger.info("开始优化过程")
        best_params, best_score = optimizer.optimize(
            MagicNineSmartStrategy,
            data,
            config['param_space']
        )
        
        # 保存结果
        optimizer.save_results(f"{config['output_dir']}/results.pkl")
        
        # 输出结果
        logger.info(f"最佳参数: {best_params}")
        logger.info(f"最佳得分: {best_score}")
        
        # 可视化结果
        visualizer = OptimizationVisualizer({
            'best_params': best_params,
            'best_score': best_score,
            'history': optimizer.history
        })
        
        # 绘制图表
        visualizer.plot_convergence(f"{config['output_dir']}/convergence.png")
        visualizer.plot_parameter_importance(f"{config['output_dir']}/importance.png")
        
        # 绘制参数分布
        for param in best_params.keys():
            visualizer.plot_parameter_distribution(
                param,
                f"{config['output_dir']}/{param}_distribution.png"
            )
            
        # 绘制参数热力图
        params = list(best_params.keys())
        for i in range(len(params)):
            for j in range(i+1, len(params)):
                visualizer.plot_parameter_heatmap(
                    params[i],
                    params[j],
                    f"{config['output_dir']}/{params[i]}_{params[j]}_heatmap.png"
                )
                
    except Exception as e:
        logger.error(f"优化过程错误: {str(e)}")
        raise

if __name__ == '__main__':
    main() 