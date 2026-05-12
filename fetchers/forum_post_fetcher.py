#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WorldQuant 论坛帖子采集工具

功能:
1. 支持指定 URL 采集单个帖子
2. 支持批量采集多个帖子
3. 自动保存到知识库
4. 支持增量更新（避免重复采集）
"""

import os
import json
import time
import argparse
import re
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urlparse

# 尝试导入 requests
try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ForumPostFetcher:
    """WorldQuant 论坛帖子采集器"""

    # 知识库路径（与 fetchers 同级）
    KNOWLEDGE_BASE_PATH = os.path.join(
        os.path.dirname(__file__),
        '..',
        'knowledge_base'
    )

    # 采集记录文件
    FETCH_HISTORY_FILE = "forum_fetch_history.json"

    def __init__(self, output_dir: str = None):
        """
        初始化采集器

        Args:
            output_dir: 输出目录，默认使用知识库路径
        """
        self.output_dir = output_dir or self.KNOWLEDGE_BASE_PATH
        self.session = None
        self.fetch_history = {}

        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            })

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

        # 加载采集历史
        self._load_fetch_history()

    def _load_fetch_history(self):
        """加载采集历史记录"""
        history_path = os.path.join(self.output_dir, self.FETCH_HISTORY_FILE)
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    self.fetch_history = json.load(f)
                logger.info(f"加载采集历史: {len(self.fetch_history)} 条记录")
            except Exception as e:
                logger.warning(f"加载采集历史失败: {e}")
                self.fetch_history = {}

    def _save_fetch_history(self):
        """保存采集历史记录"""
        history_path = os.path.join(self.output_dir, self.FETCH_HISTORY_FILE)
        try:
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(self.fetch_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存采集历史失败: {e}")

    def fetch_post(self, url: str, force: bool = False) -> Dict:
        """
        采集单个帖子

        Args:
            url: 帖子 URL
            force: 是否强制重新采集（忽略历史记录）

        Returns:
            帖子内容字典
        """
        if not REQUESTS_AVAILABLE:
            return {'url': url, 'error': 'requests 或 BeautifulSoup 未安装'}

        # 检查是否已采集
        if not force and url in self.fetch_history:
            logger.info(f"帖子已采集过，跳过: {url}")
            return {'url': url, 'status': 'skipped', 'reason': 'already_fetched'}

        logger.info(f"开始采集: {url}")

        try:
            response = self.session.get(url, timeout=30)

            if response.status_code != 200:
                return {'url': url, 'error': f'HTTP {response.status_code}'}

            soup = BeautifulSoup(response.text, 'html.parser')

            # 提取帖子信息
            post_data = self._extract_post_data(soup, url)

            if post_data.get('title'):
                # 保存到知识库
                self._save_to_knowledge_base(post_data)

                # 更新采集历史
                self.fetch_history[url] = {
                    'title': post_data.get('title', ''),
                    'fetched_at': datetime.now().isoformat(),
                    'output_file': post_data.get('output_file', '')
                }
                self._save_fetch_history()

                logger.info(f"采集成功: {post_data.get('title', 'Unknown')}")
            else:
                logger.warning(f"未能提取帖子内容: {url}")

            return post_data

        except Exception as e:
            logger.error(f"采集失败: {url} - {e}")
            return {'url': url, 'error': str(e)}

    def _extract_post_data(self, soup: BeautifulSoup, url: str) -> Dict:
        """从 HTML 中提取帖子数据"""
        post_data = {'url': url}

        # 提取标题
        title_elem = soup.select_one('h1, .post-title, .article-title, [class*="title"]')
        if title_elem:
            post_data['title'] = title_elem.get_text(strip=True)

        # 提取作者
        author_elem = soup.select_one('.author, .post-author, [class*="author"]')
        if author_elem:
            post_data['author'] = author_elem.get_text(strip=True)

        # 提取发布时间
        time_elem = soup.select_one('time, .post-date, .date, [class*="date"]')
        if time_elem:
            post_data['date'] = time_elem.get_text(strip=True)
            # 尝试提取 datetime 属性
            if time_elem.get('datetime'):
                post_data['date'] = time_elem.get('datetime')

        # 提取正文内容
        content_elem = soup.select_one('article, .post-content, .article-body, .content, [class*="content"]')
        if content_elem:
            # 清理不需要的元素
            for elem in content_elem.select('script, style, nav, footer, .comments, .sidebar'):
                elem.decompose()

            post_data['content'] = content_elem.get_text(separator='\n', strip=True)

        # 提取代码块
        code_blocks = []
        for code in soup.select('pre, code, .code'):
            code_text = code.get_text(strip=True)
            if len(code_text) > 10:  # 过滤太短的代码
                code_blocks.append(code_text)
        if code_blocks:
            post_data['code_blocks'] = code_blocks

        # 提取标签/分类
        tags = []
        for tag in soup.select('.tag, .label, .category, [class*="tag"]'):
            tag_text = tag.get_text(strip=True)
            if tag_text and len(tag_text) < 50:
                tags.append(tag_text)
        if tags:
            post_data['tags'] = list(set(tags))

        # 提取帖子 ID（用于文件命名）
        match = re.search(r'/posts/(\d+)', url)
        if match:
            post_data['post_id'] = match.group(1)

        return post_data

    def _save_to_knowledge_base(self, post_data: Dict) -> str:
        """保存帖子到知识库"""
        # 生成文件名
        post_id = post_data.get('post_id', datetime.now().strftime('%Y%m%d%H%M%S'))
        title = post_data.get('title', 'Untitled')
        # 清理标题用于文件名
        safe_title = re.sub(r'[^\w\s-]', '', title)[:50].strip().replace(' ', '_')
        filename = f"forum_post_{post_id}_{safe_title}.json"
        filepath = os.path.join(self.output_dir, filename)

        # 添加元数据
        post_data['fetched_at'] = datetime.now().isoformat()
        post_data['output_file'] = filename

        # 保存
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(post_data, f, ensure_ascii=False, indent=2)

        logger.info(f"已保存: {filepath}")
        return filepath

    def fetch_batch(self, urls: List[str], force: bool = False) -> List[Dict]:
        """
        批量采集帖子

        Args:
            urls: URL 列表
            force: 是否强制重新采集

        Returns:
            采集结果列表
        """
        results = []
        total = len(urls)

        for i, url in enumerate(urls, 1):
            logger.info(f"[{i}/{total}] 采集: {url}")

            result = self.fetch_post(url, force=force)
            results.append(result)

            # 避免请求过快
            if i < total:
                time.sleep(1)

        # 统计
        success_count = sum(1 for r in results if not r.get('error') and r.get('status') != 'skipped')
        skip_count = sum(1 for r in results if r.get('status') == 'skipped')
        error_count = sum(1 for r in results if r.get('error'))

        logger.info(f"批量采集完成: 成功 {success_count}, 跳过 {skip_count}, 失败 {error_count}")

        return results

    def fetch_from_file(self, file_path: str, force: bool = False) -> List[Dict]:
        """
        从文件读取 URL 列表并批量采集

        Args:
            file_path: 包含 URL 列表的文件路径（每行一个 URL）
            force: 是否强制重新采集

        Returns:
            采集结果列表
        """
        urls = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url and url.startswith('http'):
                    urls.append(url)

        logger.info(f"从文件读取 {len(urls)} 个 URL")
        return self.fetch_batch(urls, force=force)

    def list_fetched_posts(self) -> List[Dict]:
        """列出已采集的帖子"""
        posts = []
        for url, info in self.fetch_history.items():
            posts.append({
                'url': url,
                'title': info.get('title', ''),
                'fetched_at': info.get('fetched_at', ''),
                'output_file': info.get('output_file', '')
            })
        return posts


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='WorldQuant 论坛帖子采集工具')
    parser.add_argument('urls', nargs='*', help='要采集的帖子 URL')
    parser.add_argument('--file', '-f', type=str, help='包含 URL 列表的文件路径')
    parser.add_argument('--output', '-o', type=str, help='输出目录')
    parser.add_argument('--force', action='store_true', help='强制重新采集')
    parser.add_argument('--list', action='store_true', help='列出已采集的帖子')

    args = parser.parse_args()

    fetcher = ForumPostFetcher(output_dir=args.output)

    if args.list:
        # 列出已采集的帖子
        posts = fetcher.list_fetched_posts()
        print(f"\n已采集 {len(posts)} 个帖子:")
        for i, post in enumerate(posts, 1):
            print(f"{i}. {post['title'][:50]}...")
            print(f"   URL: {post['url']}")
            print(f"   时间: {post['fetched_at']}")
        return

    urls = args.urls or []

    if args.file:
        # 从文件读取 URL
        results = fetcher.fetch_from_file(args.file, force=args.force)
    elif urls:
        # 直接采集指定的 URL
        if len(urls) == 1:
            result = fetcher.fetch_post(urls[0], force=args.force)
            results = [result]
        else:
            results = fetcher.fetch_batch(urls, force=args.force)
    else:
        parser.print_help()
        return

    # 输出结果摘要
    print(f"\n采集完成:")
    for result in results:
        if result.get('error'):
            print(f"  ✗ {result['url'][:60]}... - 错误: {result['error']}")
        elif result.get('status') == 'skipped':
            print(f"  ⊙ {result['url'][:60]}... - 已跳过")
        else:
            print(f"  ✓ {result.get('title', 'Unknown')[:50]}...")


if __name__ == "__main__":
    main()
