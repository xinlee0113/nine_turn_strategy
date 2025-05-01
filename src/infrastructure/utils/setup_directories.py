"""
目录初始化模块，确保所有结果目录存在
"""
import os
from pathlib import Path

def setup_result_directories():
    """
    初始化所有结果目录，确保目录结构正确
    删除outputs目录，创建results目录及子目录
    """
    # 要创建的目录列表
    result_dirs = [
        "results/backtest",          # 回测结果目录
        "results/backtest/plots",    # 回测图表目录
        "results/optimization",      # 优化结果目录
        "results/live",              # 实盘交易结果目录
    ]
    
    # 创建目录
    for dir_path in result_dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"已创建目录: {dir_path}")
    
    # 检查是否存在outputs目录，存在则提示可以删除
    if os.path.exists("outputs"):
        print("发现outputs目录，建议手动删除这个目录，所有结果已改为保存到results目录")

if __name__ == "__main__":
    setup_result_directories()
    print("目录结构初始化完成") 