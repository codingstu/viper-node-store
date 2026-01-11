"""
日志配置模块
"""

import logging
from ..config import config

# 创建全局日志记录器
logger = logging.getLogger("viper-node-store")

def setup_logger():
    """初始化日志配置"""
    
    # 清空现有处理器
    logger.handlers.clear()
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # 创建格式化器
    formatter = logging.Formatter(
        fmt=config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT
    )
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(console_handler)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    return logger


# 初始化日志
setup_logger()
