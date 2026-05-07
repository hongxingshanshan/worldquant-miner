---
name: QuantGPT VWAP因子案例
description: QuantGPT首个成功提交WorldQuant BRAIN的因子案例，包含完整参数优化过程和关键发现
type: reference
originSessionId: b111effb-e7f8-4cf7-b661-79b985b64ac2
---
# QuantGPT VWAP 衰减反转因子案例

## 核心因子表达式

### 种子因子
```
-1 * rank(ts_decay_linear(close / vwap, 5))
```

### 最终提交因子
```
-1 * rank(ts_decay_linear(close / vwap, 10))
```

**Alpha ID**: 78aAQjoL

## 投资逻辑

收盘价与成交量加权均价（VWAP）的比值，经过线性衰减加权后取反排名。当收盘价持续低于 VWAP 时看多——这代表机构卖出压力下的均值回归机会。

## 性能指标

| 指标 | 值 |
|------|-----|
| Sharpe | 1.69 |
| Fitness | 1.07 |
| Turnover | 46.14% |
| Returns | 18.63% |
| IS Tests | 全部通过 ✅ |
| 状态 | 已正式提交 |

## 参数优化过程

### 测试维度
- **窗口长度**: 5, 10, 20
- **WQ decay**: 0, 5, 10
- **中性化方式**: SUBINDUSTRY, MARKET

### 关键发现：中性化方式是突破点

| 配置 | Sharpe | Fitness | Turnover | Returns |
|------|--------|---------|----------|---------|
| window=5, SUBINDUSTRY | 1.93 | 0.88 | 69.25% | 14.51% |
| window=5, MARKET | 1.84 | 1.06 | 64.57% | 21.27% |
| **window=10, MARKET** | **1.69** | **1.07** | **46.14%** | **18.63%** |

### 为什么 MARKET 中性化更好？

**Why**: 因子的核心 alpha 来自行业间配置差异——不同行业的 close/vwap 偏离有系统性差异。SUBINDUSTRY 中性化把这个信号来源消除了。MARKET 中性化只去除市场整体偏差，保留了行业间的有效信号。

**How to apply**: 当因子信号来源于行业间差异时，优先使用 MARKET 中性化而非 SUBINDUSTRY。

### WQ decay 参数的影响

**发现**: WQ decay 参数对这个因子有害。所有 decay > 0 的变体 Fitness 都更低——额外的时序平滑削弱了短期反转信号。

**How to apply**: 对于短期反转类因子，decay=0 可能更优。

### 窗口长度选择

**选择 window=10 而非 window=5 的原因**:
- window=5 的 Sharpe 更高（1.84），但 Turnover 达到 64.57%，接近 BRAIN 的 70% 上限，风险余量不足
- window=10 的 Fitness 略高（1.07 vs 1.06）且 Turnover 更安全（46%）

**How to apply**: 在 Sharpe 和 Turnover 之间需要平衡，Turnover 接近 70% 上限时要谨慎。

## QuantGPT 工具信息

**GitHub**: https://github.com/Miasyster/QuantGPT

**核心技术栈**:
- 后端：Python 3.10+, FastAPI, 50+ WQ 兼容算子
- AI：glm-5.1 LLM（因子设计 + 双模型交叉验证）
- 数据：baostock + akshare（免费 A 股数据）
- WQ BRAIN 集成：httpx 同步客户端
- 前端：React 18 + TypeScript + Tailwind CSS 4
- MCP：8 个工具，Claude Code / Claude Desktop 原生调用

**WQ BRAIN 集成关键模块**:
- `wq_brain_client.py`: API 客户端（认证、模拟轮询、IS 检测、提交）
- `routes/wq_brain.py`: REST API 路由（异步提交 + SSE 进度）
- `mcp_server.py`: MCP 工具（`wq_brain_submit`）
- `wq_simulate.py`: 本地 WQ 模拟（不依赖 BRAIN API 的离线近似）

## 完整工作流

```
自然语言描述
    ↓
AI 生成因子表达式
    ↓
本地 A 股回测（2 分钟）
    ↓
本地评分 + 反过拟合检测
    ↓
WQ BRAIN 真实模拟（自动 API）
    ↓
IS Tests 全部通过？
    ↓ Yes
一键正式提交 Alpha
```

## 关键启示

1. **中性化方式的选择可以让 Fitness 差 20%**
2. **decay 参数的选择可以让信号强度差一倍**
3. **这些都不是本地回测能发现的**
4. **API 自动网格搜索** - 一个下午跑完 9 个变体，找到最优参数

## 评分体系对齐

QuantGPT 新增 WQ Alignment 维度（权重 25%）:
- WQ Sharpe 得分（40%）: `min(wq_sharpe / 1.25, 1.0) × 100`
- WQ Fitness 得分（40%）: `min(wq_fitness / 1.0, 1.0) × 100`
- Turnover 合规（20%）: Turnover 在 1%-70% 范围内得满分

**评级对标**:
- A 级: Fitness ≥ 1.0，可正式提交
- B+ 级: Sharpe 1.5+，IS 6/7 PASS
- B 级: Sharpe 0.9-1.2

## 文章来源

**URL**: https://zhuanlan.zhihu.com/p/2032510766050493800

**标题**: 开源量化工具 QuantGPT 首个因子正式提交 WorldQuant BRAIN — 从自然语言到 Alpha 提交的全自动化之路

**作者**: QuantGPT

**发布日期**: 2026-04-28
