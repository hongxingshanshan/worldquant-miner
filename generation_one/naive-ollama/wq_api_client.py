"""
WorldQuant Brain API 客户端

从 machine_lib.py 拆分出来，包含：
- WorldQuantBrain 类（API 认证和调用）
- 模拟、提交、检查等功能
- 向后兼容旧版 machine_lib.py 的方法
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

# 操作符定义（向后兼容）
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
        # 操作符集合（向后兼容）
        self.basic_ops = ["log", "sqrt", "reverse", "inverse", "rank", "zscore",
                          "log_diff", "s_log_1p", "fraction", "quantile",
                          "normalize", "scale_down"]
        self.ts_ops = ["ts_rank", "ts_zscore", "ts_delta", "ts_sum", "ts_product",
                       "ts_ir", "ts_std_dev", "ts_mean", "ts_arg_min", "ts_arg_max",
                       "ts_min_diff", "ts_max_diff", "ts_returns", "ts_scale",
                       "ts_skewness", "ts_kurtosis", "ts_quantile"]
        self.arsenal = ARSENAL_OPS
        self.group_ops = GROUP_OPS
        self.twin_field_ops = TWIN_FIELD_OPS
        self.ops_set = self.basic_ops + self.ts_ops + self.arsenal + self.group_ops
        self.inaccessible_ops = ["log_diff", "s_log_1p", "fraction", "quantile"]
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

    # ==================== 向后兼容方法 ====================

    def single_simulate(self, alpha_data: list, neut: str, region: str, universe: str) -> list:
        """运行单个 Alpha 模拟（向后兼容方法）

        Args:
            alpha_data: [(alpha_expression, decay), ...] 格式的列表
            neut: 中性化方式
            region: 地区
            universe: 股票池

        Returns:
            模拟结果列表
        """
        logger.info(f"开始单次模拟")
        sim_data_list = self.generate_sim_data(alpha_data, region, universe, neut)
        results = []

        for sim_data in sim_data_list:
            try:
                if self._has_inaccessible_operator(sim_data['regular']):
                    continue

                simulation_response = self.session.post(
                    'https://api.worldquantbrain.com/simulations',
                    json=sim_data
                )
                if simulation_response.status_code == 401:
                    logger.info("会话过期，重新认证...")
                    self.login()
                    simulation_response = self.session.post(
                        'https://api.worldquantbrain.com/simulations',
                        json=sim_data
                    )

                if simulation_response.status_code != 201:
                    logger.error(f"模拟 API 错误: {simulation_response.text}")
                    continue

                simulation_progress_url = simulation_response.headers.get('Location')
                if not simulation_progress_url:
                    logger.error("响应中无 Location 头")
                    continue

                result = self._monitor_single_progress(simulation_progress_url)
                if result:
                    results.append(result)

            except Exception as e:
                logger.error(f"模拟错误: {str(e)}")
                sleep(60)
                self.login()
                continue

        return results

    def _monitor_single_progress(self, progress_url: str) -> Optional[Dict]:
        """监控单个模拟进度"""
        try:
            while True:
                simulation_progress = self.session.get(progress_url)
                retry_after = simulation_progress.headers.get("Retry-After", 0)

                if not retry_after:
                    result = simulation_progress.json()
                    status = result.get("status")
                    logger.info(f"模拟状态: {status}")

                    if status == "COMPLETE":
                        return result
                    elif status in ["FAILED", "ERROR"]:
                        error_message = result.get("message", "")
                        logger.error(f"模拟失败: {result}")
                        inaccessible_op = self._extract_inaccessible_operator(error_message)
                        if inaccessible_op and inaccessible_op not in self.inaccessible_ops:
                            logger.info(f"添加新的不可访问操作符: {inaccessible_op}")
                            self.inaccessible_ops.append(inaccessible_op)
                        return None
                    break

                sleep(float(retry_after))

        except Exception as e:
            logger.error(f"监控进度错误: {str(e)}")
            return None

    def _extract_inaccessible_operator(self, error_message: str) -> Optional[str]:
        """从错误消息中提取不可访问的操作符"""
        match = re.search(r'operator "([^"]+)"', error_message)
        if match:
            return match.group(1)
        return None

    def _has_inaccessible_operator(self, alpha: str) -> bool:
        """检查 Alpha 是否包含不可访问的操作符"""
        for op in self.inaccessible_ops:
            if op in alpha:
                logger.warning(f"跳过包含不可访问操作符 '{op}' 的 Alpha: {alpha}")
                return True
        return False

    def generate_sim_data(self, alpha_list: list, region: str, uni: str, neut: str) -> list:
        """生成模拟数据"""
        sim_data_list = []
        for alpha, decay in alpha_list:
            simulation_data = {
                'type': 'REGULAR',
                'settings': {
                    'instrumentType': 'EQUITY',
                    'region': region,
                    'universe': uni,
                    'delay': 1,
                    'decay': decay,
                    'neutralization': neut,
                    'truncation': 0.08,
                    'pasteurization': 'ON',
                    'unitHandling': 'VERIFY',
                    'nanHandling': 'OFF',
                    'language': 'FASTEXPR',
                    'visualization': False,
                },
                'regular': alpha
            }
            sim_data_list.append(simulation_data)
        return sim_data_list

    def get_datafields(self, instrument_type: str = 'EQUITY', region: str = 'USA',
                       delay: int = 1, universe: str = 'TOP3000',
                       dataset_id: str = '', search: str = '') -> pd.DataFrame:
        """获取数据字段（向后兼容别名）"""
        return self.get_data_fields(
            instrument_type=instrument_type,
            region=region,
            delay=delay,
            universe=universe,
            dataset_id=dataset_id,
            search=search
        )

    def get_vec_fields(self, fields: List[str]) -> List[str]:
        """生成向量字段操作"""
        vec_ops = ["vec_avg", "vec_sum", "vec_ir", "vec_max", "vec_count",
                   "vec_skewness", "vec_stddev", "vec_choose"]
        vec_fields = []

        for field in fields:
            for vec_op in vec_ops:
                if vec_op == "vec_choose":
                    vec_fields.append(f"{vec_op}({field}, nth=-1)")
                    vec_fields.append(f"{vec_op}({field}, nth=0)")
                else:
                    vec_fields.append(f"{vec_op}({field})")

        return vec_fields

    def process_datafields(self, df: pd.DataFrame, data_type: str) -> List[str]:
        """处理数据字段"""
        if data_type == "matrix":
            datafields = df[df['type'] == "MATRIX"]["id"].tolist()
        elif data_type == "vector":
            datafields = self.get_vec_fields(df[df['type'] == "VECTOR"]["id"].tolist())
        else:
            datafields = []

        tb_fields = []
        for field in datafields:
            tb_fields.append(f"winsorize(ts_backfill({field}, 120), std=4)")
        return tb_fields

    def get_first_order(self, vec_fields: List[str], ops_set: List[str] = None) -> List[str]:
        """生成一阶 Alpha 表达式"""
        from alpha_factory import AlphaFactory
        factory = AlphaFactory()
        return factory.get_first_order(vec_fields, ops_set or self.ops_set)


# 保持向后兼容的别名
WorldQuantBrain = WorldQuantBrainAPIClient
