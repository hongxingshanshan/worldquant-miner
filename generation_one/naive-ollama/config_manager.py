"""
配置管理模块 - 支持从配置文件加载模型和参数配置
"""
import json
import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ModelInfo:
    """模型信息"""
    name: str
    size_mb: int
    priority: int
    description: str

@dataclass
class Config:
    """全局配置"""
    # Ollama 配置
    ollama_api_url: str = "http://localhost:11434"
    default_model: str = "llama3:8b"
    fallback_model: str = "qwen2.5-coder:1.5b"

    # 模型舰队
    model_fleet: List[ModelInfo] = field(default_factory=list)

    # 挖掘配置
    batch_size: int = 3
    max_concurrent: int = 2
    mining_interval_hours: int = 6
    sleep_time: int = 30

    # 模拟配置
    instrument_type: str = "EQUITY"
    region: str = "USA"
    universe: str = "TOP3000"
    delay: int = 1
    decay: int = 0
    neutralization: str = "INDUSTRY"
    truncation: float = 0.08

    # 阈值
    min_fitness: float = 0.5
    min_sharpe: float = 1.0

class ConfigManager:
    """配置管理器"""

    DEFAULT_CONFIG = Config(
        model_fleet=[
            ModelInfo("llama3:8b", 4661, 1, "Llama 3 8B - Primary model"),
            ModelInfo("qwen2.5-coder:1.5b", 986, 2, "Qwen 2.5 Coder 1.5B - Fallback model"),
        ]
    )

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config.json"
        self.config = self._load_config()

    def _load_config(self) -> Config:
        """加载配置文件"""
        config = Config()

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Ollama 配置
                ollama = data.get('ollama', {})
                config.ollama_api_url = ollama.get('api_url', config.ollama_api_url)
                config.default_model = ollama.get('default_model', config.default_model)
                config.fallback_model = ollama.get('fallback_model', config.fallback_model)

                # 模型舰队
                model_fleet_data = data.get('model_fleet', [])
                if model_fleet_data:
                    config.model_fleet = [
                        ModelInfo(
                            name=m.get('name', ''),
                            size_mb=m.get('size_mb', 0),
                            priority=m.get('priority', 99),
                            description=m.get('description', '')
                        )
                        for m in model_fleet_data
                    ]
                else:
                    config.model_fleet = self.DEFAULT_CONFIG.model_fleet

                # 挖掘配置
                mining = data.get('mining', {})
                config.batch_size = mining.get('batch_size', config.batch_size)
                config.max_concurrent = mining.get('max_concurrent', config.max_concurrent)
                config.mining_interval_hours = mining.get('mining_interval_hours', config.mining_interval_hours)
                config.sleep_time = mining.get('sleep_time', config.sleep_time)

                # 模拟配置
                simulation = data.get('simulation', {})
                config.instrument_type = simulation.get('instrument_type', config.instrument_type)
                config.region = simulation.get('region', config.region)
                config.universe = simulation.get('universe', config.universe)
                config.delay = simulation.get('delay', config.delay)
                config.decay = simulation.get('decay', config.decay)
                config.neutralization = simulation.get('neutralization', config.neutralization)
                config.truncation = simulation.get('truncation', config.truncation)

                # 阈值
                thresholds = data.get('thresholds', {})
                config.min_fitness = thresholds.get('min_fitness', config.min_fitness)
                config.min_sharpe = thresholds.get('min_sharpe', config.min_sharpe)

                logger.info(f"配置已从 {self.config_path} 加载")
                logger.info(f"默认模型: {config.default_model}")
                logger.info(f"模型舰队: {[m.name for m in config.model_fleet]}")

            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}，使用默认配置")
                config = self.DEFAULT_CONFIG
        else:
            logger.info("配置文件不存在，使用默认配置")
            config = self.DEFAULT_CONFIG
            # 创建默认配置文件
            self._create_default_config()

        return config

    def _create_default_config(self):
        """创建默认配置文件"""
        default_data = {
            "ollama": {
                "api_url": self.DEFAULT_CONFIG.ollama_api_url,
                "default_model": self.DEFAULT_CONFIG.default_model,
                "fallback_model": self.DEFAULT_CONFIG.fallback_model
            },
            "model_fleet": [
                {
                    "name": m.name,
                    "size_mb": m.size_mb,
                    "priority": m.priority,
                    "description": m.description
                }
                for m in self.DEFAULT_CONFIG.model_fleet
            ],
            "mining": {
                "batch_size": self.DEFAULT_CONFIG.batch_size,
                "max_concurrent": self.DEFAULT_CONFIG.max_concurrent,
                "mining_interval_hours": self.DEFAULT_CONFIG.mining_interval_hours,
                "sleep_time": self.DEFAULT_CONFIG.sleep_time
            },
            "simulation": {
                "instrument_type": self.DEFAULT_CONFIG.instrument_type,
                "region": self.DEFAULT_CONFIG.region,
                "universe": self.DEFAULT_CONFIG.universe,
                "delay": self.DEFAULT_CONFIG.delay,
                "decay": self.DEFAULT_CONFIG.decay,
                "neutralization": self.DEFAULT_CONFIG.neutralization,
                "truncation": self.DEFAULT_CONFIG.truncation
            },
            "thresholds": {
                "min_fitness": self.DEFAULT_CONFIG.min_fitness,
                "min_sharpe": self.DEFAULT_CONFIG.min_sharpe
            }
        }

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)
            logger.info(f"已创建默认配置文件: {self.config_path}")
        except Exception as e:
            logger.warning(f"创建默认配置文件失败: {e}")

    def get_model_fleet_names(self) -> List[str]:
        """获取模型舰队名称列表"""
        return [m.name for m in self.config.model_fleet]

    def get_model_by_name(self, name: str) -> Optional[ModelInfo]:
        """根据名称获取模型信息"""
        for model in self.config.model_fleet:
            if model.name == name:
                return model
        return None

    def update_default_model(self, model_name: str):
        """更新默认模型"""
        if self.get_model_by_name(model_name):
            self.config.default_model = model_name
            logger.info(f"默认模型已更新为: {model_name}")
        else:
            logger.warning(f"模型 {model_name} 不在模型舰队中")

    def save_config(self):
        """保存配置到文件"""
        data = {
            "ollama": {
                "api_url": self.config.ollama_api_url,
                "default_model": self.config.default_model,
                "fallback_model": self.config.fallback_model
            },
            "model_fleet": [
                {
                    "name": m.name,
                    "size_mb": m.size_mb,
                    "priority": m.priority,
                    "description": m.description
                }
                for m in self.config.model_fleet
            ],
            "mining": {
                "batch_size": self.config.batch_size,
                "max_concurrent": self.config.max_concurrent,
                "mining_interval_hours": self.config.mining_interval_hours,
                "sleep_time": self.config.sleep_time
            },
            "simulation": {
                "instrument_type": self.config.instrument_type,
                "region": self.config.region,
                "universe": self.config.universe,
                "delay": self.config.delay,
                "decay": self.config.decay,
                "neutralization": self.config.neutralization,
                "truncation": self.config.truncation
            },
            "thresholds": {
                "min_fitness": self.config.min_fitness,
                "min_sharpe": self.config.min_sharpe
            }
        }

        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"配置已保存到 {self.config_path}")

# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None

def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager

def get_config() -> Config:
    """获取当前配置"""
    return get_config_manager().config

def init_config(config_path: Optional[str] = None) -> Config:
    """初始化配置"""
    global _config_manager
    _config_manager = ConfigManager(config_path)
    return _config_manager.config
