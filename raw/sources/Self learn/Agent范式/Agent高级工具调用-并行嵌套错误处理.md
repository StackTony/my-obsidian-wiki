---
credibility: low
---
> 原文： [Introducing advanced tool use](https://anthropic.com/engineering/advanced-tool-use) | Anthropic Engineering Blog | 2025.11.20

## 导语

随着 Agent 连接的工具越来越多——IDE 助手集成 git、包管理器、测试框架、部署管道；运维协调器连接 Slack、GitHub、Google Drive、Jira 和数十个 MCP 服务器——一个问题浮出水面： **如何让模型在数百甚至上千个工具中高效工作？**

Anthropic 在 Claude 开发者平台上推出了三项 Beta 功能，从根本上解决了工具调用的扩展性问题。

---

## 一、工具搜索工具（Tool Search Tool）

### 问题

传统做法是将所有工具定义预加载到上下文中。当工具数量达到数百个时，这会消耗大量 token（文中提到多达 134K tokens），而且容易导致错误的工具选择。

### 解决方案

将工具定义标记为延迟加载（ `defer_loading: true` ），Claude 仅在需要时通过搜索动态发现并加载相关工具。

### 效果

- 上下文消耗从 ~77K tokens 降低到 8.7K tokens， **减少 85%**
- 工具选择准确性从 79.5% 提升至 88.1%（Opus 4.5 在 MCP 评估中）

---

## 二、程序化工具调用（Programmatic Tool Calling）

### 问题

传统工具调用每个步骤都需要一次完整的推理，且中间结果（如处理大量日志或数据）会污染上下文窗口。

### 解决方案

允许 Claude 编写 Python 代码来编排工具调用。工具在代码执行环境中运行，处理大量数据，仅将最终结果返回给 Claude。

![程序化工具调用](https://img2024.cnblogs.com/blog/383528/202602/383528-20260220091355560-2030949710.png)

### 效果

- 复杂研究任务的 token 使用量平均下降 **37%**
- 显著降低延迟

---

## 三、工具使用示例（Tool Use Examples）

### 问题

JSON Schema 只能定义结构，无法表达具体的使用模式——可选参数何时填写、日期格式惯例等。

### 解决方案

在工具定义中直接提供 `input_examples` ，通过具体示例向 Claude 展示正确的调用方式。

### 效果

- 复杂参数处理的准确率从 72% 提升至 **90%**

---

## 四、最佳实践：分层使用

根据你的瓶颈，分层选择功能：

| 功能 | 适用场景 |
| --- | --- |
| Tool Search Tool | 工具定义 >10K tokens 或拥有 10+ 工具 |
| Programmatic Tool Calling | 处理大型数据集、多步骤工作流 |
| Tool Use Examples | 复杂嵌套结构或多个可选参数 |

---

## 五、如何启用

```
client.beta.messages.create(
    betas=["advanced-tool-use-2025-11-20"],
    model="claude-sonnet-4-5-20250929",
    # ... 其他参数
)
```

---

## 读后感

这三个功能解决了 Agent 工程化中最头疼的三个问题： **工具发现、数据流和参数准确性** 。特别是 Tool Search Tool，它让"连接上千个 MCP 服务器"从理论变成了现实。

---

> 本文是 **Anthropic AI Agent 系列** 第 3 篇，共 15 篇。下一篇： [如何为 Agent 设计好用的工具](https://www.cnblogs.com/informatics/04-writing-tools-for-agents/)
> 
> 关注公众号 **coft** 获取系列更新。

## 转载声明

本文来自博客园，作者： [warm3snow](https://www.cnblogs.com/informatics/)

转载请注明原文链接： [https://www.cnblogs.com/informatics/p/19625891](https://www.cnblogs.com/informatics/p/19625891)

本文版权归作者和博客园共有，欢迎转载，但未经作者同意必须在文章页面给出原文连接，否则保留追究法律责任的权利。