# Web Dashboard 数据库切换方案

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Web Dashboard                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Alpha 列表  │  │ Alpha 详情  │  │ 同步按钮(新增)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ↓ API 调用
┌─────────────────────────────────────────────────────────────┐
│                   Flask API 层                               │
│  /api/alphas          /api/alpha/<id>    /api/sync          │
│  (列表查询)           (详情查询)         (触发同步)          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   MySQL 数据库                               │
│  alpha | alpha_performance | alpha_checks | alpha_settings  │
└─────────────────────────────────────────────────────────────┘
                          ↓ 同步
┌─────────────────────────────────────────────────────────────┐
│                 WorldQuant Brain API                         │
└─────────────────────────────────────────────────────────────┘
```

## 二、数据库表结构

### 2.1 已有表结构

| 表名 | 说明 | 主要字段 |
|------|------|----------|
| `alpha` | Alpha 主表 | id, expression, grade, status, stage, date_created, date_submitted, synced_at |
| `alpha_settings` | Alpha 设置 | instrument_type, region, universe, delay, decay, neutralization |
| `alpha_performance` | 性能指标 | stage(IS/OS), sharpe, fitness, turnover, returns, drawdown |
| `alpha_checks` | 检查结果 | stage, check_name, result(PASS/FAIL), limit_value, actual_value |
| `alpha_sync_log` | 同步日志 | sync_type, total_count, new_count, update_count, started_at |

### 2.2 关键索引

```sql
-- 已有索引
CREATE INDEX idx_alpha_date_created ON alpha(date_created);
CREATE INDEX idx_alpha_stage ON alpha(stage);
CREATE INDEX idx_alpha_status ON alpha(status);
CREATE INDEX idx_perf_sharpe ON alpha_performance(sharpe);
CREATE INDEX idx_perf_fitness ON alpha_performance(fitness);

-- 建议新增索引（优化检查项统计查询）
CREATE INDEX idx_checks_result ON alpha_checks(result);
```

## 三、后端 API 改造

### 3.1 新增数据库查询服务

**文件**: `db/alpha_query_service.py`

```python
from db.alpha_query_service import AlphaQueryService

# 初始化
with open('db/db_config.json', 'r') as f:
    db_config = json.load(f)
query_service = AlphaQueryService(db_config)
```

### 3.2 API 接口改造

#### 3.2.1 Alpha 列表接口

**原接口**: `/api/failed-alphas` (调用 WorldQuant API)

**新接口**: `/api/alphas` (从数据库查询)

```python
@app.route('/api/alphas')
def api_alphas():
    """获取 Alpha 列表（从数据库）"""
    limit = request.args.get('limit', 50, type=int)
    order_by = request.args.get('order', 'is_checks_pass')
    status = request.args.get('status')
    stage = request.args.get('stage')

    alphas = query_service.get_alpha_list(
        limit=limit,
        order_by=order_by,
        status_filter=status,
        stage_filter=stage
    )

    # 格式化返回
    result = []
    for a in alphas:
        result.append({
            "id": a['id'],
            "expression": a['expression'],
            "grade": a['grade'],
            "status": a['status'],
            "stage": a['stage'],
            "is_submitted": a['status'] != 'UNSUBMITTED',
            "date_created": str(a['date_created']) if a['date_created'] else None,
            "date_submitted": str(a['date_submitted']) if a['date_submitted'] else None,
            "synced_at": str(a['synced_at']) if a['synced_at'] else None,
            # IS 指标
            "is_sharpe": float(a['is_sharpe']) if a['is_sharpe'] else None,
            "is_fitness": float(a['is_fitness']) if a['is_fitness'] else None,
            "is_turnover": float(a['is_turnover']) if a['is_turnover'] else None,
            "is_returns": float(a['is_returns']) if a['is_returns'] else None,
            # OS 指标
            "os_sharpe": float(a['os_sharpe']) if a['os_sharpe'] else None,
            "os_fitness": float(a['os_fitness']) if a['os_fitness'] else None,
            # 检查结果统计
            "is_checks_pass": a['is_checks_pass'] or 0,
            "is_checks_fail": a['is_checks_fail'] or 0,
            "os_checks_pass": a['os_checks_pass'] or 0,
            "os_checks_fail": a['os_checks_fail'] or 0,
            # 可提交判断
            "is_submittable": (a['is_checks_fail'] or 0) == 0 and a['status'] != 'UNSUBMITTED'
        })

    return jsonify({"alphas": result, "total": len(result)})
```

#### 3.2.2 Alpha 详情接口

**原接口**: `/api/alpha/<alpha_id>` (调用 WorldQuant API)

**新接口**: 保持路径，改为从数据库查询

```python
@app.route('/api/alpha/<alpha_id>')
def api_alpha_details(alpha_id):
    """获取 Alpha 详情（从数据库）"""
    alpha = query_service.get_alpha_detail(alpha_id)

    if not alpha:
        return jsonify({"success": False, "error": f"Alpha 不存在: {alpha_id}"})

    # 格式化检查结果
    failed_checks = [c['check_name'] for c in alpha['checks'] if c['result'] == 'FAIL']

    result = {
        "success": True,
        "data": {
            "id": alpha['id'],
            "expression": alpha['expression'],
            "description": alpha['description'],
            "grade": alpha['grade'],
            "status": alpha['status'],
            "stage": alpha['stage'],
            "date_created": str(alpha['date_created']) if alpha['date_created'] else None,
            "date_submitted": str(alpha['date_submitted']) if alpha['date_submitted'] else None,
            "date_modified": str(alpha['date_modified']) if alpha['date_modified'] else None,
            "synced_at": str(alpha['synced_at']) if alpha['synced_at'] else None,
            "settings": alpha['settings'],
            "is": alpha['performances'].get('IS'),
            "os": alpha['performances'].get('OS'),
            "checks": alpha['checks'],
            "failed_checks": failed_checks,
            "is_submittable": len(failed_checks) == 0 and alpha['status'] != 'UNSUBMITTED'
        }
    }

    return jsonify(result)
```

#### 3.2.3 同步接口（新增）

```python
@app.route('/api/sync', methods=['POST'])
def api_sync():
    """触发增量同步"""
    result = {"success": False, "stats": None, "error": None}

    try:
        db_config = query_service.db_config
        sync_service = AlphaSyncService('credential.txt', db_config)
        stats = sync_service.sync_incremental(batch_size=50)

        result["success"] = True
        result["stats"] = stats
    except Exception as e:
        result["error"] = str(e)

    return jsonify(result)

@app.route('/api/sync/full', methods=['POST'])
def api_sync_full():
    """触发全量同步"""
    result = {"success": False, "stats": None, "error": None}

    try:
        db_config = query_service.db_config
        sync_service = AlphaSyncService('credential.txt', db_config)
        stats = sync_service.sync_all(batch_size=50)

        result["success"] = True
        result["stats"] = stats
    except Exception as e:
        result["error"] = str(e)

    return jsonify(result)

@app.route('/api/sync/status')
def api_sync_status():
    """获取同步状态"""
    return jsonify({
        "last_sync_time": str(query_service.get_last_sync_time()) if query_service.get_last_sync_time() else None,
        "last_created_time": str(query_service.get_last_created_time()) if query_service.get_last_created_time() else None,
        "total_alphas": query_service.get_alpha_count(),
        "statistics": query_service.get_statistics()
    })
```

## 四、前端改造

### 4.1 同步按钮

```html
<!-- 在页面顶部添加同步区域 -->
<div class="sync-section" style="margin-bottom: 20px; padding: 15px; background: #f5f5f5; border-radius: 5px;">
    <button id="sync-btn" class="btn btn-primary">
        <i class="glyphicon glyphicon-refresh"></i> 增量同步
    </button>
    <button id="sync-full-btn" class="btn btn-default">
        全量同步
    </button>
    <span id="sync-status" class="text-muted" style="margin-left: 15px;">
        最后同步: <span id="last-sync-time">-</span>
        | Alpha 总数: <span id="alpha-count">-</span>
    </span>
</div>

<script>
// 增量同步
$('#sync-btn').click(function() {
    var $btn = $(this);
    $btn.prop('disabled', true).html('<i class="glyphicon glyphicon-refresh spinning"></i> 同步中...');

    $.post('/api/sync', function(data) {
        if (data.success) {
            alert('同步完成!\n新增: ' + data.stats.new + '\n更新: ' + data.stats.updated);
            refreshAlphaList();
            updateSyncStatus();
        } else {
            alert('同步失败: ' + data.error);
        }
    }).fail(function() {
        alert('同步请求失败');
    }).always(function() {
        $btn.prop('disabled', false).html('<i class="glyphicon glyphicon-refresh"></i> 增量同步');
    });
});

// 全量同步
$('#sync-full-btn').click(function() {
    if (!confirm('确定要执行全量同步吗？可能需要较长时间。')) {
        return;
    }

    var $btn = $(this);
    $btn.prop('disabled', true).html('同步中...');

    $.post('/api/sync/full', function(data) {
        if (data.success) {
            alert('全量同步完成!\n总数: ' + data.stats.total);
            refreshAlphaList();
            updateSyncStatus();
        } else {
            alert('同步失败: ' + data.error);
        }
    }).always(function() {
        $btn.prop('disabled', false).html('全量同步');
    });
});

// 更新同步状态
function updateSyncStatus() {
    $.get('/api/sync/status', function(data) {
        $('#last-sync-time').text(data.last_sync_time || '-');
        $('#alpha-count').text(data.total_alphas);
    });
}

// 页面加载时更新状态
$(document).ready(function() {
    updateSyncStatus();
});
</script>

<style>
/* 旋转动画 */
.spinning {
    animation: spin 1s linear infinite;
}
@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
</style>
```

### 4.2 Alpha 列表表格扩展

```html
<!-- 排序和过滤控件 -->
<div class="filter-section" style="margin-bottom: 15px;">
    <label>排序:</label>
    <select id="order-select" class="form-control" style="width: 200px; display: inline-block;">
        <option value="is_checks_pass">按 IS 检查通过数排序</option>
        <option value="sharpe">按 IS Sharpe 排序</option>
        <option value="fitness">按 IS Fitness 排序</option>
        <option value="date_created">按创建时间排序</option>
        <option value="date_modified">按修改时间排序</option>
    </select>

    <label style="margin-left: 15px;">状态:</label>
    <select id="status-filter" class="form-control" style="width: 150px; display: inline-block;">
        <option value="">全部</option>
        <option value="UNSUBMITTED">未提交</option>
        <option value="SUBMITTED">已提交</option>
        <option value="CORRELATED">已关联</option>
    </select>

    <label style="margin-left: 15px;">阶段:</label>
    <select id="stage-filter" class="form-control" style="width: 150px; display: inline-block;">
        <option value="">全部</option>
        <option value="IS">IS</option>
        <option value="OS">OS</option>
        <option value="PROD">PROD</option>
    </select>
</div>

<!-- Alpha 列表表格 -->
<table id="alpha-table" class="table table-striped table-hover">
    <thead>
        <tr>
            <th>ID</th>
            <th>表达式</th>
            <th>等级</th>
            <th>状态</th>
            <th>已提交</th>
            <th>IS Sharpe</th>
            <th>IS Fitness</th>
            <th>IS Turnover</th>
            <th>OS Sharpe</th>
            <th>IS检查</th>
            <th>OS检查</th>
            <th>可提交</th>
            <th>创建时间</th>
            <th>同步时间</th>
            <th>操作</th>
        </tr>
    </thead>
    <tbody id="alpha-tbody">
        <!-- 动态填充 -->
    </tbody>
</table>

<script>
// 刷新 Alpha 列表
function refreshAlphaList() {
    var orderBy = $('#order-select').val();
    var status = $('#status-filter').val();
    var stage = $('#stage-filter').val();

    $.get('/api/alphas', {
        order: orderBy,
        status: status,
        stage: stage,
        limit: 100
    }, function(data) {
        var tbody = $('#alpha-tbody');
        tbody.empty();

        data.alphas.forEach(function(alpha) {
            var isSubmitted = alpha.is_submitted ? '<span class="label label-success">是</span>' : '<span class="label label-default">否</span>';
            var isSubmittable = alpha.is_submittable ? '<span class="label label-success">可提交</span>' : '<span class="label label-danger">不可提交</span>';
            var isChecks = '<span class="text-success">' + alpha.is_checks_pass + '</span>/<span class="text-danger">' + alpha.is_checks_fail + '</span>';
            var osChecks = '<span class="text-success">' + alpha.os_checks_pass + '</span>/<span class="text-danger">' + alpha.os_checks_fail + '</span>';

            var row = '<tr>' +
                '<td><a href="#" class="alpha-detail-link" data-id="' + alpha.id + '">' + alpha.id + '</a></td>' +
                '<td><code style="font-size: 11px;">' + (alpha.expression || '').substring(0, 50) + '...</code></td>' +
                '<td>' + (alpha.grade || '-') + '</td>' +
                '<td>' + alpha.status + '</td>' +
                '<td>' + isSubmitted + '</td>' +
                '<td>' + (alpha.is_sharpe ? alpha.is_sharpe.toFixed(4) : '-') + '</td>' +
                '<td>' + (alpha.is_fitness ? alpha.is_fitness.toFixed(4) : '-') + '</td>' +
                '<td>' + (alpha.is_turnover ? alpha.is_turnover.toFixed(4) : '-') + '</td>' +
                '<td>' + (alpha.os_sharpe ? alpha.os_sharpe.toFixed(4) : '-') + '</td>' +
                '<td>' + isChecks + '</td>' +
                '<td>' + osChecks + '</td>' +
                '<td>' + isSubmittable + '</td>' +
                '<td>' + (alpha.date_created || '-') + '</td>' +
                '<td>' + (alpha.synced_at || '-') + '</td>' +
                '<td>' +
                    '<button class="btn btn-xs btn-primary optimize-btn" data-id="' + alpha.id + '">优化</button> ' +
                    '<button class="btn btn-xs btn-default detail-btn" data-id="' + alpha.id + '">详情</button>' +
                '</td>' +
            '</tr>';

            tbody.append(row);
        });
    });
}

// 排序和过滤变化时刷新
$('#order-select, #status-filter, #stage-filter').change(function() {
    refreshAlphaList();
});

// 页面加载时刷新
$(document).ready(function() {
    refreshAlphaList();
});
</script>
```

### 4.3 Alpha 详情弹窗

```html
<!-- 详情弹窗 -->
<div class="modal fade" id="alpha-detail-modal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal">&times;</button>
                <h4 class="modal-title">Alpha 详情 - <span id="detail-alpha-id"></span></h4>
            </div>
            <div class="modal-body">
                <div id="detail-content">加载中...</div>
            </div>
        </div>
    </div>
</div>

<script>
// 显示详情
$(document).on('click', '.detail-btn, .alpha-detail-link', function(e) {
    e.preventDefault();
    var alphaId = $(this).data('id');

    $('#detail-alpha-id').text(alphaId);
    $('#detail-content').html('加载中...');
    $('#alpha-detail-modal').modal('show');

    $.get('/api/alpha/' + alphaId, function(response) {
        if (!response.success) {
            $('#detail-content').html('<div class="alert alert-danger">' + response.error + '</div>');
            return;
        }

        var alpha = response.data;
        var html = '<div class="row">';

        // 基本信息
        html += '<div class="col-md-6"><h4>基本信息</h4><table class="table table-condensed">';
        html += '<tr><td>ID</td><td>' + alpha.id + '</td></tr>';
        html += '<tr><td>等级</td><td>' + (alpha.grade || '-') + '</td></tr>';
        html += '<tr><td>状态</td><td>' + alpha.status + '</td></tr>';
        html += '<tr><td>阶段</td><td>' + alpha.stage + '</td></tr>';
        html += '<tr><td>创建时间</td><td>' + (alpha.date_created || '-') + '</td></tr>';
        html += '<tr><td>提交时间</td><td>' + (alpha.date_submitted || '-') + '</td></tr>';
        html += '</table></div>';

        // 表达式
        html += '<div class="col-md-12"><h4>表达式</h4><pre>' + (alpha.expression || '-') + '</pre></div>';

        // IS 性能指标
        if (alpha.is) {
            html += '<div class="col-md-6"><h4>IS 性能指标</h4><table class="table table-condensed">';
            html += '<tr><td>Sharpe</td><td>' + (alpha.is.sharpe || '-') + '</td></tr>';
            html += '<tr><td>Fitness</td><td>' + (alpha.is.fitness || '-') + '</td></tr>';
            html += '<tr><td>Turnover</td><td>' + (alpha.is.turnover || '-') + '</td></tr>';
            html += '<tr><td>Returns</td><td>' + (alpha.is.returns || '-') + '</td></tr>';
            html += '<tr><td>Drawdown</td><td>' + (alpha.is.drawdown || '-') + '</td></tr>';
            html += '</table></div>';
        }

        // OS 性能指标
        if (alpha.os) {
            html += '<div class="col-md-6"><h4>OS 性能指标</h4><table class="table table-condensed">';
            html += '<tr><td>Sharpe</td><td>' + (alpha.os.sharpe || '-') + '</td></tr>';
            html += '<tr><td>Fitness</td><td>' + (alpha.os.fitness || '-') + '</td></tr>';
            html += '<tr><td>Turnover</td><td>' + (alpha.os.turnover || '-') + '</td></tr>';
            html += '</table></div>';
        }

        // 检查结果
        if (alpha.checks && alpha.checks.length > 0) {
            html += '<div class="col-md-12"><h4>检查结果</h4><table class="table table-condensed">';
            html += '<tr><th>阶段</th><th>检查项</th><th>结果</th><th>限制值</th><th>实际值</th></tr>';
            alpha.checks.forEach(function(check) {
                var resultClass = check.result === 'PASS' ? 'text-success' : 'text-danger';
                html += '<tr>' +
                    '<td>' + check.stage + '</td>' +
                    '<td>' + check.check_name + '</td>' +
                    '<td class="' + resultClass + '"><strong>' + check.result + '</strong></td>' +
                    '<td>' + (check.limit_value || '-') + '</td>' +
                    '<td>' + (check.actual_value || '-') + '</td>' +
                '</tr>';
            });
            html += '</table></div>';
        }

        html += '</div>';
        $('#detail-content').html(html);
    });
});
</script>
```

## 五、排序规则说明

### 5.1 支持的排序方式

| 排序字段 | 说明 | SQL 排序子句 |
|----------|------|--------------|
| `is_checks_pass` | IS 检查通过数量（默认） | `is_checks_pass DESC, is_sharpe DESC` |
| `sharpe` | IS 夏普比率 | `is_sharpe DESC` |
| `fitness` | IS 适应度 | `is_fitness DESC` |
| `date_created` | 创建时间 | `a.date_created DESC` |
| `date_modified` | 修改时间 | `a.date_modified DESC` |

### 5.2 检查项统计 SQL

```sql
SELECT
    a.id,
    COUNT(CASE WHEN c.result = 'PASS' AND c.stage = 'IS' THEN 1 END) as is_checks_pass,
    COUNT(CASE WHEN c.result = 'FAIL' AND c.stage = 'IS' THEN 1 END) as is_checks_fail,
    COUNT(CASE WHEN c.result = 'PASS' AND c.stage = 'OS' THEN 1 END) as os_checks_pass,
    COUNT(CASE WHEN c.result = 'FAIL' AND c.stage = 'OS' THEN 1 END) as os_checks_fail
FROM alpha a
LEFT JOIN alpha_checks c ON a.id = c.alpha_id
GROUP BY a.id
ORDER BY is_checks_pass DESC, is_sharpe DESC
```

## 六、增量同步逻辑

### 6.1 同步流程

```
1. 获取数据库中最新的 date_created
2. 调用 WorldQuant API 获取 Alpha 列表（按 dateCreated 倒序）
3. 遍历 Alpha:
   - 如果 date_created <= 数据库最新时间，跳过
   - 否则检查是否已存在
     - 已存在：更新
     - 不存在：新增
4. 记录同步日志
```

### 6.2 关键代码

```python
# 获取数据库中最新的 date_created
result = self.db.query_one("SELECT MAX(date_created) as max_date FROM alpha")
since = result['max_date']

# 比较时统一处理时区
if hasattr(alpha_date_created, 'tzinfo') and alpha_date_created.tzinfo is not None:
    alpha_date_created = alpha_date_created.replace(tzinfo=None)

if alpha_date_created <= since:
    self.stats['skipped'] += 1
    continue
```

## 七、实施步骤

| 步骤 | 内容 | 文件 | 预计时间 |
|------|------|------|----------|
| 1 | 修改 Web Dashboard 初始化，加载数据库配置 | `web_dashboard.py` | 10 分钟 |
| 2 | 改造 Alpha 列表接口 | `web_dashboard.py` | 20 分钟 |
| 3 | 改造 Alpha 详情接口 | `web_dashboard.py` | 15 分钟 |
| 4 | 新增同步接口 | `web_dashboard.py` | 15 分钟 |
| 5 | 前端添加同步按钮和状态显示 | `templates/dashboard.html` | 20 分钟 |
| 6 | 前端扩展列表字段和排序功能 | `templates/dashboard.html` | 30 分钟 |
| 7 | 前端添加详情弹窗 | `templates/dashboard.html` | 20 分钟 |
| 8 | 测试验证 | - | 15 分钟 |

**总计**: 约 2.5 小时

## 八、注意事项

1. **同步按钮防抖**: 避免用户频繁点击触发多次同步
2. **同步状态显示**: 显示同步进度和结果统计
3. **错误处理**: API 连接失败时显示友好提示
4. **时区处理**: 统一使用 naive datetime 进行比较
5. **性能优化**: 列表查询使用 LEFT JOIN 一次性获取所有数据
6. **缓存策略**: 可考虑短期缓存减少数据库压力（可选）
