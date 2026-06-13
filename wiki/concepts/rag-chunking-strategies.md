---
title: RAG分块策略
category: concepts
tags: [AI, RAG, Chunking, 分块, 文本分割]
summary: 21种文本分块策略从基础到前沿：分块是决定RAG系统性能的关键因素——不当的分块直接影响检索质量和生成效果
source_dir: AI 人工智能/Agent架构/RAG/传统RAG
source_files: [RAG Chunk分块策略.md, RAG Chunk分块策略：主流方法（递归、jina-seg）+ 前沿推荐（Meta-chunking、Late chunking、SLM-SFT）.md, RAG Chunk分块策略-图解.md, RAG Chunk分块策略-代码示例.md]
provenance:
  extracted: 0.70
  inferred: 0.25
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-13
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

## 图解：11种策略对比

来自 RAG Chunk分块策略-图解 的11种策略分类：

| 类别 | 方法 | 优势 | 不足 |
|------|------|------|------|
| 基础 | 固定长度 | 简单 | 不保语义 |
| 基础 | 句子 | 保句子边界 | 跨句语义丢失 |
| 基础 | 段落 | 保段落完整 | 段落太长时噪声 |
| 基础 | 滑动窗口 | overlap保上下文 | 存储/计算冗余 |
| 语义 | 语义分割 | 保语义完整 | 计算成本高 |
| 结构 | 递归字符 | 多级分隔 | LangChain默认 |
| 结构 | 上下文增强 | 加前后文 | 存储膨胀 |
| 混合 | 模态特定 | 不同类型不同策略 | 需文档类型识别 |
| 混合 | 代理分块 | Agent决策 | LLM调用成本 |
| 混合 | 子文档 | 层级结构 | 父子关系管理 |
| 混合 | 混合策略 | 综合 | 实现复杂 |

**选型建议**：80%场景用递归字符分割（LangChain默认），剩余20%按文档类型选结构或语义方法 ^[inferred]。

## 代码实现要点

RAG Chunk分块策略-代码示例提供了21种方法的Python实现，核心亮点：

- **HybridChunker类**：组合多种策略的统一接口，先按结构切再按语义精切
- **表格感知分块**：识别表格为原子Element，不切分
- **层次化分块**：父子chunk关系（父chunk存全文摘要，子chunk存细节）
- **模态感知**：图片/代码/表格/文本分别处理

## 工程要点

- **Chunking是数据工程而非算法工程**：选择正确的分块策略比调检索参数更重要 ^[inferred]
- **评测驱动**：用RAGAS等框架量化不同分块策略的检索质量差异 ^[inferred]
- **混合策略**：不同类型文档用不同策略（代码→代码分割、论文→语义分割） ^[inferred]

## 来源

- RAG Chunk分块策略（raw/sources/AI 人工智能/Agent架构/RAG/传统RAG/）
- RAG Chunk分块策略：主流方法+前沿推荐（raw/sources/AI 人工智能/Agent架构/RAG/传统RAG/）
- RAG Chunk分块策略-图解（raw/sources/AI 人工智能/Agent架构/RAG/传统RAG/）
- RAG Chunk分块策略-代码示例（raw/sources/AI 人工智能/Agent架构/RAG/传统RAG/）