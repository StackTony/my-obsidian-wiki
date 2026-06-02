---
title: Hot Cache
updated: 2026-06-02
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-02] INGEST — AI 人工智能50个源文件蒸馏为17个新wiki页面，覆盖大模型基础设施全景（GPU→CUDA→训练→推理→RAG→Agent→服务化→网关→观测）和Agent架构（LangChain/LangGraph/RAG/知识图谱）
- [2026-06-02] INGEST — DFX工具29个源文件蒸馏为16个新wiki页面+1个更新

## Active Threads

- **LLM基础设施知识网络成型**：12个概念页+5个实体页+1个综合页，从GPU底层到服务上层形成五层知识栈
- **Agent/RAG知识栈建立**：RAG五代演进→分块策略→Agent框架→工具调用/MCP→知识图谱工具，从检索到编排的完整链条
- **DeepSeek-V4工程密度**：MLA+MoE+FP8+DualPipe+磁盘KV cache+专家蒸馏的组合创新案例

## Key Takeaways

- GPU架构决定了推理优化空间：HBM带宽限制Decode吞吐、Tensor Core加速Prefill，同一GPU上两阶段不能共用调参逻辑
- 3D并行不是越多越好：DP/TP/PP/EP各有切分对象和通信开销，组合需按瓶颈算账而非全开
- PagedAttention+Continuous Batching是推理引擎的现代范式——所有主流引擎都已采纳
- RAG效果差不能只怪大模型或Prompt——需要沿流水线逐层排查（解析→切片→检索→重排→组装→评估）
- 可靠Agent=可观测状态机，而非自由聊天循环——LangGraph将行为建模为有向图
- DeepSeek-V4展示了"工程密度>硬件堆量"的完整路径：10倍成本下降来自架构创新而非GPU堆量

## Flagged Contradictions

- GPU互联与网络（04篇）、Checkpoint与故障容忍（10篇）、长上下文工程（16篇）、成本合规安全（24篇）、未来展望（25篇）、评测基准汇总尚未创建独立页面——内容被整合到相关概念页中
- Ollama本地运行工具和Transformer模型源文件为空/极短链接索引，未产生独立wiki页面
- 推测解码与MTP（15篇）内容被整合到推理引擎概念页，未创建独立页面