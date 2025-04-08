"""
日志管理器
提供统一的日志记录功能
"""
import logging
import os
from datetime import datetime


class Logger:
    """日志管理器"""

    def __init__(self, name=None, log_dir='logs'):
        """初始化日志管理器
        
        Args:
            name: 日志名称，默认为root
            log_dir: 日志目录，默认为logs
        """
        # 如果没有提供名称，使用root
        self.name = name or 'root'
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.INFO)

        # 防止重复添加处理器
        if self.logger.handlers:
            return

        # 创建日志目录
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 确定日志子目录（根据类型区分）
        if 'backtest' in self.name.lower():
            sub_dir = 'backtest'
        elif 'live' in self.name.lower():
            sub_dir = 'live'
        else:
            sub_dir = 'common'

        # 创建子目录
        log_subdir = os.path.join(log_dir, sub_dir)
        if not os.path.exists(log_subdir):
            os.makedirs(log_subdir)

        # 创建文件处理器
        current_date = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(log_subdir, f'{self.name}_{current_date}.log')
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

    def setup_basic_logging(cls):
        """设置基本日志配置，配置根日志记录器"""
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        # 防止重复添加处理器
        if root_logger.handlers:
            return

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)

        # 添加处理器
        root_logger.addHandler(console_handler)
