# WorldQuant Brain Alpha Guide

## Best Practices

### 1. 表达式设计原则
- **简洁性**: 简单表达式往往更稳定，避免过度复杂的组合
- **可解释性**: 确保表达式有清晰的金融逻辑
- **稳定性**: 使用适当的参数避免过度拟合

### 2. 常用参数范围
| 参数类型 | 推荐范围 | 说明 |
|---------|---------|------|
| 时间窗口 | 20-180 | 过短易噪音，过长易滞后 |
| 截断值 | 0.01-0.08 | 控制极端值影响 |
| 中性化 | INDUSTRY/SUBINDUSTRY | 消除行业偏差 |

### 3. 高质量 Alpha 特征
- Fitness > 0.5
- Sharpe > 1.5
- Turnover < 0.5
- 低相关性

## Common Patterns

### 时间序列模式
ts_rank(field, window)      # 时序排名
ts_delta(field, window)     # 时序变化
ts_zscore(field, window)    # 时序标准化
ts_decay_linear(field, window)  # 线性衰减

### 截面模式
rank(field)                 # 截面排名
group_neutralize(field, group)  # 组内中性化
zscore(field)               # 截面标准化

### 组合模式
rank(ts_delta(field1, 20) / ts_delta(field2, 20))
group_neutralize(rank(ts_mean(field, 60)), sector)

## Tips

1. **避免常见错误**:
   - 不要对事件数据使用时序算子
   - 注意算子类型兼容性（SCALAR/VECTOR/MATRIX）
   - 避免除零（使用 divide(a, b) 而非 a/b）

2. **数据字段选择**:
   - 优先使用高频更新的字段
   - 避免使用过于稀疏的数据
   - 注意数据延迟（delay 参数）

3. **性能优化**:
   - 减少 group_neutralize 的嵌套层数
   - 避免过长的表达式链
   - 使用 winsorize 控制极端值
