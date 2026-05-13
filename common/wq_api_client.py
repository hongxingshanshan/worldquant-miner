"""
WorldQuant Brain API 统一客户端

提供完整的 API 封装，支持：
- 认证和会话管理
- Alpha 增删改查
- 模拟提交和监控
- 数据字段和操作符获取
- 统一错误处理和重试机制

使用方式：
    from common.wq_api_client import WorldQuantBrainAPIClient

    # 从凭证文件初始化
    client = WorldQuantBrainAPIClient.from_credentials('credential.txt')

    # 或直接传入用户名密码
    client = WorldQuantBrainAPIClient(username='xxx', password='xxx')

    # 获取 Alpha 详情
    alpha = client.get_alpha('E5q3lZ3J')

    # 提交模拟
    result = client.create_simulation('rank(close)', settings={...})
"""

import requests
from requests.auth import HTTPBasicAuth
import json
import time
import os
from typing import Dict, List, Optional, Any
from functools import wraps
from datetime import datetime, timezone, timedelta

from .wq_exceptions import (
    WQAPIError,
    WQAuthError,
    WQRateLimitError,
    WQNotFoundError,
    WQServerError,
    WQValidationError,
    WQSimulationError,
)

# 日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# API 配置
DEFAULT_BASE_URL = "https://api.worldquantbrain.com"
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 60

# 中国时区
CN_TIMEZONE = timezone(timedelta(hours=8))


def with_retry(max_retries: int = None, retry_delay: int = None):
    """
    重试装饰器

    自动处理认证过期、限流等可恢复错误
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            retries = max_retries if max_retries is not None else self.max_retries
            delay = retry_delay if retry_delay is not None else self.retry_delay

            last_error = None
            for attempt in range(retries + 1):
                try:
                    return func(self, *args, **kwargs)
                except WQAuthError as e:
                    if attempt < retries:
                        logger.warning(f"认证过期，重新登录 (尝试 {attempt + 1}/{retries})")
                        self._authenticate()
                        continue
                    raise
                except WQRateLimitError as e:
                    if attempt < retries:
                        wait_time = e.retry_after or delay
                        logger.warning(f"触发限流，等待 {wait_time} 秒后重试")
                        time.sleep(wait_time)
                        continue
                    raise
                except WQServerError as e:
                    if attempt < retries:
                        logger.warning(f"服务器错误，等待 {delay} 秒后重试 (尝试 {attempt + 1}/{retries})")
                        time.sleep(delay)
                        continue
                    raise
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    if attempt < retries:
                        logger.warning(f"网络错误: {e}，等待 {delay} 秒后重试")
                        time.sleep(delay)
                        continue
                    raise WQAPIError(f"网络错误: {e}")
                except WQAPIError:
                    raise
                except Exception as e:
                    last_error = e
                    if attempt < retries:
                        logger.warning(f"未知错误: {e}，等待 {delay} 秒后重试")
                        time.sleep(delay)
                        continue

            raise WQAPIError(f"重试失败: {last_error}")
        return wrapper
    return decorator


class WorldQuantBrainAPIClient:
    """
    WorldQuant Brain API 统一客户端

    Features:
    - 统一的 API 入口
    - 自动认证和会话管理
    - 错误处理和重试机制
    - 完整的 API 封装
    """

    def __init__(
        self,
        username: str = None,
        password: str = None,
        credentials_path: str = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: int = DEFAULT_RETRY_DELAY
    ):
        """
        初始化 API 客户端

        Args:
            username: 用户名
            password: 密码
            credentials_path: 凭证文件路径（优先级高于 username/password）
            base_url: API 基础 URL
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # 加载凭证
        if credentials_path:
            username, password = self._load_credentials(credentials_path)

        if not username or not password:
            raise WQAuthError("需要提供用户名和密码，或指定凭证文件路径")

        self.username = username
        self.password = password

        # 初始化会话
        self.session: Optional[requests.Session] = None
        self._authenticate()

    @classmethod
    def from_credentials(cls, credentials_path: str, **kwargs) -> 'WorldQuantBrainAPIClient':
        """
        从凭证文件创建客户端

        Args:
            credentials_path: 凭证文件路径
            **kwargs: 其他参数

        Returns:
            WorldQuantBrainAPIClient 实例
        """
        return cls(credentials_path=credentials_path, **kwargs)

    @staticmethod
    def _load_credentials(credentials_path: str) -> tuple:
        """从文件加载凭证"""
        if not os.path.exists(credentials_path):
            raise WQAuthError(f"凭证文件不存在: {credentials_path}")

        with open(credentials_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        # 支持两种格式：JSON 数组或用户名密码分行
        if content.startswith('['):
            creds = json.loads(content)
            return creds[0], creds[1]
        elif '\n' in content:
            lines = content.split('\n')
            return lines[0].strip(), lines[1].strip()
        else:
            raise WQAuthError("凭证文件格式错误，应为 JSON 数组或用户名密码分行")

    def _authenticate(self) -> None:
        """认证并初始化会话"""
        logger.info("正在连接 WorldQuant Brain...")

        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.username, self.password)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

        response = self.session.post(
            f'{self.base_url}/authentication',
            timeout=self.timeout
        )

        if response.status_code == 401:
            raise WQAuthError("认证失败：用户名或密码错误")
        elif response.status_code not in [200, 201]:
            raise WQAuthError(f"认证失败: {response.text}")

        logger.info("认证成功")

    # ==================== Alpha 操作 ====================

    @with_retry()
    def get_alpha(self, alpha_id: str) -> Dict:
        """
        获取 Alpha 详情

        Args:
            alpha_id: Alpha ID

        Returns:
            Alpha 完整数据

        Raises:
            WQNotFoundError: Alpha 不存在
        """
        response = self.session.get(
            f'{self.base_url}/alphas/{alpha_id}',
            timeout=self.timeout
        )

        if response.status_code == 404:
            raise WQNotFoundError(f"Alpha 不存在: {alpha_id}")
        elif response.status_code == 401:
            raise WQAuthError("会话过期")
        elif response.status_code != 200:
            raise WQAPIError(f"获取 Alpha 失败: {response.text}", response.status_code)

        return response.json()

    @with_retry()
    def get_user_alphas(
        self,
        limit: int = 100,
        offset: int = 0,
        order: str = '-dateCreated',
        status: str = None,
        hidden: bool = False
    ) -> List[Dict]:
        """
        获取用户 Alpha 列表

        Args:
            limit: 返回数量
            offset: 偏移量
            order: 排序方式
            status: 状态过滤
            hidden: 是否包含隐藏的

        Returns:
            Alpha 列表
        """
        params = {
            'limit': limit,
            'offset': offset,
            'order': order,
            'hidden': 'true' if hidden else 'false'
        }

        if status:
            params['status'] = status

        response = self.session.get(
            f'{self.base_url}/users/self/alphas',
            params=params,
            timeout=self.timeout
        )

        if response.status_code == 401:
            raise WQAuthError("会话过期")
        elif response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', self.retry_delay))
            raise WQRateLimitError("请求过于频繁", retry_after=retry_after)
        elif response.status_code != 200:
            raise WQAPIError(f"获取 Alpha 列表失败: {response.text}", response.status_code)

        return response.json().get('results', [])

    @with_retry()
    def submit_alpha(self, alpha_id: str) -> Dict:
        """
        提交 Alpha

        Args:
            alpha_id: Alpha ID

        Returns:
            提交结果
        """
        response = self.session.post(
            f'{self.base_url}/alphas/{alpha_id}/submit',
            timeout=self.timeout
        )

        if response.status_code == 404:
            raise WQNotFoundError(f"Alpha 不存在: {alpha_id}")
        elif response.status_code == 401:
            raise WQAuthError("会话过期")
        elif response.status_code == 400:
            raise WQValidationError(f"提交失败: {response.text}")
        elif response.status_code not in [200, 201]:
            raise WQAPIError(f"提交 Alpha 失败: {response.text}", response.status_code)

        return response.json()

    @with_retry()
    def patch_alpha(self, alpha_id: str, data: Dict) -> Dict:
        """
        更新 Alpha 属性

        Args:
            alpha_id: Alpha ID
            data: 更新数据（如 name, favorite, hidden 等）

        Returns:
            更新后的 Alpha 数据
        """
        response = self.session.patch(
            f'{self.base_url}/alphas/{alpha_id}',
            json=data,
            timeout=self.timeout
        )

        if response.status_code == 404:
            raise WQNotFoundError(f"Alpha 不存在: {alpha_id}")
        elif response.status_code == 401:
            raise WQAuthError("会话过期")
        elif response.status_code != 200:
            raise WQAPIError(f"更新 Alpha 失败: {response.text}", response.status_code)

        return response.json()

    # ==================== 模拟操作 ====================

    @with_retry()
    def create_simulation(
        self,
        expression: str,
        settings: Dict = None,
        wait_for_completion: bool = False,
        max_wait: int = 300
    ) -> Dict:
        """
        创建模拟

        Args:
            expression: Alpha 表达式
            settings: 模拟设置（可选）
            wait_for_completion: 是否等待完成
            max_wait: 最大等待时间（秒）

        Returns:
            模拟结果
        """
        # 默认设置
        default_settings = {
            'instrumentType': 'EQUITY',
            'region': 'USA',
            'universe': 'TOP3000',
            'delay': 1,
            'decay': 0,
            'neutralization': 'INDUSTRY',
            'truncation': 0.08,
            'pasteurization': 'ON',
            'unitHandling': 'VERIFY',
            'nanHandling': 'OFF',
            'language': 'FASTEXPR',
            'visualization': False,
        }

        if settings:
            default_settings.update(settings)

        sim_data = {
            'type': 'REGULAR',
            'settings': default_settings,
            'regular': expression
        }

        response = self.session.post(
            f'{self.base_url}/simulations',
            json=sim_data,
            timeout=self.timeout
        )

        if response.status_code == 401:
            raise WQAuthError("会话过期")
        elif response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', self.retry_delay))
            raise WQRateLimitError("模拟次数超限", retry_after=retry_after)
        elif response.status_code == 400:
            raise WQValidationError(f"模拟参数错误: {response.text}")
        elif response.status_code != 201:
            raise WQAPIError(f"创建模拟失败: {response.text}", response.status_code)

        progress_url = response.headers.get('Location')
        sim_id = progress_url.rstrip('/').split('/')[-1] if progress_url else None

        result = {
            'simulation_id': sim_id,
            'progress_url': progress_url,
            'status': 'pending'
        }

        if wait_for_completion and progress_url:
            return self._wait_for_simulation(progress_url, max_wait)

        return result

    def _wait_for_simulation(self, progress_url: str, max_wait: int = 300) -> Dict:
        """等待模拟完成"""
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = self.session.get(progress_url, timeout=self.timeout)

            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 5))
                time.sleep(min(retry_after, 10))
                continue

            if response.status_code != 200:
                raise WQAPIError(f"获取模拟状态失败: {response.text}")

            data = response.json()
            status = data.get('status')

            if status == 'COMPLETE':
                alpha_id = data.get('alpha')
                return {
                    'status': 'complete',
                    'alpha_id': alpha_id,
                    'simulation_id': data.get('id'),
                    'result': data
                }
            elif status in ['ERROR', 'FAILED']:
                raise WQSimulationError(
                    f"模拟失败: {data.get('message', 'Unknown error')}",
                    alpha_id=data.get('alpha')
                )

            # 等待后重试
            retry_after = response.headers.get('Retry-After', 5)
            time.sleep(float(retry_after))

        raise WQSimulationError(f"模拟超时（{max_wait}秒）")

    @with_retry()
    def get_simulation(self, sim_id: str) -> Dict:
        """获取模拟状态"""
        response = self.session.get(
            f'{self.base_url}/simulations/{sim_id}',
            timeout=self.timeout
        )

        if response.status_code == 404:
            raise WQNotFoundError(f"模拟不存在: {sim_id}")
        elif response.status_code != 200:
            raise WQAPIError(f"获取模拟失败: {response.text}", response.status_code)

        return response.json()

    # ==================== 数据获取 ====================

    @with_retry()
    def get_data_fields(
        self,
        instrument_type: str = 'EQUITY',
        region: str = 'USA',
        delay: int = 1,
        universe: str = 'TOP3000',
        dataset_id: str = None,
        search: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """
        获取数据字段

        Args:
            instrument_type: 工具类型
            region: 地区
            delay: 延迟
            universe: 股票池
            dataset_id: 数据集 ID
            search: 搜索关键词
            limit: 返回数量
            offset: 偏移量

        Returns:
            包含 results 和 count 的字典
        """
        params = {
            'instrumentType': instrument_type,
            'region': region,
            'delay': delay,
            'universe': universe,
            'limit': limit,
            'offset': offset
        }

        if dataset_id:
            params['dataset.id'] = dataset_id
        if search:
            params['search'] = search

        response = self.session.get(
            f'{self.base_url}/data-fields',
            params=params,
            timeout=self.timeout
        )

        if response.status_code != 200:
            raise WQAPIError(f"获取数据字段失败: {response.text}", response.status_code)

        return response.json()

    @with_retry()
    def get_operators(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        获取操作符列表

        Args:
            limit: 返回数量
            offset: 偏移量

        Returns:
            操作符列表
        """
        response = self.session.get(
            f'{self.base_url}/operators',
            params={'limit': limit, 'offset': offset},
            timeout=self.timeout
        )

        if response.status_code != 200:
            raise WQAPIError(f"获取操作符失败: {response.text}", response.status_code)

        data = response.json()
        # 可能是数组或包含 results 的对象
        if isinstance(data, list):
            return data
        return data.get('results', [])

    @with_retry()
    def get_data_sets(
        self,
        instrument_type: str = 'EQUITY',
        region: str = 'USA',
        delay: int = 1,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        获取数据集列表

        Args:
            instrument_type: 工具类型
            region: 地区
            delay: 延迟
            limit: 返回数量
            offset: 偏移量

        Returns:
            数据集列表
        """
        params = {
            'instrumentType': instrument_type,
            'region': region,
            'delay': delay,
            'limit': limit,
            'offset': offset
        }

        response = self.session.get(
            f'{self.base_url}/data-sets',
            params=params,
            timeout=self.timeout
        )

        if response.status_code != 200:
            raise WQAPIError(f"获取数据集失败: {response.text}", response.status_code)

        data = response.json()
        return data.get('results', [])

    # ==================== 高级功能 ====================

    @with_retry()
    def get_alpha_pnl(self, alpha_id: str) -> Dict:
        """获取 Alpha PnL 数据"""
        response = self.session.get(
            f'{self.base_url}/alphas/{alpha_id}/recordsets/pnl',
            timeout=self.timeout
        )

        if response.status_code == 404:
            raise WQNotFoundError(f"Alpha 或 PnL 数据不存在: {alpha_id}")
        elif response.status_code != 200:
            raise WQAPIError(f"获取 PnL 失败: {response.text}", response.status_code)

        return response.json()

    @with_retry()
    def get_alpha_correlations(self, alpha_id: str, correlation_type: str = 'prod') -> Dict:
        """
        获取 Alpha 相关性

        Args:
            alpha_id: Alpha ID
            correlation_type: 相关性类型 (prod, power-pool)

        Returns:
            相关性数据
        """
        response = self.session.get(
            f'{self.base_url}/alphas/{alpha_id}/correlations/{correlation_type}',
            timeout=self.timeout
        )

        if response.status_code == 404:
            raise WQNotFoundError(f"相关性数据不存在: {alpha_id}")
        elif response.status_code != 200:
            raise WQAPIError(f"获取相关性失败: {response.text}", response.status_code)

        return response.json()

    @with_retry()
    def check_alpha(self, alpha_id: str) -> Dict:
        """
        检查 Alpha 提交状态

        Args:
            alpha_id: Alpha ID

        Returns:
            检查结果
        """
        response = self.session.get(
            f'{self.base_url}/alphas/{alpha_id}/check',
            timeout=self.timeout
        )

        if response.status_code == 404:
            raise WQNotFoundError(f"Alpha 不存在: {alpha_id}")
        elif response.status_code != 200:
            raise WQAPIError(f"检查 Alpha 失败: {response.text}", response.status_code)

        return response.json()

    # ==================== 工具方法 ====================

    def test_connection(self) -> bool:
        """测试连接是否正常"""
        try:
            self.get_operators(limit=1)
            return True
        except Exception:
            return False

    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()
            self.session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 向后兼容别名
WorldQuantBrain = WorldQuantBrainAPIClient


# 操作符常量（向后兼容）
ARSENAL_OPS = [
    "ts_moment", "ts_entropy", "ts_min_max_cps", "ts_min_max_diff",
    "inst_tvr", "sigmoid", "ts_decay_exp_window", "ts_percentage",
    "vector_neut", "vector_proj", "signed_power"
]

GROUP_OPS = [
    "group_rank", "group_sum", "group_max", "group_mean",
    "group_median", "group_min", "group_std_dev"
]

TWIN_FIELD_OPS = [
    "ts_corr", "ts_covariance", "ts_co_kurtosis",
    "ts_co_skewness", "ts_theilsen"
]
