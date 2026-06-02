---
title: RLHF与对齐流水线
category: concepts
tags: [AI, LLM, RLHF, DPO, 对齐, PPO]
summary: 对齐是在数据、奖励、采样和训练稳定性之间做工程取舍——SFT+奖励模型+PPO/DPO/GRPO串成完整对齐流水线
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】09：RLHF 与对齐流水线.md]
provenance:
  extracted: 0.60
  inferred: 0.35
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
relationships:
  - target: "[[concepts/llm-training-pipeline]]"
    type: extends
---

# RLHF与对齐流水线

对齐（Alignment）让模型从"能生成文本"升级为"生成安全、有用、可控的回答"。但对齐不是一次训练，而是数据、奖励、采样和训练稳定性之间的工程取舍。

## 对齐流水线

```
SFT模型 → 奖励模型训练 → PPO/DPO/GRPO → 评估 → 发布
```

## 奖励模型（Reward Model）

- 从SFT模型初始化，去掉最后一层语言模型头，换成奖励值输出头
- 训练数据：人类偏好对比（同一个问题，两个回答，标注哪个更好）
- 损失函数：Bradley-Terry偏好排序模型
- 工程要点：奖励模型的质量直接决定PPO的效果 ^[inferred]

## PPO（Proximal Policy Optimization）

- 从SFT模型初始化Policy（待对齐模型）和Reference（SFT模型副本）
- Policy生成回答 → Reward Model评分 → PPO更新Policy
- KL散度惩罚：防止Policy偏离Reference太远（奖励黑客问题）
- 工程难点：
  - 四个模型同时运行（Policy+Reference+Reward+Value）→ 显存大
  - 训练稳定性差 → 需要careful超参调优
  - Reward hacking → Policy可能找到奖励模型漏洞 ^[inferred]

## DPO（Direct Preference Optimization）

- 不需要奖励模型！直接从偏好数据训练
- 损失函数：将偏好对比转化为Policy与Reference的log概率差
- 优势：无奖励模型→省显存、更稳定、训练更简单
- 劣势：缺乏奖励模型的细粒度信号 ^[inferred]

## GRPO（Group Relative Policy Optimization）

- DeepSeek-R1提出的变体
- 同一个问题生成多个回答，组内相对排名代替绝对奖励值
- 不需要Value Model → 三模型变两模型
- 更适合大规模训练 ^[inferred]

## 对齐方法对比

| 方法 | 需要奖励模型 | 需要Value Model | 训练稳定性 | 显存需求 | 适用场景 |
|------|------------|----------------|-----------|----------|----------|
| PPO | ✅ | ✅ | 低 | 高（4模型） | 有明确奖励信号 |
| DPO | ❌ | ❌ | 高 | 低（2模型） | 有偏好对比数据 |
| GRPO | ❌ | ❌ | 中 | 中（2模型） | 大规模对齐 |

## 来源

- 大模型基础设施工程系列09：RLHF与对齐流水线（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）