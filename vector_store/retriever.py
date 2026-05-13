# -*- coding: utf-8 -*-
"""
知识检索器

从向量数据库中检索相关知识。
"""

from typing import List, Dict, Optional

from .store import VectorStore
from .embedding import EmbeddingModel
from .config import RETRIEVAL_CONFIG


class KnowledgeRetriever:
    """知识检索器"""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_model: Optional[EmbeddingModel] = None
    ):
        """
        初始化检索器

        Args:
            vector_store: 向量存储
            embedding_model: 嵌入模型
        """
        self.store = vector_store or VectorStore()
        self.embedder = embedding_model or EmbeddingModel()

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        layer_filter: Optional[List[str]] = None,
        category_filter: Optional[str] = None
    ) -> str:
        """
        检索相关知识

        Args:
            query: 查询文本
            top_k: 返回结果数量
            layer_filter: 知识层级过滤
            category_filter: 分类过滤

        Returns:
            组装好的知识上下文
        """
        top_k = top_k or RETRIEVAL_CONFIG["default_top_k"]

        # 生成查询向量
        query_embedding = self.embedder.embed_query(query)

        # 构建过滤条件
        where_filter = self._build_filter(layer_filter, category_filter)

        # 执行搜索
        results = self.store.search(
            query_embedding=query_embedding,
            n_results=top_k,
            where=where_filter
        )

        # 组装上下文
        return self._format_results(results)

    def retrieve_raw(
        self,
        query: str,
        top_k: int = None,
        layer_filter: Optional[List[str]] = None,
        category_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        检索原始结果

        Args:
            query: 查询文本
            top_k: 返回结果数量
            layer_filter: 知识层级过滤
            category_filter: 分类过滤

        Returns:
            知识块列表
        """
        top_k = top_k or RETRIEVAL_CONFIG["default_top_k"]

        query_embedding = self.embedder.embed_query(query)
        where_filter = self._build_filter(layer_filter, category_filter)

        results = self.store.search(
            query_embedding=query_embedding,
            n_results=top_k,
            where=where_filter
        )

        items = []
        if results["documents"] and results["documents"][0]:
            for doc, metadata, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            ):
                # 余弦距离转换为相似度 (distance 范围 0-2，相似度 = 1 - distance/2)
                similarity = max(0, 1 - distance / 2)
                items.append({
                    "document": doc,
                    "metadata": metadata,
                    "distance": distance,
                    "similarity": similarity
                })

        return items

    def _build_filter(
        self,
        layer_filter: Optional[List[str]],
        category_filter: Optional[str]
    ) -> Optional[Dict]:
        """构建过滤条件"""
        conditions = []

        if layer_filter:
            conditions.append({"layer": {"$in": layer_filter}})

        if category_filter:
            conditions.append({"category": category_filter})

        if not conditions:
            return None

        if len(conditions) == 1:
            return conditions[0]

        return {"$and": conditions}

    def _format_results(self, results: Dict) -> str:
        """格式化结果"""
        if not results["documents"] or not results["documents"][0]:
            return "未找到相关知识。"

        context_parts = []
        for i, (doc, metadata) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0]
        )):
            source = metadata.get("source", "unknown")
            header1 = metadata.get("header1", "")
            header2 = metadata.get("header2", "")
            header_path = f"{header1} > {header2}" if header2 else header1

            context_parts.append(
                f"[知识 {i+1}] 来源: {source} - {header_path}\n{doc}\n"
            )

        return "\n".join(context_parts)
