---
title: Hot Cache
updated: 2026-06-16
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-16] INGEST — Harness工程+Claude Code+高级RAG+向量数据库+LangGraph Memory：2个新页面+5个更新页面+2个交叉链接更新
- [2026-06-15] LEARN — Harness Engineering 第二次推荐：9篇新博客下载+新概念发现
- [2026-06-15] INGEST — DFX网络Bonding调试日志：1个新summary+4个已有页面更新

## Active Threads

- **Harness Engineering 正式进入Wiki**：从学习推荐→原始文档收集→wiki概念页面创建，完整知识构建闭环完成。concepts/harness-engineering 已整合4篇原始文档（范式革命+从零理解+起源原理+驾驭工程介绍），覆盖三次范式跃迁+四大支柱+六大共识+四实战案例+三阶段路线图
- **Claude Code 实体页面创建**：entities/claude-code 整合3篇原始文档（工作原理深度解析+使用技巧+记忆系统设计），覆盖极简while循环架构+六层记忆+子代理+技能+Hook+蚂蚁喂养开发哲学
- **高级RAG演进方向补充**：concepts/rag-engineering 新增GraphRAG+HyDE+Self-RAG+Code-RAG+行业黑话+多模态RAG七大演进方向，与已有传统RAG流水线形成完整知识链

## Key Takeaways

- **Agent = Model + Harness**：瓶颈在外围工程而非模型智能——Can.ac改Harness分数翻10倍(6.7%→68.3%)是最直接证据
- **上下文40%甜区**：超过40%进入Dumb Zone（幻觉、死循环、格式错误），"更多token≠更好结果"
- **Claude Code 记忆六层架构**：Agent→Auto→Local→Project→User→Managed，Auto Memory四类内容(user/feedback/project/reference)+时间衰减(>2天提醒/>30天stale)
- **向量数据库银弹论**：四大局限（更新困难/过滤弱/精度权衡/运维贵），混合检索+场景适配是务实之选
- **LangGraph Memory完整分类**：短期(Checkpoint+3种长对话管理技术)+长期(Store+写入/管理/表示各2种方式)——Agent记忆设计从此有清晰框架

## Flagged Contradictions

- GraphRAG"以检索为始" vs KAG"以推理为始"——不同范式而非矛盾
- Harness定义：arXiv要求Control Mechanisms必要，但部分实践文章将Control作为可选——定义vs实践的张力
- Claude Code 简单循环 vs LangGraph 复杂状态图——不同哲学而非对立（Harness vs Workflow之争）
