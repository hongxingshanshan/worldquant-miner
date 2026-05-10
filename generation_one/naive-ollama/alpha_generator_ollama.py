import argparse
import requests
import json
import os
from time import sleep
from requests.auth import HTTPBasicAuth
from typing import List, Dict
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

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

# 知识库路径（统一存放在项目根目录的 knowledge_base 文件夹）
KNOWLEDGE_BASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                    'knowledge_base')

# 成功模式缓存文件
SUCCESSFUL_PATTERNS_FILE = "successful_patterns.json"
SUBMITTED_ALPHAS_CACHE = "submitted_alphas_cache.json"


def load_successful_patterns(max_patterns: int = 20, randomize: bool = True) -> List[Dict]:
    """加载成功的 alpha 模式（fitness > 0.5）

    Args:
        max_patterns: 最大加载数量
        randomize: 是否随机选择（而非按 fitness 排序）
    """
    patterns = []
    results_dir = "results"

    if not os.path.exists(results_dir):
        return patterns

    try:
        # 获取所有结果文件
        result_files = [f for f in os.listdir(results_dir) if f.endswith('.json')]

        # 按修改时间排序，优先使用最新的
        result_files.sort(key=lambda x: os.path.getmtime(os.path.join(results_dir, x)), reverse=True)

        for filename in result_files[:100]:  # 只检查最近 100 个文件
            if len(patterns) >= max_patterns * 2:  # 收集更多用于随机选择
                break
            filepath = os.path.join(results_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                alpha_data = item.get("alpha_data", {})
                                fitness = alpha_data.get("is", {}).get("fitness")
                                expression = item.get("alpha", "")
                                if fitness is not None and fitness > 0.5 and expression:
                                    patterns.append({
                                        "expression": expression,
                                        "fitness": fitness,
                                        "sharpe": alpha_data.get("is", {}).get("sharpe"),
                                        "turnover": alpha_data.get("is", {}).get("turnover"),
                                    })
                    elif isinstance(data, dict):
                        alpha_data = data.get("alpha_data", {})
                        fitness = alpha_data.get("is", {}).get("fitness")
                        expression = data.get("alpha", "")
                        if fitness is not None and fitness > 0.5 and expression:
                            patterns.append({
                                "expression": expression,
                                "fitness": fitness,
                                "sharpe": alpha_data.get("is", {}).get("sharpe"),
                                "turnover": alpha_data.get("is", {}).get("turnover"),
                            })
            except Exception as e:
                continue

        if randomize and len(patterns) > max_patterns:
            # 随机选择，而非按 fitness 排序
            return random.sample(patterns, max_patterns)
        else:
            # 原有逻辑：按 fitness 排序
            patterns.sort(key=lambda x: x.get("fitness", 0), reverse=True)
            return patterns[:max_patterns]

    except Exception as e:
        logger.warning(f"Failed to load successful patterns: {e}")
        return patterns


def load_submitted_alphas(sess, max_alphas: int = 20) -> List[Dict]:
    """从 WorldQuant Brain API 获取已提交的 alpha"""
    cache_file = SUBMITTED_ALPHAS_CACHE
    alphas = []

    # 尝试从缓存加载
    if os.path.exists(cache_file):
        try:
            cache_age = time.time() - os.path.getmtime(cache_file)
            if cache_age < 3600:  # 缓存 1 小时有效
                with open(cache_file, 'r', encoding='utf-8') as f:
                    alphas = json.load(f)
                    logger.info(f"Loaded {len(alphas)} submitted alphas from cache")
                    return alphas[:max_alphas]
        except Exception as e:
            logger.warning(f"Failed to load submitted alphas cache: {e}")

    # 从 API 获取 - 使用正确的端点
    try:
        response = sess.get(
            'https://api.worldquantbrain.com/users/self/alphas',
            params={
                'limit': 50,
                'offset': 0,
                'status!': 'UNSUBMITTED\x1fIS-FAIL',  # 排除未提交和失败的
                'order': '-dateSubmitted',  # 按提交日期倒序
                'hidden': 'false'
            },
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            for alpha in data.get('results', []):
                expression = alpha.get('regular', {}).get('code', '').strip()
                fitness = alpha.get('is', {}).get('fitness')
                if expression and fitness:
                    alphas.append({
                        "expression": expression,
                        "fitness": fitness,
                        "sharpe": alpha.get('is', {}).get('sharpe'),
                        "turnover": alpha.get('is', {}).get('turnover'),
                        "dateSubmitted": alpha.get('dateSubmitted'),
                        "grade": alpha.get('grade'),
                        "status": alpha.get('status'),
                    })

            # 保存缓存
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(alphas, f, indent=2)
            logger.info(f"Fetched and cached {len(alphas)} submitted alphas")
        else:
            logger.warning(f"Failed to fetch submitted alphas: {response.status_code}")
    except Exception as e:
        logger.warning(f"Failed to fetch submitted alphas: {e}")

    return alphas[:max_alphas]


def load_knowledge_base(randomize: bool = True) -> str:
    """加载 WorldQuant Brain 知识库，智能分段加载，支持随机章节选择

    Args:
        randomize: 是否随机选择章节（而非按优先级顺序）
    """
    knowledge_parts = []

    # 知识库文件及其关键章节（按优先级）
    # 注意：worldquant_data_fields_reference.md 与 load_data_fields_reference() 功能重叠
    # 字段信息通过 load_data_fields_reference() 动态加载，这里不重复加载
    knowledge_config = [
        {
            'filename': 'worldquantbrain_alpha_guide.md',
            'key_sections': ['Best Practices', 'Common Patterns', 'Tips'],
            'max_chars': 1500
        },
        {
            'filename': 'worldquantbrain_alpha_templates.md',
            'key_sections': ['Templates', 'Examples'],
            'max_chars': 1500
        },
        {
            'filename': 'worldquantbrain_datasets_reference.md',
            'key_sections': ['Popular Fields', 'Categories'],
            'max_chars': 1000
        },
        {
            'filename': 'worldquant_community_knowledge.md',
            'key_sections': ['模拟设置', 'Alpha 研究', '操作符技巧', '常见问题'],
            'max_chars': 2000
        },
    ]

    for config in knowledge_config:
        filename = config['filename']
        filepath = os.path.join(KNOWLEDGE_BASE_PATH, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 提取主要内容（跳过 frontmatter）
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        content = parts[2].strip()

                # 智能提取关键章节
                extracted = extract_key_sections(content, config['key_sections'], randomize=randomize)

                # 如果没有找到关键章节，使用前 N 字符
                if not extracted:
                    extracted = content[:config['max_chars']]

                # 截断到最大长度
                if len(extracted) > config['max_chars']:
                    extracted = extracted[:config['max_chars']] + "..."

                knowledge_parts.append(f"### {filename}\n{extracted}")
            except Exception as e:
                logger.warning(f"Failed to load knowledge file {filename}: {e}")

    return "\n\n".join(knowledge_parts)


def extract_key_sections(content: str, key_sections: List[str], randomize: bool = False) -> str:
    """从内容中提取关键章节，支持随机选择

    Args:
        content: 文档内容
        key_sections: 关键章节关键词列表
        randomize: 是否随机选择章节（而非按顺序）
    """
    extracted = []
    lines = content.split('\n')
    current_section = None
    section_content = []

    for line in lines:
        # 检测章节标题 (## 或 ###)
        if line.startswith('## ') or line.startswith('### '):
            # 保存上一个章节
            if current_section and section_content:
                extracted.append(f"**{current_section}**\n" + '\n'.join(section_content[:10]))
            # 开始新章节
            current_section = line.lstrip('#').strip()
            section_content = []
        elif current_section:
            section_content.append(line)

    # 保存最后一个章节
    if current_section and section_content:
        extracted.append(f"**{current_section}**\n" + '\n'.join(section_content[:10]))

    # 过滤出关键章节
    result = []
    for section in extracted:
        for key in key_sections:
            if key.lower() in section.lower():
                result.append(section)
                break

    # 随机化：打乱章节顺序
    if randomize and len(result) > 1:
        random.shuffle(result)

    return '\n\n'.join(result)


def load_data_fields_reference(max_fields: int = 80, randomize: bool = True) -> str:
    """加载数据字段参考，用于 prompt 增强，支持随机化字段顺序

    Args:
        max_fields: 最大加载数量
        randomize: 是否随机选择字段（而非按覆盖率排序）
    """
    fields_file = os.path.join(KNOWLEDGE_BASE_PATH, "worldquant_data_fields.json")

    if not os.path.exists(fields_file):
        return ""

    try:
        with open(fields_file, 'r', encoding='utf-8') as f:
            all_fields = json.load(f)

        # 按数据集分组
        datasets = {}
        for field in all_fields:
            dataset_name = field.get('dataset', {}).get('name', 'Unknown')
            if dataset_name not in datasets:
                datasets[dataset_name] = []
            datasets[dataset_name].append({
                'id': field.get('id'),
                'description': field.get('description', '')[:80],
                'type': field.get('type', ''),
                'coverage': field.get('coverage', 0)
            })

        # 选择高覆盖率字段
        selected_fields = []
        for dataset_name, fields in datasets.items():
            if randomize:
                # 随机打乱后选择
                shuffled = fields.copy()
                random.shuffle(shuffled)
                for field in shuffled[:8]:
                    selected_fields.append({
                        'dataset': dataset_name,
                        **field
                    })
                    if len(selected_fields) >= max_fields:
                        break
            else:
                # 按覆盖率排序
                sorted_fields = sorted(fields, key=lambda x: x['coverage'], reverse=True)
                for field in sorted_fields[:8]:
                    selected_fields.append({
                        'dataset': dataset_name,
                        **field
                    })
                    if len(selected_fields) >= max_fields:
                        break
            if len(selected_fields) >= max_fields:
                break

        # 格式化输出
        lines = ["## 高覆盖率数据字段\n"]
        current_dataset = None

        # 随机化时打乱整体顺序
        if randomize:
            random.shuffle(selected_fields)
        else:
            selected_fields = sorted(selected_fields, key=lambda x: (x['dataset'], -x['coverage']))

        for field in selected_fields:
            if field['dataset'] != current_dataset:
                current_dataset = field['dataset']
                lines.append(f"\n### {current_dataset}\n")
            lines.append(f"- `{field['id']}`: {field['description']} (覆盖率: {field['coverage']}%)\n")

        return ''.join(lines)

    except Exception as e:
        logger.warning(f"Failed to load data fields: {e}")
        return ""


def _get_random_strategy_hints() -> str:
    """获取随机策略提示，增加生成多样性"""
    strategies = [
        "考虑使用时间序列操作符（ts_mean, ts_std_dev, ts_rank）捕捉动量或反转信号",
        "尝试组合多个数据字段，使用算术操作符（add, subtract, multiply, divide）",
        "使用 rank 或 zscore 进行横截面标准化，减少行业偏差",
        "关注财务数据（fundamental）与市场数据（model）的交互",
        "考虑使用 group 操作符进行行业中性化",
        "尝试使用逻辑操作符（greater, less, if_else）构建条件表达式",
        "关注新闻和分析师数据（news, analyst）的情绪信号",
        "使用 ts_decay 或 ts_product 捕捉趋势衰减",
        "考虑使用 ts_corr 计算相关性因子",
        "尝试使用 ts_delta 或 ts_pct_change 捕捉变化率",
    ]
    # 随机选择 3-5 条策略
    num_hints = random.randint(3, 5)
    selected = random.sample(strategies, num_hints)
    return "\n".join([f"- {hint}" for hint in selected])


def _get_random_example_format() -> str:
    """获取随机示例格式，增加 prompt 多样性"""
    examples = [
        """Example format:
ts_std_dev(cashflow_op, 180)
rank(divide(revenue, assets))
market_ret = ts_product(1+group_mean(returns,1,market),250)-1;rfr = vec_avg(fnd6_newqeventv110_optrfrq);expected_return = rfr+beta_last_360_days_spy*(market_ret-rfr);actual_return = ts_product(returns+1,250)-1;actual_return-expected_return""",
        """Example format:
ts_rank(volume, 20)
zscore(eps_estimate, industry)
group_neutralize(ts_mean(returns, 10), sector)""",
        """Example format:
rank(ts_delta(close, 5))
divide(ts_sum(earnings, 60), ts_sum(revenue, 60))
if_else(greater(sharpe, 1), rank(returns), rank(-returns))""",
    ]
    return random.choice(examples)


class RetryQueue:
    def __init__(self, generator, max_retries=3, retry_delay=60):
        self.queue = Queue()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.generator = generator  # Store reference to generator
        self.worker = Thread(target=self._process_queue, daemon=True)
        self.worker.start()
    
    def add(self, alpha: str, retry_count: int = 0):
        self.queue.put((alpha, retry_count))
    
    def _process_queue(self):
        while True:
            if not self.queue.empty():
                alpha, retry_count = self.queue.get()
                if retry_count >= self.max_retries:
                    logger.error(f"Max retries exceeded for alpha: {alpha}")
                    continue

                try:
                    result = self.generator._test_alpha_impl(alpha)  # Use _test_alpha_impl to avoid recursion
                    if result.get("status") == "error" and "SIMULATION_LIMIT_EXCEEDED" in result.get("message", ""):
                        logger.info(f"Simulation limit exceeded, requeueing alpha: {alpha}")
                        time.sleep(self.retry_delay)
                        self.add(alpha, retry_count + 1)
                    else:
                        self.generator.results.append({
                            "alpha": alpha,
                            "result": result
                        })
                except Exception as e:
                    logger.error(f"Error processing alpha: {str(e)}")
                    
            time.sleep(1)  # Prevent busy waiting

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
        if OPTIMIZER_AVAILABLE and self.llm_client:
            try:
                self.optimizer = AlphaOptimizer(self.llm_client)
                self.alpha_queue = AlphaQueue()
                # 从配置加载优化设置
                self._load_optimization_config()
                logger.info(f"优化器初始化成功 - 启用: {self.optimization_enabled}")
            except Exception as e:
                logger.warning(f"优化器初始化失败: {e}")

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
            'optimize_per_cycle': 5,
            'generate_per_cycle': 5,
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
        logging.info(f"Loading credentials from {credentials_path}")
        with open(credentials_path) as f:
            credentials = json.load(f)
        
        username, password = credentials
        self.sess.auth = HTTPBasicAuth(username, password)
        
        logging.info("Authenticating with WorldQuant Brain...")
        response = self.sess.post('https://api.worldquantbrain.com/authentication', timeout=30)
        logging.info(f"Authentication response status: {response.status_code}")
        logging.debug(f"Authentication response: {response.text[:500]}...")
        
        if response.status_code != 201:
            raise Exception(f"Authentication failed: {response.text}")
    
    def cleanup_vram(self):
        """Perform VRAM cleanup by forcing garbage collection and waiting."""
        try:
            import gc
            gc.collect()
            logging.info("Performed VRAM cleanup")
            # Add a small delay to allow GPU memory to be freed
            time.sleep(2)
        except Exception as e:
            logging.warning(f"VRAM cleanup failed: {e}")
        
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
            print(f"[数据字段获取] 开始获取数据字段，共 {total_datasets} 个数据集...")

            for idx, dataset in enumerate(datasets, 1):
                print(f"[数据字段获取]   [{idx}/{total_datasets}] 正在处理数据集: {dataset}")

                # First get the count
                params = base_params.copy()
                params['dataset.id'] = dataset
                params['limit'] = 1  # Just to get count efficiently

                time.sleep(api_request_delay)  # 请求前等待
                count_response = self.sess.get('https://api.worldquantbrain.com/data-fields', params=params, timeout=30)

                if count_response.status_code == 200:
                    count_data = count_response.json()
                    total_fields = count_data.get('count', 0)
                    print(f"[数据字段获取]     字段总数: {total_fields}")

                    if total_fields > 0:
                        # Generate random offset
                        max_offset = max(0, total_fields - base_params['limit'])
                        random_offset = random.randint(0, max_offset)

                        # Fetch random subset
                        params['offset'] = random_offset
                        params['limit'] = min(20, total_fields)  # Don't exceed total fields

                        time.sleep(api_request_delay)  # 请求前等待
                        response = self.sess.get('https://api.worldquantbrain.com/data-fields', params=params, timeout=30)

                        if response.status_code == 200:
                            data = response.json()
                            fields = data.get('results', [])
                            print(f"[数据字段获取]     ✓ 成功获取 {len(fields)} 个字段")
                            all_fields.extend(fields)
                        else:
                            print(f"[数据字段获取]     ⚠ 获取字段失败: {response.text[:200]}")
                else:
                    print(f"[数据字段获取]     ⚠ 获取字段数量失败: {count_response.text[:200]}")

            # Remove duplicates if any
            unique_fields = {field['id']: field for field in all_fields}.values()
            print(f"[数据字段获取] ✓ 完成! 共获取 {len(unique_fields)} 个唯一字段")
            return list(unique_fields)

        except Exception as e:
            logger.error(f"Failed to fetch data fields: {e}")
            return []

    def get_operators(self) -> List[Dict]:
        """Fetch available operators from WorldQuant Brain."""
        print("Requesting operators...")
        response = self.sess.get('https://api.worldquantbrain.com/operators', timeout=30)
        print(f"Operators response status: {response.status_code}")
        print(f"Operators response: {response.text[:500]}...")  # Print first 500 chars
        
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
        print("Organizing operators by category...")
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

            print("Preparing prompt for LLM...")
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

            # 加载成功的 alpha 模式（随机选择）
            successful_patterns = load_successful_patterns(max_patterns=10, randomize=True)
            success_context = ""
            if successful_patterns:
                success_context = "\n\n### Successful Alpha Patterns (High Fitness, Learn from These):\n"
                for i, pattern in enumerate(successful_patterns[:5], 1):
                    success_context += f"{i}. {pattern['expression'][:80]}\n"
                    success_context += f"   Fitness: {pattern.get('fitness', 'N/A'):.3f}"
                    if pattern.get('sharpe'):
                        success_context += f", Sharpe: {pattern['sharpe']:.2f}"
                    success_context += "\n"

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

            prompt = f"""Generate 5 unique alpha factor expressions using the available operators and data fields. Return ONLY the expressions, one per line, with no comments or explanations.

Available Data Fields:
{[field['id'] for field in data_fields]}

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
{error_context}{knowledge_context}{fields_ref_context}{success_context}{submitted_context}
Requirements:
1. Let your intuition guide you.
2. Use the operators and data fields to create a unique and potentially profitable alpha factor.
3. Anything is possible 42.
4. Avoid using event-type data fields (like nws12_*, fnd6_newqeventv*) with time series operators (ts_rank, ts_sum, etc.) as they don't support event inputs.

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
                print(f"Sending request to LLM ({self.llm_client.get_provider()}: {self.llm_client.get_model_name()})...")
                try:
                    if self.llm_client.is_online():
                        content = self.llm_client.generate(prompt, system_prompt=system_prompt, temperature=0.3, max_tokens=1000)
                    else:
                        content = self.llm_client.generate(prompt, temperature=0.3, max_tokens=1000)
                    print(f"LLM response received ({len(content)} chars)")
                except Exception as e:
                    logging.error(f"LLM request failed: {e}")
                    self._handle_llm_error(str(e))
                    return []
            else:
                # 回退到原有 Ollama 直接调用
                print("Sending request to Ollama API (fallback)...")
                model_name = getattr(self, 'model_name', self.model_fleet[self.current_model_index])
                ollama_data = {
                    'model': model_name,
                    'prompt': prompt,
                    'stream': False,
                    'temperature': 0.3,
                    'top_p': 0.9,
                    'num_predict': 1000
                }

                try:
                    response = requests.post(
                        f'{self.ollama_url}/api/generate',
                        json=ollama_data,
                        timeout=360
                    )

                    print(f"Ollama API response status: {response.status_code}")

                    if response.status_code == 500:
                        logging.error(f"Ollama API returned 500 error: {response.text}")
                        self._handle_llm_error("500_error")
                        return []
                    elif response.status_code != 200:
                        raise Exception(f"Ollama API request failed: {response.text}")

                    response_data = response.json()
                    if 'response' not in response_data:
                        raise Exception(f"Unexpected Ollama API response format: {response_data}")
                    content = response_data['response']

                except requests.exceptions.Timeout:
                    logging.error("Ollama API request timed out (360s)")
                    self._handle_llm_error("timeout")
                    return []
                except requests.exceptions.ConnectionError as e:
                    if "Read timed out" in str(e):
                        logging.error("Ollama API read timeout")
                        self._handle_llm_error("read_timeout")
                        return []
                    else:
                        raise e

            print("Processing LLM response...")

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

            print(f"Generated {len(alpha_ideas)} alpha ideas")
            for i, alpha in enumerate(alpha_ideas, 1):
                print(f"Alpha {i}: {alpha}")

            # Clean and validate ideas
            cleaned_ideas = self.clean_alpha_ideas(alpha_ideas)
            logging.info(f"Found {len(cleaned_ideas)} valid alpha expressions")

            return cleaned_ideas

        except Exception as e:
            if "token limit" in str(e).lower():
                self._hit_token_limit = True
            logging.error(f"Error generating alpha ideas: {str(e)}")
            return []

    def _handle_llm_error(self, error_type: str):
        """Handle LLM errors by downgrading model if needed (only for Ollama)."""
        # 线上模型不需要降级
        if self.llm_client and self.llm_client.is_online():
            logging.warning(f"Online LLM error ({error_type}), will retry with same model")
            return

        self.error_count += 1
        logging.warning(f"Ollama error ({error_type}) - Count: {self.error_count}/{self.max_errors_before_downgrade}")

        if self.error_count >= self.max_errors_before_downgrade:
            self._downgrade_model()
            self.error_count = 0
    
    def _downgrade_model(self):
        """Downgrade to the next smaller model in the fleet."""
        if self.current_model_index >= len(self.model_fleet) - 1:
            logging.error("Already using the smallest model in the fleet!")
            # Reset to initial model if we've exhausted all options
            self.current_model_index = 0
            self.model_name = self.initial_model
            logging.info(f"Reset to initial model: {self.initial_model}")
            return
        
        old_model = self.model_fleet[self.current_model_index]
        self.current_model_index += 1
        new_model = self.model_fleet[self.current_model_index]
        
        logging.warning(f"Downgrading model: {old_model} -> {new_model}")
        self.model_name = new_model
        
        # Update the model in the orchestrator if it exists
        try:
            # Try to update the orchestrator's model fleet manager
            if hasattr(self, 'orchestrator') and hasattr(self.orchestrator, 'model_fleet_manager'):
                self.orchestrator.model_fleet_manager.current_model_index = self.current_model_index
                self.orchestrator.model_fleet_manager.save_state()
                logging.info(f"Updated orchestrator model fleet to use: {new_model}")
        except Exception as e:
            logging.warning(f"Could not update orchestrator model fleet: {e}")
        
        logging.info(f"Successfully downgraded to {new_model}")

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
                    logging.warning(f"Simulation {sim_id} exceeded max check attempts ({max_check_attempts}), marking as failed")
                    completed.append(sim_id)
                    continue

                # Check if simulation has been pending too long (30 minutes)
                if "start_time" not in info:
                    info["start_time"] = time.time()
                elif time.time() - info["start_time"] > 1800:  # 30 minutes
                    logging.warning(f"Simulation {sim_id} has been pending for too long, marking as failed")
                    completed.append(sim_id)
                    continue
                try:
                    sim_progress_resp = self.sess.get(info["progress_url"], timeout=30)
                    logging.info(f"Checking simulation {sim_id} (attempt {info['attempts']}/{max_check_attempts}) for alpha: {info['alpha'][:50]}...")

                    # Handle rate limits
                    if sim_progress_resp.status_code == 429:
                        logging.info("Rate limit hit, will retry later")
                        continue

                    # Handle simulation limits
                    if "SIMULATION_LIMIT_EXCEEDED" in sim_progress_resp.text:
                        logging.info(f"Simulation limit exceeded for alpha: {info['alpha']}")
                        retry_queue.append((info['alpha'], sim_id))
                        continue

                    # 解析响应内容
                    try:
                        sim_result = sim_progress_resp.json()
                    except Exception as json_err:
                        logging.warning(f"Failed to parse simulation response: {json_err}")
                        continue

                    # 检查进度（如果只有 progress 字段，说明还在运行）
                    progress = sim_result.get("progress")
                    status = sim_result.get("status")

                    # 如果有 progress 但没有 status，说明模拟还在运行中
                    if progress is not None and status is None:
                        logging.info(f"Simulation {sim_id} progress: {progress*100:.1f}% - URL: {info['progress_url']}")
                        # 等待 Retry-After 时间后继续检查
                        retry_after = sim_progress_resp.headers.get("Retry-After")
                        if retry_after:
                            try:
                                wait_time = int(float(retry_after))
                                logging.info(f"Waiting {wait_time}s for simulation to complete...")
                                time.sleep(wait_time)
                            except (ValueError, TypeError):
                                time.sleep(5)
                        continue

                    logging.info(f"Simulation {sim_id} status: {status} - URL: {info['progress_url']}")

                    # Log additional details for debugging
                    if status == "PENDING":
                        logging.debug(f"Simulation {sim_id} is pending...")
                    elif status == "RUNNING":
                        logging.debug(f"Simulation {sim_id} is running...")
                    elif status not in ["COMPLETE", "ERROR"]:
                        logging.warning(f"Simulation {sim_id} has unknown status: {status} - URL: {info['progress_url']}")

                    if status == "COMPLETE":
                        alpha_id = sim_result.get("alpha")
                        if alpha_id:
                            alpha_resp = self.sess.get(f'https://api.worldquantbrain.com/alphas/{alpha_id}', timeout=30)
                            if alpha_resp.status_code == 200:
                                alpha_data = alpha_resp.json()
                                fitness = alpha_data.get("is", {}).get("fitness")
                                logging.info(f"Alpha {alpha_id} completed with fitness: {fitness}")

                                self.results.append({
                                    "alpha": info["alpha"],
                                    "result": sim_result,
                                    "alpha_data": alpha_data
                                })

                                # Check if fitness is not None and greater than threshold
                                if fitness is not None and fitness > 0.5:
                                    logging.info(f"Found promising alpha! Fitness: {fitness}")
                                    self.log_hopeful_alpha(info["alpha"], alpha_data)
                                    successful += 1
                                elif fitness is None:
                                    logging.warning(f"Alpha {alpha_id} has no fitness data, skipping hopeful alpha logging")
                    elif status == "ERROR":
                        # 记录详细错误信息
                        error_msg = sim_result.get("message", "Unknown error")
                        error_location = sim_result.get("location", {})
                        logging.error(f"Simulation failed for alpha: {info['alpha']}")
                        logging.error(f"  Error: {error_msg}")
                        if error_location:
                            logging.error(f"  Location: line {error_location.get('line')}, pos {error_location.get('start')}-{error_location.get('end')}")

                        # 保存错误信息到文件，供后续分析和反馈给大模型
                        self._log_simulation_error(info["alpha"], sim_result)
                    completed.append(sim_id)
                    
                except Exception as e:
                    logging.error(f"Error checking result for {sim_id}: {str(e)}")
        
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

    def test_alpha(self, alpha: str) -> Dict:
        result = self._test_alpha_impl(alpha)
        if result.get("status") == "error" and "SIMULATION_LIMIT_EXCEEDED" in result.get("message", ""):
            self.retry_queue.add(alpha)
            return {"status": "queued", "message": "Added to retry queue"}
        return result

    def _test_alpha_impl(self, alpha_expression: str) -> Dict:
        """Implementation of alpha testing with proper URL handling and retry logic."""
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
                    return {"status": "error", "message": sim_resp.text}

                sim_progress_url = sim_resp.headers.get('location')
                if not sim_progress_url:
                    return {"status": "error", "message": "No progress URL received"}

                # 从 URL 中提取真实的模拟 ID
                # URL 格式: https://api.worldquantbrain.com/simulations/{sim_id}
                sim_id = sim_progress_url.rstrip('/').split('/')[-1]

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
        """Log promising alphas to a JSON file."""
        log_file = 'hopeful_alphas.json'

        # Load existing data
        existing_data = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {log_file}, starting fresh")

        # Add new alpha with timestamp
        entry = {
            "expression": expression,  # Store just the expression string
            "timestamp": int(time.time()),
            "alpha_id": alpha_data.get("id", "unknown"),
            "fitness": alpha_data.get("is", {}).get("fitness"),
            "sharpe": alpha_data.get("is", {}).get("sharpe"),
            "turnover": alpha_data.get("is", {}).get("turnover"),
            "returns": alpha_data.get("is", {}).get("returns"),
            "grade": alpha_data.get("grade", "UNKNOWN"),
            "checks": alpha_data.get("is", {}).get("checks", [])
        }

        existing_data.append(entry)

        # Save updated data
        with open(log_file, 'w') as f:
            json.dump(existing_data, f, indent=2)

        print(f"Logged promising alpha to {log_file}")

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

    def optimize_failed_alphas(self) -> List[Dict]:
        """
        优化失败的 Alpha

        Returns:
            优化结果列表
        """
        if not self.optimizer or not self.optimization_enabled:
            logger.info("优化功能未启用")
            return []

        # 设置 WorldQuant 客户端给优化器
        self.optimizer.set_wq_client(self)

        # 获取优化配置
        min_sharpe = self.optimization_config.get('min_sharpe', 1.0)
        top_n = self.optimization_config.get('optimize_per_cycle', 5)
        temperature = self.optimization_config.get('temperature', 0.5)

        logger.info(f"开始优化失败的 Alpha (min_sharpe={min_sharpe}, top_n={top_n})")

        try:
            results = self.optimizer.optimize_top_failed(
                top_n=top_n,
                min_sharpe=min_sharpe,
                temperature=temperature
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

        # Get data fields and operators once
        print("Fetching data fields and operators...")
        data_fields = generator.get_data_fields()
        operators = generator.get_operators()
        
        batch_number = 1
        total_successful = 0

        print(f"Starting continuous alpha mining with batch size {args.batch_size}")
        print(f"Results will be saved to {args.output_dir}")
        print(f"Using Ollama at {args.ollama_url}")

        # 显示优化状态
        if generator.optimization_enabled:
            print(f"优化功能已启用 - 每轮优化 {generator.optimization_config.get('optimize_per_cycle', 5)} 个 Alpha")
        else:
            print("优化功能未启用")

        while True:
            try:
                logger.info(f"\nProcessing batch #{batch_number}")
                logger.info("-" * 50)

                # 1. 生成新 Alpha
                logger.info("步骤 1: 生成新 Alpha...")
                alpha_ideas = generator.generate_alpha_ideas_with_ollama(data_fields, operators)

                # 添加到队列（标记为生成）
                if generator.alpha_queue:
                    for alpha in alpha_ideas:
                        generator.alpha_queue.add_generated(alpha)

                # 2. 优化失败的 Alpha
                if generator.optimization_enabled:
                    logger.info("步骤 2: 优化失败的 Alpha...")
                    try:
                        optimized_results = generator.optimize_failed_alphas()
                        if optimized_results:
                            logger.info(f"优化完成: {len(optimized_results)} 个")
                    except Exception as e:
                        logger.error(f"优化过程出错: {e}")
                else:
                    logger.info("步骤 2: 跳过优化（未启用）")

                # 3. 统一提交测试
                logger.info("步骤 3: 提交测试...")
                batch_successful = generator.test_alpha_batch()
                total_successful += batch_successful

                # 4. 汇报统计
                if generator.alpha_queue and batch_number % 5 == 0:
                    generator.report_optimization_stats()

                # Perform VRAM cleanup every few batches
                generator.operation_count += 1
                if generator.operation_count % generator.vram_cleanup_interval == 0:
                    generator.cleanup_vram()

                # Save batch results
                results = generator.get_results()
                timestamp = int(time.time())
                output_file = os.path.join(args.output_dir, f'batch_{batch_number}_{timestamp}.json')
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)

                logger.info(f"Batch {batch_number} results saved to {output_file}")
                logger.info(f"Batch successful: {batch_successful}")
                logger.info(f"Total successful alphas: {total_successful}")

                batch_number += 1

                # Sleep between batches
                print(f"Sleeping for {args.sleep_time} seconds...")
                sleep(args.sleep_time)

            except Exception as e:
                logger.error(f"Error in batch {batch_number}: {str(e)}")
                logger.info("Sleeping for 5 minutes before retrying...")
                sleep(300)
                continue

    except KeyboardInterrupt:
        logger.info("\nStopping alpha mining...")
        logger.info(f"Total batches processed: {batch_number - 1}")
        logger.info(f"Total successful alphas: {total_successful}")
        return 0

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        return 1


def setup_cleanup_handler(generator):
    """设置 Windows 控制台关闭事件处理器"""
    def cleanup():
        logger.info("Alpha Generator 正在关闭...")
        if generator:
            try:
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
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 收到 Windows 控制台关闭事件 (类型: {ctrl_type})，正在关闭...")
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
