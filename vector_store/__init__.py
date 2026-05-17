# -*- coding: utf-8 -*-
"""
向量数据库知识库模块

提供知识库的向量化存储和语义检索功能。
"""

from .store import VectorStore
from .embedding import EmbeddingModel
from .chunker import chunk_document
from .retriever import KnowledgeRetriever
from .ingestor import KnowledgeIngestor
from .forum_fetcher import ForumFetcher
from .browser_integration import (
    BrowserFetchIntegration,
    process_browser_snapshot,
    search_knowledge
)
from .feature_extractor import AlphaFeatureExtractor
from .weight_manager import PromptWeightManager, Phase
from .alpha_vector_sync import AlphaVectorSync

__all__ = [
    'VectorStore',
    'EmbeddingModel',
    'chunk_document',
    'KnowledgeRetriever',
    'KnowledgeIngestor',
    'ForumFetcher',
    'BrowserFetchIntegration',
    'process_browser_snapshot',
    'search_knowledge',
    'AlphaFeatureExtractor',
    'PromptWeightManager',
    'Phase',
    'AlphaVectorSync'
]
