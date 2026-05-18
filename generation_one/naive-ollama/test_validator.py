"""
测试本地 Alpha 验证器集成

演示如何在不提交到 WorldQuant Brain 平台的情况下，
使用本地验证器预筛选 Alpha 表达式
"""

import sys
import os

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# 直接导入模块
from alpha_validator import AlphaValidator


def test_validator():
    """测试验证器基本功能"""
    print("=" * 60)
    print("测试 AlphaValidator 本地验证器")
    print("=" * 60)

    validator = AlphaValidator()

    # 测试用例：包含各种情况的 Alpha 表达式
    test_expressions = [
        # ✅ 好的表达式
        "rank(ts_zscore(divide(close, cap), 60))",
        "ts_rank(divide(volume, cap), 40)",
        "group_neutralize(ts_decay_linear(returns, 10), industry)",
        "rank(ts_mean(divide(fnd6_oiadps, cap), 60))",
        "group_rank(ts_corr(close, volume, 40), industry)",

        # ⚠️ 缺少外层排名
        "divide(close, cap)",
        "ts_mean(returns, 60)",
        "ts_zscore(volume, 40)",

        # ⚠️ 财务数据缺少市值标准化
        "rank(fnd6_oiadps)",
        "ts_rank(fnd2_eps, 60)",

        # ❌ 事件数据 + 时间序列（冲突）
        "ts_rank(nws12_sentiment, 20)",
        "ts_mean(fnd6_newqeventv, 40)",

        # ⚠️ 时间窗口不合理
        "rank(ts_mean(close, 3))",
        "rank(ts_mean(close, 300))",
    ]

    print(f"\n测试 {len(test_expressions)} 个表达式:\n")

    # 批量验证
    results = validator.batch_validate(test_expressions)

    # 显示结果
    for i, result in enumerate(results):
        expr = test_expressions[i]
        status = "✅" if result["valid"] and result["score"] >= 50 else "❌"

        print(f"{status} [{result['score']:3d}分] {expr[:50]}...")

        if result["warnings"]:
            print(f"    ⚠️  警告: {result['warnings'][0]}")
        if result["errors"]:
            print(f"    ❌ 错误: {result['errors'][0]}")
        if result["predicted_failures"]:
            print(f"    🔮 预测失败: {result['predicted_failures']}")

    # 获取摘要
    print("\n" + "=" * 60)
    print("验证摘要统计")
    print("=" * 60)

    summary = validator.get_validation_summary(test_expressions)

    print(f"总数: {summary['total']}")
    print(f"有效: {summary['valid']}")
    print(f"无效: {summary['invalid']}")
    print(f"有外层排名: {summary['has_outer_rank']}")
    print(f"有市值标准化: {summary['has_cap_norm']}")
    print(f"有中性化: {summary['has_neutralization']}")
    print(f"平均评分: {summary['avg_score']:.1f}")

    print("\n预测失败类型分布:")
    for fail_type, count in summary['predicted_failures'].items():
        print(f"  {fail_type}: {count}")

    # 筛选高质量表达式
    print("\n" + "=" * 60)
    print("筛选高质量表达式 (min_score=50)")
    print("=" * 60)

    filtered = validator.filter_valid(test_expressions, min_score=50)

    print(f"\n通过筛选: {len(filtered)}/{len(test_expressions)} 个")
    for i, expr in enumerate(filtered, 1):
        print(f"  {i}. {expr}")


def test_integration_simulation():
    """
    模拟集成到生成流程的效果

    演示如何在不消耗 API 配额的情况下预筛选 Alpha
    """
    print("\n" + "=" * 60)
    print("模拟集成效果")
    print("=" * 60)

    validator = AlphaValidator()

    # 模拟 LLM 生成的 20 个表达式
    generated_expressions = [
        # 好的表达式 (应该通过)
        "rank(ts_zscore(divide(close, cap), 60))",
        "ts_rank(divide(volume, cap), 40)",
        "group_neutralize(ts_decay_linear(returns, 20), industry)",
        "rank(ts_mean(divide(fnd6_oiadps, cap), 80))",
        "group_rank(ts_corr(close, volume, 60), industry)",

        # 中等质量 (可能通过)
        "rank(ts_delta(close, 20))",
        "ts_rank(volume, 40)",
        "rank(divide(returns, cap))",

        # 低质量 (应该被过滤)
        "divide(close, cap)",  # 缺少外层排名
        "fnd6_oiadps",  # 缺少排名和市值标准化
        "ts_mean(nws12_sentiment, 20)",  # 事件数据 + 时间序列
        "close",  # 太简单
    ]

    print(f"\n模拟生成 {len(generated_expressions)} 个 Alpha 表达式")

    # 本地验证
    validation_result = validator.batch_validate(generated_expressions)

    # 统计
    passed = sum(1 for r in validation_result if r["valid"] and r["score"] >= 50)
    filtered_out = len(generated_expressions) - passed

    print(f"\n验证结果:")
    print(f"  ✅ 通过: {passed} 个")
    print(f"  ❌ 过滤: {filtered_out} 个")

    # 预测节省的 API 调用
    api_time_per_alpha = 5 * 60  # 5 分钟
    saved_time = filtered_out * api_time_per_alpha

    print(f"\n预估节省:")
    print(f"  API 调用: {filtered_out} 次")
    print(f"  时间: {saved_time // 60} 分钟")
    print(f"  配额: {filtered_out} 个模拟配额")

    # 如果提交到平台，需要的时间
    total_time = len(generated_expressions) * api_time_per_alpha
    print(f"\n如果全部提交到平台:")
    print(f"  总时间: {total_time // 60} 分钟 = {total_time // 3600} 小时")


if __name__ == "__main__":
    test_validator()
    test_integration_simulation()

    print("\n" + "=" * 60)
    print("结论")
    print("=" * 60)
    print("""
本地验证器可以在不消耗 WorldQuant Brain API 配额的情况下：

1. 预测可能失败的检查项（CONCENTRATED_WEIGHT、LOW_SUB_UNIVERSE_SHARPE 等）
2. 过滤低质量表达式，节省宝贵的 5 分钟模拟限制
3. 提供详细的验证报告，帮助改进生成策略

建议：
- 在提交到平台前，先进行本地验证
- 只提交评分 >= 50 的表达式
- 根据预测失败类型调整生成策略
    """)
