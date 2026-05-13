# -*- coding: utf-8 -*-
"""
登录助手

启动浏览器让用户手动登录，保存登录状态供后续采集使用。
"""

import os
import sys
from pathlib import Path

# 添加路径
_current_dir = os.path.dirname(__file__)
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def login_and_save_state(
    user_data_dir: str = None,
    login_url: str = "https://platform.worldquantbrain.com/sign-in"
):
    """
    启动浏览器让用户登录，保存登录状态

    Args:
        user_data_dir: 用户数据目录（保存登录状态）
        login_url: 登录页面 URL
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("请先安装 playwright: pip install playwright && python -m playwright install chromium")
        return

    if user_data_dir is None:
        user_data_dir = os.path.join(_current_dir, 'browser_data')

    print("=" * 60)
    print("登录助手")
    print("=" * 60)
    print(f"用户数据目录: {user_data_dir}")
    print(f"登录页面: {login_url}")
    print("")
    print("说明:")
    print("1. 浏览器将打开，请手动登录 WorldQuant Brain")
    print("2. 登录成功后，按 Enter 键关闭浏览器")
    print("3. 登录状态将保存，供后续采集使用")
    print("=" * 60)
    print("")

    input("按 Enter 键启动浏览器...")

    with sync_playwright() as p:
        # 使用持久化上下文（保存登录状态）
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,  # 显示浏览器
            args=['--disable-blink-features=AutomationControlled']
        )

        page = context.new_page()

        # 打开登录页面
        page.goto(login_url)

        print("")
        print("浏览器已打开，请在浏览器中完成登录")
        print("登录成功后，回到此窗口按 Enter 键关闭浏览器")

        input("\n按 Enter 键关闭浏览器并保存登录状态...")

        context.close()

    print(f"\n登录状态已保存到: {user_data_dir}")
    print("\n使用方法:")
    print("from vector_store.forum_fetcher import ForumFetcher")
    print(f'fetcher = ForumFetcher(fetch_method="playwright_mcp", browser_user_data_dir="{user_data_dir}")')


if __name__ == '__main__':
    login_and_save_state()
