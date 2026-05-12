# 多进程日志死锁问题解决方案

## 问题分析

当前架构使用 `subprocess.Popen` 启动子进程，存在以下问题：

1. **logging 死锁**：Python 的 `logging` 模块使用全局锁，多进程共享日志文件会导致死锁
2. **进程间通信复杂**：需要使用 Queue、Pipe 等机制，增加复杂度
3. **资源消耗大**：每个子进程独立内存空间

## 解决方案

### 方案一：QueueHandler + QueueListener（已实现）

使用队列模式，所有日志发送到队列，单独的监听线程负责写入：

```
主进程/子进程 → QueueHandler → Queue → QueueListener → 文件/控制台
```

**优点**：
- 多进程/多线程安全
- 最小改动
- 兼容现有代码

**使用方法**：
```python
from logging_config import get_logger, setup_mp_logging

# 主程序开始时调用一次
setup_mp_logging('INFO')

# 获取 logger
logger = get_logger(__name__)
```

### 方案二：多线程替代子进程（推荐）

将 `subprocess.Popen` 改为 `threading.Thread`：

```python
# 之前（子进程）
self.generator_process = subprocess.Popen([sys.executable, 'alpha_generator_ollama.py', ...])

# 之后（多线程）
from threading import Thread
self.generator_thread = Thread(target=self._run_generator, daemon=True)
self.generator_thread.start()
```

**优点**：
- 无 logging 死锁
- 共享内存，通信简单
- 资源消耗低

**缺点**：
- 一个线程崩溃可能影响整个进程
- 需要改造代码

### 方案三：asyncio（长期方案）

使用异步编程：

```python
import asyncio

async def run_generator():
    # 异步生成 alpha
    pass

async def main():
    tasks = [
        asyncio.create_task(run_generator()),
        asyncio.create_task(run_submitter()),
    ]
    await asyncio.gather(*tasks)
```

**优点**：
- 高效、单线程无竞争
- 现代化架构

**缺点**：
- 需要大量改造

## 当前实现

已创建 `mp_logging.py`，使用 QueueHandler 模式：

- `mp_logging.py` - 多进程安全日志核心
- `logging_config.py` - 统一日志接口

## 迁移步骤

1. **立即可用**：所有模块已自动使用新的日志系统
2. **可选优化**：将子进程改为多线程（需要重构）

## 日志文件

日志统一输出到 `logs/app.log`，格式：
```
2024-01-15 10:30:45 - INFO - [PID:12345] alpha_generator:100 生成 Alpha 成功
```

## 注意事项

- 子进程启动前，确保已调用 `setup_mp_logging()`
- 子进程中的日志会通过队列发送到主进程处理
- 程序退出时会自动刷新日志队列
