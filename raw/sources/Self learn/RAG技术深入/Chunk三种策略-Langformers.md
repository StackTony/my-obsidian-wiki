---
title: Fixed-size, Semantic and Recursive Chunking Strategies for LLMs
source_url: https://blog.langformers.com/llm-chunking-strategies/
source_site: Langformers Blog
author: Rabindra Lamsal
date_extracted: 2026-05-16
credibility: low
tags: [RAG, Chunk策略, Langformers, 固定大小, 语义分块]
---

# Fixed-size, Semantic and Recursive Chunking Strategies for LLMs

## What is Chunking?

**Chunking** is the process of splitting a large document into smaller units called *chunks*. Each chunk is small enough to fit within the token limits of the chosen embedding model, yet sufficient enough to retain meaningful information.

The ultimate goal of chunking is to improve:
- **Retrieval accuracy** — relevant chunks are retrieved instead of entire documents
- **Processing efficiency** — smaller inputs lead to faster model inference

## Chunking Strategies in Langformers

### 1. Fixed-size Chunking

Divides text based purely on token count. Optional overlapping between chunks for better context preservation.

```python
from langformers import tasks

chunker = tasks.create_chunker(strategy="fixed_size", tokenizer="sentence-transformers/all-mpnet-base-v2")

chunks = chunker.chunk(
    document="This is a test document. It contains several sentences.",
    chunk_size=8
)
```

### 2. Semantic Chunking

Consider the *meaning* of the content. It first creates small initial chunks, then merges them based on semantic similarity.

**How Semantic Chunking Works:**
1. Initially, the document is split into small chunks based on a token limit
2. The chunks are then grouped together based on their semantic similarity, controlled by a similarity threshold

```python
from langformers import tasks

chunker = tasks.create_chunker(strategy="semantic", model_name="sentence-transformers/all-mpnet-base-v2")

chunks = chunker.chunk(
    document="Cats are awesome. Dogs are awesome. Python is amazing.",
    initial_chunk_size=4,
    max_chunk_size=10,
    similarity_threshold=0.3
)
```

In this example:
- The document is initially split into very small chunks (4 tokens)
- Similar chunks are merged until a maximum size of 10 tokens is reached
- Only chunks with similarity greater than 0.3 are grouped together

### 3. Recursive Chunking

The document is split hierarchically based on the provided separators.

Generally, a document can be first divided by sections, then by paragraphs, and further down at token level. Langformers adopts this strategy by first splitting text at double newlines (`\n\n`) to identify sections, then at single newlines (`\n`) for paragraphs.

```python
from langformers import tasks

chunker = tasks.create_chunker(strategy="recursive", tokenizer="sentence-transformers/all-mpnet-base-v2")

chunks = chunker.chunk(
    document="Cats are awesome.\n\nDogs are awesome.\nPython is amazing.",
    separators=["\n\n", "\n"],
    chunk_size=5
)
```

---

*来源：Langformers Blog | 作者：Rabindra Lamsal | 提取日期：2026-05-16*
