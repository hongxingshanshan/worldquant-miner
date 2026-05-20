"""
安全移除外键约束的迁移脚本

自动检测外键名称并删除，避免手动执行 SQL 的错误
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from db import MySQLConnector


def get_foreign_keys(db: MySQLConnector) -> list:
    """
    获取所有指向 alpha 表的外键

    Args:
        db: 数据库连接器

    Returns:
        外键列表 [{'table_name': str, 'constraint_name': str}, ...]
    """
    sql = """
        SELECT
            TABLE_NAME as table_name,
            CONSTRAINT_NAME as constraint_name
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
          AND REFERENCED_TABLE_NAME = 'alpha'
    """
    return db.query_all(sql)


def remove_foreign_keys(db: MySQLConnector, dry_run: bool = False) -> dict:
    """
    移除所有外键约束

    Args:
        db: 数据库连接器
        dry_run: 是否只模拟运行

    Returns:
        结果统计
    """
    results = {
        'found': 0,
        'removed': 0,
        'errors': [],
        'details': []
    }

    # 获取外键列表
    foreign_keys = get_foreign_keys(db)
    results['found'] = len(foreign_keys)

    print(f"\n发现 {len(foreign_keys)} 个外键约束:")
    for fk in foreign_keys:
        print(f"  - {fk['table_name']}: {fk['constraint_name']}")

    if len(foreign_keys) == 0:
        print("\n没有需要删除的外键约束")
        return results

    # 删除外键
    for fk in foreign_keys:
        table_name = fk['table_name']
        constraint_name = fk['constraint_name']

        sql = f"ALTER TABLE {table_name} DROP FOREIGN KEY {constraint_name}"

        if dry_run:
            print(f"\n[模拟] 将执行: {sql}")
            results['details'].append({
                'table': table_name,
                'constraint': constraint_name,
                'status': 'dry_run'
            })
        else:
            try:
                print(f"\n执行: {sql}")
                db.execute(sql)
                print(f"  ✓ 成功删除")
                results['removed'] += 1
                results['details'].append({
                    'table': table_name,
                    'constraint': constraint_name,
                    'status': 'success'
                })
            except Exception as e:
                error_msg = f"删除 {table_name} 的外键失败: {e}"
                print(f"  ✗ {error_msg}")
                results['errors'].append(error_msg)
                results['details'].append({
                    'table': table_name,
                    'constraint': constraint_name,
                    'status': 'error',
                    'error': str(e)
                })

    return results


def ensure_indexes(db: MySQLConnector) -> dict:
    """
    确保必要的索引存在

    Args:
        db: 数据库连接器

    Returns:
        结果统计
    """
    results = {
        'created': 0,
        'errors': []
    }

    # 需要确保存在的索引
    indexes = [
        ('alpha_settings', 'alpha_id'),
        ('alpha_performance', 'alpha_id'),
        ('alpha_checks', 'alpha_id'),
        ('alpha_competitions', 'alpha_id'),
        ('alpha_team', 'alpha_id'),
        ('alpha_classifications', 'alpha_id'),
        ('alpha_optimization_history', 'alpha_id'),
    ]

    for table_name, column in indexes:
        # 检查索引是否存在
        check_sql = """
            SELECT COUNT(*) as cnt
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME = %s
              AND INDEX_NAME != 'PRIMARY'
        """
        result = db.query_one(check_sql, (table_name, column))

        if result and result['cnt'] > 0:
            print(f"  ✓ 索引已存在: {table_name}({column})")
            continue

        # 创建索引
        index_name = f"idx_{table_name}_{column}"
        create_sql = f"CREATE INDEX {index_name} ON {table_name}({column})"

        try:
            print(f"  创建索引: {index_name}")
            db.execute(create_sql)
            results['created'] += 1
        except Exception as e:
            # 索引可能已存在（检查可能有误）
            if 'Duplicate key name' in str(e) or 'already exists' in str(e).lower():
                print(f"  ✓ 索引已存在: {index_name}")
            else:
                error_msg = f"创建索引 {index_name} 失败: {e}"
                print(f"  ✗ {error_msg}")
                results['errors'].append(error_msg)

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description='安全移除外键约束')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际删除')
    parser.add_argument('--execute', action='store_true', help='实际执行删除')
    parser.add_argument('--config', type=str, default='config.json', help='配置文件路径')

    args = parser.parse_args()

    dry_run = not args.execute

    # 加载配置
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), args.config)
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        db_config = config.get('database', {})
    else:
        print(f"配置文件不存在: {config_path}")
        print("请确保 config.json 中包含 database 配置")
        sys.exit(1)

    # 初始化数据库连接
    db = MySQLConnector(db_config)

    # 测试连接
    if not db.test_connection():
        print("数据库连接失败")
        sys.exit(1)

    print("=" * 60)
    print("移除外键约束迁移脚本")
    print("=" * 60)
    print(f"模式: {'模拟运行' if dry_run else '实际执行'}")

    # 移除外键
    print("\n【步骤 1】移除外键约束")
    print("-" * 40)
    fk_results = remove_foreign_keys(db, dry_run=dry_run)

    # 确保索引
    if not dry_run:
        print("\n【步骤 2】确保索引存在")
        print("-" * 40)
        idx_results = ensure_indexes(db)
    else:
        print("\n【步骤 2】确保索引存在 (模拟运行，跳过)")
        idx_results = {'created': 0, 'errors': []}

    # 验证结果
    print("\n【验证】检查外键状态")
    print("-" * 40)
    remaining = get_foreign_keys(db)
    if len(remaining) == 0:
        print("  ✓ 所有外键已移除")
    else:
        print(f"  ✗ 仍有 {len(remaining)} 个外键:")
        for fk in remaining:
            print(f"    - {fk['table_name']}: {fk['constraint_name']}")

    # 总结
    print("\n" + "=" * 60)
    print("执行结果:")
    print(f"  发现外键: {fk_results['found']}")
    print(f"  已删除: {fk_results['removed']}")
    print(f"  创建索引: {idx_results['created']}")
    if fk_results['errors'] or idx_results['errors']:
        print(f"  错误: {len(fk_results['errors']) + len(idx_results['errors'])}")
    print("=" * 60)


if __name__ == '__main__':
    main()
