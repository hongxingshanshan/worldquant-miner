"""
Alpha 数据库查询服务

从 MySQL 数据库查询 Alpha 数据供 Web Dashboard 使用
"""
import pymysql
from pymysql.cursors import DictCursor
from typing import List, Dict, Optional
from datetime import datetime
import json

from db.db_connector import MySQLConnector


class AlphaQueryService:
    """Alpha 数据库查询服务"""

    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.db = MySQLConnector(db_config)

    def get_alpha_list(self, limit: int = 50, order_by: str = 'is_checks_pass',
                       status_filter: str = None, stage_filter: str = None) -> List[Dict]:
        """
        获取 Alpha 列表

        Args:
            limit: 返回数量
            order_by: 排序字段
                - 'is_checks_pass': IS 检查通过数量（默认）
                - 'sharpe': IS 夏普比率
                - 'fitness': IS 适应度
                - 'date_created': 创建时间
                - 'date_modified': 修改时间
            status_filter: 状态过滤
            stage_filter: 阶段过滤

        Returns:
            Alpha 列表
        """
        # 排序映射
        order_map = {
            'is_checks_pass': 'is_checks_pass DESC, is_sharpe DESC',
            'sharpe': 'is_sharpe DESC',
            'fitness': 'is_fitness DESC',
            'date_created': 'a.date_created DESC',
            'date_modified': 'a.date_modified DESC'
        }
        order_clause = order_map.get(order_by, order_map['is_checks_pass'])

        # 构建 WHERE 条件
        where_conditions = ["(a.hidden = FALSE OR a.hidden IS NULL)"]
        params = []

        if status_filter:
            where_conditions.append("a.status = %s")
            params.append(status_filter)

        if stage_filter:
            where_conditions.append("a.stage = %s")
            params.append(stage_filter)

        where_clause = " AND ".join(where_conditions)

        sql = f"""
            SELECT
                a.id,
                a.expression,
                a.description,
                a.grade,
                a.status,
                a.stage,
                a.date_created,
                a.date_submitted,
                a.date_modified,
                a.synced_at,
                a.operator_count,
                p_is.sharpe as is_sharpe,
                p_is.fitness as is_fitness,
                p_is.turnover as is_turnover,
                p_is.returns as is_returns,
                p_is.drawdown as is_drawdown,
                p_os.sharpe as os_sharpe,
                p_os.fitness as os_fitness,
                p_os.turnover as os_turnover,
                COUNT(CASE WHEN c.result = 'PASS' AND c.stage = 'IS' THEN 1 END) as is_checks_pass,
                COUNT(CASE WHEN c.result = 'FAIL' AND c.stage = 'IS' THEN 1 END) as is_checks_fail,
                COUNT(CASE WHEN c.result = 'PASS' AND c.stage = 'OS' THEN 1 END) as os_checks_pass,
                COUNT(CASE WHEN c.result = 'FAIL' AND c.stage = 'OS' THEN 1 END) as os_checks_fail
            FROM alpha a
            LEFT JOIN alpha_performance p_is ON a.id = p_is.alpha_id AND p_is.stage = 'IS'
            LEFT JOIN alpha_performance p_os ON a.id = p_os.alpha_id AND p_os.stage = 'OS'
            LEFT JOIN alpha_checks c ON a.id = c.alpha_id
            WHERE {where_clause}
            GROUP BY a.id
            ORDER BY {order_clause}
            LIMIT %s
        """

        params.append(limit)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.fetchall()

    def get_alpha_detail(self, alpha_id: str) -> Optional[Dict]:
        """
        获取 Alpha 详情

        Args:
            alpha_id: Alpha ID

        Returns:
            包含主表、设置、性能指标、检查结果的完整信息
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 1. 主表信息
            cursor.execute("SELECT * FROM alpha WHERE id = %s", (alpha_id,))
            alpha = cursor.fetchone()
            if not alpha:
                return None

            # 2. 设置信息
            cursor.execute("SELECT * FROM alpha_settings WHERE alpha_id = %s", (alpha_id,))
            alpha['settings'] = cursor.fetchone()

            # 3. 性能指标（各阶段）
            cursor.execute(
                "SELECT * FROM alpha_performance WHERE alpha_id = %s ORDER BY stage",
                (alpha_id,)
            )
            performances = cursor.fetchall()
            alpha['performances'] = {p['stage']: p for p in performances}

            # 4. 检查结果
            cursor.execute(
                "SELECT * FROM alpha_checks WHERE alpha_id = %s ORDER BY stage, check_name",
                (alpha_id,)
            )
            alpha['checks'] = cursor.fetchall()

            # 5. 参赛信息
            cursor.execute("SELECT * FROM alpha_competitions WHERE alpha_id = %s", (alpha_id,))
            alpha['competitions'] = cursor.fetchall()

            # 6. 团队信息
            cursor.execute("SELECT * FROM alpha_team WHERE alpha_id = %s", (alpha_id,))
            alpha['team'] = cursor.fetchone()

            # 7. 分类信息
            cursor.execute("SELECT * FROM alpha_classifications WHERE alpha_id = %s", (alpha_id,))
            alpha['classifications'] = cursor.fetchall()

            return alpha

    def get_last_created_time(self) -> Optional[datetime]:
        """获取数据库中最新的 Alpha 创建时间"""
        sql = "SELECT MAX(date_created) as max_date FROM alpha"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            result = cursor.fetchone()
            return result.get('max_date') if result else None

    def get_last_sync_time(self) -> Optional[datetime]:
        """获取最后一次同步时间"""
        sql = "SELECT MAX(synced_at) as last_sync FROM alpha"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            result = cursor.fetchone()
            return result.get('last_sync') if result else None

    def get_alpha_count(self) -> int:
        """获取 Alpha 总数"""
        sql = "SELECT COUNT(*) as cnt FROM alpha"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            result = cursor.fetchone()
            return result.get('cnt', 0) if result else 0

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 总数
            cursor.execute("SELECT COUNT(*) as cnt FROM alpha")
            total = cursor.fetchone()['cnt']

            # 按状态统计
            cursor.execute("SELECT status, COUNT(*) as cnt FROM alpha GROUP BY status")
            by_status = {row['status']: row['cnt'] for row in cursor.fetchall()}

            # 按阶段统计
            cursor.execute("SELECT stage, COUNT(*) as cnt FROM alpha GROUP BY stage")
            by_stage = {row['stage']: row['cnt'] for row in cursor.fetchall()}

            # 按等级统计
            cursor.execute("SELECT grade, COUNT(*) as cnt FROM alpha WHERE grade IS NOT NULL GROUP BY grade")
            by_grade = {row['grade']: row['cnt'] for row in cursor.fetchall()}

            # 最近同步日志
            cursor.execute("SELECT * FROM alpha_sync_log ORDER BY started_at DESC LIMIT 1")
            last_sync_log = cursor.fetchone()

            return {
                'total': total,
                'by_status': by_status,
                'by_stage': by_stage,
                'by_grade': by_grade,
                'last_sync_log': last_sync_log
            }

    def get_optimizable_alphas(self, limit: int = 50) -> List[Dict]:
        """
        获取可优化的 Alpha 列表（IS 检查通过 6 项，失败 1 项）

        筛选条件：
        - status = 'UNSUBMITTED'
        - IS 检查项：6 项 PASS，1 项 FAIL
        - 未隐藏
        - 按创建时间倒序排列

        Args:
            limit: 返回数量上限

        Returns:
            可优化的 Alpha 列表
        """
        sql = """
            SELECT
                a.id,
                a.expression,
                a.grade,
                a.status,
                a.stage,
                a.date_created,
                p.sharpe as is_sharpe,
                p.fitness as is_fitness,
                p.turnover as is_turnover,
                p.returns as is_returns,
                COUNT(CASE WHEN c.result = 'PASS' AND c.stage = 'IS' THEN 1 END) as is_checks_pass,
                COUNT(CASE WHEN c.result = 'FAIL' AND c.stage = 'IS' THEN 1 END) as is_checks_fail
            FROM alpha a
            LEFT JOIN alpha_performance p ON a.id = p.alpha_id AND p.stage = 'IS'
            LEFT JOIN alpha_checks c ON a.id = c.alpha_id
            WHERE a.status = 'UNSUBMITTED'
              AND (a.hidden = FALSE OR a.hidden IS NULL)
            GROUP BY a.id
            HAVING is_checks_pass = 6 AND is_checks_fail = 1
            ORDER BY is_sharpe DESC, a.date_created DESC
            LIMIT %s
        """

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (limit,))
            return cursor.fetchall()

    def get_alpha_checks_detail(self, alpha_id: str) -> List[Dict]:
        """
        获取 Alpha 的检查项详情

        Args:
            alpha_id: Alpha ID

        Returns:
            检查项列表
        """
        sql = """
            SELECT
                check_name,
                stage,
                result,
                limit_value,
                actual_value
            FROM alpha_checks
            WHERE alpha_id = %s AND stage = 'IS'
            ORDER BY check_name
        """

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (alpha_id,))
            return cursor.fetchall()
