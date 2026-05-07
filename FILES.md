# 📁 项目文件说明

**清理完成时间**: 2026-05-07

---

## 🚀 启动脚本（2 个）

| 脚本 | 用途 | 说明 |
|-----|------|------|
| **start.bat** | 启动 Generation One | 3 种模式：单次挖掘、Dashboard、持续挖掘 |
| **start_generation_two.bat** | 启动 Generation Two | Cyberpunk GUI 界面 |

---

## 📚 核心文档（10 个）

### 必读文档：

| 文档 | 说明 |
|-----|------|
| **README.md** | 项目官方说明（原作者） |
| **START.md** | 快速开始指南（必读）⭐ |
| **QUICKSTART.md** | 详细快速开始 |

### 参考文档：

| 文档 | 说明 |
|-----|------|
| **GENERATION_COMPARISON.md** | Gen One vs Gen Two 详细对比 |
| **ARCHITECTURE_ANALYSIS.md** | 系统架构深度分析 |
| **OLLAMA_MODELS_GUIDE.md** | Ollama 模型推荐 |
| **FORK_CONFIGURATION.md** | Git Fork 配置说明 |

### 项目文档：

| 文档 | 说明 |
|-----|------|
| **RELEASE.md** | 发布说明 |
| **GITHUB_ACTIONS_WORKFLOW.md** | GitHub Actions 工作流 |
| **IMPLEMENTATION_SUMMARY.md** | 实现总结 |

---

## 📂 项目结构

```
worldquant-miner/
│
├── 🚀 启动脚本
│   ├── start.bat                    # Gen One 启动
│   └── start_generation_two.bat     # Gen Two 启动
│
├── 📚 核心文档
│   ├── README.md                    # 官方说明
│   ├── START.md                     # 快速开始 ⭐
│   ├── QUICKSTART.md                # 详细指南
│   ├── GENERATION_COMPARISON.md     # Gen 对比
│   ├── ARCHITECTURE_ANALYSIS.md     # 架构分析
│   └── OLLAMA_MODELS_GUIDE.md       # 模型推荐
│
├── 📁 Generation One
│   └── generation_one/naive-ollama/
│       ├── alpha_generator_ollama.py  # 主程序
│       ├── web_dashboard.py           # Dashboard（可选）
│       ├── alpha_orchestrator.py      # 编排器
│       └── credential.txt             # 凭证文件
│
├── 📁 Generation Two
│   └── generation_two/
│       └── gui/run_gui.py             # Cyberpunk GUI
│
└── 📁 文档归档
    └── docs/archive/                  # 已归档的文档
```

---

## 🎯 快速开始

### 1. 启动 Generation One

```bash
# 双击运行
start.bat

# 选择模式：
# 1 - 单次挖掘（测试）
# 2 - Web Dashboard（监控）
# 3 - 持续挖掘（24/7）
```

### 2. 启动 Generation Two

```bash
# 双击运行
start_generation_two.bat
```

---

## ❓ 常见问题

### Q: 需要分别启动前后端吗？

**A: 不需要。**

- **Generation One**: 单服务架构
  - `alpha_generator_ollama.py` - 主程序（独立运行）
  - `web_dashboard.py` - Dashboard（可选，仅用于监控）

- **Generation Two**: 单 GUI 应用
  - `run_gui.py` - 包含所有功能

### Q: Web Dashboard 是做什么的？

**A: 只是一个监控界面。**

- 显示系统状态（GPU、Ollama、挖掘进度）
- 不影响挖掘程序运行
- 可选功能，不是必需的

### Q: 应该选择哪个模式？

**A: 推荐顺序：**

1. **新手**: 模式 1（单次挖掘）- 测试系统
2. **日常使用**: 模式 3（持续挖掘）- 24/7 自动运行
3. **监控**: 模式 2（Dashboard）- 查看运行状态

---

## ✅ 当前状态

- ✅ 文件已清理
- ✅ 只保留必要脚本
- ✅ 文档已整理
- ✅ 所有依赖已安装
- ✅ 系统可以正常运行

---

**现在文件结构清晰，只保留必要的启动脚本和文档！**
