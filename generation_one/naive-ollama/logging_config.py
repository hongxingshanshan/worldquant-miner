"""
极简日志配置 - 使用 print 输出，避免 logging 模块的复杂性

多进程环境下，logging 模块可能导致各种问题：
- 文件锁定
- 缓冲区未刷新
- 内部锁竞争

使用 print 直接输出到 stdout，简单可靠。
"""
import sys
from datetime import datetime
import os

LOG_FORMAT = '{} - {} - [PID:{}] {}:{} {}'

_initialized = False

def _init_logging():
    """初始化日志系统"""
    global _initialized
    if _initialized:
        return
    _initialized = True


def get_logger(name: str = None):
    """获取一个简单的 logger 对象"""
    _init_logging()
    return SimpleLogger(name or 'root')


class SimpleLogger:
    """简单日志类，使用 print 输出"""

    def __init__(self, name: str):
        self.name = name

    def _log(self, level: str, msg: str):
        """输出日志"""
        import threading
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
        pid = os.getpid()
        # 获取调用者的文件名和行号
        import inspect
        frame = inspect.currentframe()
        # 向上查找，跳过 _log, info, debug 等方法
        caller_frame = frame.f_back.f_back
        filename = os.path.basename(caller_frame.f_code.co_filename)
        lineno = caller_frame.f_lineno
        print(LOG_FORMAT.format(timestamp, level, pid, filename, lineno, msg), flush=True)

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


def shutdown_logging():
    """关闭日志系统（兼容性函数）"""
    pass
