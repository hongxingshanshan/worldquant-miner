"""
Test script to verify LLM configuration loading
"""
import logging
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Configure logging to show all levels
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)

from generation_two.core.config.config_manager import ConfigManager
from generation_two.ollama.ollama_manager import OllamaManager

def test_config_manager():
    """Test ConfigManager LLM settings"""
    print("\n=== Testing ConfigManager ===")
    config = ConfigManager()

    # Check LLM section
    llm_section = config.get_section('llm')
    if llm_section:
        print(f"LLM Section found: {llm_section.to_dict()}")
    else:
        print("LLM Section NOT found!")

    # Get individual values
    provider = config.get('llm', 'provider', 'ollama')
    print(f"Provider: {provider}")

    return config

def test_ollama_manager_with_config():
    """Test OllamaManager with ConfigManager"""
    print("\n=== Testing OllamaManager with ConfigManager ===")
    config = ConfigManager()

    # Set online provider
    config.set('llm', 'provider', 'online')
    config.set('llm', 'online', {
        'api_key': 'test_key',
        'base_url': 'https://test.example.com',
        'model': 'test-model'
    })

    print(f"Config provider: {config.get('llm', 'provider')}")
    print(f"Config online: {config.get_section('llm').data.get('online')}")

    # Create OllamaManager with config
    manager = OllamaManager(config_manager=config)

    print(f"\nManager provider: {manager.provider}")
    print(f"Manager model: {manager.model}")
    print(f"Manager base_url: {manager.base_url}")
    print(f"Manager api_key: {manager.api_key}")

def test_ollama_manager_without_config():
    """Test OllamaManager without ConfigManager (default)"""
    print("\n=== Testing OllamaManager without ConfigManager ===")
    manager = OllamaManager()

    print(f"Manager provider: {manager.provider}")
    print(f"Manager model: {manager.model}")
    print(f"Manager base_url: {manager.base_url}")

if __name__ == "__main__":
    test_config_manager()
    test_ollama_manager_with_config()
    test_ollama_manager_without_config()
