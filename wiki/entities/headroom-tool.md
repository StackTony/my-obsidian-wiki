---
title: Headroom（上下文压缩中间件）
category: entities
tags: [AI, Agent, Token压缩, 上下文压缩, 中间件, 开源工具]
aliases: [Headroom, headroom-ai]
summary: Headroom上下文压缩中间件：部署应用与LLM之间，最高减95%Token且可逆不降质，ContentRouter+5策略，MCP server模式跨Agent共享记忆
source_dir: AI 人工智能/AI Agent/Skills
source_files: [Headroom工具：减少token消耗.md]
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.70
lifecycle: draft
lifecycle_changed: 2026-08-03
tier: supporting
created: 2026-08-03
updated: 2026-08-03
relationships:
  - target: "[[concepts/agent-framework-engineering]]"
    type: uses
  - target: "[[concepts/llm-observability]]"
    type: related_to
  - target: "[[concepts/rag-engineering]]"
    type: related_to
  - target: "[[entities/claude-code]]"
    type: related_to
---

# Headroom（上下文压缩中间件）

Headroom是面向AI Agent、LLM流水线的开源上下文压缩中间件，部署在应用与大模型服务商之间。**在内容送入LLM前自动压缩，最高减少95% Token消耗，且完全可逆、不降低模型输出质量**，专门解决工具返回数据、日志、RAG分片、对话历史造成的上下文膨胀、调用成本高昂问题。

**开源地址**：https://github.com/chopratejas/headroom

## 核心压缩架构与多策略分流

内置`ContentRouter`自动识别内容类型，匹配专属压缩算法。**原始内容本地永久存储，LLM可按需调取完整原文，属于无损可逆压缩**。

| 策略 | 适用场景 |
|------|----------|
| **SmartCrusher** | JSON / 数组 / 嵌套结构化数据专用压缩 |
| **CodeCompressor** | 基于AST语法树压缩多编程语言代码（Python/JS/Go/Java等） |
| **Kompress-base** | HuggingFace专用模型，处理自然文本、Agent运行日志 |
| **CacheAligner** | 优化提示词前缀，稳定KV缓存，大幅提升缓存命中率 |
| **CCR**（内容压缩检索） | 原文本地留存，支持模型按需还原完整数据 |

## 实测压缩效果（真实Agent业务负载）

| 业务场景 | 压缩前Token | 压缩后Token | Token节省比例 |
|----------|-------------|-------------|----------------|
| 代码检索（100条结果） | 17765 | 1408 | 92% |
| SRE故障日志排查 | 65694 | 5118 | 92% |
| GitHub工单分类处理 | 54174 | 14761 | 73% |
| 代码库全局浏览 | 78502 | 41254 | 47% |

**精度测试**：在GSM8K数学、TruthfulQA、SQuAD、工具调用BFCL等标准数据集评测，压缩后模型准确率持平甚至小幅提升——原因是过滤冗余噪声，模型更容易抓取关键信号。

## 三种极简接入方案

| 方案 | 适用场景 | 接入方式 |
|------|----------|----------|
| **方案1：一键包装现有Agent** | 零代码改动 | `headroom wrap claude`——自动拦截Claude Code/Cursor/Copilot等工具流量 |
| **方案2：本地代理Proxy** | 不限编程语言、框架 | `headroom proxy --port 8787`——修改SDK请求地址即可 |
| **方案3：内嵌代码库** | 精细控制 | 提供Python/TS原生API，原生兼容Anthropic SDK、LangChain、Vercel AI SDK |

## 特色高阶功能

1. **MCP服务端模式**——执行`headroom mcp install`，对外暴露`headroom_compress/retrieve/stats`三个MCP工具，适配Claude Desktop等MCP客户端，集成进Agent工具循环
2. **跨Agent共享内存**——多Agent共用压缩上下文存储，自动去重，避免多智能体流水线重复传输相同内容
3. **自动学习命令`headroom learn`**——解析失败会话日志，提炼错误经验，自动写入`CLAUDE.md`/`AGENTS.md`配置，规避同类问题重复发生
4. **数据统计`headroom stats`**——统计累计Token节省量、各类内容压缩比例，直观展示成本优化收益

## 适用/不适用人群

### 推荐使用

1. 高频使用Claude Code、Cursor等AI编程工具，有大额Token账单
2. 业务存在大量工具返回JSON、长日志、批量RAG检索的LLM流水线
3. 多Agent协作场景，需要统一共享上下文
4. 要求压缩后可完整还原原始数据，不能粗暴截断文本

### 谨慎使用

1. 仅依赖厂商原生上下文管理、无大量冗余输入
2. 沙箱/受限环境，无法运行本地进程
3. 单次简单问答、上下文几乎无膨胀的轻量场景

## 基础安装与常用命令

```bash
# Python
pip install "headroom-ai[all]"

# Node/TS
npm install headroom-ai
```

核心指令：包装Agent、启动代理、安装MCP、查看节省数据、自动学习故障经验。

## 与其他Wiki页面的关系

- **Agent框架五大支柱** 详见 [[concepts/agent-framework-engineering]]——Headroom是上下文管理支柱的具体实现工具
- **LLM可观测性** 详见 [[concepts/llm-observability]]——Headroom的`headroom stats`是成本观测的具体实现
- **RAG工程全景** 详见 [[concepts/rag-engineering]]——Headroom解决RAG分片造成的上下文膨胀
- **Claude Code** 详见 [[entities/claude-code]]——Headroom的`headroom wrap claude`直接针对Claude Code场景

## 来源

- Headroom工具：减少token消耗.md（raw/sources/AI 人工智能/AI Agent/Skills/）
- 原文：https://dev.to/arshtechpro/headroom-cut-your-llm-token-usage-by-up-to-95-without-changing-your-answers-5g06
- 开源地址：https://github.com/chopratejas/headroom
