# -*- coding: utf-8 -*-
"""
Alpha 向量同步启动脚本

定时将 MySQL 中的 Alpha 数据同步到向量数据库
"""

import sys
import os
import time
import json
import logging
import schedule
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vector_store.alpha_vector_sync import AlphaVectorSync
from db.db_connector import MySQLConnector

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_db_config() -> dict:
    """加载数据库配置"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'db', 'db_config.json'
    )

    if not os.path.exists(config_path):
        logger.error(f"配置文件不存在: {config_path}")
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def sync_job(full_sync: bool = False):
    """同步任务"""
    logger.info("=" * 50)
    logger.info(f"开始同步任务 - {datetime.now().isoformat()}")
    logger.info("=" * 50)

    try:
        db_config = load_db_config()
        db_connector = MySQLConnector(db_config)

        sync_service = AlphaVectorSync(db_connector)

        if full_sync:
            logger.info("执行全量同步...")
            stats = sync_service.full_sync()
            logger.info(f"全量同步完成: {stats}")
        else:
            logger.info("执行增量同步...")

            # 同步已提交 Alpha（最高优先级）
            submitted_count = sync_service.sync_submitted_alphas(limit=100)
            logger.info(f"同步已提交 Alpha: {submitted_count}")

            # 同步可提交 Alpha（次优先级）
            submittable_count = sync_service.sync_submittable_alphas(limit=100)
            logger.info(f"同步可提交 Alpha: {submittable_count}")

            # 同步失败 Alpha
            failure_count = sync_service.sync_failure_alphas(limit=200)
            logger.info(f"同步失败 Alpha: {failure_count}")

            # 同步优化案例
            opt_count = sync_service.sync_optimization_cases()
            logger.info(f"同步优化案例: {opt_count}")

        # 打印统计信息
        stats = sync_service.get_stats()
        logger.info(f"向量数据库统计: {stats}")

    except Exception as e:
        logger.error(f"同步任务失败: {e}")
        raise

    logger.info("=" * 50)
    logger.info(f"同步任务完成 - {datetime.now().isoformat()}")
    logger.info("=" * 50)


def main():
    """主函数"""
    logger.info("Alpha 向量同步服务启动")

    # 立即执行一次增量同步
    logger.info("执行初始同步...")
    sync_job(full_sync=False)

    # 每小时执行增量同步
    schedule.every(1).hours.do(lambda: sync_job(full_sync=False))

    # 每天凌晨 3 点执行全量同步
    schedule.every().day.at("03:00").do(lambda: sync_job(full_sync=True))

    logger.info("定时任务已配置:")
    logger.info("  - 每小时: 增量同步")
    logger.info("  - 每天 03:00: 全量同步")

    # 运行调度
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    # 支持命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--full":
            # 全量同步
            sync_job(full_sync=True)
        elif sys.argv[1] == "--incremental":
            # 增量同步
            sync_job(full_sync=False)
        elif sys.argv[1] == "--stats":
            # 查看统计
            db_config = load_db_config()
            db_connector = MySQLConnector(db_config)
            sync_service = AlphaVectorSync(db_connector)
            stats = sync_service.get_stats()
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        elif sys.argv[1] == "--daemon":
            # 后台运行
            main()
        else:
            print("用法:")
            print("  python sync_alpha_vectors.py --full        # 全量同步")
            print("  python sync_alpha_vectors.py --incremental # 增量同步")
            print("  python sync_alpha_vectors.py --stats       # 查看统计")
            print("  python sync_alpha_vectors.py --daemon      # 后台运行")
    else:
        # 默认增量同步
        sync_job(full_sync=False)