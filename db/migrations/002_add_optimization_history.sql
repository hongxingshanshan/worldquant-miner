-- Alpha 优化历史表
-- 创建时间: 2026-05-17
-- 用途: 记录 Alpha 优化历史，支持优化案例的向量化和学习

CREATE TABLE IF NOT EXISTS alpha_optimization_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alpha_id VARCHAR(8) NOT NULL COMMENT 'Alpha ID',
    original_expression TEXT COMMENT '原始表达式',
    optimized_expression TEXT COMMENT '优化后表达式',
    original_sharpe DECIMAL(10,6) COMMENT '原始 Sharpe',
    original_fitness DECIMAL(10,6) COMMENT '原始 Fitness',
    original_turnover DECIMAL(10,6) COMMENT '原始 Turnover',
    optimized_sharpe DECIMAL(10,6) COMMENT '优化后 Sharpe',
    optimized_fitness DECIMAL(10,6) COMMENT '优化后 Fitness',
    optimized_turnover DECIMAL(10,6) COMMENT '优化后 Turnover',
    fail_type VARCHAR(50) COMMENT '失败类型',
    fail_check_name VARCHAR(100) COMMENT '失败检查项名称',
    optimization_method VARCHAR(100) COMMENT '优化方法',
    optimization_strategy TEXT COMMENT '优化策略描述',
    success BOOLEAN DEFAULT FALSE COMMENT '是否成功通过检查',
    attempt_count INT DEFAULT 1 COMMENT '尝试次数',
    llm_model VARCHAR(100) COMMENT '使用的 LLM 模型',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_alpha (alpha_id),
    INDEX idx_success (success),
    INDEX idx_fail_type (fail_type),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (alpha_id) REFERENCES alpha(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Alpha 优化历史表';
