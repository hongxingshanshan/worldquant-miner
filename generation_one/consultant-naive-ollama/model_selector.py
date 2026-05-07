"""
模型选择工具 - 启动时选择要使用的 LLM 模型
"""
import argparse
import sys
import requests
from typing import List, Dict, Optional
from config_manager import get_config_manager, ConfigManager

def get_available_models(ollama_url: str = "http://localhost:11434") -> List[Dict]:
    """获取 Ollama 中可用的模型列表"""
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("models", [])
        else:
            print(f"[错误] 获取模型列表失败: HTTP {response.status_code}")
            return []
    except requests.exceptions.ConnectionError:
        print(f"[错误] 无法连接到 Ollama 服务: {ollama_url}")
        print("[提示] 请确保 Ollama 正在运行")
        return []
    except Exception as e:
        print(f"[错误] 获取模型列表时出错: {e}")
        return []

def display_models(available_models: List[Dict], config_manager: ConfigManager):
    """显示可用模型列表"""
    print("\n" + "="*60)
    print("  可用的 Ollama 模型")
    print("="*60)

    if not available_models:
        print("  [!] 没有找到已安装的模型")
        print("  [提示] 使用 'ollama pull <model_name>' 安装模型")
        return False

    fleet_names = config_manager.get_model_fleet_names()
    default_model = config_manager.config.default_model

    for i, model in enumerate(available_models, 1):
        name = model.get("name", "unknown")
        size = model.get("size", 0) / (1024**3)  # 转换为 GB

        # 标记状态
        status = ""
        if name == default_model:
            status = " [默认]"
        elif name in fleet_names:
            status = " [舰队]"

        print(f"  {i}. {name} ({size:.1f} GB){status}")

    print("="*60)
    return True

def select_model_interactive(available_models: List[Dict], config_manager: ConfigManager) -> Optional[str]:
    """交互式选择模型"""
    if not available_models:
        return None

    default_model = config_manager.config.default_model

    while True:
        print(f"\n当前默认模型: {default_model}")
        print("选项:")
        print("  - 输入数字选择模型")
        print("  - 输入模型名称直接指定")
        print("  - 按 Enter 使用当前默认模型")
        print("  - 输入 'q' 退出")

        choice = input("\n请选择模型: ").strip()

        if choice.lower() == 'q':
            print("已取消")
            return None

        if choice == "":
            return default_model

        # 尝试解析为数字
        try:
            index = int(choice)
            if 1 <= index <= len(available_models):
                selected = available_models[index - 1].get("name")
                print(f"[选择] {selected}")
                return selected
            else:
                print(f"[错误] 请输入 1-{len(available_models)} 之间的数字")
                continue
        except ValueError:
            pass

        # 尝试匹配模型名称
        for model in available_models:
            if model.get("name") == choice or model.get("name", "").startswith(choice):
                print(f"[选择] {model.get('name')}")
                return model.get("name")

        print(f"[错误] 未找到模型: {choice}")

def pull_model(model_name: str, ollama_url: str = "http://localhost:11434") -> bool:
    """拉取模型"""
    print(f"[拉取] 正在下载模型: {model_name}")
    print("[提示] 这可能需要几分钟，请耐心等待...")

    try:
        response = requests.post(
            f"{ollama_url}/api/pull",
            json={"name": model_name},
            timeout=600,
            stream=True
        )

        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    data = line.decode('utf-8')
                    try:
                        import json
                        status = json.loads(data).get("status", "")
                        if "pulling" in status or "downloading" in status:
                            print(f"\r[状态] {status}", end="", flush=True)
                    except:
                        pass
            print(f"\n[成功] 模型 {model_name} 已安装")
            return True
        else:
            print(f"[错误] 拉取模型失败: {response.text}")
            return False
    except Exception as e:
        print(f"[错误] 拉取模型时出错: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='模型选择工具')
    parser.add_argument('--config', type=str, default='config.json',
                       help='配置文件路径 (默认: config.json)')
    parser.add_argument('--ollama-url', type=str, default='http://localhost:11434',
                       help='Ollama API URL (默认: http://localhost:11434)')
    parser.add_argument('--model', type=str, default=None,
                       help='直接指定模型名称，跳过交互选择')
    parser.add_argument('--list', action='store_true',
                       help='仅列出可用模型，不选择')
    parser.add_argument('--set-default', type=str, default=None,
                       help='设置默认模型并保存到配置文件')
    parser.add_argument('--pull', type=str, default=None,
                       help='拉取指定模型')

    args = parser.parse_args()

    # 初始化配置管理器
    config_manager = get_config_manager(args.config)

    # 拉取模型
    if args.pull:
        pull_model(args.pull, args.ollama_url)
        return

    # 设置默认模型
    if args.set_default:
        config_manager.update_default_model(args.set_default)
        config_manager.save_config()
        print(f"[成功] 默认模型已设置为: {args.set_default}")
        return

    # 获取可用模型
    available_models = get_available_models(args.ollama_url)

    # 仅列出模型
    if args.list:
        display_models(available_models, config_manager)
        return

    # 直接指定模型
    if args.model:
        # 检查模型是否存在
        model_names = [m.get("name") for m in available_models]
        if args.model in model_names or any(n.startswith(args.model) for n in model_names):
            print(f"[选择] {args.model}")
            # 输出选择结果供其他脚本使用
            print(f"SELECTED_MODEL={args.model}")
        else:
            print(f"[错误] 模型 {args.model} 未安装")
            print("[提示] 使用 --pull 参数拉取模型")
        return

    # 交互式选择
    if not display_models(available_models, config_manager):
        return

    selected = select_model_interactive(available_models, config_manager)

    if selected:
        # 询问是否保存为默认
        save = input("\n是否保存为默认模型? (y/N): ").strip().lower()
        if save == 'y':
            config_manager.update_default_model(selected)
            config_manager.save_config()
            print(f"[保存] 默认模型已更新为: {selected}")

        # 输出选择结果
        print(f"\nSELECTED_MODEL={selected}")

if __name__ == "__main__":
    main()
