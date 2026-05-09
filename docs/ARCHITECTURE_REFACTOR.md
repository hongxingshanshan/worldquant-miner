# WorldQuant Miner 架构重构方案

**版本**: 1.0  
**日期**: 2026-05-09  
**状态**: 待实施

---

## 一、重构目标

1. **消除代码重复**: 从 70%+ 降低到 < 10%
2. **提升可维护性**: 文件行数 < 500，函数行数 < 50
3. **增强扩展性**: 支持策略插件动态加载
4. **提高测试覆盖**: 从 < 5% 提升到 > 80%

---

## 二、完整目录结构

```
worldquant-miner/
│
├── .github/                              # GitHub 配置
│   ├── workflows/                        # CI/CD 工作流
│   │   ├── test.yml                      # 测试流水线
│   │   ├── lint.yml                      # 代码检查
│   │   └── release.yml                   # 发布流程
│   ├── ISSUE_TEMPLATE/                   # Issue 模板
│   └── PULL_REQUEST_TEMPLATE.md          # PR 模板
│
├── .claude/                              # Claude Code 配置
│   ├── settings.json                     # 项目设置
│   ├── rules/                            # 规则文件
│   │   ├── general.md
│   │   └── python.md
│   └── projects/
│       └── C--WorkSpace-worldquant-miner/
│           └── memory/                   # 项目记忆
│
├── config/                               # 配置文件（根目录）
│   ├── default.yaml                      # 默认配置
│   ├── development.yaml                  # 开发环境配置
│   ├── production.yaml                   # 生产环境配置
│   └── models.yaml                       # 模型舰队配置
│
├── knowledge_base/                       # 知识库
│   ├── operators.json                    # 操作符定义
│   ├── data_fields/                      # 数据字段
│   │   ├── fundamental.json
│   │   ├── price_volume.json
│   │   ├── analyst.json
│   │   └── ...
│   ├── patterns/                         # 成功模式
│   │   ├── momentum.json
│   │   ├── mean_reversion.json
│   │   └── ...
│   └── community/                        # 社区知识
│       ├── tips.json
│       └── best_practices.json
│
├── tests/                                # 测试（统一）
│   ├── __init__.py
│   ├── conftest.py                       # pytest 配置和 fixtures
│   │
│   ├── unit/                             # 单元测试
│   │   ├── __init__.py
│   │   ├── test_config_manager.py
│   │   ├── test_llm_client.py
│   │   ├── test_validator.py
│   │   ├── test_generator.py
│   │   ├── test_submitter.py
│   │   └── test_orchestrator.py
│   │
│   ├── integration/                      # 集成测试
│   │   ├── __init__.py
│   │   ├── test_workflow_e2e.py          # 端到端工作流
│   │   ├── test_api_integration.py       # WorldQuant API 集成
│   │   ├── test_model_switching.py       # 模型切换
│   │   └── test_concurrent_mining.py     # 并发挖矿
│   │
│   ├── performance/                      # 性能测试
│   │   ├── __init__.py
│   │   ├── test_concurrent_load.py
│   │   ├── test_memory_usage.py
│   │   └── test_api_rate_limit.py
│   │
│   └── fixtures/                         # 测试数据
│       ├── __init__.py
│       ├── mock_ollama.py                # Ollama 模拟
│       ├── mock_wq_api.py                # WorldQuant API 模拟
│       ├── sample_alphas.json
│       └── sample_results.json
│
├── shared/                               # 共享模块（新增）
│   ├── __init__.py
│   │
│   ├── config/                           # 配置管理
│   │   ├── __init__.py
│   │   ├── manager.py                    # 统一配置管理器
│   │   ├── schema.py                     # 配置模式定义
│   │   └── validators.py                 # 配置验证器
│   │
│   ├── llm/                              # LLM 客户端抽象
│   │   ├── __init__.py
│   │   ├── base.py                       # 抽象接口
│   │   ├── ollama_client.py              # Ollama 实现
│   │   ├── online_client.py              # 在线模型实现
│   │   └── factory.py                    # 客户端工厂
│   │
│   ├── logging/                          # 日志工具
│   │   ├── __init__.py
│   │   ├── setup.py                      # 日志配置
│   │   ├── formatters.py                 # 格式化器
│   │   └── handlers.py                   # 处理器
│   │
│   ├── process/                          # 进程管理
│   │   ├── __init__.py
│   │   ├── cleanup.py                    # 进程清理
│   │   ├── signals.py                    # 信号处理
│   │   └── pool.py                       # 进程池管理
│   │
│   ├── monitoring/                       # 监控工具
│   │   ├── __init__.py
│   │   ├── health.py                     # 健康检查
│   │   ├── vram.py                       # VRAM 监控
│   │   └── metrics.py                    # 指标收集
│   │
│   ├── validation/                       # 验证工具
│   │   ├── __init__.py
│   │   ├── ast_parser.py                 # AST 解析
│   │   ├── expression_validator.py       # 表达式验证
│   │   └── template_checker.py           # 模板检查
│   │
│   ├── utils/                            # 通用工具
│   │   ├── __init__.py
│   │   ├── retry.py                      # 重试机制
│   │   ├── rate_limiter.py               # 限流器
│   │   ├── cache.py                      # 缓存工具
│   │   ├── http_client.py                # HTTP 客户端封装
│   │   └── helpers.py                    # 辅助函数
│   │
│   └── security/                         # 安全工具
│       ├── __init__.py
│       ├── credential_manager.py         # 凭证管理
│       └── sanitizer.py                  # 数据脱敏
│
├── core/                                 # 核心业务逻辑
│   ├── __init__.py
│   │
│   ├── generator/                        # Alpha 生成
│   │   ├── __init__.py
│   │   ├── base.py                       # 生成器抽象接口
│   │   ├── alpha_generator.py            # Alpha 表达式生成器
│   │   ├── prompt_builder.py             # 提示词构建器
│   │   ├── template_generator.py         # 模板生成器
│   │   └── variation_generator.py        # 变体生成器
│   │
│   ├── validator/                        # Alpha 验证
│   │   ├── __init__.py
│   │   ├── base.py                       # 验证器抽象接口
│   │   ├── syntax_validator.py           # 语法验证
│   │   ├── semantic_validator.py         # 语义验证
│   │   └── duplicate_detector.py         # 重复检测
│   │
│   ├── tester/                           # Alpha 测试
│   │   ├── __init__.py
│   │   ├── base.py                       # 测试器抽象接口
│   │   ├── simulation_tester.py          # 模拟测试
│   │   ├── batch_tester.py               # 批量测试
│   │   └── result_parser.py              # 结果解析
│   │
│   ├── submitter/                        # Alpha 提交
│   │   ├── __init__.py
│   │   ├── base.py                       # 提交器抽象接口
│   │   ├── alpha_submitter.py            # Alpha 提交器
│   │   └── submission_tracker.py         # 提交追踪
│   │
│   ├── orchestrator/                     # 编排器
│   │   ├── __init__.py
│   │   ├── base.py                       # 编排器抽象接口
│   │   ├── mining_orchestrator.py        # 挖矿编排器
│   │   ├── model_manager.py              # 模型管理
│   │   ├── task_scheduler.py             # 任务调度
│   │   └── workflow_engine.py            # 工作流引擎
│   │
│   └── api/                              # API 客户端
│       ├── __init__.py
│       ├── base.py                       # API 基类
│       ├── worldquant_api.py             # WorldQuant Brain API
│       └── rate_limiter.py               # API 限流
│
├── strategies/                           # 策略插件（解耦）
│   ├── __init__.py
│   ├── base.py                           # 策略抽象接口
│   ├── registry.py                       # 策略注册表
│   │
│   ├── naive/                            # 基础策略
│   │   ├── __init__.py
│   │   ├── strategy.py                   # 策略实现
│   │   └── config.yaml                   # 策略配置
│   │
│   ├── consultant/                       # 顾问策略
│   │   ├── __init__.py
│   │   ├── strategy.py
│   │   ├── advisor.py                    # 顾问逻辑
│   │   └── config.yaml
│   │
│   ├── bandit/                           # 多臂老虎机策略
│   │   ├── __init__.py
│   │   ├── strategy.py
│   │   ├── arm_selector.py               # 臂选择器
│   │   ├── reward_calculator.py          # 奖励计算
│   │   └── config.yaml
│   │
│   ├── evolution/                        # 演化策略
│   │   ├── __init__.py
│   │   ├── strategy.py
│   │   ├── crossover.py                  # 交叉操作
│   │   ├── mutation.py                   # 变异操作
│   │   └── config.yaml
│   │
│   └── templates/                        # 模板策略
│       ├── __init__.py
│       ├── strategy.py
│       ├── template_library.py           # 模板库
│       └── config.yaml
│
├── interfaces/                           # 用户界面
│   ├── __init__.py
│   │
│   ├── cli/                              # 命令行界面
│   │   ├── __init__.py
│   │   ├── main.py                       # CLI 入口
│   │   ├── commands/                     # 命令定义
│   │   │   ├── __init__.py
│   │   │   ├── mine.py                   # 挖矿命令
│   │   │   ├── submit.py                 # 提交命令
│   │   │   ├── status.py                 # 状态命令
│   │   │   └── config.py                 # 配置命令
│   │   └── utils/                        # CLI 工具
│   │       ├── __init__.py
│   │       ├── display.py                # 显示工具
│   │       └── progress.py               # 进度条
│   │
│   ├── web/                              # Web Dashboard
│   │   ├── __init__.py
│   │   ├── app.py                        # Flask 应用
│   │   ├── routes/                       # 路由
│   │   │   ├── __init__.py
│   │   │   ├── api.py                    # REST API
│   │   │   ├── dashboard.py              # Dashboard 页面
│   │   │   └── websocket.py              # WebSocket
│   │   ├── static/                       # 静态文件
│   │   │   ├── css/
│   │   │   ├── js/
│   │   │   └── img/
│   │   ├── templates/                    # HTML 模板
│   │   │   ├── base.html
│   │   │   ├── dashboard.html
│   │   │   └── status.html
│   │   └── api/                          # API 定义
│   │       ├── __init__.py
│   │       ├── schemas.py                # 数据模式
│   │       └── serializers.py            # 序列化器
│   │
│   └── gui/                              # PyQt5 GUI
│       ├── __init__.py
│       ├── main.py                       # GUI 入口
│       ├── main_window.py                # 主窗口
│       ├── components/                   # UI 组件
│       │   ├── __init__.py
│       │   ├── config_panel.py
│       │   ├── dashboard_panel.py
│       │   ├── log_panel.py
│       │   ├── monitor_panel.py
│       │   └── workflow_panel.py
│       ├── dialogs/                      # 对话框
│       │   ├── __init__.py
│       │   ├── login_dialog.py
│       │   └── settings_dialog.py
│       ├── models/                       # 数据模型
│       │   ├── __init__.py
│       │   └── alpha_model.py
│       ├── styles/                       # 样式
│       │   └── theme.py
│       └── resources/                    # 资源文件
│           ├── icons/
│           └── images/
│
├── storage/                              # 数据存储
│   ├── __init__.py
│   ├── base.py                           # 存储抽象接口
│   ├── json_store.py                     # JSON 存储
│   ├── sqlite_store.py                   # SQLite 存储
│   ├── backtest_storage.py               # 回测结果存储
│   └── migration/                        # 数据迁移
│       └── versions/
│
├── scripts/                              # 脚本文件
│   ├── setup.sh                          # Linux/Mac 安装脚本
│   ├── setup.bat                         # Windows 安装脚本
│   ├── start_mining.bat                  # 启动挖矿
│   ├── start_dashboard.bat               # 启动 Dashboard
│   ├── start_gui.bat                     # 启动 GUI
│   ├── check_health.py                   # 健康检查
│   └── cleanup.py                        # 清理脚本
│
├── docs/                                 # 文档
│   ├── README.md                         # 项目说明
│   ├── ARCHITECTURE.md                   # 架构设计
│   ├── API.md                            # API 文档
│   ├── CONFIGURATION.md                  # 配置说明
│   ├── STRATEGIES.md                     # 策略开发指南
│   ├── CONTRIBUTING.md                   # 贡献指南
│   └── CHANGELOG.md                      # 变更日志
│
├── .gitignore                            # Git 忽略配置
├── .env.example                          # 环境变量示例
├── pyproject.toml                        # 项目配置
├── setup.py                              # 安装配置
├── requirements.txt                      # 依赖列表
├── requirements-dev.txt                  # 开发依赖
├── Makefile                              # 构建命令
└── README.md                             # 项目说明
```

---

## 三、核心模块设计

### 3.1 shared/config/manager.py - 统一配置管理

```python
"""统一配置管理器"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import yaml
import os


@dataclass
class Config:
    """全局配置"""
    # LLM 配置
    llm_provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    model_fleet: list = field(default_factory=lambda: ["llama3:8b"])
    
    # API 配置
    api_timeout: int = 30
    api_max_retries: int = 3
    api_rate_limit: float = 2.0  # 请求/秒
    
    # 挖矿配置
    max_concurrent: int = 10
    max_results: int = 1000
    knowledge_base_path: str = "knowledge_base"
    
    # 凭证配置
    credentials_path: Optional[str] = None
    
    @classmethod
    def from_file(cls, path: str) -> 'Config':
        """从 YAML 文件加载配置"""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    @classmethod
    def from_env(cls) -> 'Config':
        """从环境变量加载配置"""
        return cls(
            llm_provider=os.getenv('WQ_LLM_PROVIDER', 'ollama'),
            ollama_url=os.getenv('WQ_OLLAMA_URL', 'http://localhost:11434'),
            credentials_path=os.getenv('WQ_CREDENTIALS_PATH'),
        )


class ConfigManager:
    """配置管理器"""
    
    _instance: Optional['ConfigManager'] = None
    _config: Optional[Config] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load(self, config_path: Optional[str] = None) -> Config:
        """加载配置"""
        if config_path and os.path.exists(config_path):
            self._config = Config.from_file(config_path)
        else:
            self._config = Config.from_env()
        return self._config
    
    @property
    def config(self) -> Config:
        """获取当前配置"""
        if self._config is None:
            self.load()
        return self._config
```

### 3.2 shared/llm/base.py - LLM 客户端抽象

```python
"""LLM 客户端抽象接口"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class BaseLLMClient(ABC):
    """LLM 客户端抽象基类"""
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        pass
    
    @abstractmethod
    def set_model(self, model_name: str) -> None:
        """设置当前模型"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """健康检查"""
        pass
```

### 3.3 core/generator/base.py - 生成器抽象

```python
"""Alpha 生成器抽象接口"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class GenerationResult:
    """生成结果"""
    expression: str
    confidence: float
    metadata: Dict[str, Any]


class BaseGenerator(ABC):
    """Alpha 生成器抽象基类"""
    
    @abstractmethod
    def generate(
        self,
        count: int = 5,
        context: Optional[Dict[str, Any]] = None
    ) -> List[GenerationResult]:
        """生成 Alpha 表达式"""
        pass
    
    @abstractmethod
    def generate_from_template(
        self,
        template: str,
        variations: int = 3
    ) -> List[GenerationResult]:
        """从模板生成变体"""
        pass
```

### 3.4 strategies/base.py - 策略抽象

```python
"""策略抽象接口"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class StrategyConfig:
    """策略配置"""
    name: str
    version: str
    params: Dict[str, Any]


class AlphaStrategy(ABC):
    """Alpha 策略抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """策略版本"""
        pass
    
    @abstractmethod
    def initialize(self, config: StrategyConfig) -> None:
        """初始化策略"""
        pass
    
    @abstractmethod
    def generate(self, context: Dict[str, Any]) -> List[str]:
        """生成 Alpha 表达式列表"""
        pass
    
    @abstractmethod
    def evaluate(self, result: Dict[str, Any]) -> float:
        """评估结果质量，返回 0-1 分数"""
        pass
    
    @abstractmethod
    def adapt(self, feedback: Dict[str, Any]) -> None:
        """根据反馈调整策略"""
        pass
```

---

## 四、文件迁移映射

### 4.1 共享模块迁移

| 源文件 | 目标文件 | 说明 |
|--------|---------|------|
| `generation_one/naive-ollama/config_manager.py` | `shared/config/manager.py` | 合并两套 ConfigManager |
| `generation_two/core/config/config_manager.py` | `shared/config/manager.py` | 合并 |
| `generation_one/naive-ollama/llm_client.py` | `shared/llm/ollama_client.py` | 迁移 |
| `generation_one/naive-ollama/cleanup_handler.py` | `shared/process/cleanup.py` | 迁移 |
| `generation_one/naive-ollama/vram_monitor.py` | `shared/monitoring/vram.py` | 迁移 |
| `generation_one/naive-ollama/health_check.py` | `shared/monitoring/health.py` | 迁移 |

### 4.2 核心模块拆分

| 源文件 | 目标文件 | 行数变化 |
|--------|---------|---------|
| `alpha_generator_ollama.py` (1509行) | `core/generator/alpha_generator.py` (200行) | -87% |
| | `core/generator/prompt_builder.py` (150行) | |
| | `core/generator/template_generator.py` (100行) | |
| | `core/validator/duplicate_detector.py` (100行) | |
| `alpha_expression_miner.py` (461行) | `core/tester/simulation_tester.py` (150行) | -67% |
| | `core/tester/batch_tester.py` (100行) | |
| | `core/tester/result_parser.py` (80行) | |
| `alpha_orchestrator.py` (1080行) | `core/orchestrator/mining_orchestrator.py` (200行) | -81% |
| | `core/orchestrator/model_manager.py` (150行) | |
| | `core/orchestrator/task_scheduler.py` (100行) | |

### 4.3 策略模块迁移

| 源目录 | 目标目录 |
|--------|---------|
| `generation_one/naive-ollama/` | `strategies/naive/` |
| `generation_one/consultant-naive-ollama/` | `strategies/consultant/` |
| `generation_one/consultant-multi-arm-bandit-ollama/` | `strategies/bandit/` |
| `generation_two/evolution/` | `strategies/evolution/` |
| `generation_one/consultant-templates-*/` | `strategies/templates/` |

---

## 五、重构步骤

### 第一阶段：创建骨架（1天）

```bash
# 1. 创建目录结构
mkdir -p shared/{config,llm,logging,process,monitoring,validation,utils,security}
mkdir -p core/{generator,validator,tester,submitter,orchestrator,api}
mkdir -p strategies/{naive,consultant,bandit,evolution,templates}
mkdir -p interfaces/{cli/commands,web/routes,gui/components}
mkdir -p tests/{unit,integration,performance,fixtures}
mkdir -p storage/migration
mkdir -p scripts docs config knowledge_base

# 2. 创建 __init__.py 文件
find shared core strategies interfaces tests storage -type d -exec touch {}/__init__.py \;

# 3. 创建配置文件
touch config/default.yaml config/development.yaml config/production.yaml
```

### 第二阶段：提取共享模块（2-3天）

1. 合并配置管理器 → `shared/config/`
2. 提取 LLM 客户端 → `shared/llm/`
3. 提取进程管理 → `shared/process/`
4. 提取监控工具 → `shared/monitoring/`
5. 提取验证工具 → `shared/validation/`

### 第三阶段：拆分核心模块（3-5天）

1. 拆分 `alpha_generator_ollama.py` → `core/generator/`
2. 拆分 `alpha_expression_miner.py` → `core/tester/`
3. 拆分 `alpha_orchestrator.py` → `core/orchestrator/`
4. 迁移 `improved_alpha_submitter.py` → `core/submitter/`

### 第四阶段：迁移策略（2-3天）

1. 迁移 naive 策略
2. 迁移 consultant 策略
3. 迁移 bandit 策略
4. 迁移 evolution 策略
5. 迁移 templates 策略

### 第五阶段：统一界面（2-3天）

1. 重构 CLI
2. 重构 Web Dashboard
3. 适配 GUI

### 第六阶段：添加测试（3-5天）

1. 添加单元测试
2. 添加集成测试
3. 添加性能测试

---

## 六、依赖关系图

```
                    ┌─────────────┐
                    │   config/   │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
    ┌─────────┐      ┌──────────┐      ┌─────────┐
    │ shared/ │      │  core/   │      │ tests/  │
    └────┬────┘      └────┬─────┘      └────┬────┘
         │                │                 │
         │    ┌───────────┼───────────┐     │
         │    │           │           │     │
         ▼    ▼           ▼           ▼     ▼
    ┌─────────────────────────────────────────┐
    │              strategies/                │
    └────────────────────┬────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐    ┌──────────┐    ┌─────────┐
    │  cli/   │    │   web/   │    │   gui/  │
    └─────────┘    └──────────┘    └─────────┘
```

---

## 七、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 重构期间功能中断 | 高 | 使用 feature branch，保持旧代码可用 |
| 测试覆盖不足 | 中 | 重构前添加基本测试 |
| 依赖关系复杂 | 中 | 使用依赖注入，逐步解耦 |
| 团队不熟悉新结构 | 低 | 编写详细文档和示例 |

---

## 八、验收标准

| 指标 | 当前值 | 目标值 | 验收方法 |
|------|--------|--------|---------|
| 文件最大行数 | 1509 | < 500 | `wc -l` |
| 函数最大行数 | 283 | < 50 | 代码审查 |
| 代码重复率 | 70%+ | < 10% | 抽重复检测工具 |
| 测试覆盖率 | < 5% | > 80% | `pytest --cov` |
| API 响应时间 | 5-10s | < 2s | 性能测试 |
| 内存占用 (24h) | > 1GB | < 200MB | 内存监控 |

---

**文档版本**: 1.0  
**最后更新**: 2026-05-09
