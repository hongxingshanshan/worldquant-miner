"""
WorldQuant Brain API 客户端

从 machine_lib.py 拆分出来，包含：
- WorldQuantBrain 类（API 认证和调用）
- 模拟、提交、检查等功能
"""
import requests
import json
import time
import re
from time import sleep
from typing import Dict, List, Optional, Tuple
import pandas as pd

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class WorldQuantBrainAPIClient:
    """WorldQuant Brain API 客户端

    负责：
    - 认证和会话管理
    - Alpha 模拟
    - Alpha 提交检查
    - 数据字段获取
    """

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = None
        self.login()

    def login(self) -> requests.Session:
        """初始化或刷新 WorldQuant Brain 会话"""
        logger.info("正在连接 WorldQuant Brain...")
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        response = self.session.post('https://api.worldquantbrain.com/authentication')

        if response.status_code != 201:
            raise Exception(f"认证失败: {response.text}")

        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        logger.info("认证成功")
        return self.session

    def simulate_alpha(self, alpha: str, settings: Dict) -> Dict:
        """提交单个 Alpha 进行模拟

        Args:
            alpha: Alpha 表达式
            settings: 模拟设置（region, universe, decay 等）

        Returns:
            模拟结果或错误信息
        """
        sim_data = {
            'type': 'REGULAR',
            'settings': {
                'instrumentType': 'EQUITY',
                'region': settings.get('region', 'USA'),
                'universe': settings.get('universe', 'TOP3000'),
                'delay': settings.get('delay', 1),
                'decay': settings.get('decay', 0),
                'neutralization': settings.get('neutralization', 'MARKET'),
                'truncation': settings.get('truncation', 0.08),
                'pasteurization': 'ON',
                'unitHandling': 'VERIFY',
                'nanHandling': 'OFF',
                'language': 'FASTEXPR',
                'visualization': False,
            },
            'regular': alpha
        }

        try:
            response = self.session.post(
                'https://api.worldquantbrain.com/simulations',
                json=sim_data
            )

            if response.status_code == 401:
                logger.info("会话过期，重新认证...")
                self.login()
                response = self.session.post(
                    'https://api.worldquantbrain.com/simulations',
                    json=sim_data
                )

            if response.status_code == 201:
                progress_url = response.headers.get('Location')
                return {
                    'status': 'success',
                    'progress_url': progress_url,
                    'result': response.json()
                }
            else:
                return {
                    'status': 'error',
                    'message': response.text,
                    'code': response.status_code
                }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def get_simulation_result(self, progress_url: str) -> Dict:
        """获取模拟结果

        Args:
            progress_url: 模拟进度 URL

        Returns:
            模拟结果
        """
        try:
            while True:
                response = self.session.get(progress_url)
                retry_after = response.headers.get("Retry-After", 0)

                if not retry_after:
                    result = response.json()
                    status = result.get("status")

                    if status == "COMPLETE":
                        return {'status': 'complete', 'result': result}
                    elif status in ["FAILED", "ERROR"]:
                        return {'status': 'failed', 'message': result.get("message", "")}
                    else:
                        return {'status': 'unknown', 'result': result}

                sleep(float(retry_after))

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_alpha_details(self, alpha_id: str) -> Dict:
        """获取 Alpha 详情

        Args:
            alpha_id: Alpha ID

        Returns:
            Alpha 详情数据
        """
        try:
            response = self.session.get(f"https://api.worldquantbrain.com/alphas/{alpha_id}")
            if response.status_code == 200:
                return response.json()
            return {'error': f"状态码: {response.status_code}"}
        except Exception as e:
            return {'error': str(e)}

    def check_alpha_submission(self, alpha_id: str) -> Dict:
        """检查 Alpha 提交状态

        Args:
            alpha_id: Alpha ID

        Returns:
            检查结果
        """
        while True:
            result = self.session.get(f"https://api.worldquantbrain.com/alphas/{alpha_id}/check")
            if "retry-after" in result.headers:
                time.sleep(float(result.headers["Retry-After"]))
            else:
                break

        try:
            data = result.json()
            if data.get("is", 0) == 0:
                return {'status': 'logged_out'}

            checks_df = pd.DataFrame(data["is"]["checks"])
            pc = checks_df[checks_df.name == "PROD_CORRELATION"]["value"].values[0]

            if not any(checks_df["result"] == "FAIL"):
                return {'status': 'pass', 'correlation': pc}
            else:
                return {'status': 'fail', 'correlation': pc}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_data_fields(self,
                       instrument_type: str = 'EQUITY',
                       region: str = 'USA',
                       delay: int = 1,
                       universe: str = 'TOP3000',
                       dataset_id: str = '',
                       search: str = '') -> pd.DataFrame:
        """获取数据字段列表

        Args:
            instrument_type: 工具类型
            region: 地区
            delay: 延迟
            universe: 股票池
            dataset_id: 数据集 ID
            search: 搜索关键词

        Returns:
            数据字段 DataFrame
        """
        if search:
            url_template = (
                "https://api.worldquantbrain.com/data-fields?"
                f"&instrumentType={instrument_type}"
                f"&region={region}&delay={str(delay)}&universe={universe}&limit=50"
                f"&search={search}"
                "&offset={x}"
            )
            count = 100
        else:
            url_template = (
                "https://api.worldquantbrain.com/data-fields?"
                f"&instrumentType={instrument_type}"
                f"&region={region}&delay={str(delay)}&universe={universe}&dataset.id={dataset_id}&limit=50"
                "&offset={x}"
            )
            count = self.session.get(url_template.format(x=0)).json()['count']

        datafields_list = []
        for x in range(0, count, 50):
            datafields = self.session.get(url_template.format(x=x))
            datafields_list.append(datafields.json()['results'])

        datafields_list_flat = [item for sublist in datafields_list for item in sublist]
        return pd.DataFrame(datafields_list_flat)

    def get_user_alphas(self,
                       start_date: str,
                       end_date: str,
                       sharpe_th: float = 1.0,
                       fitness_th: float = 0.5,
                       region: str = 'USA',
                       limit: int = 500) -> List[Dict]:
        """获取用户 Alpha 列表

        Args:
            start_date: 开始日期
            end_date: 结束日期
            sharpe_th: Sharpe 阈值
            fitness_th: Fitness 阈值
            region: 地区
            limit: 数量限制

        Returns:
            Alpha 列表
        """
        alphas = []
        for i in range(0, limit, 100):
            url = (
                f"https://api.worldquantbrain.com/users/self/alphas?limit=100&offset={i}"
                f"&status=UNSUBMITTED&dateCreated%3E=2025-{start_date}T00:00:00-04:00"
                f"&dateCreated%3C2025-{end_date}T00:00:00-04:00"
                f"&is.fitness%3E{fitness_th}&is.sharpe%3E{sharpe_th}"
                f"&settings.region={region}&order=-is.sharpe&hidden=false&type!=SUPER"
            )

            try:
                response = self.session.get(url)
                alpha_list = response.json().get("results", [])
                alphas.extend(alpha_list)
            except Exception as e:
                logger.error(f"获取 Alpha 列表失败: {e}")
                self.login()

        return alphas


# 保持向后兼容的别名
WorldQuantBrain = WorldQuantBrainAPIClient
