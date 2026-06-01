---
title: "Chunking Strategies for RAG: Semantic vs Fixed-Size vs Recursive"
source_url: https://www.buildmvpfast.com/blog/chunking-strategies-rag-semantic-fixed-size-recursive-2026
source_site: BuildMVPFast
author: BuildMVPFast Team
date_extracted: 2026-05-16
credibility: low
tags: [RAG, Chunk策略, 语义分块, 递归分块, Greg Kamradt]
---

# Chunking Strategies for RAG: Semantic vs Fixed-Size vs Recursive

## The five levels of text splitting

Greg Kamradt's framework for thinking about chunking has become the standard reference.

**Level 1: Character splitting.** You pick a number, say 500 characters, and chop the text every 500 characters. No awareness of words, sentences, or meaning. This is the baseline.

**Level 2: Recursive character splitting.** LangChain's `RecursiveCharacterTextSplitter` tries separators in order: double newlines, single newlines, spaces, then individual characters. It respects paragraph boundaries first, then sentences, then words. This is LangChain's recommended default, and honestly, it's good enough for most production systems.

**Level 3: Document-structure splitting.** Respects markdown headers, HTML tags, code blocks, LaTeX sections. If your documents have structure, use it.

**Level 4: Semantic chunking.** Uses embedding similarity to detect topic shifts between consecutive sentences. When the cosine distance between sentence N and sentence N+1 crosses a threshold, you split there. Variable-size chunks that each cover one coherent topic.

**Level 5: Agentic chunking.** An LLM reads the text and decides: "Does this sentence belong to the current chunk, or should I start a new one?" Highest quality. Also the slowest and most expensive.

## Fixed-size chunking: the boring default that actually works

NVIDIA tested chunk sizes of 128, 256, 512, 1024, and 2048 tokens with 15% overlap across multiple datasets:

| Dataset | Best Chunk Size | Score |
|---------|-----------------|-------|
| KG-RAG | 1024 tokens | 0.804 |
| FinanceBench | 1024 tokens | 0.579 |
| Earnings | 512 tokens | 0.681 |
| SQuAD (entity answers) | 64 tokens | 64.1% recall@1 |
| TechQA (technical answers) | 512 tokens | 61.3% recall@1 |

**When fixed-size works great:**
- Uniform document lengths
- Simple retrieval needs
- Speed is priority

**When it falls apart:**
- Mixed document types (patents vs chat logs)
- Cross-boundary context critical

## Recursive splitting: the real workhorse

The algorithm: define separators in priority order:
- `"\n\n"` (paragraphs)
- `"\n"` (lines)
- `" "` (words)
- `""` (characters)

It tries to split on double newlines first. If a resulting chunk is still too big, it splits that chunk on single newlines. Still too big? Spaces. The output respects document structure without needing embeddings.

**Chonkie benchmarks on 100K Wikipedia articles (A100 GPU):**
- Token chunking: 58s (4.82 MB/s)
- Recursive chunking: 1m19s (3.54 MB/s)
- Semantic chunking: 14min (0.33 MB/s) - **10x slower**

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " ", ""]
)
chunks = splitter.split_text(document)
```

## Semantic chunking: when meaning actually matters

The algorithm (Greg Kamradt):
1. Split document into sentences
2. Embed each sentence
3. Group sentences by embedding similarity (threshold ~0.7 cosine distance)
4. Merge similar consecutive sentences into chunks

**The speed problem:** 14x slower than recursive
**The threshold problem:** 0.7 threshold is arbitrary, model-dependent
**The variable-size problem:** Some chunks 50 tokens, others 2000

**When semantic chunking is genuinely worth it:**
- Legal contracts with clear section boundaries
- Earnings calls with distinct topic transitions
- Research papers with method/result/discussion structure

## Late chunking: Jina AI's clever inversion

Late chunking flips the pipeline: embed first, chunk second.

**The problem it solves:**
- Chunk 2 says "Its population is 3.6 million"
- Traditional embedding has no idea what "Its" refers to
- Late chunking: entire document contextualized before splitting

**Benchmarks (Jina AI, BeIR datasets, nDCG@10):**

| Dataset | Avg Doc Length | Naive Chunking | Late Chunking |
|---------|----------------|----------------|---------------|
| SciFact | 1498 chars | 64.20% | 66.10% |
| NFCorpus | 1590 chars | 23.46% | 29.98% (+6.5) |
| Quora | 62 chars | 87.19% | 87.19% (no change) |

**Pattern:** Longer documents benefit more. Short documents show zero improvement.

## Contextual retrieval: Anthropic's $1 fix

Anthropic published a technique: use an LLM (Claude 3 Haiku) to generate a 50-100 token context description for each chunk, then prepend it before embedding.

**Before:** "The company's revenue grew by 3% over the previous quarter."

**After:** "This chunk is from an SEC filing on ACME corp's performance in Q2 2023; the previous quarter's revenue was $314 million. The company's revenue grew by 3% over the previous quarter."

**Retrieval failure rates:** 67% reduction. Cost: $1.02 per million document tokens (prompt caching).

## The parent-child pattern

**Parent-child chunking:** Create two levels:
- Small "child" chunks (128-256 tokens) for embedding and retrieval
- Larger "parent" chunks (512-1024 tokens) that contain the children
- Search against children, return parent to LLM

Small chunks have better retrieval precision. Large chunks have better generation context. You get both.

## Recommendation

**Start here:** `RecursiveCharacterTextSplitter` with 256-512 token chunks and 10-15% overlap. Handles 80% of use cases.

**Add parent-child** if retrieval precision is good but generation quality is poor.

**Add hybrid retrieval (embeddings + BM25)** before upgrading chunking strategy. Anthropic's data shows bigger lift than semantic chunking.

**Try semantic chunking** only if documents have clear multi-topic structure.

**Skip agentic chunking** unless you justify 100x cost increase.

---

*来源：BuildMVPFast | 提取日期：2026-05-16*
