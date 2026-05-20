"""
统一日志配置

提供项目级别的日志配置，使用多进程安全的 QueueHandler 模式
"""
import sys
import os

# 动态加载 mp_logging 模块
import importlib.util
_mp_logging_path = os.path.join(
    os.path.dirname(__file__),
    "generation_one", "naive-ollama", "mp_logging.py"
)

spec = importlib.util.spec_from_file_location("mp_logging", _mp_logging_path)
mp_logging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mp_logging)

setup_logging = mp_logging.setup_logging
get_logger = mp_logging.get_logger
shutdown_logging = mp_logging.shutdown_logging

_initialized = False


def setup_mp_logging(log_level: str = 'INFO', log_file: str = None):
    """
    初始化多进程安全日志系统

    应在主程序开始时调用一次
    """
    global _initialized
    if _initialized:
        return
    setup_logging(log_level, log_file)
    _initialized = True


def shutdown_mp_logging():
    """关闭日志系统"""
    shutdown_logging()
