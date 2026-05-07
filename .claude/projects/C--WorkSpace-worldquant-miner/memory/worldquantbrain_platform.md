---
name: WorldQuant Brain 平台信息
description: WorldQuant BRAIN 量化研究平台的使用经验和关键信息
type: project
originSessionId: 9e99bfa4-0f27-4045-b629-bc2d440c8cb7
---

## 平台概述

WorldQuant BRAIN 是一个量化因子研究平台，用于创建和测试 Alpha 因子表达式。

## 核心功能

### Alpha 表达式
- 使用 operators: `rank()`, `scale()`, `group_neutralize()`, `ts_rank()`, `ts_decay_linear()`, `signed_power()`, `winsorize`
- Option 数据字段: `implied_volatility_call_120`, `implied_volatility_put_120`
- Group neutralization: `industry`, `subindustry`, `sector`

### IS Testing Status 标准
| 指标 | 要求 |
|------|------|
| Fitness | > 1 |
| Sharpe | > 1.25 |
| Turnover | 1% - 70% |
| Weight concentration | < 10% |
| Sub-universe Sharpe | > 70% of main Sharpe |
| Self-correlation | < 0.7 |

## 最佳测试结果

**表达式 1 (原始):**
```
ts_decay_linear(scale(group_neutralize(implied_volatility_call_120 - implied_volatility_put_120, industry)), 5)
```

**结果 (TOP3000):**
- IS Sharpe: 2.23
- IS Fitness: 1.82
- Turnover: 37.95%
- Returns: 25.32%
- Weight concentration: 12.53%

**表达式 2 (乘以 adv20 优化 Sub-universe Sharpe):**
```
ts_decay_linear(scale(group_neutralize(implied_volatility_call_120 - implied_volatility_put_120, industry)), 5) * adv20
```

**结果 (TOP3000):**
- IS Sharpe: 1.47
- IS Fitness: 1.99 ✓
- Turnover: 26.20% ✓
- Returns: 48.07% ✓
- Weight concentration: 13.10% (需 < 10%)
- IS Testing Status: 6 PASS, 1 FAIL (Weight concentration), 1 PENDING

**表达式 3 (winsorize 处理极值):**
```
winsorize(ts_decay_linear(scale(group_neutralize(implied_volatility_call_120 - implied_volatility_put_120, industry)), 5) * adv20)
```

**结果 (TOP3000):**
- IS Sharpe: 1.70
- IS Fitness: 1.84 ✓
- Turnover: 27.72% ✓
- Returns: 32.34% ✓
- Weight concentration: 12.21% (需 < 10%)
- IS Testing Status: 6 PASS, 1 FAIL (Weight concentration), 1 PENDING

**表达式 4 (rank 包装 - 效果不好):**
```
rank(ts_decay_linear(scale(group_neutralize(implied_volatility_call_120 - implied_volatility_put_120, industry)), 5) * adv20)
```

**结果 (TOP3000):**
- IS Sharpe: 1.43
- IS Fitness: 0.68 ✗
- Turnover: 26.98%
- Returns: 6.10% ✗
- 结论: rank() 使结果显著恶化，不推荐

## 关键发现

1. **scale() 降低 Weight concentration**: 从 50% 降至 12.53%
2. **ts_decay_linear 降低 Turnover**: 从 88.18% 降至 37.95%
3. **Universe 选择影响**: TOP200 → TOP3000 显著提升 Sharpe (0.62 → 2.23)
4. **乘以 adv20 效果**:
   - Fitness 提高: 1.82 → 1.99
   - Turnover 降低: 37.95% → 26.20%
   - Returns 提高: 25.32% → 48.07%
   - Sharpe 略降: 2.23 → 1.47
5. **Weight concentration 问题**: 信号本身分布问题，需要进一步优化
6. **winsorize() 效果**:
   - Weight concentration 略微改善: 13.10% → 12.21%
   - 但仍超过 10% 限制
   - Sharpe 提高: 1.47 → 1.70
7. **rank() 效果不好**:
   - Fitness 大幅下降: 1.99 → 0.68
   - Returns 大幅下降: 48.07% → 6.10%
   - 不推荐用于此表达式

## 论坛学习笔记

### 提高 Fitness 的方法
1. **降低 Turnover 比提高 Sharpe 更容易**
   - 增加 decay（最简单方法）
   - 使用 group_operator
   - 使用 neutralization
2. **Fitness 公式**: 平衡 Sharpe/Returns 和 Turnover

### Options 数据使用技巧
1. **Volatility Skew（波动率偏斜）**
   - 隐含波动率在高/低行权价之间的差异
   - 与个股收益呈负相关

2. **Volatility Spread（波动率价差）**
   - 美式期权看涨/看跌的隐含波动率差异
   - 可作为情绪指标
   - 数据字段: `mdl777_2400_rmi`

3. **Options Trading Volume**
   - O/S 比率包含私人信息
   - 数据字段: `opt6_cvolu`, `opt6_pvolu`

4. **Option Open Interest**
   - 看跌期权持仓量与收益负相关
   - 数据字段: `opt4_call_openinterest`, `opt4_put_openinterest`

### Sub-universe Sharpe 优化
**问题**: Alpha 在较小 universe 上表现不佳

**公式**:
```
subuniverse_sharpe >= 0.75 * sqrt(subuniverse_size / alpha_universe_size) * alpha_sharpe
```

**解决方案**:
1. **最简单方法**: Alpha 乘以 `volume` 或 `adv20`
   - 例如: `alpha * adv20`
   - 给流动性更高的股票更多权重
2. 整合流动性相关因素
3. 添加特定子 universe 相关特征

## 登录问题

- 验证邮件可能过期，需要重新发送
- reCAPTCHA 验证可能出现（消防栓图片识别等）
- 登录后页面可能跳转到帮助中心社区页面

## 浏览器自动化注意事项

- 使用 Chrome DevTools MCP 或 Playwright MCP 进行自动化
- 模拟时可能卡住（15%, 35%），需要刷新或取消重试
- 编辑器修改时注意使用 `selectAll` 防止追加文本
- Session 可能过期，需要重新登录

## 当前状态 (2026-05-05)

### ✅ 已解决：Weight concentration 问题
使用 `ts_backfill(x, 60)` 成功解决了 Weight concentration 问题！

### ✅ 已解决：Sub-universe Sharpe 问题
使用 `volume` 替代 `adv20` 成功解决了 Sub-universe Sharpe 问题！

**最终成功的表达式：**
```
ts_backfill(winsorize(ts_decay_linear(scale(group_neutralize(implied_volatility_call_120 - implied_volatility_put_120, industry)), 5) * volume), 60)
```

**结果 (TOP3000):**
- IS Sharpe: 1.85 ✓
- IS Fitness: 1.39 ✓
- Turnover: 39.25% ✓
- Returns: 22.03% ✓
- **IS Testing Status: 7 PASS, 1 PENDING** ✓✓

### 关键发现
1. `ts_backfill(x, 60)` 解决了 Weight concentration 问题
2. `volume` 比 `adv20` 更有效地解决 Sub-universe Sharpe 问题
3. `scale(adv20)` 有轻微改善（Sub-universe Sharpe: 0.82 → 0.83）
4. `volume` 完全解决了 Sub-universe Sharpe 问题

### ✅ Alpha 已成功提交 (2026-05-05 19:55)
- 状态: **Regular Alpha**
- 所有检查通过，已进入下一个教程模块

### 关键经验总结
1. **Weight concentration 解决方案**: `ts_backfill(x, 60)` 确保权重均匀分布
2. **Sub-universe Sharpe 解决方案**: 使用 `volume` 替代 `adv20` 给流动性更高的股票更多权重
3. **Option 数据信号**: 隐含波动率差值 (call_put_diff) 是有效的 Alpha 信号源
4. **模拟卡住问题**: 复杂表达式需要等待更长时间（5-10分钟），不要轻易取消

### 教程进度 (2026-05-05)

#### ✅ Chapter 5 of 6: Sentiment & News Alphas 已完成
- **任务 1**: `ts_regression(scl12_buzz, volume, 60)` - 完成 (Sharpe -0.52, 教程通过)
- **任务 2**: `rank(ts_mean(vec_avg(nws12_afterhsz_sl), 20)) > 0.5 ? 1 : -returns` - 完成 (Sharpe 1.14, 教程通过)
- **任务 3**: 创建可提交的 Alpha - 完成 (使用之前成功的 Option 数据表达式)

#### 关键学习
1. **Sentiment Alpha**: 使用 `ts_regression` 比较 `scl12_buzz` 和 `volume`
2. **News Alpha**: 使用 `vec_avg` 处理向量数据，结合 `ts_mean` 和条件逻辑
3. **Vector 数据**: 新闻数据是向量类型，需要用 `vec_avg` 转换为矩阵形式

### 下一步
- 观看 "Introduction to Alphas" 课程 (6 个视频)
- 继续探索其他课程，如 "Quantcepts" (19 个课程)
- 每天提交新的 Alpha 以积累积分达到 Gold 级别 (需要 10,000 分)

### 当前状态 (2026-05-05)
- **Reaching gold**: 2000 / 10000 (20%)
- **已提交 Alpha**: 2 个
- **教程进度**: Chapter 5 of 6 已完成
