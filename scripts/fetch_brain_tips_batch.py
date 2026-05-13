# -*- coding: utf-8 -*-
"""
BRAIN TIPS 帖子批量采集脚本

使用 Playwright MCP 采集帖子内容，保存为 JSON 文件。
"""

import os
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent
KB_PATH = PROJECT_ROOT / "knowledge_base"
URLS_FILE = KB_PATH / "brain_tips_urls.json"

# 采集历史文件
HISTORY_FILE = KB_PATH / "fetch_history.json"


def load_urls():
    """加载 URL 列表"""
    with open(URLS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_history():
    """加载采集历史"""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_history(history):
    """保存采集历史"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def save_post(post_data):
    """保存帖子到 JSON 文件"""
    post_id = hashlib.md5(post_data['url'].encode()).hexdigest()[:12]
    safe_title = "".join(c if c.isalnum() or c in ' -_' else '' for c in post_data.get('title', 'Untitled'))[:50]
    filename = f"brain_tips_{post_id}_{safe_title}.json"
    filepath = KB_PATH / filename

    post_data['fetched_at'] = datetime.now().isoformat()
    post_data['source_file'] = filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)

    return filename


def get_pending_urls(urls, history):
    """获取待采集的 URL"""
    pending = []
    for item in urls:
        url = item['url']
        if url not in history or history[url].get('status') != 'success':
            pending.append(item)
    return pending


def main():
    """主函数"""
    print("=" * 60)
    print("BRAIN TIPS 帖子批量采集")
    print("=" * 60)

    # 创建知识库目录
    KB_PATH.mkdir(parents=True, exist_ok=True)

    # 加载数据
    urls = load_urls()
    history = load_history()

    print(f"总帖子数: {len(urls)}")
    print(f"已采集数: {len(history)}")

    # 获取待采集 URL
    pending = get_pending_urls(urls, history)
    print(f"待采集数: {len(pending)}")

    if not pending:
        print("所有帖子已采集完成")
        return

    # 输出待采集列表
    print("\n待采集帖子列表:")
    for i, item in enumerate(pending[:10], 1):
        print(f"  {i}. {item['title'][:50]}...")

    if len(pending) > 10:
        print(f"  ... 还有 {len(pending) - 10} 个")

    # 输出采集指令
    print("\n" + "=" * 60)
    print("请在 Claude Code 中使用 Playwright MCP 采集")
    print("=" * 60)
    print("\n采集脚本已准备好，请使用以下命令开始采集:")
    print(f"  待采集帖子数: {len(pending)}")
    print(f"  URL 列表文件: {URLS_FILE}")
    print(f"  采集历史文件: {HISTORY_FILE}")


if __name__ == "__main__":
    main()
