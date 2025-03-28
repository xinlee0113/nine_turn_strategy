import os
import logging
import csv
from datetime import datetime

def setup_logging(log_dir='logs', log_level=logging.INFO):
    """
    配置日志
    
    Args:
        log_dir: 日志目录
        log_level: 日志级别
    """
    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建日志文件名，包含时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"magic_nine_{timestamp}.log")
    
    # 配置日志
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger()


def log_trade(symbol, timestamp, action, price, quantity, value, commission, profit=None):
    """
    记录交易信息到CSV文件
    
    Args:
        symbol: 交易标的
        timestamp: 交易时间
        action: 交易动作（买入/卖出）
        price: 交易价格
        quantity: 交易数量
        value: 交易金额
        commission: 手续费
        profit: 利润（仅卖出时有效）
    """
    # 确保交易记录目录存在
    trade_log_dir = 'logs/trades'
    os.makedirs(trade_log_dir, exist_ok=True)
    
    # 交易记录文件
    trade_log_file = os.path.join(trade_log_dir, f"trades_{datetime.now().strftime('%Y%m%d')}.csv")
    
    # 检查文件是否存在，不存在则创建并写入表头
    file_exists = os.path.isfile(trade_log_file)
    
    with open(trade_log_file, mode='a', newline='') as file:
        fieldnames = ['timestamp', 'symbol', 'action', 'price', 'quantity', 'value', 'commission', 'profit']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        # 写入交易记录
        writer.writerow({
            'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else timestamp,
            'symbol': symbol,
            'action': action,
            'price': f"{price:.2f}",
            'quantity': quantity,
            'value': f"{value:.2f}",
            'commission': f"{commission:.2f}",
            'profit': f"{profit:.2f}" if profit is not None else ""
        }) 