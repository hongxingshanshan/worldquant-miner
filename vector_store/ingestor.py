# -*- coding: utf-8 -*-
"""
知识入库处理器

将知识库文档入库到向量数据库。
"""

import os
import hashlib
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime

from .store import VectorStore
from .embedding import EmbeddingModel
from .chunker import chunk_document


class KnowledgeIngestor:
    """知识入库处理器"""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        knowledge_base_path: Optional[str] = None
    ):
        """
        初始化入库处理器

        Args:
            vector_store: 向量存储
            embedding_model: 嵌入模型
            knowledge_base_path: 知识库路径
        """
        self.store = vector_store or VectorStore()
        self.embedder = embedding_model or EmbeddingModel()

        # 默认知识库路径
        if knowledge_base_path is None:
            knowledge_base_path = os.path.join(
                os.path.dirname(__file__),
                '..',
                'knowledge_base'
            )
        self.kb_path = knowledge_base_path

    def ingest_file(
        self,
        file_path: str,
        layer: str = "technical_methods",
        category: str = "general"
    ) -> int:
        """
        将单个文件入库

        Args:
            file_path: 文件路径
            layer: 知识层级
            category: 分类标签

        Returns:
            入库的块数量
        """
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        source = os.path.basename(file_path)

        # 先删除该文件的旧数据
        self.store.delete_by_source(source)

        # 分块
        chunks = chunk_document(content, source)

        # 过滤空块
        chunks = [c for c in chunks if c and c.page_content.strip()]

        if not chunks:
            return 0

        # 生成向量
        texts = [chunk.page_content for chunk in chunks]
        embeddings = self.embedder.embed(texts)

        # 生成 ID 和元数据
        ids = []
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(
                f"{source}_{i}_{chunk.page_content[:50]}".encode()
            ).hexdigest()[:16]
            ids.append(chunk_id)

            metadata = {
                **chunk.metadata,
                "layer": layer,
                "category": category,
                "created_at": datetime.now().isoformat()
            }
            metadatas.append(metadata)

        # 存入向量数据库
        self.store.add_chunks(
            chunks=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        return len(chunks)

    def ingest_knowledge_base(self) -> Dict[str, int]:
        """
        入库整个知识库

        Returns:
            各文件的入库统计
        """
        stats = {}

        # 遍历知识库目录
        kb_path = Path(self.kb_path)
        if not kb_path.exists():
            print(f"知识库目录不存在: {self.kb_path}")
            return stats

        for file_path in kb_path.glob("*.md"):
            if file_path.name.startswith("."):
                continue

            print(f"正在处理: {file_path.name}")

            count = self.ingest_file(
                str(file_path),
                layer=self._infer_layer(file_path.name),
                category=self._infer_category(file_path.name)
            )
            stats[file_path.name] = count

            print(f"  - 入库 {count} 个知识块")

        return stats

    def _infer_layer(self, filename: str) -> str:
        """根据文件名推断知识层级"""
        filename_lower = filename.lower()

        if "basic" in filename_lower or "概念" in filename:
            return "basic_concepts"
        elif "advanced" in filename_lower or "高级" in filename:
            return "advanced_strategies"
        elif "experience" in filename_lower or "经验" in filename:
            return "practical_experience"
        else:
            return "technical_methods"

    def _infer_category(self, filename: str) -> str:
        """根据文件名推断分类"""
        filename_lower = filename.lower()

        if "momentum" in filename_lower or "动量" in filename:
            return "momentum"
        elif "volume" in filename_lower or "量价" in filename:
            return "volume"
        elif "data" in filename_lower or "数据" in filename or "field" in filename_lower:
            return "data_fields"
        elif "community" in filename_lower or "知识" in filename:
            return "community_knowledge"
        else:
            return "general"

    def get_stats(self) -> Dict:
        """获取向量数据库统计信息"""
        return self.store.get_stats()
