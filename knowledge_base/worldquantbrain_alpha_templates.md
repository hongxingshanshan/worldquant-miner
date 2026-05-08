# WorldQuant Brain Alpha Templates

## Templates

### 动量类 Alpha
ts_delta(close, 20)                    # 价格动量
ts_rank(returns, 60)                   # 收益率排名
rank(ts_mean(returns, 20))             # 平均收益排名

### 价值类 Alpha
rank(divide(earnings, price))          # 盈利收益率
rank(divide(book_value, market_cap))   # 账面市值比
-rank(pe_ratio)                        # 低 PE 策略

### 质量类 Alpha
rank(roa)                              # 资产回报率
rank(gross_margin)                     # 毛利率
rank(divide(cashflow_op, assets))      # 现金流质量

### 波动率类 Alpha
-rank(ts_std_dev(returns, 60))         # 低波动策略
rank(ts_skewness(returns, 120))        # 收益偏度
-rank(ts_corr(returns, market, 60))    # 低 Beta 策略

### 流动性类 Alpha
rank(divide(volume, shares_outstanding))  # 换手率
-rank(bid_ask_spread)                  # 低买卖价差

## Examples

### 简单表达式
ts_rank(revenue, 180)
rank(divide(earnings, assets))

### 中等复杂度
group_neutralize(rank(ts_delta(close, 20)), sector)
rank(ts_zscore(cashflow_op, 60) / ts_zscore(assets, 60))

### 复杂表达式
market_ret = ts_product(1+group_mean(returns,1,market),250)-1;
expected = beta_last_360_days_spy*(market_ret-rfr);
actual = ts_product(returns+1,250)-1;
actual-expected
