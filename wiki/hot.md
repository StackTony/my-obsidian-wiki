---
title: Hot Cache
updated: 2026-08-03
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-08-03] INGEST — AI Agent 协议+平台增量：11新来源（6实质+4稀薄+1重命名）+74 CRLF重命名 → 7新页面+3更新。manifest 188→198条目
- [2026-06-29] INGEST — AI Agent增量：2新来源（Agent系统架构设计+消息总线架构）+7修改来源 → 3新页面+7更新页面
- [2026-06-29] UPDATE — Graphify与GitNexus实体页更新：新增GitNexus CLI/MCP/Web工具体系
- [2026-06-27] INGEST — Multi-Agent协同：2新页面（OMO实体+Multi-Agent编排概念）+7更新

## Active Threads

- **三大Agent协议栈分层模型**：新概念页agent-communication-protocols提出MCP/ACP/A2A三层分工——MCP（工具驱动层，Agent↔Resource）+ACP（协作通信层，企业内Agent↔Agent）+A2A（公共发现层，跨厂商Agent↔Agent）——形成"对物 vs 对智"的清晰边界 ^[inferred]
- **Agent开发平台5分类全景**：新概念页agent-development-platforms-landscape将10+平台分为自主执行（AutoGPT）/可视化编排（Dify/Flowise）/通用框架（LangChain）/多Agent协作（MetaGPT/CrewAI）/有状态Agent（Letta）——选型从"流行度比较"升级为"定位匹配" ^[inferred]
- **Headroom上下文压缩中间件**：新实体页entities/headroom-tool——ContentRouter+5策略（SmartCrusher/CodeCompressor/Kompress-base/CacheAligner/CCR），SRE日志场景92% token节省，MCP server模式实现跨Agent共享压缩记忆
- **消息总线文件重命名同步**：Agent 架构设计解析 → Agent 系统架构设计（消息总线），字节相同，manifest条目迁移+wiki页面source_files同步更新

## Key Takeaways

- **MCP对物，A2A对智**：MCP解决Agent调用外部能力（工具/数据），A2A解决Agent调用另一个Agent——两者互补而非替代，主Agent通过MCP取数据+通过A2A委派子任务 ^[inferred]
- **ACP企业内协作定位明确**：ACP强调"企业防火墙内"Agent协作，采用REST+Agent/Run两阶段+离线发现机制——与A2A"跨厂商公网"形成部署边界 ^[inferred]
- **稀薄来源识别与跳过**：4个仅含URL的文件（≤100字节）标记为source_type="sparse"，manifest登记但不生成页面——避免无意义摘要污染wiki
- **CRLF行尾转换非内容变化**：72个LF→CRLF转换通过SHA-256识别为无实质变化，仅更新哈希避免重复ingest——Delta追踪机制有效降低成本

## Flagged Contradictions

- **ACP与A2A边界重叠？**：两者都是Agent↔Agent通信，仅"企业内 vs 跨厂商"区分是否足够？若企业内Agent需要跨厂商调远程专家，走ACP还是A2A？^[ambiguous]
- **平台分类重叠**：LangChain既算"通用框架"也支持"多Agent协作"（LangGraph），分类是否应按"主要定位"而非"支持能力"？^[ambiguous]
- **Headroom跨Agent共享记忆 vs Agent隔离原则**：共享压缩记忆提升效率但模糊了Agent间上下文边界，是否引入新的耦合问题？^[inferred]
