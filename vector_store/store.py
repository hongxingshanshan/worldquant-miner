# -*- coding: utf-8 -*-
"""
向量数据库存储管理

使用 ChromaDB 存储和检索向量。
"""

import os
from typing import List, Dict, Optional

import chromadb
from chromadb.config import Settings

from .config import VECTOR_STORE_CONFIG


class VectorStore:
    """向量数据库管理类"""

    def __init__(self, persist_directory: Optional[str] = None):
        """
        初始化向量存储

        Args:
            persist_directory: 持久化目录，默认为 vector_store/chroma_db
        """
        if persist_directory is None:
            persist_directory = os.path.join(
                os.path.dirname(__file__),
                'chroma_db'
            )

        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=persist_directory)

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=VECTOR_STORE_CONFIG["collection_name"],
            metadata={"description": VECTOR_STORE_CONFIG["description"]}
        )

    def add_chunks(
        self,
        chunks: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict],
        ids: List[str]
    ):
        """
        添加知识块

        Args:
            chunks: 文本内容列表
            embeddings: 向量列表
            metadatas: 元数据列表
            ids: ID 列表
        """
        self.collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict] = None,
        collection_name: Optional[str] = None
    ) -> Dict:
        """
        语义搜索

        Args:
            query_embedding: 查询向量
            n_results: 返回结果数量
            where: 元数据过滤条件
            collection_name: 指定集合名称（如 alpha_submitted, alpha_submittable, alpha_failure）

        Returns:
            搜索结果
        """
        # 如果指定了集合名称，使用该集合
        if collection_name:
            try:
                collection = self.client.get_collection(name=collection_name)
            except Exception:
                # 集合不存在，返回空结果
                return {
                    "documents": [[]],
                    "metadatas": [[]],
                    "distances": [[]],
                    "ids": [[]]
                }
        else:
            collection = self.collection

        return collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"]
        )

    def delete_by_source(self, source: str):
        """
        删除指定来源的所有知识块

        Args:
            source: 来源文件名
        """
        # 先查询该来源的所有 ID
        results = self.collection.get(
            where={"source": source}
        )

        if results["ids"]:
            self.collection.delete(ids=results["ids"])

    def delete_all(self):
        """删除所有数据"""
        results = self.collection.get()
        if results["ids"]:
            self.collection.delete(ids=results["ids"])

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_chunks": self.collection.count(),
            "persist_directory": self.persist_directory
        }

    def get_by_ids(self, ids: List[str]) -> Dict:
        """
        根据 ID 获取数据

        Args:
            ids: ID 列表

        Returns:
            数据
        """
        return self.collection.get(ids=ids)
