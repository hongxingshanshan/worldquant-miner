-- 移除所有外键约束
-- 创建时间: 2026-05-20
-- 目的: 提升 DDL 性能，避免锁表问题
-- 方案: 应用层保证数据完整性

-- MySQL 不支持 DROP FOREIGN KEY IF EXISTS，需要使用存储过程或手动删除
-- 使用方法: 直接执行此脚本，如果外键不存在会报错，可以忽略

-- 步骤 1: 先查询实际的外键名称
-- SELECT CONSTRAINT_NAME, TABLE_NAME FROM information_schema.KEY_COLUMN_USAGE
-- WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME = 'alpha';

-- 步骤 2: 删除外键（如果报错说外键不存在，说明已经删除过了，可以忽略）

-- 1. 移除 alpha_settings 外键
ALTER TABLE alpha_settings DROP FOREIGN KEY alpha_settings_ibfk_1;

-- 2. 移除 alpha_performance 外键
ALTER TABLE alpha_performance DROP FOREIGN KEY alpha_performance_ibfk_1;

-- 3. 移除 alpha_checks 外键
ALTER TABLE alpha_checks DROP FOREIGN KEY alpha_checks_ibfk_1;

-- 4. 移除 alpha_competitions 外键
ALTER TABLE alpha_competitions DROP FOREIGN KEY alpha_competitions_ibfk_1;

-- 5. 移除 alpha_team 外键
ALTER TABLE alpha_team DROP FOREIGN KEY alpha_team_ibfk_1;

-- 6. 移除 alpha_classifications 外键
ALTER TABLE alpha_classifications DROP FOREIGN KEY alpha_classifications_ibfk_1;

-- 7. 移除 alpha_optimization_history 外键
ALTER TABLE alpha_optimization_history DROP FOREIGN KEY alpha_optimization_history_ibfk_1;

-- 步骤 3: 确保索引存在（外键删除后索引可能被删除）
-- MySQL 也不支持 CREATE INDEX IF NOT EXISTS，需要单独处理

-- 验证外键已移除
-- 执行后可通过以下查询验证:
-- SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
-- WHERE TABLE_SCHEMA = DATABASE() AND CONSTRAINT_TYPE = 'FOREIGN KEY';
-- 预期结果: 0