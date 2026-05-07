# WorldQuant Miner - 版本启动指南

## 快速启动

### 方式一：使用启动脚本（推荐）

```bash
# Windows 批处理脚本
.\start_all_versions.bat

# 或 PowerShell 脚本（更美观）
.\start_all_versions.ps1
```

### 方式二：直接启动

```bash
# Generation One - naive-ollama（推荐新手）
cd generation_one\naive-ollama
python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --mining-interval 6 --batch-size 3 --max-concurrent 2 --ollama-model llama3:8b

# Generation One - consultant-naive-ollama（自适应优化）
cd generation_one\consultant-naive-ollama
python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --mining-interval 6 --batch-size 3 --max-concurrent 2 --ollama-model llama3:8b

# Generation One - consultant-multi-arm-bandit-ollama（多臂老虎机）
cd generation_one\consultant-multi-arm-bandit-ollama
python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --mining-interval 6 --batch-size 3 --max-concurrent 2 --ollama-model llama3:8b

# Generation Two（高级）
cd generation_two
pip install PyQt5
python gui/run_gui.py credential.txt

# Alpha ICU（分析工具）
cd generation_one\alpha-icu
python main.py --credentials ./credential.txt

# Web Dashboard（监控面板）
cd generation_one\naive-ollama
python web_dashboard.py
```

## 版本对比

| 版本 | 特点 | 适用场景 |
|------|------|----------|
| **naive-ollama** | 简单直接、Web Dashboard | 新手入门、快速部署 |
| **consultant-naive-ollama** | 自适应优化、VRAM 监控 | 需要自动优化参数 |
| **consultant-multi-arm-bandit-ollama** | 多臂老虎机、智能选择 | 深度优化模型选择 |
| **Generation Two** | 遗传算法、AST 验证、Cyberpunk GUI | 长期研究、深度优化 |
| **alpha-icu** | Alpha 分析、相关性检查 | 分析已有 Alpha |

## 前置要求

1. **Python 3.8+**
2. **Ollama** 运行中（端口 11434）
3. **已安装模型**：`llama3:8b` 或 `qwen2.5-coder:1.5b`
4. **凭证文件**：`credential.txt`（格式：`["email", "password"]`）

## 模型安装

```bash
# 安装 Ollama 模型
ollama pull llama3:8b
ollama pull qwen2.5-coder:1.5b
```

## 推荐使用路径

```
阶段 1: 入门
└── naive-ollama → 理解基础流程

阶段 2: 优化（1-2周后）
└── consultant-naive-ollama → 自适应优化

阶段 3: 高级（1个月后）
└── consultant-multi-arm-bandit-ollama → 多臂老虎机

阶段 4: 进阶（可选）
└── Generation Two → 遗传算法进化

并行使用:
└── alpha-icu → 分析已有 Alpha
```

## 常见问题

### 1. 模型未找到错误
```
Error: model 'xxx' not found
```
**解决方案**：确保已安装对应模型，或使用 `--ollama-model llama3:8b` 参数指定已安装的模型。

### 2. 认证失败
```
Authentication failed
```
**解决方案**：检查 `credential.txt` 格式是否正确：`["email@worldquant.com", "password"]`

### 3. VRAM 不足
**解决方案**：使用较小的模型 `qwen2.5-coder:1.5b`，或减少 `--max-concurrent` 参数。

## 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| Web Dashboard | 5000 | Flask 监控面板 |
| Ollama API | 11434 | Ollama 服务 |
| Generation Two GUI | - | PyQt5 桌面应用 |
