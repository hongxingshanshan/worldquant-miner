# 向量数据库知识库使用指南

## 快速开始

### 1. 入库知识库

```python
from vector_store.ingestor import KnowledgeIngestor

# 初始化入库处理器
ingestor = KnowledgeIngestor()

# 入库整个知识库
stats = ingestor.ingest_knowledge_base()
print(f"入库完成: {stats}")

# 或入库单个文件
count = ingestor.ingest_file(
    file_path="path/to/file.md",
    layer="technical_methods",  # 知识层级
    category="momentum"          # 分类标签
)
```

### 2. 检索知识

```python
from vector_store.retriever import KnowledgeRetriever

# 初始化检索器
retriever = KnowledgeRetriever()

# 检索相关知识（返回格式化文本）
context = retriever.retrieve(
    query="如何优化 Alpha 的 Sharpe",
    top_k=5
)
print(context)

# 检索原始结果（返回列表）
results = retriever.retrieve_raw(
    query="动量因子",
    top_k=3,
    layer_filter=["technical_methods"],  # 可选：按层级过滤
    category_filter="momentum"            # 可选：按分类过滤
)

for item in results:
    print(f"来源: {item['metadata']['source']}")
    print(f"相似度: {item['similarity']:.2f}")
    print(f"内容: {item['document'][:100]}...")
```

### 3. 论坛帖子采集（支持 LLM 提炼）

论坛采集器支持两种模式：
- **LLM 提炼模式**：使用大模型从原文中提炼关键知识点，提高检索质量
- **原文分块模式**：直接将原文分块入库

```python
from vector_store.forum_fetcher import ForumFetcher

# 初始化采集器（默认启用 LLM 提炼）
fetcher = ForumFetcher(use_llm_extract=True)

# 采集单个帖子（自动提炼知识点）
result = fetcher.fetch_post("https://example.com/forum/post/123")

# 批量采集
urls = [
    "https://example.com/forum/post/1",
    "https://example.com/forum/post/2",
]
results = fetcher.fetch_batch(urls)

# 从文件读取 URL 并采集
results = fetcher.fetch_from_file("urls.txt")

# 切换提炼模式
fetcher.set_extract_mode(False)  # 使用原文分块模式
fetcher.set_extract_mode(True)   # 使用 LLM 提炼模式

# 查看已采集的帖子
posts = fetcher.list_fetched_posts()
for post in posts:
    print(f"{post['title']} - {post['chunk_count']} 个知识块 (提炼: {post['extracted']})")
```

**LLM 提炼效果**：
- 提取核心知识点，去除冗余内容
- 结构化处理：标题、内容、类型、领域
- 提高检索精准度，减少噪音

**提炼后的知识点格式**：
```json
[
    {
        "title": "知识点标题",
        "content": "知识点详细内容",
        "type": "技巧/经验/问题解决/代码示例",
        "domain": "相关领域（如动量因子、数据字段等）"
    }
]
```

### 4. 查看统计信息

```python
from vector_store.store import VectorStore

store = VectorStore()
stats = store.get_stats()
print(f"知识块总数: {stats['total_chunks']}")
print(f"存储位置: {stats['persist_directory']}")
```

## 知识层级说明

| 层级 | 说明 |
|------|------|
| `basic_concepts` | 基础概念 |
| `technical_methods` | 技术方法 |
| `practical_experience` | 实践经验 |
| `advanced_strategies` | 高级策略 |

## 分类标签说明

| 分类 | 说明 |
|------|------|
| `momentum` | 动量相关 |
| `volume` | 量价相关 |
| `data_fields` | 数据字段 |
| `community_knowledge` | 社区知识 |
| `forum_post` | 论坛帖子 |
| `general` | 通用 |

## 配置说明

配置文件位于 `vector_store/config.py`：

```python
# 嵌入模型配置
EMBEDDING_CONFIG = {
    "model": "paraphrase-multilingual-MiniLM-L12-v2",
    "device": "cpu",
    "batch_size": 32
}

# 分块配置
CHUNKING_CONFIG = {
    "chunk_size": 500,      # 每块字符数
    "chunk_overlap": 50,    # 块间重叠
    "min_chunk_size": 100,
    "separators": ["\n\n", "\n", "。", "；", "，", " "]
}

# 检索配置
RETRIEVAL_CONFIG = {
    "default_top_k": 5,
    "alpha_generation_top_k": 5
}
```

## 性能指标

| 指标 | 实测值 |
|------|--------|
| 知识块总数 | 1641 |
| 平均检索延迟 | 17.8ms |
| 平均相似度 | 0.5+ |

## 目录结构

```
vector_store/
├── __init__.py        # 模块导出
├── config.py          # 配置管理
├── embedding.py       # 向量嵌入模型
├── chunker.py         # 文本分块器
├── store.py           # ChromaDB 存储
├── retriever.py       # 知识检索器
├── ingestor.py        # 知识入库处理器
├── forum_fetcher.py   # 论坛帖子采集器
├── README.md          # 使用指南
└── chroma_db/         # 数据存储目录
```

## 常见问题

### Q: 如何更新知识库？

```python
# 重新入库会自动删除旧数据
ingestor.ingest_file("path/to/file.md")
```

### Q: 如何清空向量数据库？

```python
from vector_store.store import VectorStore

store = VectorStore()
store.delete_all()
```

### Q: 如何使用 GPU 加速？

修改 `config.py` 中的 `device` 为 `cuda`：

```python
EMBEDDING_CONFIG = {
    "model": "paraphrase-multilingual-MiniLM-L12-v2",
    "device": "cuda",  # 使用 GPU
    "batch_size": 64   # 可增大批次
}
```
