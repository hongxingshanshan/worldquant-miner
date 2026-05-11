# Alpha 提交筛选条件修改方案

## 一、背景

当前 `improved_alpha_submitter.py` 从 WorldQuant API 获取符合条件的 Alpha 进行提交，筛选条件为：
- `status = UNSUBMITTED`
- `is.fitness > 1`
- `is.sharpe > 1.25`

现需修改为从 MySQL 数据库获取，筛选条件改为：**IS 检查项全部通过（7 项 PASS，0 项 FAIL）**。

## 二、修改文件清单

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `db/alpha_query_service.py` | 新增方法 | 添加 `get_submittable_alphas` 方法 |
| `generation_one/naive-ollama/improved_alpha_submitter.py` | 修改 | 添加数据库模式支持 |

## 三、详细修改内容

### 3.1 `db/alpha_query_service.py`

**新增方法：`get_submittable_alphas`**

```python
def get_submittable_alphas(self, limit: int = 100) -> List[Dict]:
    """
    获取可提交的 Alpha 列表（IS 检查全部通过）

    筛选条件：
    - status = 'UNSUBMITTED'
    - IS 检查项全部通过（7 项 PASS，0 项 FAIL）
    - 未隐藏
    - 按创建时间倒序排列

    Args:
        limit: 返回数量上限

    Returns:
        可提交的 Alpha 列表，包含以下字段：
        - id: Alpha ID
        - expression: Alpha 表达式
        - grade: 等级
        - status: 状态
        - stage: 阶段
        - date_created: 创建时间
        - is_sharpe: IS 夏普比率
        - is_fitness: IS 适应度
        - is_turnover: IS 换手率
        - is_returns: IS 收益率
        - is_checks_pass: IS 检查通过数量
        - is_checks_fail: IS 检查失败数量
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
        HAVING is_checks_pass = 7 AND is_checks_fail = 0
        ORDER BY a.date_created DESC
        LIMIT %s
    """

    with self.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (limit,))
        return cursor.fetchall()
```

### 3.2 `generation_one/naive-ollama/improved_alpha_submitter.py`

#### 3.2.1 修改 `__init__` 方法

**原代码：**
```python
def __init__(self, credentials_path: str):
    self.sess = requests.Session()
    self.sess.timeout = (30, 300)
    self.setup_auth(credentials_path)
```

**修改后：**
```python
def __init__(self, credentials_path: str, db_config: dict = None):
    self.sess = requests.Session()
    self.sess.timeout = (30, 300)
    self.setup_auth(credentials_path)

    # 数据库服务（可选）
    self.db_config = db_config
    self.query_service = None
    if db_config:
        try:
            from db.alpha_query_service import AlphaQueryService
            self.query_service = AlphaQueryService(db_config)
            logger.info("数据库查询服务初始化成功")
        except Exception as e:
            logger.warning(f"数据库查询服务初始化失败: {e}")
```

#### 3.2.2 新增 `fetch_submittable_from_db` 方法

```python
def fetch_submittable_from_db(self, limit: int = 100) -> List[Dict]:
    """
    从数据库获取可提交的 Alpha（IS 检查全部通过）

    Args:
        limit: 获取数量上限

    Returns:
        Alpha 列表，每个元素包含：
        - id: Alpha ID
        - expression: 表达式
        - is_sharpe, is_fitness, is_turnover, is_returns: 性能指标
    """
    if not self.query_service:
        logger.error("数据库服务不可用，无法从数据库获取 Alpha")
        return []

    try:
        alphas = self.query_service.get_submittable_alphas(limit=limit)
        logger.info(f"从数据库获取到 {len(alphas)} 个可提交的 Alpha（IS 检查全部通过）")

        # 记录详细信息
        for alpha in alphas[:5]:  # 只记录前 5 个
            logger.info(f"  - {alpha['id']}: Sharpe={alpha.get('is_sharpe')}, "
                       f"Fitness={alpha.get('is_fitness')}, "
                       f"Checks={alpha.get('is_checks_pass')}PASS/{alpha.get('is_checks_fail')}FAIL")

        return alphas

    except Exception as e:
        logger.error(f"从数据库获取 Alpha 失败: {e}")
        return []
```

#### 3.2.3 新增 `batch_submit_from_db` 方法

```python
def batch_submit_from_db(self, batch_size: int = 3, limit: int = 100) -> int:
    """
    从数据库获取可提交的 Alpha 并批量提交

    Args:
        batch_size: 每批次提交数量
        limit: 从数据库获取的最大数量

    Returns:
        成功提交的 Alpha 数量
    """
    logger.info(f"开始从数据库获取可提交的 Alpha（IS 检查全部通过）")

    # 从数据库获取
    alphas = self.fetch_submittable_from_db(limit=limit)
    if not alphas:
        logger.info("数据库中没有可提交的 Alpha")
        return 0

    logger.info(f"共获取 {len(alphas)} 个可提交的 Alpha")

    # 提交
    total_submitted = 0
    consecutive_failures = 0
    max_consecutive_failures = 3

    for i, alpha in enumerate(alphas):
        alpha_id = alpha['id']
        expression = alpha.get('expression', 'N/A')
        sharpe = alpha.get('is_sharpe')
        fitness = alpha.get('is_fitness')

        logger.info(f"[{i+1}/{len(alphas)}] 提交 Alpha {alpha_id}")
        logger.info(f"  Expression: {expression[:80]}..." if len(expression) > 80 else f"  Expression: {expression}")
        logger.info(f"  Sharpe: {sharpe}, Fitness: {fitness}")

        if self.submit_alpha(alpha_id):
            total_submitted += 1
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                logger.error(f"连续失败 {consecutive_failures} 次，停止提交")
                break

        # 提交间隔，避免限流
        if i < len(alphas) - 1:
            logger.info("等待 30 秒后继续...")
            time.sleep(30)

    logger.info(f"提交完成，共成功提交 {total_submitted} 个 Alpha")
    return total_submitted
```

#### 3.2.4 修改命令行参数

**新增参数：**

```python
# 在 main() 函数的 argparse 部分添加
parser.add_argument('--use-db', action='store_true',
                    help='从数据库获取可提交的 Alpha（IS 检查全部通过），而非从 API 获取')
parser.add_argument('--db-config', type=str, default='../db/db_config.json',
                    help='数据库配置文件路径（默认: ../db/db_config.json）')
parser.add_argument('--db-limit', type=int, default=100,
                    help='从数据库获取的最大 Alpha 数量（默认: 100）')
```

#### 3.2.5 修改 `main()` 函数逻辑

```python
def main():
    # ... 现有参数解析代码 ...

    # 加载数据库配置
    db_config = None
    if args.use_db:
        db_config_path = args.db_config
        if not os.path.exists(db_config_path):
            # 尝试相对路径
            db_config_path = os.path.join(os.path.dirname(__file__), args.db_config)

        if os.path.exists(db_config_path):
            with open(db_config_path, 'r', encoding='utf-8') as f:
                db_config = json.load(f)
            logger.info(f"已加载数据库配置: {db_config_path}")
        else:
            logger.error(f"数据库配置文件不存在: {args.db_config}")
            return 1

    try:
        submitter = ImprovedAlphaSubmitter(args.credentials, db_config=db_config)

        if args.use_db:
            # 数据库模式
            if args.auto_mode:
                logger.info("单次提交模式（数据库）")
                submitter.batch_submit_from_db(
                    batch_size=args.batch_size,
                    limit=args.db_limit
                )
            else:
                # 持续模式
                while True:
                    logger.info(f"开始提交任务（数据库模式）: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    submitter.batch_submit_from_db(
                        batch_size=args.batch_size,
                        limit=args.db_limit
                    )
                    logger.info(f"等待 {args.interval_hours} 小时后进行下一轮...")
                    time.sleep(args.interval_hours * 3600)
        else:
            # 原有的 API 模式
            if args.use_hopeful_file:
                if submitter.check_hopeful_alphas_count(args.min_hopeful_count):
                    submitter.submit_hopeful_alphas(batch_size=args.batch_size)
                else:
                    logger.info("Hopeful alphas 数量不足，跳过提交")
            else:
                submitter.batch_submit(batch_size=args.batch_size)

    except KeyboardInterrupt:
        logger.info("收到中断信号，退出...")
        return 0
    except Exception as e:
        logger.error(f"发生错误: {e}")
        return 1
```

## 四、使用方式

### 4.1 命令行使用

```bash
cd C:\WorkSpace\worldquant-miner\generation_one\naive-ollama

# 从数据库获取 IS 检查全部通过的 Alpha 并提交（单次模式）
python improved_alpha_submitter.py --credentials ./credential.txt --use-db --auto-mode

# 指定数据库配置文件路径
python improved_alpha_submitter.py --credentials ./credential.txt --use-db --db-config ../db/db_config.json --auto-mode

# 限制获取数量
python improved_alpha_submitter.py --credentials ./credential.txt --use-db --db-limit 50 --auto-mode

# 持续模式（每 24 小时运行一次）
python improved_alpha_submitter.py --credentials ./credential.txt --use-db --interval-hours 24

# 原有 API 模式（保持兼容）
python improved_alpha_submitter.py --credentials ./credential.txt --auto-mode
```

### 4.2 Web Dashboard 集成

可在 `web_dashboard.py` 中添加新的触发接口：

```python
@app.route('/api/trigger_submission_db', methods=['POST'])
def api_trigger_submission_db():
    """从数据库获取可提交的 Alpha 并提交"""
    return jsonify(dashboard.trigger_submission_from_db())

# 在 AlphaDashboard 类中添加方法
def trigger_submission_from_db(self) -> Dict:
    """从数据库获取可提交的 Alpha 并触发提交"""
    try:
        result = subprocess.run([
            "python", "improved_alpha_submitter.py",
            "--credentials", "./credential.txt",
            "--use-db",
            "--db-config", "../db/db_config.json",
            "--auto-mode"
        ], capture_output=True, text=True, timeout=5400)

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## 五、筛选条件对比

| 条件 | 原方案（API） | 新方案（数据库） |
|------|--------------|-----------------|
| 数据源 | WorldQuant API | MySQL 数据库 |
| 状态 | `status = UNSUBMITTED` | `status = UNSUBMITTED` |
| Fitness | `is.fitness > 1` | 不限制 |
| Sharpe | `is.sharpe > 1.25` | 不限制 |
| IS 检查 | 无筛选 | 7 项 PASS，0 项 FAIL |
| 排序 | 创建时间倒序 | 创建时间倒序 |

## 六、注意事项

1. **数据库同步**：使用数据库模式前，需确保数据库已同步最新的 Alpha 数据
2. **检查项数量**：WorldQuant 的 IS 检查项共 7 项，全部通过才符合提交条件
3. **限流处理**：提交间隔保持 30 秒，避免 API 限流
4. **兼容性**：原有 API 模式保持不变，通过 `--use-db` 参数切换

## 七、测试验证

修改完成后，建议按以下步骤测试：

1. 验证数据库查询：
   ```bash
   python -c "
   import json
   from db.alpha_query_service import AlphaQueryService
   with open('db/db_config.json') as f:
       config = json.load(f)
   qs = AlphaQueryService(config)
   alphas = qs.get_submittable_alphas(limit=5)
   print(f'找到 {len(alphas)} 个可提交的 Alpha')
   for a in alphas:
       print(f\"  {a['id']}: checks_pass={a['is_checks_pass']}, checks_fail={a['is_checks_fail']}\")
   "
   ```

2. 验证提交流程：
   ```bash
   python improved_alpha_submitter.py --credentials ./credential.txt --use-db --db-limit 1 --auto-mode
   ```

3. 检查提交日志确认结果
