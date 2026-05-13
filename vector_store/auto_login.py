# -*- coding: utf-8 -*-
"""
自动登录脚本

自动登录 WorldQuant Brain 并保存登录状态。
"""

import os
import sys
import json
import time

# 添加路径
_current_dir = os.path.dirname(__file__)
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def load_credentials(credential_file: str = None) -> tuple:
    """加载登录凭证"""
    if credential_file is None:
        credential_file = os.path.join(
            _parent_dir, 'generation_one', 'naive-ollama', 'credential.txt'
        )

    if os.path.exists(credential_file):
        with open(credential_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # 解析格式: ["email", "password"]
            if content.startswith('['):
                creds = json.loads(content)
                return creds[0], creds[1]

    return None, None


def auto_login(
    user_data_dir: str = None,
    credential_file: str = None
) -> bool:
    """
    自动登录 WorldQuant Brain

    Args:
        user_data_dir: 用户数据目录
        credential_file: 凭证文件路径

    Returns:
        是否登录成功
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("请先安装 playwright: pip install playwright && python -m playwright install chromium")
        return False

    # 加载凭证
    email, password = load_credentials(credential_file)
    if not email or not password:
        print("无法加载登录凭证")
        return False

    if user_data_dir is None:
        user_data_dir = os.path.join(_current_dir, 'browser_data')

    print("=" * 60)
    print("自动登录 WorldQuant Brain")
    print("=" * 60)
    print(f"邮箱: {email}")
    print(f"用户数据目录: {user_data_dir}")
    print("")

    try:
        with sync_playwright() as p:
            # 启动浏览器（显示界面以便观察）
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,  # 显示浏览器
                args=['--disable-blink-features=AutomationControlled']
            )

            page = context.new_page()

            # 访问登录页面
            print("正在访问登录页面...")
            page.goto("https://platform.worldquantbrain.com/sign-in", wait_until='domcontentloaded')

            # 等待页面加载
            page.wait_for_timeout(2000)

            # 检查是否已登录
            if 'sign-in' not in page.url.lower():
                print("已经登录")
                context.close()
                return True

            # 填写邮箱
            print("填写登录信息...")
            try:
                email_input = page.query_selector('input[type="email"], input[name="email"], input[placeholder*="email"]')
                if email_input:
                    email_input.fill(email)
                else:
                    # 尝试其他选择器
                    email_input = page.query_selector('input[type="text"]')
                    if email_input:
                        email_input.fill(email)
            except Exception as e:
                print(f"填写邮箱失败: {e}")

            # 填写密码
            try:
                password_input = page.query_selector('input[type="password"]')
                if password_input:
                    password_input.fill(password)
            except Exception as e:
                print(f"填写密码失败: {e}")

            # 点击登录按钮
            print("点击登录按钮...")
            try:
                login_btn = page.query_selector('button[type="submit"], button:has-text("Sign In"), button:has-text("登录")')
                if login_btn:
                    login_btn.click()
            except Exception as e:
                print(f"点击登录按钮失败: {e}")

            # 等待登录完成
            print("等待登录完成...")
            try:
                # 等待 URL 变化或出现登录成功标志
                page.wait_for_url("**/platform.worldquantbrain.com/**", timeout=30000)
                print("登录成功!")

                # 等待页面完全加载
                page.wait_for_timeout(3000)

                # 访问社区页面确认登录状态
                print("验证登录状态...")
                page.goto("https://support.worldquantbrain.com/hc/en-us/community/topics", wait_until='domcontentloaded')
                page.wait_for_timeout(2000)

                if 'sign-in' not in page.url.lower():
                    print("登录状态验证成功!")
                else:
                    print("登录状态验证失败，请手动完成登录")
                    input("完成登录后按 Enter 键继续...")

            except PlaywrightTimeout:
                # 可能需要验证码或其他操作
                print("登录可能需要额外验证，请在浏览器中完成")
                print("完成后按 Enter 键继续...")
                input()

            # 等待状态保存
            page.wait_for_timeout(2000)

            # 保存状态
            context.close()

            print(f"\n登录状态已保存到: {user_data_dir}")
            return True

    except Exception as e:
        print(f"登录失败: {e}")
        return False


if __name__ == '__main__':
    success = auto_login()

    if success:
        print("\n" + "=" * 60)
        print("使用方法:")
        print("from vector_store.forum_fetcher import ForumFetcher")
        print('fetcher = ForumFetcher(fetch_method="playwright_mcp", browser_user_data_dir="browser_data")')
        print("=" * 60)
