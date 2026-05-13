"""
WorldQuant Brain API 客户端（本地业务扩展版）

继承自 common.wq_api_client.WorldQuantBrainAPIClient，
添加 naive-ollama 特有的业务方法。

向后兼容：
- WorldQuantBrain 别名
- 操作符常量
- single_simulate 等业务方法
"""
import time
import re
from time import sleep
from typing import Dict, List, Optional
import pandas as pd

# 导入统一 API 客户端
from common.wq_api_client import WorldQuantBrainAPIClient as BaseClient
from common.wq_exceptions import WQAPIError, WQAuthError

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


class WorldQuantBrainAPIClient(BaseClient):
    """WorldQuant Brain API 客户端（本地业务扩展版）

    继承自统一 API 客户端，添加：
    - 操作符集合管理
    - 单次模拟流程
    - 数据字段处理
    - 向后兼容方法
    """

    def __init__(self, username: str = None, password: str = None,
                 credentials_path: str = None, **kwargs):
        """初始化客户端

        Args:
            username: 用户名
            password: 密码
            credentials_path: 凭证文件路径
            **kwargs: 其他参数传递给基类
        """
        super().__init__(
            username=username,
            password=password,
            credentials_path=credentials_path,
            **kwargs
        )

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

    # ==================== 本地业务方法 ====================

    def single_simulate(self, alpha_data: list, neut: str, region: str, universe: str) -> list:
        """运行单个 Alpha 模拟

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

                # 使用基类的 create_simulation 方法
                sim_result = self.create_simulation(
                    expression=sim_data['regular'],
                    settings=sim_data['settings'],
                    wait_for_completion=True,
                    max_wait=300
                )

                if sim_result.get('status') == 'complete':
                    results.append(sim_result.get('result'))

            except WQAPIError as e:
                logger.error(f"模拟错误: {e}")
                sleep(60)
                continue
            except Exception as e:
                logger.error(f"模拟错误: {str(e)}")
                sleep(60)
                continue

        return results

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
        # 使用基类方法获取数据
        if search:
            result = self.get_data_fields(
                instrument_type=instrument_type,
                region=region,
                delay=delay,
                universe=universe,
                search=search,
                limit=50
            )
            count = result.get('count', 0)
            all_results = result.get('results', [])

            # 分页获取剩余数据
            offset = 50
            while offset < count:
                page_result = self.get_data_fields(
                    instrument_type=instrument_type,
                    region=region,
                    delay=delay,
                    universe=universe,
                    search=search,
                    limit=50,
                    offset=offset
                )
                all_results.extend(page_result.get('results', []))
                offset += 50
        else:
            result = self.get_data_fields(
                instrument_type=instrument_type,
                region=region,
                delay=delay,
                universe=universe,
                dataset_id=dataset_id if dataset_id else None,
                limit=50
            )
            count = result.get('count', 0)
            all_results = result.get('results', [])

            # 分页获取剩余数据
            offset = 50
            while offset < count:
                page_result = self.get_data_fields(
                    instrument_type=instrument_type,
                    region=region,
                    delay=delay,
                    universe=universe,
                    dataset_id=dataset_id if dataset_id else None,
                    limit=50,
                    offset=offset
                )
                all_results.extend(page_result.get('results', []))
                offset += 50

        return pd.DataFrame(all_results)

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

    def _has_inaccessible_operator(self, alpha: str) -> bool:
        """检查 Alpha 是否包含不可访问的操作符"""
        for op in self.inaccessible_ops:
            if op in alpha:
                logger.warning(f"跳过包含不可访问操作符 '{op}' 的 Alpha: {alpha}")
                return True
        return False

    def check_alpha_submission(self, alpha_id: str) -> Dict:
        """检查 Alpha 提交状态

        Args:
            alpha_id: Alpha ID

        Returns:
            检查结果
        """
        try:
            data = self.check_alpha(alpha_id)

            if not data or not data.get('is'):
                return {'status': 'logged_out'}

            checks = data.get('is', {}).get('checks', [])
            checks_df = pd.DataFrame(checks)

            pc = checks_df[checks_df.name == "PROD_CORRELATION"]["value"].values[0] if len(checks_df) > 0 else 0

            if not any(checks_df["result"] == "FAIL"):
                return {'status': 'pass', 'correlation': pc}
            else:
                return {'status': 'fail', 'correlation': pc}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_user_alphas(self,
                       start_date: str,
                       end_date: str,
                       sharpe_th: float = 1.0,
                       fitness_th: float = 0.5,
                       region: str = 'USA',
                       limit: int = 500) -> List[Dict]:
        """获取用户 Alpha 列表（带过滤条件）

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
            try:
                # 使用基类方法，但添加过滤参数
                batch = super().get_user_alphas(
                    limit=100,
                    offset=i,
                    order='-is.sharpe',
                    hidden=False
                )
                alphas.extend(batch)
            except Exception as e:
                logger.error(f"获取 Alpha 列表失败: {e}")

        return alphas


# 保持向后兼容的别名
WorldQuantBrain = WorldQuantBrainAPIClient
