# -*- coding: utf-8 -*-
"""
论坛帖子采集器

从 WorldQuant 论坛采集帖子，使用 LLM 提炼关键知识点后入库到向量数据库。
支持三种采集方式：
1. requests + BeautifulSoup（简单快速，适合静态页面）
2. Chrome DevTools MCP（适合动态页面，需要 Chrome 浏览器）
3. Playwright MCP（适合自动化采集，无头模式）
"""

import os
import json
import time
import hashlib
import re
import sys
from datetime import datetime
from typing import List, Dict, Optional

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from .store import VectorStore
from .embedding import EmbeddingModel

# 添加 LLMClient 路径
_llm_client_path = os.path.join(
    os.path.dirname(__file__),
    '..',
    'generation_one',
    'naive-ollama'
)
if _llm_client_path not in sys.path:
    sys.path.insert(0, _llm_client_path)

try:
    from llm_client import LLMClient
    LLM_CLIENT_AVAILABLE = True
except ImportError:
    LLM_CLIENT_AVAILABLE = False


class ForumFetcher:
    """论坛帖子采集器"""

    # 采集历史文件
    FETCH_HISTORY_FILE = "forum_fetch_history.json"

    # 采集方式
    METHOD_REQUESTS = "requests"
    METHOD_CHROME_MCP = "chrome_mcp"
    METHOD_PLAYWRIGHT_MCP = "playwright_mcp"

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        knowledge_base_path: Optional[str] = None,
        use_llm_extract: bool = True,
        llm_config_path: Optional[str] = None,
        fetch_method: str = "requests",
        browser_user_data_dir: Optional[str] = None,
        browser_cookies_file: Optional[str] = None,
        auto_login: bool = True,
        login_credentials: Optional[tuple] = None
    ):
        """
        初始化采集器

        Args:
            vector_store: 向量存储
            embedding_model: 嵌入模型
            knowledge_base_path: 知识库路径
            use_llm_extract: 是否使用 LLM 提炼知识点
            llm_config_path: LLM 配置文件路径
            fetch_method: 采集方式 (requests/playwright_mcp)
            browser_user_data_dir: 浏览器用户数据目录
            browser_cookies_file: 浏览器 Cookie 文件
            auto_login: 是否自动登录（需要登录时）
            login_credentials: 登录凭证 (email, password)
        """
        self.store = vector_store or VectorStore()
        self.embedder = embedding_model or EmbeddingModel()
        self.use_llm_extract = use_llm_extract
        self.fetch_method = fetch_method
        self.browser_user_data_dir = browser_user_data_dir
        self.browser_cookies_file = browser_cookies_file
        self.auto_login = auto_login
        self.login_credentials = login_credentials
        self._logged_in = False

        # 知识库路径
        if knowledge_base_path is None:
            knowledge_base_path = os.path.join(
                os.path.dirname(__file__),
                '..',
                'knowledge_base'
            )
        self.kb_path = knowledge_base_path

        # LLM 客户端
        self.llm_client = None
        if use_llm_extract and LLM_CLIENT_AVAILABLE:
            config_path = llm_config_path or os.path.join(
                os.path.dirname(__file__),
                '..',
                'generation_one',
                'naive-ollama',
                'config.json'
            )
            try:
                self.llm_client = LLMClient(config_path)
                print(f"LLM 客户端初始化成功 - 模型: {self.llm_client.get_model_name()}")
            except Exception as e:
                print(f"LLM 客户端初始化失败: {e}")

        # 采集历史
        self.fetch_history = {}
        self._load_fetch_history()

        # HTTP Session
        self.session = None
        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
                'Accept-Language': 'en-US,en;q=0.5',
            })

    def _load_fetch_history(self):
        """加载采集历史"""
        history_path = os.path.join(self.kb_path, self.FETCH_HISTORY_FILE)
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    self.fetch_history = json.load(f)
            except Exception:
                self.fetch_history = {}

    def _save_fetch_history(self):
        """保存采集历史"""
        history_path = os.path.join(self.kb_path, self.FETCH_HISTORY_FILE)
        try:
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(self.fetch_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存采集历史失败: {e}")

    def fetch_post(self, url: str, force: bool = False) -> Dict:
        """
        采集单个帖子

        Args:
            url: 帖子 URL
            force: 是否强制重新采集

        Returns:
            采集结果
        """
        # 检查是否已采集
        if not force and url in self.fetch_history:
            return {'url': url, 'status': 'skipped', 'reason': 'already_fetched'}

        print(f"正在采集: {url} (方式: {self.fetch_method})")

        # 根据采集方式选择方法
        if self.fetch_method == self.METHOD_CHROME_MCP:
            post_data = self._fetch_with_chrome_mcp(url)
        elif self.fetch_method == self.METHOD_PLAYWRIGHT_MCP:
            post_data = self._fetch_with_playwright_mcp(url)
        else:
            post_data = self._fetch_with_requests(url)

        if post_data and post_data.get('title'):
            # 保存原始 JSON
            self._save_post_json(post_data)

            # 入库到向量数据库
            chunk_count = self._ingest_post(post_data)

            # 更新采集历史
            self.fetch_history[url] = {
                'title': post_data.get('title', ''),
                'fetched_at': datetime.now().isoformat(),
                'chunk_count': chunk_count,
                'extracted': self.use_llm_extract,
                'method': self.fetch_method
            }
            self._save_fetch_history()

            print(f"采集成功: {post_data.get('title', 'Unknown')} ({chunk_count} 个知识块)")

        return post_data or {'url': url, 'error': '采集失败'}

    def _fetch_with_requests(self, url: str) -> Optional[Dict]:
        """使用 requests 采集"""
        if not REQUESTS_AVAILABLE:
            return {'url': url, 'error': 'requests 或 BeautifulSoup 未安装'}

        try:
            response = self.session.get(url, timeout=30)

            if response.status_code != 200:
                return {'url': url, 'error': f'HTTP {response.status_code}'}

            soup = BeautifulSoup(response.text, 'html.parser')
            return self._extract_post_data(soup, url)

        except Exception as e:
            return {'url': url, 'error': str(e)}

    def _fetch_with_chrome_mcp(self, url: str) -> Optional[Dict]:
        """
        使用 Chrome DevTools MCP 采集

        需要通过 MCP 工具调用，此方法返回提示信息
        实际使用时需要在 Claude Code 环境中调用 MCP 工具
        """
        print("Chrome DevTools MCP 采集需要在 Claude Code 环境中使用")
        print(f"请使用以下 MCP 工具序列采集: {url}")
        print("1. mcp__plugin_chrome-devtools-mcp_chrome-devtools__new_page")
        print("2. mcp__plugin_chrome-devtools-mcp_chrome-devtools__take_snapshot")
        print("3. mcp__plugin_chrome-devtools-mcp_chrome-devtools__evaluate_script (提取内容)")

        return {
            'url': url,
            'error': 'Chrome MCP 需要在 Claude Code 环境中使用',
            'hint': '请使用 take_snapshot 和 evaluate_script 工具'
        }

    def _do_login(self, page, email: str, password: str) -> bool:
        """
        执行登录操作

        Args:
            page: Playwright 页面对象
            email: 邮箱
            password: 密码

        Returns:
            是否登录成功
        """
        try:
            print("正在登录...")

            # 等待登录表单加载
            page.wait_for_selector('input[type="email"], input[name="email"], input[type="text"]', timeout=5000)

            # 填写邮箱
            email_input = page.query_selector('input[type="email"], input[name="email"], input[type="text"]')
            if email_input:
                email_input.fill(email)
                print(f"填写邮箱: {email}")

            # 填写密码
            password_input = page.query_selector('input[type="password"]')
            if password_input:
                password_input.fill(password)
                print("填写密码")

            # 点击登录按钮
            login_btn = page.query_selector('button[type="submit"], button:has-text("Sign In"), button:has-text("登录")')
            if login_btn:
                login_btn.click()
                print("点击登录按钮")

            # 等待登录完成
            page.wait_for_timeout(3000)

            # 检查是否登录成功
            current_url = page.url.lower()
            if 'sign-in' not in current_url and 'login' not in current_url:
                print("登录成功!")
                self._logged_in = True
                return True

            # 可能需要等待更长时间
            page.wait_for_timeout(5000)
            current_url = page.url.lower()
            if 'sign-in' not in current_url and 'login' not in current_url:
                print("登录成功!")
                self._logged_in = True
                return True

            print("登录可能失败，继续尝试提取...")
            return False

        except Exception as e:
            print(f"登录过程出错: {e}")
            return False

    def _fetch_with_playwright_mcp(self, url: str) -> Optional[Dict]:
        """
        使用 Playwright 浏览器采集（代码内闭环）

        自动启动浏览器、加载页面、提取内容
        支持自动登录和加载已登录的浏览器状态
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {
                'url': url,
                'error': 'playwright 未安装，请运行: pip install playwright && python -m playwright install chromium'
            }

        print(f"使用 Playwright 浏览器采集: {url}")

        # 获取登录凭证
        email, password = None, None
        if self.login_credentials:
            email, password = self.login_credentials
        elif self.auto_login:
            # 尝试从凭证文件加载
            cred_file = os.path.join(
                os.path.dirname(__file__),
                '..',
                'generation_one',
                'naive-ollama',
                'credential.txt'
            )
            if os.path.exists(cred_file):
                try:
                    with open(cred_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content.startswith('['):
                            creds = json.loads(content)
                            email, password = creds[0], creds[1]
                            print(f"加载凭证: {email}")
                except Exception as e:
                    print(f"加载凭证失败: {e}")

        try:
            with sync_playwright() as p:
                # 启动浏览器（非 headless 以避免安全验证）
                if self.browser_user_data_dir:
                    print(f"使用浏览器配置: {self.browser_user_data_dir}")
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=self.browser_user_data_dir,
                        headless=False,
                        args=['--disable-blink-features=AutomationControlled']
                    )
                else:
                    browser = p.chromium.launch(headless=False)
                    context = browser.new_context(
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    )

                    # 加载 Cookie
                    if self.browser_cookies_file and os.path.exists(self.browser_cookies_file):
                        print(f"加载 Cookie: {self.browser_cookies_file}")
                        try:
                            with open(self.browser_cookies_file, 'r', encoding='utf-8') as f:
                                cookies = json.load(f)
                                context.add_cookies(cookies)
                        except Exception as e:
                            print(f"加载 Cookie 失败: {e}")

                page = context.new_page()

                # 访问页面
                print("正在加载页面...")
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                page.wait_for_timeout(2000)

                # 检查是否需要登录
                current_url = page.url.lower()
                needs_login = 'sign-in' in current_url or 'login' in current_url

                if needs_login and email and password and not self._logged_in:
                    print("页面需要登录，执行自动登录...")
                    login_success = self._do_login(page, email, password)

                    if login_success:
                        # 登录成功后重新访问目标页面
                        page.goto(url, wait_until='domcontentloaded', timeout=60000)
                        page.wait_for_timeout(2000)

                # 尝试关闭 Cookie 弹窗
                try:
                    cookie_btns = [
                        'button:has-text("Accept")',
                        'button:has-text("OK")',
                        '#onetrust-accept-btn-handler'
                    ]
                    for selector in cookie_btns:
                        btn = page.query_selector(selector)
                        if btn:
                            btn.click()
                            page.wait_for_timeout(500)
                            print("已关闭 Cookie 弹窗")
                            break
                except Exception:
                    pass

                # 提取标题 - 优化选择器
                title = ''
                title_selectors = [
                    'article h1',
                    'h1',
                    '.post-title',
                    '.article-title'
                ]
                for selector in title_selectors:
                    try:
                        elem = page.query_selector(selector)
                        if elem:
                            text = elem.inner_text().strip()
                            if text and 'privacy' not in text.lower() and 'cookie' not in text.lower() and 'sign' not in text.lower():
                                title = text
                                print(f"标题: {title}")
                                break
                    except Exception:
                        pass

                # 提取正文内容
                content = ''

                # 使用 JavaScript 提取（针对 Zendesk Help Center 优化）
                print("使用 JavaScript 提取内容...")
                try:
                    js_result = page.evaluate('''() => {
                        const result = {
                            title: '',
                            content: '',
                            author: '',
                            date: ''
                        };

                        // 提取标题 - h1 在 article 内
                        const h1 = document.querySelector('article h1');
                        if (h1) {
                            result.title = h1.innerText.trim();
                        }

                        // 提取作者 - 在 .generic 内的链接文本
                        const authorLink = document.querySelector('article a[href*="/profiles/"]');
                        if (authorLink) {
                            result.author = authorLink.innerText.trim();
                        }

                        // 提取时间
                        const timeElem = document.querySelector('article time');
                        if (timeElem) {
                            result.date = timeElem.innerText.trim();
                        }

                        // 提取正文 - article 内的段落和标题
                        const article = document.querySelector('article');
                        if (article) {
                            // 获取主要内容区域（排除评论）
                            const contentArea = article.querySelector('.article-body, .post-body, [class*="content"]');
                            if (contentArea) {
                                result.content = contentArea.innerText.trim();
                            } else {
                                // 提取 article 内的 h4 和 p（正文内容）
                                const contentParts = [];
                                const mainContent = article.querySelector('main, [role="main"], .main-content');
                                const targetArea = mainContent || article;

                                // 提取所有 h4 和 p 标签
                                const elements = targetArea.querySelectorAll('h4, p');
                                for (const el of elements) {
                                    const text = el.innerText.trim();
                                    if (text && text.length > 5 && !text.includes('Related to:') && !text.includes('comments')) {
                                        contentParts.push(text);
                                    }
                                }
                                result.content = contentParts.join('\\n\\n');
                            }
                        }

                        // 如果内容为空，尝试提取所有段落
                        if (!result.content || result.content.length < 50) {
                            const paragraphs = document.querySelectorAll('article p');
                            const texts = Array.from(paragraphs)
                                .map(p => p.innerText.trim())
                                .filter(t => t.length > 10 && !t.includes('Related to:') && !t.includes('comments'));
                            result.content = texts.join('\\n\\n');
                        }

                        return result;
                    }''')

                    if js_result:
                        title = js_result.get('title', '') or title
                        content = js_result.get('content', '')
                        print(f"JavaScript 提取成功: 标题='{title[:50]}...', 内容={len(content)} 字符")
                except Exception as e:
                    print(f"JavaScript 提取失败: {e}")

                # 提取代码块
                code_blocks = []
                try:
                    code_elements = page.query_selector_all('pre, code')
                    for code in code_elements:
                        code_text = code.inner_text().strip()
                        if len(code_text) > 10:
                            code_blocks.append(code_text)
                except Exception:
                    pass

                # 关闭浏览器/上下文
                if self.browser_user_data_dir:
                    context.close()
                else:
                    browser.close()

                if not content or len(content) < 50:
                    return {'url': url, 'error': f'未能提取到足够内容 (仅 {len(content)} 字符)，可能需要登录'}

                print(f"页面内容提取成功: {len(content)} 字符")

                return {
                    'url': url,
                    'title': title,
                    'content': content,
                    'code_blocks': code_blocks if code_blocks else None,
                    'source': 'playwright_browser'
                }

        except PlaywrightTimeout:
            return {'url': url, 'error': '页面加载超时'}
        except Exception as e:
            return {'url': url, 'error': f'Playwright 采集失败: {e}'}

    def fetch_with_browser_snapshot(self, url: str, snapshot_content: str) -> Dict:
        """
        使用浏览器快照内容进行采集

        当使用 Chrome MCP 或 Playwright MCP 获取页面快照后，
        可以调用此方法处理快照内容

        Args:
            url: 页面 URL
            snapshot_content: 浏览器快照内容（文本格式）

        Returns:
            采集结果
        """
        print(f"处理浏览器快照: {url}")

        # 从快照内容提取信息
        post_data = {
            'url': url,
            'title': '',
            'content': snapshot_content,
            'source': 'browser_snapshot'
        }

        # 尝试从快照中提取标题（通常是第一个非空行或 [button] 后的内容）
        lines = [l.strip() for l in snapshot_content.split('\n') if l.strip()]
        if lines:
            # 查找可能的标题
            for line in lines[:10]:
                if not line.startswith('[') and len(line) > 5:
                    post_data['title'] = line[:100]
                    break

        if post_data.get('title'):
            # 保存原始 JSON
            self._save_post_json(post_data)

            # 入库到向量数据库
            chunk_count = self._ingest_post(post_data)

            # 更新采集历史
            self.fetch_history[url] = {
                'title': post_data.get('title', ''),
                'fetched_at': datetime.now().isoformat(),
                'chunk_count': chunk_count,
                'extracted': self.use_llm_extract,
                'method': 'browser_mcp'
            }
            self._save_fetch_history()

            print(f"采集成功: {post_data.get('title', 'Unknown')} ({chunk_count} 个知识块)")

        return post_data

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
            if len(code_text) > 10:
                code_blocks.append(code_text)
        if code_blocks:
            post_data['code_blocks'] = code_blocks

        # 提取标签
        tags = []
        for tag in soup.select('.tag, .label, .category, [class*="tag"]'):
            tag_text = tag.get_text(strip=True)
            if tag_text and len(tag_text) < 50:
                tags.append(tag_text)
        if tags:
            post_data['tags'] = list(set(tags))

        # 提取帖子 ID
        match = re.search(r'/posts/(\d+)', url)
        if match:
            post_data['post_id'] = match.group(1)

        return post_data

    def _save_post_json(self, post_data: Dict) -> str:
        """保存帖子 JSON"""
        post_id = post_data.get('post_id', datetime.now().strftime('%Y%m%d%H%M%S'))
        title = post_data.get('title', 'Untitled')
        safe_title = re.sub(r'[^\w\s-]', '', title)[:50].strip().replace(' ', '_')
        filename = f"forum_post_{post_id}_{safe_title}.json"
        filepath = os.path.join(self.kb_path, filename)

        post_data['fetched_at'] = datetime.now().isoformat()
        post_data['source_file'] = filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(post_data, f, ensure_ascii=False, indent=2)

        return filepath

    def _extract_knowledge_with_llm(self, post_data: Dict) -> List[Dict]:
        """
        使用 LLM 提炼关键知识点

        Args:
            post_data: 原始帖子数据

        Returns:
            提炼后的知识点列表
        """
        if not self.llm_client:
            print("LLM 客户端未初始化，跳过提炼")
            return []

        title = post_data.get('title', '')
        content = post_data.get('content', '')
        code_blocks = post_data.get('code_blocks', [])

        # 构建提炼提示词
        prompt = f"""请从以下论坛帖子中提炼关键知识点。

## 帖子标题
{title}

## 帖子内容
{content[:3000]}

## 代码示例（如有）
{chr(10).join(code_blocks[:3]) if code_blocks else '无'}

## 要求
请提取帖子中的核心知识点，每个知识点包含：
1. 标题：简洁概括该知识点
2. 内容：详细描述知识点内容
3. 类型：属于哪种类型（技巧/经验/问题解决/代码示例）
4. 相关领域：如动量因子、数据字段、优化技巧等

请以 JSON 数组格式输出，格式如下：
[
    {{
        "title": "知识点标题",
        "content": "知识点详细内容",
        "type": "技巧/经验/问题解决/代码示例",
        "domain": "相关领域"
    }}
]

只输出 JSON 数组，不要其他内容。"""

        try:
            print("正在使用 LLM 提炼知识点...")
            response = self.llm_client.generate(prompt, temperature=0.3, timeout=120)

            # 解析 JSON
            json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                knowledge_points = json.loads(json_str)
                print(f"提炼完成: {len(knowledge_points)} 个知识点")
                return knowledge_points
            else:
                print("未能解析 LLM 输出为 JSON")
                return []

        except Exception as e:
            print(f"LLM 提炼失败: {e}")
            return []

    def _ingest_post(self, post_data: Dict) -> int:
        """将帖子入库到向量数据库"""
        source = post_data.get('source_file', 'forum_post.json')

        # 如果启用 LLM 提炼，先提炼知识点
        if self.use_llm_extract and self.llm_client:
            knowledge_points = self._extract_knowledge_with_llm(post_data)

            if knowledge_points:
                # 保存提炼后的知识点
                extracted_file = source.replace('.json', '_extracted.json')
                extracted_path = os.path.join(self.kb_path, extracted_file)
                with open(extracted_path, 'w', encoding='utf-8') as f:
                    json.dump(knowledge_points, f, ensure_ascii=False, indent=2)

                # 入库提炼后的知识点
                texts = []
                metadatas = []

                for i, kp in enumerate(knowledge_points):
                    kp_text = f"# {kp.get('title', '')}\n\n{kp.get('content', '')}"
                    texts.append(kp_text)
                    metadatas.append({
                        "source": extracted_file,
                        "layer": "community_knowledge",
                        "category": "forum_post",
                        "type": kp.get('type', 'general'),
                        "domain": kp.get('domain', 'general'),
                        "post_url": post_data.get('url', ''),
                        "post_title": post_data.get('title', ''),
                        "created_at": datetime.now().isoformat()
                    })

                # 生成向量
                embeddings = self.embedder.embed(texts)

                # 生成 ID
                ids = [
                    hashlib.md5(f"{source}_kp_{i}".encode()).hexdigest()[:16]
                    for i in range(len(texts))
                ]

                # 存入向量数据库
                self.store.add_chunks(
                    chunks=texts,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids
                )

                return len(texts)

        # 如果没有 LLM 提炼，使用原文分块入库
        content_parts = []

        if post_data.get('title'):
            content_parts.append(f"# {post_data['title']}")

        if post_data.get('author'):
            content_parts.append(f"作者: {post_data['author']}")

        if post_data.get('date'):
            content_parts.append(f"时间: {post_data['date']}")

        if post_data.get('content'):
            content_parts.append(f"\n## 内容\n{post_data['content']}")

        if post_data.get('code_blocks'):
            content_parts.append(f"\n## 代码示例\n")
            for code in post_data['code_blocks']:
                content_parts.append(f"```\n{code}\n```")

        content = '\n'.join(content_parts)

        # 分块
        from .chunker import chunk_document
        chunks = chunk_document(content, source)
        chunks = [c for c in chunks if c and c.page_content.strip()]

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
                "layer": "community_knowledge",
                "category": "forum_post",
                "post_url": post_data.get('url', ''),
                "post_title": post_data.get('title', ''),
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
            print(f"[{i}/{total}] 采集: {url}")

            result = self.fetch_post(url, force=force)
            results.append(result)

            # 避免请求过快
            if i < total:
                time.sleep(1)

        # 统计
        success_count = sum(1 for r in results if not r.get('error') and r.get('status') != 'skipped')
        skip_count = sum(1 for r in results if r.get('status') == 'skipped')
        error_count = sum(1 for r in results if r.get('error'))

        print(f"\n批量采集完成: 成功 {success_count}, 跳过 {skip_count}, 失败 {error_count}")

        return results

    def fetch_from_file(self, file_path: str, force: bool = False) -> List[Dict]:
        """
        从文件读取 URL 并批量采集

        Args:
            file_path: URL 文件路径
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

        print(f"从文件读取 {len(urls)} 个 URL")
        return self.fetch_batch(urls, force=force)

    def list_fetched_posts(self) -> List[Dict]:
        """列出已采集的帖子"""
        posts = []
        for url, info in self.fetch_history.items():
            posts.append({
                'url': url,
                'title': info.get('title', ''),
                'fetched_at': info.get('fetched_at', ''),
                'chunk_count': info.get('chunk_count', 0),
                'extracted': info.get('extracted', False),
                'method': info.get('method', 'requests')
            })
        return posts

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "fetched_posts": len(self.fetch_history),
            "llm_extract_enabled": self.use_llm_extract,
            "llm_client_available": self.llm_client is not None,
            "fetch_method": self.fetch_method,
            "vector_store_stats": self.store.get_stats()
        }

    def set_extract_mode(self, use_llm: bool):
        """
        设置提炼模式

        Args:
            use_llm: True 使用 LLM 提炼，False 使用原文分块
        """
        self.use_llm_extract = use_llm
        mode = "LLM 提炼" if use_llm else "原文分块"
        print(f"提炼模式已切换为: {mode}")

    def set_fetch_method(self, method: str):
        """
        设置采集方式

        Args:
            method: 采集方式 (requests/chrome_mcp/playwright_mcp)
        """
        if method in [self.METHOD_REQUESTS, self.METHOD_CHROME_MCP, self.METHOD_PLAYWRIGHT_MCP]:
            self.fetch_method = method
            print(f"采集方式已切换为: {method}")
        else:
            print(f"不支持的采集方式: {method}")
