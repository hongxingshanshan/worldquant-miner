# -*- coding: utf-8 -*-
"""
提示词权重动态管理器

支持渐进式知识库建设的三阶段权重切换
"""

from typing import Dict, Optional
from enum import Enum
import logging

from .config import (
    PROGRESSIVE_PHASE_WEIGHTS,
    PHASE_TRANSITION_CONDITIONS,
    QUALITY_THRESHOLDS
)

logger = logging.getLogger(__name__)


class Phase(Enum):
    """知识库建设阶段"""
    SHORT = "short"   # 短期：专家主导
    MID = "mid"       # 中期：检索主导
    LONG = "long"     # 长期：数据驱动


class PromptWeightManager:
    """提示词权重动态管理器"""

    def __init__(self, initial_phase: Phase = Phase.SHORT):
        """
        初始化权重管理器

        Args:
            initial_phase: 初始阶段，默认为短期
        """
        self.phase = initial_phase
        self.weights = PROGRESSIVE_PHASE_WEIGHTS.copy()
        self.transition_conditions = PHASE_TRANSITION_CONDITIONS.copy()
        self.quality_thresholds = QUALITY_THRESHOLDS.copy()

        # 统计缓存
        self._last_stats: Optional[Dict] = None
        self._transition_log: list = []

    def get_current_weights(self) -> Dict[str, float]:
        """
        获取当前权重配置

        Returns:
            包含 expert 和 retrieval 权重的字典
        """
        return self.weights[self.phase.value]

    def get_current_phase(self) -> Phase:
        """获取当前阶段"""
        return self.phase

    def check_phase_transition(self, stats: Dict) -> str:
        """
        检查是否需要阶段转换

        Args:
            stats: 知识库统计信息
                - total_chunks: 总知识块数
                - external_knowledge: 外部知识数量
                - success_alphas: 成功 Alpha 数量
                - optimization_cases: 优化成功案例数
                - retrieval_hit_rate: 检索命中率
                - avg_similarity: 平均相似度

        Returns:
            转换结果: "transition_to_mid" / "transition_to_long" / "no_transition"
        """
        self._last_stats = stats

        if self.phase == Phase.SHORT:
            conditions = self.transition_conditions["short_to_mid"]
            if self._check_conditions_met(stats, conditions):
                self.phase = Phase.MID
                self._log_transition("short", "mid", stats)
                logger.info(f"阶段转换: SHORT -> MID (知识块: {stats.get('total_chunks', 0)})")
                return "transition_to_mid"

        elif self.phase == Phase.MID:
            conditions = self.transition_conditions["mid_to_long"]
            if self._check_conditions_met(stats, conditions):
                self.phase = Phase.LONG
                self._log_transition("mid", "long", stats)
                logger.info(f"阶段转换: MID -> LONG (知识块: {stats.get('total_chunks', 0)})")
                return "transition_to_long"

        return "no_transition"

    def _check_conditions_met(self, stats: Dict, conditions: Dict) -> bool:
        """检查条件是否满足"""
        for key, threshold in conditions.items():
            value = stats.get(key, 0)
            if isinstance(threshold, dict):
                # 复杂条件（如比率）
                continue
            if value < threshold:
                return False
        return True

    def _log_transition(self, from_phase: str, to_phase: str, stats: Dict):
        """记录阶段转换"""
        self._transition_log.append({
            "from": from_phase,
            "to": to_phase,
            "stats": stats.copy() if stats else {},
            "timestamp": self._get_timestamp()
        })

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()

    def force_phase(self, phase: Phase):
        """
        强制设置阶段（用于测试或手动控制）

        Args:
            phase: 目标阶段
        """
        old_phase = self.phase
        self.phase = phase
        logger.warning(f"强制阶段转换: {old_phase.value} -> {phase.value}")

    def get_expert_weight(self) -> float:
        """获取当前专家角色权重"""
        return self.weights[self.phase.value]["expert"]

    def get_retrieval_weight(self) -> float:
        """获取当前检索权重"""
        return self.weights[self.phase.value]["retrieval"]

    def should_prioritize_expert(self) -> bool:
        """是否应该优先使用专家角色"""
        return self.get_expert_weight() >= self.get_retrieval_weight()

    def should_prioritize_retrieval(self) -> bool:
        """是否应该优先使用检索结果"""
        return self.get_retrieval_weight() > self.get_expert_weight()

    def get_transition_log(self) -> list:
        """获取阶段转换日志"""
        return self._transition_log.copy()

    def get_last_stats(self) -> Optional[Dict]:
        """获取最近的统计信息"""
        return self._last_stats

    def get_status(self) -> Dict:
        """
        获取管理器状态

        Returns:
            包含当前状态信息的字典
        """
        return {
            "phase": self.phase.value,
            "weights": self.get_current_weights(),
            "prioritize_expert": self.should_prioritize_expert(),
            "transition_count": len(self._transition_log),
            "last_stats": self._last_stats
        }

    def reset(self):
        """重置到初始状态"""
        self.phase = Phase.SHORT
        self._last_stats = None
        self._transition_log.clear()
        logger.info("权重管理器已重置到初始状态")
