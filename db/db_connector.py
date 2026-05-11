"""
数据库连接模块

提供 MySQL 数据库连接和基础操作
"""
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from typing import Generator, Optional, List, Dict, Any
import logging

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


class MySQLConnector:
    """MySQL 数据库连接器"""

    def __init__(self, config: dict):
        """
        初始化数据库连接器

        Args:
            config: 数据库配置字典
                - host: 主机地址
                - port: 端口
                - user: 用户名
                - password: 密码
                - database: 数据库名
                - charset: 字符集（默认 utf8mb4）
        """
        self.config = {
            'host': config.get('host', 'localhost'),
            'port': config.get('port', 3306),
            'user': config.get('user', 'root'),
            'password': config.get('password', ''),
            'database': config.get('database', 'worldquant_alpha'),
            'charset': config.get('charset', 'utf8mb4'),
            'cursorclass': DictCursor,
            'autocommit': False
        }
        self._connected = False

    @contextmanager
    def get_connection(self) -> Generator:
        """
        获取数据库连接（上下文管理器）

        Yields:
            pymysql.Connection: 数据库连接对象
        """
        conn = pymysql.connect(**self.config)
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库错误: {e}")
            raise
        finally:
            conn.close()

    def execute(self, sql: str, params: tuple = None) -> int:
        """
        执行单条 SQL

        Args:
            sql: SQL 语句
            params: 参数元组

        Returns:
            影响的行数
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                affected = cursor.execute(sql, params)
                conn.commit()
                return affected

    def execute_many(self, sql: str, params_list: List[tuple]) -> int:
        """
        批量执行 SQL

        Args:
            sql: SQL 语句
            params_list: 参数列表

        Returns:
            影响的行数
        """
        if not params_list:
            return 0
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                affected = cursor.executemany(sql, params_list)
                conn.commit()
                return affected

    def query_one(self, sql: str, params: tuple = None) -> Optional[Dict]:
        """
        查询单条记录

        Args:
            sql: SQL 语句
            params: 参数元组

        Returns:
            查询结果字典，无结果返回 None
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()

    def query_all(self, sql: str, params: tuple = None) -> List[Dict]:
        """
        查询多条记录

        Args:
            sql: SQL 语句
            params: 参数元组

        Returns:
            查询结果列表
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

    def insert(self, table: str, data: Dict) -> int:
        """
        插入记录

        Args:
            table: 表名
            data: 数据字典

        Returns:
            影响的行数
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return self.execute(sql, tuple(data.values()))

    def insert_ignore(self, table: str, data: Dict) -> int:
        """
        插入记录（忽略重复）

        Args:
            table: 表名
            data: 数据字典

        Returns:
            影响的行数
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        sql = f"INSERT IGNORE INTO {table} ({columns}) VALUES ({placeholders})"
        return self.execute(sql, tuple(data.values()))

    def upsert(self, table: str, data: Dict, key_column: str = 'id') -> int:
        """
        插入或更新记录（ON DUPLICATE KEY UPDATE）

        Args:
            table: 表名
            data: 数据字典
            key_column: 主键列名（更新时排除）

        Returns:
            影响的行数
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        updates = ', '.join([f"{k}=VALUES({k})" for k in data.keys() if k != key_column])
        sql = f"""
            INSERT INTO {table} ({columns}) VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {updates}
        """
        return self.execute(sql, tuple(data.values()))

    def delete(self, table: str, where: str, params: tuple = None) -> int:
        """
        删除记录

        Args:
            table: 表名
            where: WHERE 条件（不含 WHERE 关键字）
            params: 参数元组

        Returns:
            影响的行数
        """
        sql = f"DELETE FROM {table} WHERE {where}"
        return self.execute(sql, params)

    def table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在

        Args:
            table_name: 表名

        Returns:
            是否存在
        """
        sql = """
            SELECT COUNT(*) as cnt
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
        """
        result = self.query_one(sql, (self.config['database'], table_name))
        return result['cnt'] > 0 if result else False

    def create_database_if_not_exists(self):
        """
        创建数据库（如果不存在）
        """
        # 连接到 MySQL 服务器（不指定数据库）
        config = self.config.copy()
        del config['database']

        conn = pymysql.connect(**config)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS {self.config['database']} "
                    f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            conn.commit()
            logger.info(f"数据库 {self.config['database']} 已就绪")
        finally:
            conn.close()

    def test_connection(self) -> bool:
        """
        测试数据库连接

        Returns:
            连接是否成功
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
