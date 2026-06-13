---
title: 分类评估指标
category: concepts
tags: [AI, 评估, 混淆矩阵, 准确率, 精确率, 召回率, F1]
aliases: [混淆矩阵, accuracy precision recall, 准确率精确率召回率]
summary: 分类评估指标的核心：混淆矩阵导出准确率/精确率/召回率/F1——类别不平衡时准确率失效，精确率防错报、召回率防漏报、F1兼顾两者
source_dir: AI 人工智能/Agent架构/评估系统
source_files: [如何理解准确率、精确率和召回率.md, RAG评测完整指南：指标、测试和最佳实践.md, RAG效果差？7个指标让你的准确率大幅提升.md]
provenance:
  extracted: 0.85
  inferred: 0.12
  ambiguous: 0.03
base_confidence: 0.65
lifecycle: draft
lifecycle_changed: 2026-06-11
tier: supporting
created: 2026-06-11
updated: 2026-06-13
relationships:
  - target: "[[concepts/rag-engineering]]"
    type: related_to
  - target: "[[concepts/llm-observability]]"
    type: related_to
---

# 分类评估指标

分类问题的评估从**混淆矩阵**出发，导出准确率、精确率、召回率和F1 Score四个核心指标。类别不平衡时准确率失效——需要精确率和召回率来衡量正例识别质量。

## 混淆矩阵

|  | 实际正例 | 实际反例 | 合计 |
|--|---------|---------|------|
| **预测正例** | TP(真阳性) | FP(假阳性) | P |
| **预测反例** | FN(假阴性) | TN(真阴性) | N |
| **合计** | T | F | P+N |

## 四个核心指标

| 指标 | 公式 | 直觉 | 关心什么 |
|------|------|------|----------|
| **准确率(Accuracy)** | (TP+TN)/(TP+FN+FP+TN) | 正确预测占总样本比例 | 所有分类都正确吗？ |
| **精确率(Precision)** | TP/(TP+FP) | 预测正例中真正是正例的比例 | 预测有多"准"？ |
| **召回率(Recall)** | TP/(TP+FN) | 实际正例中被识别出来的比例 | 正例有多"全"？ |
| **F1 Score** | 2×P×R/(P+R) | 精确率与召回率的调和平均 | 同时控风险和成本 |

## 类别不平衡：准确率失效

罕见病发病率仅1%时，算法一直预测"不发病"也能达到99%准确率——但完全没有识别出正例。此时准确率不反映模型对正例的识别能力，必须用精确率和召回率。

## 精确率 vs 召回率的应用取舍

- **提升精确率 = 防错报(FP)**：司法审判（宁可漏判不可错判）、人脸识别支付（错报=别人替你付）。**错报后果严重、成本高 → 提精确率**
- **提升召回率 = 防漏报(FN)**：罕见病筛查（宁可多检不可漏检）、安全隐患排查。**漏报后果严重、风险大 → 提召回率**
- **F1 Score兼顾两者**：当既不能错报也不能漏报时，用F1调和平均平衡

## 与RAG评估的连接

[[concepts/rag-engineering]] 的评估层使用了这些指标的变体：
- 检索层：Recall@K（召回率的Top-K版本）、nDCG@K（考虑排序质量的扩展）
- 生成层（RAGAS）：Context Precision（召回文档中真正被用到的比例）对应精确率思想，Context Recall（参考答案涉及的事实是否被召回）对应召回率思想 ^[inferred]

[[concepts/llm-observability]] 的语义质量维度同样需要精确率/召回率来判断LLM输出是否准确、是否遗漏关键信息 ^[inferred]。

## LLM评测基准的连接

[[concepts/llm-benchmarks]] 按六大能力维度组织评测数据集（知识理解/推理/对话/抽取/安全/编程），本页的底层指标体系是评测基准的**计算基础** ^[inferred]。

[[entities/ragas-framework]] 的四个核心指标是精确率/召回率思想在RAG领域的具体实现：Context Precision=检索精确率、Context Recall=检索召回率、Faithfulness=生成精确率（防幻觉）、Answer Relevancy=生成召回率（防偏题） ^[inferred]。

## RAG检索排序指标

RAG检索层的7个核心排序指标（来自"RAG效果差？7个指标让你的准确率大幅提升"）：

| 指标 | 公式/定义 | 含义 | 类别 |
|------|-----------|------|------|
| **Precision@K** | 前K个结果中相关文档数/K | 检索前K个有多准 | 预测指标 |
| **Recall@K** | 前K个结果中相关文档数/所有相关文档数 | 相关文档被检索到多少 | 预测指标 |
| **F-score@K** | P@K和R@K的调和平均 | 兼顾准确和全面 | 预测指标 |
| **MRR** | 第一个相关文档排名倒数的平均值 | 第一个正确答案排多前 | 排序指标 |
| **MAP** | 各query的AP平均值 | 所有位置的平均精确率 | 排序指标 |
| **Hit Rate** | 至少1个相关文档出现在Top-K的比例 | 能否找到任何相关 | 预测指标 |
| **nDCG@K** | 归一化折扣累积增益 | 高相关排前面得高分 | 排序指标 |

**预测指标vs排序指标**：Precision@K只关心"前K有没有"，不关心顺序；nDCG/MRR关心"正确的排多前面"。生产上两者都要看 ^[inferred]。

### RAG评测完整指南补充要点

来自"RAG评测完整指南"的分层评估体系：

- **检索评估**：ground truth标注+人工/LLM-as-judge判定相关性
- **生成评估**：基于参考(reference-based)和无参考(reference-free)两种模式
- **合成测试数据**：LLM自动生成测试集（详见 [[entities/ragas-framework]]）
- **鲁棒性测试**：对抗性输入、噪声数据、边界case
- **对话级评估**：多轮对话的一致性和上下文连贯性

## 来源

- 如何理解准确率、精确率和召回率（raw/sources/AI 人工智能/Agent架构/评估系统/）
- RAG评测完整指南：指标、测试和最佳实践（raw/sources/AI 人工智能/Agent架构/评估系统/）
- RAG效果差？7个指标让你的准确率大幅提升（raw/sources/AI 人工智能/Agent架构/评估系统/）