"""
统一日志配置模块

使用 QueueHandler/QueueListener 模式避免多线程 logging 死锁。
所有模块应通过此模块获取 logger。

使用方法:
    from logging_config import get_logger
    logger = get_logger(__name__)
"""
import logging
import logging.handlers
import queue
import os

# 全局日志队列
_log_queue = None
_queue_listener = None
_initialized = False

# 日志文件目录和文件名
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = 'alpha_mining.log'

# 统一日志格式
LOG_FORMAT = '%(asctime)s - %(levelname)s - [%(name)s] %(message)s'
LOG_FORMAT_FILE = '%(asctime)s - %(levelname)s - [%(name)s:%(filename)s:%(lineno)d] %(message)s'


def _init_logging():
    """初始化日志系统（内部方法）"""
    global _log_queue, _queue_listener, _initialized

    if _initialized:
        return

    # 创建日志队列
    _log_queue = queue.Queue(-1)

    # 创建 QueueHandler
    queue_handler = logging.handlers.QueueHandler(_log_queue)

    # 创建实际的 handlers
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    # 文件 handler
    log_path = os.path.join(LOG_DIR, LOG_FILE)
    file_handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT_FILE))

    # 创建 QueueListener
    _queue_listener = logging.handlers.QueueListener(
        _log_queue, stream_handler, file_handler
    )
    _queue_listener.start()

    _initialized = True

    # 配置 root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(queue_handler)


def get_logger(name: str = None) -> logging.Logger:
    """
    获取 logger 实例

    Args:
        name: logger 名称，通常使用 __name__

    Returns:
        配置好的 logger 实例
    """
    if not _initialized:
        _init_logging()

    # 获取或创建 logger
    logger = logging.getLogger(name)

    # 确保 logger 有 QueueHandler
    if _log_queue and not any(isinstance(h, logging.handlers.QueueHandler) for h in logger.handlers):
        queue_handler = logging.handlers.QueueHandler(_log_queue)
        logger.addHandler(queue_handler)
        logger.propagate = False

    return logger


def shutdown_logging():
    """关闭日志系统"""
    global _queue_listener, _initialized

    if _queue_listener:
        _queue_listener.stop()
        _queue_listener = None

    _initialized = False
