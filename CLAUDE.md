# WorldQuant Miner 项目规则

## 项目概述
这是一个 WorldQuant Brain Alpha 挖掘项目，使用 Ollama 本地 LLM 生成和提交 Alpha 表达式。

## 技术栈
- Python 3.x
- Ollama (本地 LLM)
- WorldQuant Brain API

## 代码规范
- 使用 Python 类型提示
- 异步操作使用 asyncio
- 日志使用 logging 模块

## 文件结构
- `generation_one/` - 第一代实现
  - `naive-ollama/` - 基础版本
  - `consultant-naive-ollama/` - 自适应优化版本
  - `consultant-multi-arm-bandit-ollama/` - 多臂老虎机优化版本
  - `alpha-icu/` - Alpha 分析监控工具
- `generation_two/` - 第二代实现（带 PyQt5 GUI）
- 启动脚本使用 `.bat` 文件

## 注意事项
- 凭证文件 `credential.txt` 包含敏感信息，不要提交到版本控制
- Ollama 服务需要在本地运行 (http://localhost:11434)

---

## 项目特定规则

### 一、进程管理规则

#### 1.1 子进程清理
- 所有 `alpha_orchestrator.py` 文件必须包含子进程清理逻辑
- 使用 `signal.SIGINT` 和 `signal.SIGTERM` 处理退出信号
- 使用 `atexit` 注册清理函数
- 退出时必须终止所有子进程（generator、miner、monitor 等）

#### 1.2 进程状态检查
- 启动新进程前检查是否有旧进程运行
- 提供进程终止命令或脚本
- 记录进程 PID 以便追踪

### 二、配置文件规则

#### 2.1 配置加载
- 使用 `config.json` 存储模型和参数配置
- 配置变更后需要重启服务
- 不硬编码配置参数

#### 2.2 模型配置
- 默认模型从 `config.json` 的 `model` 字段读取
- 支持模型热切换时需要验证模型可用性
- 模型不可用时提供备选方案

### 三、API 交互规则

#### 3.1 WorldQuant Brain API
- 调用 API 前验证凭证有效性
- 处理 API 限流和错误响应
- 记录 API 调用结果

#### 3.2 Ollama API
- 检查 Ollama 服务状态 (http://localhost:11434)
- 模型调用失败时使用 requests fallback
- 监控 Ollama 内存使用

### 四、日志和监控规则

#### 4.1 日志规范
- 使用统一的日志格式
- 关键操作必须记录日志
- 错误日志包含堆栈信息

#### 4.2 Web Dashboard
- Dashboard 端口默认 5000
- 提供实时状态监控
- 显示 Alpha 生成和提交统计

### 五、错误处理规则

#### 5.1 语法错误
- Python 文件修改后检查语法
- 使用 `python -m py_compile` 验证
- Batch 文件确保 CRLF 行尾和 GBK 编码

#### 5.2 运行时错误
- 捕获并记录异常
- 提供错误恢复机制
- 不因单点错误中断整个流程

### 六、测试规则

#### 6.1 功能测试
- 新功能添加前测试现有功能
- 修改核心逻辑后运行回归测试
- 记录测试结果

#### 6.2 集成测试
- 测试完整流程（生成 → 验证 → 提交）
- 验证 API 连接和凭证
- 测试异常场景处理

### 七、版本控制规则

#### 7.1 提交规范
- 提交信息描述具体变更
- 不提交凭证文件和临时文件
- 大改动分多次提交

#### 7.2 分支管理
- 新功能在独立分支开发
- 合并前测试通过
- 保持主分支稳定

### 八、性能优化规则

#### 8.1 并发控制
- 使用 `max-concurrent` 参数控制并发数
- 遵守 API 限流规则
- 监控系统资源使用

#### 8.2 内存管理
- 监控 VRAM 使用情况
- 大模型调用时检查内存
- 提供内存不足时的降级方案