---
name: WorldQuant Brain News Alpha 表达式合集
description: 基于5个优化方向设计的 News Alpha 表达式，包含数据集字段说明
type: reference
originSessionId: current
---

## News 数据集字段汇总 (2026-05-06)

### 1. US News Data (news12) - 322 字段, 80% 覆盖率

| 字段 | 描述 | 类型 | 覆盖率 |
|------|------|------|--------|
| `news_all_vwap` | 所有交易时段的 VWAP | Matrix | 73% |
| `news_atr14` | 14日平均真实波幅 | Matrix | 89% |
| `news_atr_ratio` | 当日价格波幅与20日ATR比率 | Matrix | 80% |
| `news_cap` | 市值 | Matrix | 83% |
| `news_eod_close` | 收盘价 | Matrix | 88% |
| `news_eod_high` | 新闻发布后最高价 | Matrix | 97% |
| `news_eod_low` | 新闻发布后最低价 | Matrix | 97% |
| `news_eod_vwap` | 新闻发布后 VWAP | Matrix | 97% |
| `news_eps_actual` | 实际 EPS | Matrix | 96% |
| `news_high_exc_stddev` | 标准化高价波动 | Matrix | 97% |
| `news_indx_perf` | 相对 S&P500 超额收益 | Matrix | 97% |
| `news_low_exc_stddev` | 标准化低价波动 | Matrix | 97% |
| `news_ls` | 多空指示 (Long/Short) | Matrix | 49% |
| `news_main_vwap` | 主交易时段 VWAP | Matrix | 97% |
| `news_max_dn_amt` | 新闻后最大下跌金额 | Matrix | 97% |
| `news_max_dn_ret` | 新闻后最大下跌收益率 | Matrix | 97% |
| `news_max_up_amt` | 新闻后最大上涨金额 | Matrix | 97% |

### 2. Ravenpack News Data (news18) - 75 字段, 50% 覆盖率

#### Vector 类型字段 (需用 vec_avg 转换)

| 字段 | 描述 | 覆盖率 | Alphas |
|------|------|--------|--------|
| `nws18_acb` | 企业行动公告情绪 | 50% | 515 |
| `nws18_bam` | 并购情绪指标 (-1, 0, +1) | 50% | 984 |
| `nws18_bee` | **盈利评估分数 (-1, 0, +1)** ⭐ | 50% | 497 |
| `nws18_ber` | 盈利发布指示器 | 50% | 595 |
| `nws18_event_relevance` | 事件相关性 (0-100) | 50% | 878 |
| `nws18_event_similarity_days` | 相似事件间隔天数 | 50% | 591 |
| `nws18_ghc_lna` | 分析师推荐变化 | 50% | 1388 |
| `nws18_nip` | **叙事影响分数 [-1, 1]** ⭐ | 50% | 1241 |
| `nws18_qcm` | 高置信度新闻情绪 | 50% | 631 |
| `nws18_qep` | 股票情绪极性分数 | 50% | 970 |
| `nws18_qmb` | 社论评论分数 | 50% | 471 |
| `nws18_relevance` | **实体相关性分数 (0-100)** ⭐ | 50% | 653 |
| `nws18_ssc` | 细粒度情绪分数 [-1, 1] | 50% | 722 |
| `nws18_sse` | 实体事件情绪分数 | 50% | 367 |

#### Matrix 类型字段 (直接使用)

| 字段 | 描述 | 覆盖率 | Alphas |
|------|------|--------|--------|
| `rp_css_assets` | 资产新闻复合情绪 | 50% | 1048 |
| `rp_css_business` | 商业新闻复合情绪 | 50% | 3200 |
| `rp_css_credit` | 信贷新闻复合情绪 | 50% | 257 |
| `rp_css_earnings` | **盈利新闻复合情绪** ⭐ | 50% | 1645 |
| `rp_css_equity` | 股票行动新闻复合情绪 | 50% | 932 |
| `rp_css_insider` | 内幕交易新闻复合情绪 | 50% | 554 |
| `rp_css_legal` | 法律新闻复合情绪 | 50% | 275 |
| `rp_css_mna` | 并购相关新闻复合情绪 | 50% | 560 |
| `rp_css_price` | 股价新闻复合情绪 | 50% | 1155 |
| `rp_css_ratings` | 分析师评级新闻复合情绪 | 50% | 1826 |
| `rp_css_revenue` | **营收新闻复合情绪** ⭐ | 50% | 1168 |
| `rp_ess_assets` | 资产新闻事件情绪 | 50% | 694 |
| `rp_ess_business` | 商业新闻事件情绪 | 50% | 872 |

---

## 基础表达式 (已测试最佳)

```
group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20))
```
**结果**: Sharpe 0.61, Turnover 16.49%, Fitness 0.24

---

## 优化方向 1: 组合其他数据

### 1.1 News + 分析师预期 (est_eps)
```
group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20)) * rank(est_eps/close)
```

### 1.2 News + 情绪数据 (scl12_sentiment)
```
group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(scl12_sentiment, 20))
```

### 1.3 News + 债务安全指标 (fnd6_fopo/debt_lt)
```
group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(fnd6_fopo/debt_lt)
```

### 1.4 News + 叙事影响分数 (nws18_nip)
```
group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(vec_avg(nws18_nip), 20))
```

### 1.5 News + 盈利新闻复合情绪 (rp_css_earnings)
```
group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(rp_css_earnings, 20))
```

### 1.6 News + 多因子组合
```
scale(group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry)) * scale(rank(ts_mean(volume, 20))) * scale(rank(est_eps/close))
```

### 1.7 News + 营收新闻复合情绪
```
group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(rp_css_revenue, 20))
```

### 1.8 News + 分析师评级新闻
```
group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(rp_css_ratings, 20))
```

---

## 优化方向 2: 使用条件交易 (trade_when)

### 2.1 高成交量时激活
```
trade_when(adv20 > ts_mean(adv20, 252), group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry), -1)
```

### 2.2 新闻相关性高时激活
```
trade_when(vec_avg(nws18_relevance) > 0.1, group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20)), -1)
```

### 2.3 极端情绪时激活
```
trade_when(abs(ts_zscore(ts_backfill(vec_avg(nws18_bee), 20), 60)) > 1, group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry), -1)
```

### 2.4 综合条件 (成交量 + 新闻相关性)
```
trade_when(and(adv20 > 1, vec_avg(nws18_relevance) > 0.1), group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry), -1)
```

### 2.5 高叙事影响时激活
```
trade_when(vec_avg(nws18_nip) > 0.3, group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20)), -1)
```

### 2.6 盈利发布期间激活
```
trade_when(vec_avg(nws18_ber) > 0, group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry), -1)
```

### 2.7 高置信度新闻时激活
```
trade_when(vec_avg(nws18_qcm) != 0, group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry), -1)
```

---

## 优化方向 3: 调整时间窗口

### 3.1 短期窗口 (5日)
```
group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 5), 5), industry) * rank(ts_mean(volume, 5))
```

### 3.2 中期窗口 (20日) - 已测试
```
group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20))
```

### 3.3 长期窗口 (60日)
```
group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 60), 20), industry) * rank(ts_mean(volume, 60))
```

### 3.4 多窗口组合
```
scale(group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 5), 5), industry)) + scale(group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry)) + scale(group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 60), 20), industry))
```

### 3.5 指数衰减窗口 (factor=0.5)
```
group_rank(ts_decay_exp_window(ts_backfill(vec_avg(nws18_bee), 20), 20, factor=0.5), industry) * rank(ts_mean(volume, 20))
```

### 3.6 指数衰减窗口 (factor=0.8)
```
group_rank(ts_decay_exp_window(ts_backfill(vec_avg(nws18_bee), 20), 20, factor=0.8), industry) * rank(ts_mean(volume, 20))
```

### 3.7 时间序列排名 (ts_rank)
```
ts_rank(group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20)), 60)
```

---

## 优化方向 4: 中性化处理

### 4.1 行业中性化 + 规模中性化
```
group_neutralize(group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20)), bucket(rank(cap), range="0.1,1,0.1"))
```

### 4.2 子行业中性化
```
group_neutralize(group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20)), subindustry)
```

### 4.3 回归中性化 (对规模)
```
regression_neut(group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20)), rank(cap))
```

### 4.4 双重中性化 (行业 + 规模)
```
group_neutralize(regression_neut(group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20)), rank(cap)), industry)
```

### 4.5 板块中性化
```
group_neutralize(group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20)), sector)
```

### 4.6 回归中性化 (对成交量)
```
regression_neut(group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20)), rank(adv20))
```

---

## 优化方向 5: 筛选股票池

### 5.1 小市值股票 (新闻效应更强)
```
trade_when(rank(cap) < 0.3, group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20)), -1)
```

### 5.2 低分析师覆盖率
```
trade_when(ts_mean(snt1_d1_analystcoverage, 60) < ts_mean(ts_mean(snt1_d1_analystcoverage, 60), 252), group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry), -1)
```

### 5.3 高流动性小市值
```
trade_when(and(rank(cap) < 0.5, rank(adv20) > 0.3), group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry), -1)
```

### 5.4 中等市值股票
```
trade_when(and(rank(cap) > 0.3, rank(cap) < 0.7), group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20)), -1)
```

### 5.5 高新闻覆盖率股票
```
trade_when(ts_mean(vec_avg(nws18_relevance), 60) > 0.5, group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry), -1)
```

---

## 进阶组合表达式

### A. 多数据源 + 条件交易
```
trade_when(and(vec_avg(nws18_relevance) > 0.1, adv20 > 1), group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(rp_css_earnings, 20)), -1)
```

### B. 多时间窗口 + 中性化
```
group_neutralize(scale(group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 5), 5), industry)) + scale(group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry)), industry)
```

### C. 情绪极性 + 成交量 + 条件交易
```
trade_when(abs(vec_avg(nws18_qep)) > 0.5, group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20)), -1)
```

### D. 叙事影响 + 盈利新闻
```
scale(group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_nip), 20), 10), industry)) * scale(rank(ts_mean(rp_css_earnings, 20)))
```

### E. 分析师推荐变化 + 新闻情绪
```
group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_ghc_lna), 20), 10), industry) * rank(ts_mean(vec_avg(nws18_bee), 20))
```

---

## 推荐测试顺序

| 优先级 | 编号 | 表达式类型 | 预期效果 |
|--------|------|------------|----------|
| ⭐⭐⭐ | 1.1 | News + 分析师预期 | 基础好，叠加预期可能提升 |
| ⭐⭐⭐ | 2.2 | 条件交易 | 过滤低质量信号 |
| ⭐⭐⭐ | 1.5 | News + 盈利情绪 | 相关性强 |
| ⭐⭐ | 3.3 | 长期窗口 | 更稳定 |
| ⭐⭐ | 4.1 | 双重中性化 | 降低风险暴露 |
| ⭐⭐ | A | 多数据源组合 | 综合信号 |
| ⭐ | 5.1 | 小市值筛选 | 新闻效应更强 |
| ⭐ | D | 叙事影响组合 | 新角度 |

---

## 注意事项

1. **Vector 类型字段必须用 vec_avg() 转换**: `nws18_bee`, `nws18_nip`, `nws18_relevance` 等
2. **Matrix 类型字段直接使用**: `rp_css_earnings`, `rp_css_revenue` 等
3. **覆盖率**: US News Data 80%, Ravenpack 50%
4. **trade_when 退出条件**: `-1` 表示持有一天后退出
5. **时间窗口**: 短期(5日)、中期(20日)、长期(60日) 各有优劣
