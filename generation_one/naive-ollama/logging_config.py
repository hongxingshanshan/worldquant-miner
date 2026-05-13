"""
统一日志配置

优先使用多进程安全的 QueueHandler 模式
如果 mp_logging 不可用，则回退到简单的 print 模式
"""
import sys
import os

# 尝试导入多进程安全日志
try:
    from mp_logging import setup_logging, get_logger as mp_get_logger, shutdown_logging
    MP_LOGGING_AVAILABLE = True
except ImportError:
    MP_LOGGING_AVAILABLE = False

_initialized = False


def setup_mp_logging(log_level: str = 'INFO', log_file: str = None):
    """
    初始化多进程安全日志系统

    应在主程序开始时调用一次
    """
    global _initialized
    if _initialized:
        return

    if MP_LOGGING_AVAILABLE:
        setup_logging(log_level, log_file)
    _initialized = True


def get_logger(name: str = None):
    """
    获取 logger 实例

    使用多进程安全的 QueueHandler 模式
    """
    if not MP_LOGGING_AVAILABLE:
        raise ImportError(
            "mp_logging 模块不可用，请确保 mp_logging.py 存在。\n"
            "多进程安全日志系统是必需的依赖。"
        )
    return mp_get_logger(name)


def shutdown_mp_logging():
    """关闭日志系统"""
    if MP_LOGGING_AVAILABLE:
        shutdown_logging()
