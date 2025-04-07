import logging
import os
from datetime import datetime

class Logger:
    """日志管理器"""

    def __init__(self, name, log_dir='logs'):
        """初始化日志管理器"""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 创建日志目录
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # 创建文件处理器
        log_file = os.path.join(log_dir, f'{name}_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, message):
        """记录信息级别的日志"""
        self.logger.info(message)
    
    def warning(self, message):
        """记录警告级别的日志"""
        self.logger.warning(message)
    
    def error(self, message):
        """记录错误级别的日志"""
        self.logger.error(message)
    
    def debug(self, message):
        """记录调试级别的日志"""
        self.logger.debug(message) 