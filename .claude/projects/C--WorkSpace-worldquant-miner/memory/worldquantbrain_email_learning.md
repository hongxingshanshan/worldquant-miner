---
name: WorldQuant Brain 邮件学习笔记
description: 从 WorldQuant BRAIN 邮件中学习的 Alpha 策略和知识点
type: project
originSessionId: current
---

## 邮件来源学习 (2026-05-06)

### 邮件 1: IQC 2026 – Week 7 Newsletter (2026-05-06)

#### 学习资源链接
- **Key dates in IQC Stage 1**: IQC 第一阶段关键日期
- **Research Paper 06**: Penny Wise, Dollar Foolish: Buy-Sell Imbalances On and Around Round Numbers
- **Quant terms explained**: 足球和国际象棋类比解释量化术语 - 基础知识
- **Quantcepts: Options Data**: 期权数据课程
- **Webinar Recording: Price Volume Data**: 价量数据网络研讨会录像

#### 多语言支持
研讨会提供多种语言版本：
- English (Singapore/Malaysia)
- Korean
- Simplified Chinese (简体中文)
- Vietnamese

---

### 邮件 2: Debt Safety Detector - BRAIN Alpha Ideas Series (2026-05-06)

#### Alpha 策略：债务安全检测器

**Idea (理念):**
- FFO (Funds from Operations) 代表公司运营产生的现金流
- 衡量公司持续运营效率和盈利能力
- 将 FFO 与长期债务比较，可评估公司用核心运营现金流偿还长期债务的能力

**Hypothesis (假设):**
- 运营收入相对于债务较高的公司，未来可能表现更好

**Implementation (实现):**
- 对 FFO 与长期债务的比率进行排名

**Expression (表达式):**
```
rank(fnd6_fopo/debt_lt)
```

**进阶思考:**
- 能否通过时间序列比较 FFO 与长期债务的比率，突出财务健康状况的改善，产生更好的信号？

**数据字段说明:**
| 字段 | 说明 |
|------|------|
| `fnd6_fopo` | Funds from Operations (运营资金) |
| `debt_lt` | Long-term Debt (长期债务) |

---

### 邮件 3: 欢迎！开始你的 WorldQuant BRAIN 之旅 (2026-05-05)

#### 平台入门指南
- 欢迎加入 WorldQuant BRAIN 用户社群
- 平台提供 Alpha 研究和提交功能

---

### 邮件 4: 验证 WorldQuant BRAIN 账号 (2026-05-05)

#### 账号验证
- 需要点击验证链接完成邮箱验证
- 验证后可完整使用平台功能

---

### 邮件 5: [BRAIN] Congratulations on reaching the Bronze level! (2026-05-02)

#### 成就解锁
- 达到 Bronze (青铜) 级别
- 这是 WorldQuant Challenge 的第一个里程碑
- 包含附件

---

### 邮件 6: Welcome to the International Quant Championship 2026 (2026-05-01)

#### IQC 2026 赛事信息
- 欢迎参加 WorldQuant BRAIN 的国际量化锦标赛 2026

---

## 关键学习点总结

### Alpha Ideas Series 系列
WorldQuant BRAIN 定期发送 Alpha Ideas 系列邮件，提供：
1. **Idea**: 经济学理念
2. **Hypothesis**: 可验证的假设
3. **Implementation**: 具体实现方法
4. **Expression**: 可直接使用的表达式
5. **What's next?**: 进阶思考方向

### 学习资源类型
1. **Research Papers**: 研究论文
2. **Quantcepts**: 量化概念课程
3. **Webinars**: 网络研讨会录像
4. **Alpha Ideas**: Alpha 策略示例

### 推荐学习路径
1. 观看 Introduction to Alphas 课程视频
2. 学习 Quantcepts 系列课程
3. 阅读 Research Papers
4. 实践 Alpha Ideas 系列中的表达式
5. 参加网络研讨会

---

## 下一步行动
1. 尝试 `rank(fnd6_fopo/debt_lt)` 表达式
2. 观看 Price Volume Data 网络研讨会
3. 学习 Options Data 课程
4. 阅读 Research Paper 06
