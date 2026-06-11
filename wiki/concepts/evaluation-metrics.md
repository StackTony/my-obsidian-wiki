---
title: 分类评估指标
category: concepts
tags: [AI, 评估, 混淆矩阵, 准确率, 精确率, 召回率, F1]
aliases: [混淆矩阵, accuracy precision recall, 准确率精确率召回率]
summary: 分类评估指标的核心：混淆矩阵导出准确率/精确率/召回率/F1——类别不平衡时准确率失效，精确率防错报、召回率防漏报、F1兼顾两者
source_dir: AI 人工智能/Agent架构/评估系统
source_files: [如何理解准确率、精确率和召回率.md]
provenance:
  extracted: 0.85
  inferred: 0.12
  ambiguous: 0.03
base_confidence: 0.65
lifecycle: draft
lifecycle_changed: 2026-06-11
tier: supporting
created: 2026-06-11
updated: 2026-06-11
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

## 来源

- 如何理解准确率、精确率和召回率（raw/sources/AI 人工智能/Agent架构/评估系统/）