---
title: 工具调用与MCP协议
category: concepts
tags: [AI, Agent, MCP, Function Call, 工具调用]
summary: 工具调用是Agent连接外部世界的协议边界——JSON Schema描述接口、结构化输出保证安全、MCP统一工具生态
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】20：工具调用与 MCP.md]
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
  - target: "[[concepts/agent-framework-engineering]]"
    type: implements
  - target: "[[concepts/llm-infra-landscape]]"
    type: derived_from
---

# 工具调用与MCP协议

工具调用（Tool/Function Call）让LLM从"纯文本生成器"升级为"可执行动作的Agent"。但工具调用不仅是技术问题——它是**协议边界和安全边界**。

## Function Call机制

### OpenAI格式
```json
// 定义工具
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "获取指定城市的天气",
    "parameters": {
      "type": "object",
      "properties": {
        "city": {"type": "string", "description": "城市名"}
      },
      "required": ["city"]
    }
  }
}

// LLM返回调用请求
{"name": "get_weather", "arguments": {"city": "北京"}}
```

### 关键设计
- **JSON Schema描述接口**：工具的入参、出参、类型、必填字段用JSON Schema严格定义
- **LLM只生成调用意图**：不直接执行，由宿主程序调度执行
- **结构化输出**：确保LLM输出符合Schema，避免自由文本导致解析失败

## 并行工具调用

- 单次LLM推理可请求调用多个工具
- 宿主程序并行执行所有工具，收集结果
- 将结果拼回上下文，让LLM综合回答

## MCP（Model Context Protocol）

Anthropic提出的开放协议，统一LLM与外部工具/数据源的交互标准：

### MCP架构
```
Host（Claude Code等AI应用）
  ├── MCP Client（协议客户端）
  │     ├── MCP Server A（文件系统）
  │     ├── MCP Server B（数据库）
  │     └── MCP Server C（API服务）
```

### MCP核心能力
| 能力 | 描述 |
|------|------|
| **Tools** | LLM可调用的函数（计算、查询、执行） |
| **Resources** | LLM可读取的上下文（文件、数据、配置） |
| **Prompts** | 预定义的交互模板 |

### MCP vs 自定义Function Call

| 维度 | 自定义Function Call | MCP |
|------|---------------------|-----|
| 标准化 | 每个应用自定义格式 | 统一协议标准 |
| 工具生态 | 各家各自封装 | 一套Server适配所有Host |
| 安全边界 | 应用自行实现 | 协议内置权限控制 |
| 发现机制 | 手动注册 | Client自动发现Server能力 |

MCP的目标是成为"LLM的USB接口"——一个标准协议让任何工具可以接入任何LLM应用。 ^[inferred]

## 安全边界

工具调用是Agent攻击面的核心入口：
- **Prompt Injection**：恶意输入让LLM调用危险工具（如删除文件、发送邮件）
- **权限控制**：工具执行需要沙箱/权限隔离
- **审计**：每次工具调用需记录日志，支持回溯

## 来源

- 大模型基础设施工程系列20：工具调用与MCP（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）