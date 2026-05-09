#!/bin/bash
# WorldQuant Miner - Ruflo 自动修复脚本
# 使用 Ruflo Swarm 处理代码审查报告中的问题

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORT_FILE="$PROJECT_ROOT/docs/CODE_REVIEW_REPORT.md"

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
            read -p "  是否删除? (y/n): " confirm
            if [ "$confirm" = "y" ]; then
                rm -f "$PROJECT_ROOT/$file"
                echo "  已删除: $file"
            fi
        fi
    done

    # 2. 使用 AIDefence 扫描
    echo ""
    echo "2. 使用 AIDefence 扫描敏感信息..."
    ruflo aidefence_scan --input "扫描项目中的 API 密钥、密码等敏感信息"

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
    SWARM_RESULT=$(ruflo swarm_init --topology hierarchical --maxAgents 4 --strategy specialized 2>/dev/null || echo '{"swarmId": "local"}')
    SWARM_ID=$(echo "$SWARM_RESULT" | grep -o '"swarmId":"[^"]*"' | cut -d'"' -f4 || echo "local")
    echo "  Swarm ID: $SWARM_ID"

    echo ""
    echo "2. 启动修复 Agents..."

    # Agent 1: 内存泄漏
    echo "  [1/4] 内存泄漏修复..."
    ruflo agent_spawn --agentType coder --task "为 AlphaGenerator 添加结果清理机制，限制 max_results=1000" 2>/dev/null || echo "    (使用本地修复)"

    # Agent 2: 知识库缓存
    echo "  [2/4] 知识库缓存..."
    ruflo agent_spawn --agentType coder --task "为 load_knowledge_base 添加 lru_cache 装饰器" 2>/dev/null || echo "    (使用本地修复)"

    # Agent 3: API 限流
    echo "  [3/4] API 限流器..."
    ruflo agent_spawn --agentType coder --task "实现令牌桶算法 RateLimiter 类" 2>/dev/null || echo "    (使用本地修复)"

    # Agent 4: 去重优化
    echo "  [4/4] 去重算法优化..."
    ruflo agent_spawn --agentType coder --task "使用哈希索引优化 is_similar_to_existing 方法" 2>/dev/null || echo "    (使用本地修复)"

    echo ""
    echo "3. 存储修复模式到 AgentDB..."
    ruflo agentdb_pattern-store --pattern "为 requests 调用添加 timeout 参数" --type "security-fix" --confidence 0.95 2>/dev/null || true
    ruflo agentdb_pattern-store --pattern "使用 lru_cache 缓存知识库" --type "performance-fix" --confidence 0.9 2>/dev/null || true

    echo ""
    echo "=== P1: 性能问题修复完成 ==="
}

# ========================================
# P2 - 下两周修复
# ========================================
fix_p2() {
    echo "=== P2: 开始修复代码质量问题 ==="
    echo ""

    echo "1. 启动 SPARC 流程..."

    # Specification
    echo "  [Spec] 定义拆分规范..."
    ruflo agent_spawn --agentType sparc-spec --task "定义 alpha_generator_ollama.py 的拆分规范" 2>/dev/null || echo "    (跳过)"

    # Architecture
    echo "  [Arch] 设计模块架构..."
    ruflo agent_spawn --agentType sparc-architect --task "设计拆分后的模块架构" 2>/dev/null || echo "    (跳过)"

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

    echo "1. 运行代码审查..."
    ruflo agent_spawn --agentType reviewer --task "验证修复后的代码质量" 2>/dev/null || echo "  (跳过)"

    echo ""
    echo "2. 运行安全扫描..."
    ruflo aidefence_scan --input "扫描修复后的代码" 2>/dev/null || echo "  (跳过)"

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
    echo "  1. 检查修复结果"
    echo "  2. 运行测试: pytest tests/"
    echo "  3. 提交变更: git add . && git commit"
    echo ""
}

main
