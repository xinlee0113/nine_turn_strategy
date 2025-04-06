"""
主程序入口
负责程序的启动和整体流程控制
"""
from src.application.script_manager import ScriptManager
from src.application.script_factory import ScriptFactory

def main():
    """
    主程序入口函数
    """
    # 初始化脚本管理器
    script_manager = ScriptManager()
    
    # 初始化脚本工厂
    script_factory = ScriptFactory()
    
    # TODO: 根据命令行参数选择运行模式
    # 1. 回测模式
    # 2. 优化模式
    # 3. 实盘模式
    
if __name__ == "__main__":
    main() 