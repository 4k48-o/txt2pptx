"""
Logger Configuration - 日志配置
"""

import logging
import sys
from typing import Optional

from .config import Config

# 全局日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_logger_initialized = False


def setup_logger(level: Optional[str] = None) -> None:
    """
    设置全局日志配置

    Args:
        level: 日志级别，如果不传则从配置读取
    """
    global _logger_initialized

    if _logger_initialized:
        return

    config = Config()
    log_level = level or config.log_level

    # 配置根日志
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # 降低第三方库的日志级别
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    _logger_initialized = True


def get_logger(name: str) -> logging.Logger:
    """
    获取 Logger 实例

    Args:
        name: Logger 名称，通常使用 __name__

    Returns:
        Logger 实例
    """
    setup_logger()
    return logging.getLogger(name)

