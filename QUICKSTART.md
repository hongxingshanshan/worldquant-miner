# 🚀 快速开始指南

**更新时间**: 2026-05-07

---

## 📋 前置要求

- ✅ Windows 11 或 Windows 10
- ✅ Python 3.8+ (已安装: Python 3.12.4)
- ✅ NVIDIA GPU (推荐: RTX 3070 Ti 8GB VRAM)
- ✅ WorldQuant Brain 账号 ([注册地址](https://platform.worldquantbrain.com))

---

## ⚡ 一键安装（推荐）

### 方式 1: 自动安装（最简单）

双击运行 `install.bat`，脚本将自动完成所有安装步骤：

```
install.bat
```

这将自动：
1. ✅ 安装 Ollama 和下载模型
2. ✅ 配置 WorldQuant 凭证
3. ✅ 安装 Python 依赖
4. ✅ 运行首次测试

**预计时间**: 约 60 分钟

---

## 🔧 分步安装（可选）

如果你想逐步控制安装过程，可以按照以下步骤：

### 步骤 1: 安装 Ollama (30 分钟)

```bash
# 运行安装脚本
setup_ollama.bat
```

**或手动安装**:

1. 访问 https://ollama.ai/download
2. 下载 Windows 版本
3. 运行安装程序
4. 下载推荐模型:
   ```bash
   ollama pull glm-5.1-r1:1.5b
   ```

### 步骤 2: 配置凭证 (5 分钟)

```bash
# 运行配置脚本
setup_credentials.bat
```

**或手动配置**:

1. 进入项目目录:
   ```bash
   cd generation_one\naive-ollama
   ```

2. 创建凭证文件:
   ```bash
   echo '["your.email@worldquant.com", "your_password"]' > credential.txt
   ```

### 步骤 3: 安装依赖 (10 分钟)

```bash
# 运行安装脚本
setup_dependencies.bat
```

**或手动安装**:

```bash
cd generation_one\naive-ollama
pip install -r requirements.txt
```

### 步骤 4: 首次运行 (15 分钟)

```bash
# 运行启动脚本
start_mining.bat
```

选择运行模式：
1. 持续挖掘模式 (推荐)
2. 单次测试模式
3. Web Dashboard 模式

---

## 🎮 运行模式

### 模式 1: 持续挖掘模式 (推荐)

**特点**:
- 🤖 24/7 自动运行
- ⏰ 每 6 小时自动挖掘
- 📊 自动生成、测试、提交 Alpha
- 🔄 自动错误恢复

**启动**:
```bash
start_mining.bat
# 选择 1
```

**或直接运行**:
```bash
cd generation_one\naive-ollama
python alpha_orchestrator.py \
  --credentials ./credential.txt \
  --mode continuous \
  --mining-interval 6 \
  --batch-size 3 \
  --max-concurrent 2 \
  --ollama-model deepseek-r1:1.5b
```

### 模式 2: 单次测试模式

**特点**:
- 🧪 测试系统功能
- 📝 生成少量 Alpha
- ⚡ 快速验证

**启动**:
```bash
start_mining.bat
# 选择 2
```

**或直接运行**:
```bash
cd generation_one\naive-ollama
python alpha_generator_ollama.py \
  --credentials ./credential.txt \
  --batch-size 3 \
  --sleep-time 30 \
  --ollama-model deepseek-r1:1.5b \
  --max-concurrent 2
```

### 模式 3: Web Dashboard 模式

**特点**:
- 🖥️ 图形化界面
- 📊 实时监控
- 🎛️ 手动控制
- 📈 性能统计

**启动**:
```bash
start_mining.bat
# 选择 3
```

**或直接运行**:
```bash
cd generation_one\naive-ollama
python web_dashboard.py
```

**访问**: http://localhost:5000

---

## 📊 监控和管理

### GPU 监控

```bash
# 实时监控 GPU 使用
nvidia-smi -l 1

# 查看详细信息
nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv
```

### 日志查看

```bash
# 查看 Alpha 生成器日志
tail -f generation_one\naive-ollama\alpha_generator_ollama.log

# 查看编排器日志
tail -f generation_one\naive-ollama\alpha_orchestrator.log

# 查看所有日志
Get-Content generation_one\naive-ollama\*.log -Wait
```

### 结果查看

```bash
# 查看有潜力的 Alpha
cat generation_one\naive-ollama\hopeful_alphas.json

# 查看挖掘结果
ls generation_one\naive-ollama\mining_results_*.json

# 查看生成的 Alpha
ls generation_one\naive-ollama\results\
```

---

## ⚙️ 配置优化

### GPU 配置 (RTX 3070 Ti - 8GB VRAM)

**推荐配置**:
```bash
--ollama-model deepseek-r1:1.5b  # 模型
--max-concurrent 2                # 最大并发
--batch-size 3                    # 批量大小
--sleep-time 30                   # 间隔时间
```

**如果 VRAM 不足**:
```bash
--max-concurrent 1                # 降低并发
--ollama-model deepseek-r1:1.5b  # 使用更小模型
```

### 性能调优

**生成速度**:
- glm-5.1-r1:1.5b: ~3-5 秒/Alpha
- glm-5.1-r1:7b: ~5-8 秒/Alpha

**成功率**:
- 有潜力 Alpha: ~10-15%
- 可提交 Alpha: ~5-10%

---

## 🔧 故障排除

### 问题 1: Ollama 连接失败

**症状**: `Connection refused` 或 `Ollama not running`

**解决**:
```bash
# 检查 Ollama 是否运行
tasklist | findstr ollama

# 启动 Ollama
ollama serve

# 或重启 Ollama 服务
```

### 问题 2: VRAM 不足

**症状**: `CUDA out of memory`

**解决**:
1. 降低并发: `--max-concurrent 1`
2. 使用更小模型: `--ollama-model deepseek-r1:1.5b`
3. 关闭其他 GPU 应用

### 问题 3: 认证失败

**症状**: `Authentication failed: 401`

**解决**:
1. 检查凭证文件格式: `["email", "password"]`
2. 确认 WorldQuant 账号有效
3. 检查网络连接

### 问题 4: 模拟限制

**症状**: `SIMULATION_LIMIT_EXCEEDED`

**解决**:
- 系统会自动重试
- Pre-Consultant: 最大 5 个并发
- Consultant: 可调整并发数

---

## 📚 相关文档

- **README.md** - 项目主文档
- **DEPLOYMENT_GUIDE.md** - 详细部署指南
- **DEPLOYMENT_STATUS.md** - 部署状态报告
- **FORK_CONFIGURATION.md** - Fork 配置说明
- **generation_one/naive-ollama/README.md** - Naive-Ollama 详细文档

---

## 🆘 获取帮助

- **GitHub Issues**: https://github.com/hongxingshanshan/worldquant-miner/issues
- **Discord**: https://discord.gg/3B2TmHQw
- **视频教程**: https://www.youtube.com/watch?v=EAeujBRrKiI

---

## 🎉 下一步

安装完成后，你可以:

1. **优化配置**
   - 调整并发数和批量大小
   - 尝试不同的模型
   - 设置自动重启

2. **集成到 QTtrading**
   - 将模型舰队管理集成到后端
   - 添加 Web Dashboard 到前端
   - 实现持续挖掘模式

3. **增强功能**
   - 添加更多数据集支持
   - 实现多区域回测
   - 集成风险管理系统

---

**祝你挖掘愉快！** 🚀
