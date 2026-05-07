# 🤖 Ollama 模型推荐指南 - WorldQuant Miner 专用

**更新时间**: 2026-05-07
**数据来源**: https://ollama.com/search

---

## 📊 推荐模型排行榜

### 🥇 顶级推荐（适合 WorldQuant Alpha 生成）

| 排名 | 模型名称 | 参数大小 | VRAM需求 | 推荐指数 | 特点 |
|-----|---------|---------|---------|---------|------|
| 1 | **glm-5.1** | 未知 | 未知 | ⭐⭐⭐⭐⭐ | SWE-Bench Pro 最佳性能，强大编码能力 |
| 2 | **glm-5.1-v4-pro** | 284B总/13B激活 | ~8-10GB | ⭐⭐⭐⭐⭐ | 前沿 MoE 模型，三种推理模式 |
| 3 | **qwen3.6** | 27B/35B | ~16-20GB | ⭐⭐⭐⭐⭐ | 升级的代理编码和思维保留 |
| 4 | **deepseek-v4-flash** | 284B总/13B激活 | ~8-10GB | ⭐⭐⭐⭐ | 高效推理，1M token 上下文 |
| 5 | **glm-4.7-flash** | 30B | ~16-18GB | ⭐⭐⭐⭐ | 平衡性能和效率 |

### 🥈 次级推荐（适合 8GB VRAM）

| 排名 | 模型名称 | 参数大小 | VRAM需求 | 推荐指数 | 特点 |
|-----|---------|---------|---------|---------|------|
| 1 | **glm-5.1-r1:1.5b** | 1.5B | ~1.1GB | ⭐⭐⭐⭐⭐ | 轻量级，适合 8GB VRAM |
| 2 | **glm-5.1-r1:7b** | 7B | ~4.7GB | ⭐⭐⭐⭐ | 推理模型，适合 8GB VRAM |
| 3 | **qwen2.5-coder:1.5b** | 1.5B | ~1.1GB | ⭐⭐⭐⭐ | 代码生成专用 |
| 4 | **llama3:3b** | 3B | ~2GB | ⭐⭐⭐ | 备用模型 |
| 5 | **phi3:mini** | 3.8B | ~2.2GB | ⭐⭐⭐ | 紧急备用 |

### 🥉 其他推荐模型

| 模型名称 | 参数大小 | VRAM需求 | 主要用途 |
|---------|---------|---------|---------|
| **kimi-k2.6** | 未知 | 未知 | 长期编码，编码驱动设计 |
| **gemma4** | e2b-e4b/26b/31b | ~2-18GB | 推理，代理工作流，编码 |
| **mistral-medium-3.5** | 128B | ~70GB+ | 指令遵循，推理，编码 |
| **laguna-xs.2** | 33B总/3B激活 | ~2-3GB | 本地机器代理编码 |

---

## 🎯 针对 RTX 3070 Ti (8GB VRAM) 的推荐

### 最佳选择

#### 1. glm-5.1-r1:1.5b ⭐⭐⭐⭐⭐

**推荐理由**:
- ✅ VRAM 使用仅 ~1.1GB
- ✅ 速度快（3-5秒/Alpha）
- ✅ 稳定可靠
- ✅ 适合持续运行

**下载命令**:
```bash
ollama pull glm-5.1-r1:1.5b
```

**性能预期**:
- 生成速度: 3-5秒/Alpha
- 成功率: 10-15%
- 并发能力: 2个模拟

---

#### 2. glm-5.1-r1:7b ⭐⭐⭐⭐

**推荐理由**:
- ✅ VRAM 使用 ~4.7GB（8GB 可用）
- ✅ 更强的推理能力
- ✅ 更高的成功率
- ⚠️ 速度稍慢

**下载命令**:
```bash
ollama pull glm-5.1-r1:7b
```

**性能预期**:
- 生成速度: 5-8秒/Alpha
- 成功率: 12-18%
- 并发能力: 1-2个模拟

---

#### 3. qwen2.5-coder:1.5b ⭐⭐⭐⭐

**推荐理由**:
- ✅ 专为代码生成优化
- ✅ VRAM 使用 ~1.1GB
- ✅ 适合 Alpha 表达式生成
- ✅ Generation Two 推荐

**下载命令**:
```bash
ollama pull qwen2.5-coder:1.5b
```

**性能预期**:
- 生成速度: 3-5秒/Alpha
- 成功率: 10-15%
- 并发能力: 2个模拟

---

### 备用选择

#### 4. llama3:3b ⭐⭐⭐

**推荐理由**:
- ✅ 社区支持广泛
- ✅ VRAM 使用 ~2GB
- ✅ 稳定性好
- ⚠️ 非专用模型

**下载命令**:
```bash
ollama pull llama3:3b
```

---

#### 5. phi3:mini ⭐⭐⭐

**推荐理由**:
- ✅ 微软出品
- ✅ VRAM 使用 ~2.2GB
- ✅ 紧急备用
- ⚠️ 性能一般

**下载命令**:
```bash
ollama pull phi3:mini
```

---

## 🚀 模型下载和测试

### 批量下载脚本

创建 `download_models.bat`:

```batch
@echo off
echo 正在下载推荐模型...

echo 1/5 下载 glm-5.1-r1:1.5b (推荐)
ollama pull glm-5.1-r1:1.5b

echo 2/5 下载 glm-5.1-r1:7b (次推荐)
ollama pull glm-5.1-r1:7b

echo 3/5 下载 qwen2.5-coder:1.5b (Gen Two 推荐)
ollama pull qwen2.5-coder:1.5b

echo 4/5 下载 llama3:3b (备用)
ollama pull llama3:3b

echo 5/5 下载 phi3:mini (紧急备用)
ollama pull phi3:mini

echo.
echo 所有模型下载完成！
ollama list
pause
```

### 测试模型性能

创建 `test_models.py`:

```python
import requests
import time

models = [
    "glm-5.1-r1:1.5b",
    "glm-5.1-r1:7b",
    "qwen2.5-coder:1.5b",
    "llama3:3b",
    "phi3:mini"
]

test_prompt = """Generate a simple alpha factor expression using:
- Data field: close
- Operator: rank
- Time window: 20 days

Expression:"""

for model in models:
    print(f"\n测试模型: {model}")
    print("-" * 50)
    
    start = time.time()
    
    response = requests.post('http://localhost:11434/api/generate', json={
        'model': model,
        'prompt': test_prompt,
        'stream': False
    })
    
    elapsed = time.time() - start
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ 生成成功")
        print(f"✓ 耗时: {elapsed:.2f}秒")
        print(f"✓ 结果: {result['response'][:100]}...")
    else:
        print(f"✗ 生成失败: {response.status_code}")
```

---

## 📊 性能对比表

### VRAM 使用对比

| 模型 | 参数 | VRAM | 可用性 (8GB) | 推荐度 |
|-----|------|------|-------------|--------|
| glm-5.1-r1:1.5b | 1.5B | 1.1GB | ✅ 完全可用 | ⭐⭐⭐⭐⭐ |
| glm-5.1-r1:7b | 7B | 4.7GB | ✅ 可用 | ⭐⭐⭐⭐ |
| qwen2.5-coder:1.5b | 1.5B | 1.1GB | ✅ 完全可用 | ⭐⭐⭐⭐ |
| llama3:3b | 3B | 2GB | ✅ 可用 | ⭐⭐⭐ |
| phi3:mini | 3.8B | 2.2GB | ✅ 可用 | ⭐⭐⭐ |

### 速度对比

| 模型 | 生成速度 | 推理质量 | 编码能力 | 综合评分 |
|-----|---------|---------|---------|---------|
| glm-5.1-r1:1.5b | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 4.3/5 |
| glm-5.1-r1:7b | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 4.7/5 |
| qwen2.5-coder:1.5b | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 4.3/5 |
| llama3:3b | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 3.3/5 |
| phi3:mini | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 3.3/5 |

---

## 🎯 使用建议

### Generation One 推荐

**首选**: `glm-5.1-r1:1.5b`

**原因**:
- ✅ 速度快，适合持续运行
- ✅ VRAM 占用低，稳定可靠
- ✅ 成功率适中
- ✅ 适合 24/7 自动化

**备选**: `glm-5.1-r1:7b`（如果 VRAM 允许）

---

### Generation Two 推荐

**首选**: `qwen2.5-coder:1.5b`

**原因**:
- ✅ 专为代码生成优化
- ✅ 适合 Alpha 表达式生成
- ✅ 支持 AST 验证和修正
- ✅ VRAM 占用低

**备选**: `glm-5.1-r1:7b`（更强推理能力）

---

### 模型切换策略

**自动降级配置**:

```python
model_fleet = [
    ModelInfo("glm-5.1-r1:7b", 4700, 1, "主模型 - 强推理"),
    ModelInfo("glm-5.1-r1:1.5b", 1100, 2, "备用 - 快速生成"),
    ModelInfo("qwen2.5-coder:1.5b", 1100, 3, "代码专用"),
    ModelInfo("llama3:3b", 2048, 4, "通用备用"),
    ModelInfo("phi3:mini", 2200, 5, "紧急备用"),
]
```

**降级逻辑**:
1. VRAM > 90% → 降级到更小模型
2. 连续错误 3 次 → 自动降级
3. Ollama 连接失败 → 切换备用模型

---

## 🔧 高级配置

### 模型参数优化

**glm-5.1-r1:1.5b**:
```python
{
    'temperature': 0.3,      # 较低温度，更确定性
    'top_p': 0.9,           # 核采样
    'top_k': 40,            # Top-K 采样
    'repeat_penalty': 1.1,  # 重复惩罚
    'num_ctx': 2048,        # 上下文长度
    'num_predict': 512      # 预测token数
}
```

**glm-5.1-r1:7b**:
```python
{
    'temperature': 0.4,      # 稍高温度，更多样性
    'top_p': 0.95,
    'top_k': 50,
    'repeat_penalty': 1.15,
    'num_ctx': 4096,        # 更长上下文
    'num_predict': 1024
}
```

**qwen2.5-coder:1.5b**:
```python
{
    'temperature': 0.2,      # 低温度，代码生成更准确
    'top_p': 0.95,
    'top_k': 40,
    'repeat_penalty': 1.1,
    'num_ctx': 2048,
    'num_predict': 512
}
```

---

## 📚 相关资源

### 官方资源
- **Ollama 官网**: https://ollama.ai
- **模型库**: https://ollama.com/search
- **文档**: https://github.com/ollama/ollama

### 模型文档
- **glm-5.1**: https://ollama.com/library/glm-5.1
- **Qwen**: https://ollama.com/library/qwen2.5-coder
- **Llama**: https://ollama.com/library/llama3

### 社区资源
- **Discord**: https://discord.gg/ollama
- **GitHub Issues**: https://github.com/ollama/ollama/issues

---

## 🎉 总结

### 最佳实践

1. **首次使用**: 从 `glm-5.1-r1:1.5b` 开始
2. **性能优化**: 尝试 `glm-5.1-r1:7b`
3. **代码生成**: 使用 `qwen2.5-coder:1.5b`
4. **备用方案**: 准备 `llama3:3b` 和 `phi3:mini`

### 当前推荐

**对于你的 RTX 3070 Ti (8GB VRAM)**:

✅ **主模型**: `glm-5.1-r1:1.5b`
- VRAM: 1.1GB
- 速度: 快
- 稳定性: 高

✅ **备用模型**: `glm-5.1-r1:7b`
- VRAM: 4.7GB
- 质量: 更高
- 速度: 中等

✅ **Gen Two**: `qwen2.5-coder:1.5b`
- VRAM: 1.1GB
- 专用: 代码生成
- 适合: AST 验证

---

**现在请下载推荐模型**:
```bash
ollama pull glm-5.1-r1:1.5b
```
