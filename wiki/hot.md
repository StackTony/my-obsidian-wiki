---
title: Hot Cache
updated: 2026-06-27
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-27] INGEST — Multi-Agent协同：2个新页面（Oh My OpenCode实体+Multi-Agent编排概念）+7个更新页面。OMO是开源项目中最完善的multi-agent编排方案之一——11个希腊神话命名agent+精细化工具权限矩阵+Ralph Loop自动续跑+Hashline Edit防幻觉
- [2026-06-25] LEARN — Loop Engineering学习推荐：12篇深度推荐+3篇博客下载+核心术语表
- [2026-06-22] INGEST — SAG+RAG常用框架+软件工程：2个新页面+4个更新页面

## Active Threads

- **Multi-Agent编排设计模式**：从OMO实践提炼出7个核心模式——角色分化与工具隔离、主编排+子执行分层、双轨主Agent哲学、证据驱动完成标准、并发控制与防递归、completion_promise续跑、AgentPromptMetadata自描述。这是Wiki首次从"框架对比"视角升级到"设计模式提炼"视角
- **OMO作为Harness Engineering实践案例**：工具权限矩阵=约束系统、Ralph Loop=Loop Engineering实现、completion_promise=反馈回路、并发控制=资源管理——四大支柱全部落地
- **Loop Engineering vs Ralph Loop**：OMO的Ralph Loop是Loop Engineering概念的具体实现——自动续跑+completion_promise让多次运行自主可控

## Key Takeaways

- **OMO是"oh-my-zsh"模式**：不改变宿主核心，通过插件机制注入整套agent体系——AI编程工具的模块化扩展范式 ^[inferred]
- **希腊神话命名即设计文档**：Sisyphus推石头永不放弃、Oracle只给建议不动手、Prometheus规划未来——用户不需读文档就能直觉理解角色
- **开放-封闭原则在agent系统中的实现**：AgentPromptMetadata自描述系统让添加新agent时主编排prompt自动更新，第三方agent也能通过buildCustomAgentMetadata()自动融入
- **行为模式切换比参数微调更可靠**：LLM对"你是管理者"和"你是执行者"的响应差异远大于autonomy参数调整 ^[inferred]
- **证据驱动完成=机械化约束**：NO EVIDENCE=NOT COMPLETE，完成标准不是prompt软约束而是工具返回的硬证据

## Flagged Contradictions

- OMO "自主执行"（Hephaestus禁止询问）vs Harness Engineering "约束机械化"——自主和约束的边界在哪里？Hephaestus的FORBIDDEN指令本身就是一种约束 ^[inferred]
- Multi-Agent编排的"最优分层深度"——OMO用两层（主→子），但更深层意味着更多延迟和上下文传递损耗 ^[ambiguous]
