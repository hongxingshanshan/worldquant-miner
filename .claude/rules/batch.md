---
paths:
  - "**/*.bat"
---

# Batch 文件规则

## 编码要求
- 必须使用 CRLF 行尾（Windows 格式）
- 编码为 GBK
- 避免使用 Unicode 特殊字符

## 修改前必须读取
在编辑任何 .bat 文件之前，必须先使用 Read 工具读取该文件。

## 语法规则
- 使用 `@echo off` 开头
- 标签使用小写，如 `:naive_ollama`
- 跳转使用 `goto` 语句
