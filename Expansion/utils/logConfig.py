import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(console = True):
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_datefmt = '%Y-%m-%d %H:%M:%S'
    log_level = logging.ERROR  # 可以根据需要设置为 INFO, WARNING, ERROR, CRITICAL
    log_filename = 'app.log'
    log_max_size = 10 * 1024 * 1024  # 10MB
    log_backup_count = 5  # 保留 5 个备份

    # 创建日志目录
    log_directory = 'logs'
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
    log_file_path = os.path.join(log_directory, log_filename)

    # 创建一个 RotatingFileHandler
    rotating_file_handler = RotatingFileHandler(
        filename=log_file_path,
        mode='a',
        maxBytes=log_max_size,
        backupCount=log_backup_count
    )
    rotating_file_handler.setLevel(log_level)
    rotating_file_formatter = logging.Formatter(fmt=log_format, datefmt=log_datefmt)
    rotating_file_handler.setFormatter(rotating_file_formatter)

    # 获取 root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(rotating_file_handler)

    # 添加控制台日志处理器
    if console is True:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter(fmt=log_format, datefmt=log_datefmt)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
