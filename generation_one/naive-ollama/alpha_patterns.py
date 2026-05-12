"""
Alpha 模式加载和提示词生成模块

从 alpha_generator_ollama.py 拆分出来，负责：
- 加载成功的 alpha 模式
- 加载已提交的 alpha
- 加载知识库
- 加载数据字段参考
- 生成随机策略提示
"""
import os
import json
import time
import random
from typing import List, Dict

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
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


def get_sampled_field_ids(max_fields: int = 100, randomize: bool = True) -> List[str]:
    """获取采样的数据字段 ID 列表，用于 prompt

    Args:
        max_fields: 最大字段数量
        randomize: 是否随机选择（否则按覆盖率排序）

    Returns:
        字段 ID 列表
    """
    fields_file = os.path.join(KNOWLEDGE_BASE_PATH, "worldquant_data_fields.json")

    if not os.path.exists(fields_file):
        return []

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
                'coverage': field.get('coverage', 0)
            })

        # 从每个数据集选择高覆盖率字段
        selected_ids = []
        for dataset_name, fields in datasets.items():
            if randomize:
                shuffled = fields.copy()
                random.shuffle(shuffled)
                for field in shuffled[:10]:
                    selected_ids.append(field['id'])
                    if len(selected_ids) >= max_fields:
                        break
            else:
                sorted_fields = sorted(fields, key=lambda x: x['coverage'], reverse=True)
                for field in sorted_fields[:10]:
                    selected_ids.append(field['id'])
                    if len(selected_ids) >= max_fields:
                        break
            if len(selected_ids) >= max_fields:
                break

        return selected_ids

    except Exception as e:
        logger.warning(f"Failed to sample field IDs: {e}")
        return []


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


def get_random_strategy_hints() -> str:
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


def get_random_example_format() -> str:
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
