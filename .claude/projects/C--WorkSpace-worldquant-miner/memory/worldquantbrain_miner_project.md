---
name: WorldQuant Miner项目分析
description: GitHub项目worldquant-miner的完整分析，包含架构设计、核心实现、技术栈和最佳实践
type: reference
originSessionId: b111effb-e7f8-4cf7-b661-79b985b64ac2
---
# WorldQuant Miner 项目深度分析

**GitHub**: https://github.com/zhutoutoutousan/worldquant-miner

## 项目概览

这是一个完整的 WorldQuant Brain Alpha 因子挖掘自动化系统，实现了从因子生成、测试、优化到提交的端到端流程。

## 核心架构

### 三代演进

#### Generation One: Naive-Ollama (推荐)
- **核心特点**: 本地 Ollama LLM + GPU 加速 + Web Dashboard
- **性能**: 3-5x 更快（相比 Kimi API）
- **自动化**: 24/7 持续运行
- **监控**: 实时 Web Dashboard

#### Generation Two: 高级挖掘系统
- **自优化**: 基于性能的自适应参数调优
- **遗传进化**: 遗传算法驱动的 Alpha 演化
- **持续挖掘**: 自动化 24/7 发现 + 错误修正
- **质量监控**: 性能跟踪和退化检测

#### Mini-Quant: 完整量化系统
- **数据收集**: 多源数据采集（Yahoo Finance, Alpha Vantage）
- **多区域回测**: USA, EMEA, CHN, IND, AMER
- **Alpha 管理**: SQLite 数据库管理
- **交易执行**: 实时信号评估 + 风险管理

## 核心组件实现

### 1. AlphaGenerator (alpha_generator_ollama.py)

**核心功能**:
```python
class AlphaGenerator:
    def __init__(self, credentials_path, ollama_url, max_concurrent):
        self.sess = requests.Session()
        self.ollama_url = ollama_url
        self.results = []
        self.retry_queue = RetryQueue(self)
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
```

**关键方法**:

1. **数据获取**:
```python
def get_data_fields(self):
    """从多个数据集随机采样数据字段"""
    datasets = ['fundamental6', 'fundamental2', 'analyst4', 'model16', 'model51', 'news12']
    # 随机采样 ~60% 的字段
```

2. **Alpha 生成**:
```python
def generate_alpha_ideas_with_ollama(self, data_fields, operators):
    """使用 Ollama 生成 Alpha 表达式"""
    prompt = f"""Generate 5 unique alpha factor expressions...
    Available Data Fields: {[field['id'] for field in data_fields]}
    Available Operators: {operators}
    """
    response = requests.post(f'{self.ollama_url}/api/generate', json={
        'model': 'deepseek-r1:8b',
        'prompt': prompt,
        'temperature': 0.3,
        'top_p': 0.9
    })
```

3. **批量测试**:
```python
def test_alpha_batch(self, alphas):
    """并发提交多个 Alpha 进行测试"""
    for i in range(0, len(alphas), max_concurrent):
        chunk = alphas[i:i + max_concurrent]
        futures = [self.executor.submit(self._test_alpha_impl, alpha) for alpha in chunk]
        # 监控进度直到完成
```

4. **重试机制**:
```python
class RetryQueue:
    """处理模拟限制和失败重试"""
    def _process_queue(self):
        while True:
            alpha, retry_count = self.queue.get()
            if retry_count >= self.max_retries:
                logging.error(f"Max retries exceeded for alpha: {alpha}")
                continue
            result = self.generator._test_alpha_impl(alpha)
            if "SIMULATION_LIMIT_EXCEEDED" in result:
                time.sleep(self.retry_delay)
                self.add(alpha, retry_count + 1)
```

### 2. AlphaOrchestrator (alpha_orchestrator.py)

**核心功能**: 编排整个工作流

**关键特性**:

1. **模型舰队管理**:
```python
class ModelFleetManager:
    """管理多个模型，自动降级处理 VRAM 问题"""
    model_fleet = [
        ModelInfo("deepseek-r1:8b", 5200, 1, "RTX A4000 optimized"),
        ModelInfo("deepseek-r1:7b", 4700, 2, "Reasoning model"),
        ModelInfo("deepseek-r1:1.5b", 1100, 3, "Lightweight"),
        ModelInfo("llama3:3b", 2048, 4, "Fallback"),
        ModelInfo("phi3:mini", 2200, 5, "Emergency fallback"),
    ]
```

2. **VRAM 监控**:
```python
def detect_vram_error(self, log_line):
    """检测 VRAM 恢复超时错误"""
    vram_error_indicators = [
        "gpu VRAM usage didn't recover within timeout",
        "CUDA out of memory",
        "GPU memory allocation failed"
    ]
    return any(indicator in log_line for indicator in vram_error_indicators)
```

3. **自动降级**:
```python
def downgrade_model(self):
    """降级到更小的模型"""
    old_model = self.get_current_model()
    self.current_model_index += 1
    new_model = self.get_current_model()
    logger.warning(f"Downgrading: {old_model.name} -> {new_model.name}")
    self.vram_error_count = 0
    self.save_state()
```

4. **持续挖掘**:
```python
def continuous_mining(self, mining_interval_hours=6):
    """持续挖掘模式"""
    # 启动 VRAM 监控
    self.start_vram_monitoring()
    
    # 启动重启监控（每 30 分钟）
    self.start_restart_monitoring()
    
    # 启动 Alpha 生成器（持续模式）
    self.start_alpha_generator_continuous(batch_size=3, sleep_time=30)
    
    # 启动表达式挖掘器（独立线程）
    miner_thread = threading.Thread(target=self.start_alpha_expression_miner_continuous)
    miner_thread.start()
    
    # 每天下午 2 点提交
    schedule.every().day.at("14:00").do(self.run_alpha_submitter)
```

### 3. Alpha Expression Miner

**功能**: 对有潜力的 Alpha 进行参数挖掘

**实现**:
```python
def mine_expression(expression):
    """挖掘表达式的参数变体"""
    # 解析表达式，找到参数
    parameters = parse_parameters(expression)
    
    # 生成变体
    for param in parameters:
        for value in param.range:
            variant = replace_param(expression, param, value)
            test_alpha(variant)
```

## 技术栈

### 后端
- **Python 3.8+**: 主应用语言
- **Flask**: Web Dashboard 框架
- **Requests**: HTTP 客户端
- **Schedule**: 任务调度
- **ThreadPoolExecutor**: 并发执行

### AI/ML
- **Ollama**: 本地 LLM 服务
- **glm-5.1 系列**: 推理模型（8B, 7B, 1.5B）
- **Llama 3**: 备用模型
- **Phi3**: 紧急备用

### 基础设施
- **Docker**: 容器化
- **Docker Compose**: 多服务编排
- **NVIDIA CUDA**: GPU 加速

### 数据存储
- **JSON**: 结果存储
- **SQLite**: Alpha 池管理（Mini-Quant）

## 工作流程

### 完整流程

```
自然语言描述
    ↓
Ollama LLM 生成表达式
    ↓
批量并发测试（WorldQuant API）
    ↓
监控进度 + 重试失败
    ↓
筛选有潜力的 Alpha（Fitness > 0.5）
    ↓
表达式挖掘（参数变体）
    ↓
每日提交（下午 2 点）
```

### 并发控制

```python
# 最大并发模拟数
max_concurrent_simulations = 3
simulation_semaphore = threading.Semaphore(max_concurrent_simulations)

# 批量提交
for i in range(0, len(alphas), max_concurrent):
    chunk = alphas[i:i + max_concurrent]
    futures = [executor.submit(test_alpha, alpha) for alpha in chunk]
    wait_for_completion(futures)
    sleep(10)  # 避免压垮 API
```

## 关键设计模式

### 1. 重试队列模式
- **问题**: WorldQuant API 有模拟限制
- **解决**: 失败的 Alpha 进入重试队列，延迟重试

### 2. 模型舰队模式
- **问题**: VRAM 不足导致 OOM
- **解决**: 维护多个模型，自动降级到更小的模型

### 3. 持续监控模式
- **问题**: 进程可能卡住
- **解决**: 每 30 分钟自动重启所有进程

### 4. 每日提交限制
- **问题**: WorldQuant 每天只能提交一次
- **解决**: 记录上次提交日期，确保每天只提交一次

## 性能优化

### 生成速度
- **之前**: ~10-15 秒/Alpha（Kimi API）
- **之后**: ~3-5 秒/Alpha（本地 Ollama + GPU）

### 并发优化
- **Pre-Consultant**: 最大 5 个并发模拟
- **Consultant**: 无限制（但需要自己控制）

### VRAM 优化
- **清理间隔**: 每 10 次操作清理一次 VRAM
- **降级阈值**: 3 次 VRAM 错误后降级模型
- **重启间隔**: 每 30 分钟重启防止内存泄漏

## 配置示例

### Docker Compose (GPU)
```yaml
version: '3.8'
services:
  ollama:
    image: ollama/ollama:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    ports:
      - "11434:11434"
  
  alpha-generator:
    build: .
    depends_on:
      - ollama
    environment:
      - OLLAMA_URL=http://ollama:11434
    volumes:
      - ./credential.txt:/app/credential.txt
      - ./results:/app/results
```

### 凭证文件
```json
["your.email@worldquant.com", "your_password"]
```

### 启动命令
```bash
# GPU 模式
docker-compose -f docker-compose.gpu.yml up -d

# 访问 Dashboard
http://localhost:5000
```

## 最佳实践

### 1. 模型选择
- **RTX A4000 (16GB)**: deepseek-r1:8b
- **RTX 3090 (24GB)**: deepseek-r1:8b 或更大
- **RTX 3080 (10GB)**: deepseek-r1:7b 或 llama3:3b

### 2. 并发控制
- **Pre-Consultant**: max_concurrent = 2-3
- **Consultant**: max_concurrent = 3-5

### 3. 批处理
- **batch_size**: 3-5 个 Alpha/批
- **sleep_time**: 30-60 秒间隔

### 4. 监控
- **VRAM 监控**: 每 30 秒检查一次
- **重启监控**: 每 30 分钟重启一次
- **进度监控**: 每 5 秒检查一次

## 与 QuantGPT 的对比

| 特性 | WorldQuant Miner | QuantGPT |
|------|------------------|----------|
| LLM | Ollama (本地) | DeepSeek (API) |
| GPU 支持 | ✅ 完整支持 | ❌ 无 |
| Web Dashboard | ✅ 实时监控 | ❌ 无 |
| 模型舰队 | ✅ 自动降级 | ❌ 单一模型 |
| VRAM 监控 | ✅ 自动处理 | ❌ 无 |
| 持续运行 | ✅ 24/7 | ⚠️ 需手动 |
| 表达式挖掘 | ✅ 自动化 | ✅ 自动化 |
| MCP 集成 | ❌ 无 | ✅ 8 个工具 |

## 可借鉴的设计

### 1. 模型舰队管理
- 维护多个模型，按优先级排序
- VRAM 错误时自动降级
- 状态持久化到文件

### 2. 重试队列
- 失败的任务进入队列
- 指数退避重试
- 最大重试次数限制

### 3. 持续监控
- VRAM 使用监控
- 进程健康检查
- 定期重启防止卡住

### 4. 并发控制
- 信号量限制并发数
- 批量提交避免压垮 API
- 等待间隔防止速率限制

## 扩展方向

### 1. 集成到 QTtrading
- 将模型舰队管理集成到后端
- 添加 Web Dashboard 到前端
- 实现持续挖掘模式

### 2. 增强功能
- 添加更多数据集支持
- 实现多区域回测
- 集成风险管理系统

### 3. 性能优化
- 优化 Ollama 推理速度
- 实现表达式缓存
- 添加结果去重

## 文章来源

**GitHub**: https://github.com/zhutoutoutousan/worldquant-miner

**Discord**: https://discord.gg/3B2TmHQw

**视频教程**:
- Web 版本: https://www.youtube.com/watch?v=xwr9atsulSA
- 本地 Ollama 版本: https://www.youtube.com/watch?v=EAeujBRrKiI
