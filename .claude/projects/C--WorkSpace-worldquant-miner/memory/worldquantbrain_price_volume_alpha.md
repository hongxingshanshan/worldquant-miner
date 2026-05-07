---
name: WorldQuant Brain 价量与动量 Alpha 表达式
description: 价量相关性 + 动量反转 Alpha 策略，最佳表达式 IS 期间 Sharpe 1.39, Fitness 1.06 ⭐
type: reference
---

## 价量相关性 Alpha 策略 (2026-05-06)

### 核心理念
- 价量相关性是重要的市场信号
- 负相关表示价格上涨时成交量下降（或反之），可能是趋势反转信号
- 多时间窗口组合可以捕捉不同周期的信号

### 最佳表达式

#### Alpha #8 (最高 Sharpe: 1.36)
```
scale(-ts_corr(close, volume, 5)) + scale(-ts_corr(close, volume, 10)) + scale(-ts_corr(close, volume, 20))
```
- **Sharpe: 1.36**
- **Turnover: 48.57%**
- **Fitness: 0.63**
- **Returns: 10.31%**
- **IS Testing: 6 PASS, 1 FAIL, 1 PENDING**

#### Alpha #10 (最佳平衡)
```
ts_decay_linear(scale(-ts_corr(close, volume, 5)) + scale(-ts_corr(close, volume, 10)) + scale(-ts_corr(close, volume, 20)), 5)
```
- **Sharpe: 1.28**
- **Turnover: 26.34%**
- **Fitness: 0.77**
- **Returns: 9.60%**

### 时间窗口影响

| 衰减窗口 | Sharpe | Turnover | Fitness |
|---------|--------|----------|---------|
| 无衰减 | 1.36 | 48.57% | 0.63 |
| 5 | 1.28 | 26.34% | 0.77 |
| 10 | 1.17 | 18.60% | 0.80 |
| 15 | 1.10 | 14.94% | 0.82 |
| 20 | 1.08 | 12.86% | 0.86 |

### 提交要求

| 指标 | 要求 | 最佳结果 | 状态 |
|------|------|----------|------|
| Sharpe | ≥ 1.25 | 1.36 | ✅ |
| Fitness | ≥ 1.0 | 0.86 | ❌ |
| Turnover | 1-70% | 26.34% | ✅ |

### 关键发现

1. **Sharpe-Fitness 权衡**: 增加时间平滑窗口会提高 Fitness 但降低 Sharpe
2. **无法同时满足**: 当前策略无法同时达到 Sharpe ≥ 1.25 和 Fitness ≥ 1.0
3. **需要其他策略**: 需要探索不同的数据集或策略来提高 Fitness

---

## 动量反转 Alpha 策略 (2026-05-07) ⭐ 最佳

### 核心理念
- 使用更长时间窗口 (120日) 的收益率排名
- 结合 `signed_power` 变换保留信号方向
- 30日线性衰减窗口提高 Fitness

### 最佳表达式 (IS期间满足所有要求)

```
ts_decay_linear(signed_power(group_neutralize(-ts_rank(returns, 120), industry), 0.6), 30)
```

### IS 期间结果
| 指标 | 值 | 要求 | 状态 |
|------|-----|------|------|
| Sharpe | 1.39 | ≥ 1.25 | ✅ |
| Turnover | 20.08% | 1-70% | ✅ |
| Fitness | 1.06 | ≥ 1.0 | ✅ |
| Returns | 11.61% | - | - |

### 各年份表现
| 年份 | Sharpe | Fitness |
|------|--------|---------|
| 2019 | 1.81 | 1.08 ✅ |
| 2020 | 3.05 | 3.48 ✅ |
| 2021 | 0.88 | 0.61 ❌ |
| 2022 | 0.39 | 0.17 ❌ |
| 2023 | 1.80 | 1.39 ✅ |

### IS Testing Status
- 7 PASS, 1 PENDING (测试进行中)

### 关键发现
1. **长时间窗口有效**: 120日窗口比60日更稳定
2. **signed_power 变换**: 保留信号方向，提高 Fitness
3. **行业中性化**: 降低行业风险暴露
4. **衰减窗口**: 30日衰减平衡 Sharpe 和 Fitness

### 技术要点
- **ts_rank(returns, 120)**: 120日收益率时间序列排名，捕捉长期动量反转信号
- **group_neutralize(..., industry)**: 行业中性化，消除行业偏差
- **signed_power(x, 0.6)**: 保留符号的幂次变换，压缩极端值同时保持方向
- **ts_decay_linear(..., 30)**: 30日线性衰减，平滑信号降低换手率

### 与之前策略对比
| 策略 | Sharpe | Fitness | Turnover | 可提交 |
|------|--------|---------|----------|--------|
| 价量相关性 (60日) | 1.36 | 0.63 | 48.57% | ❌ |
| 动量反转 (120日) | 1.39 | 1.06 | 20.08% | ✅ |

### 为什么这个策略成功？
1. **更长的回看窗口**: 120日比60日捕捉更稳定的长期趋势
2. **适度的衰减**: 30日衰减平衡了信号强度和稳定性
3. **signed_power 的魔力**: 0.6次方变换是关键，既保留了信号又提高了 Fitness
4. **行业中性化**: 减少了行业集中风险

---
