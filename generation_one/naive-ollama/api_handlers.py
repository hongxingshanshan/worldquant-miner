"""
Web Dashboard API 处理函数

从 web_dashboard.py 拆分出来，包含所有 Flask 路由处理函数
"""
from flask import request, jsonify, render_template


def register_api_routes(app, dashboard):
    """注册所有 API 路由到 Flask 应用

    Args:
        app: Flask 应用实例
        dashboard: AlphaDashboard 实例
    """

    @app.route('/')
    def index():
        """Main dashboard page."""
        return render_template('dashboard.html')

    @app.route('/api/status')
    def api_status():
        """API endpoint for system status."""
        return jsonify(dashboard.get_system_status())

    @app.route('/api/logs')
    def api_logs():
        """API endpoint for logs."""
        lines = request.args.get('lines', 50, type=int)
        return jsonify({"logs": dashboard.get_logs(lines)})

    @app.route('/api/alpha_logs')
    def api_alpha_logs():
        """API endpoint for alpha generator specific logs."""
        lines = request.args.get('lines', 50, type=int)
        return jsonify({"logs": dashboard.get_alpha_generator_logs(lines)})

    @app.route('/api/trigger_mining', methods=['POST'])
    def api_trigger_mining():
        """API endpoint to trigger manual mining."""
        result = dashboard.trigger_mining()
        return jsonify(result)

    @app.route('/api/trigger_submission', methods=['POST'])
    def api_trigger_submission():
        """API endpoint to trigger manual submission."""
        result = dashboard.trigger_submission()
        return jsonify(result)

    @app.route('/api/trigger_alpha_generation', methods=['POST'])
    def api_trigger_alpha_generation():
        """API endpoint to trigger manual alpha generation."""
        result = dashboard.trigger_alpha_generation()
        return jsonify(result)

    @app.route('/api/refresh')
    def api_refresh():
        """API endpoint to refresh status."""
        return jsonify(dashboard.get_system_status())

    @app.route('/api/simulation/<sim_id>')
    def api_simulation_status(sim_id):
        """API endpoint to get simulation status."""
        return jsonify(dashboard.get_simulation_status(sim_id))

    @app.route('/api/alpha/<alpha_id>')
    def api_alpha_details(alpha_id):
        """API endpoint to get alpha details (优先从数据库获取)."""
        # 优先从数据库获取
        if dashboard.query_service:
            result = dashboard.get_alpha_detail_from_db(alpha_id)
            if result.get("success"):
                return jsonify(result)
        # 数据库获取失败，回退到 API
        return jsonify(dashboard.get_alpha_details(alpha_id))

    @app.route('/api/optimize-alpha/<alpha_id>', methods=['POST'])
    def api_optimize_alpha(alpha_id):
        """API endpoint to optimize alpha by ID."""
        return jsonify(dashboard.optimize_alpha_by_id(alpha_id))

    @app.route('/api/submit-alpha/<alpha_id>', methods=['POST'])
    def api_submit_alpha(alpha_id):
        """API endpoint to submit alpha to WorldQuant Brain."""
        return jsonify(dashboard.submit_alpha_by_id(alpha_id))

    @app.route('/api/failed-alphas')
    def api_failed_alphas():
        """API endpoint to get failed alphas list (从 API 获取)."""
        limit = request.args.get('limit', 20, type=int)
        return jsonify({"alphas": dashboard.get_failed_alphas(limit)})

    # ==================== 数据库相关 API ====================

    @app.route('/api/alphas')
    def api_alphas():
        """API endpoint to get alpha list from database (支持分页和筛选)."""
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        order_by = request.args.get('order', 'is_checks_pass')
        status = request.args.get('status')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        submittable = request.args.get('submittable', 'false').lower() == 'true'

        result = dashboard.get_alphas_from_db_paginated(
            page=page,
            page_size=page_size,
            order_by=order_by,
            status_filter=status,
            date_from=date_from,
            date_to=date_to,
            submittable_only=submittable
        )

        return jsonify(result)

    @app.route('/api/alpha-db/<alpha_id>')
    def api_alpha_detail_db(alpha_id):
        """API endpoint to get alpha detail from database."""
        return jsonify(dashboard.get_alpha_detail_from_db(alpha_id))

    @app.route('/api/sync', methods=['POST'])
    def api_sync():
        """API endpoint to trigger incremental sync."""
        return jsonify(dashboard.sync_incremental())

    @app.route('/api/sync/full', methods=['POST'])
    def api_sync_full():
        """API endpoint to trigger full sync."""
        return jsonify(dashboard.sync_full())

    @app.route('/api/sync/status')
    def api_sync_status():
        """API endpoint to get sync status."""
        return jsonify(dashboard.get_sync_status())

    @app.route('/alpha-db')
    def alpha_db_page():
        """Alpha database management page."""
        return render_template('alpha_db.html')
