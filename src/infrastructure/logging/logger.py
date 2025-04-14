"""
日志管理器
提供统一的日志记录功能
"""
import logging
import os
from datetime import datetime
import inspect


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

        # 创建自定义过滤器，为所有日志条目添加调用者信息
        class CallerFilter(logging.Filter):
            def filter(self, record):
                if not hasattr(record, 'caller'):
                    record.caller = 'Unknown'
                return True
                
        caller_filter = CallerFilter()
        
        # 创建文件处理器
        current_date = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(log_subdir, f'{self.name}_{current_date}.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.addFilter(caller_filter)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.addFilter(caller_filter)

        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(caller)s] - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def _get_caller_class(self):
        """获取调用者的类名"""
        try:
            # 获取调用栈
            stack = inspect.stack()
            # 找到调用当前日志方法的框架（第2帧，越过当前日志方法）
            if len(stack) > 2:
                frame = stack[2]
                # 尝试获取类实例的类名
                if 'self' in frame[0].f_locals:
                    caller_self = frame[0].f_locals['self']
                    return caller_self.__class__.__name__
                # 尝试获取模块名
                module = inspect.getmodule(frame[0])
                if module:
                    module_name = module.__name__.split('.')[-1]
                    return module_name
            return 'Unknown'
        except Exception:
            return 'Unknown'

    def info(self, message):
        """记录信息级别的日志"""
        caller_class = self._get_caller_class()
        self.logger.info(message, extra={'caller': caller_class})

    def warning(self, message):
        """记录警告级别的日志"""
        caller_class = self._get_caller_class()
        self.logger.warning(message, extra={'caller': caller_class})

    def error(self, message):
        """记录错误级别的日志"""
        caller_class = self._get_caller_class()
        self.logger.error(message, extra={'caller': caller_class})

    def debug(self, message):
        """记录调试级别的日志"""
        caller_class = self._get_caller_class()
        self.logger.debug(message, extra={'caller': caller_class})

    def setup_basic_logging(self):
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
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(caller)s] - %(message)s')
        console_handler.setFormatter(formatter)

        # 添加自定义过滤器，为所有日志条目添加调用者信息
        class CallerFilter(logging.Filter):
            def filter(self, record):
                if not hasattr(record, 'caller'):
                    record.caller = 'Unknown'
                return True
                
        caller_filter = CallerFilter()
        console_handler.addFilter(caller_filter)

        # 添加处理器
        root_logger.addHandler(console_handler)


# 测试代码，当直接运行此文件时执行
if __name__ == "__main__":
    class TestClass:
        def __init__(self):
            self.logger = Logger("test_class")
            
        def test_method(self):
            self.logger.info("这是一个来自TestClass的日志")
            self.logger.warning("这是一个警告日志")
            self.logger.error("这是一个错误日志")
            
    def test_function():
        logger = Logger("test_function")
        logger.info("这是一个来自函数的日志")
        
    # 创建测试实例并调用方法
    test_obj = TestClass()
    test_obj.test_method()
    
    # 调用测试函数
    test_function()
