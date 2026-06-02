---
title: PagedAttention与Continuous Batching
category: concepts
tags: [AI, LLM, 推理, PagedAttention, vLLM]
summary: vLLM的核心设计：用操作系统式内存管理解决KV缓存碎片问题，用请求级动态调度解决静态batch浪费问题
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】12：PagedAttention 与 Continuous Batching.md]
provenance:
  extracted: 0.70
  inferred: 0.25
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-02
relationships:
  - target: "[[concepts/llm-inference-engine]]"
    type: implements
  - target: "[[entities/vllm-sglang-tensorrt]]"
    type: uses
  - target: "[[concepts/llm-infra-landscape]]"
    type: derived_from
---

# PagedAttention与Continuous Batching

vLLM的两个核心设计解决了推理引擎最致命的两个问题：**显存碎片**和**静态batch浪费**。

## PagedAttention：操作系统式的KV缓存管理

### 传统问题
- KV缓存预分配最大长度（如2048 tokens）的连续显存 → 严重浪费
- 实际请求可能只用100 tokens，但占了2048的空间
- 显存碎片化：短请求释放的空间无法拼成大块供新请求使用

### PagedAttention解决方案
- 将KV缓存按**页（Block）**管理，类似OS的虚拟内存页
- 每页固定大小（如16 tokens的KV数据）
- 逻辑上连续，物理上分散——页表映射逻辑block到物理block
- **Block Manager**：负责分配、释放、重用物理block

### 与OS虚拟内存的类比
| OS概念 | PagedAttention对应 |
|--------|-------------------|
| 虚拟地址空间 | 逻辑KV block序列 |
| 物理页 | 物理GPU显存block |
| 页表 | Block table（逻辑→物理映射） |
| 页面分配/释放 | Block分配/释放 |
| 页面置换 | Swap to CPU内存（可选） |

PagedAttention的核心收益：**将KV缓存的显存利用率从60%提升到接近100%**。 ^[inferred]

## Continuous Batching：请求级动态调度

### 传统问题（Static Batching）
- N个请求一起送入，等所有请求完成才释放batch slot
- 短请求被迫等待长请求 → GPU资源浪费
- 等凑batch的时间也浪费 → 延迟增加

### Continuous Batching解决方案
- 每个iteration开始时，完成的请求立即退出batch
- 空出的slot立即填充新请求
- **迭代级调度**：而非请求级调度

### 核心算法
```
while 有请求排队 or batch不为空:
    1. 执行一个iteration（prefill或decode）
    2. 检查哪些请求已生成EOS → 移除
    3. 从等待队列取新请求 → 填充空slot
    4. 更新block table（PagedAttention配合）
```

Continuous Batching的吞吐提升2-4倍不是来自"更快计算"，而是来自"更少浪费"。 ^[inferred]

## Chunked Prefill

- 长prompt不再一次性处理——分块处理
- 与decode请求混合调度：Prefill chunk和decode token在同一iteration执行
- 减少Prefill独占GPU的时间窗口，decode请求不必等待长prefill完成

## 工程要点

- **KV cache sharing**：同一prompt的不同请求可共享前缀的KV blocks（如system prompt） ^[inferred]
- **Prefix caching**：高频共享前缀（system prompt）的KV缓存可预计算并缓存 ^[inferred]
- **Swap机制**：GPU显存不足时可swap KV blocks到CPU内存，代价是decode时需要swap回来 ^[inferred]

## 来源

- 大模型基础设施工程系列12：PagedAttention与Continuous Batching（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）