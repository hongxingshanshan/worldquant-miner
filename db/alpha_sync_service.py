"""
Alpha 数据同步服务

从 WorldQuant Brain API 同步 Alpha 数据到 MySQL 数据库
"""
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Optional
from datetime import datetime
import json
import os
import logging

from .db_connector import MySQLConnector

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


class AlphaSyncService:
    """Alpha 数据同步服务"""

    def __init__(self, credentials_path: str, db_config: dict):
        """
        初始化同步服务

        Args:
            credentials_path: 凭证文件路径
            db_config: 数据库配置
        """
        # 初始化 API 客户端
        self.sess = requests.Session()
        self._setup_auth(credentials_path)

        # 初始化数据库连接
        self.db = MySQLConnector(db_config)

        # 同步统计
        self.stats = {
            'total': 0,
            'new': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }

    def _setup_auth(self, credentials_path: str):
        """设置认证"""
        with open(credentials_path, 'r') as f:
            creds = json.load(f)
        username, password = creds
        self.sess.auth = HTTPBasicAuth(username, password)
        self.sess.headers.update({'Content-Type': 'application/json'})

        # 登录获取 session
        resp = self.sess.post('https://api.worldquantbrain.com/authentication')
        if resp.status_code not in [200, 201]:
            raise Exception(f"认证失败: {resp.text}")
        logger.info("WorldQuant API 认证成功")

    def init_database(self):
        """初始化数据库（创建表）"""
        # 创建数据库
        self.db.create_database_if_not_exists()

        # 读取建表 SQL
        sql_file = os.path.join(os.path.dirname(__file__), 'migrations', '001_init.sql')
        if os.path.exists(sql_file):
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # 正确解析 SQL 语句（处理多行语句和注释）
            statements = []
            current_stmt = []

            for line in sql_content.split('\n'):
                # 跳过纯注释行
                if line.strip().startswith('--'):
                    continue
                current_stmt.append(line)
                if ';' in line:
                    stmt = '\n'.join(current_stmt).strip()
                    if stmt and stmt != ';':
                        statements.append(stmt.rstrip(';'))
                    current_stmt = []

            # 执行每条语句
            for stmt in statements:
                try:
                    self.db.execute(stmt)
                except Exception as e:
                    err_msg = str(e).lower()
                    # 忽略表已存在和索引已存在的错误
                    if 'already exists' not in err_msg and 'duplicate key name' not in err_msg:
                        logger.warning(f"执行 SQL 失败: {e}")

            logger.info("数据库表初始化完成")
        else:
            logger.warning(f"SQL 文件不存在: {sql_file}")

    def sync_all(self, batch_size: int = 50) -> Dict:
        """
        全量同步 Alpha 数据

        Args:
            batch_size: 每批次获取数量

        Returns:
            同步统计信息
        """
        logger.info("开始全量同步 Alpha 数据")
        start_time = datetime.now()
        self.stats = {'total': 0, 'new': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

        offset = 0
        while True:
            try:
                # 获取一批 Alpha
                alphas = self._fetch_alphas(limit=batch_size, offset=offset)
                if not alphas:
                    break

                # 保存到数据库
                for alpha in alphas:
                    alpha_id = alpha.get('id')
                    existing = self.db.query_one(
                        "SELECT id FROM alpha WHERE id = %s", (alpha_id,)
                    )
                    self._save_alpha(alpha)
                    if existing:
                        self.stats['updated'] += 1
                    else:
                        self.stats['new'] += 1

                self.stats['total'] += len(alphas)
                logger.info(f"已同步 {self.stats['total']} 条 Alpha")

                offset += batch_size

            except Exception as e:
                logger.error(f"同步错误 (offset={offset}): {e}")
                self.stats['errors'] += 1
                break

        # 记录同步日志
        self._log_sync('FULL', start_time)

        logger.info(f"同步完成: {self.stats}")
        return self.stats

    def sync_incremental(self, since: datetime = None, batch_size: int = 50) -> Dict:
        """
        增量同步（按创建时间）

        遍历按创建时间倒序排列的 Alpha，遇到已存在的就停止

        Args:
            since: 上次同步时间（未使用，保留兼容性）
            batch_size: 每批次获取数量

        Returns:
            同步统计信息
        """
        logger.info("开始增量同步")
        start_time = datetime.now()
        self.stats = {'total': 0, 'new': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

        offset = 0
        should_stop = False
        while not should_stop:
            try:
                alphas = self._fetch_alphas(limit=batch_size, offset=offset, order='-dateCreated')
                if not alphas:
                    break

                for alpha in alphas:
                    alpha_id = alpha.get('id')
                    # 检查是否已存在
                    existing = self.db.query_one(
                        "SELECT id FROM alpha WHERE id = %s", (alpha_id,)
                    )
                    if existing:
                        # 已存在，更新数据
                        self._save_alpha(alpha)
                        self.stats['updated'] += 1
                        # 由于按创建时间倒序，遇到已存在的说明后续都已同步
                        should_stop = True
                    else:
                        # 新数据
                        self._save_alpha(alpha)
                        self.stats['new'] += 1

                self.stats['total'] += len(alphas)
                if not should_stop:
                    offset += batch_size

            except Exception as e:
                logger.error(f"增量同步错误: {e}")
                self.stats['errors'] += 1
                break

        self._log_sync('INCREMENTAL', start_time)
        return self.stats

    def _fetch_alphas(self, limit: int = 100, offset: int = 0, order: str = '-dateCreated') -> List[Dict]:
        """从 API 获取 Alpha 列表"""
        params = {
            'limit': limit,
            'offset': offset,
            'order': order,
            'hidden': 'false'
        }

        resp = self.sess.get(
            'https://api.worldquantbrain.com/users/self/alphas',
            params=params,
            timeout=60
        )

        if resp.status_code != 200:
            logger.error(f"API 错误: {resp.status_code} - {resp.text[:200]}")
            return []

        data = resp.json()
        return data.get('results', [])

    def _save_alpha(self, alpha: Dict):
        """保存单个 Alpha 到数据库"""
        alpha_id = alpha.get('id')

        try:
            # 1. 保存主表
            self._save_alpha_main(alpha)

            # 2. 保存设置
            settings = alpha.get('settings') or {}
            self._save_alpha_settings(alpha_id, settings)

            # 3. 保存性能指标（先删除该 Alpha 的所有旧数据，再插入新数据）
            self.db.delete('alpha_performance', 'alpha_id = %s', (alpha_id,))
            for stage in ['is', 'os', 'train', 'test', 'prod']:
                perf = alpha.get(stage)
                if perf:
                    self._save_alpha_performance(alpha_id, stage, perf)

            # 4. 保存检查结果（先删除该 Alpha 的所有旧数据，再插入新数据）
            self.db.delete('alpha_checks', 'alpha_id = %s', (alpha_id,))
            for stage in ['is', 'os']:
                stage_data = alpha.get(stage) or {}
                checks = stage_data.get('checks') or []
                if checks:
                    self._save_alpha_checks(alpha_id, stage, checks)

            # 5. 保存参赛信息
            competitions = alpha.get('competitions')
            if competitions:
                self._save_alpha_competitions(alpha_id, competitions)

            # 6. 保存团队信息
            team = alpha.get('team')
            if team:
                self._save_alpha_team(alpha_id, team)

            # 7. 保存分类信息
            classifications = alpha.get('classifications')
            if classifications:
                self._save_alpha_classifications(alpha_id, classifications)

        except Exception as e:
            logger.error(f"保存 Alpha {alpha_id} 失败: {e}")
            self.stats['errors'] += 1

    def _save_alpha_main(self, alpha: Dict):
        """保存 Alpha 主表"""
        regular = alpha.get('regular') or {}
        data = {
            'id': alpha.get('id'),
            'type': alpha.get('type'),
            'author': alpha.get('author'),
            'expression': regular.get('code'),
            'description': regular.get('description'),
            'operator_count': regular.get('operatorCount'),
            'date_created': self._parse_datetime(alpha.get('dateCreated')),
            'date_submitted': self._parse_datetime(alpha.get('dateSubmitted')),
            'date_modified': self._parse_datetime(alpha.get('dateModified')),
            'grade': alpha.get('grade'),
            'stage': alpha.get('stage'),
            'status': alpha.get('status'),
            'origin': alpha.get('origin'),
            'favorite': alpha.get('favorite', False),
            'hidden': alpha.get('hidden', False),
            'tags': json.dumps(alpha.get('tags', [])) if alpha.get('tags') else None,
            'synced_at': datetime.now()
        }
        self.db.upsert('alpha', data, 'id')

    def _save_alpha_settings(self, alpha_id: str, settings: Dict):
        """保存 Alpha 设置"""
        if not settings:
            return

        data = {
            'alpha_id': alpha_id,
            'instrument_type': settings.get('instrumentType'),
            'region': settings.get('region'),
            'universe': settings.get('universe'),
            'delay': settings.get('delay'),
            'decay': settings.get('decay'),
            'neutralization': settings.get('neutralization'),
            'truncation': settings.get('truncation'),
            'pasteurization': settings.get('pasteurization'),
            'unit_handling': settings.get('unitHandling'),
            'nan_handling': settings.get('nanHandling'),
            'max_trade': settings.get('maxTrade'),
            'max_position': settings.get('maxPosition'),
            'language': settings.get('language'),
            'visualization': settings.get('visualization'),
            'start_date': settings.get('startDate'),
            'end_date': settings.get('endDate')
        }
        self.db.upsert('alpha_settings', data, 'alpha_id')

    def _save_alpha_performance(self, alpha_id: str, stage: str, perf: Dict):
        """保存性能指标"""
        if not perf:
            return

        data = {
            'alpha_id': alpha_id,
            'stage': stage.upper(),
            'pnl': perf.get('pnl'),
            'book_size': perf.get('bookSize'),
            'long_count': perf.get('longCount'),
            'short_count': perf.get('shortCount'),
            'turnover': perf.get('turnover'),
            'returns': perf.get('returns'),
            'drawdown': perf.get('drawdown'),
            'margin': perf.get('margin'),
            'sharpe': perf.get('sharpe'),
            'fitness': perf.get('fitness'),
            'self_correlation': perf.get('selfCorrelation'),
            'prod_correlation': perf.get('prodCorrelation'),
            'start_date': perf.get('startDate'),
            'os_is_sharpe_ratio': perf.get('osISSharpeRatio'),
            'pre_close_sharpe_ratio': perf.get('preCloseSharpeRatio')
        }
        self.db.insert('alpha_performance', data)

    def _save_alpha_checks(self, alpha_id: str, stage: str, checks: List[Dict]):
        """保存检查结果"""
        # 先删除旧记录
        self.db.delete('alpha_checks', 'alpha_id = %s', (alpha_id))

        for check in checks:
            data = {
                'alpha_id': alpha_id,
                'stage': stage.upper(),
                'check_name': check.get('name'),
                'result': check.get('result'),
                'limit_value': check.get('limit'),
                'actual_value': check.get('value')
            }
            self.db.insert('alpha_checks', data)

    def _save_alpha_competitions(self, alpha_id: str, competitions: List[Dict]):
        """保存参赛信息"""
        for comp in competitions:
            data = {
                'alpha_id': alpha_id,
                'competition_id': comp.get('id'),
                'competition_name': comp.get('name')
            }
            self.db.insert_ignore('alpha_competitions', data)

    def _save_alpha_team(self, alpha_id: str, team: Dict):
        """保存团队信息"""
        data = {
            'alpha_id': alpha_id,
            'team_id': team.get('id'),
            'team_type': team.get('type'),
            'team_name': team.get('name'),
            'university': team.get('university')
        }
        self.db.upsert('alpha_team', data, 'alpha_id')

    def _save_alpha_classifications(self, alpha_id: str, classifications: List[Dict]):
        """保存分类信息"""
        for cls in classifications:
            data = {
                'alpha_id': alpha_id,
                'classification_id': cls.get('id'),
                'classification_name': cls.get('name')
            }
            self.db.insert_ignore('alpha_classifications', data)

    def _log_sync(self, sync_type: str, started_at: datetime):
        """记录同步日志"""
        data = {
            'sync_type': sync_type,
            'total_count': self.stats['total'],
            'new_count': self.stats['new'],
            'update_count': self.stats['updated'],
            'error_count': self.stats['errors'],
            'started_at': started_at,
            'finished_at': datetime.now()
        }
        self.db.insert('alpha_sync_log', data)

    @staticmethod
    def _parse_datetime(dt_str: str) -> Optional[datetime]:
        """解析日期时间字符串"""
        if not dt_str:
            return None
        try:
            # ISO 8601 格式: 2026-05-09T05:17:34-04:00
            from dateutil import parser
            return parser.parse(dt_str)
        except:
            # 简单格式解析
            try:
                return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            except:
                return None

    def get_alpha_by_id(self, alpha_id: str) -> Optional[Dict]:
        """
        根据 ID 获取 Alpha 详情

        Args:
            alpha_id: Alpha ID

        Returns:
            Alpha 详情字典
        """
        alpha = self.db.query_one(
            "SELECT * FROM alpha WHERE id = %s", (alpha_id,)
        )
        if not alpha:
            return None

        # 获取设置
        settings = self.db.query_one(
            "SELECT * FROM alpha_settings WHERE alpha_id = %s", (alpha_id,)
        )
        alpha['settings'] = settings

        # 获取性能指标
        performances = self.db.query_all(
            "SELECT * FROM alpha_performance WHERE alpha_id = %s", (alpha_id,)
        )
        alpha['performances'] = {p['stage']: p for p in performances}

        # 获取检查结果
        checks = self.db.query_all(
            "SELECT * FROM alpha_checks WHERE alpha_id = %s", (alpha_id,)
        )
        alpha['checks'] = checks

        return alpha

    def get_top_alphas(self, limit: int = 20, stage: str = 'IS', order_by: str = 'fitness') -> List[Dict]:
        """
        获取排名靠前的 Alpha

        Args:
            limit: 返回数量
            stage: 阶段
            order_by: 排序字段

        Returns:
            Alpha 列表
        """
        valid_order = ['fitness', 'sharpe', 'returns', 'turnover']
        if order_by not in valid_order:
            order_by = 'fitness'

        sql = f"""
            SELECT a.id, a.expression, a.grade, a.status, a.date_submitted,
                   p.sharpe, p.fitness, p.turnover, p.returns
            FROM alpha a
            JOIN alpha_performance p ON a.id = p.alpha_id
            WHERE p.stage = %s
            ORDER BY p.{order_by} DESC
            LIMIT %s
        """
        return self.db.query_all(sql, (stage, limit))
