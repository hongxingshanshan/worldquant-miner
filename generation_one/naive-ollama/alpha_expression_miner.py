#!/usr/bin/env python3
"""
Alpha Expression Miner

合并自:
- alpha_expression_miner.py (核心类)
- alpha_expression_miner_continuous.py (持续运行模式)

提供两种运行模式:
1. 单次模式 - 处理单个表达式
2. 持续模式 - 定期从 hopeful_alphas.json 读取并处理
"""

import argparse
import requests
import json
import os
import re
import time
import shutil
from time import sleep
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Optional
from itertools import product

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class AlphaExpressionMiner:
    """Alpha 表达式挖掘器

    负责:
    - 解析 Alpha 表达式中的数值参数
    - 生成参数变化组合
    - 测试每个变体的模拟结果
    """

    def __init__(self, credentials_path: str):
        logger.info("初始化 AlphaExpressionMiner")
        self.sess = requests.Session()
        self.setup_auth(credentials_path)
        self.simulated_file = 'simulated_expressions.json'

    def setup_auth(self, credentials_path: str) -> None:
        """设置 WorldQuant Brain 认证"""
        logger.info(f"从 {credentials_path} 加载凭证")
        with open(credentials_path) as f:
            credentials = json.load(f)

        username, password = credentials
        self.sess.auth = HTTPBasicAuth(username, password)

        logger.info("正在连接 WorldQuant Brain...")
        response = self.sess.post('https://api.worldquantbrain.com/authentication')
        logger.info(f"认证响应状态: {response.status_code}")

        if response.status_code != 201:
            logger.error(f"认证失败: {response.text}")
            raise Exception(f"认证失败: {response.text}")
        logger.info("认证成功")

    def _is_already_simulated(self, expression: str) -> bool:
        """检查表达式是否已经模拟过"""
        if not os.path.exists(self.simulated_file):
            return False

        try:
            with open(self.simulated_file, 'r') as f:
                simulated = json.load(f)
            for entry in simulated:
                if entry.get('expression') == expression:
                    return True
            return False
        except (json.JSONDecodeError, FileNotFoundError):
            return False

    def _record_simulation(self, expression: str, sim_id: str, status: str = "submitted") -> None:
        """记录已提交的模拟"""
        existing = []
        if os.path.exists(self.simulated_file):
            try:
                with open(self.simulated_file, 'r') as f:
                    existing = json.load(f)
            except json.JSONDecodeError:
                pass

        entry = {
            "expression": expression,
            "simulation_id": sim_id,
            "timestamp": int(time.time()),
            "status": status
        }
        existing.append(entry)

        # 限制记录数量
        if len(existing) > 1000:
            existing = existing[-1000:]

        with open(self.simulated_file, 'w') as f:
            json.dump(existing, f, indent=2)

    def parse_expression(self, expression: str) -> List[Dict]:
        """解析 Alpha 表达式中的数值参数"""
        logger.info(f"解析表达式: {expression}")
        parameters = []

        # 匹配数值参数（不在变量名中的数字）
        for match in re.finditer(r'(?<=[,()\s])(-?\d*\.?\d+)(?![a-zA-Z])', expression):
            number_str = match.group()
            try:
                number = float(number_str)
            except ValueError:
                continue

            start_pos = match.start()
            end_pos = match.end()
            parameters.append({
                'value': number,
                'start': start_pos,
                'end': end_pos,
                'context': expression[max(0, start_pos-20):min(len(expression), end_pos+20)],
                'is_integer': number.is_integer()
            })
            logger.debug(f"发现参数: {number} 位置 {start_pos}-{end_pos}")

        logger.info(f"发现 {len(parameters)} 个可变参数")
        return parameters

    def get_user_parameter_selection(self, parameters: List[Dict]) -> List[Dict]:
        """交互式获取用户选择的参数"""
        if not parameters:
            logger.info("表达式中未发现参数")
            return []

        print("\n发现以下参数:")
        for i, param in enumerate(parameters, 1):
            print(f"{i}. 值: {param['value']} | 上下文: ...{param['context']}...")

        while True:
            try:
                selection = input("\n输入要变化的参数编号（逗号分隔，或输入 'all'): ")
                if selection.lower() == 'all':
                    selected_indices = list(range(len(parameters)))
                else:
                    selected_indices = [int(x.strip())-1 for x in selection.split(',')]
                    if not all(0 <= i < len(parameters) for i in selected_indices):
                        raise ValueError("无效的参数编号")
                break
            except ValueError as e:
                print(f"无效输入: {e}. 请重试.")

        return [parameters[i] for i in selected_indices]

    def get_parameter_ranges(self, parameters: List[Dict], auto_mode: bool = False) -> List[Dict]:
        """获取每个参数的范围和步长"""
        for param in parameters:
            if auto_mode:
                # 自动模式使用默认范围
                original_value = param['value']
                if param['is_integer']:
                    range_val = max(1, abs(original_value) * 0.2)
                    min_val = max(1, original_value - range_val)
                    max_val = original_value + range_val
                    step = 1
                else:
                    range_val = abs(original_value) * 0.1
                    min_val = original_value - range_val
                    max_val = original_value + range_val
                    step = range_val / 5

                logger.info(f"自动模式: 参数 {param['value']} -> 范围 [{min_val:.2f}, {max_val:.2f}], 步长 {step:.2f}")
            else:
                # 交互模式
                while True:
                    try:
                        print(f"\n参数: {param['value']} | 上下文: ...{param['context']}...")
                        range_input = input("输入范围（如 '10' 表示 ±10，或 '5,15' 表示 5 到 15): ")
                        if ',' in range_input:
                            min_val, max_val = map(float, range_input.split(','))
                        else:
                            range_val = float(range_input)
                            min_val = param['value'] - range_val
                            max_val = param['value'] + range_val

                        step = float(input("输入步长: "))
                        if step <= 0:
                            raise ValueError("步长必须为正数")
                        if min_val >= max_val:
                            raise ValueError("最小值必须小于最大值")

                        if param['is_integer'] and not step.is_integer():
                            print("警告: 原值为整数，步长将取整")
                            step = round(step)

                        break
                    except ValueError as e:
                        print(f"无效输入: {e}. 请重试.")

            param['min'] = min_val
            param['max'] = max_val
            param['step'] = step

        return parameters

    def generate_variations(self, expression: str, parameters: List[Dict]) -> List[str]:
        """基于参数范围生成表达式变体"""
        logger.info("基于选定参数生成变体")
        variations = []

        # 从后向前排序参数位置
        parameters.sort(reverse=True, key=lambda x: x['start'])

        # 生成所有参数值组合
        param_values = []
        for param in parameters:
            values = []
            current = param['min']
            while current <= param['max']:
                if param['is_integer']:
                    value = str(int(round(current)))
                else:
                    value = f"{current:.10f}".rstrip('0').rstrip('.')
                values.append(value)
                current += param['step']

            # 添加原值（如果未包含）
            original_value = str(int(param['value'])) if param['is_integer'] else f"{param['value']:.10f}".rstrip('0').rstrip('.')
            if original_value not in values:
                values.append(original_value)

            param_values.append(values)

        # 生成所有组合
        for value_combination in product(*param_values):
            new_expr = expression
            for param, value in zip(parameters, value_combination):
                new_expr = new_expr[:param['start']] + value + new_expr[param['end']:]
            variations.append(new_expr)
            logger.debug(f"生成变体: {new_expr}")

        logger.info(f"共生成 {len(variations)} 个变体")
        return variations

    def test_alpha(self, alpha_expression: str, retry_on_limit: bool = True) -> Dict:
        """测试 Alpha 表达式"""
        if self._is_already_simulated(alpha_expression):
            logger.info(f"Alpha 已模拟过，跳过: {alpha_expression[:50]}...")
            return {"status": "skipped", "message": "Alpha 已模拟过"}

        logger.info(f"测试 Alpha: {alpha_expression}")

        simulation_data = {
            'type': 'REGULAR',
            'settings': {
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
            },
            'regular': alpha_expression
        }

        # 处理并发限制，最多重试 3 次
        max_limit_retries = 3
        limit_retry_count = 0

        while limit_retry_count < max_limit_retries:
            try:
                sim_resp = self.sess.post(
                    'https://api.worldquantbrain.com/simulations',
                    json=simulation_data,
                    timeout=30
                )
                logger.info(f"模拟创建响应: {sim_resp.status_code}")
            except requests.exceptions.RequestException as e:
                limit_retry_count += 1
                is_network_error = any(keyword in str(e).lower() for keyword in [
                    'ssl', 'eof', 'protocol', 'proxy', 'connection', 'timeout', 'remote'
                ])
                if is_network_error and limit_retry_count < max_limit_retries:
                    wait_time = 30 * limit_retry_count
                    logger.warning(f"网络错误 (尝试 {limit_retry_count}/{max_limit_retries}): {e}")
                    logger.warning(f"{wait_time}s 后重试...")
                    sleep(wait_time)
                    continue
                else:
                    logger.error(f"模拟创建失败: {e}")
                    return {"status": "error", "message": str(e), "code": "network_error"}

            # 处理 429 并发限制
            if sim_resp.status_code == 429:
                limit_retry_count += 1
                if retry_on_limit and limit_retry_count < max_limit_retries:
                    wait_time = 30 * limit_retry_count
                    logger.warning(f"并发限制 (尝试 {limit_retry_count}/{max_limit_retries}), 等待 {wait_time}s...")
                    sleep(wait_time)
                    continue
                else:
                    logger.error(f"模拟创建失败: {sim_resp.text}")
                    return {"status": "error", "message": sim_resp.text, "code": 429}

            if sim_resp.status_code != 201:
                logger.error(f"模拟创建失败: {sim_resp.text}")
                return {"status": "error", "message": sim_resp.text}

            break

        sim_progress_url = sim_resp.headers.get('location')
        if not sim_progress_url:
            logger.error("响应头中未收到模拟 ID")
            return {"status": "error", "message": "未收到模拟 ID"}

        # 提取模拟 ID 并记录
        sim_id = sim_progress_url.rstrip('/').split('/')[-1]
        self._record_simulation(alpha_expression, sim_id, "submitted")

        logger.info(f"监控模拟: {sim_progress_url}")

        # 监控模拟进度
        retry_count = 0
        max_retries = 3
        max_wait_time = 1200
        start_time = time.time()

        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > max_wait_time:
                logger.error(f"模拟监控超时 ({elapsed_time:.0f}s)")
                return {"status": "error", "message": f"超时 {max_wait_time}s", "code": "timeout"}

            try:
                sim_progress_resp = self.sess.get(sim_progress_url, timeout=30)

                if not sim_progress_resp.text.strip():
                    logger.debug("空响应，模拟仍在初始化...")
                    sleep(10)
                    continue

                try:
                    progress_data = sim_progress_resp.json()
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON 解析失败: {sim_progress_resp.text}")
                    retry_count += 1
                    if retry_count > max_retries:
                        logger.error("JSON 解析重试次数超限")
                        return {"status": "error", "message": "无法解析响应"}
                    sleep(10)
                    continue

                status = progress_data.get("status")
                logger.info(f"模拟状态: {status}")

                if status == "COMPLETE" or status == "WARNING":
                    logger.info("模拟成功完成")
                    return {"status": "success", "result": progress_data}
                elif status in ["FAILED", "ERROR"]:
                    logger.error(f"模拟失败: {progress_data}")
                    return {"status": "error", "message": progress_data}

                sleep(10)

            except requests.exceptions.RequestException as e:
                logger.error(f"请求错误: {str(e)}")
                retry_count += 1
                if retry_count > max_retries:
                    return {"status": "error", "message": f"请求失败"}
                sleep(10)

    def remove_alpha_from_hopeful(self, expression: str, hopeful_file: str = "hopeful_alphas.json") -> bool:
        """从 hopeful_alphas.json 中移除已处理的 Alpha"""
        try:
            if not os.path.exists(hopeful_file):
                logger.warning(f"文件 {hopeful_file} 不存在")
                return False

            # 创建备份
            backup_file = f"{hopeful_file}.backup.{int(time.time())}"
            shutil.copy2(hopeful_file, backup_file)
            logger.debug(f"创建备份: {backup_file}")

            with open(hopeful_file, 'r') as f:
                hopeful_alphas = json.load(f)

            original_count = len(hopeful_alphas)
            remaining_alphas = []

            for alpha in hopeful_alphas:
                if alpha.get('expression') != expression:
                    remaining_alphas.append(alpha)

            removed_count = original_count - len(remaining_alphas)

            if removed_count > 0:
                with open(hopeful_file, 'w') as f:
                    json.dump(remaining_alphas, f, indent=2)
                logger.info(f"从 {hopeful_file} 移除 {removed_count} 个 Alpha")
                return True
            else:
                logger.info(f"未在 {hopeful_file} 中找到匹配的 Alpha")
                return False

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析错误: {e}")
            return False
        except Exception as e:
            logger.error(f"移除 Alpha 失败: {e}")
            return False


class ContinuousAlphaExpressionMiner:
    """持续运行的 Alpha 表达式挖掘器"""

    def __init__(self, credentials_path: str, mining_interval: int = 6):
        self.miner = AlphaExpressionMiner(credentials_path)
        self.mining_interval = mining_interval * 3600  # 小时转秒
        self.hopeful_alphas_file = 'hopeful_alphas.json'

    def get_hopeful_alphas(self) -> List[str]:
        """读取 hopeful_alphas.json"""
        try:
            if os.path.exists(self.hopeful_alphas_file):
                with open(self.hopeful_alphas_file, 'r') as f:
                    data = json.load(f)
                    return data.get('alphas', [])
            else:
                logger.warning(f"文件 {self.hopeful_alphas_file} 不存在")
                return []
        except Exception as e:
            logger.error(f"读取 {self.hopeful_alphas_file} 失败: {e}")
            return []

    def mine_alpha_expression(self, expression: str) -> bool:
        """挖掘单个 Alpha 表达式的变体"""
        try:
            logger.info(f"开始挖掘: {expression}")

            parameters = self.miner.parse_expression(expression)
            if not parameters:
                logger.info(f"未发现参数: {expression}")
                return False

            selected_params = parameters
            logger.info(f"选定 {len(selected_params)} 个参数")

            selected_params = self.miner.get_parameter_ranges(selected_params, auto_mode=True)
            variations = self.miner.generate_variations(expression, selected_params)
            logger.info(f"生成 {len(variations)} 个变体")

            results = []
            total = len(variations)
            for i, var in enumerate(variations, 1):
                logger.info(f"测试变体 {i}/{total}: {var}")
                result = self.miner.test_alpha(var)
                if result["status"] == "success":
                    logger.info(f"成功: {var}")
                    results.append({
                        "expression": var,
                        "result": result["result"]
                    })
                else:
                    logger.error(f"失败: {var} - {result['message']}")

            if results:
                timestamp = int(time.time())
                output_file = f'mined_expressions_{timestamp}.json'
                logger.info(f"保存 {len(results)} 个结果到 {output_file}")
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)

            logger.info("挖掘完成，从 hopeful_alphas.json 移除")
            removed = self.miner.remove_alpha_from_hopeful(expression)
            if removed:
                logger.info(f"成功移除: {expression}")
            else:
                logger.warning(f"移除失败: {expression}")

            return True

        except Exception as e:
            logger.error(f"挖掘错误 {expression}: {e}")
            return False

    def run_continuous_mining(self) -> None:
        """持续运行挖掘"""
        logger.info(f"启动持续挖掘，间隔 {self.mining_interval/3600}h")

        while True:
            try:
                hopeful_alphas = self.get_hopeful_alphas()

                if not hopeful_alphas:
                    logger.info("无待处理 Alpha，等待下一轮...")
                    sleep(self.mining_interval)
                    continue

                logger.info(f"发现 {len(hopeful_alphas)} 个待处理 Alpha")

                for alpha in hopeful_alphas:
                    try:
                        success = self.mine_alpha_expression(alpha)
                        if success:
                            logger.info(f"成功挖掘: {alpha}")
                        else:
                            logger.warning(f"挖掘失败: {alpha}")

                        sleep(10)

                    except Exception as e:
                        logger.error(f"处理 Alpha 错误 {alpha}: {e}")
                        continue

                logger.info(f"本轮完成，等待 {self.mining_interval/3600}h...")
                sleep(self.mining_interval)

            except KeyboardInterrupt:
                logger.info("收到中断信号，停止...")
                break
            except Exception as e:
                logger.error(f"持续挖掘错误: {e}")
                logger.info("5 分钟后重试...")
                sleep(300)


def run_single_mode(args):
    """单次模式运行"""
    logger.info(f"单次模式 - 表达式: {args.expression}")

    miner = AlphaExpressionMiner(args.credentials)
    parameters = miner.parse_expression(args.expression)

    if args.auto_mode:
        selected_params = parameters
        logger.info(f"自动模式: 选定 {len(selected_params)} 个参数")
    else:
        selected_params = miner.get_user_parameter_selection(parameters)

    if not selected_params:
        logger.info("无选定参数")
        miner.remove_alpha_from_hopeful(args.expression)
        return

    selected_params = miner.get_parameter_ranges(selected_params, auto_mode=args.auto_mode)
    variations = miner.generate_variations(args.expression, selected_params)

    results = []
    failed_due_to_limit = False
    total = len(variations)

    for i, var in enumerate(variations, 1):
        logger.info(f"测试变体 {i}/{total}: {var}")
        result = miner.test_alpha(var)
        if result["status"] == "success":
            logger.info(f"成功: {var}")
            results.append({"expression": var, "result": result["result"]})
        else:
            logger.error(f"失败: {var} - {result['message']}")
            if result.get("code") == 429:
                failed_due_to_limit = True
                logger.warning("因并发限制停止")
                break

    output_file = args.output_file
    logger.info(f"保存 {len(results)} 个结果到 {output_file}")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    if failed_due_to_limit:
        logger.warning("因并发限制停止，保留 Alpha 待重试")
    else:
        miner.remove_alpha_from_hopeful(args.expression)

    logger.info("挖掘完成")


def run_continuous_mode(args):
    """持续模式运行"""
    miner = ContinuousAlphaExpressionMiner(
        args.credentials,
        args.mining_interval
    )
    miner.run_continuous_mining()


def main():
    parser = argparse.ArgumentParser(description='Alpha Expression Miner')
    parser.add_argument('--credentials', type=str, default='./credential.txt',
                        help='凭证文件路径')
    parser.add_argument('--mode', choices=['single', 'continuous'], default='single',
                        help='运行模式: single(单次), continuous(持续)')
    parser.add_argument('--expression', type=str,
                        help='单次模式: 要挖掘的表达式')
    parser.add_argument('--output-file', type=str, default='mined_expressions.json',
                        help='输出文件')
    parser.add_argument('--mining-interval', type=int, default=6,
                        help='持续模式: 挖掘间隔（小时）')
    parser.add_argument('--auto-mode', action='store_true',
                        help='自动模式（无需交互）')
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='日志级别')

    args = parser.parse_args()

    logging.getLogger().setLevel(getattr(logging, args.log_level))

    try:
        if args.mode == 'single':
            if not args.expression:
                parser.error("单次模式需要 --expression 参数")
            run_single_mode(args)
        else:
            run_continuous_mode(args)
    except Exception as e:
        logger.error(f"致命错误: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())