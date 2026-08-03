---
title: ACP协议（Agent Communication Protocol）
category: summaries
tags: [AI, Agent, ACP, 协议, IBM, Linux基金会]
summary: IBM/LinuxFoundation的ACP协议——Agent间"世界语"：REST/HTTP+框架无关+多模态+离线发现+三种部署模式，与MCP（工具层）和A2A（发现层）形成协议栈分工
source_dir: AI 人工智能/AI Agent/各种协议/ACP
source_files: [ACP协议让AI团队协作成为现实（上篇）.md, ACP协议实战指南：从零构建你的AI智能体团队（下篇）.md]
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-08-03
tier: supporting
created: 2026-08-03
updated: 2026-08-03
---

# ACP协议（Agent Communication Protocol）

原文（上篇）：https://zhuanlan.zhihu.com/p/1935325407202222463
原文（下篇）：https://zhuanlan.zhihu.com/p/1935327158538077444
GitHub仓库：https://github.com/i-am-bee/acp

## 核心内容

### 上篇：ACP理论深度解析

#### AI生态碎片化的"巴别塔"困境

LangChain框架Agent说"LangChain语"，CrewAI框架Agent说"CrewAI语"，AutoGen框架Agent说"AutoGen语"——每要让不同框架Agent协作，开发者必须为每种组合编写昂贵、脆弱、不可复用的定制化集成代码。这种碎片化阻碍了大规模AI系统的构建，企业难以组建跨团队AI协作网络。

#### ACP是什么

**Agent Communication Protocol (ACP)**——IBM团队（现已交由Linux基金会管理）推出的"AI智能体领域的HTTP协议"标准，让所有智能体都能说同一种"世界语"。

**设计哲学**：
- 基于成熟**REST架构**和HTTP协议——任何会写Web应用的程序员都能快速上手，可用cURL/Postman/浏览器直接测试
- 完全**框架无关**——不管用什么技术栈构建Agent，都能通过简单适配层接入ACP网络
- 天然支持**多模态数据传输**——文字、图片、音频、自定义格式都能无缝处理
- 由**Linux基金会管理**——开放治理，避免供应商锁定

#### 三大核心优势

1. **简单到极致的通信方式**——基于REST和HTTP，开发者不需要学习新协议规范，现有网关、负载均衡器、监控工具都能直接使用
2. **高度灵活的部署架构**——支持三种部署模式：
   - 单智能体模式：客户端直接对接一个智能体，适合快速原型/简单任务/调试测试
   - 多智能体单服务器模式：一个服务器同时托管多个相关智能体，优化资源利用便于集中管理
   - 分布式多服务器架构：每个服务器独立部署和扩展，不同类型智能体实现故障隔离
3. **独特的离线发现机制**——把智能体"能力清单"直接嵌入到分发包中，即使某个智能体暂时不在线，其他系统也能知道它的存在和具体能力。对云原生架构友好，支持"按需启动"资源管理，解决企业内网和边缘计算场景的服务发现难题

#### ACP vs MCP vs A2A

| 特性 | ACP | MCP | A2A |
|------|-----|-----|-----|
| 开发者 | IBM/Linux基金会 | Anthropic | Google |
| 核心目标 | 智能体间协作 | 智能体连接工具 | 公网智能体发现 |
| 通信协议 | REST/HTTP | JSON-RPC | JSON-RPC |
| 治理模式 | 开放治理 | 企业主导 | 企业主导 |
| 主要场景 | 团队协作、企业内部 | 单体能力增强 | 公共服务发现 |

**网络协议栈式分工**：
- **MCP** = 工具驱动层（智能体如何连接外部工具）
- **ACP** = 协作通信层（团队内智能体如何相互协作，如企业内部财务AI/法务AI/市场AI无缝配合）
- **A2A** = 公共发现层（帮助智能体发现和使用公共互联网上的第三方智能体服务）

#### 战略优势

1. **开放治理带来的安全感**——Linux基金会中立地位确保发展方向由社区需求驱动而非某家公司商业利益
2. **工程师友好的务实设计**——选择REST而非更复杂协议规范，学习成本对技术普及重要
3. **与云原生生态的天然契合**——架构设计与现代微服务最佳实践高度一致，熟悉Kubernetes/Docker/服务网格的团队可直接应用现有经验

### 下篇：ACP实战指南

#### 环境准备

ACP官方推荐使用`uv`包管理器：

```bash
uv init --python '>=3.11' my_acp_project
cd my_acp_project

# 基础ACP SDK
uv add acp-sdk

# 诗歌生成场景
uv add transformers torch crewai crewai-tools
uv add scipy pydub httpx asyncio

# 智能体生成器需要
uv add langchain langchain-mcp-adapters langgraph mcpdoc
uv add pydantic-settings
```

#### 案例一：诗歌创作多智能体系统

通过ACP搭建多智能体协作：
- **诗人**：根据主题创作诗歌（中英文）
- **配音师**：把诗歌转成语音
- **音乐家**：配背景音乐
- **协调器**：统筹整个流程

服务器端使用`acp_sdk.server.Server`，通过`@server.agent()`装饰器注册Agent；客户端使用`acp_sdk.client.Client`调用。

核心技术选型：
- TTS：BosonAI语音生成模型（支持情感表达和多语言）
- 音乐生成：Meta开源的文本到音乐生成模型（300M参数版本）
- LLM：Gemini 2.0 Flash（temperature=0.7提升创意性）

#### 案例二：动态智能体生成器（Meta-Agent）

让智能体生成智能体——元智能体（Meta-Agent）能力：
1. **多源文档集成（MCP协议）**：通过MCP实时读取ACP/LangGraph/BeeAI等技术文档
2. **智能代码生成**：用LangGraph+LLM理解需求并生成代码
3. **自适应模板系统**：根据不同需求选择合适代码模板

技术架构要点：
- **SessionManager**：管理MCP文档连接和工具
- **ReAct Agent**：使用推理-行动模式生成代码
- **Temperature=0.1**：确保代码生成的准确性和一致性

#### ACP核心代码模式

```python
from acp_sdk import Message, MessagePart
from acp_sdk.server import Context, Server

server = Server()

@server.agent()
def poetry_agent(input: list[Message], context: Context) -> Iterator:
    """多智能体诗歌创作系统"""
    theme = str(input[-1].parts[0].content) if input else ""
    # ... 业务逻辑 ...
    yield MessagePart(content=f"诗歌: {poem_content}")
```

## 来源

- ACP协议让AI团队协作成为现实（上篇）.md（raw/sources/AI 人工智能/AI Agent/各种协议/ACP/）
- ACP协议实战指南：从零构建你的AI智能体团队（下篇）.md（raw/sources/AI 人工智能/AI Agent/各种协议/ACP/）
- 官方文档：https://agentcommunicationprotocol.dev/
- GitHub仓库：https://github.com/i-am-bee/acp
- BeeAI平台：https://beeai.dev/agents

## 相关Wiki页面

- [[concepts/agent-communication-protocols]] — 三大Agent协议三层协议栈概念页
- [[concepts/tool-calling-mcp]] — MCP协议——ACP的"对物"互补
- [[summaries/ai-protocols-comparison]] — 三大协议对比原文摘要
