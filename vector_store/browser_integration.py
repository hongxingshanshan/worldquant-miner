# -*- coding: utf-8 -*-
"""
浏览器采集集成器

在 Claude Code 环境中，通过 MCP 工具获取页面内容后，
使用 ForumFetcher 进行 LLM 提炼和入库。

使用方式：
1. Claude Code 调用 MCP 工具获取页面快照
2. 将快照内容传递给此模块处理
"""

import os
import sys
from typing import Dict, List, Optional

# 添加路径
_current_dir = os.path.dirname(__file__)
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from vector_store.forum_fetcher import ForumFetcher


class BrowserFetchIntegration:
    """浏览器采集集成器"""

    def __init__(self, use_llm_extract: bool = True):
        """
        初始化集成器

        Args:
            use_llm_extract: 是否使用 LLM 提炼知识点
        """
        self.fetcher = ForumFetcher(use_llm_extract=use_llm_extract)

    def process_snapshot(
        self,
        url: str,
        snapshot_content: str,
        title: Optional[str] = None
    ) -> Dict:
        """
        处理浏览器快照内容

        Args:
            url: 页面 URL
            snapshot_content: 浏览器快照内容
            title: 可选的标题（如果已知）

        Returns:
            处理结果
        """
        return self.fetcher.fetch_with_browser_snapshot(url, snapshot_content)

    def process_snapshots_batch(self, snapshots: List[Dict]) -> List[Dict]:
        """
        批量处理浏览器快照

        Args:
            snapshots: 快照列表，每个元素包含 url 和 content

        Returns:
            处理结果列表
        """
        results = []
        for snapshot in snapshots:
            url = snapshot.get('url', '')
            content = snapshot.get('content', '')
            title = snapshot.get('title')

            if url and content:
                result = self.process_snapshot(url, content, title)
                results.append(result)

        return results

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        检索知识

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            检索结果
        """
        from vector_store.retriever import KnowledgeRetriever
        retriever = KnowledgeRetriever()
        return retriever.retrieve_raw(query, top_k=top_k)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.fetcher.get_stats()


# 便捷函数
_integration = None

def get_integration(use_llm_extract: bool = True) -> BrowserFetchIntegration:
    """获取集成器实例"""
    global _integration
    if _integration is None:
        _integration = BrowserFetchIntegration(use_llm_extract=use_llm_extract)
    return _integration


def process_browser_snapshot(url: str, content: str) -> Dict:
    """
    处理浏览器快照（便捷函数）

    在 Claude Code 中使用 MCP 工具获取页面后调用此函数

    Args:
        url: 页面 URL
        content: 页面快照内容

    Returns:
        处理结果
    """
    integration = get_integration()
    return integration.process_snapshot(url, content)


def search_knowledge(query: str, top_k: int = 5) -> List[Dict]:
    """
    检索知识（便捷函数）

    Args:
        query: 查询文本
        top_k: 返回结果数量

    Returns:
        检索结果
    """
    integration = get_integration()
    return integration.search(query, top_k)


if __name__ == "__main__":
    # 测试
    print("浏览器采集集成器")
    print("=" * 50)

    integration = get_integration()
    stats = integration.get_stats()

    print(f"已采集帖子数: {stats['fetched_posts']}")
    print(f"LLM 提炼: {'启用' if stats['llm_extract_enabled'] else '禁用'}")
    print(f"向量库统计: {stats['vector_store_stats']}")
