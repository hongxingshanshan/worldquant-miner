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

    优先使用多进程安全的 QueueHandler 模式
    如果不可用，则使用简单的 print 模式
    """
    if MP_LOGGING_AVAILABLE:
        return mp_get_logger(name)

    # 回退到简单模式
    return SimpleLogger(name or 'root')


def shutdown_mp_logging():
    """关闭日志系统"""
    if MP_LOGGING_AVAILABLE:
        shutdown_logging()


class SimpleLogger:
    """
    简单日志类，使用 print 输出

    用于极端情况或 mp_logging 不可用时
    """
    from datetime import datetime

    def __init__(self, name: str):
        self.name = name

    def _log(self, level: str, msg: str):
        """输出日志"""
        timestamp = self.datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
        pid = os.getpid()
        print(f'{timestamp} - {level} - [PID:{pid}] {self.name} {msg}', flush=True)

    def info(self, msg: str):
        self._log('INFO', msg)

    def debug(self, msg: str):
        self._log('DEBUG', msg)

    def warning(self, msg: str):
        self._log('WARNING', msg)

    def error(self, msg: str):
        self._log('ERROR', msg)

    def critical(self, msg: str):
        self._log('CRITICAL', msg)
