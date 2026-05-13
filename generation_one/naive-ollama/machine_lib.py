"""
Machine Learning Library for Alpha Generation

此文件现在作为兼容层，从拆分后的模块导入功能：
- wq_api_client.py: WorldQuant Brain API 客户端
- alpha_factory.py: Alpha 表达式工厂

保持向后兼容性，原有导入路径仍然有效。
"""

# 从拆分后的模块导入
try:
    from wq_api_client import WorldQuantBrain, WorldQuantBrainAPIClient
    from alpha_factory import (
        AlphaFactory,
        ARSENAL_OPS,
        GROUP_OPS,
        TWIN_FIELD_OPS
    )
    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# 导出操作符常量（向后兼容）
if MODULES_AVAILABLE:
    arsenal = ARSENAL_OPS
    group_ops = GROUP_OPS
    twin_field_ops = TWIN_FIELD_OPS
else:
    # 模块不可用时抛出错误，而非静默降级
    raise ImportError(
        "必需模块不可用，请确保 wq_api_client.py 和 alpha_factory.py 存在。\n"
        "这些模块提供 WorldQuantBrain 和 AlphaFactory 的核心功能。"
    )


# 导出
__all__ = [
    'WorldQuantBrain',
    'WorldQuantBrainAPIClient',
    'AlphaFactory',
    'arsenal',
    'group_ops',
    'twin_field_ops',
    'ARSENAL_OPS',
    'GROUP_OPS',
    'TWIN_FIELD_OPS'
]
