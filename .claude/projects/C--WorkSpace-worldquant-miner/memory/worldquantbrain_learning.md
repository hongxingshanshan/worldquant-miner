---
name: WorldQuant Brain 学习笔记
description: WorldQuant BRAIN 平台学习笔记和关键知识点
type: project
originSessionId: a3885ee6-994a-432e-9801-77eaed18686a
---
## 学习进度 (2026-05-06 更新)

### ✅ 已完成学习

#### 1. NaN 处理 (BRAIN TIPS)
- **NaN 定义**: "Not a Number"，表示无效操作或缺失数据
- **重要性**: NaN 会降低覆盖率，减少交易机会，可能降低 Sharpe 比率
- **NaN Handling 设置**:
  - Off (默认): 保留 NaN，需要手动处理
  - On: 时间序列操作符将 NaN 替换为 0，组操作符替换为组值
- **手动处理操作符**:
  - `ts_backfill()`: 用第一个可用的非 NaN 值替换 NaN
  - `is_nan()`: 检测 NaN（返回 1 或 0）
  - `to_nan()`: 转换值为 NaN 或 NaN 为值

#### 2. Starter Pack 入门指南
- **研究顾问**: 需要 10,000 分以上才有资格申请
- **金融基础知识**: 做多、做空、交易量、开盘价/收盘价
- **量化分析**: Alpha 是将输入数据转化为权重向量的算法
- **分析方法**:
  - 技术分析: 分析价格变动和成交量
  - 基本面分析: 检查经济和财务因素
  - 时间序列分析: 观察变量随时间变化
  - 横截面分析: 将公司与同行业竞争对手比较

#### 3. Introduction to Alphas
- **Alpha 定义**: 数学模型或策略，以表达式形式书写
- **Alpha 生命周期**: 想法 → 表达式 → 回测 → 评估 → 修改/提交
- **权重**: 正权重 = 多头，负权重 = 空头

#### 4. BRAIN Expression Language
- **Fast Expression**: WorldQuant BRAIN 专有编程语言
- **组成部分**: 数据集、运算符、数字值
- **语法特点**: 块注释 `/* */`，语句分隔 `;`，无类/对象/指针/函数

### 🔄 进行中
- 尝试使用 Ravenpack News Dataset 创建有效的 News Alpha
- 探索其他数据集（Options、Fundamental）

### ⏳ 待学习
- Operators 详细文档（已浏览概览）
- 中文论坛精华帖子
- Global Research webinars

## 下一步
1. 尝试使用 Ravenpack News Dataset (nws18_bee, rp_nip_assets) 创建 News Alpha
2. 探索 Options 数据集的其他信号
3. 结合多种数据源创建组合 Alpha
4. 观看 Introduction to Alphas 课程视频

### ✅ 新增学习内容 (2026-05-05)

#### 5. Intermediate Pack - Understand Results [1/2]
- **IS 概要指标**:
  - Sharpe: 衡量超额回报与波动性比率，要求 > 1.25
  - Turnover: 交易频率，要求 1% - 70%
  - Fitness: Sharpe * |Returns| / max(Turnover, 0.125)，要求 > 1.0
  - Returns: 年化收益率
  - Drawdown: 最大回撤幅度
  - Margin: 每美元交易额的利润
- **常见问题解决**:
  - Sharpe 过低: 增加回报或降低波动性
  - 权重集中: 使用 rank()、ts_backfill()、设置截断
  - 子股票池 Sharpe: 增加 universe 大小（如 TOP3000）

#### 6. Intermediate Pack - Improve your Alpha [2/2]
- **运算符使用技巧**:
  - Divide (/): 将数据字段除以其他字段
  - Rank(x): 限制极端值，均匀分布 0.0-1.0
  - Ts_rank: 时间序列排名
  - Ts_delta: 计算变化量
- **回测设置调整**:
  - Region: 选择市场
  - Universe: 选择股票池（TOP3000 流动性最高）
  - Decay: 减少换手率，但过大会削弱信号
  - Truncation: 设置最大权重（推荐 5-10%）
  - Neutralization: 市场中性化，降低系统性风险

#### 7. Sentiment1 Dataset
- **数据特点**: 结合情绪指标、分析师共识、盈利惊喜
- **关键字段**:
  - `snt1_cored1_score`: 情绪分数（>5 看涨，<-5 看跌）
  - `snt1_d1_earningssurprise`: 盈利惊喜
  - `snt1_d1_buyrecpercent`: 分析师买入推荐比例
  - `snt1_d1_analystcoverage`: 分析师覆盖度
- **覆盖范围**: TOP3000 约 2000 只股票
- **建议**: 使用 decay 平滑高频数据，注意长回看期（>63天）可能失去相关性

#### 8. Alpha Examples for Beginners
- **示例 1: Operating Earnings Yield**
  - 假设: 营业收入高于过去1年 → 买入
  - 表达式: `ts_rank(operating_income, 252)`
- **示例 2: Appreciation of liabilities**
  - 假设: 负债公允价值增加 → 财务健康恶化 → 做空
  - 表达式: `-ts_rank(fn_liab_fair_val_l1_a, 252)`
- **示例 3: Power of leverage**
  - 假设: 高负债资产比（排除财务健康差的）→ 利用杠杆增长 → 做多
  - 表达式: `liabilities/assets`
- **示例 4: Earnings Yield Momentum**
  - 假设: 盈利收益率高 → 低估值 → 做多
  - 表达式: `group_rank(ts_rank(est_eps/close, 60), industry)`
- **示例 5: Short-Term Sentiment Volume Stability**
  - 假设: 情绪成交量波动大 → 关注度不稳定 → 做空
  - 表达式: `-ts_std_dev(scl12_buzz, 10)`

#### 9. Must-read Posts (必读论坛帖子)
- **Alpha 研究周期**: 理念 → 实现 → 优化
- **关键主题**:
  - 如何获得更高的 Sharpe
  - 如何潜在地增加 Alpha 的回报
  - 如何降低 Alpha 的相关性
  - 如何降低换手率
  - 如何潜在地减少 PnL 波动
  - 如何选择合适的中性化
  - 如何避免过度拟合

#### 10. Finding Alphas: News and Social Media
- **五个 Alpha 理念** (来自《Finding Alphas》第22章):
  1. **Sentiment 情绪**: 使用情绪分数 (nws18_bee) 判断正面/负面/中性
  2. **Novelty 新颖性**: 使用新闻影响投影 (rp_nip_assets) 识别新独特信息
  3. **Relevance 相关性**: 使用 nws18_relevance 和 nws18_qcm 增强信号
  4. **No News is Good News**: 新闻敏感股票在不确定性增加时可能减少机构投资
  5. **News Momentum 新闻动量**: 分析新闻数据识别未被有效反映的趋势
- **推荐数据集**: Ravenpack News Dataset
- **高换手率解决方案**:
  - 覆盖率问题: 使用 ts_backfill 填充缺失数据
  - 数据变化频繁: 使用 hump 和 hump_decay 操作符限制变化

## 关键发现

### Sentiment 数据 Alpha 测试结果
| 表达式 | Sharpe | Fitness | 结论 |
|--------|--------|---------|------|
| `ts_decay_linear(scale(group_neutralize(scl12_buzz, industry)), 5)` | -1.59 | -0.91 | 不推荐 |
| `ts_backfill(winsorize(ts_decay_linear(scale(vec_avg(nws12_afterhsz_sl)), 10)), 60)` | 0.77 | 0.26 | 不推荐 |
| `ts_backfill(winsorize(ts_decay_linear(scale(group_neutralize(snt1_cored1_score, industry)), 5) * volume), 60)` | -0.72 | -0.41 | 不推荐 |
| `ts_backfill(winsorize(ts_decay_linear(scale(group_neutralize(snt1_d1_dynamicfocusrank, industry)), 5) * volume), 60)` | -0.01 | -0.00 | 不推荐 |
| `ts_backfill(winsorize(ts_decay_linear(scale(group_neutralize(scl12_sentiment, industry)), 5) * volume), 60)` | 0.04 | 0.01 | 不推荐 |
| `ts_backfill(winsorize(ts_decay_linear(scale(group_neutralize(snt1_d1_netrecpercent, industry)), 5) * volume), 60)` | -0.70 | -0.47 | 不推荐 |
| `ts_backfill(winsorize(ts_decay_linear(scale(group_neutralize(snt1_d1_earningsrevision, industry)), 5) * volume), 60)` | -0.52 | -0.34 | 不推荐 |

### 结论
Sentiment 数据的 Alpha 表达式效果都不理想，需要进一步研究或尝试其他数据组合。

### ✅ 新增学习内容 (2026-05-05)

#### 11. BRAIN TIPS 论坛帖子学习

##### 11.1 Simulation Settings 深入理解
- **Pasteurization 设置**:
  - 作用：将不在选定 Universe 中的股票的 Alpha 值设为 NaN
  - 默认设置：On
  - `pasteurize()` 操作符：还额外将 INF 值转为 NaN，可控制何时何地应用
  - 用途：比较 Universe 内股票与全市场股票时设为 Off

##### 11.2 Truncation（截断）的重要性
- **为什么需要**：金融数据噪声大，单只股票可能主导整个投资组合
- **作用**：限制单个股票对信号的最大影响
- **全局设置 vs 操作符**：
  - 全局设置：Max Weight 是计算后的硬限制
  - Alpha 内部处理：使用 `winsorize()` 或 `rank()` 在计算前平滑
- **实用技巧**：Sharpe 高但 Drawdown 失败时，检查异常值

##### 11.3 Statistical Neutralization（统计中性化）
- **问题**：有些 Alpha 只是依赖于已知市场效应（规模、价值、行业趋势）
- **解决方案**：使用 PCA 识别并剥离隐藏模式
- **优势**：更稳健、更低相关性、聚焦独特信号
- **使用方法**：设置 `'neutralization': 'STATISTICAL'`

##### 11.4 提高 Sharpe 而不过拟合
- **核心方法**：
  - 聚焦于有逻辑基础的想法
  - 使用 `rank` 或 `ts_rank` 标准化信号
  - 较短回看期（60、20、5天）比年度（250天）更好
  - 调整 decay、中性化设置
- **组合 Alpha 技巧**：
  - 先 `group_neutralize` 再 `scale` 确保平等贡献
  - 使用非线性 if/else 条件组合
  - 确保组合的 Alpha 不高度相关

##### 11.5 降低 Self Correlation 和 Production Correlation
- **多样化策略**：
  - 使用不同数据源、时间框架、方法
  - 探索新区域：EUR, AMR, GLB, JPN
  - 使用新操作符和高 Value score 数据集
  - 不同 Universe 和 Neutralization 设置
- **技术方法**：
  - PCA 转换为正交组件
  - Hierarchical Risk Parity (HRP)
  - Decorrelation（信号白化）
- **实用技巧**：只看最近3个月的相关性

#### 12. WorldQuant Challenge 评分规则

##### 概述
- 永久的在线个人比赛，提交 Alpha 提高得分和排名
- **10,000 分**可获得研究顾问机会邀请
- 新用户自动参加

##### 级别
| 级别 | 得分要求 |
|------|----------|
| 青铜 | > 1,000 |
| 银 | > 5,000 |
| 金 | > 10,000 |

##### 评分标准
- 得分基于 Alpha 的**数量和质量**（5年样本内表现）
- 最高日得分 **2,000 分**（每天提交 1-2 个 Alpha）
- **没有负分**，得分不会降低
- 得分每天在东部标准时间**凌晨 3 点**更新

##### 质量因素取决于
- **股票池**：股票池较小的得分较高
- **自相关性**：越小越好
- **适应度**：越高越好
- **延迟**：D1 Alpha 贡献大于 D0 Alpha

### ✅ 新增学习内容 (2026-05-05)

#### 13. 中文论坛课程学习 - 2026年IQC专辑《BRAIN x AI 零基础入门量化》

##### Course 1 作业内容
**Day1 课后作业：**
- **任务1**：在 AI 的帮助下，至少成功提交 1 个 Alpha，并提供截图
  - 参考文档：Alpha Examples for Beginners, Alpha Examples for Bronze/Silver Users
- **任务2**：学习平台上所有关键术语的计算公式，推荐使用 AI 工具
- **任务3**：阅读 "How BRAIN platform works" 并回答问题
  - 问题：假设全市场共5个股票，收盘价 [5,15,66,85,25]，Alpha表达式为 "-close"
  - 在 Market Neutralization 下计算交易权重

**任务3 答案解析：**
1. 原始信号：`-close` → `[-5, -15, -66, -85, -25]`
2. 市场中性化：平均值 `-39.2`，减去平均值 → `[34.2, 24.2, -26.8, -45.8, 14.2]`
3. 归一化：绝对值总和 `145.2`，除以总和 → `[0.2355, 0.1667, -0.1846, -0.3154, 0.0978]`
4. 结果：Long Count = 3，Short Count = 2

##### Course 2 作业内容
**参考文章：**
- 《101个Alpha》论文：展示如何将文字语言转化成数学语言
- Research-paper-1-The-Momentum-of-News
- Understanding Data in BRAIN: Key Concepts and Tips

**Day2 课后作业（所有必做）：**
- **必做1**：概念辨析 - 什么是 long-count 和 short-count？平台中如何计算？
- **必做2**：研究 datafield `anl4_cff_flag` 的更新频率，并解释理由
- **必做3**：解释 `ts_std_dev(x, d)` operator 能测出数据更新频率的逻辑
- **必做4**：使用 get datafields 批量生成 Alpha，实现 20 次以上回测
- **必做5**：使用 AI 实现"新闻动量"Alpha想法，给出 3 个 Alpha 表达式
  - 核心理念：新闻反映并预告公司基本面的持续性，市场对"新闻本身"和"新闻的可持续性"存在低反应

##### Course 3 作业内容
**必做 Task：**
1. 任选一数据集，使用 AI 为数据集提供模板（至少 3 个模板）
2. 任选其中一个模板，使用代码展开并拼装成多个表达式，阐述搜索空间
3. 回测这些 Alpha 并获得至少一个可提交的 Alpha
4. 必做阅读：一文带你读懂 "Genius Program" -- 高阶顾问 Quarterly Payment 有机会获得高达 8000 USD 保底
5. 选做：完成研究顾问问卷，截图 workday task portal

**注意事项：**
- 不要踩点提交，最好每天都保持提交
- Challenge score 每天仅更新一次且上限为 2000 分/日
- 需要在任一问题展示点赞或点踩，证明对 AI 答案已进行思考

#### 14. 中文论坛精华帖子学习

##### 14.1 【新人指南】到底要交什么样的Alpha？

**核心观点：**
- Alpha 质量没有单一"金标准"，不能过度依赖 Sharpe、Fitness 或 Margin 等单一指标
- 判断 Alpha 是否值得提交更像诊断病情，需要多维度综合评估

**数量与质量的平衡：**
- 每月提交的 Alpha 数量不要少于 40 个
- 数量不足：Portfolio 不稳定，缺乏真实水平验证
- 质量不足：拉低整体 Portfolio 表现，浪费资源
- 螺旋上升原则：先解决数量问题，再逐步提高质量

**平台最低标准解读：**

| 指标 | 要求 | 进阶建议 |
|------|------|----------|
| Turnover | 1% - 70% | 进阶：< 30%；高手：< 15% |
| Sub Universe | Sharpe ≥ 50% | 避免 Alpha 仅依赖小市值股票 |
| Self Correlation | < 0.7 | PPAC 要求 Pool 内 < 0.5 |

**Turnover 深入理解：**
- 高换手率带来交易手续费，但不应为节省手续费让 Alpha 变成"死鱼"
- 个人评判标准：`return/tvr > 0.3-0.4 && margin > 5-10%`
- 能带来收益和 Sharpe 提升的高换手率是值得的

**Product Correlation (PC)：**
- PC 超过 0.7 无法进入实盘获得 weight
- 平台已有相同 Alpha，新 Alpha 没有新价值

##### 14.2 Combined Alpha Performance 提升指南

**定义：**
- 把所有地区已提交的 Alpha 和 Super Alpha 等权组合
- 计算 2023-2025 年（semi-OS）的费后表现

**三个关键词：**

**1. 分散（Diversity）：**
- 地区分散：不同地区市场环境、手续费、波动性不同
- 降低同一地区的 SC：多用不同类型的模板和数据类别
- 多地区、多模板、多数据类别、多中性化（尤其是风险中性化）

**2. 质量：**
- 质量比数量更重要
- 一个负的 OS Sharpe 需要 2 个正的 OS Sharpe 来弥补
- 关注 Alpha 的核心逻辑，使用 AI 和 MCP 验证

**3. 手续费：**
- 亚洲市场（ASI）：Margin 尽量保持 15 以上，20 以上为佳
- 其他地区：Margin 建议 10 以上
- 优化交易频率，避免低 Margin 的 Alpha

**Super Alpha（SA）注意事项：**
- IS Sharpe 高的 SA 不一定 OS 表现好
- 质量差的 RA 会让 SA 成为"双倍伤害"
- 过滤掉 IQC 表现差的 RA，剔除 product_correlation > 0 的 RA

##### 14.3 Alpha 模板合集

**模板分类：**

**1. 基础模板：**
- `group_neutralize(group_zscore(vec_avg({data}),sector),bucket(rank(cap),range="0.1,1,0.1"))`
- 使用 `regression_neut` 进行中性化处理

**2. 时间序列模板：**
- `ts_rank(ts_backfill({datafield}, 30), 504)` - 时间序列排名
- `ts_decay_linear` - 线性衰减
- `ts_zscore` - 时间序列标准化

**3. 组合模板：**
- 多信号组合：`group_rank(signal1) * group_rank(signal2) * group_rank(signal3)`
- 条件交易：`trade_when(condition, alpha, exit_condition)`

**4. 新闻情绪模板：**
- 新闻动量：`ts_mean(group_rank(processed_news_sentiment,industry), 20)`
- 情绪反转：结合 `ts_delta` 和 `group_neutralize`

**5. 基本面量化模板：**
- 财务数据回归：`regression_neut(ts_zscore(A,500), ts_zscore(B,500))`
- 多因子组合：ROA、PB、ITR、DtA 等组合

**重要提示：**
- 部分模板存在严重 overfitting 风险
- 建议从经济逻辑出发，不使用过于复杂的公式
- 注意口径问题（财报发布时间差异）和数据及时利用问题

##### 14.4 BRAIN 平台自学路径图

**学习路径：**

**1. 介绍 / Introduction：**
- 什么是 Alphas? / Introduction to Alphas
- Brain 平台的原理 / How BRAIN platform works
- Brain 快速表达式 / Introduction to BRAIN Expression Language
- 理解平台规则和 BRAIN Consultant 项目

**2. 运算符 / Operators & 数据集 / Datasets：**
- 理解数据结构和基本概念 / Understanding Data in BRAIN
- 如何使用数据浏览器 / How to use the Data Explorer
- 运算符 / Operators
- 三维数据类型 / Vector Data Fields 🥉
- 分组数据类型 / Group Data Fields 🥈
- 重要：6 ways to quickly evaluate a new dataset

**3. 模拟回测 Alpha / Simulation & 评估 Alpha 表现：**
- 如何进行回测前的参数设定 / How to choose the Simulation Settings
- 模拟你的第一个 Alpha / Simulate your first Alpha
- 评估指标 / Parameters in the Simulation results
- 如何理解回测表现 / Intermediate Pack - Understand Results
- Alpha 提交测试 / Clear these tests before submitting an Alpha
- 什么是样本内和样本外 / IS, Semi-OS, and OS

**4. 如何改进 Alpha / Alpha Improvement：**
- 提高 Alpha 表现 / Intermediate Pack - Improve your Alpha
- 如何使用条件运算符 / Intermediate Pack - Conditional Operators
- 改进 Alpha 必读 / Must-read posts: How to improve your Alphas
- 解读需要通过的各项测试

**5. Alpha 例子：**
- 新手 Alpha 例子 / Alpha Examples for Beginners
- Alpha Examples 合集

##### 14.5 Alpha 灵感启示录合集

**研究方法：**
- 从一篇研报论文开始，找到核心思想需要的数据集、操作算符
- 进行论文复现，再进一步加强信号

**按地区分类的灵感来源：**

**CHN-D1（中国市场，D1延迟）：**
- ⭐ 股票收益是球队还是硬币？
- ⭐ A股换手率类因子
- ⭐ 基于价量互动的选股因子
- 盈利加速的定量刻画与高增长组合的构建
- 处置效应下的换手率因子策略分析
- A股市场拥挤度因子
- A股动量类因子
- 隔夜涨跌反转
- 跳跃因子在A股的表现

**USA-D1（美国市场，D1延迟）：**
- ⭐ 通过期权隐含价格与股票市场价格的差异寻找投资机会
- ⭐ 基于遗憾规避逻辑近似构建因子
- ⭐ 基于量价信息的可靠投资信号
- 分析师建议和回报率
- The Momentum of News
- 期权和股票成交量比率和未来回报率

**Super Alpha 灵感：**
- ChatGPT Portfolio Selection
- Risk Parity
- Modern Portfolio Theory
- Post-Modern Portfolio Theory
- 从面试题到 Regular Alpha 和 Super Alpha 的思考

**General（通用）：**
- 从价量看技术指标总结 (Technical Indicator)
- 流行基本面指标汇总 (Fundamental indicators)
- 市场异常情况总结 (Market Anomalies)
- 投资因素总结 (Factor investing)

##### 14.6 IQC 2025 中国大陆区第一名参赛经验分享

**参赛时间轴：**
- 25年春节期间：第一次了解到 WorldQuant Brain 平台
- 三月份：开始作为 user 提交 alpha 并报名 IQC
- 一个星期后：达到 10000 分
- 大约一个月后：成为有条件顾问
- 大约三个月后：成为正式顾问
- 7月11号：在上海参加 IQC China Regional Final
- 9月28号：在新加坡参加 Global Final

**参加 IQC 的好处：**
1. **更平滑的难度曲线**：IQC 期间即使成为有条件顾问，alpha 的提交标准仍然与 user 保持一致
2. **更快更早的收入激励**：
   - 每日 payment（在单独的 consultant pool 中计算，更容易拿高 payment）
   - IQC 比赛奖金（China Regional Final 可获得 3000 刀奖金）
   - 免费的五星级酒店和美食
3. **深入接触量化行业的机会**：与业内人员接触，进入 WorldQuant 实习的机会

**赛事规则注意事项：**
- 队伍人数：一至四个同校的参赛选手进行组队，单人队也能取得好成绩
- 尽量不要发生退队或队伍解散，否则可能面临 score 清零
- IS/OS 记分比例：1 比 3（OS 占主导地位）

**Alpha 产出技术路线：**
1. 机器暴力遍历 alpha 并不断优化遍历的速度
2. 参考研报论文构造可解释的 alpha
3. 引入 AI 工具创造更多可能

**关键经验：**
- **Alpha pool 的多样性（diversity）**：较高的 diversity 有助于减轻 OS 反向走势对整体 alpha pool 的影响
- **避免 overfitting 的方法**：
  - 通过微调表达式做稳健性测试
  - 用 rank 之类的操作符对整个 alpha 套上一层"重新映射"
  - 通过调整 settings 做稳健性测试，观察 alpha 逻辑是否在另一个市场中也站得住脚

##### 14.7 2026年 IQC 第一阶段 FAQ 与进阶指南

**赛事日程（2026年）：**
- 报名及组队开启：2026年3月17日
- 第一阶段 Alpha 提交开启：2026年3月17日
- 报名及组队截止：2026年5月13日
- 第一阶段 Alpha 提交截止：2026年5月18日
- 晋级通知：最迟 2026年5月22日
- 时间标准：美东时间 (EST) 23:59

**IQC 顾问收益构成：**
1. **Base Payment**：每日提交的前 4 个 Alpha 有机会赚取 1 至 60 美元
   - 数量因素：确保每日提交满 4 个符合标准的 Alpha
   - 质量因素：高夏普比率、高 Fitness、低相关性
   - 自我增长因素：保持持续的创新和改进
   - 相对竞争力：与全平台顾问横向对比
2. **季度奖金**：每季度奖励 100 至 25,000 美元
   - 要求：一个季度内至少有 20 天每天提交至少 1 个 Alpha
3. **推荐费**

**核心评分逻辑：**
- 双重评分体系：个人资格赛积分 + 团队合并表现分数
- 解锁机制：团队中至少一名成员达到 10,000 分时解锁合并表现分数
- 权重分配：25% IS 分数 + 75% OS 分数
- OS 分数仅在赛段结束时公布

**提升 Alpha 质量的建议：**
1. **注重经济学含义**：高评分不代表高质量，专注简单且稳健的逻辑
2. **善用 Compare Performance 功能**：观察提交前后的指标变化
3. **警惕 IS 分数陷阱**：IS 分数仅占 25%，OS 占 75%
4. **质量胜过数量**：每日提交 1-2 个高质量因子（满分 2000 分/日）
5. **分散化提交策略**：
   - 数据集多元化
   - 模板与算子多样化
   - 中性化与 Universe 分散
6. **避免过度拟合**：严禁为了强行通过相关性测试而插入随机噪声

##### 14.8 【Alpha灵感】股票收益是球队还是硬币？

**研报来源：**
- 标题：个股动量效应的识别及"球队硬币"因子构建——多因子选股系列研究之四
- 作者：曹春晓
- 数据集：Price Volume Data for Equity CHN

**核心概念：**
- **球队效应**：当人们对事物"可知性"较低时，倾向于猜测动量（与最近结果相同）
- **硬币效应**：当人们对事物"可知性"较高时，倾向于猜测反转
- **应用逻辑**：
  - 投资者将股票视为"球队"时，认为其会发生动量效应，最近上涨→超买→未来回落
  - 投资者将股票视为"硬币"时，认为其会发生反转效应，最近上涨→超卖→未来补涨
  - **Alpha 机会**：从量价指标中发现"收割"机会

**因子构建（三个子因子）：**

**1. 波动翻转因子：**
```
日内收益率的波动率 < 市场截面均值 ? -1*当月日内收益率 : 当月日内收益率
```
- 计算最近 20 天的日间收益率均值和标准差
- 日内收益 = close/open - 1
- 日间收益 = returns

**2. 换手翻转因子：**
```
换手率 < 市场截面均值 ? -1*日内收益率波动率 : 日内收益率波动率
```
- 计算翻转后的翻转收益率 20 日均值

**3. 隔夜翻转因子：**
- 隔夜距离 = |隔夜涨跌幅 - 市场平均水平|
- 换手距离 = |t-1日换手率变化量 - 市场均值|
- 按波动翻转方法构造

**回测设置建议：**
- **Decay**：量价 alpha 有效期较短，推荐 0、5、10、20，最佳为 10（两周）
- **中性化**：
  - 行业中性化：效果好但相关性过高（约 0.8）
  - Slow+Fast Factor 中性化：对风险因子无额外暴露，表现更稳定
- **市场差异**：
  - CHN 市场：散户多，喜欢短线，反转效应强
  - 欧美市场：机构多，动量效应强，相同构造方法效果不佳

**关键发现：**
- 量价因子趋同化难以避免，优秀量价因子的 PnL 可能近似
- 可尝试引入其他数据（基本面、分析师预期、财务指标）赋能
- 欧美市场可从"机构反应过度迟钝"角度刻画球队硬币

##### 14.9 从零建立自动化 Alpha 系统经验分享

**背景：**
- 作者从 2024 年了解 WorldQuant，2025 年正式开始学习
- 手动和 AI 聊天、提交 Alpha 效率太低（每天花好几个小时只测试几十个）
- 决定建立自动化系统，只需和 AI 交流升级系统、提供新方法

**建立自动化系统的六个步骤：**

**一、定义工作流**
- 回顾工作流：研究灵感 → 表达式生成与评估 → 回测 → 反思优化
- 与 Deepseek 专家模式对话，采用问答形式逐步完善
- 半小时即可拥有一份完整的工作流文档

**二、生成项目架构**
- 开新会话，把工作流文档给 AI
- 定义 AI 为"项目架构专家"，生成项目架构文档
- 推荐代码工具：
  - Claude Code + cc-switch 接 Deepseek 模型
  - 国产 Trae（目前免费）

**三、部署环境**
- **云服务器选项**：
  - 阿里云：免费领 300 元额度，建 2 核 4G 服务器（可用 1-2 个月）
  - 腾讯云：每日秒杀（上午 10 点、下午 3 点），低价抢 1 年服务器
  - 推荐用 Ubuntu（系统占用少，跑代码更好）
- **本地电脑**：完全可以运行
- 作者部署了 OpenClaw + 飞书机器人，自动更新数据、跑代码、发结果

**四、优化代码**
- 告诉 AI 运行环境，让它写操作文档或启动脚本
- 示例提示：
  - "我有一个 2 核 4G 轻量化服务器，硬盘 40G，安装了 OpenClaw..."
  - "我有一台笔记本电脑，内存 24G，硬盘 1T..."

**五、获取 API 代码**
- 登录中文论坛，右上角切换成中文
- 搜索"代码"，复制所有能搜到的代码
- 存成文档给 AI，让它提取可复用的代码逻辑（表达式生成、API 格式）

**六、持续优化**
- 问题：怎么获取运算符和表达式、怎么组合 Alpha、怎么判断价值、怎么处理回测信息
- 借助 AI 慢慢优化

**项目成果：**
- 自动回测了 160 多个 Alpha，用时 4 小时
- 初步跑通生成-回测-通知流程

**未来迭代计划（5 个 Agent）：**
1. 自动分析论文产出模版
2. 用模版生成表达式并评估
3. 批量回测并记录结果
4. 筛选和提交 Alpha
5. 数据维护和更新
- 用 OpenClaw 统一管理

**关键工具推荐：**
- Claude Code + cc-switch（接 Deepseek）
- Trae（国产免费）
- OpenClaw（自动化管理）
- 飞书机器人（消息通知）

### ✅ 新增学习内容 (2026-05-06)

#### 15. Combined Alpha Performance 计算原理

**定义：**
- 把所有地区已提交的 Alpha 和 Super Alpha 等权组合
- 计算 2023-2025 年（semi-OS）的费后表现

**三个关键词：**

**1. 分散（Diversity）：**
- 地区分散：不同地区市场环境、手续费、波动性不同
- 降低同一地区的 SC：多用不同类型的模板和数据类别
- 多地区、多模板、多数据类别、多中性化（尤其是风险中性化）

**2. 质量：**
- 质量比数量更重要
- 一个负的 OS Sharpe 需要 **2 个正的 OS Sharpe** 来弥补
- 关注 Alpha 的核心逻辑，使用 AI 和 MCP 验证

**3. 手续费：**
- 提交时看到的 Sharpe 是不计手续费的
- Margin 过低，扣除手续费后可能变负
- **亚洲市场（ASI）**：Margin 尽量保持 **15 以上，20 以上为佳**
- **其他地区**：Margin 建议 **10 以上**

**Super Alpha 注意事项：**
- IS Sharpe 高的 SA 不一定 OS 表现好
- 质量差的 RA 会让 SA 成为"双倍伤害"
- 过滤掉 IQC 表现差的 RA，剔除 product_correlation > 0 的 RA

#### 16. 顾问收入计算详解

**收入组成（四部分）：**

| 收入类型 | 说明 | 关键因素 |
|----------|------|----------|
| Base Payment | 日常津贴 | Value Factor, Theme |
| Quarterly Payment | 季度奖金 | Weight Factor, Value Factor |
| Competition | 比赛奖金 | 比赛名次 |
| Referral Bonus | 推荐奖金 | 200刀/人，上不封顶 |

**Base Payment：**
- Regular Alpha：每日 1-60 USD
- 计算逻辑：`Group_Rank(Score, value_factor)`
- 每日上限 4 个 Alpha
- **1.5USD 大法**：新人当日只提交 1 个 Alpha，Base Payment 在 1.5 以上说明质量不错

**影响 Base Payment 的因素：**
1. **Quantity Factor**：数量是入参，但不是乘数
2. **Quality Factor**：Theme 影响乘数，完成 Theme 内的 Alpha 有奖励加成
3. **Self Growth Factor**：自我成长比较

**Super Alpha Base Payment：**
- 解锁条件：提交满 100 个 Alpha
- 每日 1-60 USD，每日只可提交 1 个
- 符合条件人数少，能拿到的 payment 更多

**Quarterly Payment：**
- 符合条件：每季度有 20 天提交过 Alpha
- 奖金范围：100-25,000 USD
- 发放周期：每季度末发放上季度的季度奖
- 主要取决于 Alpha 在样本外的表现（OS）

**Genius Level 对应季度奖金：**
| Level | 季度奖金范围 |
|-------|--------------|
| 新人 → Expert | 200 - 2,000 USD |
| Master | 2,000 - 8,000 USD |

**税务代扣代缴：**
- 800 以内部分免税
- 800 以上部分 20%
- 每年四月进行汇算清缴

**薪资发放周期：**
- Base Payment：每两月发放一次
- Quarterly Payment：每季度发放一次
- 发薪月份：1月、3月、5月、6月、7月、9月、11月、12月

**关键建议：**
- 前三个月是顾问的"试用期"
- 提高Value Factor是新顾问前三个月的最主要目标
- 每天 1-2 个 Alpha 是建议的节奏
- 一个月 30-60 个 Alpha 可以有稳定的 Value Factor 表现

## 下一步
1. 尝试使用 Ravenpack News Dataset (nws18_bee, rp_nip_assets) 创建 News Alpha ✅ 已完成
2. 探索 Options 数据集的其他信号
3. 结合多种数据源创建组合 Alpha
4. 关注 Margin 指标，确保 ASI 达标（15+）

### ✅ 新增学习内容 (2026-05-06)

#### 17. Ravenpack News Dataset Alpha 测试结果

**数据集信息：**
- **数据集名称**: Ravenpack News Data (news18)
- **关键字段**:
  - `nws18_bee`: Earnings evaluation score (-1, 0, +1) - Vector 类型
  - `rp_css_earnings`: Composite sentiment score of earnings news - Matrix 类型
  - `rp_nip_revenue`: News impact projection of revenue news - Matrix 类型
- **覆盖率**: 50%
- **已有 Alpha 数量**: 497 (nws18_bee)

**测试的 Alpha 表达式及结果：**

| 表达式 | Sharpe | Turnover | Fitness | Returns | Margin | 结论 |
|--------|--------|----------|---------|---------|--------|------|
| `ts_backfill(winsorize(ts_decay_linear(scale(group_neutralize(vec_avg(nws18_bee), industry)), 10)), 60)` | 0.14 | 33.31% | 0.02 | 0.54% | 0.33‱ | 不推荐 |
| `group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry)` | 0.13 | 23.11% | 0.02 | 0.53% | 0.46‱ | 不推荐 |
| `ts_backfill(winsorize(ts_decay_linear(scale(group_neutralize(rp_css_earnings, industry)), 10)), 60)` | -0.15 | 29.63% | -0.02 | -0.66% | -0.45‱ | 不推荐 |
| `group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20))` | **0.61** | **16.49%** | 0.24 | **2.51%** | 3.05‱ | **有潜力** |
| `ts_rank(group_rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 10), industry) * rank(ts_mean(volume, 20)), 60)` | -0.07 | 27.05% | -0.01 | -0.18% | -0.13‱ | 不推荐 |
| `scale(group_neutralize(ts_zscore(ts_backfill(vec_avg(nws18_bee), 20), 60), industry)) * rank(ts_mean(volume, 20) / ts_mean(volume, 252))` | -0.47 | 68.10% | -0.07 | -1.50% | -0.44‱ | 不推荐（Turnover过高） |
| `rank(ts_decay_linear(ts_backfill(vec_avg(nws18_bee), 20), 20))` | 0.12 | **15.25%** | 0.02 | 0.51% | 0.67‱ | 不推荐（但2021年Sharpe=2.04） |

**关键发现：**

1. **单独使用 News 数据效果有限**：所有简单表达式 Sharpe < 1.25，Fitness < 1.0
2. **组合成交量信号有潜力**：`group_rank(...) * rank(ts_mean(volume, 20))` 表达式 Sharpe 达到 0.61
3. **Turnover 控制重要**：使用 `ts_decay_linear` 可有效降低换手率（15-30%）
4. **年度表现波动大**：2021年表现最好（Sharpe 2.04），2020年表现最差（Sharpe -1.56）
5. **Vector 类型字段需要 vec_avg()**：`nws18_bee` 是 Vector 类型，必须使用 `vec_avg()` 转换

**改进建议：**

1. **组合其他数据源**：将 News 数据与 Fundamental、Sentiment 数据组合
2. **使用更长的衰减窗口**：尝试 `ts_decay_linear(..., 30)` 或 `ts_decay_exp_window`
3. **添加条件交易**：使用 `trade_when()` 在特定条件下激活信号
4. **尝试其他 Ravenpack 字段**：`rp_nip_assets`（新闻影响预测）可能有更好效果
5. **调整 Settings**：尝试增加 Decay 参数（5-20）来进一步降低换手率

**下一步测试方向：**
- 使用 `rp_nip_revenue` 或 `rp_nip_assets` 字段
- 组合 Fundamental 数据（如 `est_eps`）
- 尝试 CHN 市场（散户多，反转效应强）

### ✅ 新增学习内容 (2026-05-06)

#### 18. 论坛精华：News Alpha 优化方案

**来源帖子：**
1. 【Alpha灵感】The Momentum of News (ML13205)
2. 【Alpha灵感】Brain Tips 新闻数据的 Alpha 优化 (ZM32460)

##### 论坛推荐的 News Alpha 表达式

**表达式 1：新闻动量策略**
```
a=ts_mean(scl12_sentiment,5);
b=normalize(group_rank(a,densify(subindustry)));
c_1=group_percentage(a,densify(subindustry),percentage=0.9);
c_2=group_percentage(a,densify(subindustry),percentage=0.1);
c_0=if_else(or(a<c_1,a>c_2),b,0);

trade_when(and(vec_avg(nws18_relevance)>0.1,adv20>1),c_0,-1)
```

**核心逻辑：**
1. 计算5日内新闻情绪得分 `ts_mean(scl12_sentiment,5)`
2. 按子行业排名并标准化
3. 筛选极端值（前10%和后10%）
4. 使用 `trade_when` 条件交易：新闻相关性 > 0.1 且成交量 > 1

**表达式 2：事件检测策略**
```
trade_when(news_tot_ticks, news_pct_5_min, -1)
```

**优化方法：**
- 使用 `ts_arg_min` 或 `ts_arg_max` 找到极值点
- 使用 `arc_tan` 使值更接近
- 延长 alpha 申请时间（5分钟太短）
- 尝试 **Risk Neutralization** 解决多空不平衡

##### 关键数据集字段

| 字段 | 描述 | 来源 |
|------|------|------|
| `scl12_sentiment` | 新闻情绪分数 | Sentiment Data |
| `nws18_relevance` | 新闻相关性 | Ravenpack News |
| `rp_css_assets` | 新闻复合情绪分数 | Ravenpack |
| `news_tot_ticks` | 新闻总tick数 | News Data |
| `news_pct_5_min` | 5分钟价格变化 | News Data |

##### 新闻数据处理三步骤

1. **事件检测**：确定新闻发生的日期（检查 NaN 和非 NaN 值）
2. **作业分配**：识别新闻事件后，仓位视为新闻对股价百分比变化的影响
3. **持仓管理**：剩余时间保持仓位

##### 常见问题与解决方案

| 问题 | 解决方案 |
|------|----------|
| 换手率过高 | 使用 `ts_decay_linear` 延长持仓时间 |
| 多空不平衡 | 尝试 Risk Neutralization 或 `group_neutralize` |
| 覆盖率低 | 使用 `ts_backfill` 填充缺失数据 |
| 信号衰减快 | 使用 `arc_tan` 或 `ts_rank` 平滑信号 |

##### 论坛建议的改进方向

1. **组合其他数据**：将 News 数据与 Fundamental、Sentiment 数据组合
2. **使用条件交易**：`trade_when(condition, alpha, exit_condition)`
3. **调整时间窗口**：尝试不同的回看期（5日、20日、60日）
4. **中性化处理**：使用 `group_neutralize` 或 Risk Neutralization
5. **筛选股票池**：关注小市值、低分析师覆盖率的股票（新闻效应更强）

##### 论坛论文推荐

**The Momentum of News**
- 作者：Ying Wang, Bohui Zhang, Xiaoneng Zhu
- 年份：2018
- 链接：https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3267337
- 核心发现：新闻动量现象由公司基本面持续性驱动，年化风险调整回报率 7.45%
