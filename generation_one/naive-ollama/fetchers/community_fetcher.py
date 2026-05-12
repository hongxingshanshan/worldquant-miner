#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WorldQuant 社区知识采集器

合并自:
- fetch_community_knowledge.py (requests + BeautifulSoup)
- fetch_community_batch.py (批量处理)
- fetch_community_playwright.py (Playwright 自动化)

提供三种采集模式:
1. API 模式 - 使用 requests + BeautifulSoup（默认，无需浏览器）
2. 批量模式 - 处理预设的重要帖子列表
3. Playwright 模式 - 使用浏览器自动化（需要安装 Playwright）
"""

import json
import time
import os
import re
from typing import List, Dict, Optional
from datetime import datetime

# 尝试导入 requests（必需）
try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# 尝试导入 Playwright（可选）
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class CommunityFetcher:
    """WorldQuant 社区知识采集器"""

    # 重要帖子列表（精选内容）
    IMPORTANT_POSTS = [
        {"title": "Demystifying Simulation Settings: Pasteurization", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/17518278995991"},
        {"title": "Controlling Extremes: The Role of Truncation", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/37835332451607"},
        {"title": "Introduction to Alpha Research and Fine-Tuning", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/37032754310679"},
        {"title": "Statistical Neutralization Sharpens Signals", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/35254553150231"},
        {"title": "How to increase Sharpe without overfitting", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/27841757470359"},
        {"title": "Reduce correlation by combining fields", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/27630690341399"},
        {"title": "How to reduce self and production correlation", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/26750743873943"},
        {"title": "Finding Alphas: Price Volume Data", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/20051361858327"},
        {"title": "Finding Alphas: Fundamental and Model Data", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/20051403346583"},
        {"title": "Finding Alphas: Signal or Overfitting?", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/20051405370903"},
        {"title": "Finding Alphas: News and Social Media", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/20051406364695"},
        {"title": "Finding Alphas: Options Data", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/20051507959959"},
        {"title": "Sequencing Multiple Operators", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/19344464221335"},
        {"title": "Generate insights from research paper using GPT", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/20457074342807"},
        {"title": "Use test period to improve OS performance", "url": "https://support.worldquantbrain.com/hc/en-us/community/posts/22205077935895"},
    ]

    def __init__(self, output_dir: str = "knowledge_base"):
        """
        初始化采集器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        self.session = None

        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

    def fetch_topics_api(self, page: int = 1) -> List[Dict]:
        """
        使用 API 模式获取社区主题列表

        Args:
            page: 页码

        Returns:
            主题列表
        """
        if not REQUESTS_AVAILABLE:
            print("错误: requests 或 BeautifulSoup 未安装")
            return []

        url = "https://support.worldquantbrain.com/hc/en-us/community/topics"
        params = {"page": page}

        try:
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                print(f"请求失败: {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, 'html.parser')
            topics = []

            # 查找主题列表
            topic_elements = soup.select('.topic-list-item, .community-topic-item, article')

            for elem in topic_elements:
                try:
                    title_elem = elem.select_one('a[href*="/community/posts/"], h2 a, .title a, a.title')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '')
                    if link and not link.startswith('http'):
                        link = 'https://support.worldquantbrain.com' + link

                    desc_elem = elem.select_one('.description, .excerpt, p')
                    description = desc_elem.get_text(strip=True) if desc_elem else ""

                    tags = [t.get_text(strip=True) for t in elem.select('.label, .tag, .category')]

                    topics.append({
                        'title': title,
                        'link': link,
                        'description': description,
                        'tags': tags
                    })
                except Exception:
                    continue

            return topics

        except Exception as e:
            print(f"获取主题列表失败: {e}")
            return []

    def fetch_post_content_api(self, url: str) -> Dict:
        """
        使用 API 模式获取帖子详细内容

        Args:
            url: 帖子 URL

        Returns:
            帖子内容
        """
        if not REQUESTS_AVAILABLE:
            return {'url': url, 'error': 'requests 未安装'}

        try:
            resp = self.session.get(url, timeout=30)
            if resp.status_code != 200:
                return {'url': url, 'error': f"状态码: {resp.status_code}"}

            soup = BeautifulSoup(resp.text, 'html.parser')

            # 获取标题
            title_elem = soup.select_one('h1, .post-title, .article-title')
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"

            # 获取内容
            content_elem = soup.select_one('article, .post-content, .article-body')
            content = content_elem.get_text(strip=True) if content_elem else ""

            # 获取代码块
            code_blocks = [code.get_text(strip=True) for code in soup.select('pre, code')]

            return {
                'url': url,
                'title': title,
                'content': content[:5000],  # 限制长度
                'code_blocks': code_blocks[:5]
            }

        except Exception as e:
            return {'url': url, 'error': str(e)}

    def fetch_batch(self, posts: Optional[List[Dict]] = None) -> List[Dict]:
        """
        批量获取帖子内容

        Args:
            posts: 帖子列表，默认使用 IMPORTANT_POSTS

        Returns:
            帖子内容列表
        """
        if posts is None:
            posts = self.IMPORTANT_POSTS

        results = []
        total = len(posts)

        for i, post in enumerate(posts):
            print(f"[{i+1}/{total}] 获取: {post['title'][:50]}...")

            content = self.fetch_post_content_api(post['url'])
            content['title'] = post['title']
            results.append(content)

            # 避免请求过快
            time.sleep(1)

        return results

    def fetch_playwright(self, topics: Optional[List[Dict]] = None,
                         posts_per_topic: int = 20,
                         headless: bool = True) -> List[Dict]:
        """
        使用 Playwright 模式采集社区帖子

        Args:
            topics: 主题列表
            posts_per_topic: 每个主题采集的帖子数
            headless: 是否无头模式

        Returns:
            帖子内容列表
        """
        if not PLAYWRIGHT_AVAILABLE:
            print("错误: Playwright 未安装，请运行: pip install playwright && playwright install")
            return []

        if topics is None:
            topics = [
                {"name": "BRAIN TIPS", "url": "https://support.worldquantbrain.com/hc/en-us/community/topics/18068926798871-BRAIN-TIPS"},
                {"name": "Getting started with Research", "url": "https://support.worldquantbrain.com/hc/en-us/community/topics/4419282859415-Getting-started-with-Research"},
                {"name": "Research Papers for Users", "url": "https://support.worldquantbrain.com/hc/en-us/community/topics/13724934223127-Research-Papers-for-Users"},
            ]

        posts_data = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context()
            page = context.new_page()

            for topic in topics:
                print(f"\n采集主题: {topic['name']}")
                try:
                    page.goto(topic['url'], timeout=30000)
                    page.wait_for_load_state("networkidle")
                    time.sleep(2)

                    # 获取帖子链接
                    post_links = page.eval_on_selector_all('a[href*="/community/posts/"]', '''
                        (links) => links.map(link => ({
                            url: link.href,
                            title: link.textContent.trim()
                        }))
                    ''')

                    print(f"找到 {len(post_links)} 个帖子")

                    # 采集每个帖子
                    for i, post_info in enumerate(post_links[:posts_per_topic]):
                        try:
                            print(f"  [{i+1}/{min(len(post_links), posts_per_topic)}] {post_info['title'][:50]}...")
                            page.goto(post_info['url'], timeout=30000)
                            page.wait_for_load_state("networkidle")
                            time.sleep(1)

                            content = page.eval_on_selector('main, article, .post-content', '''
                                (el) => el ? el.textContent.trim() : ""
                            ''')

                            code_blocks = page.eval_on_selector_all('pre, code', '''
                                (blocks) => blocks.map(b => b.textContent.trim()).filter(c => c.length > 10)
                            ''')

                            posts_data.append({
                                "topic": topic['name'],
                                "title": post_info['title'],
                                "url": post_info['url'],
                                "content": content[:5000] if content else "",
                                "code_blocks": code_blocks[:5]
                            })

                        except Exception as e:
                            print(f"    错误: {e}")
                            continue

                except Exception as e:
                    print(f"主题采集失败: {e}")
                    continue

            browser.close()

        return posts_data

    def save_to_knowledge_base(self, posts: List[Dict], filename: str = "community_knowledge.json"):
        """
        保存到知识库

        Args:
            posts: 帖子列表
            filename: 文件名
        """
        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, filename)

        data = {
            "collected_at": datetime.now().isoformat(),
            "source": "WorldQuant Brain Community Forums",
            "total_posts": len(posts),
            "posts": posts
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"已保存 {len(posts)} 个帖子到 {filepath}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='WorldQuant 社区知识采集器')
    parser.add_argument('--mode', choices=['api', 'batch', 'playwright'], default='batch',
                        help='采集模式: api(实时), batch(批量), playwright(浏览器)')
    parser.add_argument('--output', default='knowledge_base', help='输出目录')
    parser.add_argument('--headless', action='store_true', help='Playwright 无头模式')
    parser.add_argument('--posts-per-topic', type=int, default=20, help='每个主题采集的帖子数')

    args = parser.parse_args()

    fetcher = CommunityFetcher(output_dir=args.output)

    if args.mode == 'api':
        print("使用 API 模式采集...")
        topics = fetcher.fetch_topics_api()
        posts = [fetcher.fetch_post_content_api(t['link']) for t in topics[:10]]

    elif args.mode == 'batch':
        print("使用批量模式采集...")
        posts = fetcher.fetch_batch()

    elif args.mode == 'playwright':
        print("使用 Playwright 模式采集...")
        posts = fetcher.fetch_playwright(headless=args.headless, posts_per_topic=args.posts_per_topic)

    if posts:
        fetcher.save_to_knowledge_base(posts)
    else:
        print("未采集到任何内容")


if __name__ == "__main__":
    main()
