"""
多进程安全日志配置

使用 QueueHandler + QueueListener 模式：
- 所有日志发送到队列
- 单独的监听线程负责写入文件
- 避免多进程/多线程的日志死锁问题

使用方法：
    from mp_logging import setup_logging, get_logger

    # 在主进程开始时调用一次
    setup_logging()

    # 获取 logger
    logger = get_logger(__name__)
    logger.info("这条日志是安全的")
"""
import logging
import logging.handlers
import os
import sys
import threading
import queue
from datetime import datetime
from typing import Optional

# 全局队列和监听器
_log_queue: Optional[queue.Queue] = None
_queue_listener: Optional[logging.handlers.QueueListener] = None
_initialized = False

# 日志格式
LOG_FORMAT = '%(asctime)s - %(levelname)s - [PID:%(process)d] %(name)s:%(lineno)d %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 日志目录
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')


def setup_logging(log_level: str = 'INFO', log_file: Optional[str] = None):
    """
    初始化多进程安全的日志系统

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径，默认为 logs/app.log
    """
    global _log_queue, _queue_listener, _initialized

    if _initialized:
        return

    # 确保日志目录存在
    os.makedirs(LOG_DIR, exist_ok=True)

    # 创建日志队列
    _log_queue = queue.Queue(-1)  # 无限大小

    # 日志文件路径
    if log_file is None:
        log_file = os.path.join(LOG_DIR, 'app.log')

    # 创建文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    # 创建队列监听器（在单独线程中处理日志写入）
    _queue_listener = logging.handlers.QueueListener(
        _log_queue,
        file_handler,
        console_handler,
        respect_handler_level=True
    )
    _queue_listener.start()

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 移除所有现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 添加队列处理器
    root_logger.addHandler(logging.handlers.QueueHandler(_log_queue))

    _initialized = True

    # 使用 print 输出初始化信息（因为 logger 还没完全准备好）
    print(f"[{datetime.now().strftime(DATE_FORMAT)}] 多进程安全日志系统已初始化 - 日志文件: {log_file}")


def get_logger(name: str = None) -> logging.Logger:
    """
    获取 logger 实例

    Args:
        name: logger 名称，通常使用 __name__

    Returns:
        Logger 实例
    """
    if not _initialized:
        setup_logging()

    return logging.getLogger(name)


def shutdown_logging():
    """
    关闭日志系统

    在程序退出前调用，确保所有日志都被写入
    """
    global _queue_listener, _initialized

    if _queue_listener:
        _queue_listener.stop()
        _queue_listener = None

    _initialized = False


def get_simple_logger(name: str = None):
    """
    获取简单 logger（不使用队列，直接 print）

    用于极端情况，如子进程中的简单日志
    """
    return SimpleLogger(name or 'root')


class SimpleLogger:
    """
    简单日志类，使用 print 输出

    用于子进程或极端情况，避免 logging 模块的复杂性
    """

    def __init__(self, name: str):
        self.name = name

    def _log(self, level: str, msg: str):
        """输出日志"""
        import os
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
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


# 注册退出清理
import atexit
atexit.register(shutdown_logging)
