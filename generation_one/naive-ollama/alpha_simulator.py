"""
Alpha 模拟器模块

从 alpha_generator_ollama.py 拆分出来，负责：
- 重试队列管理
- 消费者线程（从队列获取 Alpha 并提交测试）
"""
import time
from queue import Queue
from threading import Thread
from time import sleep
from typing import List, Dict

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class RetryQueue:
    """重试队列：处理限流后需要重试的 Alpha"""

    def __init__(self, generator, max_retries=3, retry_delay=60):
        self.queue = Queue()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.generator = generator  # Store reference to generator
        self.worker = Thread(target=self._process_queue, daemon=True)
        self.worker.start()

    def add(self, alpha: str, retry_count: int = 0):
        self.queue.put((alpha, retry_count))

    def _process_queue(self):
        while True:
            if not self.queue.empty():
                alpha, retry_count = self.queue.get()
                if retry_count >= self.max_retries:
                    logger.error(f"Max retries exceeded for alpha: {alpha}")
                    continue

                try:
                    result = self.generator._test_alpha_impl(alpha)  # Use _test_alpha_impl to avoid recursion
                    if result.get("status") == "error" and "SIMULATION_LIMIT_EXCEEDED" in result.get("message", ""):
                        logger.info(f"Simulation limit exceeded, requeueing alpha: {alpha}")
                        time.sleep(self.retry_delay)
                        self.add(alpha, retry_count + 1)
                    else:
                        self.generator.results.append({
                            "alpha": alpha,
                            "result": result
                        })
                except Exception as e:
                    logger.error(f"Error processing alpha: {str(e)}")

            time.sleep(1)  # Prevent busy waiting


class AlphaConsumer(Thread):
    """消费者线程：持续从队列获取 Alpha 并提交测试

    与生产者（生成/优化）解耦，独立运行
    """

    def __init__(self, generator, check_interval: int = 5, batch_size: int = 10):
        super().__init__(daemon=True)
        self.generator = generator
        self.check_interval = check_interval  # 检查队列的间隔（秒）
        self.batch_size = batch_size  # 每次批量提交的数量
        self.running = True
        self.name = "AlphaConsumer"

    def run(self):
        """消费者主循环"""
        logger.info("🚀 Alpha 消费者线程启动")
        consecutive_rate_limits = 0  # 连续限流计数

        while self.running:
            try:
                # 1. 检查队列中是否有待测试的 Alpha
                if self.generator.alpha_queue:
                    queue_size = len(self.generator.alpha_queue)
                    if queue_size > 0:
                        # 如果之前连续限流，增加等待时间
                        if consecutive_rate_limits > 0:
                            wait_time = min(30, 5 * consecutive_rate_limits)
                            logger.info(f"⏳ 检测到连续限流，等待 {wait_time} 秒后重试...")
                            sleep(wait_time)

                        logger.info(f"📦 队列中有 {queue_size} 个待测试 Alpha")

                        # 获取一批 Alpha
                        batch = self.generator.alpha_queue.get_next_batch(batch_size=self.batch_size)
                        if batch:
                            batch_size_before = len(batch)
                            self._submit_batch(batch)

                            # 输出当前队列剩余数量
                            if self.generator.alpha_queue:
                                remaining = len(self.generator.alpha_queue)
                                logger.info(f"📋 当前队列剩余: {remaining} 个 Alpha 待测试")

                            # 检查是否有限流发生（通过队列大小变化判断）
                            if self.generator.alpha_queue:
                                current_queue_size = len(self.generator.alpha_queue)
                                # 如果队列大小增加，说明有 Alpha 被放回
                                if current_queue_size > queue_size - batch_size_before:
                                    consecutive_rate_limits += 1
                                    logger.warning(f"🚫 检测到限流，连续限流次数: {consecutive_rate_limits}")
                                else:
                                    consecutive_rate_limits = 0  # 重置计数

                # 2. 检查待处理结果
                if self.generator.pending_results:
                    pending_count = len(self.generator.pending_results)
                    if pending_count > 0:
                        logger.info(f"⏳ 检查 {pending_count} 个待处理模拟结果")
                        self.generator.check_pending_results_with_source()

                # 3. 等待下一轮（如果限流则等待更长时间）
                base_interval = self.check_interval
                if consecutive_rate_limits > 0:
                    base_interval = min(30, self.check_interval * (1 + consecutive_rate_limits))
                sleep(base_interval)

            except Exception as e:
                logger.error(f"消费者线程错误: {e}")
                sleep(10)  # 错误后等待更长时间

        logger.info("🛑 Alpha 消费者线程停止")

    def _submit_batch(self, batch: List[Dict]):
        """提交一批 Alpha 进行测试

        限流时将未提交的 Alpha 放回队列头部，避免浪费
        """
        logger.info(f"📤 提交 {len(batch)} 个 Alpha 进行测试")

        max_concurrent = self.generator.executor._max_workers
        submitted = 0
        rate_limited = False  # 标记是否遇到限流
        unsubmitted_items = []  # 未成功提交的 Alpha

        for i in range(0, len(batch), max_concurrent):
            chunk = batch[i:i + max_concurrent]

            # 如果已经遇到限流，直接将剩余 Alpha 放回队列
            if rate_limited:
                unsubmitted_items.extend(chunk)
                logger.info(f"⚠️ 因限流，{len(chunk)} 个 Alpha 将放回队列")
                continue

            futures = []
            for item in chunk:
                alpha = item["expression"]
                future = self.generator.executor.submit(
                    self.generator._test_alpha_impl, alpha
                )
                futures.append((item, future))

            # 处理结果
            for item, future in futures:
                alpha = item["expression"]
                try:
                    result = future.result()

                    if result.get("status") == "error":
                        error_msg = result.get("message", "")
                        if "SIMULATION_LIMIT_EXCEEDED" in error_msg or "429" in error_msg or "CONCURRENT" in error_msg:
                            # 限流：将 Alpha 放回队列头部
                            rate_limited = True
                            unsubmitted_items.append(item)
                            logger.warning(f"🚫 限流: {alpha[:50]}... 将放回队列")
                        else:
                            logger.error(f"模拟错误: {error_msg}")
                            # 记录失败
                            if self.generator.alpha_queue:
                                self.generator.alpha_queue.record_result(item, {
                                    "passed": False,
                                    "error": error_msg
                                })
                        continue

                    sim_id = result.get("result", {}).get("id")
                    progress_url = result.get("result", {}).get("progress_url")

                    if sim_id and progress_url:
                        self.generator.pending_results[sim_id] = {
                            "alpha": alpha,
                            "progress_url": progress_url,
                            "status": "pending",
                            "attempts": 0,
                            "source": item.get("source", "unknown"),
                            "original_alpha": item.get("original_alpha"),
                            "opt_type": item.get("optimization_type"),
                            "queue_item": item
                        }
                        submitted += 1
                        logger.info(f"✅ 提交成功: {alpha[:50]}... (ID: {sim_id})")
                    else:
                        # 没有获得 sim_id，也算失败，放回队列
                        unsubmitted_items.append(item)
                        logger.warning(f"⚠️ 未获得模拟ID: {alpha[:50]}... 将放回队列")

                except Exception as e:
                    logger.error(f"提交错误 {alpha[:50]}: {e}")
                    # 异常情况也放回队列
                    unsubmitted_items.append(item)

            # 批次间等待
            if i + max_concurrent < len(batch) and not rate_limited:
                sleep(5)

        # 将未提交的 Alpha 放回队列头部（优先处理）
        # 先过滤掉重复的和已模拟的
        valid_items = []
        skipped_duplicates = 0
        skipped_simulated = 0

        for item in unsubmitted_items:
            alpha = item["expression"]

            # 1. 检查是否已在队列中（避免重复）
            if self.generator.alpha_queue:
                is_duplicate = any(
                    existing["expression"] == alpha
                    for existing in self.generator.alpha_queue.queue
                )
                if is_duplicate:
                    skipped_duplicates += 1
                    logger.debug(f"跳过重复: {alpha[:50]}...")
                    continue

            # 2. 检查是否已经模拟过
            if self.generator._is_already_simulated(alpha):
                skipped_simulated += 1
                logger.debug(f"跳过已模拟: {alpha[:50]}...")
                continue

            valid_items.append(item)

        # 放回队列头部
        if valid_items and self.generator.alpha_queue:
            for item in reversed(valid_items):
                self.generator.alpha_queue.queue.appendleft(item)
            logger.info(f"🔄 已将 {len(valid_items)} 个 Alpha 放回队列头部")

        if skipped_duplicates > 0 or skipped_simulated > 0:
            logger.info(f"📋 放回时过滤: {skipped_duplicates} 个重复, {skipped_simulated} 个已模拟")

        logger.info(f"📊 批次提交完成: {submitted}/{len(batch)} 成功, {len(valid_items)} 放回队列")

    def stop(self):
        """停止消费者线程"""
        self.running = False
