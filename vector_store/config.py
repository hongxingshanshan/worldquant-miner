# -*- coding: utf-8 -*-
"""
向量数据库配置
"""

# 嵌入模型配置
EMBEDDING_CONFIG = {
    "model": "paraphrase-multilingual-MiniLM-L12-v2",
    "device": "cpu",
    "batch_size": 32
}

# 分块配置
CHUNKING_CONFIG = {
    "chunk_size": 500,
    "chunk_overlap": 50,
    "min_chunk_size": 100,
    "separators": ["\n\n", "\n", "。", "；", "，", " "]
}

# 检索配置
RETRIEVAL_CONFIG = {
    "default_top_k": 5,
    "alpha_generation_top_k": 5
}

# 向量数据库配置
VECTOR_STORE_CONFIG = {
    "collection_name": "knowledge_chunks",
    "description": "知识库文档块"
}

# ============================================================
# Alpha 向量化配置（新增）
# ============================================================

# Alpha 专用集合配置（三种数据类型）
ALPHA_COLLECTIONS = {
    # 已提交 Alpha 集合（最高质量）
    "submitted_alphas": {
        "name": "alpha_submitted",
        "description": "已提交 Alpha（status=SUBMITTED）",
        "filter": {
            "status": "SUBMITTED"
        }
    },
    # 可提交 Alpha 集合（待提交候选）
    "submittable_alphas": {
        "name": "alpha_submittable",
        "description": "可提交 Alpha（status=UNSUBMITTED, IS检查7PASS0FAIL）",
        "filter": {
            "status": "UNSUBMITTED",
            "checks_pass": 7,
            "checks_fail": 0
        }
    },
    # 失败 Alpha 集合
    "failure_alphas": {
        "name": "alpha_failure",
        "description": "失败 Alpha（IS检查有FAIL）",
        "filter": {
            "checks_fail": {"$gt": 0}
        }
    },
    # 优化成功案例集合
    "optimization_cases": {
        "name": "alpha_optimization_cases",
        "description": "优化成功案例",
        "filter": {
            "success": True
        }
    },
    # 字段组合集合
    "field_combinations": {
        "name": "field_combinations",
        "description": "字段组合模式"
    }
}

# Alpha 同步配置
ALPHA_SYNC_CONFIG = {
    "batch_size": 100,
    "interval_minutes": 60,
    "full_sync_hour": 3,  # 凌晨 3 点全量同步
    # 成功 Alpha 筛选阈值
    "success_min_sharpe": 1.5,
    "success_min_fitness": 1.0,
    # 失败 Alpha 筛选阈值（高 Sharpe 但失败的更有学习价值）
    "failure_min_sharpe": 1.0
}

# ============================================================
# 渐进式知识库配置（新增）
# ============================================================

# 阶段权重配置
PROGRESSIVE_PHASE_WEIGHTS = {
    "short": {"expert": 0.7, "retrieval": 0.3},  # 短期：专家主导
    "mid": {"expert": 0.4, "retrieval": 0.6},    # 中期：检索主导
    "long": {"expert": 0.2, "retrieval": 0.8}    # 长期：数据驱动
}

# 阶段转换条件
PHASE_TRANSITION_CONDITIONS = {
    "short_to_mid": {
        "min_chunks": 1000,
        "min_external_knowledge": 200,
        "min_success_alphas": 100
    },
    "mid_to_long": {
        "min_chunks": 5000,
        "min_success_alphas": 500,
        "min_optimization_cases": 200,
        "min_external_knowledge_ratio": 0.3
    }
}

# 知识质量监控阈值
QUALITY_THRESHOLDS = {
    "min_retrieval_hit_rate": 0.8,
    "min_avg_similarity": 0.5,
    "min_alpha_success_rate": 0.15,
    "min_external_knowledge_ratio": 0.3
}

# 提示词构建配置
PROMPT_BUILD_CONFIG = {
    "success_cases_top_k": 5,
    "failure_patterns_top_k": 3,
    "field_combos_top_k": 3,
    "optimization_cases_top_k": 5,
    "max_prompt_length": 8000
}
