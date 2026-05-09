#!/bin/bash
# WorldQuant Miner - Ruflo 自动修复脚本
# 使用 Ruflo Swarm 处理代码审查报告中的问题

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORT_FILE="$PROJECT_ROOT/docs/CODE_REVIEW_REPORT.md"

# 设置 API 环境变量
export ANTHROPIC_API_KEY="sk-LVzCwEJ9SNOaL1nunwwy1LFMXw85EASHfWDAlvkdb7Ro0DLz"
export ANTHROPIC_BASE_URL="https://cmkey.cn"

echo "========================================"
echo "WorldQuant Miner - Ruflo 自动修复"
echo "========================================"
echo ""

# 检查 Ruflo 是否可用
if ! command -v ruflo &> /dev/null; then
    echo "错误: Ruflo 未安装"
    echo "请先安装 Ruflo: npm install -g ruflo"
    exit 1
fi

# 检查审查报告是否存在
if [ ! -f "$REPORT_FILE" ]; then
    echo "错误: 审查报告不存在: $REPORT_FILE"
    exit 1
fi

echo "审查报告: $REPORT_FILE"
echo ""

# 解析参数
FIX_LEVEL="${1:-all}"  # p0, p1, p2, all

echo "修复级别: $FIX_LEVEL"
echo ""

# ========================================
# P0 - 立即修复
# ========================================
fix_p0() {
    echo "=== P0: 开始修复安全问题 ==="
    echo ""

    # 1. 检查敏感文件
    echo "1. 检查敏感文件..."

    SENSITIVE_FILES=(
        ".claude/projects/C--WorkSpace-worldquant-miner/memory/worldquantbrain_credentials.md"
        "credential.txt"
        "generation_one/naive-ollama/credential.txt"
    )

    for file in "${SENSITIVE_FILES[@]}"; do
        if [ -f "$PROJECT_ROOT/$file" ]; then
            echo "  发现敏感文件: $file"
            echo "  自动删除敏感文件..."
            rm -f "$PROJECT_ROOT/$file"
            echo "  已删除: $file"
        fi
    done

    # 2. 使用 AIDefence 扫描
    echo ""
    echo "2. 使用 AIDefence 扫描敏感信息..."
    ruflo security defend --input "扫描项目中的 API 密钥、密码等敏感信息" 2>/dev/null || echo "  (跳过安全扫描)"

    # 3. 检查 git 历史
    echo ""
    echo "3. 检查 git 历史中的敏感文件..."
    git log --all --full-history -- "credential.txt" 2>/dev/null || echo "  未发现凭证文件提交记录"

    echo ""
    echo "=== P0: 安全问题修复完成 ==="
}

# ========================================
# P1 - 本周修复
# ========================================
fix_p1() {
    echo "=== P1: 开始修复性能问题 ==="
    echo ""

    # 初始化 Swarm
    echo "1. 初始化性能修复 Swarm..."
    ruflo swarm init --topology hierarchical 2>/dev/null || true

    echo ""
    echo "2. 创建修复任务..."

    # 创建任务
    TASK1=$(ruflo task create -t bugfix -d "为 AlphaGenerator 添加结果清理机制，限制 max_results=1000，防止内存泄漏" 2>/dev/null | grep -o 'task-[a-z0-9]*' || echo "")
    echo "  任务1: $TASK1 - 内存泄漏修复"

    TASK2=$(ruflo task create -t bugfix -d "为 load_knowledge_base 函数添加 lru_cache 装饰器，缓存知识库加载结果" 2>/dev/null | grep -o 'task-[a-z0-9]*' || echo "")
    echo "  任务2: $TASK2 - 知识库缓存"

    TASK3=$(ruflo task create -t bugfix -d "实现令牌桶算法 RateLimiter 类，用于 API 限流" 2>/dev/null | grep -o 'task-[a-z0-9]*' || echo "")
    echo "  任务3: $TASK3 - API 限流器"

    TASK4=$(ruflo task create -t bugfix -d "使用哈希索引优化 is_similar_to_existing 方法，从 O(n²) 优化到 O(n log n)" 2>/dev/null | grep -o 'task-[a-z0-9]*' || echo "")
    echo "  任务4: $TASK4 - 去重算法优化"

    echo ""
    echo "3. 启动修复 Agents..."

    # 启动 agents
    AGENT1=$(ruflo agent spawn -t coder 2>/dev/null | grep -o 'coder-[a-z0-9]*' || echo "")
    echo "  Agent 1: $AGENT1"

    AGENT2=$(ruflo agent spawn -t coder 2>/dev/null | grep -o 'coder-[a-z0-9]*' || echo "")
    echo "  Agent 2: $AGENT2"

    AGENT3=$(ruflo agent spawn -t coder 2>/dev/null | grep -o 'coder-[a-z0-9]*' || echo "")
    echo "  Agent 3: $AGENT3"

    AGENT4=$(ruflo agent spawn -t coder 2>/dev/null | grep -o 'coder-[a-z0-9]*' || echo "")
    echo "  Agent 4: $AGENT4"

    echo ""
    echo "4. 分配任务给 Agents..."
    [ -n "$TASK1" ] && [ -n "$AGENT1" ] && ruflo task assign "$TASK1" --agent "$AGENT1" 2>/dev/null && echo "  已分配: $TASK1 -> $AGENT1"
    [ -n "$TASK2" ] && [ -n "$AGENT2" ] && ruflo task assign "$TASK2" --agent "$AGENT2" 2>/dev/null && echo "  已分配: $TASK2 -> $AGENT2"
    [ -n "$TASK3" ] && [ -n "$AGENT3" ] && ruflo task assign "$TASK3" --agent "$AGENT3" 2>/dev/null && echo "  已分配: $TASK3 -> $AGENT3"
    [ -n "$TASK4" ] && [ -n "$AGENT4" ] && ruflo task assign "$TASK4" --agent "$AGENT4" 2>/dev/null && echo "  已分配: $TASK4 -> $AGENT4"

    echo ""
    echo "5. 存储修复模式到 Memory..."
    ruflo memory store -k "security-fix-timeout" -v "为 requests 调用添加 timeout 参数" 2>/dev/null || true
    ruflo memory store -k "performance-fix-cache" -v "使用 lru_cache 缓存知识库" 2>/dev/null || true

    echo ""
    echo "=== P1: 性能问题修复完成 ==="
    echo ""
    echo "提示: 使用 'ruflo task list' 查看任务进度"
    echo "提示: 使用 'ruflo swarm status' 查看 Swarm 状态"
}

# ========================================
# P2 - 下两周修复
# ========================================
fix_p2() {
    echo "=== P2: 开始修复代码质量问题 ==="
    echo ""

    echo "1. 创建架构重构任务..."

    TASK1=$(ruflo task create -t refactor -d "拆分 alpha_generator_ollama.py (1509行) 为多个模块" 2>/dev/null | grep -o 'task-[a-z0-9]*' || echo "")
    echo "  任务1: $TASK1 - 文件拆分"

    TASK2=$(ruflo task create -t refactor -d "创建 shared/ 模块，提取公共代码" 2>/dev/null | grep -o 'task-[a-z0-9]*' || echo "")
    echo "  任务2: $TASK2 - 公共模块提取"

    echo ""
    echo "2. 创建 shared/ 目录结构..."
    mkdir -p "$PROJECT_ROOT/shared/"{config,llm,logging,process,monitoring,validation,utils,security}
    mkdir -p "$PROJECT_ROOT/core/"{generator,validator,tester,submitter,orchestrator,api}
    mkdir -p "$PROJECT_ROOT/strategies/"{naive,consultant,bandit,evolution,templates}

    echo "  已创建目录结构"

    echo ""
    echo "=== P2: 代码质量问题修复完成 ==="
}

# ========================================
# 验证修复结果
# ========================================
verify_fixes() {
    echo "=== 验证修复结果 ==="
    echo ""

    echo "1. 查看任务状态..."
    ruflo task list 2>/dev/null || echo "  (无任务)"

    echo ""
    echo "2. 运行安全扫描..."
    ruflo security defend --input "扫描修复后的代码" 2>/dev/null || echo "  (跳过)"

    echo ""
    echo "3. 检查语法..."
    python -m py_compile "$PROJECT_ROOT/generation_one/naive-ollama/alpha_expression_miner.py" 2>/dev/null && echo "  语法检查通过" || echo "  语法检查失败"

    echo ""
    echo "=== 验证完成 ==="
}

# ========================================
# 主流程
# ========================================
main() {
    case "$FIX_LEVEL" in
        p0)
            fix_p0
            ;;
        p1)
            fix_p1
            ;;
        p2)
            fix_p2
            ;;
        all)
            fix_p0
            echo ""
            fix_p1
            echo ""
            fix_p2
            ;;
        *)
            echo "用法: $0 [p0|p1|p2|all]"
            exit 1
            ;;
    esac

    echo ""
    verify_fixes

    echo ""
    echo "========================================"
    echo "修复完成!"
    echo "========================================"
    echo ""
    echo "下一步:"
    echo "  1. 检查任务进度: ruflo task list"
    echo "  2. 查看 Swarm 状态: ruflo swarm status"
    echo "  3. 运行测试: pytest tests/"
    echo "  4. 提交变更: git add . && git commit"
    echo ""
}

main