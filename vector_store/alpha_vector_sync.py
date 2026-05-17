# -*- coding: utf-8 -*-
"""
Alpha 数据向量同步服务

将 MySQL 中的 Alpha 数据同步到 ChromaDB 向量数据库
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
import json

from chromadb import PersistentClient

from .store import VectorStore
from .embedding import EmbeddingModel
from .feature_extractor import AlphaFeatureExtractor
from .config import (
    ALPHA_COLLECTIONS,
    ALPHA_SYNC_CONFIG,
    VECTOR_STORE_CONFIG
)

logger = logging.getLogger(__name__)


class AlphaVectorSync:
    """Alpha 数据向量同步服务"""

    def __init__(
        self,
        db_connector,
        persist_directory: Optional[str] = None,
        embedding_model: Optional[EmbeddingModel] = None
    ):
        """
        初始化同步服务

        Args:
            db_connector: MySQL 数据库连接器
            persist_directory: 向量数据库持久化目录
            embedding_model: 嵌入模型实例
        """
        self.db = db_connector

        # 向量存储目录
        if persist_directory is None:
            persist_directory = os.path.join(
                os.path.dirname(__file__),
                'chroma_db'
            )
        self.persist_directory = persist_directory

        # 初始化 ChromaDB 客户端（持久化模式）
        self.client = PersistentClient(path=persist_directory)

        # 嵌入模型
        self.embedder = embedding_model or EmbeddingModel()

        # 特征提取器
        self.feature_extractor = AlphaFeatureExtractor()

        # 同步配置
        self.sync_config = ALPHA_SYNC_CONFIG

        # 初始化集合
        self._init_collections()

    def _init_collections(self):
        """初始化 Alpha 专用集合"""
        for key, config in ALPHA_COLLECTIONS.items():
            try:
                self.client.get_or_create_collection(
                    name=config["name"],
                    metadata={"description": config["description"]}
                )
                logger.info(f"集合已就绪: {config['name']}")
            except Exception as e:
                logger.error(f"初始化集合失败 {config['name']}: {e}")

    def get_collection(self, collection_key: str):
        """获取指定集合"""
        config = ALPHA_COLLECTIONS.get(collection_key)
        if not config:
            raise ValueError(f"未知的集合类型: {collection_key}")
        return self.client.get_collection(config["name"])

    def sync_submitted_alphas(self, limit: int = None) -> int:
        """
        同步已提交 Alpha（最高质量）

        status = ACTIVE 的 Alpha 是已通过 OS 阶段的成功案例

        Args:
            limit: 同步数量限制

        Returns:
            同步的记录数
        """
        limit = limit or self.sync_config["batch_size"]

        # ACTIVE 状态表示已通过 OS 阶段，是真正成功的 Alpha
        sql = """
            SELECT
                a.id,
                a.expression,
                a.grade,
                a.status,
                a.stage,
                a.operator_count,
                a.date_created,
                a.date_submitted,
                p.sharpe,
                p.fitness,
                p.turnover,
                p.returns,
                p.drawdown,
                COUNT(CASE WHEN c.result = 'PASS' AND c.stage = 'IS' THEN 1 END) as checks_pass,
                COUNT(CASE WHEN c.result = 'FAIL' AND c.stage = 'IS' THEN 1 END) as checks_fail
            FROM alpha a
            LEFT JOIN alpha_performance p ON a.id = p.alpha_id AND p.stage = 'OS'
            LEFT JOIN alpha_checks c ON a.id = c.alpha_id
            WHERE a.status = 'ACTIVE'
              AND (a.hidden = FALSE OR a.hidden IS NULL)
            GROUP BY a.id
            ORDER BY p.sharpe DESC
            LIMIT %s
        """

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (limit,))
            alphas = cursor.fetchall()

        if not alphas:
            logger.info("没有找到已提交 Alpha")
            return 0

        logger.info(f"找到 {len(alphas)} 个已提交 Alpha")
        return self._store_alphas(alphas, "submitted_alphas", category="submitted")

    def sync_submittable_alphas(self, limit: int = None) -> int:
        """
        同步可提交 Alpha（次优先级）

        status = UNSUBMITTED 且 IS 检查 7 PASS, 0 FAIL

        Args:
            limit: 同步数量限制

        Returns:
            同步的记录数
        """
        limit = limit or self.sync_config["batch_size"]

        sql = """
            SELECT
                a.id,
                a.expression,
                a.grade,
                a.status,
                a.stage,
                a.operator_count,
                a.date_created,
                p.sharpe,
                p.fitness,
                p.turnover,
                p.returns,
                p.drawdown,
                COUNT(CASE WHEN c.result = 'PASS' AND c.stage = 'IS' THEN 1 END) as checks_pass,
                COUNT(CASE WHEN c.result = 'FAIL' AND c.stage = 'IS' THEN 1 END) as checks_fail
            FROM alpha a
            LEFT JOIN alpha_performance p ON a.id = p.alpha_id AND p.stage = 'IS'
            LEFT JOIN alpha_checks c ON a.id = c.alpha_id
            WHERE a.status = 'UNSUBMITTED'
              AND (a.hidden = FALSE OR a.hidden IS NULL)
            GROUP BY a.id
            HAVING checks_pass = 7 AND checks_fail = 0
            ORDER BY p.sharpe DESC
            LIMIT %s
        """

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (limit,))
            alphas = cursor.fetchall()

        if not alphas:
            logger.info("没有找到可提交 Alpha")
            return 0

        logger.info(f"找到 {len(alphas)} 个可提交 Alpha")
        return self._store_alphas(alphas, "submittable_alphas", category="submittable")

    def sync_failure_alphas(self, limit: int = None) -> int:
        """
        同步失败 Alpha（全量）

        除了已提交(ACTIVE)和可提交之外的 Alpha（IS 检查有 FAIL）

        Args:
            limit: 同步数量限制（None 表示全量）

        Returns:
            同步的记录数
        """
        # 失败 Alpha：不是 ACTIVE，且不是 UNSUBMITTED+7PASS
        sql = """
            SELECT
                a.id,
                a.expression,
                a.grade,
                a.status,
                a.stage,
                a.operator_count,
                a.date_created,
                p.sharpe,
                p.fitness,
                p.turnover,
                p.returns,
                p.drawdown,
                COUNT(CASE WHEN c.result = 'PASS' AND c.stage = 'IS' THEN 1 END) as checks_pass,
                COUNT(CASE WHEN c.result = 'FAIL' AND c.stage = 'IS' THEN 1 END) as checks_fail
            FROM alpha a
            LEFT JOIN alpha_performance p ON a.id = p.alpha_id AND p.stage = 'IS'
            LEFT JOIN alpha_checks c ON a.id = c.alpha_id
            WHERE a.status != 'ACTIVE'
              AND (a.hidden = FALSE OR a.hidden IS NULL)
            GROUP BY a.id
            HAVING checks_fail > 0 OR (a.status != 'UNSUBMITTED' OR checks_pass < 7)
            ORDER BY p.sharpe DESC
        """

        if limit:
            sql += f" LIMIT {limit}"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            alphas = cursor.fetchall()

        if not alphas:
            logger.info("没有找到失败 Alpha")
            return 0

        logger.info(f"找到 {len(alphas)} 个失败 Alpha")

        # 获取失败详情
        alphas_with_fail = []
        for alpha in alphas:
            fail_info = self._get_failure_info(alpha['id'])
            alpha['fail_type'] = fail_info.get('fail_type')
            alpha['fail_check_name'] = fail_info.get('check_name')
            alpha['fail_limit_value'] = fail_info.get('limit_value')
            alpha['fail_actual_value'] = fail_info.get('actual_value')
            alphas_with_fail.append(alpha)

        return self._store_alphas(alphas_with_fail, "failure_alphas", category="failure")

    def sync_optimization_cases(self, limit: int = 100) -> int:
        """
        同步优化成功案例

        Args:
            limit: 同步数量限制

        Returns:
            同步的记录数
        """
        # 检查优化历史表是否存在
        if not self.db.table_exists('alpha_optimization_history'):
            logger.warning("优化历史表不存在，跳过同步")
            return 0

        sql = """
            SELECT
                h.id,
                h.alpha_id,
                h.original_expression,
                h.optimized_expression,
                h.original_sharpe,
                h.original_fitness,
                h.optimized_sharpe,
                h.optimized_fitness,
                h.fail_type,
                h.optimization_method,
                h.success,
                h.created_at
            FROM alpha_optimization_history h
            WHERE h.success = TRUE
            ORDER BY h.created_at DESC
            LIMIT %s
        """

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (limit,))
            cases = cursor.fetchall()

        if not cases:
            logger.info("没有找到优化成功案例")
            return 0

        return self._store_optimization_cases(cases)

    def _get_failure_info(self, alpha_id: str) -> Dict:
        """获取 Alpha 的失败信息"""
        sql = """
            SELECT check_name, result, limit_value, actual_value
            FROM alpha_checks
            WHERE alpha_id = %s AND stage = 'IS' AND result = 'FAIL'
            LIMIT 1
        """

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (alpha_id,))
            result = cursor.fetchone()

        if result:
            return {
                'check_name': result['check_name'],
                'fail_type': result['check_name'],
                'limit_value': float(result['limit_value']) if result['limit_value'] else None,
                'actual_value': float(result['actual_value']) if result['actual_value'] else None
            }
        return {}

    def _store_alphas(self, alphas: List[Dict], collection_key: str, category: str = None) -> int:
        """
        存储 Alpha 到向量数据库

        Args:
            alphas: Alpha 数据列表
            collection_key: 集合键名
            category: 分类标识（submitted/submittable/failure）

        Returns:
            存储的记录数
        """
        if not alphas:
            return 0

        collection = self.get_collection(collection_key)

        # 准备数据
        ids = []
        documents = []
        metadatas = []
        embeddings = []

        for alpha in alphas:
            # 提取特征
            features = self.feature_extractor.extract_features(alpha['expression'])

            # 构建文档文本
            doc_text = self.feature_extractor.build_document_text({
                'expression': alpha['expression'],
                'features': features,
                'sharpe': alpha.get('sharpe'),
                'fitness': alpha.get('fitness'),
                'turnover': alpha.get('turnover'),
                'fail_type': alpha.get('fail_type')
            })

            # 构建元数据（确保所有值都是基本类型，不能是 None）
            metadata = {
                'alpha_id': str(alpha['id']),
                'expression': str(alpha['expression'][:500] if alpha.get('expression') else ''),
                'grade': str(alpha.get('grade') or ''),
                'status': str(alpha.get('status') or ''),
                'stage': str(alpha.get('stage') or ''),
                'category': str(category or alpha.get('status') or ''),
                'sharpe': float(alpha.get('sharpe') or 0),
                'fitness': float(alpha.get('fitness') or 0),
                'turnover': float(alpha.get('turnover') or 0),
                'checks_pass': int(alpha.get('checks_pass') or 0),
                'checks_fail': int(alpha.get('checks_fail') or 0),
                # 特征
                'has_rank': bool(features.get('has_rank', False)),
                'has_ts_rank': bool(features.get('has_ts_rank', False)),
                'has_group_rank': bool(features.get('has_group_rank', False)),
                'has_divide_cap': bool(features.get('has_divide_cap', False)),
                'has_group_neutralize': bool(features.get('has_group_neutralize', False)),
                'outer_operator': str(features.get('outer_operator') or 'none'),
                'time_window': int(features.get('time_window') or 0),
                'operator_count': int(features.get('operator_count') or 0),
                'quality_score': float(features.get('quality_score') or 0),
                # 失败信息
                'fail_type': str(alpha.get('fail_type') or ''),
                'fail_check_name': str(alpha.get('fail_check_name') or ''),
                'fail_limit_value': float(alpha.get('fail_limit_value') or 0),
                'fail_actual_value': float(alpha.get('fail_actual_value') or 0),
                # 时间戳
                'synced_at': datetime.now().isoformat()
            }

            ids.append(f"alpha_{alpha['id']}")
            documents.append(doc_text)
            metadatas.append(metadata)

        # 批量生成向量
        logger.info(f"正在生成 {len(documents)} 个向量...")
        embeddings = self.embedder.embed(documents)

        # 分批存储（ChromaDB 批量限制 5000）
        batch_size = 5000
        total_stored = 0

        try:
            for i in range(0, len(ids), batch_size):
                batch_end = min(i + batch_size, len(ids))
                collection.add(
                    ids=ids[i:batch_end],
                    documents=documents[i:batch_end],
                    embeddings=embeddings[i:batch_end],
                    metadatas=metadatas[i:batch_end]
                )
                total_stored += batch_end - i
                logger.info(f"已存储 {total_stored}/{len(ids)} 条记录")

            logger.info(f"成功存储 {total_stored} 条记录到 {collection_key}")
            return total_stored
        except Exception as e:
            logger.error(f"存储失败: {e}")
            return total_stored

    def _store_optimization_cases(self, cases: List[Dict]) -> int:
        """存储优化案例"""
        if not cases:
            return 0

        collection = self.get_collection("optimization_cases")

        ids = []
        documents = []
        metadatas = []
        embeddings = []

        for case in cases:
            # 构建文档
            doc_text = f"""优化案例:
原始表达式: {case['original_expression']}
优化后表达式: {case['optimized_expression']}
失败类型: {case['fail_type']}
原始 Sharpe: {case['original_sharpe']:.2f}
优化后 Sharpe: {case['optimized_sharpe']:.2f}
优化方法: {case['optimization_method']}
"""

            metadata = {
                'alpha_id': case['alpha_id'],
                'original_expression': case['original_expression'][:500],
                'optimized_expression': case['optimized_expression'][:500],
                'fail_type': case['fail_type'],
                'original_sharpe': float(case['original_sharpe'] or 0),
                'original_fitness': float(case['original_fitness'] or 0),
                'optimized_sharpe': float(case['optimized_sharpe'] or 0),
                'optimized_fitness': float(case['optimized_fitness'] or 0),
                'optimization_method': case['optimization_method'] or '',
                'synced_at': datetime.now().isoformat()
            }

            ids.append(f"opt_{case['id']}")
            documents.append(doc_text)
            metadatas.append(metadata)

        # 生成向量
        embeddings = self.embedder.embed(documents)

        # 存储
        try:
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info(f"成功存储 {len(ids)} 条优化案例")
            return len(ids)
        except Exception as e:
            logger.error(f"存储优化案例失败: {e}")
            return 0

    def full_sync(self) -> Dict:
        """
        执行全量同步

        Returns:
            同步统计信息
        """
        stats = {
            'submitted_alphas': 0,
            'submittable_alphas': 0,
            'failure_alphas': 0,
            'optimization_cases': 0,
            'started_at': datetime.now().isoformat(),
            'errors': []
        }

        try:
            # 清空现有数据
            self._clear_collections()

            # 同步已提交 Alpha（最高优先级）
            stats['submitted_alphas'] = self.sync_submitted_alphas(limit=1000)
        except Exception as e:
            stats['errors'].append(f"同步已提交 Alpha 失败: {e}")
            logger.error(f"同步已提交 Alpha 失败: {e}")

        try:
            # 同步可提交 Alpha（次优先级）
            stats['submittable_alphas'] = self.sync_submittable_alphas(limit=1000)
        except Exception as e:
            stats['errors'].append(f"同步可提交 Alpha 失败: {e}")
            logger.error(f"同步可提交 Alpha 失败: {e}")

        try:
            # 同步失败 Alpha（全量）
            stats['failure_alphas'] = self.sync_failure_alphas(limit=None)
        except Exception as e:
            stats['errors'].append(f"同步失败 Alpha 失败: {e}")
            logger.error(f"同步失败 Alpha 失败: {e}")

        try:
            # 同步优化案例
            stats['optimization_cases'] = self.sync_optimization_cases()
        except Exception as e:
            stats['errors'].append(f"同步优化案例失败: {e}")
            logger.error(f"同步优化案例失败: {e}")

        stats['finished_at'] = datetime.now().isoformat()
        return stats

    def _clear_collections(self):
        """清空 Alpha 集合"""
        for key, config in ALPHA_COLLECTIONS.items():
            try:
                collection = self.get_collection(key)
                # 获取所有 ID 并删除
                results = collection.get()
                if results['ids']:
                    collection.delete(ids=results['ids'])
                    logger.info(f"已清空集合: {config['name']}")
            except Exception as e:
                logger.warning(f"清空集合失败 {config['name']}: {e}")

    def get_stats(self) -> Dict:
        """获取同步统计信息"""
        stats = {}

        for key, config in ALPHA_COLLECTIONS.items():
            try:
                collection = self.get_collection(key)
                stats[key] = {
                    'name': config['name'],
                    'count': collection.count()
                }
            except Exception as e:
                stats[key] = {
                    'name': config['name'],
                    'count': 0,
                    'error': str(e)
                }

        return stats
