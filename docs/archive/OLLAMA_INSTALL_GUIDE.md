# Ollama 安装指南

## 当前状态
❌ Ollama 未安装

## 安装步骤

### 方法 1: 自动安装（推荐）

1. 访问 Ollama 官网: https://ollama.ai/download
2. 点击 "Download for Windows"
3. 运行下载的安装程序
4. 按照安装向导完成安装
5. 安装完成后，Ollama 会自动在后台运行

### 方法 2: 使用命令行

```powershell
# 使用 winget 安装（如果已安装）
winget install Ollama.Ollama

# 或使用 Chocolatey（如果已安装）
choco install ollama
```

## 验证安装

安装完成后，打开新的命令行窗口，运行：

```bash
ollama --version
```

应该看到类似输出：
```
ollama version is 0.x.x
```

## 下载推荐模型

安装完成后，下载适合你 GPU 的模型：

```bash
# 推荐：适合 8GB VRAM
ollama pull glm-5.1-r1:1.5b

# 备用选项
ollama pull glm-5.1-r1:7b    # 如果 VRAM 充足
ollama pull llama3:3b        # 备用模型
ollama pull phi3:mini        # 紧急备用
```

## 模型 VRAM 使用参考

- glm-5.1-r1:1.5b: ~1.1GB VRAM ✅ 推荐
- glm-5.1-r1:7b: ~4.7GB VRAM
- llama3:3b: ~2GB VRAM
- phi3:mini: ~2.2GB VRAM

## 安装完成后

运行以下命令继续安装：

```bash
setup_credentials.bat
```

## 故障排除

### 问题 1: 下载速度慢
- 使用代理或 VPN
- 尝试在非高峰时段下载

### 问题 2: 安装失败
- 以管理员身份运行安装程序
- 检查防病毒软件是否阻止
- 确保有足够的磁盘空间（至少 10GB）

### 问题 3: Ollama 服务未启动
- 手动启动：运行 `ollama serve`
- 检查防火墙设置
- 重启计算机

## 下载链接

- 官网: https://ollama.ai
- Windows 下载: https://ollama.ai/download
- 文档: https://github.com/ollama/ollama
- 模型库: https://ollama.ai/library

---

**安装完成后，请运行 `setup_credentials.bat` 继续配置。**
