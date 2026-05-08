# WorldQuant Brain 社区知识库

采集时间: 2026-05-09
来源: WorldQuant Brain Community Forums

---

## 目录

1. [模拟设置](#模拟设置)
2. [Alpha 研究](#alpha-研究)
3. [数据类型](#数据类型)
4. [相关性优化](#相关性优化)
5. [操作符技巧](#操作符技巧)

---

## 模拟设置

### NaN Handling（NaN 处理）

**来源**: [BRAIN TIPS] Demystifying Simulation Settings: NaN Handling

#### 什么是 NaN？
NaN（Not a Number）表示无效操作结果或缺失数据。例如，季度财报数据在公告之间可能不可用。如果股票在某天的输入数据是 NaN，模拟不会给该股票分配任何权重。

#### 为什么 NaN 很重要？
- 当股票的 Alpha 值为 NaN 时，该股票不会获得权重，降低覆盖率
- NaN 数据波动可能导致不必要的波动性和更高的换手率

#### NaN 处理选项
- **OFF（默认）**: 保留所有 NaN，需要在 Alpha 表达式中手动处理
- **ON**: 根据操作符类型自动处理 NaN
  - 时间序列操作符：NaN → 0
  - 分组操作符：NaN → 组值

#### 手动处理 NaN 的操作符
```python
ts_backfill(x)  # 用第一个可用的非 NaN 值替换 NaN
is_nan(x)       # 如果是 NaN 返回 1，否则返回 0
to_nan(x, value, reverse=False)  # 转换值
```

---

### Pasteurization（巴氏消毒）

**来源**: [BRAIN TIPS] Demystifying Simulation Settings: Pasteurization

Pasteurization 是一种数据清洗技术，用于处理极端值和异常值。

---

### Truncation（截断）

**来源**: Controlling Extremes: The Role of Truncation

截断用于控制极端值对 Alpha 的影响。通过设置截断参数，可以限制极端值的权重。

**常用截断值**: 0.08（8%）

---

## Alpha 研究

### Alpha 研究流程

**来源**: Introduction to Alpha Research and the Process of Fine-Tuning an Alpha

1. **想法生成**: 从研究论文、市场观察、数据探索中获得灵感
2. **表达式构建**: 使用操作符和数据字段构建 Alpha 表达式
3. **模拟测试**: 运行模拟，评估 IS（样本内）表现
4. **参数调优**: 调整窗口期、衰减等参数
5. **OS 验证**: 检查 OS（样本外）表现
6. **相关性检查**: 确保与现有 Alpha 低相关
7. **提交**: 通过所有测试后提交

### 提高 Sharpe 而不过拟合

**来源**: How to increase Sharpe without overfitting?

**关键原则**:
- 使用经济逻辑而非数据挖掘
- 保持表达式简洁
- 避免过度参数化
- 关注 OS 表现而非仅 IS
- 使用适当的衰减和中和化

### 测试期优化

**来源**: How can I use the test period to improve the OS performance?

- 测试期是验证 Alpha 稳定性的重要工具
- 如果 OS 表现差，考虑：
  - 简化表达式
  - 增加衰减
  - 检查数据质量
  - 验证经济逻辑

---

## 数据类型

### 价格成交量数据

**来源**: [BRAIN TIPS] Finding Alphas: Price Volume Data

**常用字段**:
- `close`: 收盘价
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `volume`: 成交量
- `vwap`: 成交量加权平均价

**常见模式**:
```python
# 动量
ts_return(close, 20)
# 波动率
ts_std_dev(close, 20)
# 成交量异常
volume / ts_mean(volume, 20)
```

### 基本面和模型数据

**来源**: [BRAIN TIPS] Finding Alphas: Fundamental and Model Data

**常用数据集**:
- `fnd6_*`: 公司基本面数据
- `model77_*`: 分析师因子模型
- `analyst4_*`: 分析师估计数据

### 新闻和社交媒体数据

**来源**: [BRAIN TIPS] Finding Alphas: News and Social Media

**数据集**:
- `news12_*`: 美国新闻数据
- `sentiment1_*`: 研究情绪数据
- `socialmedia_*`: 社交媒体数据

### 期权数据

**来源**: [BRAIN TIPS] Finding Alphas: Options Data

**数据集**:
- `option8_*`: 波动率数据
- `option9_*`: 期权分析数据

---

## 相关性优化

### 降低自相关和生产相关

**来源**: How to reduce self correlation and production correlation

**方法**:
1. **使用不同数据源**: 结合多个数据集
2. **时间维度变化**: 使用不同的窗口期
3. **操作符变换**: 尝试不同的操作符组合
4. **中和化**: 使用行业或子行业中和化
5. **衰减**: 增加衰减参数

### 结合多个数据集

**来源**: Reduce correlation by combining some fields from other datasets

```python
# 示例：结合价格和基本面数据
rank(close / ts_mean(close, 20)) + rank(earnings_surprise)
```

---

## 操作符技巧

### 操作符序列

**来源**: [BRAIN TIPS] Sequencing Multiple Operators in an Expression

**最佳实践**:
1. 从数据字段开始
2. 应用时间序列操作符（如 ts_mean, ts_std_dev）
3. 应用横截面操作符（如 rank, zscore）
4. 应用分组操作符（如 group_neutralize）

**示例**:
```python
# 正确的序列
group_neutralize(rank(ts_mean(close, 20)), industry)

# 错误的序列（类型不匹配）
ts_mean(rank(close), 20)  # rank 返回 SCALAR，ts_mean 需要 MATRIX
```

### 使用 GPT 生成洞察

**来源**: [BRAIN TIPS] Generate insights from a research paper using GPT

**步骤**:
1. 找到相关的研究论文
2. 提取关键发现和假设
3. 将假设转化为 Alpha 表达式
4. 测试和验证

---

## 常见问题

### Q: 如何提高覆盖率？
A:
- 使用 NaN Handling = ON
- 使用 ts_backfill() 处理缺失值
- 选择高覆盖率的数据字段

### Q: 如何提高 Fitness？
A:
- 优化 Sharpe 比率
- 降低换手率
- 减少相关性
- 确保稳定性

### Q: 如何选择窗口期？
A:
- 短窗口（5-20天）：捕捉短期信号
- 中窗口（20-60天）：平衡稳定性和敏感性
- 长窗口（60-250天）：长期趋势

---

## 参考链接

- [WorldQuant Brain Help Center](https://support.worldquantbrain.com/hc/en-us)
- [BRAIN TIPS 论坛](https://support.worldquantbrain.com/hc/en-us/community/topics/18068926798871-BRAIN-TIPS)
- [Getting Started with Research](https://support.worldquantbrain.com/hc/en-us/community/topics/4419282859415)
