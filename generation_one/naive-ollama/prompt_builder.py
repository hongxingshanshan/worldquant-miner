# -*- coding: utf-8 -*-
"""
智能提示词构建器

基于向量数据库检索动态构建 Alpha 生成和优化提示词
支持渐进式知识库建设的三阶段权重切换
"""

from typing import Dict, List, Optional
import logging
import sys
import os

# 添加项目根目录到 Python 路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from vector_store.retriever import KnowledgeRetriever
from vector_store.weight_manager import PromptWeightManager, Phase
from vector_store.config import PROMPT_BUILD_CONFIG

logger = logging.getLogger(__name__)


# ============================================================
# 专家角色提示词（短期阶段使用）
# ============================================================

EXPERT_ROLE_PROMPT = """
你是 WorldQuant Brain 平台的资深量化研究员，拥有 10 年因子研究经验。

## 专业背景
- 熟悉动量、反转、流动性、质量、价值等主流因子类型
- 理解截面排名、时间序列操作、行业中性化等核心技术
- 掌握 Sharpe、Fitness、Turnover 等评估指标的平衡方法

## 核心原则（必须遵守）
1. **外层排名必须**：所有表达式必须使用 rank/ts_rank/group_rank 作为最外层
2. **市值标准化**：财务数据必须 divide(field, cap) 消除市值影响
3. **时间窗口合理**：使用 20-120 天范围，避免过短或过长
4. **权重分散**：确保 CONCENTRATED_WEIGHT 检查通过

## 成功模式（基于数据分析）
- 90% 成功 Alpha 使用外层排名操作符
- 100% 成功 Alpha 使用市值标准化 divide(field, cap)
- 35% 成功 Alpha 使用行业中性化 group_neutralize

## 常见失败原因（避免）
- LOW_FITNESS (39.1%): Sharpe 与 Turnover 不平衡
- LOW_SHARPE (38.4%): 信号强度不足
- LOW_SUB_UNIVERSE_SHARPE (12.1%): 行业中性化不足
- CONCENTRATED_WEIGHT (7.1%): 缺少外层 rank() 操作符

## 生成策略
- 优先使用检索到的成功案例模式（如有）
- 如无相关检索结果，使用你的专业知识生成
- 始终遵循平台语法规范和检查要求
"""


# ============================================================
# 三阶段提示词模板
# ============================================================

SHORT_TERM_TEMPLATE = """
{expert_role}

## 检索参考（如有相关数据）
{retrieved_context}

## 当前任务
- 数据字段: {data_fields}
- 目标数量: {count}

## 输出要求
每行一个表达式，不要编号、注释或解释。
"""

MID_TERM_TEMPLATE = """
你是 WorldQuant Brain 量化研究员，参考以下知识库内容生成 Alpha。

## 知识库检索结果（优先参考）
{retrieved_context}

## 专业补充（当检索不足时使用）
{expert_knowledge}

## 当前任务
- 数据字段: {data_fields}
- 目标数量: {count}

## 输出要求
每行一个表达式，不要编号、注释或解释。
"""

LONG_TERM_TEMPLATE = """
基于知识库生成 Alpha 表达式。

## 成功案例参考（检索自向量库）
{success_cases}

## 失败模式警示（避免以下特征）
{failure_patterns}

## 推荐字段组合
{field_combos}

## 基础约束（必须遵守）
- 外层必须使用 rank/ts_rank/group_rank
- 财务数据必须市值标准化 divide(field, cap)
- 时间窗口 20-120 天

## 当前任务
- 数据字段: {data_fields}
- 目标数量: {count}

## 输出要求
每行一个表达式，不要编号、注释或解释。
"""


# ============================================================
# 优化提示词模板
# ============================================================

OPTIMIZATION_TEMPLATE = """
# Alpha 表达式优化任务

## 原始 Alpha
- 表达式: {original_expression}
- Sharpe: {sharpe:.2f}
- Fitness: {fitness:.2f}
- Turnover: {turnover:.2f}
- 失败检查: {fail_type}

## 相似成功案例（检索自向量库）
{similar_success}

## 同类失败优化成功案例
{optimization_cases}

## 针对性修复知识
{fix_knowledge}

## 失败类型修复指南

### LOW_FITNESS (适应度低)
问题：Sharpe 和 Turnover 不平衡
解决：
- 优化信号质量：rank(ts_mean(expr, 5))
- 平衡收益与成本：expr - 0.1 * abs(delta(expr, 1))
- 添加时间平滑：ts_decay_linear(expr, 5)
- 确保外层有 rank() 或 ts_rank()

### LOW_SHARPE (夏普值过低)
问题：风险调整后收益不足
解决：
- 增强信号强度：scale(expr), normalize(expr)
- 添加动量：ts_delta(expr, 5), ts_momentum(expr, 5)
- 使用排名：rank(expr), group_rank(expr, industry)
- 行业中性化：group_neutralize(expr, industry)

### LOW_SUB_UNIVERSE_SHARPE (子宇宙夏普值低)
问题：在某些行业或市值范围内表现不佳
解决：
- 行业中性化：group_neutralize(expr, industry) - 最重要！
- 板块中性化：group_neutralize(expr, sector)
- 市值标准化：divide(expr, cap)

### CONCENTRATED_WEIGHT (权重集中)
问题：权重过于集中在少数股票
解决：
- 添加外层排名：rank(expr), ts_rank(expr, 20) - 关键！
- 行业中性化：group_neutralize(expr, industry)

## 优化要求
1. 保持核心逻辑，只做最小改动
2. 针对失败类型 {fail_type} 进行修复
3. 确保优化后表达式包含外层排名操作符

## 输出格式
直接输出优化后的表达式，不要包含解释。
"""


class IntelligentPromptBuilder:
    """智能提示词构建器"""

    def __init__(
        self,
        retriever: Optional[KnowledgeRetriever] = None,
        weight_manager: Optional[PromptWeightManager] = None
    ):
        """
        初始化提示词构建器

        Args:
            retriever: 知识检索器
            weight_manager: 权重管理器
        """
        self.retriever = retriever or KnowledgeRetriever()
        self.weight_manager = weight_manager or PromptWeightManager()
        self.config = PROMPT_BUILD_CONFIG

    def build_generation_prompt(
        self,
        data_fields: List[str],
        operators: Dict[str, List] = None,
        context: Dict = None
    ) -> str:
        """
        构建 Alpha 生成提示词

        Args:
            data_fields: 可用数据字段列表
            operators: 操作符分类字典
            context: 额外上下文

        Returns:
            构建好的提示词
        """
        context = context or {}
        phase = self.weight_manager.get_current_phase()
        weights = self.weight_manager.get_current_weights()

        # 检索相关知识
        retrieved_context = self._retrieve_for_generation(data_fields, context)

        # 根据阶段选择模板
        if phase == Phase.SHORT:
            return self._build_short_term_prompt(data_fields, retrieved_context, context)
        elif phase == Phase.MID:
            return self._build_mid_term_prompt(data_fields, retrieved_context, context)
        else:
            return self._build_long_term_prompt(data_fields, retrieved_context, context)

    def build_optimization_prompt(
        self,
        alpha_data: Dict,
        fail_type: str
    ) -> str:
        """
        构建 Alpha 优化提示词

        Args:
            alpha_data: Alpha 数据（包含 expression, sharpe, fitness 等）
            fail_type: 失败类型

        Returns:
            构建好的提示词
        """
        # 检索相似成功案例
        similar_success = self._retrieve_similar_success(alpha_data['expression'])

        # 检索同类失败优化案例
        optimization_cases = self._retrieve_optimization_cases(fail_type)

        # 检索针对性修复知识
        fix_knowledge = self._retrieve_fix_knowledge(fail_type)

        return OPTIMIZATION_TEMPLATE.format(
            original_expression=alpha_data.get('expression', ''),
            sharpe=alpha_data.get('sharpe', 0) or 0,
            fitness=alpha_data.get('fitness', 0) or 0,
            turnover=alpha_data.get('turnover', 0) or 0,
            fail_type=fail_type,
            similar_success=similar_success,
            optimization_cases=optimization_cases,
            fix_knowledge=fix_knowledge
        )

    def _retrieve_for_generation(self, data_fields: List[str], context: Dict) -> str:
        """检索生成相关知识"""
        parts = []

        # 检索成功案例
        try:
            query = f"高 Sharpe 高 Fitness 的成功 Alpha 表达式模式 {', '.join(data_fields[:5])}"
            success_cases = self.retriever.retrieve(
                query=query,
                top_k=self.config.get('success_cases_top_k', 5)
            )
            if success_cases and success_cases != "未找到相关知识。":
                parts.append(f"### 成功案例参考\n{success_cases}")
        except Exception as e:
            logger.warning(f"检索成功案例失败: {e}")

        # 检索失败模式
        try:
            query = "LOW_FITNESS LOW_SHARPE 失败的 Alpha 特征 缺少外层排名"
            failure_patterns = self.retriever.retrieve(
                query=query,
                top_k=self.config.get('failure_patterns_top_k', 3)
            )
            if failure_patterns and failure_patterns != "未找到相关知识。":
                parts.append(f"### 失败模式警示\n{failure_patterns}")
        except Exception as e:
            logger.warning(f"检索失败模式失败: {e}")

        return "\n\n".join(parts) if parts else "暂无相关检索结果"

    def _retrieve_similar_success(self, expression: str) -> str:
        """检索相似成功案例"""
        try:
            return self.retriever.retrieve(
                query=f"成功 Alpha 表达式 {expression[:100]}",
                top_k=3
            )
        except Exception as e:
            logger.warning(f"检索相似成功案例失败: {e}")
            return "暂无相关案例"

    def _retrieve_optimization_cases(self, fail_type: str) -> str:
        """检索同类失败优化案例"""
        try:
            return self.retriever.retrieve(
                query=f"{fail_type} 失败优化成功的案例",
                top_k=self.config.get('optimization_cases_top_k', 5)
            )
        except Exception as e:
            logger.warning(f"检索优化案例失败: {e}")
            return "暂无相关案例"

    def _retrieve_fix_knowledge(self, fail_type: str) -> str:
        """检索针对性修复知识"""
        try:
            return self.retriever.retrieve(
                query=f"如何修复 {fail_type} 检查失败 Alpha",
                top_k=3
            )
        except Exception as e:
            logger.warning(f"检索修复知识失败: {e}")
            return "暂无相关知识"

    def _build_short_term_prompt(
        self,
        data_fields: List[str],
        retrieved_context: str,
        context: Dict
    ) -> str:
        """构建短期阶段提示词"""
        return SHORT_TERM_TEMPLATE.format(
            expert_role=EXPERT_ROLE_PROMPT,
            retrieved_context=retrieved_context,
            data_fields=', '.join(data_fields[:20]) if data_fields else '无',
            count=context.get('count', 20)
        )

    def _build_mid_term_prompt(
        self,
        data_fields: List[str],
        retrieved_context: str,
        context: Dict
    ) -> str:
        """构建中期阶段提示词"""
        expert_knowledge = """
- 外层必须使用 rank/ts_rank/group_rank
- 财务数据必须 divide(field, cap)
- 时间窗口推荐 40-80 天
"""
        return MID_TERM_TEMPLATE.format(
            retrieved_context=retrieved_context,
            expert_knowledge=expert_knowledge,
            data_fields=', '.join(data_fields[:20]) if data_fields else '无',
            count=context.get('count', 20)
        )

    def _build_long_term_prompt(
        self,
        data_fields: List[str],
        retrieved_context: str,
        context: Dict
    ) -> str:
        """构建长期阶段提示词"""
        # 分离成功案例和失败模式
        success_cases = "见上方检索结果"
        failure_patterns = "见上方检索结果"
        field_combos = "见上方检索结果"

        return LONG_TERM_TEMPLATE.format(
            success_cases=success_cases,
            failure_patterns=failure_patterns,
            field_combos=field_combos,
            data_fields=', '.join(data_fields[:20]) if data_fields else '无',
            count=context.get('count', 20)
        )

    def get_status(self) -> Dict:
        """获取构建器状态"""
        return {
            "weight_manager": self.weight_manager.get_status(),
            "config": self.config
        }
