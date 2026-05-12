#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
三层提示词架构 + 成功模式学习器

架构说明:
第一层 - 核心骨架: 固定的 Alpha 生成模式，确保基本质量
第二层 - 随机探索: 可变的元素组合，增加多样性
第三层 - 质量门: 验证规则，过滤低质量输出

成功模式学习:
- 从成功 Alpha 中提取模式
- 更新模式权重
- 固化到知识链
"""

import os
import json
import random
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ThreeLayerPromptArchitecture:
    """三层提示词架构"""

    def __init__(self, knowledge_chain_path: str = None):
        """
        初始化三层架构

        Args:
            knowledge_chain_path: 知识链文件路径
        """
        self.knowledge_chain_path = knowledge_chain_path
        self.knowledge_chain = self._load_knowledge_chain()

        # 第一层：核心骨架（固定模式）
        self.core_skeleton = self._build_core_skeleton()

        # 第二层：随机探索（可变元素）
        self.random_exploration = self._build_random_exploration()

        # 第三层：质量门（验证规则）
        self.quality_gate = self._build_quality_gate()

    def _load_knowledge_chain(self) -> Dict:
        """加载知识链"""
        if self.knowledge_chain_path and os.path.exists(self.knowledge_chain_path):
            try:
                with open(self.knowledge_chain_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载知识链失败: {e}")

        # 返回默认知识链
        return {
            'knowledge_chain': {
                'basic_concepts': [],
                'technical_methods': [],
                'practical_experience': [],
                'advanced_strategies': []
            },
            'key_insights': [],
            'recommended_patterns': []
        }

    def _build_core_skeleton(self) -> Dict:
        """构建核心骨架层

        核心骨架包含:
        - Alpha 基本结构模板
        - 必须包含的元素
        - 基础操作符集合
        """
        chain = self.knowledge_chain.get('knowledge_chain', {})

        # 从知识链提取核心模式
        core_patterns = []
        for concept in chain.get('basic_concepts', []):
            pattern = concept.get('concept', '')
            if pattern:
                core_patterns.append(pattern)

        # 默认核心骨架
        skeleton = {
            # Alpha 基本结构
            'structure_templates': [
                'operator(data_field)',
                'operator1(operator2(data_field))',
                'operator(ts_operator(data_field, window))',
                'group_operator(operator(data_field), group)',
            ],

            # 必须包含的元素
            'required_elements': {
                'data_field': True,      # 必须有数据字段
                'operator': True,        # 必须有操作符
                'valid_syntax': True,    # 语法必须有效
            },

            # 基础操作符集合（高频使用）
            'core_operators': [
                'rank', 'zscore', 'ts_rank', 'ts_zscore',
                'ts_delta', 'ts_sum', 'ts_mean', 'ts_std_dev',
                'group_rank', 'group_mean', 'group_std_dev'
            ],

            # 从知识链提取的模式
            'knowledge_patterns': core_patterns,

            # 生成约束
            'constraints': {
                'max_length': 200,       # Alpha 最大长度
                'max_nesting': 3,        # 最大嵌套层数
                'min_sharpe': 1.0,      # 最低 Sharpe 要求
                'min_fitness': 0.5,     # 最低 Fitness 要求
            }
        }

        return skeleton

    def _build_random_exploration(self) -> Dict:
        """构建随机探索层

        随机探索包含:
        - 可选操作符池
        - 数据字段采样
        - 参数范围
        - 策略提示
        """
        chain = self.knowledge_chain.get('knowledge_chain', {})

        # 从知识链提取技术方法
        technical_methods = []
        for method in chain.get('technical_methods', []):
            method_name = method.get('method', '')
            if method_name:
                technical_methods.append({
                    'name': method_name,
                    'practice': method.get('best_practice', '')
                })

        exploration = {
            # 可选操作符池（随机采样）
            'operator_pool': {
                'basic': ['log', 'sqrt', 'reverse', 'inverse', 'scale_down', 'normalize'],
                'time_series': ['ts_rank', 'ts_zscore', 'ts_delta', 'ts_sum', 'ts_product',
                               'ts_ir', 'ts_std_dev', 'ts_mean', 'ts_skewness', 'ts_kurtosis'],
                'arsenal': ['ts_moment', 'ts_entropy', 'sigmoid', 'signed_power'],
                'group': ['group_rank', 'group_sum', 'group_mean', 'group_std_dev'],
            },

            # 采样权重（可动态调整）
            'operator_weights': {
                'basic': 0.3,
                'time_series': 0.4,
                'arsenal': 0.2,
                'group': 0.1
            },

            # 参数范围（随机选择）
            'parameter_ranges': {
                'window': [5, 10, 20, 30, 60],
                'decay': [0, 1, 2, 3, 5],
                'std': [2, 3, 4, 5],
            },

            # 策略提示（随机选择）
            'strategy_hints': [
                '使用时间序列操作符捕捉动量',
                '使用横截面操作符进行相对排名',
                '使用组合操作符增加复杂度',
                '使用中性化降低风险',
                '使用衰减参数控制换手率',
                '使用分组操作符捕捉行业效应',
                '使用波动率调整信号强度',
                '使用趋势过滤提高稳定性',
            ],

            # 从知识链提取的技术方法
            'knowledge_methods': technical_methods,

            # 随机探索配置
            'exploration_config': {
                'operator_sample_rate': 0.5,    # 操作符采样率
                'field_sample_rate': 0.3,       # 字段采样率
                'hint_sample_rate': 0.4,        # 提示采样率
                'mutation_rate': 0.1,           # 变异率
            }
        }

        return exploration

    def _build_quality_gate(self) -> Dict:
        """构建质量门层

        质量门包含:
        - 语法验证规则
        - 语义检查规则
        - 性能阈值
        - 黑名单规则
        """
        chain = self.knowledge_chain.get('knowledge_chain', {})

        # 从知识链提取实践经验作为质量规则
        quality_rules = []
        for experience in chain.get('practical_experience', []):
            lesson = experience.get('lesson', '')
            if lesson:
                quality_rules.append(lesson)

        # 添加关键洞察
        for insight in self.knowledge_chain.get('key_insights', []):
            quality_rules.append(insight)

        gate = {
            # 语法验证规则
            'syntax_rules': {
                'balanced_parentheses': True,
                'valid_operators': True,
                'valid_fields': True,
                'no_empty_args': True,
            },

            # 语义检查规则
            'semantic_rules': {
                'no_self_reference': True,      # 不能引用自身
                'valid_window': True,           # 窗口参数必须有效
                'compatible_types': True,       # 类型必须兼容
            },

            # 性能阈值
            'performance_thresholds': {
                'min_sharpe': 1.0,
                'min_fitness': 0.5,
                'max_turnover': 0.5,
                'min_margin': 0.01,
                'max_correlation': 0.7,        # 与已有 Alpha 的最大相关性
            },

            # 黑名单规则
            'blacklist': {
                'operators': ['log_diff', 's_log_1p', 'fraction', 'quantile'],
                'patterns': ['NaN', 'Inf', 'division by zero'],
            },

            # 从知识链提取的质量规则
            'knowledge_rules': quality_rules,

            # 验证函数列表
            'validators': [
                'validate_syntax',
                'validate_semantics',
                'validate_performance',
                'validate_blacklist',
            ]
        }

        return gate

    def generate_prompt(self,
                       context: Dict = None,
                       random_seed: int = None) -> str:
        """生成三层架构的提示词

        Args:
            context: 上下文信息
            random_seed: 随机种子（用于可重复性）

        Returns:
            生成的提示词
        """
        if random_seed is not None:
            random.seed(random_seed)

        # 第一层：核心骨架
        skeleton_prompt = self._generate_skeleton_prompt()

        # 第二层：随机探索
        exploration_prompt = self._generate_exploration_prompt()

        # 第三层：质量门
        quality_prompt = self._generate_quality_prompt()

        # 组合三层
        full_prompt = f"""{skeleton_prompt}

{exploration_prompt}

{quality_prompt}
"""

        return full_prompt

    def _generate_skeleton_prompt(self) -> str:
        """生成核心骨架提示词"""
        skeleton = self.core_skeleton

        prompt = """## 核心骨架（必须遵循）

### Alpha 结构模板
"""
        for template in skeleton['structure_templates']:
            prompt += f"- {template}\n"

        prompt += "\n### 核心操作符\n"
        prompt += ", ".join(skeleton['core_operators'])

        prompt += "\n\n### 约束条件\n"
        for key, value in skeleton['constraints'].items():
            prompt += f"- {key}: {value}\n"

        return prompt

    def _generate_exploration_prompt(self) -> str:
        """生成随机探索提示词"""
        exploration = self.random_exploration

        prompt = "## 随机探索（增加多样性）\n\n"

        # 随机采样操作符
        prompt += "### 推荐操作符组合\n"
        for category, ops in exploration['operator_pool'].items():
            weight = exploration['operator_weights'].get(category, 0.25)
            sampled_ops = random.sample(ops, min(3, len(ops)))
            prompt += f"- {category} ({weight*100:.0f}%): {', '.join(sampled_ops)}\n"

        # 随机选择参数
        prompt += "\n### 推荐参数\n"
        for param, values in exploration['parameter_ranges'].items():
            selected = random.choice(values)
            prompt += f"- {param}: {selected}\n"

        # 随机选择策略提示
        prompt += "\n### 策略提示\n"
        hints = random.sample(
            exploration['strategy_hints'],
            min(3, len(exploration['strategy_hints']))
        )
        for hint in hints:
            prompt += f"- {hint}\n"

        # 添加知识链中的技术方法
        if exploration['knowledge_methods']:
            prompt += "\n### 技术方法参考\n"
            for method in random.sample(
                exploration['knowledge_methods'],
                min(2, len(exploration['knowledge_methods']))
            ):
                prompt += f"- {method['name']}: {method['practice']}\n"

        return prompt

    def _generate_quality_prompt(self) -> str:
        """生成质量门提示词"""
        gate = self.quality_gate

        prompt = """## 质量门（必须通过）

### 性能要求
"""
        for key, value in gate['performance_thresholds'].items():
            prompt += f"- {key}: {value}\n"

        prompt += "\n### 禁止使用的操作符\n"
        prompt += ", ".join(gate['blacklist']['operators'])

        prompt += "\n\n### 质量规则\n"
        for rule in random.sample(
            gate['knowledge_rules'],
            min(3, len(gate['knowledge_rules']))
        ) if gate['knowledge_rules'] else []:
            prompt += f"- {rule}\n"

        return prompt

    def validate_alpha(self, alpha: str, metrics: Dict = None) -> Tuple[bool, List[str]]:
        """验证 Alpha 是否通过质量门

        Args:
            alpha: Alpha 表达式
            metrics: 性能指标

        Returns:
            (是否通过, 错误信息列表)
        """
        errors = []
        gate = self.quality_gate

        # 语法验证
        if not self._validate_syntax(alpha):
            errors.append("语法验证失败")

        # 黑名单检查
        for op in gate['blacklist']['operators']:
            if op in alpha:
                errors.append(f"使用了黑名单操作符: {op}")

        for pattern in gate['blacklist']['patterns']:
            if pattern in alpha:
                errors.append(f"包含禁止模式: {pattern}")

        # 性能验证
        if metrics:
            thresholds = gate['performance_thresholds']

            if metrics.get('sharpe', 0) < thresholds['min_sharpe']:
                errors.append(f"Sharpe 低于阈值: {metrics['sharpe']} < {thresholds['min_sharpe']}")

            if metrics.get('fitness', 0) < thresholds['min_fitness']:
                errors.append(f"Fitness 低于阈值: {metrics['fitness']} < {thresholds['min_fitness']}")

            if metrics.get('turnover', 1) > thresholds['max_turnover']:
                errors.append(f"Turnover 高于阈值: {metrics['turnover']} > {thresholds['max_turnover']}")

        return len(errors) == 0, errors

    def _validate_syntax(self, alpha: str) -> bool:
        """验证 Alpha 语法"""
        # 检查括号平衡
        if alpha.count('(') != alpha.count(')'):
            return False

        # 检查是否为空
        if not alpha.strip():
            return False

        # 检查长度
        if len(alpha) > self.core_skeleton['constraints']['max_length']:
            return False

        return True


class SuccessPatternLearner:
    """成功模式学习器"""

    def __init__(self, knowledge_chain_path: str = None):
        """
        初始化学习器

        Args:
            knowledge_chain_path: 知识链文件路径
        """
        self.knowledge_chain_path = knowledge_chain_path
        self.pattern_weights = defaultdict(float)
        self.pattern_counts = defaultdict(int)
        self.success_history = []

    def learn_from_success(self,
                          alpha: str,
                          metrics: Dict,
                          features: Dict = None):
        """从成功的 Alpha 中学习模式

        Args:
            alpha: Alpha 表达式
            metrics: 性能指标
            features: 提取的特征
        """
        # 提取特征
        if features is None:
            features = self._extract_features(alpha)

        # 计算成功得分
        success_score = self._calculate_success_score(metrics)

        # 更新模式权重
        for feature_name, feature_value in features.items():
            pattern_key = f"{feature_name}:{feature_value}"
            self.pattern_counts[pattern_key] += 1

            # 使用指数移动平均更新权重
            old_weight = self.pattern_weights[pattern_key]
            new_weight = success_score
            self.pattern_weights[pattern_key] = 0.7 * old_weight + 0.3 * new_weight

        # 记录成功历史
        self.success_history.append({
            'alpha': alpha,
            'metrics': metrics,
            'features': features,
            'score': success_score,
            'timestamp': datetime.now().isoformat()
        })

        logger.info(f"学习成功模式: {alpha[:50]}... (score: {success_score:.3f})")

    def _extract_features(self, alpha: str) -> Dict:
        """从 Alpha 中提取特征

        Args:
            alpha: Alpha 表达式

        Returns:
            特征字典
        """
        features = {}

        # 操作符特征
        operators = self._extract_operators(alpha)
        features['operator_count'] = len(operators)
        features['top_operator'] = operators[0] if operators else 'none'
        features['operator_types'] = ','.join(sorted(set(operators))[:3])

        # 结构特征
        features['length'] = len(alpha)
        features['nesting_depth'] = alpha.count('(')
        features['has_group_op'] = any(op in alpha for op in ['group_rank', 'group_mean', 'group_std_dev'])
        features['has_ts_op'] = any(op in alpha for op in ['ts_rank', 'ts_zscore', 'ts_mean', 'ts_sum'])

        # 参数特征
        import re
        numbers = re.findall(r'\d+', alpha)
        features['window_size'] = int(numbers[0]) if numbers else 0

        # 复杂度特征
        features['complexity'] = len(operators) + alpha.count('(') * 0.5

        return features

    def _extract_operators(self, alpha: str) -> List[str]:
        """提取 Alpha 中的操作符"""
        import re
        # 匹配操作符模式
        pattern = r'([a-z_]+)\s*\('
        operators = re.findall(pattern, alpha)
        return operators

    def _calculate_success_score(self, metrics: Dict) -> float:
        """计算成功得分

        Args:
            metrics: 性能指标

        Returns:
            成功得分 (0-1)
        """
        sharpe = metrics.get('sharpe', 0)
        fitness = metrics.get('fitness', 0)
        turnover = metrics.get('turnover', 0)

        # 综合评分
        score = (
            min(sharpe / 3.0, 1.0) * 0.4 +      # Sharpe 权重 40%
            min(fitness, 1.0) * 0.4 +            # Fitness 权重 40%
            max(0, 1 - turnover) * 0.2          # Turnover 权重 20%
        )

        return score

    def get_top_patterns(self, top_n: int = 10) -> List[Dict]:
        """获取权重最高的模式

        Args:
            top_n: 返回数量

        Returns:
            模式列表
        """
        sorted_patterns = sorted(
            self.pattern_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            {
                'pattern': pattern,
                'weight': weight,
                'count': self.pattern_counts[pattern]
            }
            for pattern, weight in sorted_patterns[:top_n]
        ]

    def consolidate_to_knowledge_chain(self) -> Dict:
        """将学习到的模式固化到知识链

        Returns:
            更新的知识链
        """
        top_patterns = self.get_top_patterns(20)

        # 构建新的知识链内容
        new_knowledge = {
            'knowledge_chain': {
                'basic_concepts': [],
                'technical_methods': [],
                'practical_experience': [],
                'advanced_strategies': []
            },
            'key_insights': [],
            'recommended_patterns': []
        }

        # 将高频模式添加到推荐模式
        for pattern_info in top_patterns:
            if pattern_info['count'] >= 3:  # 至少出现3次
                new_knowledge['recommended_patterns'].append(
                    f"{pattern_info['pattern']} (权重: {pattern_info['weight']:.3f}, 次数: {pattern_info['count']})"
                )

        # 分析成功历史，提取关键洞察
        if len(self.success_history) >= 5:
            insights = self._analyze_success_patterns()
            new_knowledge['key_insights'].extend(insights)

        return new_knowledge

    def _analyze_success_patterns(self) -> List[str]:
        """分析成功历史，提取关键洞察"""
        insights = []

        # 分析操作符使用频率
        operator_freq = defaultdict(int)
        for record in self.success_history:
            operators = self._extract_operators(record['alpha'])
            for op in operators:
                operator_freq[op] += 1

        # 找出高频操作符
        if operator_freq:
            top_ops = sorted(operator_freq.items(), key=lambda x: x[1], reverse=True)[:3]
            insights.append(f"高频操作符: {', '.join([op for op, _ in top_ops])}")

        # 分析性能分布
        scores = [r['score'] for r in self.success_history]
        avg_score = sum(scores) / len(scores)
        insights.append(f"平均成功得分: {avg_score:.3f}")

        return insights

    def save_state(self, output_path: str):
        """保存学习器状态

        Args:
            output_path: 输出文件路径
        """
        state = {
            'pattern_weights': dict(self.pattern_weights),
            'pattern_counts': dict(self.pattern_counts),
            'success_history': self.success_history[-100:],  # 只保留最近100条
            'saved_at': datetime.now().isoformat()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        logger.info(f"学习器状态已保存: {output_path}")

    def load_state(self, input_path: str):
        """加载学习器状态

        Args:
            input_path: 输入文件路径
        """
        if not os.path.exists(input_path):
            return

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                state = json.load(f)

            self.pattern_weights = defaultdict(float, state.get('pattern_weights', {}))
            self.pattern_counts = defaultdict(int, state.get('pattern_counts', {}))
            self.success_history = state.get('success_history', [])

            logger.info(f"学习器状态已加载: {len(self.success_history)} 条历史记录")

        except Exception as e:
            logger.warning(f"加载学习器状态失败: {e}")


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='三层提示词架构 + 成功模式学习器')
    parser.add_argument('--knowledge-chain', '-k', type=str, help='知识链文件路径')
    parser.add_argument('--generate-prompt', '-g', action='store_true', help='生成提示词')
    parser.add_argument('--seed', '-s', type=int, help='随机种子')
    parser.add_argument('--state-file', '-f', type=str, default='learner_state.json',
                       help='学习器状态文件')

    args = parser.parse_args()

    # 创建三层架构
    architecture = ThreeLayerPromptArchitecture(
        knowledge_chain_path=args.knowledge_chain
    )

    # 创建学习器
    learner = SuccessPatternLearner(
        knowledge_chain_path=args.knowledge_chain
    )

    # 加载学习器状态
    if os.path.exists(args.state_file):
        learner.load_state(args.state_file)

    if args.generate_prompt:
        # 生成提示词
        prompt = architecture.generate_prompt(random_seed=args.seed)
        print(prompt)

    # 保存学习器状态
    learner.save_state(args.state_file)


if __name__ == "__main__":
    main()