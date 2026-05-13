# 向量数据库知识库方案设计文档

## 一、问题背景

### 1.1 当前痛点
- **Token 限制**：大文件（如 `worldquant_data_fields_reference.md` 682KB）无法直接输入 LLM
- **语义检索困难**：基于关键词的检索无法理解语义相似性
- **知识更新效率低**：每次更新需要重新处理整个知识库
- **上下文窗口浪费**：无关知识占用宝贵的 token 配额

### 1.2 解决目标
- 支持任意大小的知识库文档
- 实现语义级别的知识检索
- 按需加载相关知识片段
- 支持增量更新和版本管理

---

## 二、技术方案

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        知识处理流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ 原始文档  │ -> │ 文本分块  │ -> │ 向量嵌入  │ -> │ 向量存储  │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │                                                    │    │
│       │  knowledge_base/                                   │    │
│       │  ├── worldquant_community_knowledge.md             │    │
│       │  └── worldquant_data_fields_reference.md           │    │
│       │                                                    │    │
│       v                                                    v    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    ChromaDB 向量数据库                     │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │ Collection: knowledge_chunks                         │ │  │
│  │  │ - id: chunk_id                                       │ │  │
│  │  │ - embedding: [384维向量]                              │ │  │
│  │  │ - metadata: {source, layer, category, ...}           │ │  │
│  │  │ - document: "文本内容..."                              │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        Alpha 生成流程                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ 生成请求  │ -> │ 语义检索  │ -> │ 上下文构建 │ -> │ LLM生成  │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │               │        │
│       │          查询向量          Top-K 相关       组装提示词   │
│       │          相似度匹配        知识片段                     │
│       │                                                         │
│       v                                                         │
│  "生成动量因子"  ----->  检索到:                                │
│                       - 动量因子定义                            │
│                       - 常见动量表达式                          │
│                       - 动量因子优化技巧                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

#### 2.2.1 文本分块器 (Text Chunker)

**分块策略**：
```python
# 推荐参数
CHUNK_SIZE = 500      # 每块字符数
CHUNK_OVERLAP = 50    # 块间重叠字符数
MIN_CHUNK_SIZE = 100  # 最小块大小
```

**分块规则**：
1. **优先按段落分割**：保持语义完整性
2. **按标题层级分割**：`#`, `##`, `###` 作为分割点
3. **代码块保护**：不切断代码块
4. **重叠窗口**：相邻块有重叠，保证上下文连贯

**示例**：
```python
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

def chunk_document(content: str, source: str) -> List[Document]:
    """将文档分割成语义完整的块"""
    # 先按 Markdown 标题分割
    headers_to_split_on = [
        ("#", "header1"),
        ("##", "header2"),
        ("###", "header3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on
    )
    md_splits = markdown_splitter.split_text(content)

    # 再按字符数细分
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "；", "，", " "]
    )

    chunks = []
    for split in md_splits:
        sub_chunks = text_splitter.split_text(split.page_content)
        for i, chunk in enumerate(sub_chunks):
            chunks.append(Document(
                page_content=chunk,
                metadata={
                    "source": source,
                    "header1": split.metadata.get("header1", ""),
                    "header2": split.metadata.get("header2", ""),
                    "header3": split.metadata.get("header3", ""),
                    "chunk_index": i
                }
            ))
    return chunks
```

#### 2.2.2 向量嵌入模型 (Embedding Model)

**推荐方案**：

| 方案 | 模型 | 维度 | 优点 | 缺点 |
|------|------|------|------|------|
| **本地部署（推荐）** | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 384 | 中英文支持好，速度快，免费 | 精度略低于大模型 |
| 本地部署 | `BAAI/bge-large-zh-v1.5` | 1024 | 中文效果最好，精度高 | 模型较大，速度较慢 |
| 在线 API | OpenAI `text-embedding-3-small` | 1536 | 效果好，稳定 | 需要付费，网络依赖 |

**本地模型使用**：
```python
from sentence_transformers import SentenceTransformer

class EmbeddingModel:
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: List[str]) -> List[List[float]]:
        """生成文本向量"""
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """生成查询向量"""
        return self.model.encode([query], normalize_embeddings=True)[0].tolist()
```

#### 2.2.3 向量数据库 (Vector Database)

**推荐方案：ChromaDB**

**选择理由**：
1. **轻量级**：纯 Python 实现，无需额外服务
2. **持久化**：支持本地磁盘存储
3. **易集成**：与 LangChain、LlamaIndex 无缝集成
4. **功能完整**：支持元数据过滤、相似度搜索

**数据模型设计**：
```python
# Collection: knowledge_chunks
{
    "id": "chunk_uuid",                    # 唯一标识
    "embedding": [0.1, 0.2, ...],          # 384维向量
    "document": "知识文本内容...",           # 原始文本
    "metadata": {
        "source": "worldquant_community_knowledge.md",  # 来源文件
        "layer": "technical_methods",      # 知识层级
        "category": "momentum",            # 分类标签
        "header1": "Alpha研究",            # 一级标题
        "header2": "动量因子",             # 二级标题
        "chunk_index": 0,                  # 块索引
        "created_at": "2024-01-15",        # 创建时间
        "quality_score": 0.85              # 质量评分
    }
}
```

---

## 三、实现方案

### 3.1 目录结构

向量数据库作为独立的数据服务，放在项目根目录，与 `generation_one` 同级，便于多服务共享。

```
worldquant-miner/
├── vector_store/                        # 向量数据库服务（独立模块）
│   ├── __init__.py
│   ├── embedding.py                     # 向量嵌入模型
│   ├── chunker.py                       # 文本分块器
│   ├── store.py                         # ChromaDB 存储管理
│   ├── retriever.py                     # 检索器
│   ├── ingestor.py                      # 知识入库处理器
│   ├── config.py                        # 配置管理
│   └── chroma_db/                       # ChromaDB 数据目录
│       └── chroma.sqlite3               # 数据库文件
├── knowledge_base/                      # 原始知识库（Markdown 文件）
│   ├── worldquant_community_knowledge.md
│   └── worldquant_data_fields_reference.md
├── generation_one/                      # 第一代实现
│   └── naive-ollama/
│       └── ...                          # 使用 vector_store 服务
└── generation_two/                      # 第二代实现
    └── ...                              # 使用 vector_store 服务
```

**设计说明**：
- `vector_store/` 是独立的数据服务模块
- `generation_one` 和 `generation_two` 都可以导入使用
- 数据持久化在 `vector_store/chroma_db/` 目录

### 3.2 核心类设计

#### 3.2.1 VectorStore 类

```python
# vector_store/store.py
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import os

class VectorStore:
    """向量数据库管理类"""

    def __init__(self, persist_directory: str = None):
        """
        初始化向量存储

        Args:
            persist_directory: 持久化目录，默认为 vector_store/chroma_db
        """
        if persist_directory is None:
            # 默认使用 vector_store 目录下的 chroma_db
            persist_directory = os.path.join(
                os.path.dirname(__file__),
                'chroma_db'
            )

        self.client = chromadb.PersistentClient(path=persist_directory)

        # 知识块集合
        self.collection = self.client.get_or_create_collection(
            name="knowledge_chunks",
            metadata={"description": "知识库文档块"}
        )

    def add_chunks(
        self,
        chunks: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict],
        ids: List[str]
    ):
        """添加知识块"""
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
        where: Optional[Dict] = None
    ) -> Dict:
        """
        语义搜索

        Args:
            query_embedding: 查询向量
            n_results: 返回结果数量
            where: 元数据过滤条件
        """
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )

    def delete_by_source(self, source: str):
        """删除指定来源的所有知识块"""
        self.collection.delete(
            where={"source": source}
        )

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_chunks": self.collection.count()
        }
```

#### 3.2.2 KnowledgeRetriever 类

```python
# vector_store/retriever.py
from typing import List, Dict, Optional
from .embedding import EmbeddingModel
from .store import VectorStore

class KnowledgeRetriever:
    """知识检索器"""

    def __init__(
        self,
        vector_store: VectorStore = None,
        embedding_model: EmbeddingModel = None
    ):
        self.store = vector_store or VectorStore()
        self.embedder = embedding_model or EmbeddingModel()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        layer_filter: Optional[List[str]] = None,
        category_filter: Optional[str] = None
    ) -> str:
        """
        检索相关知识

        Args:
            query: 查询文本（如"生成动量因子"）
            top_k: 返回结果数量
            layer_filter: 知识层级过滤
            category_filter: 分类过滤

        Returns:
            组装好的知识上下文
        """
        # 生成查询向量
        query_embedding = self.embedder.embed_query(query)

        # 构建过滤条件
        where_filter = None
        if layer_filter or category_filter:
            conditions = []
            if layer_filter:
                conditions.append({"layer": {"$in": layer_filter}})
            if category_filter:
                conditions.append({"category": category_filter})

            if len(conditions) == 1:
                where_filter = conditions[0]
            else:
                where_filter = {"$and": conditions}

        # 执行搜索
        results = self.store.search(
            query_embedding=query_embedding,
            n_results=top_k,
            where=where_filter
        )

        # 组装上下文
        context_parts = []
        for i, (doc, metadata) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0]
        )):
            source = metadata.get('source', 'unknown')
            header1 = metadata.get('header1', '')
            header2 = metadata.get('header2', '')
            header_path = f"{header1} > {header2}" if header2 else header1

            context_parts.append(
                f"[知识 {i+1}] 来源: {source} - {header_path}\n{doc}\n"
            )

        return "\n".join(context_parts)

    def retrieve_raw(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        检索原始结果（返回列表）

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            知识块列表，每项包含 document 和 metadata
        """
        query_embedding = self.embedder.embed_query(query)
        results = self.store.search(
            query_embedding=query_embedding,
            n_results=top_k
        )

        items = []
        for doc, metadata, distance in zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ):
            items.append({
                "document": doc,
                "metadata": metadata,
                "distance": distance
            })

        return items
```

#### 3.2.3 KnowledgeIngestor 类

```python
# vector_store/ingestor.py
import os
import hashlib
from typing import List, Dict
from pathlib import Path
from datetime import datetime
from .chunker import chunk_document
from .embedding import EmbeddingModel
from .store import VectorStore

class KnowledgeIngestor:
    """知识入库处理器"""

    def __init__(
        self,
        vector_store: VectorStore = None,
        embedding_model: EmbeddingModel = None,
        knowledge_base_path: str = None
    ):
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
        for file_path in Path(self.kb_path).glob("*.md"):
            if file_path.name.startswith("."):
                continue

            count = self.ingest_file(
                str(file_path),
                layer=self._infer_layer(file_path.name),
                category=self._infer_category(file_path.name)
            )
            stats[file_path.name] = count

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
```

### 3.3 模块导出

```python
# vector_store/__init__.py
from .store import VectorStore
from .embedding import EmbeddingModel
from .chunker import chunk_document
from .retriever import KnowledgeRetriever
from .ingestor import KnowledgeIngestor

__all__ = [
    'VectorStore',
    'EmbeddingModel',
    'chunk_document',
    'KnowledgeRetriever',
    'KnowledgeIngestor'
]
```

---

## 四、配置文件

```python
# vector_store/config.py

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
```

---

## 五、依赖安装

```bash
# requirements.txt 新增依赖
chromadb>=0.4.22
sentence-transformers>=2.2.2
langchain>=0.1.0
```

安装命令：
```bash
pip install chromadb sentence-transformers langchain
```

---

## 六、实施计划

### 阶段一：基础设施搭建（1天）
- [ ] 安装依赖包
- [ ] 创建 `vector_store/` 目录结构
- [ ] 实现 `config.py` 配置管理
- [ ] 实现 `EmbeddingModel` 类
- [ ] 实现 `chunker.py` 分块器
- [ ] 实现 `VectorStore` 类

### 阶段二：知识入库（1天）
- [ ] 实现 `KnowledgeIngestor` 类
- [ ] 实现 `KnowledgeRetriever` 类
- [ ] 将现有知识库入库
- [ ] 验证检索效果

### 阶段三：测试验证（0.5天）
- [ ] 测试入库流程
- [ ] 测试检索效果
- [ ] 性能测试

### 阶段四：文档完善（0.5天）
- [ ] 更新使用文档
- [ ] 添加使用示例

---

## 七、预期效果

### 7.1 解决的问题
1. **Token 限制**：大文件分块存储，按需检索
2. **语义检索**：基于向量相似度，理解语义
3. **增量更新**：新知识直接入库，无需重建
4. **上下文优化**：只加载相关知识，节省 token

### 7.2 性能指标
| 指标 | 目标值 |
|------|--------|
| 分块速度 | > 100 chunks/s |
| 向量生成速度 | > 50 chunks/s (CPU) |
| 检索延迟 | < 100ms |
| 检索准确率 | > 85% |

### 7.3 使用示例

```python
# 示例1：入库知识库
from vector_store.ingestor import KnowledgeIngestor

ingestor = KnowledgeIngestor()
stats = ingestor.ingest_knowledge_base()
print(f"入库完成: {stats}")

# 示例2：检索知识
from vector_store.retriever import KnowledgeRetriever

retriever = KnowledgeRetriever()

# 检索相关知识
context = retriever.retrieve(
    query="生成一个基于成交量的动量因子",
    top_k=5
)
print(context)

# 示例3：获取原始检索结果
results = retriever.retrieve_raw("动量因子优化技巧", top_k=3)
for item in results:
    print(f"来源: {item['metadata']['source']}")
    print(f"内容: {item['document'][:100]}...")
    print(f"相似度: {1 - item['distance']:.2f}")
```

---

## 八、风险与应对

### 8.1 潜在风险
1. **向量质量**：嵌入模型质量影响检索效果
   - 应对：选择高质量模型，定期评估效果

2. **分块粒度**：分块过大或过小影响检索
   - 应对：提供可配置参数，根据实际调整

3. **存储空间**：向量数据库占用磁盘空间
   - 应对：定期清理过期数据，压缩存储

4. **检索延迟**：大规模数据检索变慢
   - 应对：使用索引优化，限制检索范围

### 8.2 备选方案
- 如果 ChromaDB 不满足需求，可切换到：
  - **FAISS**：Facebook 的向量检索库，性能更高
  - **Milvus**：分布式向量数据库，适合大规模场景
  - **Pinecone**：云托管向量数据库，免维护

---

## 九、总结

本方案通过引入向量数据库，实现了知识库的语义化存储和检索，解决了大文件 Token 限制问题。

**核心优势**：
1. 支持任意大小的知识库文档
2. 语义级别的智能检索
3. 按需加载，节省 Token
4. 增量更新，无需重建
5. 本地部署，数据安全
6. 独立模块，多服务共享

**后续扩展**：
- 后续可根据需要将向量检索集成到 Alpha 生成流程
- 可扩展支持更多知识来源（如论坛帖子、API 文档等）
