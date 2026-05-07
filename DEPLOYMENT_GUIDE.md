# WorldQuant Miner 本地部署指南

## 环境要求

- ✅ Git: 2.48.1
- ✅ Python: 3.12.4
- ✅ GPU: NVIDIA RTX 3070 Ti (8GB VRAM)
- ❌ Ollama: 需要安装
- ❌ Docker: 可选（推荐非 Docker 方式）

## 部署步骤

### 步骤 1: 安装 Ollama

**下载地址**: https://ollama.ai/download

1. 下载 Windows 版本
2. 运行安装程序
3. 安装完成后，Ollama 会自动在后台运行（端口 11434）

**验证安装**:
```bash
ollama --version
```

### 步骤 2: 下载模型

根据你的 RTX 3070 Ti (8GB VRAM)，推荐以下模型：

**推荐模型（按优先级）**:

1. **glm-5.1-r1:1.5b** (最推荐，适合 8GB VRAM)
   ```bash
   ollama pull deepseek-r1:1.5b
   ```

2. **glm-5.1-r1:7b** (次推荐，可能需要优化)
   ```bash
   ollama pull deepseek-r1:7b
   ```

3. **llama3:3b** (备用模型)
   ```bash
   ollama pull llama3:3b
   ```

4. **phi3:mini** (紧急备用)
   ```bash
   ollama pull phi3:mini
   ```

**VRAM 使用参考**:
- glm-5.1-r1:1.5b: ~1.1GB
- glm-5.1-r1:7b: ~4.7GB
- llama3:3b: ~2GB
- phi3:mini: ~2.2GB

### 步骤 3: 配置项目

**进入项目目录**:
```bash
cd C:/WorkSpace/worldquant-miner/generation_one/naive-ollama
```

**创建凭证文件**:
```bash
# 复制示例文件
copy credential.example.txt credential.txt

# 编辑 credential.txt，填入你的 WorldQuant Brain 账号
# 格式: ["your.email@worldquant.com", "your_password"]
```

**安装 Python 依赖**:
```bash
pip install -r requirements.txt
```

### 步骤 4: 配置模型

**修改默认模型** (推荐使用 glm-5.1-r1:1.5b):

编辑 `alpha_generator_ollama.py`，找到以下行并修改:

```python
# 修改默认模型参数
parser.add_argument('--ollama-model', type=str, default='deepseek-r1:1.5b',
                   help='Ollama model to use (default: deepseek-r1:1.5b)')
```

**修改模型舰队** (编辑 `alpha_orchestrator.py`):

```python
# 调整模型舰队顺序，将 glm-5.1-r1:1.5b 放在第一位
model_fleet = [
    ModelInfo("deepseek-r1:1.5b", 1100, 1, "DeepSeek-R1 1.5B - Optimized for 8GB VRAM"),
    ModelInfo("llama3:3b", 2048, 2, "Llama 3.2 3B - Fallback"),
    ModelInfo("phi3:mini", 2200, 3, "Phi3 mini - Emergency fallback"),
]
```

### 步骤 5: 启动服务

**方式 1: 单次运行 Alpha 生成器**

```bash
python alpha_generator_ollama.py --credentials ./credential.txt --batch-size 3 --sleep-time 30 --ollama-model deepseek-r1:1.5b --max-concurrent 2
```

**方式 2: 持续运行编排器（推荐）**

```bash
python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --mining-interval 6 --batch-size 3 --max-concurrent 2 --ollama-model deepseek-r1:1.5b
```

**方式 3: 启动 Web Dashboard**

```bash
python web_dashboard.py
```

访问: http://localhost:5000

### 步骤 6: 监控和调优

**监控 VRAM 使用**:
```bash
nvidia-smi -l 1  # 每秒刷新一次
```

**查看日志**:
```bash
# Alpha 生成器日志
tail -f alpha_generator_ollama.log

# 编排器日志
tail -f alpha_orchestrator.log
```

**检查生成的 Alpha**:
```bash
# 查看有潜力的 Alpha
cat hopeful_alphas.json

# 查看挖掘结果
ls mining_results_*.json
```

## 参数调优建议

### 并发控制

根据你的 8GB VRAM:

```bash
--max-concurrent 2  # 最大并发模拟数（推荐 2）
--batch-size 3      # 每批生成 3 个 Alpha
--sleep-time 30     # 批次间隔 30 秒
```

### VRAM 优化

如果遇到 VRAM 不足:

1. **降低并发**: `--max-concurrent 1`
2. **使用更小模型**: `--ollama-model deepseek-r1:1.5b`
3. **增加清理间隔**: 在代码中修改 `vram_cleanup_interval = 5`

### 重启间隔

防止进程卡住:

```bash
--restart-interval 30  # 每 30 分钟重启一次
```

## 常见问题

### 1. Ollama 连接失败

**检查 Ollama 是否运行**:
```bash
curl http://localhost:11434/api/tags
```

**重启 Ollama**:
```bash
# Windows: 在任务管理器中重启 Ollama 服务
# 或重新运行 Ollama 安装程序
```

### 2. VRAM 不足

**症状**: `CUDA out of memory` 或 `gpu VRAM usage didn't recover`

**解决**:
- 使用 glm-5.1-r1:1.5b 模型
- 降低并发数到 1
- 关闭其他 GPU 应用（浏览器、游戏等）

### 3. WorldQuant API 认证失败

**检查凭证文件格式**:
```json
["your.email@worldquant.com", "your_password"]
```

**重新认证**:
- 确保 WorldQuant Brain 账号有效
- 检查网络连接

### 4. 模拟限制

**症状**: `SIMULATION_LIMIT_EXCEEDED`

**解决**:
- 系统会自动重试，等待即可
- Pre-Consultant: 最大 5 个并发
- Consultant: 可调整并发数

## 性能优化

### 1. 模型选择

**RTX 3070 Ti (8GB) 最佳配置**:
- 主模型: glm-5.1-r1:1.5b
- 并发: 2
- 批量: 3
- 间隔: 30 秒

### 2. 系统优化

**关闭不必要的 GPU 应用**:
- 关闭 Chrome 硬件加速
- 关闭游戏
- 关闭视频播放器

**增加系统内存**:
- 确保至少 16GB RAM
- 关闭不必要的后台程序

### 3. 网络优化

**使用稳定的网络**:
- WorldQuant API 需要稳定连接
- 避免在网络高峰期运行

## 下一步

### 1. 集成到 QTtrading

- 将模型舰队管理集成到后端
- 添加 Web Dashboard 到前端
- 实现持续挖掘模式

### 2. 增强功能

- 添加更多数据集支持
- 实现多区域回测
- 集成风险管理系统

### 3. 性能监控

- 添加 GPU 温度监控
- 实现自动降级策略
- 添加邮件通知

## 项目结构

```
worldquant-miner/
├── generation_one/
│   └── naive-ollama/          # 主要使用这个目录
│       ├── alpha_generator_ollama.py    # Alpha 生成器
│       ├── alpha_orchestrator.py        # 编排器
│       ├── alpha_expression_miner.py    # 表达式挖掘
│       ├── web_dashboard.py             # Web Dashboard
│       ├── credential.txt               # 凭证文件（需创建）
│       ├── hopeful_alphas.json          # 有潜力的 Alpha
│       └── results/                     # 结果目录
├── generation_two/           # 高级挖掘系统
└── mini-quant/               # 完整量化系统
```

## 资源

- **GitHub**: https://github.com/zhutoutoutousan/worldquant-miner
- **Discord**: https://discord.gg/3B2TmHQw
- **视频教程**: https://www.youtube.com/watch?v=EAeujBRrKiI
- **Ollama 官网**: https://ollama.ai

## 注意事项

1. **VRAM 监控**: 8GB VRAM 比较紧张，建议使用 glm-5.1-r1:1.5b
2. **并发控制**: 不要超过 2 个并发模拟
3. **凭证安全**: 不要将 credential.txt 上传到 GitHub
4. **系统重启**: 每 30 分钟自动重启防止卡住
5. **日志监控**: 定期检查日志文件

## 预期性能

**生成速度**:
- glm-5.1-r1:1.5b: ~3-5 秒/Alpha
- glm-5.1-r1:7b: ~5-8 秒/Alpha（如果 VRAM 允许）

**成功率**:
- 有潜力 Alpha: ~10-15%
- 可提交 Alpha: ~5-10%

**运行时间**:
- 持续模式: 24/7 自动运行
- 单次模式: 手动触发

---

**部署完成后，你将拥有一个完整的 WorldQuant Brain Alpha 因子挖掘自动化系统！**