"""
脚本工厂
创建各种脚本实例
"""
import logging

class ScriptFactory:
    """脚本工厂类"""
    
    def __init__(self):
        """初始化脚本工厂"""
        self.scripts = {}
        self.logger = logging.getLogger(__name__)
        
    def register_script(self, script_type, script_class):
        """
        注册脚本
        
        Args:
            script_type: 脚本类型
            script_class: 脚本类
        """
        self.scripts[script_type] = script_class
        
    def create_script(self, script_type):
        """
        创建脚本
        
        Args:
            script_type: 脚本类型
            
        Returns:
            Script: 脚本实例
            
        Raises:
            ValueError: 如果脚本类型未注册
        """
        if script_type not in self.scripts:
            raise ValueError(f"未知的脚本类型: {script_type}")
            
        script_class = self.scripts[script_type]
        return script_class()
        
    def get_script_count(self):
        """获取已注册的脚本数量"""
        return len(self.scripts) 