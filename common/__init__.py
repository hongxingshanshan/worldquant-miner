"""
公共模块

提供跨服务共享的基础组件：
- wq_api_client: WorldQuant Brain API 统一客户端
- wq_exceptions: 自定义异常类
- wq_config: API 配置管理
"""

from .wq_api_client import WorldQuantBrainAPIClient, WorldQuantBrain
from .wq_exceptions import (
    WQAPIError,
    WQAuthError,
    WQRateLimitError,
    WQNotFoundError,
    WQServerError
)

__all__ = [
    'WorldQuantBrainAPIClient',
    'WorldQuantBrain',
    'WQAPIError',
    'WQAuthError',
    'WQRateLimitError',
    'WQNotFoundError',
    'WQServerError',
]
