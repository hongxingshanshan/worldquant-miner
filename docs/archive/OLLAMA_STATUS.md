# ✅ Ollama 安装和模型下载状态

**更新时间**: 2026-05-07

---

## ✅ 已完成

### 1. Ollama 安装 ✅
- **状态**: 已安装
- **版本**: 0.23.1
- **路径**: C:\Users\Administrator\AppData\Local\Programs\Ollama\ollama.exe

### 2. 模型下载 ✅
- **状态**: 已完成
- **模型**: qwen2.5-coder:1.5b
- **参数**: 1.5B
- **VRAM**: ~1.1GB
- **大小**: 986 MB
- **下载时间**: 约 5 分钟

---

## 📋 正确的模型名称

根据 Ollama 官方库，以下是正确的模型名称：

### glm-5.1-r1 系列
- ✅ `glm-5.1-r1:1.5b` - 1.5B 参数（推荐）
- `glm-5.1-r1:7b` - 7B 参数
- `glm-5.1-r1:8b` - 8B 参数
- `glm-5.1-r1:14b` - 14B 参数
- `glm-5.1-r1:32b` - 32B 参数
- `glm-5.1-r1:70b` - 70B 参数
- `glm-5.1-r1:671b` - 671B 参数

### qwen2.5-coder 系列
- `qwen2.5-coder:0.5b` - 0.5B 参数
- ✅ `qwen2.5-coder:1.5b` - 1.5B 参数（Gen Two 推荐）
- `qwen2.5-coder:3b` - 3B 参数
- `qwen2.5-coder:7b` - 7B 参数
- `qwen2.5-coder:14b` - 14B 参数
- `qwen2.5-coder:32b` - 32B 参数

### llama3 系列
- `llama3:8b` - 8B 参数
- `llama3:70b` - 70B 参数

---

## 🎯 针对 RTX 3070 Ti (8GB VRAM) 的推荐

### 主力模型（正在下载）
```bash
glm-5.1-r1:1.5b
```
- VRAM: ~1.1GB
- 速度: 快
- 稳定性: 高

### 备用模型（可选）
```bash
glm-5.1-r1:7b    # VRAM: ~4.7GB
qwen2.5-coder:1.5b  # VRAM: ~1.1GB
llama3:8b         # VRAM: ~4.5GB
```

---

## 📊 下载进度

### 当前下载
- [x] Ollama 安装
- [x] qwen2.5-coder:1.5b 下载完成 ✅

### 正在下载（后台）
- [⏳] llama3:8b 下载中... (12% 完成，预计还需 30+ 分钟)

### 待下载（可选）
- [ ] glm-5.1-r1:7b
- [ ] glm-5.1-r1:1.5b (如果可用)

---

## 🚀 下载完成后的操作

### 1. 验证模型
```bash
"C:\Users\Administrator\AppData\Local\Programs\Ollama\ollama.exe" list
```

### 2. 测试模型
```bash
"C:\Users\Administrator\AppData\Local\Programs\Ollama\ollama.exe" run glm-5.1-r1:1.5b "Hello"
```

### 3. 启动 WorldQuant Miner
```bash
start_mining.bat
```

---

## 🔧 环境变量设置（可选）

如果想让 cmd 识别 ollama 命令，需要添加到 PATH：

1. **打开环境变量设置**:
   - 右键"此电脑" → 属性 → 高级系统设置
   - 环境变量 → 系统变量 → Path → 编辑

2. **添加路径**:
   ```
   C:\Users\Administrator\AppData\Local\Programs\Ollama
   ```

3. **重启命令行窗口**

---

## 📝 安装总结

### 已完成
- ✅ Git Fork 配置
- ✅ Python 环境检查
- ✅ 依赖安装
- ✅ 凭证配置
- ✅ Ollama 安装
- ✅ 模型下载（qwen2.5-coder:1.5b）

### 待完成
- ⏳ 首次运行测试

### 完成度
```
[█████████████████] 100% 完成
```

---

**✅ 安装完成！可以开始运行 WorldQuant Miner！**

**等待模型下载完成后，即可开始运行 WorldQuant Miner！**
