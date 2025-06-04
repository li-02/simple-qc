"""
日志配置模块
"""
import os
import logging
import datetime
from logging.handlers import RotatingFileHandler


def setup_logger(ftp, log_dir="../logs"):
    """
    设置日志记录器
    
    Args:
        ftp: 站点FTP名称，用于生成日志文件名
        log_dir: 日志保存目录，默认为"../logs"
    
    Returns:
        logger: 配置好的日志记录器
    """
    # 确保日志目录存在
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建当前时间字符串
    time_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    
    # 日志文件名格式：ftp + 时间戳
    log_filename = f"{ftp}{time_str}.txt"
    log_path = os.path.join(log_dir, log_filename)
    
    # 创建日志记录器
    logger = logging.getLogger(f"data_qc_{ftp}_{time_str}")
    logger.setLevel(logging.DEBUG)
    
    # 防止日志重复
    if logger.handlers:
        return logger
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建文件处理器
    file_handler = RotatingFileHandler(
        log_path, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 定义日志格式
    log_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 设置处理器格式
    console_handler.setFormatter(log_format)
    file_handler.setFormatter(log_format)
    
    # 添加处理器到日志记录器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # 记录初始信息
    logger.info("=" * 50)
    logger.info(f"日志记录开始 - FTP站点: {ftp}")
    logger.info(f"日志文件路径: {log_path}")
    logger.info("=" * 50)
    
    # 存储日志文件路径，以便其他地方引用
    logger.log_file_path = log_path
    
    return logger


def get_task_logger(task_id):
    """
    获取特定任务的日志记录器
    
    Args:
        task_id: 任务ID
    
    Returns:
        logger: 任务日志记录器
    """
    logger = logging.getLogger(f"task_{task_id}")
    if not logger.handlers:
        # 如果这个logger还没有被配置，则使用根logger的配置
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            logger.addHandler(handler)
        logger.setLevel(root_logger.level)
    
    return logger


def close_logger(logger, success=True):
    """
    关闭日志记录器
    
    Args:
        logger: 日志记录器实例
        success: 任务是否成功完成
    """
    logger.info("=" * 50)
    logger.info(f"任务状态: {'成功' if success else '失败'}")
    logger.info(f"日志记录结束 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    # 关闭所有处理器
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)