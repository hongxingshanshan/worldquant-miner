# -*- coding: utf-8 -*-
"""
文本分块器

将文档分割成语义完整的块。
"""

from typing import List, Optional
from dataclasses import dataclass

from .config import CHUNKING_CONFIG


@dataclass
class Document:
    """文档块"""
    page_content: str
    metadata: dict


def chunk_document(
    content: str,
    source: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> List[Document]:
    """
    将文档分割成语义完整的块

    Args:
        content: 文档内容
        source: 来源文件名
        chunk_size: 块大小，默认使用配置
        chunk_overlap: 重叠大小，默认使用配置

    Returns:
        文档块列表
    """
    chunk_size = chunk_size or CHUNKING_CONFIG["chunk_size"]
    chunk_overlap = chunk_overlap or CHUNKING_CONFIG["chunk_overlap"]
    separators = CHUNKING_CONFIG["separators"]

    # 先按标题分割
    header_chunks = _split_by_headers(content, source)

    # 过滤空块
    header_chunks = [c for c in header_chunks if c is not None]

    # 再按字符数细分
    final_chunks = []
    for chunk in header_chunks:
        if chunk is None:
            continue
        if len(chunk.page_content) <= chunk_size:
            final_chunks.append(chunk)
        else:
            sub_chunks = _split_by_size(
                chunk.page_content,
                chunk.metadata,
                chunk_size,
                chunk_overlap,
                separators
            )
            final_chunks.extend(sub_chunks)

    return final_chunks


def _split_by_headers(content: str, source: str) -> List[Document]:
    """按 Markdown 标题分割"""
    lines = content.split('\n')
    chunks = []

    current_content = []
    current_headers = {"header1": "", "header2": "", "header3": ""}

    for line in lines:
        # 检测标题
        if line.startswith('# '):
            # 保存之前的内容
            if current_content:
                chunks.append(_create_chunk(
                    '\n'.join(current_content),
                    source,
                    current_headers
                ))
                current_content = []

            current_headers["header1"] = line[2:].strip()
            current_headers["header2"] = ""
            current_headers["header3"] = ""

        elif line.startswith('## '):
            if current_content:
                chunks.append(_create_chunk(
                    '\n'.join(current_content),
                    source,
                    current_headers
                ))
                current_content = []

            current_headers["header2"] = line[3:].strip()
            current_headers["header3"] = ""

        elif line.startswith('### '):
            if current_content:
                chunks.append(_create_chunk(
                    '\n'.join(current_content),
                    source,
                    current_headers
                ))
                current_content = []

            current_headers["header3"] = line[4:].strip()

        else:
            current_content.append(line)

    # 保存最后的内容
    if current_content:
        chunks.append(_create_chunk(
            '\n'.join(current_content),
            source,
            current_headers
        ))

    return chunks


def _split_by_size(
    content: str,
    base_metadata: dict,
    chunk_size: int,
    chunk_overlap: int,
    separators: List[str]
) -> List[Document]:
    """按字符大小分割"""
    if len(content) <= chunk_size:
        return [Document(page_content=content, metadata=base_metadata.copy())]

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(content):
        end = start + chunk_size

        # 尝试在分隔符处断开
        if end < len(content):
            best_split = end
            for sep in separators:
                # 向后查找分隔符
                pos = content.rfind(sep, start, end + 50)
                if pos > start + chunk_size // 2:
                    best_split = pos + len(sep)
                    break

            end = best_split

        chunk_content = content[start:end].strip()

        if chunk_content:
            metadata = base_metadata.copy()
            metadata["chunk_index"] = chunk_index
            chunks.append(Document(
                page_content=chunk_content,
                metadata=metadata
            ))
            chunk_index += 1

        start = end - chunk_overlap if end < len(content) else len(content)

    return chunks


def _create_chunk(
    content: str,
    source: str,
    headers: dict
) -> Document:
    """创建文档块"""
    content = content.strip()
    if not content:
        return None

    return Document(
        page_content=content,
        metadata={
            "source": source,
            "header1": headers.get("header1", ""),
            "header2": headers.get("header2", ""),
            "header3": headers.get("header3", ""),
            "chunk_index": 0
        }
    )
