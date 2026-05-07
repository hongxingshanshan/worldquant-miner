# WorldQuant Miner - 快速开始

**Generation One - 基础自动化挖掘系统**

---

## 🚀 启动方式

### 方式 1：启动脚本（推荐）

```bash
# 双击运行
start.bat

# 选择模式：
# 1 - 单次挖掘（生成 3 个 Alpha）
# 2 - Web Dashboard（监控界面）
# 3 - 持续挖掘（24/7 自动运行）
```

### 方式 2：命令行启动

```bash
cd generation_one\naive-ollama

# 单次挖掘
python alpha_generator_ollama.py --credentials ./credential.txt --batch-size 3 --ollama-model qwen2.5-coder:1.5b

# Web Dashboard
python web_dashboard.py
# 访问 http://localhost:5000

# 持续挖掘
python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --ollama-model qwen2.5-coder:1.5b
```

---

## 📊 系统说明

### Generation One 架构：

**单服务架构** - 不需要分别启动前后端

- **主程序**: `alpha_generator_ollama.py`
  - 自动生成 Alpha 表达式
  - 自动测试和提交
  - 独立运行，无需 Dashboard

- **Web Dashboard**: `web_dashboard.py`（可选）
  - Flask 应用（前端 + 后端一体）
  - 实时监控界面
  - 访问 http://localhost:5000
  - **只是一个监控工具，不影响挖掘程序运行**

### 运行模式：

1. **单次挖掘** - 测试用，生成少量 Alpha
2. **Web Dashboard** - 仅启动监控界面（需要先启动挖掘程序）
3. **持续挖掘** - 24/7 自动运行，批量生成

---

## ✅ 当前状态

- ✅ Python 3.12.4/3.12.10
- ✅ Ollama 0.23.1
- ✅ 模型: qwen2.5-coder:1.5b, llama3:8b
- ✅ 凭证已配置
- ✅ 所有依赖已安装

---

## 📚 相关文档

- `README.md` - 项目说明
- `QUICKSTART.md` - 详细指南
- `GENERATION_COMPARISON.md` - Gen One vs Gen Two 对比
- `start_generation_two.bat` - 启动 Generation Two

---

## 🎯 快速测试

```bash
# 1. 启动挖掘
start.bat
选择 1

# 2. 查看结果
# 结果保存在 generation_one/naive-ollama/promising_alphas.json
```

---

**就这么简单！一个脚本搞定所有启动。**