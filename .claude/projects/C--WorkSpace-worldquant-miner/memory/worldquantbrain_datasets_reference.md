---
name: WorldQuant Brain 数据集完整参考
description: WorldQuant BRAIN 平台所有数据集的完整字段参考 (2026-05-06)
type: reference
---

## 数据集总览 (USA Region, TOP3000 Universe)

| 数据集名称 | ID | 字段数 | 覆盖率 | Value Score | Alphas |
|------------|-----|--------|--------|-------------|--------|
| Analyst Estimate Data for Equity | analyst4 | 653 | 72% | 1 | 536,443 |
| Report Footnotes | fundamental2 | 318 | 41% | 1 | 109,998 |
| Company Fundamental Data for Equity | fundamental6 | 886 | 50% | 1 | 651,120 |
| Fundamental Scores | model16 | 24 | 56% | 1 | 4,620 |
| Systematic Risk Metrics | model51 | 16 | 77% | 1 | 26,898 |
| Analysts' Factor Model | model77 | 3,241 | 84% | 2 | 77,939 |
| US News Data | news12 | 322 | 80% | 1 | 123,813 |
| Ravenpack News Data | news18 | 75 | 50% | 1 | 42,177 |
| Volatility Data | option8 | 64 | 69% | 1 | 110,518 |
| Options Analytics | option9 | 74 | 70% | 1 | 48,564 |
| Price Volume Data for Equity | pv1 | 24 | 100% | 1 | 1,544,404 |
| Relationship Data for Equity | pv13 | 165 | 80% | 1 | 133,367 |
| Research Sentiment Data | sentiment1 | 17 | 56% | 2 | 12,082 |
| Sentiment Data for Equity | socialmedia12 | 18 | 99% | 1 | 45,186 |
| Social Media Data for Equity | socialmedia8 | 2 | 86% | 1 | 9,236 |
| Universe Dataset | univ1 | 6 | 30% | 3 | 98 |

**总计**: 16个数据集, 约6,200个字段

---

## 1. News 数据集

### 1.1 US News Data (news12) - 322字段, 80%覆盖率

#### Matrix 类型字段 (直接使用)

| 字段 | 描述 | 覆盖率 | Alphas |
|------|------|--------|--------|
| `news_all_vwap` | 所有交易时段的 VWAP | 73% | 1,497 |
| `news_atr14` | 14日平均真实波幅 | 89% | 3,670 |
| `news_atr_ratio` | 当日价格波幅与20日ATR比率 | 80% | 2,292 |
| `news_cap` | 市值 | 83% | 6,585 |
| `news_eod_close` | 收盘价 | 88% | 2,889 |
| `news_eod_high` | 新闻发布后最高价 | 97% | 1,252 |
| `news_eod_low` | 新闻发布后最低价 | 97% | 858 |
| `news_eod_vwap` | 新闻发布后 VWAP | 97% | 1,079 |
| `news_eps_actual` | 实际 EPS | 96% | 1,411 |
| `news_high_exc_stddev` | 标准化高价波动 | 97% | 1,196 |
| `news_indx_perf` | 相对 S&P500 超额收益 | 97% | 1,307 |
| `news_low_exc_stddev` | 标准化低价波动 | 97% | 1,081 |
| `news_ls` | 多空指示 (Long/Short) | 49% | 682 |
| `news_main_vwap` | 主交易时段 VWAP | 97% | 911 |
| `news_max_dn_amt` | 新闻后最大下跌金额 | 97% | 1,352 |
| `news_max_dn_ret` | 新闻后最大下跌收益率 | 97% | 1,144 |
| `news_max_up_amt` | 新闻后最大上涨金额 | 97% | 893 |
| `news_max_up_ret` | 新闻后最大上涨收益率 | 85% | 1,999 |
| `news_open` | 开盘价 | 71% | 1,071 |
| `news_open_gap` | 开盘缺口百分比 | 62% | 717 |
| `news_pe_ratio` | 市盈率 | 97% | 2,808 |
| `news_short_interest` | 卖空比例 | 87% | 535 |
| `news_spy_close` | SPY 收盘价 | 97% | 1,805 |
| `news_tot_ticks` | 总 tick 数 | 97% | 2,116 |

#### 价格变化百分比字段

| 字段 | 描述 | 覆盖率 |
|------|------|--------|
| `news_pct_30sec` | 新闻后30秒价格变化 | 97% |
| `news_pct_1min` | 新闻后1分钟价格变化 | 97% |
| `news_pct_5_min` | 新闻后5分钟价格变化 | 77% |
| `news_pct_10min` | 新闻后10分钟价格变化 | 77% |
| `news_pct_30min` | 新闻后30分钟价格变化 | 97% |
| `news_pct_60min` | 新闻后60分钟价格变化 | 97% |
| `news_pct_90min` | 新闻后90分钟价格变化 | 97% |
| `news_pct_120min` | 新闻后120分钟价格变化 | 91% |

#### Vector 类型字段 (需用 vec_avg 转换)

news12 包含大量 Vector 类型字段，主要分为以下几类：

- `nws12_afterhsz_*` - 盘后新闻相关数据
- `nws12_mainz_*` - 主交易时段新闻数据
- `nws12_prez_*` - 盘前新闻数据
- `nws12_allz_*` - 全时段新闻数据

**注意**: Vector 类型字段必须使用 `vec_avg()` 转换后才能在 Alpha 表达式中使用。

---

### 1.2 Ravenpack News Data (news18) - 75字段, 50%覆盖率

#### Vector 类型字段 (需用 vec_avg 转换)

| 字段 | 描述 | 覆盖率 | Alphas |
|------|------|--------|--------|
| `nws18_acb` | 企业行动公告情绪 | 50% | 515 |
| `nws18_bam` | 并购情绪指标 (-1, 0, +1) | 50% | 984 |
| `nws18_bee` | **盈利评估分数 (-1, 0, +1)** ⭐ | 50% | 497 |
| `nws18_ber` | 盈利发布指示器 | 50% | 595 |
| `nws18_event_relevance` | 事件相关性 (0-100) | 50% | 878 |
| `nws18_event_similarity_days` | 相似事件间隔天数 | 50% | 591 |
| `nws18_ghc_lna` | 分析师推荐变化 | 50% | 1,388 |
| `nws18_nip` | **叙事影响分数 [-1, 1]** ⭐ | 50% | 1,241 |
| `nws18_qcm` | 高置信度新闻情绪 | 50% | 631 |
| `nws18_qep` | 股票情绪极性分数 | 50% | 970 |
| `nws18_qmb` | 社论评论分数 | 50% | 471 |
| `nws18_relevance` | **实体相关性分数 (0-100)** ⭐ | 50% | 653 |
| `nws18_ssc` | 细粒度情绪分数 [-1, 1] | 50% | 722 |
| `nws18_sse` | 实体事件情绪分数 | 50% | 367 |

#### Matrix 类型字段 (直接使用)

**复合情绪分数 (Composite Sentiment Score - CSS)**

| 字段 | 描述 | 覆盖率 | Alphas |
|------|------|--------|--------|
| `rp_css_assets` | 资产新闻复合情绪 | 50% | 1,048 |
| `rp_css_business` | 商业新闻复合情绪 | 50% | 3,200 |
| `rp_css_credit` | 信贷新闻复合情绪 | 50% | 257 |
| `rp_css_credit_ratings` | 信用评级新闻复合情绪 | 50% | 1,185 |
| `rp_css_dividends` | 股息新闻复合情绪 | 50% | 192 |
| `rp_css_earnings` | **盈利新闻复合情绪** ⭐ | 50% | 1,645 |
| `rp_css_equity` | 股票行动新闻复合情绪 | 50% | 932 |
| `rp_css_insider` | 内幕交易新闻复合情绪 | 50% | 554 |
| `rp_css_inverstor` | 投资者关系新闻复合情绪 | 50% | 1,736 |
| `rp_css_labor` | 劳工新闻复合情绪 | 50% | 371 |
| `rp_css_legal` | 法律新闻复合情绪 | 50% | 275 |
| `rp_css_marketing` | 营销新闻复合情绪 | 50% | 483 |
| `rp_css_mna` | 并购相关新闻复合情绪 | 50% | 560 |
| `rp_css_partner` | 合作伙伴新闻复合情绪 | 50% | 712 |
| `rp_css_price` | 股价新闻复合情绪 | 50% | 1,155 |
| `rp_css_product` | 产品服务新闻复合情绪 | 50% | 720 |
| `rp_css_ptg` | 价格目标新闻复合情绪 | 50% | 782 |
| `rp_css_ratings` | 分析师评级新闻复合情绪 | 50% | 1,826 |
| `rp_css_revenue` | **营收新闻复合情绪** ⭐ | 50% | 1,168 |
| `rp_css_society` | 社会新闻复合情绪 | 50% | 139 |
| `rp_css_technical` | 技术分析新闻复合情绪 | 50% | 325 |

**事件情绪分数 (Event Sentiment Score - ESS)**

| 字段 | 描述 | 覆盖率 | Alphas |
|------|------|--------|--------|
| `rp_ess_assets` | 资产新闻事件情绪 | 50% | 694 |
| `rp_ess_business` | 商业新闻事件情绪 | 50% | 872 |
| `rp_ess_earnings` | 盈利新闻事件情绪 | 50% | 1,496 |
| `rp_ess_ratings` | 分析师评级新闻事件情绪 | 50% | 1,888 |
| `rp_ess_partner` | 合作伙伴新闻事件情绪 | 50% | 1,539 |
| `rp_ess_mna` | 并购新闻事件情绪 | 50% | 1,192 |

**新闻影响预测 (News Impact Projection - NIP)**

| 字段 | 描述 | 覆盖率 | Alphas |
|------|------|--------|--------|
| `rp_nip_assets` | 资产新闻影响预测 | 50% | 868 |
| `rp_nip_business` | 商业新闻影响预测 | 50% | 1,068 |
| `rp_nip_earnings` | 盈利新闻影响预测 | 50% | 1,093 |
| `rp_nip_ratings` | 分析师评级新闻影响预测 | 50% | 1,788 |
| `rp_nip_inverstor` | 投资者关系新闻影响预测 | 50% | 2,221 |

---

## 2. Analyst 数据集

### 2.1 Analyst Estimate Data for Equity (analyst4) - 653字段, 72%覆盖率

#### 核心字段

| 字段 | 描述 | 类型 | 覆盖率 | Alphas |
|------|------|------|--------|--------|
| `actual_eps_value_quarterly` | 季度实际 EPS | Matrix | 100% | 456 |
| `actual_sales_value_quarterly` | 季度实际销售额 | Matrix | 100% | 246 |
| `actual_sales_value_annual` | 年度实际销售额 | Matrix | 99% | 208 |
| `anl4_afv4_eps_mean` | 年度 EPS 预测均值 | Matrix | 100% | 713 |
| `anl4_afv4_eps_high` | 年度 EPS 预测最高值 | Matrix | 100% | 411 |
| `anl4_afv4_eps_low` | 年度 EPS 预测最低值 | Matrix | 100% | 283 |
| `anl4_afv4_eps_number` | 年度 EPS 预测数量 | Matrix | 100% | 275 |
| `anl4_adjusted_netincome_ft` | 调整后净利润预测类型 | Matrix | 87% | 41,164 |

#### 字段命名规则

- `anl4_afv4_*` - 年度预测 (Annual Forecast Value)
- `anl4_qfv4_*` - 季度预测 (Quarterly Forecast Value)
- `*_mean` - 预测均值
- `*_high` - 预测最高值
- `*_low` - 预测最低值
- `*_median` - 预测中位数
- `*_number` / `*_numest` - 预测数量
- `*_std` - 预测标准差

---

## 3. Fundamental 数据集

### 3.1 Company Fundamental Data for Equity (fundamental6) - 886字段, 50%覆盖率

**重要字段**:
- `fnd6_fopo` - 运营资金 (Funds from Operations)
- `debt_lt` - 长期债务

**常用 Alpha 表达式**:
```
rank(fnd6_fopo/debt_lt)  # 债务安全检测器
```

### 3.2 Report Footnotes (fundamental2) - 318字段, 41%覆盖率

---

## 4. Model 数据集

### 4.1 Analysts' Factor Model (model77) - 3,241字段, 84%覆盖率

### 4.2 Systematic Risk Metrics (model51) - 16字段, 77%覆盖率

### 4.3 Fundamental Scores (model16) - 24字段, 56%覆盖率

---

## 5. Option 数据集

### 5.1 Volatility Data (option8) - 64字段, 69%覆盖率

### 5.2 Options Analytics (option9) - 74字段, 70%覆盖率

---

## 6. Price Volume 数据集

### 6.1 Price Volume Data for Equity (pv1) - 24字段, 100%覆盖率

**核心字段**:
- `close` - 收盘价
- `open` - 开盘价
- `high` - 最高价
- `low` - 最低价
- `volume` - 成交量
- `vwap` - 成交量加权平均价
- `returns` - 收益率
- `cap` - 市值
- `adv20` - 20日平均成交量

### 6.2 Relationship Data for Equity (pv13) - 165字段, 80%覆盖率

---

## 7. Sentiment 数据集

### 7.1 Sentiment Data for Equity (socialmedia12) - 18字段, 99%覆盖率

### 7.2 Research Sentiment Data (sentiment1) - 17字段, 56%覆盖率

### 7.3 Social Media Data for Equity (socialmedia8) - 2字段, 86%覆盖率

---

## 8. Universe 数据集

### 8.1 Universe Dataset (univ1) - 6字段, 30%覆盖率

---

## 数据类型说明

### Matrix 类型
- 直接在 Alpha 表达式中使用
- 每个股票每天一个值

### Vector 类型
- 必须使用 `vec_avg()` 转换后才能使用
- 包含多个数据点（如多个分析师预测）
- 转换函数: `vec_avg(field)`, `vec_sum(field)`, `vec_max(field)`, `vec_min(field)`, `vec_stddev(field)`

---

## 使用建议

### 高价值数据集 (推荐优先使用)

1. **pv1** - Price Volume Data (100%覆盖率, 150万+ Alphas)
2. **analyst4** - Analyst Estimate Data (72%覆盖率, 53万+ Alphas)
3. **fundamental6** - Company Fundamental Data (50%覆盖率, 65万+ Alphas)
4. **news12** - US News Data (80%覆盖率, 12万+ Alphas)
5. **option8** - Volatility Data (69%覆盖率, 11万+ Alphas)

### 高价值字段 (按 Alphas 数量排序)

| 字段 | 数据集 | Alphas | 描述 |
|------|--------|--------|------|
| `anl4_adjusted_netincome_ft` | analyst4 | 41,164 | 调整后净利润预测类型 |
| `nws12_afterhsz_sl` | news12 | 19,312 | 盘后多空指示 |
| `anl4_ady_pu` | analyst4 | 5,491 | 年度预测上调数量 |
| `anl4_adxqfv110_pu` | analyst4 | 4,560 | 季度预测上调数量 |
| `news_cap` | news12 | 6,585 | 市值 |
| `news_atr14` | news12 | 3,670 | 14日ATR |
| `rp_css_business` | news18 | 3,200 | 商业新闻复合情绪 |

---

## 更新日期

- 创建日期: 2026-05-06
- 数据来源: WorldQuant BRAIN 平台
