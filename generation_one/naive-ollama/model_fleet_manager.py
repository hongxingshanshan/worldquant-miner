#!/usr/bin/env python3
"""
Model Fleet Manager for WorldQuant Alpha Mining System
Automatically manages model hierarchy and downgrades when VRAM issues occur.

支持两种模式：
1. Ollama API 模式（本地运行）
2. Docker 容器模式（容器化运行）
"""
import json
import subprocess
import time
import os
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass

# 尝试导入配置管理器
try:
    from config_manager import get_config_manager, ConfigManager, Config, ModelInfo as ConfigModelInfo
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

@dataclass
class ModelInfo:
    """Information about a model in the fleet."""
    name: str
    size_mb: int
    priority: int  # Lower number = higher priority (used first)
    description: str

    @classmethod
    def from_dict(cls, data: dict) -> 'ModelInfo':
        """从字典创建"""
        return cls(
            name=data.get('name', ''),
            size_mb=data.get('size_mb', 0),
            priority=data.get('priority', 99),
            description=data.get('description', '')
        )

    @classmethod
    def from_config(cls, config_model) -> 'ModelInfo':
        """从配置模块的 ModelInfo 转换"""
        return cls(
            name=config_model.name,
            size_mb=config_model.size_mb,
            priority=config_model.priority,
            description=config_model.description
        )

class ModelFleetManager:
    """Manages a fleet of models with automatic downgrading on VRAM issues.

    支持两种运行模式：
    - ollama_url: 使用 Ollama API（本地模式）
    - container_name: 使用 Docker 容器（容器模式）
    """

    DEFAULT_MODEL_FLEET = [
        {"name": "llama3:8b", "size_mb": 4661, "priority": 1, "description": "Llama 3 8B - Primary model"},
        {"name": "qwen2.5-coder:1.5b", "size_mb": 986, "priority": 2, "description": "Qwen 2.5 Coder 1.5B - Fallback model"},
    ]

    def __init__(self, ollama_url: str = None, container_name: str = None,
                 config_path: Optional[str] = None, model_override: Optional[str] = None):
        """
        初始化模型舰队管理器

        Args:
            ollama_url: Ollama API URL（本地模式）
            container_name: Docker 容器名称（容器模式）
            config_path: 配置文件路径
            model_override: 启动时指定的模型（会移到舰队首位）
        """
        self.ollama_url = ollama_url or "http://localhost:11434"
        self.container_name = container_name or "naive-ollma-gpu"
        self.config_path = config_path or "config.json"
        self.model_override = model_override
        self.current_model_index = 0
        self.vram_error_count = 0
        self.max_vram_errors = 3

        # 判断运行模式
        self.use_docker = container_name is not None and ollama_url is None

        # 加载模型舰队配置
        self.model_fleet = self._load_model_fleet()

        # 如果指定了模型，调整舰队顺序
        if model_override:
            self._reorder_fleet_for_model(model_override)

        # State file to persist current model selection
        self.state_file = "model_fleet_state.json"
        self.load_state()

    def _load_model_fleet(self) -> List[ModelInfo]:
        """从配置文件或使用默认值加载模型舰队"""
        # 尝试从配置管理器加载
        if CONFIG_AVAILABLE:
            try:
                config_manager = get_config_manager(self.config_path)
                return [ModelInfo.from_config(m) for m in config_manager.config.model_fleet]
            except Exception as e:
                logger.warning(f"从配置管理器加载失败: {e}")

        # 尝试直接读取配置文件
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    fleet_data = data.get('model_fleet', [])
                    if fleet_data:
                        return [ModelInfo.from_dict(m) for m in fleet_data]
            except Exception as e:
                logger.warning(f"读取配置文件失败: {e}")

        # 使用默认值
        logger.info("使用默认模型舰队配置")
        return [ModelInfo.from_dict(m) for m in self.DEFAULT_MODEL_FLEET]

    def _reorder_fleet_for_model(self, model_name: str):
        """将指定模型移到舰队首位"""
        for i, model in enumerate(self.model_fleet):
            if model.name == model_name or model.name.startswith(model_name):
                # 将该模型移到首位
                self.model_fleet.insert(0, self.model_fleet.pop(i))
                logger.info(f"模型 {model.name} 已设置为首选")
                return
        # 如果模型不在舰队中，添加到首位
        self.model_fleet.insert(0, ModelInfo(model_name, 0, 0, f"User specified: {model_name}"))
        logger.info(f"添加用户指定模型到舰队首位: {model_name}")
        
    def load_state(self):
        """Load the current model state from file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.current_model_index = state.get('current_model_index', 0)
                    self.vram_error_count = state.get('vram_error_count', 0)
                    logger.info(f"Loaded state: model_index={self.current_model_index}, vram_errors={self.vram_error_count}")
        except Exception as e:
            logger.warning(f"Could not load state: {e}")
            self.current_model_index = 0
            self.vram_error_count = 0
    
    def save_state(self):
        """Save the current model state to file."""
        try:
            state = {
                'current_model_index': self.current_model_index,
                'vram_error_count': self.vram_error_count,
                'current_model': self.get_current_model().name,
                'timestamp': time.time()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info(f"Saved state: {state}")
        except Exception as e:
            logger.error(f"Could not save state: {e}")
    
    def get_current_model(self) -> ModelInfo:
        """Get the current model in use."""
        if self.current_model_index >= len(self.model_fleet):
            self.current_model_index = len(self.model_fleet) - 1
        return self.model_fleet[self.current_model_index]
    
    def get_available_models(self) -> List[str]:
        """Get list of available models (supports both Docker and Ollama API modes)."""
        if self.use_docker:
            return self._get_available_models_docker()
        else:
            return self._get_available_models_ollama()

    def _get_available_models_docker(self) -> List[str]:
        """Get list of available models in the Docker container."""
        try:
            result = subprocess.run([
                'docker', 'exec', self.container_name, 'ollama', 'list'
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                models = []
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if parts:
                            models.append(parts[0])
                return models
            else:
                logger.error(f"Failed to get available models: {result.stderr}")
                return []
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []

    def _get_available_models_ollama(self) -> List[str]:
        """Get list of available models via Ollama API."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models_data = response.json()
                return [model['name'] for model in models_data.get('models', [])]
            else:
                logger.error(f"Failed to get available models: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []

    def ensure_model_available(self, model_name: str) -> bool:
        """Ensure a specific model is available, download if needed."""
        available_models = self.get_available_models()

        if model_name in available_models:
            logger.info(f"Model {model_name} is already available")
            return True

        logger.info(f"Model {model_name} not found, downloading...")
        if self.use_docker:
            return self._download_model_docker(model_name)
        else:
            return self._download_model_ollama(model_name)

    def _download_model_docker(self, model_name: str) -> bool:
        """Download model via Docker."""
        try:
            result = subprocess.run([
                'docker', 'exec', self.container_name, 'ollama', 'pull', model_name
            ], capture_output=True, text=True, timeout=600)  # 10 minute timeout

            if result.returncode == 0:
                logger.info(f"Successfully downloaded model {model_name}")
                return True
            else:
                logger.error(f"Failed to download model {model_name}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error downloading model {model_name}: {e}")
            return False

    def _download_model_ollama(self, model_name: str) -> bool:
        """Download model via Ollama API."""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/pull",
                json={'name': model_name},
                timeout=600  # 10 minute timeout
            )
            if response.status_code == 200:
                logger.info(f"Successfully downloaded model {model_name}")
                return True
            else:
                logger.error(f"Failed to download model {model_name}: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error downloading model {model_name}: {e}")
            return False
    
    def detect_vram_error(self, log_line: str) -> bool:
        """Detect VRAM recovery timeout errors in log lines."""
        vram_error_indicators = [
            "gpu VRAM usage didn't recover within timeout",
            "VRAM usage didn't recover",
            "gpu memory exhausted",
            "CUDA out of memory",
            "GPU memory allocation failed"
        ]
        
        return any(indicator.lower() in log_line.lower() for indicator in vram_error_indicators)
    
    def handle_vram_error(self) -> bool:
        """Handle VRAM error by downgrading to a smaller model."""
        self.vram_error_count += 1
        logger.warning(f"VRAM error detected! Count: {self.vram_error_count}/{self.max_vram_errors}")
        
        if self.vram_error_count >= self.max_vram_errors:
            return self.downgrade_model()
        
        self.save_state()
        return False
    
    def downgrade_model(self) -> bool:
        """Downgrade to the next smaller model in the fleet."""
        if self.current_model_index >= len(self.model_fleet) - 1:
            logger.error("Already using the smallest model in the fleet!")
            logger.warning("VRAM error persists with smallest model - triggering application reset")
            return self.trigger_application_reset()

        old_model = self.get_current_model()
        self.current_model_index += 1
        new_model = self.get_current_model()

        logger.warning(f"Downgrading model: {old_model.name} -> {new_model.name}")

        # Ensure the new model is available
        if not self.ensure_model_available(new_model.name):
            logger.error(f"Failed to ensure model {new_model.name} is available")
            self.current_model_index -= 1  # Revert
            return False

        # Reset VRAM error count
        self.vram_error_count = 0

        # Save state
        self.save_state()

        # Update the alpha generator configuration
        self.update_alpha_generator_config(new_model.name)

        logger.info(f"Successfully downgraded to {new_model.name}")
        return True
    
    def restart_with_new_model(self, model_name: str) -> bool:
        """Restart the application with the new model."""
        logger.info(f"Restarting application with model: {model_name}")
        
        try:
            # Update the alpha generator configuration
            self.update_alpha_generator_config(model_name)
            
            # Restart the Docker container
            result = subprocess.run([
                'docker-compose', '-f', 'docker-compose.gpu.yml', 'restart', 'naive-ollma'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info(f"Successfully restarted with model {model_name}")
                return True
            else:
                logger.error(f"Failed to restart container: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error restarting with new model: {e}")
            return False
    
    def update_alpha_generator_config(self, model_name: str):
        """Update the alpha generator configuration to use the new model."""
        try:
            # Update the default model in alpha_generator_ollama.py
            with open('alpha_generator_ollama.py', 'r', encoding='utf-8') as f:
                content = f.read()

            # 获取当前默认模型（从配置或使用默认值）
            current_default = "llama3:8b"  # 后备默认值
            if CONFIG_AVAILABLE:
                try:
                    config_manager = get_config_manager(self.config_path)
                    current_default = config_manager.config.default_model
                except:
                    pass

            # Replace the default model
            content = content.replace(
                f"default='{current_default}'",
                f"default='{model_name}'"
            )
            content = content.replace(
                f"getattr(self, 'model_name', '{current_default}')",
                f"getattr(self, 'model_name', '{model_name}')"
            )

            with open('alpha_generator_ollama.py', 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Updated alpha generator config to use {model_name}")
        except Exception as e:
            logger.error(f"Error updating alpha generator config: {e}")
    
    def monitor_logs(self):
        """Monitor Docker logs for VRAM errors."""
        logger.info("Starting VRAM error monitoring...")
        
        try:
            process = subprocess.Popen([
                'docker-compose', '-f', 'docker-compose.gpu.yml', 'logs', '-f', 'naive-ollma'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            for line in process.stdout:
                if self.detect_vram_error(line):
                    logger.warning(f"VRAM error detected in logs: {line.strip()}")
                    if self.handle_vram_error():
                        logger.info("Model downgraded and application restarted")
                        break  # Exit monitoring after restart
                
                # Also check for successful operations to reset error count
                if "successful" in line.lower() or "completed" in line.lower():
                    if self.vram_error_count > 0:
                        logger.info("Successful operation detected, resetting VRAM error count")
                        self.vram_error_count = 0
                        self.save_state()
        
        except KeyboardInterrupt:
            logger.info("VRAM monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error monitoring logs: {e}")
    
    def get_fleet_status(self) -> Dict:
        """Get the current status of the model fleet."""
        current_model = self.get_current_model()
        available_models = self.get_available_models()
        
        return {
            'current_model': {
                'name': current_model.name,
                'size_mb': current_model.size_mb,
                'description': current_model.description,
                'index': self.current_model_index
            },
            'vram_error_count': self.vram_error_count,
            'max_vram_errors': self.max_vram_errors,
            'available_models': available_models,
            'fleet_size': len(self.model_fleet),
            'can_downgrade': self.current_model_index < len(self.model_fleet) - 1
        }
    
    def reset_to_largest_model(self):
        """Reset to the largest model in the fleet."""
        self.current_model_index = 0
        self.vram_error_count = 0
        self.save_state()
        logger.info("Reset to largest model in fleet")
        return self.restart_with_new_model(self.get_current_model().name)

    def trigger_application_reset(self) -> bool:
        """Trigger a complete application reset when VRAM issues persist with smallest model.

        This is called when the smallest model still has VRAM issues.
        Resets to the largest model and updates configuration.
        """
        try:
            logger.warning("Triggering application reset due to persistent VRAM issues")

            # Reset to the largest model
            self.current_model_index = 0
            self.vram_error_count = 0
            self.save_state()

            # Update configuration to use largest model
            self.update_alpha_generator_config(self.get_current_model().name)

            logger.info("Application reset completed - returning to largest model")
            return True

        except Exception as e:
            logger.error(f"Error during application reset: {e}")
            return False

def main():
    """Main function for testing the model fleet manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Model Fleet Manager')
    parser.add_argument('--monitor', action='store_true', help='Start VRAM monitoring')
    parser.add_argument('--status', action='store_true', help='Show fleet status')
    parser.add_argument('--reset', action='store_true', help='Reset to largest model')
    parser.add_argument('--downgrade', action='store_true', help='Force downgrade to next model')
    
    args = parser.parse_args()
    
    manager = ModelFleetManager()
    
    if args.status:
        status = manager.get_fleet_status()
        print(json.dumps(status, indent=2))
    elif args.reset:
        manager.reset_to_largest_model()
    elif args.downgrade:
        manager.downgrade_model()
    elif args.monitor:
        manager.monitor_logs()
    else:
        print("Use --help to see available options")

if __name__ == "__main__":
    main()
