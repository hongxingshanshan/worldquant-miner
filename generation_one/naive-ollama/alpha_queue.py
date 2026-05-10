"""
Alpha 提交队列 - 统一管理生成和优化的 Alpha
"""
from typing import List, Dict, Optional
from datetime import datetime
from collections import deque
import logging

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


class AlphaQueue:
    """Alpha 提交队列"""

    def __init__(self, max_size: int = 1000):
        self.queue = deque(maxlen=max_size)
        self.tested = []
        self.stats = {
            "generated": {"total": 0, "passed": 0, "failed": 0, "submitted": 0},
            "optimized": {"total": 0, "passed": 0, "failed": 0, "submitted": 0}
        }

    def add_generated(self, alpha: str, metadata: Optional[Dict] = None) -> Dict:
        """
        添加生成的 Alpha

        Args:
            alpha: Alpha 表达式
            metadata: 额外元数据

        Returns:
            Alpha 数据对象
        """
        item = {
            "expression": alpha,
            "source": "generated",
            "original_alpha": None,
            "optimization_type": None,
            "metadata": metadata or {},
            "add_time": datetime.now().isoformat(),
            "test_result": None
        }
        self.queue.append(item)
        self.stats["generated"]["total"] += 1
        logger.debug(f"[队列] 添加生成 Alpha: {alpha[:40]}...")
        return item

    def add_optimized(self, alpha: str, original: str, opt_type: str,
                      metadata: Optional[Dict] = None) -> Dict:
        """
        添加优化的 Alpha

        Args:
            alpha: 优化后的 Alpha 表达式
            original: 原始 Alpha 表达式
            opt_type: 优化类型（失败原因）
            metadata: 额外元数据

        Returns:
            Alpha 数据对象
        """
        item = {
            "expression": alpha,
            "source": "optimized",
            "original_alpha": original,
            "optimization_type": opt_type,
            "metadata": metadata or {},
            "add_time": datetime.now().isoformat(),
            "test_result": None
        }
        self.queue.append(item)
        self.stats["optimized"]["total"] += 1
        logger.debug(f"[队列] 添加优化 Alpha ({opt_type}): {original[:30]}... → {alpha[:30]}...")
        return item

    def get_next_batch(self, batch_size: int = 10) -> List[Dict]:
        """
        获取下一批待测试的 Alpha

        Args:
            batch_size: 批次大小

        Returns:
            Alpha 数据列表
        """
        batch = []
        while len(batch) < batch_size and self.queue:
            batch.append(self.queue.popleft())
        return batch

    def record_result(self, alpha: Dict, result: Dict):
        """
        记录测试结果

        Args:
            alpha: Alpha 数据对象
            result: 测试结果
        """
        alpha["test_result"] = result
        alpha["test_time"] = datetime.now().isoformat()
        self.tested.append(alpha)

        source = alpha["source"]
        if result.get("passed") or result.get("is_submittable"):
            self.stats[source]["passed"] += 1
            logger.info(
                f"[通过-{alpha['source']}] {alpha['expression'][:40]}... "
                f"Sharpe: {result.get('sharpe', 0):.2f}"
            )
        else:
            self.stats[source]["failed"] += 1
            logger.debug(
                f"[失败-{alpha['source']}] {alpha['expression'][:40]}... "
                f"原因: {result.get('failed_checks', 'unknown')}"
            )

    def record_submitted(self, alpha: Dict):
        """
        记录已提交的 Alpha

        Args:
            alpha: Alpha 数据对象
        """
        source = alpha["source"]
        self.stats[source]["submitted"] += 1
        logger.info(f"[提交-{source}] {alpha['expression'][:40]}...")

    def get_stats(self) -> Dict:
        """
        获取统计信息

        Returns:
            统计数据
        """
        stats = {
            "queue_size": len(self.queue),
            "tested_count": len(self.tested),
            "generated": dict(self.stats["generated"]),
            "optimized": dict(self.stats["optimized"])
        }

        # 计算通过率
        for source in ["generated", "optimized"]:
            total = self.stats[source]["total"]
            passed = self.stats[source]["passed"]
            stats[source]["pass_rate"] = (passed / total * 100) if total > 0 else 0

        return stats

    def get_recent_tested(self, limit: int = 20) -> List[Dict]:
        """
        获取最近测试的 Alpha

        Args:
            limit: 返回数量

        Returns:
            Alpha 列表
        """
        return self.tested[-limit:]

    def clear(self):
        """清空队列"""
        self.queue.clear()
        logger.info("[队列] 已清空")

    def __len__(self) -> int:
        return len(self.queue)

    def __bool__(self) -> bool:
        """队列对象始终为 True（即使为空）"""
        return True

    def __repr__(self) -> str:
        return (
            f"AlphaQueue(queue={len(self.queue)}, "
            f"tested={len(self.tested)}, "
            f"gen={self.stats['generated']['total']}, "
            f"opt={self.stats['optimized']['total']})"
        )
