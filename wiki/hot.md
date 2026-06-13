---
title: Hot Cache
updated: 2026-06-13
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-13] INGEST — Agent架构增量：15新来源→5新概念页面(GraphRAG工程+RAG存储+RAG工具+Multi-Agent对比+Agent安全)+7已有页面更新
- [2026-06-13] PATH_FIX — 全量路径引用修复：21个wiki页面source_dir/source_files修复
- [2026-06-13] INGEST — RAG目录变动：2-RAG全栈介绍SHA-256变更

## Active Threads

- **GraphRAG知识链构建完成**：6个GraphRAG源文件蒸馏为完整的concepts/graphrag-engineering页面（微软14步管线+蚂蚁统一架构+6大项目PK+3种搜索模式+部署实践）
- **RAG存储与工具全景充实**：新增2个概念页面覆盖四层存储架构和核心工具链
- **Agent安全与Multi-Agent进入知识库**：Claude Fable 5破解事件和四大框架对比已入库
- **评估指标体系补全**：RAG检索排序7指标(P@K/MRR/MAP/nDCG等)补充到evaluation-metrics

## Key Takeaways

- GraphRAG不是替代传统RAG而是补充——局部型问题仍用向量检索，全局型/多跳型用GraphRAG
- RAG存储是四层架构而非"一个向量库"，缺一层功能失能
- Agent安全是动态对抗：字符混淆+上下文稀释+学术伪装+解构重组4类绕过手法
- Multi-Agent生产首选LangGraph（可靠性+可调试性），CrewAI适合快速验证

## Flagged Contradictions

- GraphRAG"以检索为始" vs KAG"以推理为始"——不同范式而非矛盾
- 3-RAG工程全景与【17】RAG工程全景内容完全相同（同一文件出现在两个路径），不是矛盾而是副本
