"""
Alpha 表达式本地验证器

在不提交到 WorldQuant Brain 平台的情况下，进行本地预筛选：
1. 语法验证：括号匹配、操作符有效性
2. 规则检查：外层排名、市值标准化等关键规则
3. 字段验证：数据字段是否存在
4. 类型兼容性：操作符输入输出类型匹配
"""

import re
import json
import os
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class AlphaValidator:
    """Alpha 表达式本地验证器"""

    # 必须作为外层的排名操作符
    OUTER_RANK_OPERATORS = ['rank', 'ts_rank', 'group_rank']

    # 市值标准化操作符
    CAP_NORMALIZATION = 'divide'

    # 中性化操作符
    NEUTRALIZATION_OPERATORS = ['group_neutralize', 'regression_neut']

    # 时间序列操作符（不支持事件数据）
    TIME_SERIES_OPERATORS = [
        'ts_rank', 'ts_mean', 'ts_sum', 'ts_std_dev', 'ts_max', 'ts_min',
        'ts_delta', 'ts_decay_linear', 'ts_zscore', 'ts_covariance',
        'ts_corr', 'ts_scale', 'ts_product', 'ts_arg_max', 'ts_arg_min'
    ]

    # 事件类型数据字段前缀（不支持时间序列操作）
    EVENT_FIELD_PREFIXES = ['nws12_', 'fnd6_newqeventv']

    # 常见失败检查项的本地检测规则
    FAILURE_RULES = {
        'CONCENTRATED_WEIGHT': {
            'check': 'has_outer_rank',
            'message': '缺少外层排名操作符 (rank/ts_rank/group_rank)'
        },
        'LOW_SUB_UNIVERSE_SHARPE': {
            'check': 'has_neutralization_or_cap_norm',
            'message': '缺少行业中性化或市值标准化'
        },
        'TYPE_MISMATCH': {
            'check': 'type_compatible',
            'message': '操作符类型不兼容'
        }
    }

    def __init__(self, data_fields_path: str = None):
        """
        初始化验证器

        Args:
            data_fields_path: 数据字段 JSON 文件路径
        """
        self.data_fields = {}
        self.operators = {}

        # 加载数据字段
        if data_fields_path:
            self._load_data_fields(data_fields_path)
        else:
            # 尝试从默认路径加载
            default_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'knowledge_base', 'worldquant_data_fields.json'
            )
            if os.path.exists(default_path):
                self._load_data_fields(default_path)

        # 加载操作符定义
        self._load_operators()

    def _load_data_fields(self, path: str):
        """加载数据字段"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                fields = json.load(f)
                self.data_fields = {f['id']: f for f in fields}
                logger.info(f"加载 {len(self.data_fields)} 个数据字段")
        except Exception as e:
            logger.warning(f"加载数据字段失败: {e}")

    def _load_operators(self):
        """加载操作符定义"""
        # 内置操作符类型定义
        self.operators = {
            # 时间序列操作符 (SCALAR -> SCALAR)
            'ts_rank': {'input': 'SCALAR', 'output': 'SCALAR', 'params': ['window']},
            'ts_mean': {'input': 'SCALAR', 'output': 'SCALAR', 'params': ['window']},
            'ts_sum': {'input': 'SCALAR', 'output': 'SCALAR', 'params': ['window']},
            'ts_std_dev': {'input': 'SCALAR', 'output': 'SCALAR', 'params': ['window']},
            'ts_max': {'input': 'SCALAR', 'output': 'SCALAR', 'params': ['window']},
            'ts_min': {'input': 'SCALAR', 'output': 'SCALAR', 'params': ['window']},
            'ts_delta': {'input': 'SCALAR', 'output': 'SCALAR', 'params': ['window']},
            'ts_decay_linear': {'input': 'SCALAR', 'output': 'SCALAR', 'params': ['window']},
            'ts_zscore': {'input': 'SCALAR', 'output': 'SCALAR', 'params': ['window']},
            'ts_covariance': {'input': 'SCALAR', 'output': 'SCALAR', 'params': ['window', 'window']},
            'ts_corr': {'input': 'SCALAR', 'output': 'SCALAR', 'params': ['window']},

            # 截面操作符 (VECTOR -> SCALAR/VECTOR)
            'rank': {'input': 'VECTOR', 'output': 'SCALAR'},
            'group_rank': {'input': 'VECTOR', 'output': 'SCALAR', 'params': ['group']},
            'zscore': {'input': 'VECTOR', 'output': 'SCALAR'},
            'scale': {'input': 'VECTOR', 'output': 'SCALAR'},
            'normalize': {'input': 'VECTOR', 'output': 'SCALAR'},
            'winsorize': {'input': 'VECTOR', 'output': 'SCALAR', 'params': ['threshold']},

            # 中性化操作符
            'group_neutralize': {'input': 'SCALAR', 'output': 'SCALAR', 'params': ['group']},
            'regression_neut': {'input': 'SCALAR', 'output': 'SCALAR', 'params': ['factor']},

            # 算术操作符
            'divide': {'input': 'SCALAR', 'output': 'SCALAR', 'binary': True},
            'multiply': {'input': 'SCALAR', 'output': 'SCALAR', 'binary': True},
            'add': {'input': 'SCALAR', 'output': 'SCALAR', 'binary': True},
            'subtract': {'input': 'SCALAR', 'output': 'SCALAR', 'binary': True},

            # 数学函数
            'log': {'input': 'SCALAR', 'output': 'SCALAR'},
            'abs': {'input': 'SCALAR', 'output': 'SCALAR'},
            'sign': {'input': 'SCALAR', 'output': 'SCALAR'},
            'sqrt': {'input': 'SCALAR', 'output': 'SCALAR'},
            'signed_power': {'input': 'SCALAR', 'output': 'SCALAR', 'params': ['exponent']},
        }

    def validate(self, expression: str) -> Dict:
        """
        验证 Alpha 表达式

        Args:
            expression: Alpha 表达式字符串

        Returns:
            验证结果字典，包含:
            - valid: 是否通过验证
            - syntax_ok: 语法是否正确
            - has_outer_rank: 是否有外层排名
            - has_cap_norm: 是否有市值标准化
            - has_neutralization: 是否有中性化
            - warnings: 警告列表
            - errors: 错误列表
            - predicted_failures: 预测可能失败的检查项
        """
        result = {
            'expression': expression,
            'valid': True,
            'syntax_ok': True,
            'has_outer_rank': False,
            'has_cap_norm': False,
            'has_neutralization': False,
            'warnings': [],
            'errors': [],
            'predicted_failures': [],
            'score': 0  # 验证评分 (0-100)
        }

        # 1. 语法验证
        syntax_result = self._validate_syntax(expression)
        if not syntax_result['ok']:
            result['syntax_ok'] = False
            result['valid'] = False
            result['errors'].append(syntax_result['message'])
            return result

        # 2. 外层排名检查
        if self._has_outer_rank(expression):
            result['has_outer_rank'] = True
            result['score'] += 30
        else:
            result['warnings'].append('缺少外层排名操作符，可能导致 CONCENTRATED_WEIGHT 失败')
            result['predicted_failures'].append('CONCENTRATED_WEIGHT')

        # 3. 市值标准化检查
        if self._has_cap_normalization(expression):
            result['has_cap_norm'] = True
            result['score'] += 20
        else:
            # 检查是否使用了财务数据
            if self._uses_fundamental_data(expression):
                result['warnings'].append('使用了财务数据但缺少市值标准化 divide(field, cap)')
                result['predicted_failures'].append('LOW_SUB_UNIVERSE_SHARPE')

        # 4. 中性化检查
        if self._has_neutralization(expression):
            result['has_neutralization'] = True
            result['score'] += 20

        # 5. 事件数据与时间序列兼容性检查
        if self._has_event_time_series_conflict(expression):
            result['errors'].append('事件类型数据字段不支持时间序列操作符')
            result['valid'] = False
            result['predicted_failures'].append('TYPE_MISMATCH')

        # 6. 数据字段有效性检查
        field_result = self._validate_fields(expression)
        if field_result['unknown_fields']:
            result['warnings'].append(f"未知数据字段: {field_result['unknown_fields']}")

        # 7. 时间窗口合理性检查
        window_result = self._validate_time_windows(expression)
        if window_result['warnings']:
            result['warnings'].extend(window_result['warnings'])

        # 计算最终评分
        result['score'] += 30 if result['syntax_ok'] else 0

        # 综合判断
        if result['errors']:
            result['valid'] = False

        return result

    def _validate_syntax(self, expression: str) -> Dict:
        """验证语法"""
        # 检查括号匹配
        paren_count = expression.count('(') - expression.count(')')
        if paren_count != 0:
            return {
                'ok': False,
                'message': f'括号不匹配: 多 {paren_count} 个括号' if paren_count > 0 else f'括号不匹配: 少 {-paren_count} 个括号'
            }

        # 检查基本结构
        if not expression or len(expression) < 5:
            return {'ok': False, 'message': '表达式过短'}

        # 检查是否包含有效操作符或数据字段
        has_operator = any(op in expression for op in self.operators.keys())
        has_field = any(field in expression for field in ['close', 'open', 'volume', 'cap', 'returns', 'vwap'])

        if not has_operator and not has_field:
            return {'ok': False, 'message': '表达式不包含有效操作符或数据字段'}

        return {'ok': True, 'message': ''}

    def _has_outer_rank(self, expression: str) -> bool:
        """检查是否有外层排名操作符"""
        stripped = expression.strip()
        for op in self.OUTER_RANK_OPERATORS:
            if stripped.startswith(f'{op}('):
                return True
        return False

    def _has_cap_normalization(self, expression: str) -> bool:
        """检查是否有市值标准化"""
        # 检查 divide(..., cap) 模式
        if 'divide(' in expression and ', cap)' in expression:
            return True
        # 也检查简写形式 / cap
        if '/ cap' in expression or '/cap' in expression:
            return True
        return False

    def _has_neutralization(self, expression: str) -> bool:
        """检查是否有中性化"""
        for op in self.NEUTRALIZATION_OPERATORS:
            if op in expression:
                return True
        return False

    def _uses_fundamental_data(self, expression: str) -> bool:
        """检查是否使用财务数据"""
        fundamental_prefixes = ['fnd6_', 'fnd2_', 'fundamental', 'operating_', 'income', 'revenue']
        for prefix in fundamental_prefixes:
            if prefix in expression.lower():
                return True
        return False

    def _has_event_time_series_conflict(self, expression: str) -> bool:
        """检查事件数据与时间序列操作符冲突"""
        # 检查是否使用了事件类型数据
        uses_event_data = any(prefix in expression for prefix in self.EVENT_FIELD_PREFIXES)

        # 检查是否使用了时间序列操作符
        uses_time_series = any(op in expression for op in self.TIME_SERIES_OPERATORS)

        return uses_event_data and uses_time_series

    def _validate_fields(self, expression: str) -> Dict:
        """验证数据字段"""
        result = {'unknown_fields': [], 'valid_fields': []}

        # 提取可能的字段名
        # 匹配模式: 字母开头，包含字母、数字、下划线的标识符
        potential_fields = re.findall(r'[a-zA-Z][a-zA-Z0-9_]*', expression)

        # 过滤掉操作符
        operators_lower = {op.lower() for op in self.operators.keys()}
        keywords = {'industry', 'sector', 'subindustry', 'cap', 'close', 'open', 'high', 'low',
                   'volume', 'vwap', 'returns', 'adv20', 'true', 'false', 'nan'}

        for field in potential_fields:
            field_lower = field.lower()
            if field_lower in operators_lower or field_lower in keywords:
                continue

            # 检查是否是已知字段
            if self.data_fields and field not in self.data_fields:
                # 可能是未知字段，但如果是常见字段则忽略
                if not any(field.startswith(p) for p in ['fnd', 'mdl', 'news', 'analyst', 'est']):
                    result['unknown_fields'].append(field)
            else:
                result['valid_fields'].append(field)

        return result

    def _validate_time_windows(self, expression: str) -> Dict:
        """验证时间窗口参数"""
        result = {'warnings': []}

        # 提取数字参数（可能是时间窗口）
        numbers = re.findall(r',\s*(\d+)\s*\)', expression)

        for num in numbers:
            window = int(num)
            if window < 5:
                result['warnings'].append(f'时间窗口 {window} 过短，建议至少 20 天')
            elif window > 250:
                result['warnings'].append(f'时间窗口 {window} 过长，建议不超过 120 天')

        return result

    def batch_validate(self, expressions: List[str]) -> List[Dict]:
        """
        批量验证多个表达式

        Args:
            expressions: 表达式列表

        Returns:
            验证结果列表
        """
        results = []
        for expr in expressions:
            results.append(self.validate(expr))
        return results

    def filter_valid(self, expressions: List[str], min_score: int = 50) -> List[str]:
        """
        筛选通过验证的表达式

        Args:
            expressions: 表达式列表
            min_score: 最低评分阈值

        Returns:
            通过验证的表达式列表
        """
        valid = []
        for expr in expressions:
            result = self.validate(expr)
            if result['valid'] and result['score'] >= min_score:
                valid.append(expr)
        return valid

    def get_validation_summary(self, expressions: List[str]) -> Dict:
        """
        获取批量验证摘要

        Args:
            expressions: 表达式列表

        Returns:
            摘要统计
        """
        results = self.batch_validate(expressions)

        summary = {
            'total': len(expressions),
            'valid': sum(1 for r in results if r['valid']),
            'invalid': sum(1 for r in results if not r['valid']),
            'has_outer_rank': sum(1 for r in results if r['has_outer_rank']),
            'has_cap_norm': sum(1 for r in results if r['has_cap_norm']),
            'has_neutralization': sum(1 for r in results if r['has_neutralization']),
            'predicted_failures': {},
            'avg_score': sum(r['score'] for r in results) / len(results) if results else 0
        }

        # 统计预测失败类型
        for r in results:
            for fail in r['predicted_failures']:
                summary['predicted_failures'][fail] = summary['predicted_failures'].get(fail, 0) + 1

        return summary


# 使用示例
if __name__ == '__main__':
    validator = AlphaValidator()

    # 测试表达式
    test_alphas = [
        'rank(ts_zscore(divide(close, cap), 60))',  # 好
        'ts_rank(divide(volume, cap), 40)',  # 好
        'group_neutralize(ts_decay_linear(returns, 10), industry)',  # 好
        'divide(close, cap)',  # 缺少外层排名
        'ts_mean(fnd6_oiadps, 60)',  # 财务数据缺少市值标准化
        'rank(nws12_sentiment)',  # 事件数据
        'ts_rank(nws12_sentiment, 20)',  # 事件数据 + 时间序列（冲突）
    ]

    print("=== Alpha 表达式验证测试 ===")
    for alpha in test_alphas:
        result = validator.validate(alpha)
        print(f"\n表达式: {alpha}")
        print(f"  有效: {result['valid']}")
        print(f"  评分: {result['score']}")
        print(f"  外层排名: {result['has_outer_rank']}")
        print(f"  市值标准化: {result['has_cap_norm']}")
        print(f"  中性化: {result['has_neutralization']}")
        if result['warnings']:
            print(f"  警告: {result['warnings']}")
        if result['errors']:
            print(f"  错误: {result['errors']}")
        if result['predicted_failures']:
            print(f"  预测失败: {result['predicted_failures']}")