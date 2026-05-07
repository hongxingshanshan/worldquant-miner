---
name: WorldQuant Brain新人指南-什么样的Alpha值得提交
description: 详细说明什么样的Alpha值得提交，包括数量与质量平衡、Turnover要求、Sub Universe测试、IS测试、PPAC机制等
type: reference
originSessionId: f69b19a4-f3c3-4bda-bf94-a2c3355f045a
---
## 到底要交什么样的Alpha？——新人指南

### 核心观点

判断一个Alpha是否值得提交不能只依赖单一指标（如Sharpe、Fitness、Margin），需要综合考虑多个维度。

### 数量与质量的平衡：螺旋上升原则

**数量不足的问题：**
- Portfolio不稳定
- 缺乏真实水平的验证
- 单个Alpha表现可能具有偶然性

**质量不足的问题：**
- Portfolio表现受损
- 资源浪费

**新人建议：**
- 每个月提交的Alpha数量不要少于 **40个**
- 先解决数量问题，再逐步提高质量要求

### 平台最低标准

#### Turnover要求

| 要求 | 说明 |
|------|------|
| 上限 | 不能高于 **70%**（避免交易成本过高） |
| 下限 | 不能低于 **1%**（避免持仓过于稳定） |

**进阶建议：**
- 水平提升后：控制在 **30%** 以下
- 不再断粮后：控制在 **15%** 以下

**特殊情况：**
- 如果Turnover较高但Margin非常优秀（如Margin超过10），高换手率可以接受
- 个人评判标准：`return/tvr > 0.3-0.4 && margin > 5-10%`

#### Sub Universe要求

- 最低标准：在更小Universe中的Sharpe必须达到至少 **50%** 的水平
- 目的：避免Alpha信号仅来源于流动性较低的小市值股票

#### Robust Test

两种方式：
1. 调整Settings中的指标（交易成本、滑点等）
2. 调整Expression中的参数

### IS测试与长期稳定性

**PNL理想形状：** 从左下角到右上角的稳定直线

**进阶标准：**
- 过去10年中，Sharpe超过1的年份不少于X年
- 特别关注最近两年的PNL表现，尤其是2022年

### PPAC与低相关性

**Self Correlation (SC) 标准：**

| SC范围 | 评价 |
|--------|------|
| 0.5-0.7 | 平台通过标准 |
| 0.3-0.5 | 很不错，对Portfolio有提升 |
| < 0.3 | 非常低，优秀 |

**Product Correlation (PC)：**
- PC超过 **0.7** 无法进入实盘获得weight
- 必须控制PC不超过0.7

### 经济学意义

- 写好Description非常重要
- Description是学习日记，帮助理解经济学意义
- 具有经济学意义的Alpha能更好适应不同市场环境

### 关键要点总结

1. **不要过度依赖单一指标**
2. **重视数量与质量的平衡**（每月至少40个）
3. **关注整体Portfolio的表现**
4. **通过写Description梳理思路和逻辑**
5. **控制Turnover在合理范围**
6. **确保Sub Universe测试通过**
7. **保持低相关性**（SC < 0.7, PC < 0.7）

---
**来源：** WorldQuant Brain 中文论坛
**作者：** XZ23611
**日期：** 2025年9月1日更新
