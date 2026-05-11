-- Alpha 数据库初始化脚本
-- 创建时间: 2026-05-11

-- 1. Alpha 主表
CREATE TABLE IF NOT EXISTS alpha (
    id VARCHAR(8) PRIMARY KEY COMMENT 'Alpha ID',
    type VARCHAR(50) COMMENT 'Alpha 类型',
    author VARCHAR(100) COMMENT '作者',
    expression TEXT COMMENT 'Alpha 表达式',
    description TEXT COMMENT '描述',
    operator_count INT COMMENT '操作符数量',
    date_created DATETIME COMMENT '创建时间',
    date_submitted DATETIME COMMENT '提交时间',
    date_modified DATETIME COMMENT '修改时间',
    grade VARCHAR(10) COMMENT '等级',
    stage VARCHAR(20) COMMENT '阶段',
    status VARCHAR(20) COMMENT '状态',
    origin VARCHAR(50) COMMENT '来源',
    favorite BOOLEAN DEFAULT FALSE COMMENT '是否收藏',
    hidden BOOLEAN DEFAULT FALSE COMMENT '是否隐藏',
    tags TEXT COMMENT '标签（JSON数组）',
    synced_at DATETIME COMMENT '同步时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Alpha 主表';

-- 2. Alpha 设置表
CREATE TABLE IF NOT EXISTS alpha_settings (
    alpha_id VARCHAR(8) PRIMARY KEY COMMENT 'Alpha ID',
    instrument_type VARCHAR(50) COMMENT '工具类型',
    region VARCHAR(20) COMMENT '区域',
    universe VARCHAR(50) COMMENT '数据范围',
    delay INT COMMENT '延迟天数',
    decay INT COMMENT '衰减天数',
    neutralization VARCHAR(50) COMMENT '中性化方式',
    truncation DECIMAL(10,4) COMMENT '截断值',
    pasteurization BOOLEAN COMMENT '是否消毒',
    unit_handling VARCHAR(50) COMMENT '单位处理',
    nan_handling VARCHAR(50) COMMENT 'NaN 处理',
    max_trade DECIMAL(25,8) COMMENT '最大交易量',
    max_position DECIMAL(25,8) COMMENT '最大持仓',
    language VARCHAR(20) COMMENT '语言',
    visualization VARCHAR(50) COMMENT '可视化类型',
    start_date DATE COMMENT '开始日期',
    end_date DATE COMMENT '结束日期',
    FOREIGN KEY (alpha_id) REFERENCES alpha(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Alpha 设置表';

-- 3. Alpha 性能指标表
CREATE TABLE IF NOT EXISTS alpha_performance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alpha_id VARCHAR(8) NOT NULL COMMENT 'Alpha ID',
    stage VARCHAR(10) NOT NULL COMMENT '阶段 (IS/OS/TRAIN/TEST/PROD)',
    pnl DECIMAL(25,8) COMMENT '盈亏',
    book_size DECIMAL(25,8) COMMENT '账面规模',
    long_count INT COMMENT '多头数量',
    short_count INT COMMENT '空头数量',
    turnover DECIMAL(25,8) COMMENT '换手率',
    returns DECIMAL(25,8) COMMENT '收益率',
    drawdown DECIMAL(25,8) COMMENT '最大回撤',
    margin DECIMAL(25,8) COMMENT '保证金',
    sharpe DECIMAL(10,6) COMMENT '夏普比率',
    fitness DECIMAL(10,6) COMMENT '适应度',
    self_correlation DECIMAL(10,6) COMMENT '自相关性',
    prod_correlation DECIMAL(10,6) COMMENT '与 Prod 相关性',
    start_date DATE COMMENT '开始日期',
    os_is_sharpe_ratio DECIMAL(10,6) COMMENT 'OS-IS 夏普比率',
    pre_close_sharpe_ratio DECIMAL(10,6) COMMENT '前收盘夏普比率',
    UNIQUE KEY uk_alpha_stage (alpha_id, stage),
    FOREIGN KEY (alpha_id) REFERENCES alpha(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Alpha 性能指标表';

-- 4. Alpha 检查结果表
CREATE TABLE IF NOT EXISTS alpha_checks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alpha_id VARCHAR(8) NOT NULL COMMENT 'Alpha ID',
    stage VARCHAR(10) NOT NULL COMMENT '阶段 (IS/OS)',
    check_name VARCHAR(100) COMMENT '检查名称',
    result VARCHAR(20) COMMENT '检查结果 (PASS/FAIL)',
    limit_value DECIMAL(25,8) COMMENT '限制值',
    actual_value DECIMAL(25,8) COMMENT '实际值',
    INDEX idx_alpha_stage (alpha_id, stage),
    FOREIGN KEY (alpha_id) REFERENCES alpha(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Alpha 检查结果表';

-- 5. Alpha 参赛信息表
CREATE TABLE IF NOT EXISTS alpha_competitions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alpha_id VARCHAR(8) NOT NULL COMMENT 'Alpha ID',
    competition_id VARCHAR(50) COMMENT '比赛 ID',
    competition_name VARCHAR(200) COMMENT '比赛名称',
    UNIQUE KEY uk_alpha_comp (alpha_id, competition_id),
    FOREIGN KEY (alpha_id) REFERENCES alpha(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Alpha 参赛信息表';

-- 6. Alpha 团队信息表
CREATE TABLE IF NOT EXISTS alpha_team (
    alpha_id VARCHAR(8) PRIMARY KEY COMMENT 'Alpha ID',
    team_id VARCHAR(50) COMMENT '团队 ID',
    team_type VARCHAR(50) COMMENT '团队类型',
    team_name VARCHAR(200) COMMENT '团队名称',
    university VARCHAR(200) COMMENT '大学',
    FOREIGN KEY (alpha_id) REFERENCES alpha(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Alpha 团队信息表';

-- 7. Alpha 分类信息表
CREATE TABLE IF NOT EXISTS alpha_classifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alpha_id VARCHAR(8) NOT NULL COMMENT 'Alpha ID',
    classification_id VARCHAR(50) COMMENT '分类 ID',
    classification_name VARCHAR(200) COMMENT '分类名称',
    UNIQUE KEY uk_alpha_class (alpha_id, classification_id),
    FOREIGN KEY (alpha_id) REFERENCES alpha(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Alpha 分类信息表';

-- 8. Alpha 同步日志表
CREATE TABLE IF NOT EXISTS alpha_sync_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sync_type VARCHAR(20) COMMENT '同步类型 (FULL/INCREMENTAL)',
    total_count INT COMMENT '总数',
    new_count INT COMMENT '新增数',
    update_count INT COMMENT '更新数',
    error_count INT COMMENT '错误数',
    started_at DATETIME COMMENT '开始时间',
    finished_at DATETIME COMMENT '完成时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Alpha 同步日志表';

-- 创建索引
CREATE INDEX idx_alpha_date_created ON alpha(date_created);
CREATE INDEX idx_alpha_date_modified ON alpha(date_modified);
CREATE INDEX idx_alpha_stage ON alpha(stage);
CREATE INDEX idx_alpha_status ON alpha(status);
CREATE INDEX idx_alpha_grade ON alpha(grade);
CREATE INDEX idx_perf_sharpe ON alpha_performance(sharpe);
CREATE INDEX idx_perf_fitness ON alpha_performance(fitness);
CREATE INDEX idx_perf_stage ON alpha_performance(stage);