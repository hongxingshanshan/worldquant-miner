"""
测试 LLM 配置加载
验证 OllamaManager 是否正确读取在线 LLM 配置
"""
import os
import sys

# 设置环境变量（模拟 .env 文件）
os.environ['LLM_PROVIDER'] = 'online'
os.environ['LLM_API_KEY'] = 'test_key'
os.environ['LLM_BASE_URL'] = 'https://cmkey.cn'
os.environ['LLM_MODEL'] = 'glm-5.1'

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from generation_two.ollama.ollama_manager import OllamaManager

def test_env_config():
    """测试从环境变量加载配置"""
    print("=" * 60)
    print("测试 LLM 配置加载")
    print("=" * 60)

    # 不传入 config_manager，应该从环境变量读取
    manager = OllamaManager()

    print(f"\n配置结果:")
    print(f"  Provider: {manager.provider}")
    print(f"  Model: {manager.model}")
    print(f"  Base URL: {manager.base_url}")
    print(f"  API Key: {'***' + manager.api_key[-4:] if manager.api_key else '(empty)'}")

    # 验证
    print(f"\n验证:")
    if manager.provider == 'online':
        print(f"  ✓ Provider 正确: online")
    else:
        print(f"  ✗ Provider 错误: 期望 'online', 实际 '{manager.provider}'")

    if manager.model == 'glm-5.1':
        print(f"  ✓ Model 正确: glm-5.1")
    else:
        print(f"  ✗ Model 错误: 期望 'glm-5.1', 实际 '{manager.model}'")

    if manager.base_url == 'https://cmkey.cn':
        print(f"  ✓ Base URL 正确: https://cmkey.cn")
    else:
        print(f"  ✗ Base URL 错误: 期望 'https://cmkey.cn', 实际 '{manager.base_url}'")

    print("\n" + "=" * 60)

    return manager.provider == 'online' and manager.model == 'glm-5.1' and manager.base_url == 'https://cmkey.cn'

if __name__ == "__main__":
    success = test_env_config()
    sys.exit(0 if success else 1)
