"""
测试 ConfigManager 加载配置文件
验证配置文件路径是否正确
"""
import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from generation_two.core.config.config_manager import ConfigManager

def test_config_manager_load():
    """测试 ConfigManager 加载配置文件"""
    print("=" * 60)
    print("测试 ConfigManager 加载配置文件")
    print("=" * 60)

    # 测试 1: 默认路径
    print("\n测试 1: 默认路径 (generation_two_config.json)")
    cm1 = ConfigManager()
    print(f"  配置文件路径: {cm1.config_path}")
    print(f"  LLM Provider: {cm1.get('llm', 'provider', 'ollama')}")
    print(f"  LLM Model: {cm1.get('llm', 'online', {}).get('model', 'N/A')}")

    # 测试 2: 正确的配置文件路径
    print("\n测试 2: 正确的配置文件路径 (generation_two_config)")
    config_path = os.path.join(os.path.dirname(__file__), '..', 'generation_two_config')
    print(f"  配置文件路径: {config_path}")
    print(f"  文件存在: {os.path.exists(config_path)}")

    cm2 = ConfigManager(config_path=config_path)
    print(f"  LLM Provider: {cm2.get('llm', 'provider', 'ollama')}")

    online_cfg = cm2.get('llm', 'online', {})
    print(f"  Online Model: {online_cfg.get('model', 'N/A')}")
    print(f"  Online Base URL: {online_cfg.get('base_url', 'N/A')}")

    # 验证
    print("\n验证:")
    if cm2.get('llm', 'provider') == 'online':
        print("  ✓ Provider 正确: online")
    else:
        print(f"  ✗ Provider 错误: 期望 'online', 实际 '{cm2.get('llm', 'provider')}'")

    if online_cfg.get('base_url') == 'https://cmkey.cn':
        print("  ✓ Base URL 正确: https://cmkey.cn")
    else:
        print(f"  ✗ Base URL 错误: 期望 'https://cmkey.cn', 实际 '{online_cfg.get('base_url')}'")

    if online_cfg.get('model') == 'glm-5.1':
        print("  ✓ Model 正确: glm-5.1")
    else:
        print(f"  ✗ Model 错误: 期望 'glm-5.1', 实际 '{online_cfg.get('model')}'")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_config_manager_load()
