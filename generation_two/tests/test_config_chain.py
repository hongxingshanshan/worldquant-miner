"""
集成测试：验证完整的 LLM 配置链
测试从 ConfigManager -> TemplateGenerator -> OllamaManager 的配置传递
"""
import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from generation_two.core.config.config_manager import ConfigManager
from generation_two.core.template_generator import TemplateGenerator

def test_full_config_chain():
    """测试完整的配置链"""
    print("=" * 60)
    print("集成测试：验证完整的 LLM 配置链")
    print("=" * 60)

    # 1. 加载配置文件
    config_path = os.path.join(os.path.dirname(__file__), '..', 'generation_two_config')
    print(f"\n1. 加载配置文件: {config_path}")
    print(f"   文件存在: {os.path.exists(config_path)}")

    config_manager = ConfigManager(config_path=config_path)
    print(f"   Provider: {config_manager.get('llm', 'provider', 'N/A')}")

    online_cfg = config_manager.get('llm', 'online', {})
    print(f"   Online Base URL: {online_cfg.get('base_url', 'N/A')}")
    print(f"   Online Model: {online_cfg.get('model', 'N/A')}")

    # 2. 创建 TemplateGenerator（不传入 ollama_url/ollama_model）
    print("\n2. 创建 TemplateGenerator (使用 config_manager)")
    generator = TemplateGenerator(
        config_manager=config_manager
    )

    # 3. 检查 OllamaManager 配置
    print("\n3. 检查 OllamaManager 配置:")
    ollama_manager = generator.ollama_manager
    print(f"   Provider: {ollama_manager.provider}")
    print(f"   Model: {ollama_manager.model}")
    print(f"   Base URL: {ollama_manager.base_url}")
    print(f"   API Key: {'***' + ollama_manager.api_key[-4:] if ollama_manager.api_key else '(empty)'}")

    # 4. 验证
    print("\n4. 验证结果:")
    success = True

    if ollama_manager.provider == 'online':
        print("   ✓ Provider 正确: online")
    else:
        print(f"   ✗ Provider 错误: 期望 'online', 实际 '{ollama_manager.provider}'")
        success = False

    if ollama_manager.model == 'glm-5.1':
        print("   ✓ Model 正确: glm-5.1")
    else:
        print(f"   ✗ Model 错误: 期望 'glm-5.1', 实际 '{ollama_manager.model}'")
        success = False

    if ollama_manager.base_url == 'https://cmkey.cn':
        print("   ✓ Base URL 正确: https://cmkey.cn")
    else:
        print(f"   ✗ Base URL 错误: 期望 'https://cmkey.cn', 实际 '{ollama_manager.base_url}'")
        success = False

    print("\n" + "=" * 60)
    if success:
        print("✅ 所有测试通过！配置链正确。")
    else:
        print("❌ 测试失败！配置链存在问题。")
    print("=" * 60)

    return success

if __name__ == "__main__":
    success = test_full_config_chain()
    sys.exit(0 if success else 1)
