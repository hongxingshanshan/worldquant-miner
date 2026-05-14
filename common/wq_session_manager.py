"""
WorldQuant Brain API 统一 Session 管理器

所有模块共享同一个 session，自动处理认证过期和重新认证。
"""

import requests
import json
import os
import threading
import logging
from typing import Optional, Tuple
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class WQSessionManager:
    """
    WorldQuant Brain API Session 管理器（单例模式）

    功能：
    - 统一管理 WorldQuant API 认证 session
    - 自动检测 session 过期并重新认证
    - 线程安全
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.sess: Optional[requests.Session] = None
        self.credentials: Optional[Tuple[str, str]] = None
        self.credentials_path: str = "./credential.txt"
        self.session_lock = threading.Lock()
        self._initialized = True
        logger.info("WQSessionManager 初始化完成")

    def set_credentials_path(self, path: str) -> None:
        """设置凭证文件路径"""
        self.credentials_path = path

    def _load_credentials(self) -> Optional[Tuple[str, str]]:
        """加载凭证"""
        try:
            if os.path.exists(self.credentials_path):
                with open(self.credentials_path, 'r') as f:
                    credentials = json.load(f)
                if isinstance(credentials, (list, tuple)) and len(credentials) >= 2:
                    return (credentials[0], credentials[1])
            logger.error(f"凭证文件格式错误或不存在: {self.credentials_path}")
        except Exception as e:
            logger.error(f"加载凭证失败: {e}")
        return None

    def _create_session(self) -> Optional[requests.Session]:
        """创建并认证新 session"""
        if self.credentials is None:
            self.credentials = self._load_credentials()

        if self.credentials is None:
            logger.error("无法加载凭证")
            return None

        try:
            sess = requests.Session()
            sess.trust_env = False  # 禁用代理
            sess.auth = HTTPBasicAuth(self.credentials[0], self.credentials[1])

            logger.info("正在认证 WorldQuant Brain API...")
            response = sess.post(
                'https://api.worldquantbrain.com/authentication',
                timeout=30
            )

            if response.status_code == 201:
                logger.info("WorldQuant Brain API 认证成功")
                return sess
            else:
                logger.error(f"认证失败: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"创建 session 失败: {e}")
            return None

    def _validate_session(self, sess: requests.Session) -> bool:
        """验证 session 是否有效"""
        try:
            response = sess.get(
                'https://api.worldquantbrain.com/users/self',
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def get_session(self, force_reauth: bool = False) -> Optional[requests.Session]:
        """
        获取有效的 session

        Args:
            force_reauth: 是否强制重新认证

        Returns:
            有效的 requests.Session 或 None
        """
        with self.session_lock:
            # 如果强制重新认证，清除现有 session
            if force_reauth and self.sess is not None:
                logger.info("强制重新认证...")
                try:
                    self.sess.close()
                except:
                    pass
                self.sess = None

            # 如果已有 session，验证是否有效
            if self.sess is not None:
                if self._validate_session(self.sess):
                    return self.sess
                else:
                    logger.info("Session 已过期，重新认证...")
                    try:
                        self.sess.close()
                    except:
                        pass
                    self.sess = None

            # 创建新 session
            self.sess = self._create_session()
            return self.sess

    def close(self) -> None:
        """关闭 session"""
        with self.session_lock:
            if self.sess is not None:
                try:
                    self.sess.close()
                except:
                    pass
                self.sess = None

    def request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """
        发送请求，自动处理认证

        Args:
            method: HTTP 方法 (GET, POST, etc.)
            url: 请求 URL
            **kwargs: requests 的其他参数

        Returns:
            requests.Response 或 None
        """
        sess = self.get_session()
        if sess is None:
            logger.error("无法获取有效 session")
            return None

        try:
            response = sess.request(method, url, **kwargs)

            # 如果返回 401，尝试重新认证一次
            if response.status_code == 401:
                logger.info("请求返回 401，尝试重新认证...")
                sess = self.get_session(force_reauth=True)
                if sess is not None:
                    response = sess.request(method, url, **kwargs)

            return response

        except Exception as e:
            logger.error(f"请求失败: {e}")
            return None

    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """GET 请求"""
        return self.request('GET', url, **kwargs)

    def post(self, url: str, **kwargs) -> Optional[requests.Response]:
        """POST 请求"""
        return self.request('POST', url, **kwargs)


# 全局单例
_session_manager: Optional[WQSessionManager] = None
_global_lock = threading.Lock()


def get_wq_session_manager(credentials_path: Optional[str] = None) -> WQSessionManager:
    """
    获取全局 Session 管理器实例

    Args:
        credentials_path: 凭证文件路径（可选）

    Returns:
        WQSessionManager 实例
    """
    global _session_manager

    with _global_lock:
        if _session_manager is None:
            _session_manager = WQSessionManager()

        if credentials_path is not None:
            _session_manager.set_credentials_path(credentials_path)

        return _session_manager


def get_wq_session(force_reauth: bool = False) -> Optional[requests.Session]:
    """
    获取 WorldQuant API Session（便捷函数）

    Args:
        force_reauth: 是否强制重新认证

    Returns:
        requests.Session 或 None
    """
    return get_wq_session_manager().get_session(force_reauth)


def close_wq_session() -> None:
    """关闭全局 session"""
    global _session_manager
    if _session_manager is not None:
        _session_manager.close()
