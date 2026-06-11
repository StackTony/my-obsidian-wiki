---
title: RAG分块策略
category: concepts
tags: [AI, RAG, Chunking, 分块, 文本分割]
summary: 21种文本分块策略从基础到前沿：分块是决定RAG系统性能的关键因素——不当的分块直接影响检索质量和生成效果
source_dir: AI 人工智能/Agent架构/RAG
source_files: [RAG Chunk分块策略.md, RAG Chunk分块策略：主流方法（递归、jina-seg）+ 前沿推荐（Meta-chunking、Late chunking、SLM-SFT）.md]
provenance:
  extracted: 0.70
  inferred: 0.25
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
relationships:
  - target: "[[concepts/rag-engineering]]"
    type: uses
---

# RAG分块策略

分块（Chunking）是RAG系统中最容易被忽视但影响最大的环节。不当的分块会让检索结果丢失上下文或包含噪声，直接影响生成效果。

## 基础分块方法

| 方法 | 描述 | 适用场景 |
|------|------|----------|
| **换行符分割** | 按换行符简单分割 | FAQ文档、笔记、聊天记录 |
| **固定大小分块** | 按预设字符数分割，不考虑语义边界 | OCR输出、无结构标记的文本 |
| **滑动窗口** | 固定大小+重叠区域维持上下文 | 学术论文、叙述性报告 |

## 结构感知分块

| 方法 | 描述 | 适用场景 |
|------|------|----------|
| **递归字符分割** | 依次尝试多种分隔符（段落→句子→字符） | 最常用的通用方法（LangChain默认） |
| **Markdown分割** | 按标题层级（#→##→###）分割 | Markdown文档、技术文档 |
| **代码分割** | 按函数/类定义分割 | 代码仓库、API文档 |
| **HTML分割** | 按DOM结构分割 | 网页抓取内容 |

## 语义驱动分块（前沿方法）

| 方法 | 描述 | 特点 |
|------|------|------|
| **语义分割** | 用Embedding相似度决定分割点 | 保持语义完整性但计算成本高 |
| **Meta-chunking** | 先粗切再按语义精切 | 两阶段策略，平衡粒度和语义 ^[inferred] |
| **Late chunking** | 先Embedding整文档再切分 | 避免切断语义边界，但需要长上下文Embedding模型 ^[inferred] |
| **SLM-SFT** | 小模型微调后专门做分块决策 | 专用分块模型，成本可控但需训练数据 ^[inferred] |
| **jina-seg** | Jina AI的语义分割API | 商业方案，无需自建 |

## 分块参数权衡

| 参数 | 影响 |
|------|------|
| **Chunk大小** | 太小→上下文不足；太大→噪声多+检索慢 |
| **Overlap** | 增加重叠→减少信息丢失但增加存储和重复检索 |
| **Separator选择** | 错误分隔符→切断语义完整单元 |

经验值：Chunk 500-1000 tokens、Overlap 50-100 tokens是大多数场景的起点。 ^[inferred]

## 工程要点

- **Chunking是数据工程而非算法工程**：选择正确的分块策略比调检索参数更重要 ^[inferred]
- **评测驱动**：用RAGAS等框架量化不同分块策略的检索质量差异 ^[inferred]
- **混合策略**：不同类型文档用不同策略（代码→代码分割、论文→语义分割） ^[inferred]

## 来源

- RAG Chunk分块策略（raw/sources/AI 人工智能/Agent架构/RAG/）
- RAG Chunk分块策略：主流方法+前沿推荐（raw/sources/AI 人工智能/Agent架构/RAG/）