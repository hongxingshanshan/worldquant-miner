# 🚀 Ollama 安装和模型下载完整指南

**更新时间**: 2026-05-07

---

## ⚠️ 当前状态

❌ **Ollama 未安装** - 需要先安装 Ollama 才能下载模型

---

## 📥 步骤 1: 安装 Ollama

### 方式 1: 官网下载（推荐）

1. **打开下载页面**: https://ollama.ai/download
2. **下载 Windows 版本**: 点击 "Download for Windows"
3. **运行安装程序**: 双击 `Ollama-setup.exe`
4. **完成安装**: 按照向导完成安装

### 方式 2: 直接下载链接

- **Windows**: https://ollama.ai/download/Ollama-setup.exe
- **macOS**: https://ollama.ai/download/Ollama-darwin.zip
- **Linux**: 
  ```bash
  curl -fsSL https://ollama.ai/install.sh | sh
  ```

### 方式 3: 使用包管理器

**Windows (winget)**:
```bash
winget install Ollama.Ollama
```

**Windows (Chocolatey)**:
```bash
choco install ollama
```

---

## ✅ 步骤 2: 验证安装

安装完成后，**打开新的命令行窗口**，运行：

```bash
ollama --version
```

**预期输出**:
```
ollama version is 0.x.x
```

---

## 🤖 步骤 3: 下载推荐模型

### 主力模型（必需）

#### glm-5.1-r1:1.5b ⭐⭐⭐⭐⭐（强烈推荐）

**特点**:
- ✅ VRAM: ~1.1GB
- ✅ 速度: 3-5秒/Alpha
- ✅ 适合 8GB VRAM
- ✅ 稳定可靠

**下载命令**:
```bash
ollama pull glm-5.1-r1:1.5b
```

**下载时间**: 约 5-10 分钟（取决于网络速度）

---

### 高质量模型（可选）

#### glm-5.1-r1:7b ⭐⭐⭐⭐

**特点**:
- ✅ VRAM: ~4.7GB
- ✅ 更强的推理能力
- ✅ 更高的成功率
- ⚠️ 速度稍慢

**下载命令**:
```bash
ollama pull glm-5.1-r1:7b
```

**下载时间**: 约 15-30 分钟

---

### Generation Two 专用（可选）

#### qwen2.5-coder:1.5b ⭐⭐⭐⭐

**特点**:
- ✅ VRAM: ~1.1GB
- ✅ 专为代码生成优化
- ✅ 适合 Alpha 表达式
- ✅ AST 验证支持

**下载命令**:
```bash
ollama pull qwen2.5-coder:1.5b
```

**下载时间**: 约 5-10 分钟

---

### 备用模型（可选）

#### llama3:3b
```bash
ollama pull llama3:3b
```

#### phi3:mini
```bash
ollama pull phi3:mini
```

---

## 📊 步骤 4: 验证模型下载

### 查看已下载模型

```bash
ollama list
```

**预期输出**:
```
NAME                    ID              SIZE    MODIFIED
glm-5.1-r1:1.5b        xxxxx           1.1 GB  x minutes ago
```

### 测试模型运行

```bash
ollama run glm-5.1-r1:1.5b "Hello, World!"
```

**预期输出**:
```
Hello! How can I assist you today?
```

---

## 🎯 步骤 5: 配置 WorldQuant Miner

### Generation One 配置

模型已自动配置在启动脚本中：
- `start_mining.bat` 使用 `glm-5.1-r1:1.5b`

### Generation Two 配置

如果使用 Generation Two，需要修改配置：

```python
# generation_two/gui/run_gui.py 或配置文件中
model_name = "qwen2.5-coder:1.5b"
```

---

## 🔧 高级配置

### 模型参数优化

创建模型配置文件 `Modelfile`:

```bash
# 创建自定义模型
ollama create my-alpha-generator -f Modelfile
```

**Modelfile 内容**:
```
FROM glm-5.1-r1:1.5b

# 设置参数
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 2048
PARAMETER num_predict 512

# 设置系统提示
SYSTEM You are an expert quantitative analyst specializing in alpha factor generation for WorldQuant Brain.
```

### 使用自定义模型

```bash
ollama run my-alpha-generator "Generate alpha factor..."
```

---

## 🚨 故障排除

### 问题 1: 下载速度慢

**解决方案**:
1. 使用代理或 VPN
2. 在非高峰时段下载（如深夜）
3. 使用镜像源（如果有）

### 问题 2: 下载失败

**解决方案**:
```bash
# 清理缓存
ollama rm glm-5.1-r1:1.5b

# 重新下载
ollama pull glm-5.1-r1:1.5b
```

### 问题 3: VRAM 不足

**解决方案**:
1. 使用更小的模型
2. 关闭其他 GPU 应用
3. 降低并发数

### 问题 4: 模型无法运行

**解决方案**:
```bash
# 检查 Ollama 服务状态
ollama serve

# 查看日志
ollama logs
```

---

## 📋 完整下载清单

### 必需模型（优先级最高）

```bash
# 1. 主力模型
ollama pull glm-5.1-r1:1.5b
```

### 推荐模型（优先级高）

```bash
# 2. 高质量模型
ollama pull glm-5.1-r1:7b

# 3. Generation Two 专用
ollama pull qwen2.5-coder:1.5b
```

### 备用模型（优先级中）

```bash
# 4. 通用备用
ollama pull llama3:3b

# 5. 紧急备用
ollama pull phi3:mini
```

---

## 🎯 快速启动命令

### 一键下载所有推荐模型

创建 `download_all_models.bat`:

```batch
@echo off
echo 正在下载所有推荐模型...
echo.

echo [1/5] 下载 glm-5.1-r1:1.5b (主力模型)
ollama pull glm-5.1-r1:1.5b

echo.
echo [2/5] 下载 glm-5.1-r1:7b (高质量模型)
ollama pull glm-5.1-r1:7b

echo.
echo [3/5] 下载 qwen2.5-coder:1.5b (Gen Two 专用)
ollama pull qwen2.5-coder:1.5b

echo.
echo [4/5] 下载 llama3:3b (备用)
ollama pull llama3:3b

echo.
echo [5/5] 下载 phi3:mini (紧急备用)
ollama pull phi3:mini

echo.
echo ========================================
echo 所有模型下载完成！
echo ========================================
echo.
echo 已安装的模型:
ollama list

pause
```

---

## 📊 下载进度跟踪

### 查看下载进度

Ollama 会显示下载进度条：
```
pulling manifest
pulling xxxxxx... 100% ▕████████████████▏ 1.1 GB/1.1 GB
verifying sha256 digest
writing manifest
success
```

### 检查下载状态

```bash
# 查看正在下载的模型
ollama list

# 查看模型详情
ollama show glm-5.1-r1:1.5b
```

---

## 🎉 完成后的下一步

### 1. 验证安装

```bash
ollama --version
ollama list
ollama run glm-5.1-r1:1.5b "Test"
```

### 2. 启动 WorldQuant Miner

```bash
# Generation One
start_mining.bat

# Generation Two
start_generation_two.bat
```

### 3. 监控运行

```bash
# GPU 监控
nvidia-smi -l 1

# 查看日志
tail -f alpha_generator_ollama.log
```

---

## 📚 相关资源

- **Ollama 官网**: https://ollama.ai
- **模型库**: https://ollama.com/search
- **文档**: https://github.com/ollama/ollama
- **模型推荐**: `OLLAMA_MODELS_GUIDE.md`

---

## ✅ 检查清单

安装完成后，确认以下项目：

- [ ] Ollama 已安装并运行
- [ ] `ollama --version` 显示版本号
- [ ] `glm-5.1-r1:1.5b` 模型已下载
- [ ] `ollama list` 显示已安装模型
- [ ] 测试运行成功
- [ ] WorldQuant Miner 凭证已配置
- [ ] Python 依赖已安装

---

**现在请按照步骤安装 Ollama，然后下载模型！**
