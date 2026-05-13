# -*- coding: utf-8 -*-
"""
向量嵌入模型

使用 sentence-transformers 生成文本向量。
"""

from typing import List, Optional
from sentence_transformers import SentenceTransformer

from .config import EMBEDDING_CONFIG


class EmbeddingModel:
    """向量嵌入模型"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None
    ):
        """
        初始化嵌入模型

        Args:
            model_name: 模型名称，默认使用配置中的模型
            device: 运行设备 (cpu/cuda)
        """
        self.model_name = model_name or EMBEDDING_CONFIG["model"]
        self.device = device or EMBEDDING_CONFIG["device"]
        self.model = SentenceTransformer(self.model_name, device=self.device)

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成文本向量

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """
        生成单个查询向量

        Args:
            query: 查询文本

        Returns:
            向量
        """
        embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embedding[0].tolist()

    def get_dimension(self) -> int:
        """获取向量维度"""
        return self.model.get_sentence_embedding_dimension()
