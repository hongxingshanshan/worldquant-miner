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
arsenal = ARSENAL_OPS if MODULES_AVAILABLE else [
    "ts_moment", "ts_entropy", "ts_min_max_cps", "ts_min_max_diff",
    "inst_tvr", "sigmoid", "ts_decay_exp_window", "ts_percentage",
    "vector_neut", "vector_proj", "signed_power"
]

group_ops = GROUP_OPS if MODULES_AVAILABLE else [
    "group_rank", "group_sum", "group_max", "group_mean",
    "group_median", "group_min", "group_std_dev"
]

twin_field_ops = TWIN_FIELD_OPS if MODULES_AVAILABLE else [
    "ts_corr", "ts_covariance", "ts_co_kurtosis",
    "ts_co_skewness", "ts_theilsen"
]


# 如果模块不可用，提供回退实现
if not MODULES_AVAILABLE:
    logger.warning("拆分模块不可用，使用内置实现")

    import requests
    from time import sleep
    import json
    import time
    import pandas as pd
    import random
    import pickle
    from itertools import product
    from collections import defaultdict
    import re

    class WorldQuantBrain:
        """WorldQuant Brain API 客户端（回退实现）"""

        def __init__(self, username: str, password: str):
            self.username = username
            self.password = password
            self.session = None
            self.basic_ops = ["log", "sqrt", "reverse", "inverse", "rank", "zscore",
                              "log_diff", "s_log_1p", "fraction", "quantile",
                              "normalize", "scale_down"]
            self.ts_ops = ["ts_rank", "ts_zscore", "ts_delta", "ts_sum", "ts_product",
                           "ts_ir", "ts_std_dev", "ts_mean", "ts_arg_min", "ts_arg_max",
                           "ts_min_diff", "ts_max_diff", "ts_returns", "ts_scale",
                           "ts_skewness", "ts_kurtosis", "ts_quantile"]
            self.ops_set = self.basic_ops + self.ts_ops + arsenal + group_ops
            self.inaccessible_ops = ["log_diff", "s_log_1p", "fraction", "quantile"]
            self.login()

        def login(self):
            logger.info("Authenticating with WorldQuant Brain...")
            self.session = requests.Session()
            self.session.auth = (self.username, self.password)
            response = self.session.post('https://api.worldquantbrain.com/authentication')

            if response.status_code != 201:
                raise Exception(f"Authentication failed: {response.text}")

            self.session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            logger.info("Authentication successful")
            return self.session

        def single_simulate(self, alpha_data: list, neut: str, region: str, universe: str) -> dict:
            """Run a single alpha simulation."""
            logger.info(f"Starting single simulation for alpha")
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
                        logger.info("Session expired, re-authenticating...")
                        self.login()
                        simulation_response = self.session.post(
                            'https://api.worldquantbrain.com/simulations',
                            json=sim_data
                        )

                    if simulation_response.status_code != 201:
                        logger.error(f"Simulation API error: {simulation_response.text}")
                        continue

                    simulation_progress_url = simulation_response.headers.get('Location')
                    if not simulation_progress_url:
                        logger.error("No Location header in response")
                        continue

                    result = self._monitor_single_progress(simulation_progress_url)
                    if result:
                        results.append(result)

                except Exception as e:
                    logger.error(f"Error in simulation: {str(e)}")
                    sleep(60)
                    self.login()
                    continue

            return results

        def _monitor_single_progress(self, progress_url: str) -> dict:
            try:
                while True:
                    simulation_progress = self.session.get(progress_url)
                    retry_after = simulation_progress.headers.get("Retry-After", 0)

                    if not retry_after:
                        result = simulation_progress.json()
                        status = result.get("status")
                        logger.info(f"Simulation status: {status}")

                        if status == "COMPLETE":
                            return result
                        elif status in ["FAILED", "ERROR"]:
                            error_message = result.get("message", "")
                            logger.error(f"Simulation failed: {result}")
                            inaccessible_op = self._extract_inaccessible_operator(error_message)
                            if inaccessible_op and inaccessible_op not in self.inaccessible_ops:
                                logger.info(f"Adding new inaccessible operator: {inaccessible_op}")
                                self.inaccessible_ops.append(inaccessible_op)
                            return None
                        break

                    sleep(float(retry_after))

            except Exception as e:
                logger.error(f"Error monitoring progress: {str(e)}")
                return None

        def _extract_inaccessible_operator(self, error_message: str) -> str:
            match = re.search(r'operator "([^"]+)"', error_message)
            if match:
                return match.group(1)
            return None

        def _has_inaccessible_operator(self, alpha: str) -> bool:
            for op in self.inaccessible_ops:
                if op in alpha:
                    logger.warning(f"Skipping alpha with inaccessible operator '{op}': {alpha}")
                    return True
            return False

        def generate_sim_data(self, alpha_list, region, uni, neut):
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

        def locate_alpha(self, alpha_id):
            alpha = self.session.get("https://api.worldquantbrain.com/alphas/" + alpha_id)
            string = alpha.content.decode('utf-8')
            metrics = json.loads(string)
            dateCreated = metrics["dateCreated"]
            sharpe = metrics["is"]["sharpe"]
            fitness = metrics["is"]["fitness"]
            turnover = metrics["is"]["turnover"]
            margin = metrics["is"]["margin"]
            triple = [sharpe, fitness, turnover, margin, dateCreated]
            return triple

        def get_datafields(self, instrument_type='EQUITY', region='USA',
                          delay=1, universe='TOP3000', dataset_id='', search=''):
            if len(search) == 0:
                url_template = (
                    "https://api.worldquantbrain.com/data-fields?"
                    f"&instrumentType={instrument_type}"
                    f"&region={region}&delay={str(delay)}&universe={universe}&dataset.id={dataset_id}&limit=50"
                    "&offset={x}"
                )
                count = self.session.get(url_template.format(x=0)).json()['count']
            else:
                url_template = (
                    "https://api.worldquantbrain.com/data-fields?"
                    f"&instrumentType={instrument_type}"
                    f"&region={region}&delay={str(delay)}&universe={universe}&limit=50"
                    f"&search={search}"
                    "&offset={x}"
                )
                count = 100

            datafields_list = []
            for x in range(0, count, 50):
                datafields = self.session.get(url_template.format(x=x))
                datafields_list.append(datafields.json()['results'])

            datafields_list_flat = [item for sublist in datafields_list for item in sublist]
            return pd.DataFrame(datafields_list_flat)


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
