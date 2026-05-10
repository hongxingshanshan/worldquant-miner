# generation_one/naive-ollama MySQL 持久化方案

## 一、概述

本方案将 `generation_one/naive-ollama` 目录下的 JSON 数据文件迁移到 MySQL 数据库，实现：
- 数据持久化存储
- 高效查询和统计
- 支持多实例并发访问
- 便于数据分析和报表生成

## 二、数据源分析

### 2.1 核心 JSON 文件

| 文件 | 用途 | 关键字段 |
|------|------|----------|
| `mined_expressions.json` | 已提交成功的 Alpha | expression, sharpe, fitness, turnover, grade, status |
| `hopeful_alphas.json` | 待优化的 Alpha | expression, alpha_id, checks[], sharpe, fitness |
| `submitted_alphas_cache.json` | 提交缓存 | expression, result.id, result.alpha, result.settings |
| `submission_results.json` | 提交结果 | alpha_id, status, error_details |
| `simulation_errors.json` | 模拟错误 | expression, error_type, error_message |

### 2.2 数据流向

```
生成 Alpha → 模拟测试 → 检查通过 → 提交成功 → mined_expressions.json
                    ↓
                检查失败 → hopeful_alphas.json → 优化 → 重新提交
                    ↓
                模拟失败 → simulation_errors.json
```

## 三、数据库表结构

### 3.1 Alpha 主表

```sql
CREATE TABLE alphas (
    id                  VARCHAR(20) PRIMARY KEY,          -- WorldQuant Alpha ID
    expression          TEXT NOT NULL,                    -- Alpha 表达式
    
    -- 性能指标
    sharpe              DECIMAL(10,4),                    -- 夏普比率
    fitness             DECIMAL(10,4),                    -- 适应度
    turnover            DECIMAL(10,4),                    -- 换手率
    returns             DECIMAL(10,4),                    -- 收益率
    
    -- 状态
    grade               ENUM('INFERIOR','AVERAGE','GOOD','EXCELLENT'),
    status              ENUM('UNSUBMITTED','SUBMITTED','ACTIVE','FAIL'),
    is_submittable      BOOLEAN DEFAULT FALSE,            -- 是否可提交
    
    -- 来源追踪（优化类型时使用）
    source_type         ENUM('generated','optimized','manual') DEFAULT 'generated',
    original_alpha_id   VARCHAR(20),                      -- 原始 Alpha ID
    original_expression TEXT,                             -- 原始表达式
    failure_type        VARCHAR(50),                      -- 失败类型
    
    -- 时间戳
    date_created        DATETIME,
    date_submitted      DATETIME,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_sharpe (sharpe),
    INDEX idx_fitness (fitness),
    INDEX idx_status (status),
    INDEX idx_source_type (source_type),
    INDEX idx_original_alpha (original_alpha_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.2 检查项表

```sql
CREATE TABLE alpha_checks (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    alpha_id        VARCHAR(20) NOT NULL,
    
    name            VARCHAR(50) NOT NULL,                 -- 检查项名称
    result          ENUM('PASS','FAIL','PENDING') NOT NULL,
    limit_value     DECIMAL(10,4),                        -- 阈值
    actual_value    DECIMAL(10,4),                        -- 实际值
    competitions    JSON,                                 -- 比赛列表（MATCHES_COMPETITION）
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (alpha_id) REFERENCES alphas(id) ON DELETE CASCADE,
    INDEX idx_alpha_check (alpha_id, name),
    INDEX idx_result (result)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**检查项名称对照表：**

| 英文名称 | 中文描述 |
|----------|----------|
| LOW_SHARPE | 低夏普比率 |
| LOW_FITNESS | 低适应度 |
| LOW_TURNOVER | 低换手率 |
| HIGH_TURNOVER | 高换手率 |
| CONCENTRATED_WEIGHT | 权重集中 |
| LOW_SUB_UNIVERSE_SHARPE | 子股票池低夏普 |
| SELF_CORRELATION | 自相关性 |
| MATCHES_COMPETITION | 比赛匹配 |

### 3.3 模拟任务表

```sql
CREATE TABLE simulations (
    id              VARCHAR(50) PRIMARY KEY,              -- 模拟任务 ID
    alpha_id        VARCHAR(20),                          -- 关联的 Alpha ID
    expression      TEXT NOT NULL,                        -- 模拟的表达式
    
    status          ENUM('PENDING','RUNNING','COMPLETE','ERROR','FAIL') NOT NULL,
    
    -- 设置参数
    instrument_type VARCHAR(20) DEFAULT 'EQUITY',
    region          VARCHAR(20) DEFAULT 'USA',
    universe        VARCHAR(20) DEFAULT 'TOP3000',
    delay           INT DEFAULT 1,
    decay           INT DEFAULT 0,
    neutralization  VARCHAR(50) DEFAULT 'INDUSTRY',
    truncation      DECIMAL(10,4) DEFAULT 0.08,
    
    -- 错误信息
    error_message   TEXT,
    error_line      INT,
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME,
    
    INDEX idx_status (status),
    INDEX idx_alpha (alpha_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.4 优化历史表

```sql
CREATE TABLE optimization_history (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    original_alpha_id   VARCHAR(20) NOT NULL,             -- 原始 Alpha ID
    original_expression TEXT NOT NULL,
    optimized_expression TEXT NOT NULL,
    
    failure_type        VARCHAR(50),                      -- 失败类型
    simulation_id       VARCHAR(50),                      -- 模拟任务 ID
    
    -- 原始指标
    original_sharpe     DECIMAL(10,4),
    original_fitness    DECIMAL(10,4),
    original_turnover   DECIMAL(10,4),
    
    success             BOOLEAN DEFAULT FALSE,
    error_message       TEXT,
    
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_original (original_alpha_id),
    INDEX idx_success (success)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.5 提交结果表

```sql
CREATE TABLE submission_results (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    alpha_id        VARCHAR(20) NOT NULL,
    
    status          ENUM('success','failed') NOT NULL,
    error_details   JSON,                                 -- 错误详情
    
    -- 自相关性信息
    correlated_alpha_id     VARCHAR(20),
    correlation_value       DECIMAL(10,4),
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_alpha (alpha_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.6 模拟错误表

```sql
CREATE TABLE simulation_errors (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    expression      TEXT NOT NULL,
    error_type      VARCHAR(50),
    error_message   TEXT,
    error_line      INT,
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_error_type (error_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 四、Python 数据库操作类

### 4.1 基础类

```python
"""
alpha_database.py - Alpha 数据库管理模块
"""
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from typing import Dict, List, Optional
import json
from datetime import datetime


class AlphaDatabase:
    """Alpha 数据库管理类"""
    
    # 检查项名称翻译
    CHECK_NAMES = {
        "LOW_SHARPE": "低夏普比率",
        "LOW_FITNESS": "低适应度",
        "LOW_TURNOVER": "低换手率",
        "HIGH_TURNOVER": "高换手率",
        "CONCENTRATED_WEIGHT": "权重集中",
        "LOW_SUB_UNIVERSE_SHARPE": "子股票池低夏普",
        "SELF_CORRELATION": "自相关性",
        "MATCHES_COMPETITION": "比赛匹配"
    }
    
    def __init__(self, host='localhost', user='root', password='', db='alpha_miner', port=3306):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': db,
            'port': port,
            'charset': 'utf8mb4',
            'cursorclass': DictCursor
        }
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = pymysql.connect(**self.config)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """初始化数据库（创建表）"""
        # 执行上述 CREATE TABLE 语句
        tables = [
            """CREATE TABLE IF NOT EXISTS alphas (...);""",
            """CREATE TABLE IF NOT EXISTS alpha_checks (...);""",
            # ... 其他表
        ]
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for sql in tables:
                cursor.execute(sql)
```

### 4.2 Alpha 操作方法

```python
    def save_alpha(self, alpha_data: Dict) -> str:
        """
        保存 Alpha 及其检查项
        
        Args:
            alpha_data: {
                'alpha_id': str,
                'expression': str,
                'sharpe': float,
                'fitness': float,
                'turnover': float,
                'returns': float,
                'grade': str,
                'status': str,
                'checks': [{'name': str, 'result': str, 'limit': float, 'value': float}],
                'source_type': str,
                'original_alpha_id': str
            }
        
        Returns:
            alpha_id
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 插入或更新 Alpha 主记录
            sql = """
            INSERT INTO alphas (id, expression, sharpe, fitness, turnover, 
                               returns, grade, status, source_type, original_alpha_id,
                               original_expression, failure_type, date_created, date_submitted)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                sharpe=VALUES(sharpe), fitness=VALUES(fitness),
                turnover=VALUES(turnover), returns=VALUES(returns),
                grade=VALUES(grade), status=VALUES(status),
                updated_at=NOW()
            """
            cursor.execute(sql, (
                alpha_data.get('alpha_id') or alpha_data.get('id'),
                alpha_data.get('expression'),
                alpha_data.get('sharpe'),
                alpha_data.get('fitness'),
                alpha_data.get('turnover'),
                alpha_data.get('returns'),
                alpha_data.get('grade'),
                alpha_data.get('status'),
                alpha_data.get('source_type', 'generated'),
                alpha_data.get('original_alpha_id'),
                alpha_data.get('original_expression'),
                alpha_data.get('failure_type'),
                alpha_data.get('date_created'),
                alpha_data.get('date_submitted')
            ))
            
            alpha_id = alpha_data.get('alpha_id') or alpha_data.get('id')
            
            # 删除旧的检查项
            cursor.execute("DELETE FROM alpha_checks WHERE alpha_id = %s", (alpha_id,))
            
            # 插入新的检查项
            checks = alpha_data.get('checks', [])
            for check in checks:
                self._save_check(cursor, alpha_id, check)
            
            # 判断是否可提交
            is_submittable = all(
                c.get('result') == 'PASS' 
                for c in checks 
                if c.get('name') != 'MATCHES_COMPETITION'
            )
            cursor.execute(
                "UPDATE alphas SET is_submittable = %s WHERE id = %s",
                (is_submittable, alpha_id)
            )
            
            return alpha_id
    
    def _save_check(self, cursor, alpha_id: str, check: Dict):
        """保存检查项"""
        sql = """
        INSERT INTO alpha_checks (alpha_id, name, result, limit_value, actual_value, competitions)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            alpha_id,
            check.get('name'),
            check.get('result'),
            check.get('limit'),
            check.get('value'),
            json.dumps(check.get('competitions')) if check.get('competitions') else None
        ))
    
    def get_alpha(self, alpha_id: str) -> Optional[Dict]:
        """获取单个 Alpha 详情"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取 Alpha 主记录
            cursor.execute("SELECT * FROM alphas WHERE id = %s", (alpha_id,))
            alpha = cursor.fetchone()
            if not alpha:
                return None
            
            # 获取检查项
            cursor.execute(
                "SELECT * FROM alpha_checks WHERE alpha_id = %s ORDER BY id",
                (alpha_id,)
            )
            alpha['checks'] = cursor.fetchall()
            
            return alpha
    
    def get_failed_alphas(self, min_sharpe: float = 1.0, limit: int = 20) -> List[Dict]:
        """
        获取失败的 Alpha（用于优化）
        
        Args:
            min_sharpe: 最低夏普比率阈值
            limit: 最大返回数量
        
        Returns:
            失败的 Alpha 列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            sql = """
            SELECT a.*, 
                   GROUP_CONCAT(DISTINCT ac.name) as failed_check_names
            FROM alphas a
            LEFT JOIN alpha_checks ac ON a.id = ac.alpha_id AND ac.result = 'FAIL'
            WHERE a.is_submittable = FALSE
              AND a.sharpe >= %s
            GROUP BY a.id
            ORDER BY a.sharpe DESC
            LIMIT %s
            """
            cursor.execute(sql, (min_sharpe, limit))
            results = cursor.fetchall()
            
            # 为每个 Alpha 获取完整的检查项
            for alpha in results:
                cursor.execute(
                    "SELECT * FROM alpha_checks WHERE alpha_id = %s",
                    (alpha['id'],)
                )
                alpha['checks'] = cursor.fetchall()
            
            return results
    
    def get_quality_alphas(self, min_fitness: float = 1.0, limit: int = 50) -> List[Dict]:
        """获取高质量 Alpha"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            sql = """
            SELECT * FROM alphas 
            WHERE fitness >= %s AND is_submittable = TRUE
            ORDER BY sharpe DESC
            LIMIT %s
            """
            cursor.execute(sql, (min_fitness, limit))
            return cursor.fetchall()
```

### 4.3 模拟和优化方法

```python
    def save_simulation(self, sim_data: Dict) -> str:
        """保存模拟任务"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            settings = sim_data.get('settings', {})
            
            sql = """
            INSERT INTO simulations (id, alpha_id, expression, status,
                                   instrument_type, region, universe, delay, 
                                   decay, neutralization, truncation, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE status=VALUES(status), error_message=VALUES(error_message)
            """
            cursor.execute(sql, (
                sim_data.get('id'),
                sim_data.get('alpha'),
                sim_data.get('expression'),
                sim_data.get('status'),
                settings.get('instrumentType'),
                settings.get('region'),
                settings.get('universe'),
                settings.get('delay'),
                settings.get('decay'),
                settings.get('neutralization'),
                settings.get('truncation'),
                sim_data.get('error_message')
            ))
            
            return sim_data.get('id')
    
    def save_optimization(self, opt_data: Dict) -> int:
        """
        保存优化记录
        
        Args:
            opt_data: {
                'alpha_id': str,
                'original': str,
                'optimized': str,
                'failure_type': str,
                'simulation_id': str,
                'original_metrics': {'sharpe': float, 'fitness': float, 'turnover': float},
                'success': bool,
                'error': str
            }
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            metrics = opt_data.get('original_metrics', {})
            
            sql = """
            INSERT INTO optimization_history 
            (original_alpha_id, original_expression, optimized_expression, 
             failure_type, simulation_id, original_sharpe, original_fitness, 
             original_turnover, success, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                opt_data.get('alpha_id'),
                opt_data.get('original'),
                opt_data.get('optimized'),
                opt_data.get('failure_type'),
                opt_data.get('simulation_id'),
                metrics.get('sharpe'),
                metrics.get('fitness'),
                metrics.get('turnover'),
                opt_data.get('success', False),
                opt_data.get('error')
            ))
            
            return cursor.lastrowid
    
    def save_submission_result(self, result_data: Dict):
        """保存提交结果"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            sql = """
            INSERT INTO submission_results (alpha_id, status, error_details,
                                          correlated_alpha_id, correlation_value)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                result_data.get('alpha_id'),
                result_data.get('status'),
                json.dumps(result_data.get('error_details')) if result_data.get('error_details') else None,
                result_data.get('correlated_alpha_id'),
                result_data.get('correlation_value')
            ))
    
    def save_simulation_error(self, error_data: Dict):
        """保存模拟错误"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            sql = """
            INSERT INTO simulation_errors (expression, error_type, error_message, error_line)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (
                error_data.get('expression'),
                error_data.get('error_type'),
                error_data.get('error_message'),
                error_data.get('error_line')
            ))
```

### 4.4 统计查询方法

```python
    def get_statistics(self) -> Dict:
        """获取统计数据"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # 总 Alpha 数量
            cursor.execute("SELECT COUNT(*) as count FROM alphas")
            stats['total_alphas'] = cursor.fetchone()['count']
            
            # 可提交 Alpha 数量
            cursor.execute("SELECT COUNT(*) as count FROM alphas WHERE is_submittable = TRUE")
            stats['submittable_alphas'] = cursor.fetchone()['count']
            
            # 高质量 Alpha 数量 (fitness >= 1.0)
            cursor.execute("SELECT COUNT(*) as count FROM alphas WHERE fitness >= 1.0")
            stats['quality_alphas'] = cursor.fetchone()['count']
            
            # 各等级分布
            cursor.execute("""
                SELECT grade, COUNT(*) as count 
                FROM alphas 
                WHERE grade IS NOT NULL 
                GROUP BY grade
            """)
            stats['grade_distribution'] = {row['grade']: row['count'] for row in cursor.fetchall()}
            
            # 检查项失败统计
            cursor.execute("""
                SELECT name, COUNT(*) as count 
                FROM alpha_checks 
                WHERE result = 'FAIL' 
                GROUP BY name 
                ORDER BY count DESC
            """)
            stats['failed_checks'] = cursor.fetchall()
            
            # 优化成功率
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) as successful
                FROM optimization_history
            """)
            row = cursor.fetchone()
            stats['optimization_total'] = row['total']
            stats['optimization_successful'] = row['successful']
            stats['optimization_success_rate'] = (
                row['successful'] / row['total'] * 100 if row['total'] > 0 else 0
            )
            
            return stats
    
    def get_top_alphas(self, metric: str = 'sharpe', limit: int = 10) -> List[Dict]:
        """获取 Top Alpha"""
        valid_metrics = ['sharpe', 'fitness', 'returns']
        if metric not in valid_metrics:
            metric = 'sharpe'
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            sql = f"""
            SELECT id, expression, sharpe, fitness, turnover, returns, grade, status
            FROM alphas 
            WHERE {metric} IS NOT NULL
            ORDER BY {metric} DESC 
            LIMIT %s
            """
            cursor.execute(sql, (limit,))
            return cursor.fetchall()
```

## 五、数据迁移脚本

```python
"""
migrate_to_mysql.py - JSON 数据迁移脚本
"""
import json
import os
from alpha_database import AlphaDatabase


def migrate_json_to_mysql(db: AlphaDatabase, base_path: str = '.'):
    """将 JSON 文件迁移到 MySQL"""
    
    # 1. 迁移 mined_expressions.json（已提交成功的 Alpha）
    mined_file = os.path.join(base_path, 'mined_expressions.json')
    if os.path.exists(mined_file):
        with open(mined_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"迁移 mined_expressions.json: {len(data)} 条记录")
            for item in data:
                db.save_alpha({
                    'alpha_id': item.get('alpha_id'),
                    'expression': item.get('expression'),
                    'fitness': item.get('fitness'),
                    'sharpe': item.get('sharpe'),
                    'turnover': item.get('turnover'),
                    'grade': item.get('grade'),
                    'status': item.get('status'),
                    'date_submitted': item.get('dateSubmitted'),
                    'source_type': 'generated'
                })
    
    # 2. 迁移 hopeful_alphas.json（待优化的 Alpha）
    hopeful_file = os.path.join(base_path, 'hopeful_alphas.json')
    if os.path.exists(hopeful_file):
        with open(hopeful_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"迁移 hopeful_alphas.json: {len(data)} 条记录")
            for item in data:
                db.save_alpha({
                    'alpha_id': item.get('alpha_id'),
                    'expression': item.get('expression'),
                    'fitness': item.get('fitness'),
                    'sharpe': item.get('sharpe'),
                    'turnover': item.get('turnover'),
                    'returns': item.get('returns'),
                    'grade': item.get('grade'),
                    'checks': item.get('checks', []),
                    'source_type': 'generated'
                })
    
    # 3. 迁移 submitted_alphas_cache.json（模拟任务缓存）
    cache_file = os.path.join(base_path, 'submitted_alphas_cache.json')
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"迁移 submitted_alphas_cache.json: {len(data)} 条记录")
            for item in data:
                result = item.get('result', {})
                settings = result.get('settings', {})
                db.save_simulation({
                    'id': result.get('id'),
                    'alpha': result.get('alpha'),
                    'expression': item.get('expression'),
                    'status': result.get('status'),
                    'settings': settings
                })
    
    # 4. 迁移 submission_results.json（提交结果）
    results_file = os.path.join(base_path, 'submission_results.json')
    if os.path.exists(results_file):
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"迁移 submission_results.json: {len(data)} 条记录")
            for item in data:
                result = item.get('result', {})
                db.save_submission_result({
                    'alpha_id': item.get('alpha_id'),
                    'status': result.get('status'),
                    'error_details': result.get('error') if result.get('status') == 'failed' else None
                })
    
    # 5. 迁移 simulation_errors.json（模拟错误）
    errors_file = os.path.join(base_path, 'simulation_errors.json')
    if os.path.exists(errors_file):
        with open(errors_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"迁移 simulation_errors.json: {len(data)} 条记录")
            for item in data:
                db.save_simulation_error({
                    'expression': item.get('expression'),
                    'error_type': item.get('error_type'),
                    'error_message': item.get('error_message'),
                    'error_line': item.get('error_line')
                })
    
    print("迁移完成！")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='JSON 数据迁移到 MySQL')
    parser.add_argument('--host', default='localhost', help='MySQL 主机')
    parser.add_argument('--user', default='root', help='MySQL 用户')
    parser.add_argument('--password', default='', help='MySQL 密码')
    parser.add_argument('--database', default='alpha_miner', help='数据库名称')
    parser.add_argument('--path', default='.', help='JSON 文件目录')
    
    args = parser.parse_args()
    
    db = AlphaDatabase(
        host=args.host,
        user=args.user,
        password=args.password,
        db=args.database
    )
    
    # 初始化数据库表
    db.init_database()
    
    # 执行迁移
    migrate_json_to_mysql(db, args.path)
```

## 六、集成到现有代码

### 6.1 修改 `alpha_optimizer.py`

```python
# 在 AlphaOptimizer 类中添加数据库支持

class AlphaOptimizer:
    def __init__(self, llm_client, wq_client=None, db=None):
        self.llm_client = llm_client
        self.wq_client = wq_client
        self.db = db  # 新增：数据库实例
        
    def optimize_alpha(self, alpha_data: Dict, temperature: float = 0.5) -> Dict:
        """优化单个 Alpha"""
        # ... 原有优化逻辑 ...
        
        # 保存优化记录到数据库
        if self.db and result.get("success"):
            self.db.save_optimization({
                'alpha_id': alpha_data.get('alpha_id'),
                'original': alpha_data.get('expression'),
                'optimized': result.get('optimized'),
                'failure_type': result.get('failure_type'),
                'simulation_id': result.get('simulation_id'),
                'original_metrics': result.get('original_metrics', {}),
                'success': True
            })
        
        return result
```

### 6.2 修改 `web_dashboard.py`

```python
# 在 AlphaDashboard 类中添加数据库支持

class AlphaDashboard:
    def __init__(self, db=None):
        self.db = db  # 新增：数据库实例
        # ... 其他初始化 ...
    
    def get_failed_alphas(self, limit: int = 20) -> List[Dict]:
        """获取未通过检查的 Alpha 列表"""
        if self.db:
            return self.db.get_failed_alphas(min_sharpe=1.0, limit=limit)
        else:
            # 回退到 API 查询
            return self._get_failed_alphas_from_api(limit)
```

## 七、使用示例

```python
# 示例：初始化并使用数据库
from alpha_database import AlphaDatabase

# 创建数据库实例
db = AlphaDatabase(
    host='localhost',
    user='root',
    password='your_password',
    db='alpha_miner'
)

# 初始化表结构
db.init_database()

# 保存 Alpha
db.save_alpha({
    'alpha_id': 'abc123',
    'expression': 'rank(ts_zscore(divide(close, cap), 60))',
    'sharpe': 1.88,
    'fitness': 1.31,
    'turnover': 0.2293,
    'grade': 'AVERAGE',
    'status': 'ACTIVE',
    'checks': [
        {'name': 'LOW_SHARPE', 'result': 'PASS', 'limit': 1.25, 'value': 1.88},
        {'name': 'LOW_FITNESS', 'result': 'PASS', 'limit': 1.0, 'value': 1.31}
    ]
})

# 查询失败的 Alpha
failed = db.get_failed_alphas(min_sharpe=1.0, limit=10)
print(f"找到 {len(failed)} 个待优化的 Alpha")

# 获取统计数据
stats = db.get_statistics()
print(f"总 Alpha: {stats['total_alphas']}")
print(f"高质量 Alpha: {stats['quality_alphas']}")
```

## 八、性能优化建议

1. **索引优化**
   - 所有查询字段已建立索引
   - 组合查询考虑建立联合索引

2. **批量插入**
   - 迁移时使用批量插入提高效率
   - 日常操作单条插入即可

3. **连接池**
   - 生产环境建议使用连接池
   - 推荐 `DBUtils` 或 `SQLAlchemy`

4. **定期清理**
   - 定期清理过期的模拟错误记录
   - 归档历史优化记录

## 九、备份策略

```bash
# 每日备份脚本
mysqldump -u root -p alpha_miner > backup_$(date +%Y%m%d).sql

# 恢复备份
mysql -u root -p alpha_miner < backup_20260510.sql
```
