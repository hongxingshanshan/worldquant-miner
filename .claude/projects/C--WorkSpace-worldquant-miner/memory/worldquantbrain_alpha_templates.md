---
name: WorldQuant Brain Alpha模板合集
description: 中文论坛收集的Alpha模板，包含多种类型的表达式模板
type: reference
originSessionId: f69b19a4-f3c3-4bda-bf94-a2c3355f045a
---
## Alpha模板合集

**注意：** 本贴仅收集总结，优秀程度不一定。部分存在严重overfitting风险。

---

### 模板1: 基础回归中性化
```
regression_neut(regression_neut(group_neutralize(group_zscore(\
vec_avg({data}),sector),bucket(rank(cap),range="0.1,1,0.1")),\
group_neutralize(group_zscore(cap,sector),bucket(rank(cap),range="0.1,1,0.1"))),\
ts_ir(returns-group_median(returns,sector),126))
```

### 模板2: Fear因子
```
fear = ts_mean(abs(returns - group_mean(returns,1,market))/(abs(returns)+abs(group_mean(returns,1,market))+0.1),20);\
-group_neutralize(fear*group_normalize(ts_decay_exp_window(ts_percentage(vec_count(rsk82_raw_m3g_tni_p_su_fte),60,percentage=0.9)\
-ts_percentage(vec_count({data}),60,percentage=0.1),20, factor=0.8),market)*inverse(abs(ts_entropy(volume,20)))\
,bucket(rank(cap),range="0.1,1,0.1"))
```

### 模板3: 稳定性因子
```
d1_level=ts_max(vec_stddev({data}),20);\
d1_stability=ts_kurtosis(vec_stddev({data}),20);\
mkt_level=group_min(d1_stability,industry);\
-group_neutralize(d1_stability<=mkt_level?-d1_level:d1_level,bucket(rank(cap),range="0.1,1,0.1"))
```

### 模板4: 分析师数据+期权价格
```
group = bucket(rank(cap),range='0.1,1,0.1');
risk = rank(-ts_av_diff(vec_min({Analyst Std}),360));
alpha=rank((1-risk)*group_rank(ts_scale(vec_max({OptionHighPrice})/close,120),industry));
group_neutralize(ts_mean(alpha,2),group)
```
**Decay=10, Neutralize=industry**

### 模板5: 成交量衰减+基本面
```
my_group = market;
my_group2 = bucket(rank(cap),range='0,1,0.1');
alpha=rank(group_rank(ts_decay_linear(volume/ts_sum(volume,252),10),my_group)*group_rank(ts_rank(vec_avg({Fundamental})),my_group)*group_rank(-ts_delta(close,5),my_group));
trade_when(volume>adv20,group_neutralize(alpha,my_group2),-1)
```

### 模板6: 市场恐惧+情绪回归
```
market_return = group_mean(returns,1,market);
fear = ts_mean(abs(returns - market_return)/(abs(returns)+abs(market_return)),20);
vhat = ts_regression(volume,ts_mean(vec_avg({Sentiment}),5),120);
ehat = ts_regression(returns-market_return,vhat,120);
alpha = group_neutralize(-ehat*rank(fear),bucket(rank(cap),range='0,1,0.1'));
trade_when(abs(returns)<0.075,regression_neut(alpha,volume),abs(returns)>0.1)
```
**Decay=20, Neutralize=industry**

### 模板7: 向量中性化
```
vector_neut(group_neutralize(group_neutralize(ts_arg_max(vec_norm({datafield}), 220),bucket(rank(assets), range="0.1,1,0.1")), subindustry), group_normalize(ts_delay(cap, 220),subindustry))
```

### 模板8: 情绪回归
```
sentiment = ts_backfill(ts_delay( vec_avg(SENTIMENT FROME OTHER),1),20)
vhat=ts_regression(volume,sentiment,250);
ehat=-ts_regression(returns,vhat,750);
alpha=group_rank(ehat,bucket(rank(cap),range='0,0.1,0.1'))
```

### 模板9: IR中性化
```
IR = abs(ts_mean(returns,252)/ts_std_dev(returns,252));
regression_neut ( vector_neut (ts_zscore( vec_max (ANALYST)/close, 126),ts_median(cap, 126) ),IR)
```

### 模板10: 订单流因子
```
small_sell = vec_sum(SPECIAL SELL ORDER);
small_buy = vec_sum(SPECIAL BUY ORDER);
fac = - small_sell - small_buy;
fac_diff_mean = power(rank(fac - group_mean(fac, 1, subindustry)),D);
IR = abs(ts_mean(returns,126)/ts_std_dev(returns,126));
group_neutralize(regression_neut(group_neutralize(fac_diff_mean,bucket(rank(cap), range='-0.1,1,0.1')),IR),sta1_top3000c10)
```

### 模板11: 波动率条件交易
```
trade_when(ts_rank(ts_std_dev(returns,10),252)<0.9,-regression_neut(group_neutralize(ts_std_dev(vec_avg(volatility),20)/ ts_mean(vec_avg(volatility),20),bucket(rank(assets),range = '0,1,0.1')),ts_std_dev(returns,30))+group_neutralize(-ts_std_dev(vec_avg(volume)/sharesout,30)/ ts_mean(vec_avg(volume)/sharesout,30),bucket(rank(cap), range = '0,1,0.1')),-1)
```

### 模板12: VWAP行业偏离
```
e = power(group_rank(-ts_decay_exp_window(ts_sum(if_else(vwap-group_mean(vwap,1,industry)-0.01>0,1,0)*ts_corr((log(volume/sharesout)),cap,5),5),20),industry),3);
trade_when(ts_rank(ts_std_dev(returns,10),252)<0.9,e,-1)
```

### 模板13: 财务数据回归系列

**系列1:**
```
A = sign(finance_var)*log(abs(finance_var)+1));
B = sign(finance_var)*log(abs(finance_var)+1));
regression_neut(A,B)
```

**系列2:**
```
ts_regression (ts_zscore(A,500), ts_zscore(B,500),500)
```

**系列3:**
```
1/ts_std_dev(ts_regression (ts_zscore(A,500), ts_zscore(B,500),500)，500)
```

**系列4:**
```
residual = ts_regression (ts_zscore(A,500), ts_zscore(B,500),500);
residual/ts_std_dev(residual ，500)
```

**系列5:**
```
ts_regression (ts_zscore(A,500), timestep(500),500);
```

### 模板14: 新闻情绪过滤
```
group_rank(
  filter(
    sigmoid(
      if_else(
        greater(ts_zscore(news_sentiment, 30), 1),
        ts_zscore(news_sentiment, 30),
        0
      )
    ),
    h="1 2 3 4",
    t="0.5"
  ),
  industry
)
```

### 模板15: 现金流组合
```
tmp = (group_rank(fnd72_s_pit_or_cf_q_cf_cash_from_inv_act, sector) > 0.5) * 4 + (group_rank(fnd72_s_pit_or_cf_q_cf_cash_from_fnc_act, sector) > 0.5) * 2 + (group_rank(fnd72_s_pit_or_cf_q_cf_cash_from_oper, sector) > 0.5) * 1;
2 * (tmp == 1) - (tmp == 2) - (tmp == 6)
```

### 模板16: 偏度因子
```
power(ts_std_dev(abs(returns),30),2)-power(ts_std_dev(returns,30),2)
```

### 模板17: 反转因子
```
a = -ts_delta(datafield,3);
b=abs(ts_mean(returns,252)/ts_std_dev(returns,252));
group_neutralize(vector_neut(a,b),subindustry)
```

### 模板18: "小而稳"因子
```
a = - A * ts_std_dev(A, 20);
b=abs(ts_mean(returns,252)/ts_std_dev(returns,252));
vector_neut(a,b)
```

### 模板19: 新闻情绪+收益
```
nss = ts_backfill(se_score,20);
processed_news_sentiment = (nss - ts_mean(nss,250))/ts_std_dev(nss,250);
monthly_returns = ts_ir(returns,20);
processed_returns = ts_backfill(monthly_returns, 20);
ranked_sentiment = ts_mean(group_rank(processed_news_sentiment,industry), 20);
ranked_returns = ts_mean(group_rank(-processed_returns,industry), 20);
lrhs = add(ranked_sentiment, ranked_returns);
hrls = add(inverse(ranked_sentiment), inverse(ranked_returns));
alpha = subtract(lrhs, hrls);
```

### 模板20: 日内/隔夜收益
```
# day1
d1_mean = ts_mean(close/ts_delay(close, 1)-1,20);
d1_std = ts_std_dev(close/ts_delay(close, 1)-1,20);
d1_mkt_mean = group_mean(d1_std, 1, market);
d1_std_rev = d1_std<d1_mkt_mean?-d1_mean:d1_mean;
tnv = volume/(sharesout*1000000);
tnv_diff = ts_delta(tnv, 1);
mkt_tnv_mean = group_mean(tnv_diff, 1, market);
rev_return = tnv_diff<mkt_tnv_mean?-(returns): (returns);
d1_tnv_rev = ts_mean(rev_return, 20);
...
ballteam_coin = -d1_std_rev-d1_tnv_rev-d0_std_rev-d0_tnv_rev-night_tnv_rev-night_std_rev;
group_neutralize(ballteam_coin,bucket(rank(cap),range='0.1,1,0.1'))
```

### 模板21: 换手率相关性
```
turnover = volume / sharesout;
avg_turn = ts_mean(turnover, 30);
nor_turn = ts_delay(turnover - avg_turn, 3);
change = (close - open) / open;
avg_change = ts_mean(change, 30);
nor_change = change - avg_change;
ts_corr(nor_turn, abs(nor_change), 10)
```

### 模板22: 条件交易
```
triggerTradeexp = (ts_arg_min(volume, 5) > 3) || (volume >= ts_sum(volume, 5) / 5);
alphaexp = rank(rank((high + low) / 2 - close) * rank((mdl175_roediluted*mdl175_cashrateofsales)));
tradeExitexp = -1;
trade_when(triggerTradeexp, alphaexp, tradeExitexp)
```

### 模板23: 隔夜收益与换手率
```
overnight_ret = (open - ts_delay(close,1))/ts_delay(close,1);
abs_ovn_ret = abs (overnight_ret);
turn = volume/sharesout;
turn_d1 = ts_delay(turn, 1);
corr = ts_corr (abs_ovn_ret, turn_d1,7);
-(corr)
```

### 模板24: 换手率稳定性
```
Turn20_ = ts_mean(volume/sharesout, 20);
Turn20 = group_neutralize(Turn20_, bucket(rank(cap), range="0.1,1,0.1"));
STR_ = ts_std_dev(volume/sharesout, 20);
STR = group_neutralize(STR_, bucket(rank(cap), range="0.1,1,0.1"));
score2 = rank(- nan_mask(Turn20, if_else(rank(STR) < 0.5, 1, -1))) * 0.5;
score3 = rank(nan_mask(Turn20, if_else(rank(STR) >= 0.5, 1, -1))) * 0.5;
signal_ = add(rank(STR), score2, score3, filter = true);
signal = left_tail(rank(signal_), maximum=0.98);
- group_rank(signal, bucket(rank(cap), range="0.1,1,0.1"))
```

### 模板25: 冲击因子
```
my_group=bucket(rank(cap), range="0,1,0.1");
shock=(high-ts_delay(low, 1))/ts_delay(low, 1);
talor_shock=(shock-log(shock+1))*2-log(shock+1)**2;
alpha=-group_rank(ts_mean(talor_shock, 24), my_group);
group_neutralize(alpha,my_group)
```

### 模板26: 分析师预期
```
turnover_rank = ts_mean(rank(volume / (sharesout * 1000000)), 22);
spe = rank(vec_avg(anl17_d1_spe_tse));
bp = rank(vec_avg(anl17_d1_bp_tse));
alpha = spe - bp;
turnover_rank > 0.1 ? alpha : 0
```

### 模板27: CHN模板
```
turn = volume/sharesout ;
turn20 = rank(regression_neut(-ts_mean(turn,20),densify(cap)));
STR = regression_neut(-ts_std_dev(turn,20),densify(cap));
UTR = STR+ turn20 * (STR/(1+abs(STR)));
regression_neut(regression_neut(regression_neut(sign(UTR) * power(abs(UTR),0.5),turn20),vwap),ts_delta(retained_earnings / sharesout, 120))
```

### 模板28: 内部收益
```
internal=ts_delay(ts_percentage(returns, 60, percentage=0.9)-ts_percentage(returns, 60, percentage=0.1),40);
CV=ts_std_dev((close/open - 1), 20)/ts_mean((close/open - 1),20);
alpha=ts_sum(-returns,20)*rank(internal)*abs (1/CV);
group_neutralize (alpha, bucket(rank(cap), range='0.1,1,0.1'))
```

### 模板29: 行业趋势
```
industry_open = group_mean(open, cap, subindustry);
industry_close = group_mean(close, cap, subindustry);
industry_high = group_mean(high, cap, subindustry);
industry_low = group_mean(low, cap, subindustry);
Trends = if_else(industry_close > ts_delay(industry_close, 40), industry_close/ts_max(industry_high, 100), rank(industry_close/ts_min(industry_low, 500))-1);
OTSM = ts_sum((industry_high-ts_delay(industry_close, 1)) / (ts_delay(industry_close, 1)-industry_low+1), 90);
DTSM = ts_sum((industry_high-industry_open) / (industry_open-industry_low+1), 5);
TSM = rank(OTSM) + rank(DTSM);
rank(Trends) + rank(TSM)
```

### 模板30: 大小单因子
```
small_sell = vec_avg(pv27_sell_value_small_order);
small_buy = vec_avg(pv27_buy_value_small_order);
large_sell = vec_avg(pv27_sell_value_exlarge_order);
large_buy = vec_avg(pv27_buy_value_exlarge_order);
fac_small = small_sell + small_buy;
fac_large = large_sell + large_buy;
fac_small_diff_mean = fac_small - group_mean(fac_small, 1, subindustry);
fac_large_diff_mean = fac_large - group_mean(fac_large, 1, subindustry);
factor = if_else(rank(cap)<0.05, fac_small_diff_mean, fac_large_diff_mean);
if_else(rank(factor) <0.45, rank(factor)*0.55, factor, -1)
```

---

## 使用建议

1. **注意overfitting风险** - 部分模板可能过拟合
2. **参数调整** - 时间窗口、分组方式可根据数据调整
3. **组合使用** - 可尝试组合多个模板
4. **经济逻辑** - 从经济逻辑出发，避免过于复杂的公式

---
**来源：** WorldQuant Brain 中文论坛
**作者：** WL13229 及其他贡献者
