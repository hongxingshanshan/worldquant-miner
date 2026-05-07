# 模型配置指南

## 概述

系统支持三种方式配置 LLM 模型：

1. **配置文件** - `config.json`（推荐）
2. **命令行参数** - `--ollama-model`
3. **交互式选择** - 启动时选择

## 配置文件 (config.json)

配置文件位于 `generation_one/naive-ollama/config.json`：

```json
{
    "ollama": {
        "api_url": "http://localhost:11434",
        "default_model": "llama3:8b",
        "fallback_model": "qwen2.5-coder:1.5b"
    },
    "model_fleet": [
        {
            "name": "llama3:8b",
            "size_mb": 4661,
            "priority": 1,
            "description": "Llama 3 8B - Primary model"
        },
        {
            "name": "qwen2.5-coder:1.5b",
            "size_mb": 986,
            "priority": 2,
            "description": "Qwen 2.5 Coder 1.5B - Fallback model"
        }
    ],
    "mining": {
        "batch_size": 3,
        "max_concurrent": 2,
        "mining_interval_hours": 6
    },
    "thresholds": {
        "min_fitness": 0.5,
        "min_sharpe": 1.0
    }
}
```

### 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `ollama.api_url` | Ollama API 地址 | `http://localhost:11434` |
| `ollama.default_model` | 默认使用的模型 | `llama3:8b` |
| `ollama.fallback_model` | 备用模型 | `qwen2.5-coder:1.5b` |
| `model_fleet` | 模型舰队列表 | - |
| `mining.batch_size` | 批次大小 | `3` |
| `mining.max_concurrent` | 最大并发数 | `2` |
| `mining.mining_interval_hours` | 挖掘间隔（小时） | `6` |
| `thresholds.min_fitness` | 最小 fitness 阈值 | `0.5` |

## 使用方法

### 方式一：使用配置文件

```bash
cd generation_one\naive-ollama
python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --config config.json
```

### 方式二：命令行指定模型

```bash
# 使用 llama3:8b
python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --ollama-model llama3:8b

# 使用 qwen2.5-coder:1.5b
python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --ollama-model qwen2.5-coder:1.5b
```

### 方式三：交互式选择

```bash
# 启动模型选择工具
python model_selector.py --config config.json

# 或在启动时选择
python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --select-model
```

## 模型选择工具

### 功能

- 列出已安装的模型
- 交互式选择模型
- 设置默认模型
- 拉取新模型

### 使用示例

```bash
# 列出可用模型
python model_selector.py --list

# 设置默认模型
python model_selector.py --set-default llama3:8b

# 拉取新模型
python model_selector.py --pull mistral:7b

# 直接指定模型（跳过交互）
python model_selector.py --model llama3:8b
```

## 添加新模型

### 步骤 1：拉取模型

```bash
ollama pull <model_name>

# 示例
ollama pull mistral:7b
ollama pull codellama:7b
```

### 步骤 2：更新配置文件

编辑 `config.json`，添加到 `model_fleet` 数组：

```json
{
    "model_fleet": [
        {
            "name": "llama3:8b",
            "size_mb": 4661,
            "priority": 1,
            "description": "Llama 3 8B - Primary model"
        },
        {
            "name": "mistral:7b",
            "size_mb": 4100,
            "priority": 2,
            "description": "Mistral 7B - Alternative model"
        },
        {
            "name": "qwen2.5-coder:1.5b",
            "size_mb": 986,
            "priority": 3,
            "description": "Qwen 2.5 Coder 1.5B - Fallback model"
        }
    ]
}
```

### 步骤 3：验证

```bash
python model_selector.py --list
```

## 模型舰队说明

模型舰队（Model Fleet）是一个模型列表，按优先级排序：

- **优先级 1**：首选模型（VRAM 充足时使用）
- **优先级 2+**：备用模型（VRAM 不足时自动降级）

当系统检测到 VRAM 问题时，会自动切换到优先级更低的模型。

## 常见问题

### Q: 模型未找到

```
Error: model 'xxx' not found
```

**解决方案**：
```bash
# 检查已安装模型
ollama list

# 拉取模型
ollama pull xxx
```

### Q: 如何查看当前使用的模型？

```bash
python alpha_orchestrator.py --mode fleet-status
```

### Q: 如何重置到默认模型？

```bash
python alpha_orchestrator.py --mode fleet-reset
```

### Q: 配置文件不存在怎么办？

系统会自动创建默认配置文件 `config.json`。

## 推荐模型

| 模型 | 大小 | VRAM 需求 | 适用场景 |
|------|------|-----------|----------|
| `llama3:8b` | 4.7GB | 8GB+ | 通用，推荐 |
| `qwen2.5-coder:1.5b` | 1GB | 4GB+ | 低 VRAM 备用 |
| `mistral:7b` | 4.1GB | 8GB+ | 高质量生成 |
| `codellama:7b` | 4.1GB | 8GB+ | 代码相关 |
| `phi3:mini` | 2.2GB | 4GB+ | 轻量级 |
