"""
Web Dashboard API 处理函数

从 web_dashboard.py 拆分出来，包含所有 Flask 路由处理函数
"""
import sys
import os
from pathlib import Path
from flask import request, jsonify, render_template

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 向量数据库相关导入
try:
    import chromadb
    from vector_store.embedding import EmbeddingModel
    from vector_store.store import VectorStore
    VECTOR_DB_AVAILABLE = True
    VECTOR_DB_PATH = project_root / 'vector_store' / 'chroma_db'
    vector_embedder = None
    VECTOR_DB_ERROR = None
except ImportError as e:
    VECTOR_DB_AVAILABLE = False
    VECTOR_DB_ERROR = str(e)


def get_vector_embedder():
    """获取向量嵌入模型（延迟初始化）"""
    global vector_embedder
    if vector_embedder is None and VECTOR_DB_AVAILABLE:
        vector_embedder = EmbeddingModel()
    return vector_embedder


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

    @app.route('/api/submit-batch', methods=['POST'])
    def api_submit_batch():
        """API endpoint to batch submit submittable alphas."""
        limit = request.args.get('limit', 10, type=int)
        dry_run = request.args.get('dry_run', 'false').lower() == 'true'
        return jsonify(dashboard.submit_batch_alphas(limit=limit, dry_run=dry_run))

    @app.route('/api/submittable-count')
    def api_submittable_count():
        """API endpoint to get count of submittable alphas."""
        return jsonify(dashboard.get_submittable_count())

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

    # ==================== 向量数据库相关 API ====================

    @app.route('/vector-db')
    def vector_db_page():
        """向量数据库管理页面"""
        return render_template('vector_db.html')

    @app.route('/api/vector/stats')
    def api_vector_stats():
        """向量数据库统计信息"""
        if not VECTOR_DB_AVAILABLE:
            return jsonify({'error': f'向量数据库不可用: {VECTOR_DB_ERROR}'}), 500

        try:
            client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
            collection = client.get_collection('knowledge_chunks')
            return jsonify({
                'collection': collection.name,
                'count': collection.count(),
                'path': str(VECTOR_DB_PATH),
                'model': 'paraphrase-multilingual-MiniLM-L12-v2'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/vector/browse')
    def api_vector_browse():
        """浏览向量数据库数据"""
        if not VECTOR_DB_AVAILABLE:
            return jsonify({'error': '向量数据库不可用'}), 500

        try:
            limit = int(request.args.get('limit', 10))
            client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
            collection = client.get_collection('knowledge_chunks')

            result = collection.get(limit=limit, include=['documents', 'metadatas'])

            results = []
            for i in range(len(result['ids'])):
                results.append({
                    'id': result['ids'][i],
                    'document': result['documents'][i] if result['documents'] else '',
                    'metadata': result['metadatas'][i] if result['metadatas'] else {}
                })

            return jsonify({'count': len(results), 'results': results})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/vector/filter')
    def api_vector_filter():
        """条件查询向量数据库"""
        if not VECTOR_DB_AVAILABLE:
            return jsonify({'error': '向量数据库不可用'}), 500

        try:
            limit = int(request.args.get('limit', 10))
            layer = request.args.get('layer', '')
            category = request.args.get('category', '')

            client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
            collection = client.get_collection('knowledge_chunks')

            where_filter = {}
            if layer:
                where_filter['layer'] = layer
            if category:
                where_filter['category'] = category

            result = collection.get(
                where=where_filter if where_filter else None,
                limit=limit,
                include=['documents', 'metadatas']
            )

            results = []
            for i in range(len(result['ids'])):
                results.append({
                    'id': result['ids'][i],
                    'document': result['documents'][i] if result['documents'] else '',
                    'metadata': result['metadatas'][i] if result['metadatas'] else {}
                })

            return jsonify({'count': len(results), 'results': results})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/vector/search', methods=['POST'])
    def api_vector_search():
        """语义搜索向量数据库"""
        if not VECTOR_DB_AVAILABLE:
            return jsonify({'error': '向量数据库不可用'}), 500

        try:
            data = request.json
            query = data.get('query', '')
            limit = int(data.get('limit', 5))

            if not query:
                return jsonify({'error': '查询内容不能为空'}), 400

            client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
            collection = client.get_collection('knowledge_chunks')

            # 生成查询向量
            emb = get_vector_embedder()
            query_embedding = emb.embed_query(query)

            result = collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                include=['documents', 'metadatas', 'distances']
            )

            results = []
            if result['documents'] and result['documents'][0]:
                for i in range(len(result['ids'][0])):
                    distance = result['distances'][0][i] if result['distances'] else 0
                    similarity = max(0, 1 - distance / 2)
                    results.append({
                        'id': result['ids'][0][i],
                        'document': result['documents'][0][i] if result['documents'] else '',
                        'metadata': result['metadatas'][0][i] if result['metadatas'] else {},
                        'distance': distance,
                        'similarity': similarity
                    })

            return jsonify({'count': len(results), 'results': results})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
