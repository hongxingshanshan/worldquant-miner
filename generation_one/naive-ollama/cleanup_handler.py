"""
Windows 控制台关闭事件处理器工具

用于捕获 Windows 控制台关闭事件，确保子进程和资源被正确清理。
"""

import sys
import ctypes
import signal
import atexit
from typing import Callable, Optional

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class WindowsCleanupHandler:
    """
    Windows 平台的清理处理器

    使用方法：
    ```python
    from cleanup_handler import WindowsCleanupHandler

    def my_cleanup():
        # 清理逻辑
        print("清理资源...")

    handler = WindowsCleanupHandler(cleanup_callback=my_cleanup)
    handler.setup()
    ```
    """

    def __init__(self, cleanup_callback: Optional[Callable] = None):
        """
        初始化清理处理器

        Args:
            cleanup_callback: 清理回调函数，在退出时调用
        """
        self.cleanup_callback = cleanup_callback
        self.handler = None

    def setup(self):
        """设置清理处理器"""
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Windows 平台特殊处理
        if sys.platform == 'win32':
            self._setup_windows_handler()

        # 注册 atexit 处理器
        atexit.register(self._cleanup)

        logger.info("清理处理器已设置")

    def _signal_handler(self, signum=None, frame=None):
        """处理 SIGINT 和 SIGTERM 信号"""
        signal_name = signal.Signals(signum).name if signum else "UNKNOWN"
        logger.info(f"收到退出信号 ({signal_name})，正在清理...")
        self._cleanup()
        sys.exit(0)

    def _setup_windows_handler(self):
        """设置 Windows 控制台事件处理器"""
        try:
            # 定义控制台事件类型
            CTRL_HANDLER_TYPE = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)

            def console_ctrl_handler(ctrl_type):
                """
                处理 Windows 控制台事件

                事件类型：
                - CTRL_C_EVENT = 0
                - CTRL_BREAK_EVENT = 1
                - CTRL_CLOSE_EVENT = 2 (关闭窗口)
                - CTRL_LOGOFF_EVENT = 5 (用户注销)
                - CTRL_SHUTDOWN_EVENT = 6 (系统关机)
                """
                if ctrl_type in (2, 5, 6):
                    logger.info(f"收到 Windows 控制台关闭事件 (类型: {ctrl_type})，正在清理...")
                    self._cleanup()
                    return True
                return False

            # 保存处理器引用，防止被垃圾回收
            self.handler = CTRL_HANDLER_TYPE(console_ctrl_handler)

            # 设置控制台处理器
            result = ctypes.windll.kernel32.SetConsoleCtrlHandler(self.handler, True)
            if result:
                logger.info("已注册 Windows 控制台关闭事件处理器")
            else:
                logger.warning("注册 Windows 控制台事件处理器失败")

        except Exception as e:
            logger.warning(f"无法注册 Windows 控制台事件处理器: {e}")

    def _cleanup(self):
        """执行清理"""
        if self.cleanup_callback:
            try:
                self.cleanup_callback()
                logger.info("清理完成")
            except Exception as e:
                logger.error(f"清理过程中出错: {e}")


# 便捷函数
def setup_cleanup_handler(cleanup_callback: Optional[Callable] = None):
    """
    设置清理处理器的便捷函数

    Args:
        cleanup_callback: 清理回调函数

    Returns:
        WindowsCleanupHandler 实例
    """
    handler = WindowsCleanupHandler(cleanup_callback)
    handler.setup()
    return handler
