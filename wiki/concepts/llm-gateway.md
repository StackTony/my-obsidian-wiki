---
title: 大模型网关
category: concepts
tags: [AI, LLM, 网关, LiteLLM, 路由, 成本]
summary: 大模型网关将模型调用统一成可治理入口——多供应商路由、配额、计费、语义缓存、Guardrails和可观测的基础设施价值
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】22：大模型网关.md]
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
  - target: "[[concepts/llm-serving-infrastructure]]"
    type: extends
  - target: "[[concepts/llm-observability]]"
    type: related_to
---

# 大模型网关

企业接入多个模型供应商后，模型调用变成可治理的生产流量——网关、配额、计费、缓存和安全都需要统一管理。

## 大模型网关的核心功能

| 功能 | 描述 |
|------|------|
| **统一API入口** | OpenAI兼容API格式，屏蔽不同供应商差异 |
| **多供应商路由** | 按成本/延迟/能力自动路由到最优模型 |
| **配额管理** | 多租户请求速率限制、token配额 |
| **计费与账单** | 按token/请求计费，成本归属到业务线 |
| **语义缓存** | 相似请求直接返回缓存结果，减少模型调用 |
| **Guardrails** | 输入输出安全检查（PII脱敏、越狱检测、内容过滤） |
| **可观测** | 请求日志、token消耗、延迟追踪 |
| **模型版本管理** | 多版本共存、渐进发布、回滚 |

## 代表方案

### LiteLLM
- 开源LLM网关，100+供应商API统一接口
- 自动路由：按成本/延迟选择最优模型
- 配额管理：基于Redis的速率限制
- 语义缓存：GPTCache集成
- 适合：中小规模、快速接入多供应商

### OneAPI
- 中国社区开发的LLM网关
- 支持国内供应商（百度、阿里、腾讯、字节）
- 渠道管理：多供应商负载均衡
- 适合：中国本土化需求

## 模型路由策略

| 策略 | 描述 | 适用 |
|------|------|------|
| **成本优先** | 选择最便宜的模型 | 批量处理、非关键场景 |
| **延迟优先** | 选择最快的模型 | 实时对话、用户交互 |
| **能力优先** | 按任务复杂度选模型 | 简单→小模型、复杂→大模型 |
| **Fallback** | 主模型失败→备用模型 | 容灾、供应商故障 |

## 来源

- 大模型基础设施工程系列22：大模型网关（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）