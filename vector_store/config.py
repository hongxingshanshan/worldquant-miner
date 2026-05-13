# -*- coding: utf-8 -*-
"""
向量数据库配置
"""

# 嵌入模型配置
EMBEDDING_CONFIG = {
    "model": "paraphrase-multilingual-MiniLM-L12-v2",
    "device": "cpu",
    "batch_size": 32
}

# 分块配置
CHUNKING_CONFIG = {
    "chunk_size": 500,
    "chunk_overlap": 50,
    "min_chunk_size": 100,
    "separators": ["\n\n", "\n", "。", "；", "，", " "]
}

# 检索配置
RETRIEVAL_CONFIG = {
    "default_top_k": 5,
    "alpha_generation_top_k": 5
}

# 向量数据库配置
VECTOR_STORE_CONFIG = {
    "collection_name": "knowledge_chunks",
    "description": "知识库文档块"
}
