"""
统一 LLM 客户端 - 支持 Ollama 本地模型和线上大模型
"""
import os
import json
import logging
import requests
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# 加载 .env 文件的辅助函数
def _load_env_file(config_path: str = None):
    """从多个可能的位置加载 .env 文件"""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    # 可能的 .env 文件位置
    env_paths = []

    # 1. 从配置文件所在目录
    if config_path:
        config_dir = Path(config_path).parent
        if config_dir:
            env_paths.append(config_dir / ".env")

    # 2. 从脚本所在目录
    env_paths.append(Path(__file__).parent / ".env")

    # 3. 当前工作目录
    env_paths.append(Path.cwd() / ".env")

    # 尝试加载第一个存在的 .env 文件
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            return

# 初始加载（模块导入时）
_load_env_file()

class LLMClient:
    """统一 LLM 客户端"""

    def __init__(self, config_path: str = "config.json"):
        # 再次尝试从配置文件目录加载 .env
        _load_env_file(config_path)

        self.config = self._load_config(config_path)
        # provider 放在顶层配置
        self.provider = self.config.get("provider", "ollama")

        if self.provider == "online":
            self._init_online_client()
        else:
            self._init_ollama_client()

    def _load_config(self, config_path: str) -> Dict:
        """加载配置"""
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}")
        return {}

    def _init_online_client(self):
        """初始化线上大模型客户端"""
        llm_config = self.config.get("llm", {})
        self.api_key = os.environ.get("LLM_API_KEY", llm_config.get("api_key", ""))
        self.base_url = os.environ.get("LLM_BASE_URL", llm_config.get("base_url", "https://cmkey.cn"))
        self.model = os.environ.get("LLM_MODEL", llm_config.get("model", "glm-5.1"))
        self.max_tokens = llm_config.get("max_tokens", 4096)

        # 尝试导入 anthropic 库
        self.client = None
        try:
            import anthropic
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            self.client = anthropic.Anthropic(**client_kwargs)
            logger.info(f"线上大模型客户端初始化成功 - 模型: {self.model}, URL: {self.base_url}")
        except ImportError:
            logger.warning("anthropic 库未安装，使用 requests 方式调用")
        except Exception as e:
            logger.warning(f"anthropic 客户端初始化失败: {e}，使用 requests 方式调用")

    def _init_ollama_client(self):
        """初始化 Ollama 本地模型客户端"""
        ollama_config = self.config.get("ollama", {})
        self.ollama_url = ollama_config.get("api_url", "http://localhost:11434")
        self.model = ollama_config.get("default_model", "llama3:8b")
        logger.info(f"Ollama 客户端初始化成功 - 模型: {self.model}, URL: {self.ollama_url}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.3, max_tokens: Optional[int] = None,
                 timeout: int = 360) -> str:
        """
        生成文本

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大 token 数
            timeout: 超时时间（秒）

        Returns:
            生成的文本
        """
        if self.provider == "online":
            return self._generate_online(prompt, system_prompt, temperature, max_tokens, timeout)
        else:
            return self._generate_ollama(prompt, temperature, max_tokens, timeout)

    def _generate_online(self, prompt: str, system_prompt: Optional[str],
                         temperature: float, max_tokens: Optional[int], timeout: int) -> str:
        """调用线上大模型"""
        max_tokens = max_tokens or self.max_tokens

        if self.client:
            # 使用 anthropic SDK
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt or "",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature
                )
                # 处理不同类型的 content block（GLM-5.1 可能返回 ThinkingBlock）
                text_parts = []
                for block in response.content:
                    # 检查 block 类型
                    if hasattr(block, 'text'):
                        text_parts.append(block.text)
                    elif hasattr(block, 'type') and block.type == 'text':
                        text_parts.append(block.text)
                    # 跳过 ThinkingBlock 等其他类型
                return "".join(text_parts)
            except Exception as e:
                logger.error(f"anthropic SDK 调用失败: {e}，尝试使用 requests")
                # 降级到 requests 方式

        # 使用 requests 直接调用
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        data = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_prompt or "",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature
        }

        try:
            response = requests.post(
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=data,
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()
            # 处理不同类型的 content block
            text_parts = []
            for block in result.get("content", []):
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            return "".join(text_parts)
        except requests.exceptions.Timeout:
            logger.error(f"线上大模型请求超时 ({timeout}s)")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"线上大模型请求失败: {e}")
            raise

    def _generate_ollama(self, prompt: str, temperature: float,
                         max_tokens: Optional[int], timeout: int) -> str:
        """调用 Ollama 本地模型"""
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature,
            "num_predict": max_tokens or 1000
        }

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=data,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.exceptions.Timeout:
            logger.error(f"Ollama 请求超时 ({timeout}s)")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama 请求失败: {e}")
            raise

    def get_model_name(self) -> str:
        """获取当前模型名称"""
        return self.model

    def is_online(self) -> bool:
        """是否使用线上模型"""
        return self.provider == "online"

    def get_provider(self) -> str:
        """获取当前提供商"""
        return self.provider

    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        if self.provider == "online":
            # 线上模型返回配置的模型
            return [self.model]
        else:
            # Ollama 返回本地可用模型
            try:
                response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return [m.get("name") for m in models]
            except Exception as e:
                logger.warning(f"获取 Ollama 模型列表失败: {e}")
            return []

    def set_model(self, model_name: str):
        """设置模型"""
        self.model = model_name
        logger.info(f"模型已切换为: {model_name}")
