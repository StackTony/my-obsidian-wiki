---
title: Hot Cache
updated: 2026-06-29
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-29] INGEST — AI Agent增量：2新来源（Agent系统架构设计+消息总线架构）+7修改来源 → 3新页面+7更新页面。manifest 40+条目从Agent架构迁移到AI Agent路径
- [2026-06-29] UPDATE — Graphify与GitNexus实体页更新：新增GitNexus CLI/MCP/Web工具体系
- [2026-06-27] INGEST — Multi-Agent协同：2新页面（OMO实体+Multi-Agent编排概念）+7更新
- [2026-06-25] LEARN — Loop Engineering学习推荐：12篇深度推荐+3篇博客下载

## Active Threads

- **Agent系统架构设计**：新概念页agent-system-architecture横跨两篇新来源——执行循环Observe-Think-Act+消息总线解耦Channel-Agent，首次将Skill vs Tool、三层Memory、Sub-agent机制整合为统一架构视图
- **消息总线作为Agent解耦核心**：Agent架构设计解析文章提出四层架构（Channel→Session→Agent→Skill），同Session串行不同Session并发，LLM Provider统一接口——这是继Harness Engineering后第三个独立Agent架构范式 ^[inferred]
- **目录迁移Agent架构→AI Agent**：manifest 50个键+wiki 23个页面source_dir全部从Agent架构迁移到AI Agent，与raw/sources目录重命名同步

## Key Takeaways

- **执行循环是Agent的"心脏"**：Observe-Think-Act三步循环驱动所有Agent行为，Skill/Memory/Sub-agent都是循环内的资源接入点 ^[inferred]
- **消息总线解耦Channel-Agent**：多渠道接入不再需要为每个Channel写不同Agent，而是Channel发消息→Bus路由→Agent处理——统一入口+统一处理 ^[inferred]
- **Skill vs Tool的关键区分**：Skill是Agent主动调用的能力包（声明式），Tool是被动响应的外部接口（命令式）——这是Agent架构从"工具调用"到"能力编排"的范式升级 ^[inferred]
- **LangChain/LangGraph持续深化**：7个修改来源中有5个来自LangChain/LangGraph目录，工作流编排原理大幅更新+状态/状态图三层概念+四种驱动机制

## Flagged Contradictions

- **消息总线串行vs并发**：同Session串行保证一致性，但串行是否成为瓶颈？Session粒度的并发调度可能不够细 ^[ambiguous]
- **Skill声明式vs实际执行**：声明式Skill设计目标是"Agent按需调用"，但LLM对Skill的理解可能偏差导致调用失败——需要验证器（Verifier Engineering交叉） ^[inferred]
- **OMO自主执行vs消息总线约束**：OMO的Hephaestus"禁止询问"与消息总线"统一接口"是否矛盾？前者强调Agent自主、后者强调系统约束 ^[ambiguous]
