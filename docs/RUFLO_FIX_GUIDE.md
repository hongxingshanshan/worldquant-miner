# 使用 Ruflo 处理代码审查问题指南

## 概述

本文档说明如何使用 Ruflo 的各种能力来自动化处理 `CODE_REVIEW_REPORT.md` 中发现的问题。

---

## 一、Ruflo 能力映射

| 问题类型 | Ruflo 能力 | 工具/Agent |
|---------|-----------|------------|
| 安全漏洞 | Security & Compliance | `aidefence_scan`, `security-auditor` |
| 性能问题 | Performance & Profiling | `performance_*`, `hooks_route` |
| 代码质量 | Code Analysis | `analyze_diff`, `code-reviewer` |
| 架构重构 | Swarm Orchestration | `swarm_init`, `agent_spawn` |
| 知识持久化 | Memory & Knowledge | `memory_store`, `agentdb_*` |
| 自动化修复 | Hooks & Automation | `hooks_pre-edit`, `hooks_post-edit` |

---

## 二、按优先级处理方案

### P0 - 立即修复（手动 + Ruflo 辅助）

#### 问题 1: 凭证泄露

**手动操作**:
```bash
# 1. 删除敏感文件
rm .claude/projects/C--WorkSpace-worldquant-miner/memory/worldquantbrain_credentials.md

# 2. 检查 git 历史
git log --all --full-history -- "credential.txt"
git log --all --full-history -- "**/credential.txt"
```

**Ruflo 辅助**:
```bash
# 使用 AIDefence 扫描敏感信息
ruflo aidefence_scan --input "扫描项目中的敏感信息"

# 使用 security-auditor agent
ruflo agent_spawn --agentType security-auditor --task "扫描项目中的凭证泄露风险"
```

#### 问题 2: 网络请求无 timeout

**使用 Ruflo 自动修复**:
```bash
# 1. 启动 coder agent
ruflo agent_spawn --agentType coder --task "为所有 requests.get/post 调用添加 timeout=300 参数"

# 2. 或者使用 hooks_pre-edit
ruflo hooks_pre-edit --filePath "alpha_orchestrator.py" --operation "update"
```

---

### P1 - 本周修复（Ruflo Swarm 协作）

#### 问题 3: 内存泄漏

**启动修复 Swarm**:
```bash
# 初始化 swarm
ruflo swarm_init --topology hierarchical --maxAgents 3 --strategy specialized

# 启动 coder agent
ruflo agent_spawn --agentType coder --task "为 AlphaGenerator 添加结果清理机制，限制最大结果数为 1000"

# 启动 reviewer agent 验证
ruflo agent_spawn --agentType reviewer --task "验证内存泄漏修复是否正确"
```

#### 问题 4: 知识库缓存

**使用 Ruflo Intelligence**:
```bash
# 存储修复模式到 AgentDB
ruflo agentdb_pattern-store --pattern "使用 lru_cache 装饰器缓存知识库加载结果" --type "optimization"

# 启动 coder agent
ruflo agent_spawn --agentType coder --task "为 load_knowledge_base 函数添加 lru_cache 缓存"
```

#### 问题 5: API 限流

**使用 Ruflo Workflow**:
```bash
# 创建修复工作流
ruflo workflow_create --name "api-rate-limiter" \
  --steps '[{"name": "create_rate_limiter", "type": "task"}, {"name": "integrate_rate_limiter", "type": "task"}, {"name": "test_rate_limiter", "type": "task"}]'

# 执行工作流
ruflo workflow_execute --workflowId "api-rate-limiter"
```

---

### P2 - 下两周修复（Ruflo SPARC 方法论）

#### 问题 6: 文件拆分

**使用 SPARC 方法论**:
```bash
# 启动 SPARC 流程
ruflo agent_spawn --agentType sparc-architect --task "设计 alpha_generator_ollama.py 的拆分方案"

# Specification 阶段
ruflo agent_spawn --agentType sparc-spec --task "定义拆分后的模块接口"

# Architecture 阶段
ruflo agent_spawn --agentType sparc-architect --task "设计模块间的依赖关系"

# Refinement 阶段
ruflo agent_spawn --agentType coder --task "实现拆分后的模块"

# Completion 阶段
ruflo agent_spawn --agentType reviewer --task "验证拆分后的代码质量"
```

---

## 三、完整修复工作流

### 方案 A: 单 Agent 逐个修复

```bash
# 1. 读取审查报告
REPORT="docs/CODE_REVIEW_REPORT.md"

# 2. 按优先级启动修复
# P0
ruflo agent_spawn --agentType coder --task "修复 P0 问题：添加 timeout 参数"

# P1
ruflo agent_spawn --agentType coder --task "修复 P1 问题：内存泄漏、缓存、限流"

# P2
ruflo agent_spawn --agentType coder --task "修复 P2 问题：拆分过长文件"
```

### 方案 B: Swarm 并行修复

```bash
# 1. 初始化修复 swarm
ruflo swarm_init --topology hierarchical --maxAgents 5 --strategy specialized

# 2. 并行启动多个 agent
ruflo agent_spawn --agentType coder --task "修复安全问题" --domain security &
ruflo agent_spawn --agentType coder --task "修复性能问题" --domain performance &
ruflo agent_spawn --agentType coder --task "修复代码质量问题" --domain quality &
ruflo agent_spawn --agentType reviewer --task "验证所有修复" --domain review &

# 3. 等待完成并合并结果
ruflo swarm_status --swarmId <swarm_id>

# 4. 关闭 swarm
ruflo swarm_shutdown --swarmId <swarm_id>
```

### 方案 C: Autopilot 自动修复

```bash
# 1. 启用 autopilot
ruflo autopilot_enable

# 2. 配置 autopilot
ruflo autopilot_config --maxIterations 100 --timeoutMinutes 120

# 3. 创建修复任务列表
ruflo task_create --type bugfix --description "修复 P0 安全问题"
ruflo task_create --type bugfix --description "修复 P1 性能问题"
ruflo task_create --type refactor --description "拆分过长文件"

# 4. Autopilot 会自动分配 agent 处理任务

# 5. 检查进度
ruflo autopilot_progress

# 6. 完成后关闭
ruflo autopilot_disable
```

---

## 四、具体执行脚本

### 4.1 安全问题修复脚本

```bash
#!/bin/bash
# scripts/fix_security_issues.sh

echo "=== 开始修复安全问题 ==="

# 1. 扫描敏感信息
echo "扫描敏感信息..."
ruflo aidefence_scan --input "$(cat docs/CODE_REVIEW_REPORT.md | grep -A 20 '安全问题')"

# 2. 启动安全审计 agent
echo "启动安全审计 agent..."
AGENT_ID=$(ruflo agent_spawn --agentType security-auditor --task "审计并修复 WorldQuant Miner 项目中的安全问题" --format json | jq -r '.agentId')

# 3. 等待完成
echo "等待安全审计完成..."
sleep 60

# 4. 检查结果
ruflo agent_status --agentId $AGENT_ID

echo "=== 安全问题修复完成 ==="
```

### 4.2 性能问题修复脚本

```bash
#!/bin/bash
# scripts/fix_performance_issues.sh

echo "=== 开始修复性能问题 ==="

# 1. 初始化性能修复 swarm
echo "初始化性能修复 swarm..."
SWARM_ID=$(ruflo swarm_init --topology hierarchical --maxAgents 4 --strategy specialized --format json | jq -r '.swarmId')

# 2. 启动多个 coder agent
echo "启动 coder agents..."
ruflo agent_spawn --agentType coder --task "修复内存泄漏：为 AlphaGenerator 添加结果清理机制"
ruflo agent_spawn --agentType coder --task "添加知识库缓存：使用 lru_cache 装饰器"
ruflo agent_spawn --agentType coder --task "实现 API 限流器：令牌桶算法"
ruflo agent_spawn --agentType coder --task "优化去重算法：使用哈希索引"

# 3. 监控进度
echo "监控修复进度..."
while true; do
  STATUS=$(ruflo swarm_status --swarmId $SWARM_ID --format json)
  echo "$STATUS"
  
  if echo "$STATUS" | jq -e '.status == "completed"' > /dev/null; then
    break
  fi
  
  sleep 30
done

# 4. 关闭 swarm
ruflo swarm_shutdown --swarmId $SWARM_ID

echo "=== 性能问题修复完成 ==="
```

### 4.3 代码质量修复脚本

```bash
#!/bin/bash
# scripts/fix_code_quality.sh

echo "=== 开始修复代码质量问题 ==="

# 1. 使用 SPARC 方法论拆分文件
echo "启动 SPARC 流程..."

# Specification
ruflo agent_spawn --agentType sparc-spec --task "定义 alpha_generator_ollama.py 的拆分规范"

# Architecture
ruflo agent_spawn --agentType sparc-architect --task "设计拆分后的模块架构"

# Refinement
ruflo agent_spawn --agentType coder --task "实现拆分后的模块"

# Completion
ruflo agent_spawn --agentType reviewer --task "验证拆分后的代码质量"

echo "=== 代码质量问题修复完成 ==="
```

---

## 五、使用 Ruflo Hooks 自动化

### 5.1 配置 pre-edit hook

在 `.claude/settings.json` 中添加：

```json
{
  "hooks": {
    "PreEdit": [
      {
        "command": "ruflo hooks_pre-edit --filePath ${file_path} --operation ${operation}"
      }
    ]
  }
}
```

### 5.2 配置 post-edit hook

```json
{
  "hooks": {
    "PostEdit": [
      {
        "command": "ruflo hooks_post-edit --filePath ${file_path} --success ${success}"
      }
    ]
  }
}
```

### 5.3 配置后台 worker

```bash
# 启动代码质量监控 worker
ruflo hooks_worker-dispatch --trigger optimize --context "generation_one/naive-ollama"

# 启动测试覆盖率 worker
ruflo hooks_worker-dispatch --trigger testgaps --context "tests/"
```

---

## 六、知识持久化

### 6.1 存储修复模式

```bash
# 存储成功的修复模式
ruflo agentdb_pattern-store \
  --pattern "为 requests 调用添加 timeout 参数防止无限阻塞" \
  --type "security-fix" \
  --confidence 0.95

ruflo agentdb_pattern-store \
  --pattern "使用 lru_cache 缓存知识库加载结果" \
  --type "performance-fix" \
  --confidence 0.9

ruflo agentdb_pattern-store \
  --pattern "使用令牌桶算法实现 API 限流" \
  --type "performance-fix" \
  --confidence 0.9
```

### 6.2 存储修复决策

```bash
# 存储修复决策到 AgentDB
ruflo memory_store \
  --key "fix-decision-timeout" \
  --value "为所有 API 调用添加 timeout=30 参数" \
  --namespace "code-review-fixes"

ruflo memory_store \
  --key "fix-decision-memory" \
  --value "限制 results 列表最大长度为 1000，保留高 fitness 结果" \
  --namespace "code-review-fixes"
```

---

## 七、验证修复结果

### 7.1 使用 Ruflo 验证

```bash
# 1. 运行代码审查
ruflo agent_spawn --agentType reviewer --task "验证修复后的代码质量"

# 2. 运行性能测试
ruflo performance_benchmark --suite all

# 3. 运行安全扫描
ruflo aidefence_scan --input "扫描修复后的代码"

# 4. 检查测试覆盖率
ruflo hooks_worker-status --workerId testgaps
```

### 7.2 生成验证报告

```bash
# 使用 Ruflo 生成报告
ruflo agent_spawn --agentType docs-writer --task "生成修复验证报告"
```

---

## 八、推荐执行顺序

### 阶段 1: 准备（今天）

1. ✅ 备份当前代码
2. ✅ 创建修复分支
3. ✅ 配置 Ruflo hooks

### 阶段 2: P0 修复（今天）

1. 删除敏感文件
2. 检查 git 历史
3. 添加 timeout 参数

### 阶段 3: P1 修复（本周）

1. 修复内存泄漏
2. 添加知识库缓存
3. 实现 API 限流
4. 优化重试策略

### 阶段 4: P2 修复（下周）

1. 拆分过长文件
2. 提取公共代码
3. 创建 shared/ 模块

### 阶段 5: P3 改进（长期）

1. 添加测试覆盖
2. 实现策略插件
3. 引入依赖注入

---

## 九、常用 Ruflo 命令速查

```bash
# Swarm 操作
ruflo swarm_init --topology hierarchical --maxAgents 4
ruflo swarm_status --swarmId <id>
ruflo swarm_shutdown --swarmId <id>

# Agent 操作
ruflo agent_spawn --agentType coder --task "修复问题"
ruflo agent_status --agentId <id>
ruflo agent_terminate --agentId <id>

# Memory 操作
ruflo memory_store --key "fix-1" --value "..." --namespace "fixes"
ruflo memory_search --query "性能优化" --namespace "fixes"

# Security 操作
ruflo aidefence_scan --input "扫描内容"
ruflo aidefence_has_pii --input "检查内容"

# Performance 操作
ruflo performance_benchmark --suite memory
ruflo performance_profile --target alpha_generator

# Workflow 操作
ruflo workflow_create --name "fix-flow" --steps '[...]'
ruflo workflow_execute --workflowId <id>
ruflo workflow_status --workflowId <id>

# Hooks 操作
ruflo hooks_pre-edit --filePath <path>
ruflo hooks_post-edit --filePath <path> --success true
ruflo hooks_worker-dispatch --trigger optimize
```

---

**文档版本**: 1.0  
**最后更新**: 2026-05-09
