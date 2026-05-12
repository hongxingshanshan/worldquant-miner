# WorldQuant Brain 知识库

本目录包含 WorldQuant Brain Alpha 挖掘项目所需的全部知识库文件。

## 文件列表

### 核心知识库

| 文件 | 描述 | 大小 |
|------|------|------|
| `worldquantbrain_alpha_guide.md` | Alpha 生成最佳实践、常见模式、技巧 | 1.6 KB |
| `worldquantbrain_alpha_templates.md` | Alpha 表达式模板和示例 | 1.4 KB |
| `worldquantbrain_datasets_reference.md` | 数据集分类和常用字段 | 0.8 KB |
| `worldquant_community_knowledge.md` | 社区论坛精华知识 | 6.2 KB |

### 数据字段参考

| 文件 | 描述 | 大小 |
|------|------|------|
| `worldquant_data_fields.json` | 完整数据字段（5,905 个字段，16 个数据集） | 3.7 MB |
| `worldquant_data_fields_reference.md` | 数据字段 Markdown 参考文档 | 674 KB |

## 数据集统计

| 数据集 | 字段数 |
|--------|--------|
| Analysts' Factor Model (model77) | 3,241 |
| Company Fundamental Data (fundamental6) | 886 |
| Analyst Estimate Data (analyst4) | 653 |
| US News Data (news12) | 322 |
| Report Footnotes (fundamental2) | 318 |
| Research Sentiment Data (sentiment1) | 17 |
| Social Media Data (socialmedia8) | 2 |
| 其他数据集 | 466 |
| **总计** | **5,905** |

## 使用方式

知识库文件由 `alpha_generator_ollama.py` 自动加载：

```python
# 加载通用知识库
knowledge_base = load_knowledge_base()

# 加载高覆盖率数据字段
data_fields_ref = load_data_fields_reference(max_fields=80)
```

## 更新记录

- **2026-05-09**: 采集全部 5,905 个数据字段
- **2026-05-09**: 采集社区论坛 BRAIN TIPS 知识
- **2026-05-09**: 整合知识库到统一目录
