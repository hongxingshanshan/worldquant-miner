# -*- coding: utf-8 -*-
"""
BRAIN TIPS 帖子批量采集脚本

从 brain_tips_posts.md 文件读取帖子链接，
使用 Playwright MCP 采集帖子内容，
通过 LLM 提炼知识点后入库到向量数据库。
"""

import os
import re
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Optional

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vector_store import ForumFetcher, VectorStore, EmbeddingModel

# BRAIN TIPS 帖子列表文件
POSTS_FILE = project_root / "generation_one" / "naive-ollama" / "docs" / "brain_tips_posts.md"

# 知识库目录
KB_PATH = project_root / "knowledge_base"


def extract_urls_from_markdown(file_path: str) -> List[Dict]:
    """
    从 Markdown 文件提取帖子 URL 和标题

    Args:
        file_path: Markdown 文件路径

    Returns:
        帖子信息列表 [{url, title, page}, ...]
    """
    posts = []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配格式: 数字. [标题](URL)
    pattern = r'\d+\.\s+\[([^\]]+)\]\(([^)]+)\)'
    matches = re.findall(pattern, content)

    for title, url in matches:
        posts.append({
            'title': title.strip(),
            'url': url.strip()
        })

    return posts


def fetch_posts_with_playwright_mcp(urls: List[str]) -> List[Dict]:
    """
    使用 Playwright MCP 批量采集帖子

    注意：此函数需要在 Claude Code 环境中执行，
    实际采集通过 MCP 工具完成。

    Args:
        urls: URL 列表

    Returns:
        采集结果列表
    """
    print(f"准备采集 {len(urls)} 个帖子")
    print("请在 Claude Code 环境中使用 Playwright MCP 工具采集")
    print("采集流程:")
    print("1. browser_navigate - 访问帖子页面")
    print("2. browser_snapshot - 获取页面快照")
    print("3. browser_evaluate - 提取帖子内容")

    return []


def create_fetch_script():
    """
    创建采集脚本内容

    返回可在 Claude Code 中执行的采集指令
    """
    posts = extract_urls_from_markdown(str(POSTS_FILE))

    script = f"""# BRAIN TIPS 帖子采集指令

## 帖子总数: {len(posts)}

## 采集步骤

### 1. 初始化采集器
```python
from vector_store import ForumFetcher

fetcher = ForumFetcher(
    fetch_method='playwright_mcp',
    use_llm_extract=True
)
```

### 2. 批量采集帖子
以下是需要采集的帖子 URL 列表（共 {len(posts)} 个）：

"""

    for i, post in enumerate(posts, 1):
        script += f"{i}. {post['title']}\n   URL: {post['url']}\n\n"

    script += """
### 3. 使用 Playwright MCP 采集

对于每个帖子，执行以下步骤：
1. `browser_navigate(url)` - 访问帖子
2. `browser_snapshot()` - 获取页面快照
3. `browser_evaluate()` - 提取内容

提取内容的 JavaScript：
```javascript
() => {
    const result = {
        title: '',
        content: '',
        author: '',
        date: ''
    };

    // 提取标题
    const h1 = document.querySelector('article h1');
    if (h1) result.title = h1.innerText.trim();

    // 提取作者
    const authorLink = document.querySelector('article a[href*="/profiles/"]');
    if (authorLink) result.author = authorLink.innerText.trim();

    // 提取时间
    const timeElem = document.querySelector('article time');
    if (timeElem) result.date = timeElem.innerText.trim();

    // 提取正文
    const article = document.querySelector('article');
    if (article) {
        const contentParts = [];
        const elements = article.querySelectorAll('h4, p');
        for (const el of elements) {
            const text = el.innerText.trim();
            if (text && text.length > 5 && !text.includes('Related to:')) {
                contentParts.push(text);
            }
        }
        result.content = contentParts.join('\\n\\n');
    }

    return result;
}
```

### 4. 入库到向量数据库

采集完成后，使用 ForumFetcher 入库：
```python
fetcher._ingest_post(post_data)
```
"""

    return script


def main():
    """主函数"""
    print("=" * 60)
    print("BRAIN TIPS 帖子批量采集")
    print("=" * 60)

    # 检查帖子列表文件
    if not POSTS_FILE.exists():
        print(f"帖子列表文件不存在: {POSTS_FILE}")
        return

    # 提取 URL
    posts = extract_urls_from_markdown(str(POSTS_FILE))
    print(f"提取到 {len(posts)} 个帖子链接")

    # 检查知识库目录
    KB_PATH.mkdir(parents=True, exist_ok=True)
    print(f"知识库目录: {KB_PATH}")

    # 初始化采集器
    fetcher = ForumFetcher(
        knowledge_base_path=str(KB_PATH),
        fetch_method='playwright_mcp',
        use_llm_extract=True
    )

    # 显示采集器状态
    stats = fetcher.get_stats()
    print(f"向量数据库统计: {stats}")

    # 输出采集指令
    script = create_fetch_script()
    script_file = KB_PATH / "fetch_instructions.md"
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script)
    print(f"采集指令已保存到: {script_file}")

    # 输出 URL 列表供 MCP 采集使用
    urls_file = KB_PATH / "brain_tips_urls.json"
    with open(urls_file, 'w', encoding='utf-8') as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print(f"URL 列表已保存到: {urls_file}")

    print("\n下一步:")
    print("1. 在 Claude Code 中使用 Playwright MCP 采集帖子内容")
    print("2. 或运行 fetcher.fetch_batch(urls) 批量采集")


if __name__ == "__main__":
    main()