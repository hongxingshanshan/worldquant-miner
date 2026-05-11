# WorldQuant Alpha 数据持久化方案

## 一、概述

本文档描述将 WorldQuant Brain API 的 Alpha 数据持久化到 MySQL 数据库的完整方案。

### 1.1 数据来源

- **API 端点**: `https://api.worldquantbrain.com/users/self/alphas`
- **认证方式**: HTTP Basic Auth
- **数据量**: 约 1500+ 条 Alpha 记录

### 1.2 设计目标

1. 完整存储 Alpha 数据，支持历史追溯
2. 支持增量同步，减少 API 调用
3. 支持多维度查询（状态、等级、性能指标等）
4. 数据结构可扩展，适应 API 变化

---

## 二、API 数据结构分析

### 2.1 顶层字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| id | VARCHAR(20) | Alpha 唯一标识（8位字符串，含大小写字母和数字） | "gJR0gwjv", "6XaA2NbJ", "rKJ8Aqmo" |
| type | VARCHAR(20) | Alpha 类型 | "REGULAR" |
| author | VARCHAR(50) | 作者 ID | "XX93980" |
| dateCreated | DATETIME | 创建时间 | "2026-05-09T05:17:34-04:00" |
| dateSubmitted | DATETIME | 提交时间 | "2026-05-09T05:18:46-04:00" |
| dateModified | DATETIME | 修改时间 | "2026-05-09T05:17:34-04:00" |
| name | VARCHAR(255) | 名称（可为空） | null |
| favorite | BOOLEAN | 是否收藏 | false |
| hidden | BOOLEAN | 是否隐藏 | false |
| grade | VARCHAR(20) | 等级 | "AVERAGE", "INFERIOR", "EXCELLENT" |
| stage | VARCHAR(20) | 阶段 | "IS", "OS", "TRAIN", "TEST", "PROD" |
| status | VARCHAR(20) | 状态 | "ACTIVE", "UNSUBMITTED", "CORRELATED" |
| origin | VARCHAR(50) | 来源 | "PLATFORM" |

### 2.2 嵌套对象

#### 2.2.1 settings（模拟设置）

| 字段 | 类型 | 说明 | 示例值 |
|------|------|------|--------|
| instrumentType | VARCHAR(20) | 工具类型 | "EQUITY" |
| region | VARCHAR(20) | 区域 | "USA" |
| universe | VARCHAR(20) | 股票池 | "TOP3000" |
| delay | INT | 延迟天数 | 1 |
| decay | INT | 衰减 | 0 |
| neutralization | VARCHAR(50) | 中性化 | "INDUSTRY" |
| truncation | DOUBLE | 截断 | 0.08 |
| pasteurization | VARCHAR(10) | 巴氏消毒 | "ON" |
| unitHandling | VARCHAR(20) | 单位处理 | "VERIFY" |
| nanHandling | VARCHAR(10) | NaN 处理 | "OFF" |
| maxTrade | VARCHAR(10) | 最大交易 | "OFF" |
| maxPosition | VARCHAR(10) | 最大持仓 | "OFF" |
| language | VARCHAR(20) | 语言 | "FASTEXPR" |
| visualization | BOOLEAN | 可视化 | false |
| startDate | DATE | 开始日期 | "2019-01-01" |
| endDate | DATE | 结束日期 | "2023-12-31" |

#### 2.2.2 regular（Alpha 表达式）

| 字段 | 类型 | 说明 |
|------|------|------|
| code | TEXT | Alpha 表达式 |
| description | TEXT | 描述（可为空） |
| operatorCount | INT | 操作符数量 |

#### 2.2.3 is/os/train/test/prod（性能指标）

| 字段 | 类型 | 说明 | 示例值 |
|------|------|------|--------|
| pnl | BIGINT | 盈亏 | 5482984 |
| bookSize | BIGINT | 账面规模 | 20000000 |
| longCount | INT | 做多数量 | 1480 |
| shortCount | INT | 做空数量 | 1484 |
| turnover | DOUBLE | 换手率 | 0.2293 |
| returns | DOUBLE | 收益率 | 0.1108 |
| drawdown | DOUBLE | 回撤 | 0.0526 |
| margin | DOUBLE | 保证金 | 0.000967 |
| sharpe | DOUBLE | 夏普比率 | 1.88 |
| fitness | DOUBLE | 适应度 | 1.31 |
| selfCorrelation | DOUBLE | 自相关 | 0.8111 |
| prodCorrelation | DOUBLE | 产品相关 | 0.0 |

#### 2.2.4 checks（检查结果）

| 字段 | 类型 | 说明 | 示例值 |
|------|------|------|--------|
| name | VARCHAR(50) | 检查项名称 | "LOW_SHARPE", "LOW_FITNESS" |
| result | VARCHAR(20) | 结果：PASS/FAIL/PENDING | "PASS" |
| limit | DOUBLE | 阈值（整数或浮点数） | 1.25 |
| value | DOUBLE | 实际值（整数或浮点数） | 1.88 |

#### 2.2.5 competitions（参赛信息）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(50) | 比赛 ID |
| name | VARCHAR(255) | 比赛名称 |

#### 2.2.6 team（团队信息）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(50) | 团队 ID |
| type | VARCHAR(50) | 团队类型 |
| name | VARCHAR(255) | 团队名称 |
| university | VARCHAR(100) | 大学 |

### 2.3 状态分布示例

```
状态: {'ACTIVE': 7, 'UNSUBMITTED': 43}
等级: {'AVERAGE': 7, 'INFERIOR': 42, 'UNKNOWN': 1}
阶段: {'OS': 7, 'IS': 43}
```

---

## 三、数据库表结构设计

### 3.1 ER 图

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   alpha     │────▶│  alpha_settings  │     │ alpha_performance│
│  (主表)     │     └──────────────────┘     └──────────────────┘
└─────────────┘              │                        │
      │                      │                        │
      │              ┌───────┴───────┐        ┌───────┴───────┐
      │              │               │        │               │
      ▼              ▼               ▼        ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│alpha_checks │ │alpha_compet-│ │ alpha_team  │ │sync_log     │
│             │ │itions       │ │             │ │             │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### 3.2 建表 SQL

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS worldquant_alpha
DEFAULT CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE worldquant_alpha;

-- =====================================================
-- 1. Alpha 主表
-- =====================================================
CREATE TABLE alpha (
    -- 主键：8位字符串，如 gJR0gwjv, 6XaA2NbJ, rKJ8Aqmo
    id VARCHAR(20) PRIMARY KEY COMMENT 'Alpha 唯一标识（8位字符串，如 gJR0gwjv）',
    type VARCHAR(20) DEFAULT 'REGULAR' COMMENT '类型',
    author VARCHAR(50) COMMENT '作者 ID',

    -- Alpha 表达式
    expression TEXT COMMENT 'Alpha 公式',
    description TEXT COMMENT '描述',
    operator_count INT COMMENT '操作符数量',

    -- 时间字段
    date_created DATETIME COMMENT '创建时间',
    date_submitted DATETIME COMMENT '提交时间',
    date_modified DATETIME COMMENT '修改时间',

    -- 状态字段
    grade VARCHAR(20) COMMENT '等级: AVERAGE, INFERIOR, EXCELLENT',
    stage VARCHAR(20) COMMENT '阶段: IS, OS, TRAIN, TEST, PROD',
    status VARCHAR(20) COMMENT '状态: ACTIVE, UNSUBMITTED, CORRELATED',
    origin VARCHAR(50) COMMENT '来源',

    -- 标记
    favorite BOOLEAN DEFAULT FALSE COMMENT '是否收藏',
    hidden BOOLEAN DEFAULT FALSE COMMENT '是否隐藏',

    -- 同步字段
    synced_at DATETIME COMMENT '最后同步时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_author (author),
    INDEX idx_grade (grade),
    INDEX idx_stage (stage),
    INDEX idx_status (status),
    INDEX idx_date_submitted (date_submitted),
    INDEX idx_synced_at (synced_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Alpha 主表';

-- =====================================================
-- 2. Alpha 设置表
-- =====================================================
CREATE TABLE alpha_settings (
    -- 外键关联到 alpha 表的 id（8位字符串）
    alpha_id VARCHAR(20) PRIMARY KEY COMMENT 'Alpha ID（如 gJR0gwjv）',

    -- 模拟设置
    instrument_type VARCHAR(20) DEFAULT 'EQUITY' COMMENT '工具类型',
    region VARCHAR(20) DEFAULT 'USA' COMMENT '区域',
    universe VARCHAR(20) DEFAULT 'TOP3000' COMMENT '股票池',
    delay INT DEFAULT 1 COMMENT '延迟天数',
    decay INT DEFAULT 0 COMMENT '衰减（整数）',
    neutralization VARCHAR(50) DEFAULT 'INDUSTRY' COMMENT '中性化',
    truncation DECIMAL(10,4) DEFAULT 0.08 COMMENT '截断（使用 DECIMAL）',
    pasteurization VARCHAR(10) DEFAULT 'ON' COMMENT '巴氏消毒',
    unit_handling VARCHAR(20) DEFAULT 'VERIFY' COMMENT '单位处理',
    nan_handling VARCHAR(10) DEFAULT 'OFF' COMMENT 'NaN 处理',
    max_trade VARCHAR(10) DEFAULT 'OFF' COMMENT '最大交易',
    max_position VARCHAR(10) DEFAULT 'OFF' COMMENT '最大持仓',
    language VARCHAR(20) DEFAULT 'FASTEXPR' COMMENT '语言',
    visualization BOOLEAN DEFAULT FALSE COMMENT '可视化',
    start_date DATE COMMENT '开始日期',
    end_date DATE COMMENT '结束日期',

    FOREIGN KEY (alpha_id) REFERENCES alpha(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Alpha 设置表';

-- =====================================================
-- 3. Alpha 性能指标表
-- =====================================================
CREATE TABLE alpha_performance (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    -- 外键：Alpha ID（8位字符串）
    alpha_id VARCHAR(20) COMMENT 'Alpha ID（如 gJR0gwjv）',
    stage VARCHAR(20) COMMENT '阶段: IS, OS, TRAIN, TEST, PROD',

    -- 性能指标（使用 DECIMAL 保证金融计算精度）
    pnl BIGINT COMMENT '盈亏（整数，如 5482984）',
    book_size BIGINT COMMENT '账面规模（整数，如 20000000）',
    long_count INT COMMENT '做多数量',
    short_count INT COMMENT '做空数量',
    turnover DECIMAL(12,6) COMMENT '换手率（如 0.2293）',
    returns DECIMAL(12,6) COMMENT '收益率（如 0.1108）',
    drawdown DECIMAL(12,6) COMMENT '回撤（如 0.0526）',
    margin DECIMAL(15,10) COMMENT '保证金（如 0.000967）',
    sharpe DECIMAL(10,4) COMMENT '夏普比率（如 1.88）',
    fitness DECIMAL(10,4) COMMENT '适应度（如 1.31）',
    self_correlation DECIMAL(10,6) COMMENT '自相关（如 0.8111）',
    prod_correlation DECIMAL(10,6) COMMENT '产品相关（如 0.0）',
    start_date DATE COMMENT '开始日期',

    -- OS 特有字段
    os_is_sharpe_ratio DECIMAL(10,4) COMMENT 'OS-IS 夏普比率',
    pre_close_sharpe_ratio DECIMAL(10,4) COMMENT '预收盘夏普比率',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_alpha_stage (alpha_id, stage),
    FOREIGN KEY (alpha_id) REFERENCES alpha(id) ON DELETE CASCADE,
    INDEX idx_stage (stage),
    INDEX idx_sharpe (sharpe),
    INDEX idx_fitness (fitness),
    INDEX idx_turnover (turnover)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Alpha 性能指标表';

-- =====================================================
-- 4. Alpha 检查结果表
-- =====================================================
CREATE TABLE alpha_checks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    -- 外键：Alpha ID（8位字符串）
    alpha_id VARCHAR(20) COMMENT 'Alpha ID（如 gJR0gwjv）',
    stage VARCHAR(20) COMMENT '阶段: IS, OS',
    check_name VARCHAR(50) COMMENT '检查项名称（如 LOW_SHARPE, LOW_FITNESS）',
    result VARCHAR(20) COMMENT '结果: PASS, FAIL, PENDING',
    limit_value DECIMAL(20,8) COMMENT '阈值（使用 DECIMAL 保证精度）',
    actual_value DECIMAL(20,8) COMMENT '实际值（使用 DECIMAL 保证精度）',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_alpha (alpha_id),
    INDEX idx_stage (stage),
    INDEX idx_result (result),
    INDEX idx_check_name (check_name),
    FOREIGN KEY (alpha_id) REFERENCES alpha(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Alpha 检查结果表';

-- =====================================================
-- 5. Alpha 参赛信息表
-- =====================================================
CREATE TABLE alpha_competitions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    -- 外键：Alpha ID（8位字符串）
    alpha_id VARCHAR(20) COMMENT 'Alpha ID（如 gJR0gwjv）',
    competition_id VARCHAR(50) COMMENT '比赛 ID',
    competition_name VARCHAR(255) COMMENT '比赛名称',

    UNIQUE KEY uk_alpha_comp (alpha_id, competition_id),
    INDEX idx_competition (competition_id),
    FOREIGN KEY (alpha_id) REFERENCES alpha(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Alpha 参赛信息表';

-- =====================================================
-- 6. Alpha 团队信息表
-- =====================================================
CREATE TABLE alpha_team (
    -- 外键：Alpha ID（8位字符串）
    alpha_id VARCHAR(20) PRIMARY KEY COMMENT 'Alpha ID（如 gJR0gwjv）',
    team_id VARCHAR(50) COMMENT '团队 ID',
    team_type VARCHAR(50) COMMENT '团队类型',
    team_name VARCHAR(255) COMMENT '团队名称',
    university VARCHAR(100) COMMENT '大学',

    FOREIGN KEY (alpha_id) REFERENCES alpha(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Alpha 团队信息表';

-- =====================================================
-- 7. 同步记录表
-- =====================================================
CREATE TABLE alpha_sync_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    sync_type VARCHAR(20) COMMENT '同步类型: FULL, INCREMENTAL',
    total_count INT COMMENT '总数量',
    new_count INT COMMENT '新增数量',
    update_count INT COMMENT '更新数量',
    error_count INT COMMENT '错误数量',
    started_at DATETIME COMMENT '开始时间',
    finished_at DATETIME COMMENT '结束时间',
    error_message TEXT COMMENT '错误信息',

    INDEX idx_sync_type (sync_type),
    INDEX idx_started_at (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='同步记录表';

-- =====================================================
-- 8. 分类信息表（可选，用于 classifications 字段）
-- =====================================================
CREATE TABLE alpha_classifications (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    -- 外键：Alpha ID（8位字符串）
    alpha_id VARCHAR(20) COMMENT 'Alpha ID（如 gJR0gwjv）',
    classification_id VARCHAR(100) COMMENT '分类 ID',
    classification_name VARCHAR(255) COMMENT '分类名称',

    INDEX idx_alpha (alpha_id),
    FOREIGN KEY (alpha_id) REFERENCES alpha(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Alpha 分类信息表';
```

---

## 四、持久化实现方案

### 4.1 架构设计

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│ WorldQuant API  │────▶│ AlphaSyncService │────▶│   MySQL     │
└─────────────────┘     └──────────────────┘     └─────────────┘
        │                       │
        │                       ▼
        │               ┌──────────────────┐
        │               │ 本地 JSON 缓存   │
        │               └──────────────────┘
        │
        ▼
┌─────────────────┐
│ credential.txt  │
└─────────────────┘
```

### 4.2 模块结构

```
generation_one/naive-ollama/
├── db/
│   ├── __init__.py
│   ├── db_connector.py      # 数据库连接
│   ├── models.py            # 数据模型
│   └── migrations/          # 数据库迁移脚本
│       └── 001_init.sql
├── alpha_sync_service.py    # 同步服务
└── config.json              # 配置文件（新增数据库配置）
```

### 4.3 配置扩展

在 `config.json` 中添加数据库配置：

```json
{
    "database": {
        "enabled": true,
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "your_password",
        "database": "worldquant_alpha",
        "charset": "utf8mb4"
    },
    "sync": {
        "enabled": true,
        "interval_minutes": 60,
        "batch_size": 100,
        "retry_count": 3
    }
}
```

### 4.4 核心代码实现

#### 4.4.1 数据库连接模块 (`db/db_connector.py`)

```python
"""
数据库连接模块
"""
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from typing import Generator, Optional
import logging

logger = logging.getLogger(__name__)


class MySQLConnector:
    """MySQL 数据库连接器"""

    def __init__(self, config: dict):
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
        self._pool = []

    @contextmanager
    def get_connection(self) -> Generator:
        """获取数据库连接（上下文管理器）"""
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
        """执行单条 SQL"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                affected = cursor.execute(sql, params)
                conn.commit()
                return affected

    def execute_many(self, sql: str, params_list: list) -> int:
        """批量执行 SQL"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                affected = cursor.executemany(sql, params_list)
                conn.commit()
                return affected

    def query_one(self, sql: str, params: tuple = None) -> Optional[dict]:
        """查询单条记录"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()

    def query_all(self, sql: str, params: tuple = None) -> list:
        """查询多条记录"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

    def insert_ignore(self, table: str, data: dict) -> int:
        """插入记录（忽略重复）"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        sql = f"INSERT IGNORE INTO {table} ({columns}) VALUES ({placeholders})"
        return self.execute(sql, tuple(data.values()))

    def upsert(self, table: str, data: dict, key_column: str = 'id') -> int:
        """插入或更新记录"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        updates = ', '.join([f"{k}=VALUES({k})" for k in data.keys() if k != key_column])
        sql = f"""
            INSERT INTO {table} ({columns}) VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {updates}
        """
        return self.execute(sql, tuple(data.values()))
```

#### 4.4.2 Alpha 同步服务 (`alpha_sync_service.py`)

```python
"""
Alpha 数据同步服务
"""
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Optional
from datetime import datetime
import json
import logging
from db.db_connector import MySQLConnector

logger = logging.getLogger(__name__)


class AlphaSyncService:
    """Alpha 数据同步服务"""

    def __init__(self, credentials_path: str, db_config: dict):
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

    def sync_all(self, batch_size: int = 100) -> Dict:
        """
        全量同步 Alpha 数据

        Args:
            batch_size: 每批次获取数量

        Returns:
            同步统计信息
        """
        logger.info("开始全量同步 Alpha 数据")
        start_time = datetime.now()
        self.stats = {'total': 0, 'new': 0, 'updated': 0, 'errors': 0}

        offset = 0
        while True:
            try:
                # 获取一批 Alpha
                alphas = self._fetch_alphas(limit=batch_size, offset=offset)
                if not alphas:
                    break

                # 保存到数据库
                for alpha in alphas:
                    self._save_alpha(alpha)

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

    def sync_incremental(self, since: datetime, batch_size: int = 100) -> Dict:
        """
        增量同步（按修改时间）

        Args:
            since: 上次同步时间
            batch_size: 每批次获取数量

        Returns:
            同步统计信息
        """
        logger.info(f"开始增量同步 (since={since})")
        start_time = datetime.now()
        self.stats = {'total': 0, 'new': 0, 'updated': 0, 'errors': 0}

        offset = 0
        while True:
            try:
                alphas = self._fetch_alphas(
                    limit=batch_size,
                    offset=offset,
                    modified_after=since
                )
                if not alphas:
                    break

                for alpha in alphas:
                    self._save_alpha(alpha)

                self.stats['total'] += len(alphas)
                offset += batch_size

            except Exception as e:
                logger.error(f"增量同步错误: {e}")
                self.stats['errors'] += 1
                break

        self._log_sync('INCREMENTAL', start_time)
        return self.stats

    def _fetch_alphas(self, limit: int = 100, offset: int = 0,
                      modified_after: datetime = None) -> List[Dict]:
        """从 API 获取 Alpha 列表"""
        params = {
            'limit': limit,
            'offset': offset,
            'order': '-dateModified',
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
            self._save_alpha_settings(alpha_id, alpha.get('settings', {}))

            # 3. 保存性能指标
            for stage in ['is', 'os', 'train', 'test', 'prod']:
                if alpha.get(stage):
                    self._save_alpha_performance(alpha_id, stage, alpha[stage])

            # 4. 保存检查结果
            for stage in ['is', 'os']:
                checks = alpha.get(stage, {}).get('checks', [])
                if checks:
                    self._save_alpha_checks(alpha_id, stage, checks)

            # 5. 保存参赛信息
            if alpha.get('competitions'):
                self._save_alpha_competitions(alpha_id, alpha['competitions'])

            # 6. 保存团队信息
            if alpha.get('team'):
                self._save_alpha_team(alpha_id, alpha['team'])

            self.stats['new'] += 1

        except Exception as e:
            logger.error(f"保存 Alpha {alpha_id} 失败: {e}")
            self.stats['errors'] += 1

    def _save_alpha_main(self, alpha: Dict):
        """保存 Alpha 主表"""
        data = {
            'id': alpha.get('id'),
            'type': alpha.get('type'),
            'author': alpha.get('author'),
            'expression': alpha.get('regular', {}).get('code'),
            'description': alpha.get('regular', {}).get('description'),
            'operator_count': alpha.get('regular', {}).get('operatorCount'),
            'date_created': self._parse_datetime(alpha.get('dateCreated')),
            'date_submitted': self._parse_datetime(alpha.get('dateSubmitted')),
            'date_modified': self._parse_datetime(alpha.get('dateModified')),
            'grade': alpha.get('grade'),
            'stage': alpha.get('stage'),
            'status': alpha.get('status'),
            'origin': alpha.get('origin'),
            'favorite': alpha.get('favorite', False),
            'hidden': alpha.get('hidden', False),
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
            'language': settings.get('language'),
            'start_date': settings.get('startDate'),
            'end_date': settings.get('endDate')
        }
        self.db.upsert('alpha_settings', data, 'alpha_id')

    def _save_alpha_performance(self, alpha_id: str, stage: str, perf: Dict):
        """保存性能指标"""
        if not perf:
            return

        # 先删除旧记录
        self.db.execute(
            "DELETE FROM alpha_performance WHERE alpha_id = %s AND stage = %s",
            (alpha_id, stage)
        )

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
        self.db.upsert('alpha_performance', data, 'alpha_id')

    def _save_alpha_checks(self, alpha_id: str, stage: str, checks: List[Dict]):
        """保存检查结果"""
        # 先删除旧记录
        self.db.execute(
            "DELETE FROM alpha_checks WHERE alpha_id = %s AND stage = %s",
            (alpha_id, stage)
        )

        for check in checks:
            data = {
                'alpha_id': alpha_id,
                'stage': stage.upper(),
                'check_name': check.get('name'),
                'result': check.get('result'),
                'limit_value': check.get('limit'),
                'actual_value': check.get('value')
            }
            self.db.execute(
                """INSERT INTO alpha_checks
                   (alpha_id, stage, check_name, result, limit_value, actual_value)
                   VALUES (%(alpha_id)s, %(stage)s, %(check_name)s,
                           %(result)s, %(limit_value)s, %(actual_value)s)""",
                data
            )

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

    def _log_sync(self, sync_type: str, started_at: datetime):
        """记录同步日志"""
        self.db.execute(
            """INSERT INTO alpha_sync_log
               (sync_type, total_count, new_count, update_count, error_count,
                started_at, finished_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (sync_type, self.stats['total'], self.stats['new'],
             self.stats['updated'], self.stats['errors'],
             started_at, datetime.now())
        )

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
            return None
```

### 4.5 使用示例

```python
# 初始化同步服务
sync_service = AlphaSyncService(
    credentials_path='credential.txt',
    db_config={
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'your_password',
        'database': 'worldquant_alpha'
    }
)

# 全量同步
stats = sync_service.sync_all()
print(f"同步完成: {stats}")

# 增量同步
from datetime import datetime, timedelta
stats = sync_service.sync_incremental(since=datetime.now() - timedelta(hours=1))
```

---

## 五、查询示例

### 5.1 常用查询

```sql
-- 1. 查询所有 ACTIVE 状态的 Alpha
SELECT a.id, a.expression, a.grade, a.stage,
       p.sharpe, p.fitness, p.turnover
FROM alpha a
LEFT JOIN alpha_performance p ON a.id = p.alpha_id AND p.stage = 'IS'
WHERE a.status = 'ACTIVE'
ORDER BY p.fitness DESC;

-- 2. 查询高夏普比率的 Alpha（Sharpe > 1.5）
SELECT a.id, a.expression, p.sharpe, p.fitness
FROM alpha a
JOIN alpha_performance p ON a.id = p.alpha_id
WHERE p.stage = 'IS' AND p.sharpe > 1.5
ORDER BY p.sharpe DESC;

-- 3. 统计各等级 Alpha 数量
SELECT grade, COUNT(*) as count
FROM alpha
GROUP BY grade
ORDER BY count DESC;

-- 4. 查询未通过的检查项
SELECT a.id, c.check_name, c.result, c.limit_value, c.actual_value
FROM alpha a
JOIN alpha_checks c ON a.id = c.alpha_id
WHERE c.result = 'FAIL'
ORDER BY a.date_submitted DESC;

-- 5. 查询最近 7 天提交的 Alpha
SELECT id, expression, grade, status, date_submitted
FROM alpha
WHERE date_submitted >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY date_submitted DESC;

-- 6. 查询参赛 Alpha
SELECT a.id, a.expression, ac.competition_name, p.sharpe, p.fitness
FROM alpha a
JOIN alpha_competitions ac ON a.id = ac.alpha_id
LEFT JOIN alpha_performance p ON a.id = p.alpha_id AND p.stage = 'IS'
ORDER BY p.fitness DESC;
```

---

## 六、同步策略

### 6.1 定时同步

```python
# 在 alpha_orchestrator.py 中添加定时同步
import schedule

def setup_sync_schedule():
    """设置定时同步任务"""
    sync_service = AlphaSyncService(...)

    # 每小时增量同步
    schedule.every(1).hours.do(
        lambda: sync_service.sync_incremental(
            since=datetime.now() - timedelta(hours=1)
        )
    )

    # 每天凌晨 2 点全量同步
    schedule.every().day.at("02:00").do(sync_service.sync_all)
```

### 6.2 同步触发条件

| 场景 | 同步类型 | 频率 |
|------|---------|------|
| 首次运行 | 全量同步 | 一次性 |
| 定时更新 | 增量同步 | 每小时 |
| 数据修复 | 全量同步 | 手动触发 |
| 新 Alpha 提交后 | 增量同步 | 事件触发 |

---

## 七、注意事项

### 7.1 性能优化

1. **批量插入**: 使用 `executemany` 批量插入，减少数据库连接开销
2. **索引优化**: 为常用查询字段创建索引
3. **分页获取**: API 分页获取，避免一次性加载大量数据
4. **连接池**: 考虑使用数据库连接池（如 `DBUtils`）

### 7.2 数据一致性

1. **事务处理**: 同一批次数据使用事务，失败时回滚
2. **幂等性**: 使用 `INSERT ... ON DUPLICATE KEY UPDATE` 保证幂等
3. **错误重试**: API 调用失败时自动重试

### 7.3 安全性

1. **密码加密**: 数据库密码不要明文存储，使用环境变量或加密配置
2. **连接安全**: 生产环境使用 SSL 连接数据库
3. **权限最小化**: 数据库用户只授予必要权限

---

## 八、扩展计划

### 8.1 后续功能

- [ ] 添加 Alpha 相关性分析功能
- [ ] 支持 Alpha 表达式解析和存储
- [ ] 添加数据可视化 Dashboard
- [ ] 支持 Alpha 回测结果存储
- [ ] 添加数据导出功能

### 8.2 监控告警

- [ ] 同步失败告警
- [ ] 数据异常检测
- [ ] 性能指标监控
