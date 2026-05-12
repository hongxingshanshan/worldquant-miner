import argparse
import requests
import json
import os
from time import sleep
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Optional
import time
import re
import logging
import logging.handlers
from queue import Queue
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import sys
import ctypes
import signal
import atexit
import queue
import logging

# 尝试导入配置管理器
try:
    from config_manager import get_config_manager, ConfigManager
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

# 尝试导入统一 LLM 客户端
try:
    from llm_client import LLMClient
    LLM_CLIENT_AVAILABLE = True
except ImportError:
    LLM_CLIENT_AVAILABLE = False

# 尝试导入优化器和队列
try:
    from alpha_optimizer import AlphaOptimizer
    from alpha_queue import AlphaQueue
    OPTIMIZER_AVAILABLE = True
except ImportError:
    OPTIMIZER_AVAILABLE = False

# 导入拆分出的模块
try:
    from alpha_patterns import (
        load_successful_patterns, load_submitted_alphas, load_knowledge_base,
        extract_key_sections, get_sampled_field_ids, load_data_fields_reference,
        get_random_strategy_hints, get_random_example_format,
        KNOWLEDGE_BASE_PATH, SUCCESSFUL_PATTERNS_FILE, SUBMITTED_ALPHAS_CACHE
    )
    ALPHA_PATTERNS_AVAILABLE = True
except ImportError:
    ALPHA_PATTERNS_AVAILABLE = False

try:
    from alpha_simulator import RetryQueue, AlphaConsumer
    ALPHA_SIMULATOR_AVAILABLE = True
except ImportError:
    ALPHA_SIMULATOR_AVAILABLE = False

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

# 知识库路径（如果 alpha_patterns 模块不可用，使用后备值）
if not ALPHA_PATTERNS_AVAILABLE:
    KNOWLEDGE_BASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                        'knowledge_base')
    SUCCESSFUL_PATTERNS_FILE = "successful_patterns.json"
    SUBMITTED_ALPHAS_CACHE = "submitted_alphas_cache.json"


# 后备函数定义（当 alpha_patterns 模块不可用时）
if not ALPHA_PATTERNS_AVAILABLE:
    def load_successful_patterns(max_patterns: int = 20, randomize: bool = True) -> List[Dict]:
        """加载成功的 alpha 模式（后备版本）"""
        return []

    def load_submitted_alphas(sess, max_alphas: int = 20) -> List[Dict]:
        """从 WorldQuant Brain API 获取已提交的 alpha（后备版本）"""
        return []

    def load_knowledge_base(randomize: bool = True) -> str:
        """加载知识库（后备版本）"""
        return ""

    def load_data_fields_reference(max_fields: int = 80, randomize: bool = True) -> str:
        """加载数据字段参考（后备版本）"""
        return ""

    def get_random_strategy_hints() -> str:
        """获取随机策略提示（后备版本）"""
        return ""

    def get_random_example_format() -> str:
        """获取随机示例格式（后备版本）"""
        return ""


# 后备类定义（当 alpha_simulator 模块不可用时）
if not ALPHA_SIMULATOR_AVAILABLE:
    class RetryQueue:
        """重试队列（后备版本）"""
        def __init__(self, generator, max_retries=3, retry_delay=60):
            self.queue = Queue()
            self.max_retries = max_retries
            self.retry_delay = retry_delay
            self.generator = generator

        def add(self, alpha: str, retry_count: int = 0):
            self.queue.put((alpha, retry_count))

    class AlphaConsumer(Thread):
        """消费者线程（后备版本）"""
        def __init__(self, generator, check_interval: int = 5, batch_size: int = 10):
            super().__init__(daemon=True)
            self.generator = generator
            self.running = True

        def run(self):
            pass

        def stop(self):
            self.running = False


class AlphaGenerator:
    def __init__(self, credentials_path: str = "credential.txt", ollama_url: str = "http://localhost:11434", max_concurrent: int = 2, config_path: str = "config.json"):
        self.sess = requests.Session()
        self.credentials_path = credentials_path  # Store path for reauth
        self.setup_auth(credentials_path)
        self.ollama_url = ollama_url
        self.results = []
        self.pending_results = {}
        self.retry_queue = RetryQueue(self)
        # Reduce concurrent workers to prevent VRAM issues
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)  # For concurrent simulations
        self.vram_cleanup_interval = 10  # Cleanup every 10 operations
        self.operation_count = 0
        self.config_path = config_path

        # 初始化统一 LLM 客户端
        self.llm_client = None
        if LLM_CLIENT_AVAILABLE:
            try:
                self.llm_client = LLMClient(config_path)
                logger.info(f"LLM 客户端初始化成功 - 提供商: {self.llm_client.get_provider()}, 模型: {self.llm_client.get_model_name()}")
            except Exception as e:
                logger.warning(f"LLM 客户端初始化失败: {e}")

        # 初始化优化器和队列
        self.optimizer = None
        self.alpha_queue = None
        self.optimization_enabled = False
        self.consumer_thread = None  # 消费者线程

        logger.info(f"OPTIMIZER_AVAILABLE: {OPTIMIZER_AVAILABLE}, llm_client: {self.llm_client is not None}")

        if OPTIMIZER_AVAILABLE and self.llm_client:
            try:
                self.optimizer = AlphaOptimizer(self.llm_client)
                self.alpha_queue = AlphaQueue()
                logger.info(f"✅ AlphaQueue 初始化成功, self.alpha_queue = {self.alpha_queue}, id(self) = {id(self)}")
                # 从配置加载优化设置
                self._load_optimization_config()
                logger.info(f"优化器初始化成功 - 启用: {self.optimization_enabled}")
            except Exception as e:
                logger.warning(f"优化器初始化失败: {e}")
                import traceback
                logger.warning(traceback.format_exc())
        else:
            logger.warning(f"优化器未初始化: OPTIMIZER_AVAILABLE={OPTIMIZER_AVAILABLE}, llm_client={self.llm_client is not None}")

        # 从配置文件加载模型舰队
        self.model_fleet = self._load_model_fleet()
        self.initial_model = getattr(self, 'model_name', self.model_fleet[0] if self.model_fleet else 'llama3:8b')
        self.error_count = 0
        self.max_errors_before_downgrade = 3
        self.current_model_index = 0

    def _load_model_fleet(self) -> List[str]:
        """从配置文件加载模型舰队"""
        # 尝试从配置管理器加载
        if CONFIG_AVAILABLE:
            try:
                config_manager = get_config_manager(self.config_path)
                return config_manager.get_model_fleet_names()
            except Exception as e:
                logger.warning(f"从配置管理器加载模型舰队失败: {e}")

        # 尝试直接读取配置文件
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    fleet_data = data.get('model_fleet', [])
                    if fleet_data:
                        return [m.get('name') for m in fleet_data if m.get('name')]
            except Exception as e:
                logger.warning(f"读取配置文件失败: {e}")

        # 使用默认值
        logger.info("使用默认模型舰队配置")
        return ['llama3:8b', 'qwen2.5-coder:1.5b']

    def _load_optimization_config(self):
        """加载优化配置"""
        # 默认配置
        self.optimization_config = {
            'enabled': True,
            'min_sharpe': 1.0,
            'optimize_per_cycle': 20,
            'generate_per_cycle': 20,
            'temperature': 0.5
        }

        # 从配置文件加载
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    opt_config = data.get('optimization', {})
                    if opt_config:
                        self.optimization_config.update(opt_config)
            except Exception as e:
                logger.warning(f"加载优化配置失败: {e}")

        self.optimization_enabled = self.optimization_config.get('enabled', True)
        logger.info(f"优化配置: {self.optimization_config}")

        
    def setup_auth(self, credentials_path: str) -> None:
        """Set up authentication with WorldQuant Brain."""
        logger.info(f"Loading credentials from {credentials_path}")
        with open(credentials_path) as f:
            credentials = json.load(f)
        
        username, password = credentials
        self.sess.auth = HTTPBasicAuth(username, password)
        
        logger.info("Authenticating with WorldQuant Brain...")
        response = self.sess.post('https://api.worldquantbrain.com/authentication', timeout=30)
        logger.info(f"Authentication response status: {response.status_code}")
        logger.debug(f"Authentication response: {response.text[:500]}...")
        
        if response.status_code != 201:
            raise Exception(f"Authentication failed: {response.text}")

    def start_consumer_thread(self, check_interval: int = 5, batch_size: int = 10):
        """启动消费者线程

        Args:
            check_interval: 检查队列的间隔（秒）
            batch_size: 每次批量提交的数量
        """
        if self.consumer_thread and self.consumer_thread.is_alive():
            logger.warning("消费者线程已在运行")
            return

        self.consumer_thread = AlphaConsumer(
            generator=self,
            check_interval=check_interval,
            batch_size=batch_size
        )
        self.consumer_thread.start()
        logger.info("消费者线程已启动")

    def stop_consumer_thread(self):
        """停止消费者线程"""
        if self.consumer_thread:
            self.consumer_thread.stop()
            self.consumer_thread.join(timeout=10)
            logger.info("消费者线程已停止")

    def cleanup_vram(self):
        """Perform VRAM cleanup by forcing garbage collection and waiting."""
        try:
            import gc
            gc.collect()
            logger.info("Performed VRAM cleanup")
            # Add a small delay to allow GPU memory to be freed
            time.sleep(2)
        except Exception as e:
            logger.warning(f"VRAM cleanup failed: {e}")

    def get_data_fields_from_local(self) -> List[Dict]:
        """从本地知识库加载数据字段"""
        knowledge_base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'knowledge_base')
        data_fields_file = os.path.join(knowledge_base_path, 'worldquant_data_fields.json')

        if os.path.exists(data_fields_file):
            try:
                with open(data_fields_file, 'r', encoding='utf-8') as f:
                    data_fields = json.load(f)
                logger.info(f"[数据字段] 从本地知识库加载成功，共 {len(data_fields)} 个字段")
                return data_fields
            except Exception as e:
                logger.warning(f"[数据字段] 本地加载失败: {e}，将尝试从 API 获取")
                return None
        else:
            logger.warning(f"[数据字段] 知识库文件不存在: {data_fields_file}")
            return None

    def get_operators_from_local(self) -> List[Dict]:
        """从本地知识库加载操作符"""
        knowledge_base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'knowledge_base')
        operators_file = os.path.join(knowledge_base_path, 'worldquant_operators.json')

        if os.path.exists(operators_file):
            try:
                with open(operators_file, 'r', encoding='utf-8') as f:
                    operators = json.load(f)
                logger.info(f"[操作符] 从本地知识库加载成功，共 {len(operators)} 个操作符")
                return operators
            except Exception as e:
                logger.warning(f"[操作符] 本地加载失败: {e}，将尝试从 API 获取")
                return None
        else:
            logger.warning(f"[操作符] 知识库文件不存在: {operators_file}")
            return None

    def get_data_fields(self) -> List[Dict]:
        """Fetch available data fields from WorldQuant Brain across multiple datasets with random sampling.

        添加请求间隔以避免 API 限流
        """
        datasets = ['fundamental6', 'fundamental2', 'analyst4', 'model16', 'model51', 'news12']
        all_fields = []
        api_request_delay = 1.0  # 每次请求间隔 1 秒，避免限流

        base_params = {
            'delay': 1,
            'instrumentType': 'EQUITY',
            'limit': 20,
            'region': 'USA',
            'universe': 'TOP3000'
        }

        try:
            total_datasets = len(datasets)
            logger.info(f"[数据字段获取] 开始获取数据字段，共 {total_datasets} 个数据集...")

            for idx, dataset in enumerate(datasets, 1):
                logger.info(f"[数据字段获取]   [{idx}/{total_datasets}] 正在处理数据集: {dataset}")

                # First get the count
                params = base_params.copy()
                params['dataset.id'] = dataset
                params['limit'] = 1  # Just to get count efficiently

                time.sleep(api_request_delay)  # 请求前等待
                logger.info(f"[数据字段获取]     正在请求字段数量...")
                try:
                    count_response = self.sess.get('https://api.worldquantbrain.com/data-fields', params=params, timeout=30)
                    logger.info(f"[数据字段获取]     字段数量请求完成，状态码: {count_response.status_code}")
                except requests.exceptions.Timeout:
                    logger.warning(f"[数据字段获取]     ⚠ 请求超时，跳过数据集: {dataset}")
                    continue
                except requests.exceptions.RequestException as e:
                    logger.warning(f"[数据字段获取]     ⚠ 请求失败: {e}，跳过数据集: {dataset}")
                    continue

                if count_response.status_code == 200:
                    try:
                        count_data = count_response.json()
                    except json.JSONDecodeError as e:
                        logger.warning(f"[数据字段获取]     ⚠ JSON 解析失败: {e}，跳过数据集: {dataset}")
                        continue

                    total_fields = count_data.get('count', 0)
                    logger.info(f"[数据字段获取]     字段总数: {total_fields}")

                    if total_fields > 0:
                        # Generate random offset
                        max_offset = max(0, total_fields - base_params['limit'])
                        random_offset = random.randint(0, max_offset)

                        # Fetch random subset
                        params['offset'] = random_offset
                        params['limit'] = min(20, total_fields)  # Don't exceed total fields

                        time.sleep(api_request_delay)  # 请求前等待
                        logger.info(f"[数据字段获取]     正在请求字段列表 (offset={random_offset})...")
                        try:
                            response = self.sess.get('https://api.worldquantbrain.com/data-fields', params=params, timeout=30)
                            logger.info(f"[数据字段获取]     字段列表请求完成，状态码: {response.status_code}")
                        except requests.exceptions.Timeout:
                            logger.warning(f"[数据字段获取]     ⚠ 请求超时，跳过数据集: {dataset}")
                            continue
                        except requests.exceptions.RequestException as e:
                            logger.warning(f"[数据字段获取]     ⚠ 请求失败: {e}，跳过数据集: {dataset}")
                            continue

                        if response.status_code == 200:
                            try:
                                data = response.json()
                            except json.JSONDecodeError as e:
                                logger.warning(f"[数据字段获取]     ⚠ JSON 解析失败: {e}")
                                continue

                            fields = data.get('results', [])
                            logger.info(f"[数据字段获取]     ✓ 成功获取 {len(fields)} 个字段")
                            all_fields.extend(fields)
                        else:
                            logger.info(f"[数据字段获取]     ⚠ 获取字段失败: {response.text[:200]}")
                else:
                    logger.info(f"[数据字段获取]     ⚠ 获取字段数量失败: {count_response.text[:200]}")

            # Remove duplicates if any
            unique_fields = {field['id']: field for field in all_fields}.values()
            logger.info(f"[数据字段获取] ✓ 完成! 共获取 {len(unique_fields)} 个唯一字段")

            return list(unique_fields)

        except Exception as e:
            logger.error(f"Failed to fetch data fields: {e}")
            return []

    def get_operators(self) -> List[Dict]:
        """Fetch available operators from WorldQuant Brain."""
        logger.info("=" * 50)
        logger.info("开始获取操作符...")
        logger.info("=" * 50)
        response = self.sess.get('https://api.worldquantbrain.com/operators', timeout=30)
        logger.info(f"Operators response status: {response.status_code}")
        logger.info(f"Operators response: {response.text[:500]}...")  # Print first 500 chars
        
        if response.status_code != 200:
            raise Exception(f"Failed to get operators: {response.text}")
        
        data = response.json()
        # The operators endpoint might return a direct array instead of an object with 'items' or 'results'
        if isinstance(data, list):
            return data
        elif 'results' in data:
            return data['results']
        else:
            raise Exception(f"Unexpected operators response format. Response: {data}")

    def clean_alpha_ideas(self, ideas: List[str]) -> List[str]:
        """Clean and validate alpha ideas, keeping only valid expressions."""
        cleaned_ideas = []
        
        for idea in ideas:
            # Skip if idea is just a number or single word
            if re.match(r'^\d+\.?$|^[a-zA-Z]+$', idea):
                continue
            
            # Skip if idea is a description (contains common English words)
            common_words = ['it', 'the', 'is', 'are', 'captures', 'provides', 'measures']
            if any(word in idea.lower() for word in common_words):
                continue
            
            # Verify idea contains valid operators/functions
            valid_functions = ['ts_mean', 'divide', 'subtract', 'add', 'multiply', 'zscore', 
                              'ts_rank', 'ts_std_dev', 'rank', 'log', 'sqrt']
            if not any(func in idea for func in valid_functions):
                continue
            
            cleaned_ideas.append(idea)  # Just append the expression string
        
        return cleaned_ideas

    def generate_alpha_ideas_with_ollama(self, data_fields: List[Dict], operators: List[Dict]) -> List[str]:
        """Generate alpha ideas using LLM (Ollama or online model)."""
        logger.info(f"开始生成 Alpha 想法 - 数据字段: {len(data_fields)}, 操作符: {len(operators)}")

        operator_by_category = {}
        for op in operators:
            category = op['category']
            if category not in operator_by_category:
                operator_by_category[category] = []
            operator_by_category[category].append({
                'name': op['name'],
                'type': op.get('type', 'SCALAR'),
                'definition': op['definition'],
                'description': op['description']
            })

        try:
            # Clear tested expressions if we hit token limit in previous attempt
            if hasattr(self, '_hit_token_limit'):
                logger.info("Clearing tested expressions due to previous token limit")
                self.results = []
                delattr(self, '_hit_token_limit')

            # Randomly sample ~60% of operators from each category
            sampled_operators = {}
            for category, ops in operator_by_category.items():
                sample_size = max(1, int(len(ops) * 0.5))  # At least 1 operator per category
                sampled_operators[category] = random.sample(ops, sample_size)

            logger.info("准备 LLM 提示词...")
            # Format operators with their types, definitions, and descriptions
            def format_operators(ops):
                formatted = []
                for op in ops:
                    formatted.append(f"{op['name']} ({op['type']})\n"
                                   f"  Definition: {op['definition']}\n"
                                   f"  Description: {op['description']}")
                return formatted

            # 获取最近的错误信息，供大模型参考
            recent_errors = self.get_simulation_errors()[-10:]  # 最近 10 条错误
            error_context = ""
            if recent_errors:
                error_context = "\n\nRecent Errors to Avoid:\n"
                for err in recent_errors[-5:]:  # 只显示最近 5 条
                    error_context += f"- {err.get('expression', '')[:60]}...\n"
                    error_context += f"  Error: {err.get('error_message', 'Unknown')}\n"

            # 加载知识库（随机选择章节）
            knowledge_base = load_knowledge_base(randomize=True)
            knowledge_context = ""
            if knowledge_base:
                knowledge_context = f"\n\n### WorldQuant Brain Knowledge Base:\n{knowledge_base}\n"

            # 加载数据字段参考（随机选择字段）
            data_fields_ref = load_data_fields_reference(max_fields=80, randomize=True)
            fields_ref_context = ""
            if data_fields_ref:
                fields_ref_context = f"\n\n### High-COverage Data Fields (Recommended):\n{data_fields_ref}\n"

            # 加载已提交的 alpha（从 WQ API）
            submitted_alphas = load_submitted_alphas(self.sess, max_alphas=10)
            submitted_context = ""
            if submitted_alphas:
                submitted_context = "\n\n### Previously Submitted Alphas (Reference):\n"
                for i, alpha in enumerate(submitted_alphas[:5], 1):
                    submitted_context += f"{i}. {alpha['expression'][:80]}\n"
                    submitted_context += f"   Fitness: {alpha.get('fitness', 'N/A'):.3f}"
                    if alpha.get('dateSubmitted'):
                        submitted_context += f", Submitted: {alpha['dateSubmitted'][:10]}"
                    submitted_context += "\n"

            # 获取随机策略提示
            strategy_hints = _get_random_strategy_hints()

            # 获取随机示例格式
            example_format = _get_random_example_format()

            # 获取采样的数据字段 ID（随机从高覆盖率字段中选择）
            sampled_field_ids = get_sampled_field_ids(max_fields=100, randomize=True)
            if not sampled_field_ids:
                # fallback: 使用全部字段
                sampled_field_ids = [field['id'] for field in data_fields]

            # 获取每轮生成数量配置
            generate_count = self.optimization_config.get('generate_per_cycle', 20)

            prompt = f"""Generate {generate_count} unique alpha factor expressions using the available operators and data fields. Return ONLY the expressions, one per line, with no comments or explanations.

Available Data Fields (Sampled {len(sampled_field_ids)} high-coverage fields):
{sampled_field_ids}

Available Operators by Category:
Time Series:
{chr(10).join(format_operators(sampled_operators.get('Time Series', [])))}

Cross Sectional:
{chr(10).join(format_operators(sampled_operators.get('Cross Sectional', [])))}

Arithmetic:
{chr(10).join(format_operators(sampled_operators.get('Arithmetic', [])))}

Logical:
{chr(10).join(format_operators(sampled_operators.get('Logical', [])))}

Vector:
{chr(10).join(format_operators(sampled_operators.get('Vector', [])))}

Transformational:
{chr(10).join(format_operators(sampled_operators.get('Transformational', [])))}

Group:
{chr(10).join(format_operators(sampled_operators.get('Group', [])))}
{error_context}{knowledge_context}{fields_ref_context}{submitted_context}
Requirements:
1. Let your intuition guide you.
2. Use the operators and data fields to create a unique and potentially profitable alpha factor.
3. Anything is possible 42.
4. Avoid using event-type data fields (like nws12_*, fnd6_newqeventv*) with time series operators (ts_rank, ts_sum, etc.) as they don't support event inputs.

Critical Success Patterns :
1. ALWAYS wrap expression with rank() / ts_rank() / group_rank() as the outermost operator - this ensures weight distribution and passes CONCENTRATED_WEIGHT check.
2. For fundamental data, use divide(field, cap) for market cap normalization - makes factor size-neutral.
3. Use group_neutralize(expr, industry) for industry neutralization - improves SUB_UNIVERSE_SHARPE.
4. Time window parameters: use 20-120 days (common: 20, 60, 120).
5. Target Turnover range: 0.15-0.45 (avoid too low or too high).

Advanced Techniques (from WorldQuant Brain Guide):
1. Neutralization Options:
   - group_neutralize(expr, industry) - industry neutralization
   - group_neutralize(expr, sector) - sector neutralization
   - group_neutralize(expr, subindustry) - subindustry neutralization
   - regression_neut(expr, factor) - regression neutralization for Size, Beta, Momentum

2. Position Distribution Operators:
   - rank(expr) - uniform distribution (recommended)
   - signed_power(expr, 0.5-0.8) - more extreme distribution, higher volatility
   - log(1 + abs(expr)) * sign(expr) - log distribution

3. Alpha Synergy (combine multiple signals):
   - Trade_when(A1 > x, A2, A1 <= x) - conditional combination
   - Avoid simple linear combinations like 3*A1 + 4*A2 (bad for diversification)

Proven Templates:
- rank(ts_zscore(divide(fundamental_field, cap), 40-80))
- ts_rank(divide(market_field, cap), 60)
- group_neutralize(ts_decay_linear(ts_rank(signal_field, 20-60), 5-10), industry)
- group_rank(ts_rank(ratio_field, 60), industry)
- signed_power(group_neutralize(expr, industry), 0.6)

Overfitting Warnings:
- Do NOT fine-tune too many details to increase In-Sample performance - leads to poor Out-Sample performance.
- Do NOT concentrate positions in few instruments - use rank() to distribute weights.
- Focus on economic significance and robustness, not just high fitness scores.

Tips:
- You can use semi-colons to separate expressions.
- Pay attention to operator types (SCALAR, VECTOR, MATRIX) for compatibility.
- Study the operator definitions and descriptions to understand their behavior.
- Avoid the error patterns shown in "Recent Errors to Avoid" section.
- Use the knowledge base above to create better alpha expressions.
- Learn from the successful patterns - they have high fitness scores.
- Reference submitted alphas for style and complexity guidance.

Strategy Suggestions (pick one or combine):
{strategy_hints}

{example_format}
"""

            # 系统提示词（用于线上模型）
            system_prompt = """你是一个量化金融专家，专门生成 Alpha 因子表达式。
规则：
1. 只返回表达式，每行一个
2. 不添加注释或解释
3. 使用提供的操作符和数据字段
4. 确保表达式语法正确
5. 使用中文回复"""

            # 使用统一 LLM 客户端
            if self.llm_client:
                logger.info(f"Sending request to LLM ({self.llm_client.get_provider()}: {self.llm_client.get_model_name()})...")
                try:
                    if self.llm_client.is_online():
                        content = self.llm_client.generate(prompt, system_prompt=system_prompt, temperature=0.3, max_tokens=40960)
                    else:
                        content = self.llm_client.generate(prompt, temperature=0.3, max_tokens=40960)
                    logger.info(f"LLM response received ({len(content)} chars)")
                except Exception as e:
                    logger.error(f"LLM request failed: {e}")
                    self._handle_llm_error(str(e))
                    return []

            logger.info("Processing LLM response...")

            # Extract pure alpha expressions by:
            # 1. Remove markdown backticks
            # 2. Remove numbering (e.g., "1. ", "2. ")
            # 3. Skip comments
            alpha_ideas = []
            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('*'):
                    continue
                # Remove numbering and backticks
                line = line.replace('`', '')
                if '. ' in line:
                    line = line.split('. ', 1)[1]
                if line and not line.startswith('Comment:'):
                    alpha_ideas.append(line)

            # Clean and validate ideas
            cleaned_ideas = self.clean_alpha_ideas(alpha_ideas)
            return cleaned_ideas

        except Exception as e:
            if "token limit" in str(e).lower():
                self._hit_token_limit = True
            logger.error(f"Error generating alpha ideas: {str(e)}")
            return []

    def _handle_llm_error(self, error_type: str):
        """Handle LLM errors by downgrading model if needed (only for Ollama)."""
        # 线上模型不需要降级
        if self.llm_client and self.llm_client.is_online():
            logger.warning(f"Online LLM error ({error_type}), will retry with same model")
            return

        self.error_count += 1
        logger.warning(f"Ollama error ({error_type}) - Count: {self.error_count}/{self.max_errors_before_downgrade}")

        if self.error_count >= self.max_errors_before_downgrade:
            self._downgrade_model()
            self.error_count = 0
    
    def _downgrade_model(self):
        """Downgrade to the next smaller model in the fleet."""
        if self.current_model_index >= len(self.model_fleet) - 1:
            logger.error("Already using the smallest model in the fleet!")
            # Reset to initial model if we've exhausted all options
            self.current_model_index = 0
            self.model_name = self.initial_model
            logger.info(f"Reset to initial model: {self.initial_model}")
            return
        
        old_model = self.model_fleet[self.current_model_index]
        self.current_model_index += 1
        new_model = self.model_fleet[self.current_model_index]
        
        logger.warning(f"Downgrading model: {old_model} -> {new_model}")
        self.model_name = new_model
        
        # Update the model in the orchestrator if it exists
        try:
            # Try to update the orchestrator's model fleet manager
            if hasattr(self, 'orchestrator') and hasattr(self.orchestrator, 'model_fleet_manager'):
                self.orchestrator.model_fleet_manager.current_model_index = self.current_model_index
                self.orchestrator.model_fleet_manager.save_state()
                logger.info(f"Updated orchestrator model fleet to use: {new_model}")
        except Exception as e:
            logger.warning(f"Could not update orchestrator model fleet: {e}")
        
        logger.info(f"Successfully downgraded to {new_model}")

    def test_alpha_batch(self, alphas: List[str] = None) -> int:
        """
        提交一批 Alpha 进行测试，同时处理队列中的 Alpha

        Args:
            alphas: 可选的 Alpha 列表（如果不提供，则从队列获取）

        Returns:
            成功提交的数量
        """
        # 收集所有待测试的 Alpha
        all_alphas_data = []

        # 1. 从队列获取待测试的 Alpha（包括生成的和优化的）
        if self.alpha_queue:
            batch_from_queue = self.alpha_queue.get_next_batch(batch_size=20)
            for item in batch_from_queue:
                all_alphas_data.append({
                    "expression": item["expression"],
                    "source": item["source"],
                    "original_alpha": item.get("original_alpha"),
                    "opt_type": item.get("optimization_type"),
                    "queue_item": item
                })
            if batch_from_queue:
                logger.info(f"从队列获取 {len(batch_from_queue)} 个 Alpha 待测试")

        # 2. 添加传入的 Alpha（标记为 generated）
        if alphas:
            for alpha in alphas:
                all_alphas_data.append({
                    "expression": alpha,
                    "source": "generated",
                    "original_alpha": None,
                    "opt_type": None,
                    "queue_item": None
                })

        if not all_alphas_data:
            logger.info("没有待测试的 Alpha")
            return 0

        logger.info(f"开始批量测试 {len(all_alphas_data)} 个 Alpha (队列: {sum(1 for a in all_alphas_data if a['queue_item'])}, 新生成: {sum(1 for a in all_alphas_data if not a['queue_item'])})")

        # 提交测试
        max_concurrent = self.executor._max_workers
        submitted = 0
        queued = 0

        for i in range(0, len(all_alphas_data), max_concurrent):
            chunk = all_alphas_data[i:i + max_concurrent]
            logger.info(f"提交批次 {i//max_concurrent + 1}/{(len(all_alphas_data)-1)//max_concurrent + 1} ({len(chunk)} 个)")

            # 提交批次
            futures = []
            for j, alpha_data in enumerate(chunk, 1):
                alpha = alpha_data["expression"]
                logger.info(f"提交 Alpha {i+j}/{len(all_alphas_data)} [{alpha_data['source']}]: {alpha[:50]}...")
                future = self.executor.submit(self._test_alpha_impl, alpha)
                futures.append((alpha_data, future))

            # 处理结果
            for alpha_data, future in futures:
                alpha = alpha_data["expression"]
                try:
                    result = future.result()
                    if result.get("status") == "error":
                        if "SIMULATION_LIMIT_EXCEEDED" in result.get("message", ""):
                            self.retry_queue.add(alpha)
                            queued += 1
                            logger.info(f"加入重试队列: {alpha}")
                        else:
                            logger.error(f"模拟错误 {alpha}: {result.get('message')}")

                            # 记录失败到队列
                            if alpha_data["queue_item"] and self.alpha_queue:
                                self.alpha_queue.record_result(alpha_data["queue_item"], {
                                    "passed": False,
                                    "error": result.get("message")
                                })
                        continue

                    sim_id = result.get("result", {}).get("id")
                    progress_url = result.get("result", {}).get("progress_url")
                    if sim_id and progress_url:
                        self.pending_results[sim_id] = {
                            "alpha": alpha,
                            "progress_url": progress_url,
                            "status": "pending",
                            "attempts": 0,
                            "source": alpha_data["source"],
                            "original_alpha": alpha_data.get("original_alpha"),
                            "opt_type": alpha_data.get("opt_type"),
                            "queue_item": alpha_data.get("queue_item")
                        }
                        submitted += 1
                        logger.info(f"成功提交 {alpha} (ID: {sim_id}) [{alpha_data['source']}]")

                except Exception as e:
                    logger.error(f"提交 Alpha 错误 {alpha}: {str(e)}")

            # 批次间等待
            if i + max_concurrent < len(all_alphas_data):
                logger.info(f"等待 10 秒后继续...")
                sleep(10)

        logger.info(f"批量提交完成: {submitted} 已提交, {queued} 加入重试队列")

        # 监控进度直到完成
        total_successful = 0
        max_monitoring_time = 3600  # 1 小时最大监控时间
        start_time = time.time()

        while self.pending_results:
            if time.time() - start_time > max_monitoring_time:
                logger.warning(f"监控超时 ({max_monitoring_time}s)，停止监控")
                logger.warning(f"剩余待处理模拟: {list(self.pending_results.keys())}")
                break

            logger.info(f"监控 {len(self.pending_results)} 个待处理模拟...")
            completed = self.check_pending_results_with_source()
            total_successful += completed
            sleep(5)

        logger.info(f"批量测试完成: {total_successful} 个成功")
        return total_successful

    def check_pending_results(self) -> int:
        """Check status of all pending simulations with proper retry handling."""
        completed = []
        retry_queue = []
        successful = 0
        max_check_attempts = 90  # 单个模拟最多检查 90 次（约 15 分钟，每次间隔 10 秒）

        for sim_id, info in self.pending_results.items():
            if info["status"] == "pending":
                # 检查次数限制
                info["attempts"] = info.get("attempts", 0) + 1
                if info["attempts"] > max_check_attempts:
                    logger.warning(f"Simulation {sim_id} exceeded max check attempts ({max_check_attempts}), marking as failed")
                    completed.append(sim_id)
                    continue

                # Check if simulation has been pending too long (30 minutes)
                if "start_time" not in info:
                    info["start_time"] = time.time()
                elif time.time() - info["start_time"] > 1800:  # 30 minutes
                    logger.warning(f"Simulation {sim_id} has been pending for too long, marking as failed")
                    completed.append(sim_id)
                    continue
                try:
                    sim_progress_resp = self.sess.get(info["progress_url"], timeout=30)
                    logger.info(f"Checking simulation {sim_id} (attempt {info['attempts']}/{max_check_attempts}) for alpha: {info['alpha'][:50]}...")

                    # Handle rate limits
                    if sim_progress_resp.status_code == 429:
                        logger.info("Rate limit hit, will retry later")
                        continue

                    # Handle simulation limits
                    if "SIMULATION_LIMIT_EXCEEDED" in sim_progress_resp.text:
                        logger.info(f"Simulation limit exceeded for alpha: {info['alpha']}")
                        retry_queue.append((info['alpha'], sim_id))
                        continue

                    # 解析响应内容
                    try:
                        sim_result = sim_progress_resp.json()
                    except Exception as json_err:
                        logger.warning(f"Failed to parse simulation response: {json_err}")
                        continue

                    # 检查进度（如果只有 progress 字段，说明还在运行）
                    progress = sim_result.get("progress")
                    status = sim_result.get("status")

                    # 如果有 progress 但没有 status，说明模拟还在运行中
                    if progress is not None and status is None:
                        logger.info(f"Simulation {sim_id} progress: {progress*100:.1f}% - URL: {info['progress_url']}")
                        # 等待 Retry-After 时间后继续检查
                        retry_after = sim_progress_resp.headers.get("Retry-After")
                        if retry_after:
                            try:
                                wait_time = int(float(retry_after))
                                logger.info(f"Waiting {wait_time}s for simulation to complete...")
                                time.sleep(wait_time)
                            except (ValueError, TypeError):
                                time.sleep(5)
                        continue

                    logger.info(f"Simulation {sim_id} status: {status} - URL: {info['progress_url']}")

                    # Log additional details for debugging
                    if status == "PENDING":
                        logger.debug(f"Simulation {sim_id} is pending...")
                    elif status == "RUNNING":
                        logger.debug(f"Simulation {sim_id} is running...")
                    elif status not in ["COMPLETE", "ERROR"]:
                        logger.warning(f"Simulation {sim_id} has unknown status: {status} - URL: {info['progress_url']}")

                    if status == "COMPLETE":
                        alpha_id = sim_result.get("alpha")
                        if alpha_id:
                            alpha_resp = self.sess.get(f'https://api.worldquantbrain.com/alphas/{alpha_id}', timeout=30)
                            if alpha_resp.status_code == 200:
                                alpha_data = alpha_resp.json()
                                fitness = alpha_data.get("is", {}).get("fitness")
                                logger.info(f"Alpha {alpha_id} completed with fitness: {fitness}")

                                self.results.append({
                                    "alpha": info["alpha"],
                                    "result": sim_result,
                                    "alpha_data": alpha_data
                                })

                                # Check if fitness is not None and greater than threshold
                                if fitness is not None and fitness > 0.5:
                                    logger.info(f"Found promising alpha! Fitness: {fitness}")
                                    self.log_hopeful_alpha(info["alpha"], alpha_data)
                                    successful += 1
                                elif fitness is None:
                                    logger.warning(f"Alpha {alpha_id} has no fitness data, skipping hopeful alpha logging")
                    elif status == "ERROR":
                        # 记录详细错误信息
                        error_msg = sim_result.get("message", "Unknown error")
                        error_location = sim_result.get("location", {})
                        logger.error(f"Simulation failed for alpha: {info['alpha']}")
                        logger.error(f"  Error: {error_msg}")
                        if error_location:
                            logger.error(f"  Location: line {error_location.get('line')}, pos {error_location.get('start')}-{error_location.get('end')}")

                        # 保存错误信息到文件，供后续分析和反馈给大模型
                        self._log_simulation_error(info["alpha"], sim_result)
                    completed.append(sim_id)
                    
                except Exception as e:
                    logger.error(f"Error checking result for {sim_id}: {str(e)}")
        
        # Remove completed simulations
        for sim_id in completed:
            del self.pending_results[sim_id]
        
        # Requeue failed simulations
        for alpha, sim_id in retry_queue:
            del self.pending_results[sim_id]
            self.retry_queue.add(alpha)
        
        return successful

    def check_pending_results_with_source(self) -> int:
        """
        检查待处理模拟结果，并记录来源信息到队列

        Returns:
            成功的 Alpha 数量
        """
        successful = 0
        completed = []
        retry_queue = []
        max_check_attempts = 100

        for sim_id, info in self.pending_results.items():
            if info["status"] == "pending":
                info["attempts"] = info.get("attempts", 0) + 1
                if info["attempts"] > max_check_attempts:
                    logger.warning(f"模拟 {sim_id} 超过最大检查次数 ({max_check_attempts})，标记为失败")
                    completed.append(sim_id)
                    continue

                if "start_time" not in info:
                    info["start_time"] = time.time()
                elif time.time() - info["start_time"] > 1800:
                    logger.warning(f"模拟 {sim_id} 等待时间过长，标记为失败")
                    completed.append(sim_id)
                    continue

                try:
                    sim_progress_resp = self.sess.get(info["progress_url"], timeout=30)
                    source = info.get("source", "generated")
                    logger.info(f"检查模拟 {sim_id} (尝试 {info['attempts']}/{max_check_attempts}) [{source}]: {info['alpha'][:50]}...")

                    if sim_progress_resp.status_code == 429:
                        logger.info("触发限流，稍后重试")
                        continue

                    if "SIMULATION_LIMIT_EXCEEDED" in sim_progress_resp.text:
                        logger.info(f"模拟次数超限: {info['alpha']}")
                        retry_queue.append((info['alpha'], sim_id))
                        continue

                    try:
                        sim_result = sim_progress_resp.json()
                    except Exception as json_err:
                        logger.warning(f"解析模拟响应失败: {json_err}")
                        continue

                    progress = sim_result.get("progress")
                    status = sim_result.get("status")

                    if progress is not None and status is None:
                        logger.info(f"模拟 {sim_id} 进度: {progress*100:.1f}%")
                        retry_after = sim_progress_resp.headers.get("Retry-After")
                        if retry_after:
                            try:
                                wait_time = int(float(retry_after))
                                logger.info(f"等待 {wait_time}s...")
                                time.sleep(wait_time)
                            except (ValueError, TypeError):
                                time.sleep(5)
                        continue

                    logger.info(f"模拟 {sim_id} 状态: {status}")

                    if status == "COMPLETE":
                        alpha_id = sim_result.get("alpha")
                        if alpha_id:
                            alpha_resp = self.sess.get(f'https://api.worldquantbrain.com/alphas/{alpha_id}', timeout=30)
                            if alpha_resp.status_code == 200:
                                alpha_data = alpha_resp.json()
                                fitness = alpha_data.get("is", {}).get("fitness")
                                sharpe = alpha_data.get("is", {}).get("sharpe", 0)
                                is_submittable = alpha_data.get("is_submittable", False)

                                logger.info(f"Alpha {alpha_id} 完成 [{source}] - Fitness: {fitness}, Sharpe: {sharpe}")

                                # 记录结果
                                result_entry = {
                                    "alpha": info["alpha"],
                                    "result": sim_result,
                                    "alpha_data": alpha_data,
                                    "source": source,
                                    "original_alpha": info.get("original_alpha"),
                                    "opt_type": info.get("opt_type")
                                }
                                self.results.append(result_entry)

                                # 记录到队列
                                if info.get("queue_item") and self.alpha_queue:
                                    self.alpha_queue.record_result(info["queue_item"], {
                                        "passed": is_submittable or (fitness is not None and fitness > 0.5),
                                        "sharpe": sharpe,
                                        "fitness": fitness,
                                        "alpha_id": alpha_id
                                    })

                                # 检查是否为有潜力的 Alpha
                                if fitness is not None and fitness > 0.5:
                                    logger.info(f"发现潜力 Alpha! [{source}] Fitness: {fitness}")
                                    self.log_hopeful_alpha(info["alpha"], alpha_data)
                                    successful += 1
                                elif fitness is None:
                                    logger.warning(f"Alpha {alpha_id} 没有 fitness 数据")

                    elif status == "ERROR":
                        error_msg = sim_result.get("message", "Unknown error")
                        error_location = sim_result.get("location", {})
                        logger.error(f"模拟失败 [{source}]: {info['alpha']}")
                        logger.error(f"  错误: {error_msg}")
                        if error_location:
                            logger.error(f"  位置: line {error_location.get('line')}")

                        # 记录失败到队列
                        if info.get("queue_item") and self.alpha_queue:
                            self.alpha_queue.record_result(info["queue_item"], {
                                "passed": False,
                                "error": error_msg
                            })

                        self._log_simulation_error(info["alpha"], sim_result)

                    completed.append(sim_id)

                except Exception as e:
                    logger.error(f"检查结果错误 {sim_id}: {str(e)}")

        # 移除已完成的模拟
        for sim_id in completed:
            del self.pending_results[sim_id]

        # 重试失败的模拟
        for alpha, sim_id in retry_queue:
            del self.pending_results[sim_id]
            self.retry_queue.add(alpha)

        return successful

    def _is_already_simulated(self, expression: str) -> bool:
        """检查公式是否已经模拟过"""
        simulated_file = 'simulated_expressions.json'
        if not os.path.exists(simulated_file):
            return False

        try:
            with open(simulated_file, 'r') as f:
                simulated = json.load(f)
            # 检查表达式是否在已模拟列表中
            for entry in simulated:
                if entry.get('expression') == expression:
                    return True
            return False
        except (json.JSONDecodeError, FileNotFoundError):
            return False

    def _record_simulation(self, expression: str, sim_id: str, status: str = "submitted") -> None:
        """记录已提交的模拟"""
        simulated_file = 'simulated_expressions.json'

        existing = []
        if os.path.exists(simulated_file):
            try:
                with open(simulated_file, 'r') as f:
                    existing = json.load(f)
            except json.JSONDecodeError:
                pass

        # 添加记录
        entry = {
            "expression": expression,
            "simulation_id": sim_id,
            "timestamp": int(time.time()),
            "status": status
        }
        existing.append(entry)

        # 只保留最近 1000 条记录
        if len(existing) > 1000:
            existing = existing[-1000:]

        with open(simulated_file, 'w') as f:
            json.dump(existing, f, indent=2)

    def test_alpha(self, alpha: str) -> Dict:
        result = self._test_alpha_impl(alpha)
        if result.get("status") == "error" and "SIMULATION_LIMIT_EXCEEDED" in result.get("message", ""):
            self.retry_queue.add(alpha)
            return {"status": "queued", "message": "Added to retry queue"}
        return result

    def _test_alpha_impl(self, alpha_expression: str) -> Dict:
        """Implementation of alpha testing with proper URL handling and retry logic."""
        logger.info(f"开始提交模拟: {alpha_expression}")

        # 检查是否已经模拟过这个公式
        if self._is_already_simulated(alpha_expression):
            logger.info(f"Alpha 已模拟过，跳过: {alpha_expression[:80]}...")
            return {"status": "skipped", "message": "Alpha already simulated"}

        def submit_simulation():
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
            logger.info(f"POST https://api.worldquantbrain.com/simulations - 公式: {alpha_expression[:60]}...")
            return self.sess.post('https://api.worldquantbrain.com/simulations', json=simulation_data, timeout=60)

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                sim_resp = submit_simulation()

                # Handle authentication error
                if sim_resp.status_code == 401 or (
                    sim_resp.status_code == 400 and
                    "authentication credentials" in sim_resp.text.lower()
                ):
                    logger.warning("Authentication expired, refreshing session...")
                    self.setup_auth(self.credentials_path)  # Refresh authentication
                    sim_resp = submit_simulation()  # Retry with new auth

                if sim_resp.status_code != 201:
                    logger.error(f"模拟提交失败 (HTTP {sim_resp.status_code}): {sim_resp.text[:200]}")
                    return {"status": "error", "message": sim_resp.text}

                sim_progress_url = sim_resp.headers.get('location')
                if not sim_progress_url:
                    logger.error("模拟提交失败: 未收到 progress URL")
                    return {"status": "error", "message": "No progress URL received"}

                # 从 URL 中提取真实的模拟 ID
                # URL 格式: https://api.worldquantbrain.com/simulations/{sim_id}
                sim_id = sim_progress_url.rstrip('/').split('/')[-1]

                # 记录已提交的模拟
                self._record_simulation(alpha_expression, sim_id, "submitted")

                logger.info(f"模拟提交成功 - ID: {sim_id}, 公式: {alpha_expression[:60]}...")

                return {
                    "status": "success",
                    "result": {
                        "id": sim_id,
                        "progress_url": sim_progress_url
                    }
                }

            except Exception as e:
                retry_count += 1
                error_msg = str(e)

                # 检查是否是 SSL 或代理错误
                is_ssl_error = any(keyword in error_msg.lower() for keyword in [
                    'ssl', 'eof', 'protocol', 'proxy', 'connection', 'timeout'
                ])

                if is_ssl_error and retry_count < max_retries:
                    wait_time = 10 * retry_count
                    logger.warning(f"Network error (attempt {retry_count}/{max_retries}), retrying in {wait_time}s: {error_msg}")
                    sleep(wait_time)
                    continue
                else:
                    logger.error(f"Error testing alpha {alpha_expression}: {error_msg}")
                    return {"status": "error", "message": error_msg}

        return {"status": "error", "message": "Max retries exceeded"}

    def log_hopeful_alpha(self, expression: str, alpha_data: Dict) -> None:
        """Log promising alphas to a JSON file with deduplication."""
        log_file = 'hopeful_alphas.json'

        # Load existing data
        existing_data = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                logger.info(f"Warning: Could not parse {log_file}, starting fresh")

        # 检查是否已存在相同表达式
        for existing in existing_data:
            if existing.get('expression') == expression:
                logger.info(f"Alpha already exists in {log_file}, skipping duplicate: {expression[:50]}...")
                return

        # Add new alpha with timestamp
        entry = {
            "expression": expression,  # Store just the expression string
            "timestamp": int(time.time()),
            "alpha_id": alpha_data.get("id", "unknown"),
            "simulation_id": alpha_data.get("id", "unknown"),  # 记录模拟 ID
            "fitness": alpha_data.get("is", {}).get("fitness"),
            "sharpe": alpha_data.get("is", {}).get("sharpe"),
            "turnover": alpha_data.get("is", {}).get("turnover"),
            "returns": alpha_data.get("is", {}).get("returns"),
            "grade": alpha_data.get("grade", "UNKNOWN"),
            "checks": alpha_data.get("is", {}).get("checks", []),
            "status": "pending_mining"  # 添加状态字段
        }

        existing_data.append(entry)

        # Save updated data
        with open(log_file, 'w') as f:
            json.dump(existing_data, f, indent=2)

        logger.info(f"Logged promising alpha to {log_file}")

    def _log_simulation_error(self, expression: str, error_result: Dict) -> None:
        """记录模拟错误信息，供后续分析和反馈给大模型"""
        log_file = 'simulation_errors.json'

        # 加载现有数据
        existing_data = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        # 构建错误条目
        entry = {
            "expression": expression,
            "timestamp": int(time.time()),
            "error_message": error_result.get("message", "Unknown error"),
            "error_location": error_result.get("location", {}),
            "help_link": error_result.get("links", {}).get("linkToCommonErrorMessages", ""),
            "simulation_id": error_result.get("id", "")
        }

        existing_data.append(entry)

        # 只保留最近 100 条错误记录
        if len(existing_data) > 100:
            existing_data = existing_data[-100:]

        # 保存
        with open(log_file, 'w') as f:
            json.dump(existing_data, f, indent=2)

        logging.info(f"Error logged to {log_file}")

    def get_simulation_errors(self) -> List[Dict]:
        """获取最近的模拟错误记录，供大模型参考"""
        log_file = 'simulation_errors.json'
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def get_results(self) -> List[Dict]:
        """Get all processed results including retried alphas."""
        return self.results

    def optimize_failed_alphas(self, use_db: bool = False, db_config: dict = None) -> List[Dict]:
        """
        优化失败的 Alpha

        Args:
            use_db: 是否从数据库获取优化候选（IS 检查 6 PASS, 1 FAIL）
            db_config: 数据库配置（可选，默认从配置文件加载）

        Returns:
            优化结果列表
        """
        if not self.optimizer or not self.optimization_enabled:
            logger.info("优化功能未启用")
            return []

        # 设置 WorldQuant 客户端给优化器
        self.optimizer.set_wq_client(self)

        # 如果使用数据库模式，初始化数据库查询服务
        if use_db and not self.optimizer.query_service:
            try:
                # 尝试从配置文件加载数据库配置
                if not db_config:
                    db_config = self._load_db_config()

                if db_config:
                    # 添加项目根目录到 Python 路径
                    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
                    if project_root not in sys.path:
                        sys.path.insert(0, project_root)
                    from db.alpha_query_service import AlphaQueryService
                    query_service = AlphaQueryService(db_config)
                    self.optimizer.set_query_service(query_service)
                    logger.info("数据库查询服务初始化成功")
                else:
                    logger.warning("未找到数据库配置，将使用 API 模式")
                    use_db = False
            except Exception as e:
                logger.error(f"数据库查询服务初始化失败: {e}")
                use_db = False

        # 获取优化配置
        min_sharpe = self.optimization_config.get('min_sharpe', 1.0)
        top_n = self.optimization_config.get('optimize_per_cycle', 5)
        temperature = self.optimization_config.get('temperature', 0.5)

        mode_str = "数据库模式（IS 检查 6 PASS, 1 FAIL）" if use_db else f"API 模式 (min_sharpe={min_sharpe})"
        logger.info(f"开始优化失败的 Alpha - {mode_str}, top_n={top_n}")

        try:
            results = self.optimizer.optimize_top_failed(
                top_n=top_n,
                min_sharpe=min_sharpe,
                temperature=temperature,
                use_db=use_db
            )

            # 将优化结果添加到队列
            for result in results:
                if result.get("success") and result.get("optimized"):
                    self.alpha_queue.add_optimized(
                        alpha=result["optimized"],
                        original=result["original"],
                        opt_type=result["failure_type"],
                        metadata={
                            "original_metrics": result.get("original_metrics", {}),
                            "timestamp": result.get("timestamp")
                        }
                    )

            logger.info(f"优化完成: 成功 {len(results)} 个")
            return results

        except Exception as e:
            logger.error(f"优化失败: {e}")
            return []

    def _load_db_config(self) -> Optional[Dict]:
        """从配置文件加载数据库配置"""
        # 尝试多个可能的数据库配置文件路径
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'db', 'db_config.json'),
            os.path.join(os.path.dirname(__file__), 'db_config.json'),
            os.path.join(os.path.dirname(self.config_path), 'db_config.json'),
        ]

        for db_config_path in possible_paths:
            if os.path.exists(db_config_path):
                try:
                    with open(db_config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    logger.info(f"已加载数据库配置: {db_config_path}")
                    return config
                except Exception as e:
                    logger.warning(f"加载数据库配置失败 ({db_config_path}): {e}")

        logger.warning("未找到数据库配置文件")
        return None

    def get_user_alphas(self) -> List[Dict]:
        """
        获取用户未通过的 Alpha（用于优化器）

        Returns:
            Alpha 列表
        """
        try:
            response = self.sess.get(
                'https://api.worldquantbrain.com/users/self/alphas',
                params={
                    'limit': 100,
                    'offset': 0,
                    'order': '-is.sharpe',
                    'hidden': 'false'
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                alphas = data.get('results', [])

                # 转换为优化器需要的格式
                result = []
                for alpha in alphas:
                    expression = alpha.get('regular', {}).get('code', '').strip()
                    if expression:
                        is_data = alpha.get('is', {})
                        checks = is_data.get('checks', [])
                        status = alpha.get('status', '')

                        # 将 checks 数组转换为 check_status 字典
                        check_status = {}
                        # 同时保存完整的检查详情（包含 limit 和 value）
                        check_details = []
                        for check in checks:
                            check_name = check.get('name', '')
                            check_result = check.get('result', '')
                            check_status[check_name] = check_result

                            # 保存失败检查的详细信息
                            if check_result == 'FAIL':
                                check_details.append({
                                    'name': check_name,
                                    'result': check_result,
                                    'limit': check.get('limit'),
                                    'value': check.get('value')
                                })

                        # 判断是否可提交：status 不是 UNSUBMITTED 且所有检查通过
                        is_submittable = status != 'UNSUBMITTED' and all(
                            c.get('result') == 'PASS'
                            for c in checks
                        )

                        result.append({
                            'expression': expression,
                            'sharpe': is_data.get('sharpe', 0),
                            'fitness': is_data.get('fitness', 0),
                            'turnover': is_data.get('turnover', 0),
                            'is_submittable': is_submittable,
                            'check_status': check_status,
                            'check_details': check_details,  # 新增：详细失败信息
                            'date_created': alpha.get('dateCreated'),
                            'alpha_id': alpha.get('id')
                        })

                logger.info(f"获取用户 Alpha: {len(result)} 个")
                return result

            else:
                logger.warning(f"获取用户 Alpha 失败: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"获取用户 Alpha 异常: {e}")
            return []

    def test_alpha_with_source(self, alpha: str, source: str = "generated",
                                original_alpha: str = None, opt_type: str = None) -> Dict:
        """
        测试 Alpha 并记录来源

        Args:
            alpha: Alpha 表达式
            source: 来源（generated/optimized）
            original_alpha: 原始表达式（优化时）
            opt_type: 优化类型（优化时）

        Returns:
            测试结果
        """
        result = self.test_alpha(alpha)

        # 添加来源信息
        result["source"] = source
        if source == "optimized":
            result["original_alpha"] = original_alpha
            result["optimization_type"] = opt_type

        return result

    def get_queue_stats(self) -> Dict:
        """
        获取队列统计

        Returns:
            统计数据
        """
        if self.alpha_queue:
            return self.alpha_queue.get_stats()
        return {"error": "队列未初始化"}

    def report_optimization_stats(self):
        """汇报优化统计"""
        if not self.alpha_queue:
            return

        stats = self.alpha_queue.get_stats()

        logger.info("=" * 60)
        logger.info("Alpha 统计:")
        logger.info(f"  队列大小: {stats.get('queue_size', 0)}")
        logger.info(f"  已测试: {stats.get('tested_count', 0)}")

        gen = stats.get('generated', {})
        opt = stats.get('optimized', {})

        logger.info(f"  生成: 总计 {gen.get('total', 0)}, 通过 {gen.get('passed', 0)}, "
                   f"失败 {gen.get('failed', 0)}, 通过率 {gen.get('pass_rate', 0):.1f}%")

        logger.info(f"  优化: 总计 {opt.get('total', 0)}, 通过 {opt.get('passed', 0)}, "
                   f"失败 {opt.get('failed', 0)}, 通过率 {opt.get('pass_rate', 0):.1f}%")

        if self.optimizer:
            opt_stats = self.optimizer.get_stats()
            logger.info(f"  优化器: 尝试 {opt_stats.get('total_attempts', 0)}, "
                       f"成功 {opt_stats.get('successful', 0)}, "
                       f"成功率 {opt_stats.get('success_rate', 0):.1f}%")

        logger.info("=" * 60)


    def fetch_submitted_alphas(self):
        """Fetch submitted alphas from the WorldQuant API with retry logic"""
        url = "https://api.worldquantbrain.com/users/self/alphas"
        params = {
            "limit": 100,
            "offset": 0,
            "status!=": "UNSUBMITTED%1FIS-FAIL",
            "order": "-dateCreated",
            "hidden": "false"
        }
        
        max_retries = 3
        retry_delay = 60  # seconds
        
        for attempt in range(max_retries):
            try:
                response = self.sess.get(url, params=params, timeout=30)
                if response.status_code == 429:  # Too Many Requests
                    wait_time = int(response.headers.get('Retry-After', retry_delay))
                    logger.info(f"Rate limited. Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                return response.json()["results"]
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to fetch submitted alphas after {max_retries} attempts: {e}")
                    return []
        
        return []

def extract_expressions(alphas):
    """Extract expressions from submitted alphas"""
    expressions = []
    for alpha in alphas:
        if alpha.get("regular") and alpha["regular"].get("code"):
            expressions.append({
                "expression": alpha["regular"]["code"],
                "performance": {
                    "sharpe": alpha["is"].get("sharpe", 0),
                    "fitness": alpha["is"].get("fitness", 0)
                }
            })
    return expressions

def is_similar_to_existing(new_expression, existing_expressions, similarity_threshold=0.7):
    """Check if new expression is too similar to existing ones"""
    for existing in existing_expressions:
        # Basic similarity checks
        if new_expression == existing["expression"]:
            return True
            
        # Check for structural similarity
        if structural_similarity(new_expression, existing["expression"]) > similarity_threshold:
            return True
    
    return False

def calculate_similarity(expr1: str, expr2: str) -> float:
    """Calculate similarity between two expressions using token-based comparison."""
    # Normalize expressions
    expr1_tokens = set(tokenize_expression(normalize_expression(expr1)))
    expr2_tokens = set(tokenize_expression(normalize_expression(expr2)))
    
    if not expr1_tokens or not expr2_tokens:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = len(expr1_tokens.intersection(expr2_tokens))
    union = len(expr1_tokens.union(expr2_tokens))
    
    return intersection / union

def structural_similarity(expr1, expr2):
    """Calculate structural similarity between two expressions"""
    return calculate_similarity(expr1, expr2)  # Use our new similarity function

def normalize_expression(expr):
    """Normalize expression for comparison"""
    # Remove whitespace and convert to lowercase
    expr = re.sub(r'\s+', '', expr.lower())
    return expr

def tokenize_expression(expr):
    """Split expression into meaningful tokens"""
    # Split on operators and parentheses while keeping them
    tokens = re.findall(r'[\w._]+|[(),*/+-]', expr)
    return tokens

def generate_alpha():
    """Generate new alpha expression"""
    generator = AlphaGenerator("./credential.txt", "http://localhost:11434")
    data_fields = generator.get_data_fields()
    operators = generator.get_operators()
    
    # Fetch existing alphas first
    submitted_alphas = generator.fetch_submitted_alphas()
    existing_expressions = extract_expressions(submitted_alphas)
    
    max_attempts = 50
    attempts = 0
    
    while attempts < max_attempts:
        alpha_ideas = generator.generate_alpha_ideas_with_ollama(data_fields, operators)
        for idea in alpha_ideas:
            if not is_similar_to_existing(idea, existing_expressions):
                logger.info(f"Generated unique expression: {idea}")
                return idea
                
        attempts += 1
        logger.debug(f"Attempt {attempts}: All expressions were too similar")
    
    logger.warning("Failed to generate unique expression after maximum attempts")
    return None

def main():
    parser = argparse.ArgumentParser(description='Generate and test alpha factors using WorldQuant Brain API with Ollama/FinGPT')
    parser.add_argument('--credentials', type=str, default='./credential.txt',
                      help='Path to credentials file (default: ./credential.txt)')
    parser.add_argument('--output-dir', type=str, default='./results',
                      help='Directory to save results (default: ./results)')
    parser.add_argument('--batch-size', type=int, default=3,
                      help='Number of alpha factors to generate per batch (default: 3)')
    parser.add_argument('--sleep-time', type=int, default=10,
                      help='Sleep time between batches in seconds (default: 10)')
    parser.add_argument('--log-level', type=str, default='INFO',
                      choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      help='Set the logging level (default: INFO)')
    parser.add_argument('--ollama-url', type=str, default='http://localhost:11434',
                      help='Ollama API URL (default: http://localhost:11434)')
    parser.add_argument('--ollama-model', type=str, default=None,
                      help='Ollama model to use (default: from config.json or llama3:8b)')
    parser.add_argument('--max-concurrent', type=int, default=2,
                      help='Maximum concurrent simulations (default: 2)')
    parser.add_argument('--config', type=str, default='config.json',
                      help='Path to configuration file (default: config.json)')

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # 确定要使用的模型
    model_name = args.ollama_model
    if model_name is None and CONFIG_AVAILABLE:
        try:
            config_manager = get_config_manager(args.config)
            model_name = config_manager.config.default_model
            logger.info(f"从配置文件加载默认模型: {model_name}")
        except Exception as e:
            logger.warning(f"从配置文件加载模型失败: {e}")
    if model_name is None:
        model_name = 'llama3:8b'
        logger.info(f"使用后备默认模型: {model_name}")

    try:
        # Initialize alpha generator with Ollama
        generator = AlphaGenerator(args.credentials, args.ollama_url, args.max_concurrent, args.config)
        generator.model_name = model_name  # Set the model name
        generator.initial_model = model_name  # Set the initial model for reset

        # 设置清理处理器
        setup_cleanup_handler(generator)

        # Get data fields and operators - 优先从本地知识库加载
        logger.info("=" * 50)
        logger.info("开始加载数据字段和操作符...")
        logger.info("=" * 50)

        # 尝试从本地加载数据字段
        data_fields = generator.get_data_fields_from_local()
        if data_fields is None:
            logger.info("[数据字段] 本地加载失败，从 API 获取...")
            data_fields = generator.get_data_fields()
        logger.info(f"数据字段加载完成，共 {len(data_fields)} 个字段")

        # 尝试从本地加载操作符
        operators = generator.get_operators_from_local()
        if operators is None:
            logger.info("[操作符] 本地加载失败，从 API 获取...")
            operators = generator.get_operators()
        logger.info(f"操作符加载完成，共 {len(operators)} 个操作符")

        batch_number = 1
        total_successful = 0

        logger.info(f"Starting continuous alpha mining with batch size {args.batch_size}")
        logger.info(f"Results will be saved to {args.output_dir}")
        logger.info(f"Using Ollama at {args.ollama_url}")

        # 显示优化状态
        if generator.optimization_enabled:
            logger.info(f"优化功能已启用 - 每轮优化 {generator.optimization_config.get('optimize_per_cycle', 5)} 个 Alpha")
        else:
            logger.info("优化功能未启用")

        logger.info("=" * 50)
        logger.info("进入主循环，开始生成 Alpha...")
        logger.info("=" * 50)

        # 启动消费者线程（独立消费队列中的 Alpha）
        generator.start_consumer_thread(check_interval=5, batch_size=10)
        logger.info("✅ 消费者线程已启动，将独立处理队列中的 Alpha")

        while True:
            try:
                logger.info(f"\n{'='*20} Processing batch #{batch_number} {'='*20}")
                logger.info("-" * 50)

                # 1. 生成新 Alpha（生产者）
                logger.info("步骤 1: 生成新 Alpha...")
                logger.info(f"调用 generate_alpha_ideas_with_ollama, 全部字段数: {len(data_fields)}, 操作符数: {len(operators)}")
                alpha_ideas = generator.generate_alpha_ideas_with_ollama(data_fields, operators)
                logger.info(f"生成完成，获得 {len(alpha_ideas)} 个 Alpha 想法")

                # 添加到队列（消费者线程会自动处理）
                if generator.alpha_queue:
                    for alpha in alpha_ideas:
                        generator.alpha_queue.add_generated(alpha)
                    queue_size = len(generator.alpha_queue)
                    logger.info(f"📦 Alpha 已加入队列，当前队列大小: {queue_size}")
                else:
                    logger.warning("⚠️ alpha_queue 未初始化，Alpha 未加入队列")

                # 2. 优化失败的 Alpha（生产者）
                if generator.optimization_enabled:
                    logger.info("步骤 2: 优化失败的 Alpha...")
                    try:
                        optimized_results = generator.optimize_failed_alphas(use_db=True)
                        if optimized_results:
                            logger.info(f"优化完成: {len(optimized_results)} 个，已加入队列")
                    except Exception as e:
                        logger.error(f"优化过程出错: {e}")
                else:
                    logger.info("步骤 2: 跳过优化（未启用）")

                # 3. 汇报统计（每 5 批次）
                if generator.alpha_queue and batch_number % 5 == 0:
                    generator.report_optimization_stats()
                    queue_size = len(generator.alpha_queue)
                    pending_count = len(generator.pending_results)
                    logger.info(f"📊 状态: 队列 {queue_size} 待测试, {pending_count} 待结果")

                # Perform VRAM cleanup every few batches
                generator.operation_count += 1
                if generator.operation_count % generator.vram_cleanup_interval == 0:
                    generator.cleanup_vram()

                # Save batch results
                results = generator.get_results()
                if results:
                    timestamp = int(time.time())
                    output_file = os.path.join(args.output_dir, f'batch_{batch_number}_{timestamp}.json')
                    with open(output_file, 'w') as f:
                        json.dump(results, f, indent=2)
                    logger.info(f"Batch {batch_number} results saved to {output_file}")

                batch_number += 1

                # Sleep between batches
                logger.info(f"Sleeping for {args.sleep_time} seconds...")
                sleep(args.sleep_time)

            except Exception as e:
                logger.error(f"Error in batch {batch_number}: {str(e)}")
                logger.info("Sleeping for 5 minutes before retrying...")
                sleep(300)
                continue

    except KeyboardInterrupt:
        logger.info("\nStopping alpha mining...")
        logger.info(f"Total batches processed: {batch_number - 1}")
        # 停止消费者线程
        generator.stop_consumer_thread()
        logger.info("消费者线程已停止")
        return 0

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        generator.stop_consumer_thread()
        return 1


def setup_cleanup_handler(generator):
    """设置 Windows 控制台关闭事件处理器"""
    def cleanup():
        logger.info("Alpha Generator 正在关闭...")
        if generator:
            try:
                # 停止消费者线程
                generator.stop_consumer_thread()
                # 关闭线程池
                generator.executor.shutdown(wait=False)
                logger.info("线程池已关闭")
            except Exception as e:
                logger.error(f"关闭线程池时出错: {e}")
        # 关闭日志系统
        try:
            from logging_config import shutdown_logging
            shutdown_logging()
        except:
            pass

    def signal_handler(signum=None, frame=None):
        logger.info("收到退出信号，正在关闭...")
        cleanup()
        sys.exit(0)

    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Windows 平台特殊处理
    if sys.platform == 'win32':
        try:
            CTRL_HANDLER_TYPE = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)

            # 保存 handler 引用，防止被垃圾回收
            ctrl_handler = None

            def console_ctrl_handler(ctrl_type):
                if ctrl_type in (2, 5, 6):
                    # 使用 print 而不是 logger，因为 logger 可能已经不可用
                    logger.info(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 收到 Windows 控制台关闭事件 (类型: {ctrl_type})，正在关闭...")
                    # 强制刷新输出
                    sys.stdout.flush()
                    cleanup()
                    return True
                return False

            ctrl_handler = CTRL_HANDLER_TYPE(console_ctrl_handler)
            result = ctypes.windll.kernel32.SetConsoleCtrlHandler(ctrl_handler, True)
            if result:
                logger.info("已注册 Windows 控制台关闭事件处理器")
            else:
                logger.warning("注册 Windows 控制台事件处理器失败")
        except Exception as e:
            logger.warning(f"无法注册 Windows 控制台事件处理器: {e}")

    atexit.register(cleanup)


if __name__ == "__main__":
    main()
