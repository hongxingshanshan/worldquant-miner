"""
数据一致性检查工具

用于检查和修复移除外键后可能出现的数据一致性问题
"""
from typing import Dict, List, Optional
from datetime import datetime
import logging

from .db_connector import MySQLConnector

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


class DataIntegrityChecker:
    """数据一致性检查器"""

    # 关联表配置
    RELATED_TABLES = [
        {
            'name': 'alpha_settings',
            'fk_column': 'alpha_id',
            'relation': '1:1',
            'description': 'Alpha 设置'
        },
        {
            'name': 'alpha_performance',
            'fk_column': 'alpha_id',
            'relation': '1:N',
            'description': 'Alpha 性能指标'
        },
        {
            'name': 'alpha_checks',
            'fk_column': 'alpha_id',
            'relation': '1:N',
            'description': 'Alpha 检查结果'
        },
        {
            'name': 'alpha_competitions',
            'fk_column': 'alpha_id',
            'relation': '1:N',
            'description': 'Alpha 参赛信息'
        },
        {
            'name': 'alpha_team',
            'fk_column': 'alpha_id',
            'relation': '1:1',
            'description': 'Alpha 团队信息'
        },
        {
            'name': 'alpha_classifications',
            'fk_column': 'alpha_id',
            'relation': '1:N',
            'description': 'Alpha 分类信息'
        },
        {
            'name': 'alpha_optimization_history',
            'fk_column': 'alpha_id',
            'relation': '1:N',
            'description': 'Alpha 优化历史'
        },
    ]

    def __init__(self, db_config: dict):
        """
        初始化检查器

        Args:
            db_config: 数据库配置
        """
        self.db = MySQLConnector(db_config)

    def check_orphan_records(self) -> Dict:
        """
        检查所有子表的孤儿记录

        孤儿记录: 子表中存在但主表中不存在的记录

        Returns:
            检查结果 {'table_name': orphan_count, ...}
        """
        results = {}

        for table_info in self.RELATED_TABLES:
            table_name = table_info['name']
            fk_column = table_info['fk_column']

            try:
                sql = f"""
                    SELECT COUNT(*) as orphan_count
                    FROM {table_name} t
                    WHERE NOT EXISTS (
                        SELECT 1 FROM alpha a WHERE a.id = t.{fk_column}
                    )
                """

                result = self.db.query_one(sql)
                orphan_count = result['orphan_count'] if result else 0
                results[table_name] = {
                    'orphan_count': orphan_count,
                    'relation': table_info['relation'],
                    'description': table_info['description'],
                    'exists': True
                }

                if orphan_count > 0:
                    logger.warning(f"发现 {orphan_count} 条孤儿记录: {table_name}")
                else:
                    logger.info(f"无孤儿记录: {table_name}")

            except Exception as e:
                # 表可能不存在
                if "doesn't exist" in str(e) or "not exist" in str(e).lower():
                    logger.info(f"表不存在，跳过: {table_name}")
                    results[table_name] = {
                        'orphan_count': 0,
                        'relation': table_info['relation'],
                        'description': table_info['description'],
                        'exists': False
                    }
                else:
                    logger.error(f"检查 {table_name} 时出错: {e}")
                    results[table_name] = {
                        'orphan_count': 0,
                        'relation': table_info['relation'],
                        'description': table_info['description'],
                        'exists': False,
                        'error': str(e)
                    }

        return results

    def get_orphan_details(self, table_name: str, limit: int = 100) -> List[Dict]:
        """
        获取指定表的孤儿记录详情

        Args:
            table_name: 表名
            limit: 返回数量限制

        Returns:
            孤儿记录列表
        """
        table_info = next((t for t in self.RELATED_TABLES if t['name'] == table_name), None)
        if not table_info:
            logger.error(f"未知的表: {table_name}")
            return []

        fk_column = table_info['fk_column']

        sql = f"""
            SELECT t.*
            FROM {table_name} t
            WHERE NOT EXISTS (
                SELECT 1 FROM alpha a WHERE a.id = t.{fk_column}
            )
            LIMIT %s
        """

        return self.db.query_all(sql, (limit,))

    def clean_orphan_records(self, dry_run: bool = True) -> Dict:
        """
        清理所有孤儿记录

        Args:
            dry_run: 是否只模拟运行（不实际删除）

        Returns:
            清理结果统计
        """
        results = {
            'dry_run': dry_run,
            'cleaned': {},
            'errors': []
        }

        for table_info in self.RELATED_TABLES:
            table_name = table_info['name']
            fk_column = table_info['fk_column']

            try:
                # 先统计数量
                count_sql = f"""
                    SELECT COUNT(*) as cnt
                    FROM {table_name} t
                    WHERE NOT EXISTS (
                        SELECT 1 FROM alpha a WHERE a.id = t.{fk_column}
                    )
                """
                count_result = self.db.query_one(count_sql)
                orphan_count = count_result['cnt'] if count_result else 0

                if orphan_count == 0:
                    results['cleaned'][table_name] = 0
                    continue

                if dry_run:
                    logger.info(f"[模拟] 将删除 {table_name} 中的 {orphan_count} 条孤儿记录")
                    results['cleaned'][table_name] = orphan_count
                else:
                    # 实际删除
                    delete_sql = f"""
                        DELETE t FROM {table_name} t
                        WHERE NOT EXISTS (
                            SELECT 1 FROM alpha a WHERE a.id = t.{fk_column}
                        )
                    """
                    deleted = self.db.execute(delete_sql)
                    results['cleaned'][table_name] = deleted
                    logger.info(f"已删除 {table_name} 中的 {deleted} 条孤儿记录")

            except Exception as e:
                error_msg = f"清理 {table_name} 失败: {e}"
                logger.error(error_msg)
                results['errors'].append(error_msg)

        return results

    def check_missing_related_data(self) -> Dict:
        """
        检查主表中缺少关联数据的记录

        例如: alpha 存在但 alpha_settings 不存在

        Returns:
            检查结果
        """
        results = {}

        # 检查缺少 settings 的 alpha
        sql = """
            SELECT COUNT(*) as missing_count
            FROM alpha a
            WHERE NOT EXISTS (
                SELECT 1 FROM alpha_settings s WHERE s.alpha_id = a.id
            )
        """
        result = self.db.query_one(sql)
        results['alpha_without_settings'] = result['missing_count'] if result else 0

        # 检查缺少 performance 的 alpha
        sql = """
            SELECT COUNT(*) as missing_count
            FROM alpha a
            WHERE NOT EXISTS (
                SELECT 1 FROM alpha_performance p WHERE p.alpha_id = a.id
            )
        """
        result = self.db.query_one(sql)
        results['alpha_without_performance'] = result['missing_count'] if result else 0

        return results

    def check_data_consistency(self) -> Dict:
        """
        全面数据一致性检查

        Returns:
            检查报告
        """
        report = {
            'check_time': datetime.now().isoformat(),
            'orphan_records': self.check_orphan_records(),
            'missing_related_data': self.check_missing_related_data(),
            'summary': {
                'total_orphan_records': 0,
                'has_issues': False
            }
        }

        # 统计孤儿记录总数
        for table_name, info in report['orphan_records'].items():
            report['summary']['total_orphan_records'] += info['orphan_count']

        # 判断是否有问题
        report['summary']['has_issues'] = (
            report['summary']['total_orphan_records'] > 0 or
            report['missing_related_data'].get('alpha_without_settings', 0) > 0
        )

        return report

    def verify_foreign_key_removal(self) -> Dict:
        """
        验证外键是否已移除

        Returns:
            验证结果
        """
        sql = """
            SELECT
                TABLE_NAME,
                CONSTRAINT_NAME,
                COLUMN_NAME,
                REFERENCED_TABLE_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND REFERENCED_TABLE_NAME IS NOT NULL
        """

        foreign_keys = self.db.query_all(sql)

        return {
            'has_foreign_keys': len(foreign_keys) > 0,
            'foreign_key_count': len(foreign_keys),
            'foreign_keys': foreign_keys
        }

    def print_report(self, report: Dict = None):
        """
        打印检查报告

        Args:
            report: 检查报告（如果为 None 则重新检查）
        """
        if report is None:
            report = self.check_data_consistency()

        print("\n" + "=" * 60)
        print("数据一致性检查报告")
        print("=" * 60)
        print(f"检查时间: {report['check_time']}")
        print()

        # 孤儿记录
        print("【孤儿记录检查】")
        for table_name, info in report['orphan_records'].items():
            status = "✓ 正常" if info['orphan_count'] == 0 else f"✗ 发现 {info['orphan_count']} 条"
            print(f"  {table_name}: {status}")
        print()

        # 缺失关联数据
        print("【缺失关联数据检查】")
        for key, count in report['missing_related_data'].items():
            status = "✓ 正常" if count == 0 else f"✗ 缺失 {count} 条"
            print(f"  {key}: {status}")
        print()

        # 外键验证
        fk_result = self.verify_foreign_key_removal()
        print("【外键状态】")
        if fk_result['has_foreign_keys']:
            print(f"  ✗ 仍存在 {fk_result['foreign_key_count']} 个外键约束")
            for fk in fk_result['foreign_keys']:
                print(f"    - {fk['TABLE_NAME']}.{fk['COLUMN_NAME']} -> {fk['REFERENCED_TABLE_NAME']}")
        else:
            print("  ✓ 所有外键已移除")
        print()

        # 总结
        print("【总结】")
        if report['summary']['has_issues']:
            print(f"  ✗ 发现数据一致性问题，建议运行清理")
        else:
            print("  ✓ 数据一致性良好")

        print("=" * 60)


def main():
    """命令行入口"""
    import argparse
    import json
    import os
    import sys

    # 添加项目根目录到路径
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    parser = argparse.ArgumentParser(description='数据一致性检查工具')
    parser.add_argument('--check', action='store_true', help='检查数据一致性')
    parser.add_argument('--clean', action='store_true', help='清理孤儿记录')
    parser.add_argument('--dry-run', action='store_true', default=True, help='模拟运行（不实际删除）')
    parser.add_argument('--execute', action='store_true', help='实际执行删除')
    parser.add_argument('--verify-fk', action='store_true', help='验证外键是否已移除')
    parser.add_argument('--config', type=str, default='db/db_config.json', help='配置文件路径')

    args = parser.parse_args()

    # 加载配置 - 支持多种格式
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), config_path)

    db_config = None

    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        # 支持两种格式: 直接是数据库配置，或者包含 database 字段
        if 'database' in config:
            db_config = config.get('database', {})
        elif 'host' in config:
            # db/db_config.json 格式 - 直接就是数据库配置
            db_config = config
    else:
        print(f"配置文件不存在: {config_path}")
        print("请确保 config.json 中包含 database 配置")
        sys.exit(1)

    if db_config is None:
        print(f"配置文件不存在或格式错误: {config_path}")
        print("请确保配置文件包含数据库配置")
        sys.exit(1)

    checker = DataIntegrityChecker(db_config)

    if args.verify_fk:
        result = checker.verify_foreign_key_removal()
        if result['has_foreign_keys']:
            print(f"仍存在 {result['foreign_key_count']} 个外键约束:")
            for fk in result['foreign_keys']:
                print(f"  - {fk['TABLE_NAME']}.{fk['COLUMN_NAME']} -> {fk['REFERENCED_TABLE_NAME']}")
        else:
            print("✓ 所有外键已移除")

    elif args.clean:
        dry_run = not args.execute
        result = checker.clean_orphan_records(dry_run=dry_run)
        print(f"\n清理结果 (dry_run={dry_run}):")
        for table, count in result['cleaned'].items():
            print(f"  {table}: {count} 条")
        if result['errors']:
            print("\n错误:")
            for err in result['errors']:
                print(f"  - {err}")

    elif args.check:
        checker.print_report()

    else:
        # 默认执行检查
        checker.print_report()


if __name__ == '__main__':
    main()
