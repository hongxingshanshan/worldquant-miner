# -*- coding: utf-8 -*-
"""
Alpha 表达式特征提取器

从 Alpha 表达式中提取结构特征，用于向量化和模式匹配
"""

import re
from typing import Dict, List, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)


class AlphaFeatureExtractor:
    """Alpha 表达式特征提取器"""

    # 操作符模式定义
    RANK_OPERATORS = ['rank', 'ts_rank', 'group_rank']
    NEUTRALIZE_OPERATORS = ['group_neutralize', 'regression_neut']
    TIME_SERIES_OPERATORS = [
        'ts_mean', 'ts_sum', 'ts_std_dev', 'ts_zscore', 'ts_rank',
        'ts_delta', 'ts_decay_linear', 'ts_scale', 'ts_av_diff',
        'ts_min', 'ts_max', 'ts_argmin', 'ts_argmax', 'ts_corr',
        'ts_covariance', 'ts_skewness', 'ts_kurtosis'
    ]

    # 数据集前缀
    DATASET_PREFIXES = [
        'fnd6_', 'fnd2_', 'fnd1_', 'anl4_', 'anl1_', 'anl2_',
        'mktv', 'prc', 'vol', 'cap', 'adv', 'close', 'open',
        'high', 'low', 'volume', 'vwap', 'returns'
    ]

    def __init__(self):
        """初始化特征提取器"""
        pass

    def extract_features(self, expression: str) -> Dict:
        """
        提取表达式的所有特征

        Args:
            expression: Alpha 表达式

        Returns:
            特征字典
        """
        if not expression:
            return {}

        expr = expression.strip().lower()

        features = {
            # 外层操作符
            'outer_operator': self.extract_outer_operator(expr),
            'has_rank': self._has_operator(expr, 'rank'),
            'has_ts_rank': self._has_operator(expr, 'ts_rank'),
            'has_group_rank': self._has_operator(expr, 'group_rank'),

            # 中性化
            'has_group_neutralize': self._has_operator(expr, 'group_neutralize'),
            'has_regression_neut': self._has_operator(expr, 'regression_neut'),

            # 市值标准化
            'has_divide_cap': self._check_divide_cap(expr),

            # 时间序列操作
            'has_time_series': self._has_time_series_operator(expr),
            'time_window': self.extract_time_window(expr),

            # 操作符统计
            'operator_count': self.count_operators(expr),
            'nesting_depth': self.calculate_nesting_depth(expr),

            # 数据字段
            'data_fields': self.extract_data_fields(expr),
            'data_datasets': self.extract_datasets(expr),

            # 特殊模式
            'has_winsorize': self._has_operator(expr, 'winsorize'),
            'has_scale': self._has_operator(expr, 'scale'),
            'has_normalize': self._has_operator(expr, 'normalize'),
            'has_zscore': self._has_operator(expr, 'zscore'),
            'has_signed_power': self._has_operator(expr, 'signed_power'),
        }

        # 计算综合评分
        features['quality_score'] = self._calculate_quality_score(features)

        return features

    def extract_outer_operator(self, expression: str) -> str:
        """
        提取最外层操作符

        Args:
            expression: Alpha 表达式

        Returns:
            最外层操作符名称，如果没有则返回 'none'
        """
        if not expression:
            return 'none'

        expr = expression.strip()

        # 去除空格后检查开头
        expr_lower = expr.lower()

        # 按优先级检查（group_neutralize 可能包含内部 rank）
        if expr_lower.startswith('group_neutralize('):
            # 检查内部是否有 rank
            inner = self._extract_inner_expression(expr, 'group_neutralize')
            if inner:
                inner_op = self.extract_outer_operator(inner)
                if inner_op in self.RANK_OPERATORS:
                    return f'group_neutralize+{inner_op}'
            return 'group_neutralize'

        if expr_lower.startswith('rank('):
            return 'rank'

        if expr_lower.startswith('ts_rank('):
            return 'ts_rank'

        if expr_lower.startswith('group_rank('):
            return 'group_rank'

        if expr_lower.startswith('signed_power('):
            return 'signed_power'

        if expr_lower.startswith('scale('):
            return 'scale'

        if expr_lower.startswith('normalize('):
            return 'normalize'

        if expr_lower.startswith('winsorize('):
            # 检查内部
            inner = self._extract_inner_expression(expr, 'winsorize')
            if inner:
                return f'winsorize+{self.extract_outer_operator(inner)}'
            return 'winsorize'

        return 'none'

    def extract_time_window(self, expression: str) -> Optional[int]:
        """
        提取时间窗口参数

        Args:
            expression: Alpha 表达式

        Returns:
            时间窗口值，如果没有则返回 None
        """
        if not expression:
            return None

        expr = expression.lower()

        # 匹配 ts_xxx(expr, N) 或 ts_xxx(expr, N, M) 中的第一个数字 N
        patterns = [
            r'ts_\w+\([^,]+,\s*(\d+)',           # ts_xxx(field, N)
            r'ts_\w+\([^,]+,\s*\d+\s*,\s*(\d+)', # ts_xxx(field, N, M) 取第二个
        ]

        for pattern in patterns:
            matches = re.findall(pattern, expr)
            if matches:
                try:
                    return int(matches[0])
                except ValueError:
                    continue

        return None

    def extract_data_fields(self, expression: str) -> List[str]:
        """
        提取数据字段名称

        Args:
            expression: Alpha 表达式

        Returns:
            数据字段列表
        """
        if not expression:
            return []

        # 匹配字段名：字母开头，包含字母、数字、下划线
        # 排除操作符名
        all_identifiers = re.findall(r'\b([a-zA-Z][a-zA-Z0-9_]*)\b', expression.lower())

        # 过滤掉操作符和保留字
        operators = {
            'rank', 'ts_rank', 'group_rank', 'ts_mean', 'ts_sum', 'ts_std_dev',
            'ts_zscore', 'ts_delta', 'ts_decay_linear', 'ts_scale', 'ts_av_diff',
            'ts_min', 'ts_max', 'ts_argmin', 'ts_argmax', 'ts_corr', 'ts_covariance',
            'group_neutralize', 'regression_neut', 'divide', 'multiply', 'add',
            'subtract', 'abs', 'log', 'sqrt', 'sign', 'power', 'scale', 'normalize',
            'zscore', 'winsorize', 'signed_power', 'trade_when', 'if_else',
            'industry', 'sector', 'subindustry', 'cap', 'close', 'open', 'high',
            'low', 'volume', 'vwap', 'returns', 'adv20', 'true', 'false', 'nan'
        }

        fields = []
        for ident in all_identifiers:
            if ident not in operators and ident not in fields:
                fields.append(ident)

        return fields[:10]  # 最多返回 10 个字段

    def extract_datasets(self, expression: str) -> List[str]:
        """
        提取数据集名称

        Args:
            expression: Alpha 表达式

        Returns:
            数据集列表
        """
        if not expression:
            return []

        expr = expression.lower()
        datasets = set()

        # 根据前缀识别数据集
        prefix_to_dataset = {
            'fnd6_': 'fundamental6',
            'fnd2_': 'fundamental2',
            'fnd1_': 'fundamental1',
            'anl4_': 'analyst4',
            'anl1_': 'analyst1',
            'anl2_': 'analyst2',
        }

        for prefix, dataset in prefix_to_dataset.items():
            if prefix in expr:
                datasets.add(dataset)

        # 检查市场数据
        market_fields = ['close', 'open', 'high', 'low', 'volume', 'vwap', 'returns', 'cap', 'adv']
        for field in market_fields:
            if field in expr:
                datasets.add('market')
                break

        return list(datasets)

    def count_operators(self, expression: str) -> int:
        """
        统计操作符数量

        Args:
            expression: Alpha 表达式

        Returns:
            操作符数量
        """
        if not expression:
            return 0

        expr = expression.lower()

        # 常见操作符列表
        operators = [
            'rank', 'ts_rank', 'group_rank', 'ts_mean', 'ts_sum', 'ts_std_dev',
            'ts_zscore', 'ts_delta', 'ts_decay_linear', 'ts_scale', 'ts_av_diff',
            'ts_min', 'ts_max', 'ts_argmin', 'ts_argmax', 'ts_corr',
            'group_neutralize', 'regression_neut', 'divide', 'multiply', 'add',
            'subtract', 'abs', 'log', 'sqrt', 'sign', 'power', 'scale', 'normalize',
            'zscore', 'winsorize', 'signed_power', 'trade_when', 'if_else',
            'ts_backfill', 'ts_product', 'ts_quantile'
        ]

        count = 0
        for op in operators:
            # 使用正则匹配操作符调用（后面紧跟括号）
            pattern = rf'\b{op}\s*\('
            matches = re.findall(pattern, expr)
            count += len(matches)

        return count

    def calculate_nesting_depth(self, expression: str) -> int:
        """
        计算嵌套深度

        Args:
            expression: Alpha 表达式

        Returns:
            最大嵌套深度
        """
        if not expression:
            return 0

        max_depth = 0
        current_depth = 0

        for char in expression:
            if char == '(':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == ')':
                current_depth -= 1

        return max_depth

    def _has_operator(self, expression: str, operator: str) -> bool:
        """检查是否包含指定操作符"""
        pattern = rf'\b{operator}\s*\('
        return bool(re.search(pattern, expression))

    def _check_divide_cap(self, expression: str) -> bool:
        """检查是否包含 divide(..., cap) 模式"""
        # 匹配 divide(..., cap) 或 divide(..., cap)
        patterns = [
            r'divide\s*\([^,]+,\s*cap\s*\)',
            r'divide\s*\([^,]+,\s*cap\s*,',
        ]
        for pattern in patterns:
            if re.search(pattern, expression):
                return True
        return False

    def _has_time_series_operator(self, expression: str) -> bool:
        """检查是否包含时间序列操作符"""
        for op in self.TIME_SERIES_OPERATORS:
            if self._has_operator(expression, op):
                return True
        return False

    def _extract_inner_expression(self, expression: str, operator: str) -> Optional[str]:
        """提取操作符内部的子表达式"""
        expr_lower = expression.lower()
        pattern = rf'{operator}\s*\('

        match = re.search(pattern, expr_lower)
        if not match:
            return None

        start = match.end()

        # 找到匹配的右括号
        depth = 1
        pos = start
        while pos < len(expression) and depth > 0:
            if expression[pos] == '(':
                depth += 1
            elif expression[pos] == ')':
                depth -= 1
            pos += 1

        if depth == 0:
            return expression[start:pos-1].strip()

        return None

    def _calculate_quality_score(self, features: Dict) -> float:
        """
        计算表达式质量评分

        基于成功 Alpha 的特征统计：
        - 外层排名: 90% 成功 Alpha 有
        - 市值标准化: 100% 成功 Alpha 有
        - 行业中性化: 35% 成功 Alpha 有

        Args:
            features: 特征字典

        Returns:
            质量评分 (0-1)
        """
        score = 0.0

        # 外层排名（权重 0.4）
        outer_op = features.get('outer_operator', 'none')
        if outer_op in self.RANK_OPERATORS:
            score += 0.4
        elif 'rank' in outer_op:
            score += 0.3

        # 市值标准化（权重 0.3）
        if features.get('has_divide_cap'):
            score += 0.3

        # 行业中性化（权重 0.15）
        if features.get('has_group_neutralize'):
            score += 0.15

        # 时间窗口合理（权重 0.15）
        time_window = features.get('time_window')
        if time_window and 20 <= time_window <= 120:
            score += 0.15
        elif time_window and 10 <= time_window <= 200:
            score += 0.1

        return min(score, 1.0)

    def build_document_text(self, alpha_data: Dict) -> str:
        """
        构建 Alpha 文档文本用于向量化

        Args:
            alpha_data: 包含 expression 和 features 的字典

        Returns:
            文档文本
        """
        parts = []

        # 1. 表达式
        expression = alpha_data.get('expression', '')
        parts.append(f"表达式: {expression}")

        # 2. 特征描述
        features = alpha_data.get('features', {})
        if not features:
            features = self.extract_features(expression)

        feature_desc = []

        # 外层操作符
        outer_op = features.get('outer_operator', 'none')
        if outer_op != 'none':
            feature_desc.append(f"外层使用 {outer_op}() 进行权重分布")
        else:
            feature_desc.append("缺少外层排名操作符")

        # 市值标准化
        if features.get('has_divide_cap'):
            feature_desc.append("使用市值标准化 divide(field, cap)")

        # 行业中性化
        if features.get('has_group_neutralize'):
            feature_desc.append("使用行业中性化")

        # 时间窗口
        time_window = features.get('time_window')
        if time_window:
            feature_desc.append(f"时间窗口 {time_window} 天")

        parts.append("特征: " + ", ".join(feature_desc))

        # 3. 性能指标
        sharpe = alpha_data.get('sharpe') or 0
        fitness = alpha_data.get('fitness') or 0
        turnover = alpha_data.get('turnover') or 0
        parts.append(f"Sharpe: {sharpe:.2f}, Fitness: {fitness:.2f}, Turnover: {turnover:.2f}")

        # 4. 数据字段
        data_fields = features.get('data_fields', [])
        if data_fields:
            parts.append(f"数据字段: {', '.join(data_fields[:5])}")

        # 5. 失败信息
        fail_type = alpha_data.get('fail_type')
        if fail_type:
            parts.append(f"失败类型: {fail_type}")

        return "\n".join(parts)
