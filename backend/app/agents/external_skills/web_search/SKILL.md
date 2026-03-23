---
name: web-search
description: 网络搜索Skill，用于在互联网上搜索信息以补充回答
license: MIT
compatibility: 需要互联网访问
metadata:
  author: nl2mql2sql
  version: "1.0"
allowed-tools: search_web
---

# Web Search

## 概述

此Skill用于在互联网上搜索相关信息，以补充回答用户的问题。

## 指令

### 1. 确定搜索需求
- 分析用户问题
- 识别需要补充的信息
- 构建合适的搜索关键词

### 2. 执行搜索
- 使用 search_web 工具
- 传入搜索关键词
- 获取搜索结果

### 3. 分析结果
- 评估搜索结果的相关性
- 提取关键信息
- 综合多个来源的信息

### 4. 集成到回答中
- 将搜索结果与已有知识结合
- 提供来源引用
- 说明信息的时效性

## 注意事项

- 网络搜索结果可能不准确，需要交叉验证
- 优先使用可靠来源的信息
- 说明信息获取时间和可能的局限性
