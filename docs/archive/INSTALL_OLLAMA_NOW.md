# 🚨 Ollama 安装 - 必需步骤

## 当前状态
❌ **Ollama 未安装** - 这是运行 WorldQuant Miner 的必需组件

---

## 📥 立即安装 Ollama

### 方法 1: 自动下载（推荐）

我已经为你打开了 Ollama 下载页面：
- **下载地址**: https://ollama.ai/download
- **选择**: Windows 版本

### 方法 2: 直接下载链接

点击以下链接直接下载：
- **Windows 安装程序**: https://ollama.ai/download/Ollama-setup.exe

---

## 🔧 安装步骤（5 分钟）

### 步骤 1: 下载安装程序
✅ 已打开下载页面

### 步骤 2: 运行安装程序
1. 找到下载的 `Ollama-setup.exe` 文件
2. 双击运行
3. 如果出现用户账户控制提示，点击"是"
4. 按照安装向导完成安装

### 步骤 3: 验证安装
安装完成后，**打开新的命令行窗口**，运行：
```bash
ollama --version
```

应该看到：
```
ollama version is 0.x.x
```

---

## 🤖 下载推荐模型（10-20 分钟）

安装完成后，下载适合你 GPU 的模型：

### 推荐：glm-5.1-r1:1.5b（适合 8GB VRAM）
```bash
ollama pull glm-5.1-r1:1.5b
```

### 备用选项
```bash
# 如果 VRAM 充足（需要 ~4.7GB）
ollama pull glm-5.1-r1:7b

# 备用模型
ollama pull llama3:3b
ollama pull phi3:mini
```

---

## ✅ 安装验证清单

完成安装后，请验证：

### 1. 检查 Ollama 版本
```bash
ollama --version
```

### 2. 检查已下载的模型
```bash
ollama list
```

应该看到：
```
NAME                    ID              SIZE    MODIFIED
glm-5.1-r1:1.5b        xxxxx           1.1 GB  x minutes ago
```

### 3. 测试模型运行
```bash
ollama run glm-5.1-r1:1.5b "Hello, World!"
```

---

## 🎯 安装完成后的下一步

完成 Ollama 安装和模型下载后：

### 1. 验证凭证文件
✅ 已完成 - 凭证文件已配置

### 2. 运行首次测试
```bash
start_mining.bat
# 选择 2 - 单次测试模式
```

### 3. 启动持续挖掘
```bash
start_mining.bat
# 选择 1 - 持续挖掘模式
```

---

## ⚠️ 常见问题

### 问题 1: 下载速度慢
**解决方案**:
- 使用代理或 VPN
- 在非高峰时段下载（如深夜）
- 尝试多次下载

### 问题 2: 安装失败
**解决方案**:
- 以管理员身份运行安装程序
- 关闭防病毒软件临时
- 确保有足够磁盘空间（至少 10GB）

### 问题 3: 命令未找到
**解决方案**:
- 关闭并重新打开命令行窗口
- 检查环境变量 PATH
- 重启计算机

### 问题 4: 模型下载失败
**解决方案**:
- 检查网络连接
- 使用代理
- 尝试其他模型

---

## 📊 安装进度

```
[████████████░░░░] 75% → 90%

✅ Git Fork 配置
✅ Python 环境检查
✅ 依赖安装
✅ 凭证配置
⏳ Ollama 安装（进行中）
⏳ 首次运行测试（等待 Ollama）
```

---

## 🎉 快速安装命令

安装完成后，依次运行：

```bash
# 1. 验证安装
ollama --version

# 2. 下载模型
ollama pull glm-5.1-r1:1.5b

# 3. 验证模型
ollama list

# 4. 运行测试
start_mining.bat
```

---

**请现在安装 Ollama，安装完成后继续下一步！**
