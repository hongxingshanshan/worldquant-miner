# WorldQuant Brain Datasets Reference

## Popular Fields

### 价格数据
- close: 收盘价
- open: 开盘价
- high: 最高价
- low: 最低价
- volume: 成交量
- returns: 收益率
- vwap: 成交量加权平均价

### 财务数据 (fnd6_*)
- fnd6_mfma2_revt: 收入
- fnd6_mfma2_oancf: 经营现金流
- fnd6_mfma2_ni: 净利润
- fnd6_mfma2_at: 总资产
- fnd6_mfma2_te: 股东权益

### 分析师数据 (anl4_*)
- anl4_qfd1_az_eps_number: EPS 预测
- anl4_qfd1_az_rev_number: 收入预测

### 新闻数据 (nws12_*)
- 注意: 事件数据，不能用于时序算子

## Categories

### 基础面数据
- fnd6_*: 季度/年度财务数据
- fscore_*: 评分数据

### 技术面数据
- beta_last_*_days_*: Beta 值
- ts_*: 时序计算结果

### 另类数据
- nws12_*: 新闻情感
- anl4_*: 分析师预测
