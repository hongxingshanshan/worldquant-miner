"""
Alpha 优化器 - 分析失败的 Alpha 并生成优化版本
"""
import re
from typing import List, Dict, Optional
from datetime import datetime
import logging

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

# 优化系统提示词
OPTIMIZATION_SYSTEM_PROMPT = """
你是一个 WorldQuant Brain Alpha 表达式优化专家。
你的任务是分析失败的 Alpha 表达式，并生成优化版本以通过检查项。
保持 Alpha 的核心逻辑，只做针对性改进。
输出必须是有效的 FASTEXPR 格式表达式，不要包含任何解释、注释或代码块标记。
"""

# 优化提示词模板
OPTIMIZATION_PROMPT = """
请优化以下未通过检查的 Alpha 表达式。

## 原始 Alpha
- 表达式: {original_alpha}
- Sharpe: {sharpe:.2f}
- Fitness: {fitness:.2f}
- Turnover: {turnover:.2f}

## 失败检查项详情
{failure_details}

## 失败类型分析
{failure_analysis}

## 优化策略指南

### LOW_SHARPE (夏普值过低)
问题：风险调整后收益不足
解决：
- 增强信号强度：scale(expr), normalize(expr)
- 添加动量：ts_delta(expr, 5), ts_momentum(expr, 5)
- 使用排名：rank(expr), group_rank(expr, industry)
- 行业中性化：group_neutralize(expr, industry)
- 尝试 signed_power(expr, 0.6) 增加信号强度

### LOW_FITNESS (适应度低)
问题：Sharpe 和 Turnover 不平衡
解决：
- 优化信号质量：rank(ts_mean(expr, 5))
- 平衡收益与成本：expr - 0.1 * abs(delta(expr, 1))
- 添加时间平滑：ts_decay_linear(expr, 5)
- 确保外层有 rank() 或 ts_rank()

### CONCENTRATED_WEIGHT (权重集中)
问题：权重过于集中在少数股票
解决：
- 添加外层排名：rank(expr), ts_rank(expr, 20) - 关键！
- 行业中性化：group_neutralize(expr, industry) - 关键！
- 板块中性化：group_neutralize(expr, sector)
- 使用分散函数：zscore(expr)
- 避免极端值：winsorize(expr, 0.01)
- 时间平滑：ts_mean(expr, 5), ts_decay_linear(expr, 5)

### LOW_SUB_UNIVERSE_SHARPE (子宇宙夏普值低)
问题：在某些行业或市值范围内表现不佳
解决：
- 行业中性化：group_neutralize(expr, industry) - 最重要！
- 板块中性化：group_neutralize(expr, sector)
- 子行业中性化：group_neutralize(expr, subindustry)
- 市值标准化：divide(expr, cap)
- 回归中性化：regression_neut(expr, factor) - 中性化 Size, Beta, Momentum
- 增强信号：scale(expr), normalize(expr)

### HIGH_TURNOVER (换手率过高)
问题：交易频率过高
解决：
- 降低频率：ts_mean(expr, 10), ts_delay(expr, 1)
- 持仓平滑：ts_decay_linear(expr, 5)
- 减少噪音：ts_rank(expr, 20)
- 增加时间窗口参数

### LOW_TURNOVER (换手率过低)
问题：交易频率过低，信号衰减
解决：
- 缩短时间窗口
- 使用更敏感的操作符：ts_delta(expr, 1)
- 减少平滑层

## 高级技术（来自 WorldQuant Brain 指南）

### 中性化选项
- group_neutralize(expr, industry) - 行业中性化
- group_neutralize(expr, sector) - 板块中性化
- group_neutralize(expr, subindustry) - 子行业中性化
- regression_neut(expr, factor) - 回归中性化（用于 Size, Beta, Momentum）

### 仓位分布操作符
- rank(expr) - 均匀分布（推荐）
- signed_power(expr, 0.5-0.8) - 更极端分布，更高波动
- log(1 + abs(expr)) * sign(expr) - 对数分布

### Alpha 协同
- Trade_when(A1 > x, A2, A1 <= x) - 条件组合
- 避免简单线性组合如 3*A1 + 4*A2（不利于分散化）

## 成功模板参考
以下模板已验证成功，可作为优化参考：
1. rank(ts_zscore(divide(fundamental_field, cap), 40-80))
2. ts_rank(divide(market_field, cap), 60)
3. group_neutralize(ts_decay_linear(ts_rank(signal, 20-60), 5-10), industry)
4. group_rank(ts_rank(ratio_field, 60), industry)
5. signed_power(group_neutralize(expr, industry), 0.6)

## 可用数据字段（部分）
close, open, high, low, volume, vwap, returns, cap, sharesout, adv20
fnd6_mfma2_oancf, operating_income, est_eps, implied_volatility_call_120, implied_volatility_put_120

## 过拟合警告
- 不要过度微调细节来提高 In-Sample 性能 - 会导致 Out-Sample 性能差
- 不要让仓位过于集中在少数工具
- 关注经济意义和稳健性，而不仅仅是高 fitness 分数

## 输出要求
直接输出优化后的 Alpha 表达式，不要包含解释或注释。
保持 FASTEXPR 格式，确保语法正确。
优化后的表达式必须包含外层 rank/ts_rank/group_rank 操作符。

优化后的表达式：
"""

# 批量优化提示词模板
BATCH_OPTIMIZATION_PROMPT = """
请批量优化以下 {count} 个未通过检查的 Alpha 表达式。

## 优化规则
1. 每个 Alpha 只需要针对性修复失败的检查项
2. 保持 Alpha 的核心逻辑，只做最小改动
3. 确保优化后的表达式包含外层 rank/ts_rank/group_rank（通过 CONCENTRATED_WEIGHT 检查的关键）
4. 输出格式必须严格遵循要求

## 常见失败检查项修复方法

### LOW_SUB_UNIVERSE_SHARPE（子宇宙夏普值低）
- 行业中性化：group_neutralize(expr, industry)
- 板块中性化：group_neutralize(expr, sector)
- 市值标准化：divide(expr, cap)

### CONCENTRATED_WEIGHT（权重集中）
- 添加外层排名：rank(expr), ts_rank(expr, 20)
- 行业中性化：group_neutralize(expr, industry)

### HIGH_TURNOVER（换手率过高）
- 时间平滑：ts_decay_linear(expr, 5), ts_mean(expr, 10)
- 降低频率：ts_delay(expr, 1)

### LOW_FITNESS（适应度低）
- 信号增强：scale(expr), normalize(expr)
- 时间平滑：ts_decay_linear(expr, 5)

## Alpha 列表

{alpha_list}

## 输出格式要求
严格按照以下格式输出，每个 Alpha 一行，格式为：
[序号]|[优化后的表达式]

示例输出：
1|rank(ts_zscore(divide(fnd6_oiadps, cap), 60))
2|group_neutralize(ts_rank(divide(fnd6_newqv1300_tfvaq, cap), 60), industry)
3|ts_rank(divide(operating_income, cap), 40)

请输出优化后的表达式：
"""


class AlphaOptimizer:
    """Alpha 优化器"""

    def __init__(self, llm_client, wq_client=None, query_service=None):
        """
        初始化优化器

        Args:
            llm_client: LLM 客户端
            wq_client: WorldQuant 客户端（可选）
            query_service: 数据库查询服务（可选）
        """
        self.llm_client = llm_client
        self.wq_client = wq_client
        self.query_service = query_service
        self.optimization_history = []
        self.optimization_stats = {
            "total_attempts": 0,
            "successful": 0,
            "failed": 0
        }

    def set_query_service(self, query_service):
        """设置数据库查询服务"""
        self.query_service = query_service

    def get_optimizable_from_db(self, limit: int = 50) -> List[Dict]:
        """
        从数据库获取可优化的 Alpha（IS 检查通过 6 项，失败 1 项）

        Args:
            limit: 最大返回数量

        Returns:
            可优化的 Alpha 列表
        """
        if not self.query_service:
            logger.warning("数据库查询服务未设置，无法从数据库获取 Alpha")
            return []

        try:
            alphas = self.query_service.get_optimizable_alphas(limit=limit)
            logger.info(f"从数据库获取到 {len(alphas)} 个可优化的 Alpha（IS 检查 6 PASS / 1 FAIL）")

            # 转换为优化器需要的格式
            result = []
            for alpha in alphas:
                alpha_id = alpha['id']
                expression = alpha.get('expression', '')

                if not expression:
                    continue

                # 获取检查项详情
                checks_detail = self.query_service.get_alpha_checks_detail(alpha_id)

                # 构建 check_status 和 check_details
                check_status = {}
                check_details = []
                for check in checks_detail:
                    check_name = check['check_name']
                    result_val = check['result']
                    check_status[check_name] = result_val == 'PASS'
                    check_details.append({
                        'name': check_name,
                        'result': result_val,
                        'limit': check.get('limit_value'),
                        'value': check.get('actual_value')
                    })

                result.append({
                    'alpha_id': alpha_id,
                    'expression': expression,
                    'sharpe': alpha.get('is_sharpe', 0) or 0,
                    'fitness': alpha.get('is_fitness', 0) or 0,
                    'turnover': alpha.get('is_turnover', 0) or 0,
                    'returns': alpha.get('is_returns', 0) or 0,
                    'check_status': check_status,
                    'check_details': check_details,
                    'is_submittable': False,  # 有 1 项 FAIL，不可提交
                    'source': 'database'
                })

            logger.info(f"转换完成: {len(result)} 个 Alpha 可用于优化")
            return result

        except Exception as e:
            logger.error(f"从数据库获取可优化 Alpha 失败: {e}")
            return []

    def get_failed_alphas(self, min_sharpe: float = 1.0, limit: int = 50) -> List[Dict]:
        """
        获取失败的 Alpha（按 Sharpe 排序）

        Args:
            min_sharpe: 最低 Sharpe 阈值
            limit: 最大返回数量

        Returns:
            失败的 Alpha 列表
        """
        if not self.wq_client:
            logger.warning("WorldQuant 客户端未设置，无法获取失败的 Alpha")
            return []

        try:
            # 获取用户的 Alpha 列表
            alphas = self.wq_client.get_user_alphas()

            if not alphas:
                logger.info("未获取到任何 Alpha")
                return []

            logger.info(f"获取到 {len(alphas)} 个 Alpha，开始过滤...")

            # 过滤失败的 Alpha（未达到提交条件）
            failed = []
            for alpha in alphas:
                # 检查是否可提交
                is_submittable = alpha.get("is_submittable", False)
                check_status = alpha.get("check_status", {})
                sharpe = alpha.get("sharpe", 0)

                # 如果有任何检查项失败，则认为是失败的 Alpha
                has_failed_checks = any(
                    v == False or v == "FAIL" or v == "FAILED"
                    for v in check_status.values()
                )

                # 调试日志：显示前几个 Alpha 的状态
            sample_count = 0
            for alpha in alphas:
                is_submittable = alpha.get("is_submittable", False)
                check_status = alpha.get("check_status", {})
                sharpe = alpha.get("sharpe", 0)

                has_failed_checks = any(
                    v == False or v == "FAIL" or v == "FAILED"
                    for v in check_status.values()
                )

                if not is_submittable and has_failed_checks:
                    failed.append(alpha)

            # 按 Sharpe 排序（降序）
            failed_sorted = sorted(
                failed,
                key=lambda x: x.get("sharpe", 0),
                reverse=True
            )

            # 过滤最低 Sharpe
            result = [
                a for a in failed_sorted
                if a.get("sharpe", 0) >= min_sharpe
            ][:limit]

            logger.info(
                f"获取失败的 Alpha: 总计 {len(failed)}, "
                f"符合条件 {len(result)} (Sharpe >= {min_sharpe})"
            )

            return result

        except Exception as e:
            logger.error(f"获取失败的 Alpha 失败: {e}")
            return []

    def analyze_failure(self, alpha_data: Dict) -> Dict:
        """
        分析失败原因

        Args:
            alpha_data: Alpha 数据

        Returns:
            分析结果
        """
        checks = alpha_data.get("check_status", {})
        check_details = alpha_data.get("check_details", [])  # 详细失败信息
        failed_checks = []

        for check_name, check_result in checks.items():
            if check_result == False or check_result == "FAIL" or check_result == "FAILED":
                failed_checks.append(check_name)

        failure_types = self._classify_failures(failed_checks)

        # 构建详细的失败原因描述（只处理失败的检查项）
        failure_details = []
        for detail in check_details:
            name = detail.get('name', '')
            result = detail.get('result', '')
            limit = detail.get('limit')
            value = detail.get('value')

            # 只处理失败的检查项
            if result != 'FAIL' and result != 'FAILED':
                continue

            # 根据检查类型构建不同的描述
            if name == "CONCENTRATED_WEIGHT":
                # CONCENTRATED_WEIGHT 可能没有 limit/value，用默认描述
                if limit is not None and value is not None:
                    failure_details.append(f"{name}: 权重集中度过高 (当前值 {value:.4f} > 阈值 {limit})")
                else:
                    failure_details.append(f"{name}: 权重过于集中在少数股票")
            elif name == "LOW_SUB_UNIVERSE_SHARPE":
                if limit is not None and value is not None:
                    failure_details.append(f"{name}: 子宇宙夏普值 {value:.2f} < 阈值 {limit:.2f}")
                else:
                    failure_details.append(f"{name}: 子宇宙夏普值过低")
            elif name == "LOW_SHARPE":
                if limit is not None and value is not None:
                    failure_details.append(f"{name}: 夏普值 {value:.2f} < 阈值 {limit:.2f}")
                else:
                    failure_details.append(f"{name}: 夏普值过低")
            elif name == "LOW_FITNESS":
                if limit is not None and value is not None:
                    failure_details.append(f"{name}: 适应度 {value:.2f} < 阈值 {limit:.2f}")
                else:
                    failure_details.append(f"{name}: 适应度过低")
            elif name == "HIGH_TURNOVER":
                if limit is not None and value is not None:
                    failure_details.append(f"{name}: 换手率 {value:.2%} > 阈值 {limit:.2%}")
                else:
                    failure_details.append(f"{name}: 换手率过高")
            elif limit is not None and value is not None:
                failure_details.append(f"{name}: 当前值 {value} < 阈值 {limit}")
            elif name:
                failure_details.append(name)

        return {
            "expression": alpha_data.get("expression", ""),
            "sharpe": alpha_data.get("sharpe", 0),
            "fitness": alpha_data.get("fitness", 0),
            "turnover": alpha_data.get("turnover", 0),
            "failed_checks": failed_checks,
            "failure_types": failure_types,
            "failure_details": failure_details  # 新增：详细失败描述
        }

    def _classify_failures(self, failed_checks: List[str]) -> List[str]:
        """
        分类失败类型

        Args:
            failed_checks: 失败检查项列表

        Returns:
            失败类型列表
        """
        types = []
        for check in failed_checks:
            check_upper = check.upper()
            if "CONCENTRATED" in check_upper:
                types.append("CONCENTRATED_WEIGHT")
            elif "SUB_UNIVERSE" in check_upper:
                types.append("LOW_SUB_UNIVERSE_SHARPE")
            elif "TURNOVER" in check_upper:
                types.append("HIGH_TURNOVER")
            elif "FITNESS" in check_upper:
                types.append("LOW_FITNESS")
            elif "SHARPE" in check_upper:
                types.append("LOW_SHARPE")
            else:
                types.append(check)
        return list(set(types))  # 去重

    def optimize_alpha(self, alpha_data: Dict, temperature: float = 0.5) -> Dict:
        """
        优化单个 Alpha

        Args:
            alpha_data: Alpha 数据
            temperature: LLM 温度参数

        Returns:
            优化结果
        """
        self.optimization_stats["total_attempts"] += 1

        analysis = self.analyze_failure(alpha_data)

        if not analysis["failure_types"]:
            logger.warning(f"未识别失败类型: {analysis['failed_checks']}")
            analysis["failure_types"] = ["UNKNOWN"]

        # 构建优化提示词
        prompt = self._build_optimization_prompt(analysis)

        try:
            # 调用 LLM 优化
            optimized = self.llm_client.generate(
                prompt=prompt,
                system_prompt=OPTIMIZATION_SYSTEM_PROMPT,
                temperature=temperature
            )

            # 清理输出
            optimized_alpha = self._clean_alpha_expression(optimized)

            if not optimized_alpha:
                raise ValueError("LLM 未返回有效的 Alpha 表达式")

            result = {
                "original": alpha_data.get("expression", ""),
                "optimized": optimized_alpha,
                "failure_type": analysis["failure_types"][0],
                "original_metrics": {
                    "sharpe": analysis["sharpe"],
                    "fitness": analysis["fitness"],
                    "turnover": analysis["turnover"]
                },
                "success": True,
                "timestamp": datetime.now().isoformat()
            }

            self.optimization_stats["successful"] += 1
            self.optimization_history.append(result)

            logger.info(
                f"优化成功: {result['original'][:30]}... → {result['optimized'][:30]}..."
            )

            return result

        except Exception as e:
            self.optimization_stats["failed"] += 1
            logger.error(f"优化失败: {e}")

            return {
                "original": alpha_data.get("expression", ""),
                "optimized": None,
                "failure_type": analysis["failure_types"][0] if analysis["failure_types"] else "UNKNOWN",
                "original_metrics": {
                    "sharpe": analysis["sharpe"],
                    "fitness": analysis["fitness"],
                    "turnover": analysis["turnover"]
                },
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def optimize_batch(self, alphas: List[Dict], temperature: float = 0.5) -> List[Dict]:
        """
        批量优化多个 Alpha（一次 LLM 调用）

        Args:
            alphas: Alpha 数据列表
            temperature: LLM 温度参数

        Returns:
            优化结果列表
        """
        if not alphas:
            return []

        self.optimization_stats["total_attempts"] += len(alphas)

        # 构建批量提示词
        alpha_list = []
        for i, alpha in enumerate(alphas, 1):
            expr = alpha.get("expression", "")
            sharpe = alpha.get("sharpe", 0) or 0
            fitness = alpha.get("fitness", 0) or 0
            turnover = alpha.get("turnover", 0) or 0
            failed_checks = alpha.get("failed_checks", [])

            alpha_list.append(f"""
### Alpha {i}
- 表达式: {expr}
- Sharpe: {sharpe:.2f}
- Fitness: {fitness:.2f}
- Turnover: {turnover:.4f}
- 失败检查项: {', '.join(failed_checks) if failed_checks else '未知'}
""")

        prompt = BATCH_OPTIMIZATION_PROMPT.format(
            count=len(alphas),
            alpha_list="\n".join(alpha_list)
        )

        try:
            logger.info(f"批量优化 {len(alphas)} 个 Alpha（单次 LLM 调用）")

            # 调用 LLM
            response = self.llm_client.generate(
                system_prompt=OPTIMIZATION_SYSTEM_PROMPT,
                prompt=prompt,
                temperature=temperature
            )

            # 解析批量结果
            results = self._parse_batch_results(response, alphas)

            # 更新统计
            self.optimization_stats["successful"] += len(results)
            self.optimization_stats["failed"] += len(alphas) - len(results)

            logger.info(f"批量优化完成: 成功 {len(results)}/{len(alphas)}")

            return results

        except Exception as e:
            self.optimization_stats["failed"] += len(alphas)
            logger.error(f"批量优化失败: {e}")
            return []

    def _parse_batch_results(self, response: str, original_alphas: List[Dict]) -> List[Dict]:
        """
        解析批量优化结果

        Args:
            response: LLM 响应文本
            original_alphas: 原始 Alpha 列表

        Returns:
            优化结果列表
        """
        results = []
        lines = response.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or "|" not in line:
                continue

            try:
                # 解析格式: [序号]|[表达式]
                parts = line.split("|", 1)
                if len(parts) != 2:
                    continue

                idx = int(parts[0].strip()) - 1  # 转为 0-based 索引
                optimized_expr = parts[1].strip()

                if idx < 0 or idx >= len(original_alphas):
                    continue

                original = original_alphas[idx]

                # 验证表达式
                if self._validate_expression(optimized_expr):
                    result = {
                        "success": True,
                        "original": original.get("expression"),
                        "optimized": optimized_expr,
                        "alpha_id": original.get("id"),
                        "original_metrics": {
                            "sharpe": original.get("sharpe"),
                            "fitness": original.get("fitness"),
                            "turnover": original.get("turnover")
                        },
                        "failure_type": original.get("failed_checks", ["UNKNOWN"])[0] if original.get("failed_checks") else "UNKNOWN",
                        "timestamp": datetime.now().isoformat()
                    }
                    results.append(result)
                    self.optimization_history.append(result)

                    logger.info(
                        f"优化成功 [{idx+1}]: {original.get('expression', '')[:30]}... → {optimized_expr[:30]}..."
                    )

            except Exception as e:
                logger.warning(f"解析行失败: {line}, 错误: {e}")
                continue

        return results

    def _validate_expression(self, expr: str) -> bool:
        """
        验证 Alpha 表达式基本有效性

        Args:
            expr: 表达式字符串

        Returns:
            是否有效
        """
        if not expr or len(expr) < 5:
            return False

        # 检查括号匹配
        if expr.count("(") != expr.count(")"):
            return False

        # 检查是否包含外层排名操作符
        outer_operators = ["rank(", "ts_rank(", "group_rank("]
        has_outer_rank = any(expr.strip().startswith(op) for op in outer_operators)

        return has_outer_rank

    def optimize_top_failed(self, top_n: int = 5, min_sharpe: float = 1.0,
                           temperature: float = 0.5, use_db: bool = False,
                           batch_mode: bool = True) -> List[Dict]:
        """
        优化前 N 个失败的 Alpha

        Args:
            top_n: 优化数量
            min_sharpe: 最低 Sharpe 阈值（仅 API 模式使用）
            temperature: LLM 温度参数
            use_db: 是否从数据库获取优化候选（IS 检查 6 PASS, 1 FAIL）
            batch_mode: 是否使用批量优化模式（默认 True，一次 LLM 调用优化所有 Alpha）

        Returns:
            优化结果列表
        """
        # 根据模式选择数据源
        if use_db:
            if not self.query_service:
                logger.error("数据库服务不可用，无法从数据库获取优化候选")
                return []
            failed_alphas = self.get_optimizable_from_db(limit=top_n)
            logger.info(f"从数据库获取到 {len(failed_alphas)} 个优化候选（IS 检查 6 PASS, 1 FAIL）")
        else:
            failed_alphas = self.get_failed_alphas(min_sharpe=min_sharpe, limit=top_n)

        if not failed_alphas:
            logger.info("没有符合条件的失败 Alpha 需要优化")
            return []

        # 选择优化模式
        if batch_mode and len(failed_alphas) > 1:
            logger.info(f"批量优化模式: 一次性优化 {len(failed_alphas)} 个 Alpha")
            results = self.optimize_batch(failed_alphas, temperature)
        else:
            logger.info(f"逐个优化模式: 优化 {len(failed_alphas)} 个 Alpha")
            results = []
            for i, alpha_data in enumerate(failed_alphas, 1):
                logger.info(f"优化进度: {i}/{len(failed_alphas)}")
                try:
                    result = self.optimize_alpha(alpha_data, temperature)
                    if result.get("success") and result.get("optimized"):
                        results.append(result)
                except Exception as e:
                    logger.error(f"优化第 {i} 个 Alpha 失败: {e}")

        logger.info(f"优化完成: 成功 {len(results)}/{len(failed_alphas)}")
        return results

    def _build_optimization_prompt(self, analysis: Dict) -> str:
        """
        构建优化提示词

        Args:
            analysis: 分析结果

        Returns:
            提示词字符串
        """
        # 构建失败详情描述
        failure_details = analysis.get("failure_details", [])
        if failure_details:
            details_text = "\n".join(f"- {d}" for d in failure_details)
        else:
            # 回退到旧的 failed_checks
            details_text = ", ".join(analysis.get("failed_checks", ["未知"]))

        return OPTIMIZATION_PROMPT.format(
            original_alpha=analysis["expression"],
            sharpe=analysis["sharpe"],
            fitness=analysis["fitness"],
            turnover=analysis["turnover"],
            failure_details=details_text,
            failure_analysis=self._get_failure_analysis(analysis["failure_types"])
        )

    def _get_failure_analysis(self, failure_types: List[str]) -> str:
        """
        获取失败原因分析

        Args:
            failure_types: 失败类型列表

        Returns:
            分析文本
        """
        analysis_map = {
            "CONCENTRATED_WEIGHT": "权重过于集中在少数股票上，需要添加平滑或分散操作",
            "LOW_SUB_UNIVERSE_SHARPE": "子宇宙夏普值低，信号强度不足或噪音过大",
            "HIGH_TURNOVER": "换手率过高，交易频率需要降低",
            "LOW_FITNESS": "适应度低，需要平衡 Sharpe 和 Turnover",
            "LOW_SHARPE": "夏普值过低，信号质量需要提升",
            "UNKNOWN": "未知失败原因，尝试通用优化策略"
        }

        lines = []
        for t in failure_types:
            lines.append(f"- {t}: {analysis_map.get(t, analysis_map['UNKNOWN'])}")

        return "\n".join(lines) if lines else "- 未识别具体失败原因"

    def _clean_alpha_expression(self, text: str) -> Optional[str]:
        """
        清理 LLM 输出的 Alpha 表达式

        Args:
            text: LLM 输出文本

        Returns:
            清理后的表达式
        """
        if not text:
            return None

        # 移除代码块标记
        text = re.sub(r'```[\w]*\n?', '', text)
        text = re.sub(r'```', '', text)

        # 移除注释
        text = re.sub(r'#.*$', '', text, flags=re.MULTILINE)

        # 移除多余空白
        text = text.strip()

        # 如果有多行，取第一行非空行
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if lines:
            text = lines[0]

        # 基本验证：表达式不应包含解释性文字
        invalid_keywords = ['优化', '解决', '问题', '策略', '输出', '要求']
        if any(kw in text for kw in invalid_keywords):
            # 尝试提取表达式部分
            # 查找可能的表达式（包含数据字段或操作符）
            for line in lines:
                if any(field in line for field in ['close', 'open', 'volume', 'rank', 'ts_']):
                    text = line
                    break

        return text if text else None

    def get_stats(self) -> Dict:
        """
        获取优化统计

        Returns:
            统计数据
        """
        return {
            "total_attempts": self.optimization_stats["total_attempts"],
            "successful": self.optimization_stats["successful"],
            "failed": self.optimization_stats["failed"],
            "success_rate": (
                self.optimization_stats["successful"] / self.optimization_stats["total_attempts"] * 100
                if self.optimization_stats["total_attempts"] > 0 else 0
            ),
            "history_size": len(self.optimization_history)
        }

    def set_wq_client(self, wq_client):
        """
        设置 WorldQuant 客户端

        Args:
            wq_client: WorldQuant 客户端
        """
        self.wq_client = wq_client
        logger.info("已设置 WorldQuant 客户端")

    def optimize_by_alpha_id(self, alpha_id: str, temperature: float = 0.5) -> Dict:
        """
        根据 Alpha ID 获取并优化指定的 Alpha

        Args:
            alpha_id: WorldQuant Brain Alpha ID
            temperature: LLM 温度参数

        Returns:
            优化结果
        """
        if not self.wq_client:
            return {
                "success": False,
                "error": "WorldQuant 客户端未设置",
                "alpha_id": alpha_id
            }

        try:
            # 从 API 获取 Alpha 详情
            alpha_data = self._get_alpha_by_id(alpha_id)

            if not alpha_data:
                return {
                    "success": False,
                    "error": f"未找到 Alpha ID: {alpha_id}",
                    "alpha_id": alpha_id
                }

            # 检查是否可提交
            is_submittable = alpha_data.get("is_submittable", False)
            if is_submittable:
                return {
                    "success": False,
                    "error": "该 Alpha 已通过所有检查，无需优化",
                    "alpha_id": alpha_id,
                    "expression": alpha_data.get("expression", "")
                }

            # 执行优化
            result = self.optimize_alpha(alpha_data, temperature)
            result["alpha_id"] = alpha_id
            return result

        except Exception as e:
            logger.error(f"优化 Alpha {alpha_id} 失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "alpha_id": alpha_id
            }

    def _get_alpha_by_id(self, alpha_id: str) -> Optional[Dict]:
        """
        根据 Alpha ID 获取单个 Alpha 的详细信息

        Args:
            alpha_id: WorldQuant Brain Alpha ID

        Returns:
            Alpha 详细信息（优化器格式）
        """
        try:
            # 使用 wq_client 的 session 获取 Alpha 详情
            sess = self.wq_client.sess if hasattr(self.wq_client, 'sess') else None
            if not sess:
                logger.error("无法获取 WorldQuant session")
                return None

            response = sess.get(
                f'https://api.worldquantbrain.com/alphas/{alpha_id}',
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                # 转换为优化器需要的格式
                return self._convert_alpha_to_optimizer_format(data)
            elif response.status_code == 404:
                logger.warning(f"Alpha {alpha_id} 不存在")
                return None
            else:
                logger.error(f"获取 Alpha {alpha_id} 失败: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"API 调用失败: {e}")
            return None

    def _convert_alpha_to_optimizer_format(self, data: Dict) -> Dict:
        """
        将 API 返回的 Alpha 数据转换为优化器需要的格式

        Args:
            data: API 返回的原始数据

        Returns:
            优化器格式的数据
        """
        expression = data.get('regular', {}).get('code', '').strip()
        if not expression:
            return None

        is_data = data.get('is', {})
        checks = is_data.get('checks', [])
        status = data.get('status', '')

        # 将 checks 数组转换为 check_status 字典
        check_status = {}
        check_details = []
        for check in checks:
            check_name = check.get('name', '')
            check_result = check.get('result', '')
            check_status[check_name] = check_result

            # 保存失败检查的详细信息
            if check_result == 'FAIL':
                check_details.append({
                    'name': check_name,
                    'result': check_result,
                    'limit': check.get('limit'),
                    'value': check.get('value')
                })

        # 判断是否可提交
        is_submittable = status != 'UNSUBMITTED' and all(
            c.get('result') == 'PASS'
            for c in checks
        )

        return {
            'expression': expression,
            'sharpe': is_data.get('sharpe', 0),
            'fitness': is_data.get('fitness', 0),
            'turnover': is_data.get('turnover', 0),
            'is_submittable': is_submittable,
            'check_status': check_status,
            'check_details': check_details,
            'alpha_id': data.get('id')
        }

    def optimize_and_submit(self, alpha_id: str, temperature: float = 0.5) -> Dict:
        """
        优化 Alpha 并提交到 WorldQuant Brain

        Args:
            alpha_id: WorldQuant Brain Alpha ID
            temperature: LLM 温度参数

        Returns:
            优化和提交结果
        """
        if not self.wq_client:
            return {
                "success": False,
                "error": "WorldQuant 客户端未设置",
                "alpha_id": alpha_id
            }

        try:
            # 1. 获取 Alpha 详情
            alpha_data = self._get_alpha_by_id(alpha_id)
            if not alpha_data:
                return {
                    "success": False,
                    "error": f"未找到 Alpha ID: {alpha_id}",
                    "alpha_id": alpha_id
                }

            # 2. 执行优化
            opt_result = self.optimize_alpha(alpha_data, temperature)
            if not opt_result.get("success"):
                return {
                    "success": False,
                    "error": f"优化失败: {opt_result.get('error', '未知错误')}",
                    "alpha_id": alpha_id,
                    "original": alpha_data.get("expression")
                }

            optimized_expr = opt_result.get("optimized")
            if not optimized_expr:
                return {
                    "success": False,
                    "error": "LLM 未返回有效的优化表达式",
                    "alpha_id": alpha_id,
                    "original": alpha_data.get("expression")
                }

            logger.info(f"优化成功: {alpha_data.get('expression')} -> {optimized_expr}")

            # 3. 测试优化后的表达式（带来源追踪）
            original_expr = alpha_data.get("expression")
            failure_type = opt_result.get("failure_type", "UNKNOWN")
            test_result = self._test_alpha(
                optimized_expr,
                original_alpha=original_expr,
                opt_type=failure_type
            )

            # 提取模拟任务 ID
            sim_id = None
            if test_result.get("success") and test_result.get("result"):
                result_data = test_result["result"]
                # result_data 是 test_alpha_with_source 的返回值
                # 结构: {"status": "success", "result": {"id": sim_id, ...}, "source": ...}
                if isinstance(result_data, dict):
                    # 检查是否有嵌套的 result
                    if result_data.get("status") == "success" and result_data.get("result"):
                        inner_result = result_data.get("result")
                        if isinstance(inner_result, dict):
                            sim_id = inner_result.get("id")
                    else:
                        # 直接尝试获取 id
                        sim_id = result_data.get("id")

            # 返回优化结果（模拟已由 _test_alpha 提交）
            return {
                "success": True,
                "alpha_id": alpha_id,
                "original": alpha_data.get("expression"),
                "optimized": optimized_expr,
                "simulation_id": sim_id,
                "message": "优化成功，已提交模拟测试"
            }

        except Exception as e:
            logger.error(f"优化并提交 Alpha {alpha_id} 失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "alpha_id": alpha_id
            }

    def _test_alpha(self, expression: str, original_alpha: str = None, opt_type: str = None) -> Dict:
        """
        测试 Alpha 表达式

        Args:
            expression: Alpha 表达式
            original_alpha: 原始表达式（优化时）
            opt_type: 优化类型（优化时）

        Returns:
            测试结果
        """
        try:
            if hasattr(self.wq_client, 'test_alpha_with_source'):
                # 使用带来源追踪的测试方法
                result = self.wq_client.test_alpha_with_source(
                    alpha=expression,
                    source="optimized",
                    original_alpha=original_alpha,
                    opt_type=opt_type
                )
                return {"success": True, "result": result}
            elif hasattr(self.wq_client, 'test_alpha'):
                result = self.wq_client.test_alpha(expression)
                return {"success": True, "result": result}
            else:
                logger.warning("wq_client 没有 test_alpha 方法")
                return {"success": True, "result": "跳过测试"}
        except Exception as e:
            logger.error(f"测试 Alpha 失败: {e}")
            return {"success": False, "error": str(e)}
