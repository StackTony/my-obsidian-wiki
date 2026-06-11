---
title: LangChain框架
category: entities
tags: [AI, LangChain, LCEL, 框架]
summary: LangChain是LLM应用开发框架，核心抽象Runnable+LCEL将全部组件统一为可执行单元，支持链式组合、批处理和流式输出
source_dir: AI 人工智能/Agent架构/LangChain
source_files: [2-LangChain 架构.md, 1-LangChain 核心术语速查表.md, LangChain 解决的核心问题.md]
provenance:
  extracted: 0.60
  inferred: 0.35
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-11
relationships:
  - target: "[[concepts/agent-framework-engineering]]"
    type: implements
  - target: "[[entities/langgraph-framework]]"
    type: extends
  - target: "[[concepts/rag-engineering]]"
    type: uses
---

# LangChain框架

LangChain不仅是抽象LLM API的SDK，而是支持运行时模块组合与执行流程组织的框架。它将LLM应用开发从"拼凑API调用"提升到"声明式编排"。

## 包结构分离

2024年后期完全分离为六个包：
| 包 | 职责 | 特性 |
|----|------|------|
| `langchain-core` | 核心抽象、Runnable协议、LCEL | 稳定、极少变更 |
| `langchain` | 高级组合、Chain、Agent、算法 | 中等变更频率 |
| `langchain-community` | 第三方集成 | 高频变更、易拆分 |
| `langgraph` | [[entities/langgraph-framework|LangGraph]]图驱动工作流编排 | 新增、独立发展 |
| `langserve` | 应用部署 | 将Chain部署为REST API |
| `langsmith` | 可观测与评测 | 追踪、评测、调试 |

## Runnable协议与LCEL

### Runnable：一切皆可执行单元
```python
class Runnable(ABC, Generic[Input, Output]):
    def invoke(self, input: Input) -> Output     # 单次执行
    def batch(self, inputs: List[Input]) -> List[Output]  # 批量
    def stream(self, input: Input) -> Iterator[Output]    # 流式
```

所有组件（PromptTemplate、LLM、Retriever、Tool、Parser）都实现Runnable接口。

### LCEL：声明式编排
- 用 `|` 运算符将Runnable组合成链式管道
- 运算符重载 `__or__()` → RunnableSequence
- 支持RunnableParallel（并行）、RunnableBranch（条件分支）

```python
chain = prompt | llm | output_parser
result = chain.invoke({"question": "什么是RAG?"})
```

## 核心模块

| 模块 | 职责 | 关键类 |
|------|------|--------|
| **Model I/O** | LLM/ChatModel调用 | BaseLanguageModel、ChatOpenAI |
| **Prompt/Memory** | 模板系统+上下文注入 | PromptTemplate、ConversationBufferMemory |
| **Chains** | 多步组合 | LLMChain、SequentialChain |
| **Agents** | 自主决策循环 | ReActAgent、ToolCallingAgent |
| **Retriever & VectorStore** | RAG检索 | VectorStoreRetriever、FAISS |
| **LangGraph** | 工作流编排 | StateGraph、Node、Edge |

## 设计模式

- **抽象层**：Runnable协议统一所有组件
- **工厂方法**：不同LLM通过统一接口创建
- **组合模式**：Runnable可嵌套组合
- **策略模式**：不同检索/重排/输出策略可替换

## 来源

- 2-LangChain 架构（raw/sources/AI 人工智能/Agent架构/LangChain/）
- 1-LangChain 核心术语速查表（raw/sources/AI 人工智能/Agent架构/LangChain/）
- LangChain 解决的核心问题（raw/sources/AI 人工智能/Agent架构/LangChain/）