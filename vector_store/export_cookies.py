# -*- coding: utf-8 -*-
"""
浏览器 Cookie 导出工具

从 Chrome/Edge 浏览器导出 Cookie，供 Playwright 使用。

使用方法：
1. 在浏览器中登录 WorldQuant Brain
2. 运行此脚本导出 Cookie
3. 在 ForumFetcher 中指定 cookies_file 参数
"""

import os
import json
import sqlite3
import shutil
from pathlib import Path
from typing import List, Dict, Optional


def get_chrome_cookie_path() -> Optional[str]:
    """获取 Chrome Cookie 文件路径"""
    chrome_paths = [
        # Windows
        os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Network\Cookies'),
        os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cookies'),
        # macOS
        '~/Library/Application Support/Google/Chrome/Default/Cookies',
        # Linux
        '~/.config/google-chrome/Default/Cookies',
    ]

    for path in chrome_paths:
        if os.path.exists(path):
            return path
    return None


def get_edge_cookie_path() -> Optional[str]:
    """获取 Edge Cookie 文件路径"""
    edge_paths = [
        # Windows
        os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Network\Cookies'),
        os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cookies'),
    ]

    for path in edge_paths:
        if os.path.exists(path):
            return path
    return None


def extract_cookies_from_db(db_path: str, domain_filter: str = None) -> List[Dict]:
    """
    从 SQLite 数据库提取 Cookie

    Args:
        db_path: Cookie 数据库路径
        domain_filter: 域名过滤（如 'worldquantbrain.com'）

    Returns:
        Cookie 列表（Playwright 格式）
    """
    import tempfile

    cookies = []

    try:
        # 使用内存模式读取，避免锁定问题
        # 先尝试直接读取
        try:
            conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        except sqlite3.OperationalError:
            # 如果失败，复制到临时文件
            temp_db = os.path.join(tempfile.gettempdir(), 'cookies_temp.sqlite')
            try:
                shutil.copy2(db_path, temp_db)
            except PermissionError:
                print("Cookie 文件被锁定，请关闭浏览器后重试")
                print("或者使用管理员权限运行此脚本")
                return []
            conn = sqlite3.connect(temp_db)

        cursor = conn.cursor()

        # 查询 Cookie
        if domain_filter:
            cursor.execute(
                "SELECT host_key, name, value, path, expires_utc, is_secure FROM cookies WHERE host_key LIKE ?",
                (f'%{domain_filter}%',)
            )
        else:
            cursor.execute(
                "SELECT host_key, name, value, path, expires_utc, is_secure FROM cookies"
            )

        for row in cursor.fetchall():
            host_key = row[0]
            name = row[1]
            value = row[2]
            path = row[3]
            expires_utc = row[4]
            is_secure = row[5]

            # 转换为 Playwright 格式
            cookie = {
                'name': name,
                'value': value,
                'domain': host_key.lstrip('.'),
                'path': path,
                'secure': is_secure == 1,
                'httpOnly': False,
            }

            # 处理过期时间（Chrome 使用微秒）
            if expires_utc and expires_utc > 0:
                # Chrome 时间戳是从 1601-01-01 开始的微秒
                # 转换为 Unix 时间戳（秒）
                expires_unix = (expires_utc / 1000000) - 11644473600
                if expires_unix > 0:
                    cookie['expires'] = int(expires_unix)

            cookies.append(cookie)

        conn.close()

    except Exception as e:
        print(f"提取 Cookie 失败: {e}")

    return cookies


def export_cookies(
    output_file: str,
    domain_filter: str = None,
    browser: str = 'chrome'
) -> int:
    """
    导出 Cookie 到 JSON 文件

    Args:
        output_file: 输出文件路径
        domain_filter: 域名过滤
        browser: 浏览器类型 ('chrome' 或 'edge')

    Returns:
        导出的 Cookie 数量
    """
    # 获取 Cookie 数据库路径
    if browser == 'edge':
        db_path = get_edge_cookie_path()
    else:
        db_path = get_chrome_cookie_path()

    if not db_path:
        print(f"未找到 {browser} Cookie 数据库")
        return 0

    print(f"Cookie 数据库: {db_path}")

    # 提取 Cookie
    cookies = extract_cookies_from_db(db_path, domain_filter)

    if not cookies:
        print("未提取到任何 Cookie")
        return 0

    # 保存到文件
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)

    print(f"导出 {len(cookies)} 个 Cookie 到: {output_file}")
    return len(cookies)


def export_worldquant_cookies(output_file: str = None) -> str:
    """
    导出 WorldQuant Brain Cookie

    Args:
        output_file: 输出文件路径（默认为 vector_store/browser_cookies.json）

    Returns:
        输出文件路径
    """
    if output_file is None:
        output_file = os.path.join(
            os.path.dirname(__file__),
            'browser_cookies.json'
        )

    count = export_cookies(
        output_file=output_file,
        domain_filter='worldquantbrain.com',
        browser='chrome'
    )

    if count == 0:
        # 尝试 Edge
        count = export_cookies(
            output_file=output_file,
            domain_filter='worldquantbrain.com',
            browser='edge'
        )

    return output_file


if __name__ == '__main__':
    print("浏览器 Cookie 导出工具")
    print("=" * 50)

    # 导出 WorldQuant Brain Cookie
    output_file = os.path.join(
        os.path.dirname(__file__),
        'browser_cookies.json'
    )

    export_worldquant_cookies(output_file)

    print("\n使用方法:")
    print("from vector_store.forum_fetcher import ForumFetcher")
    print("fetcher = ForumFetcher(fetch_method='playwright_mcp', browser_cookies_file='browser_cookies.json')")