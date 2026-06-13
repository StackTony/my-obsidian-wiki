---
title: Hot Cache
updated: 2026-06-13
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-13] STRUCTURE — 云原生领域分类显式化：新增k8s-cloud-native-landscape导航页+index.md云原生Concepts从扁平11条重构为3个子标题(K8s核心5条+容器运行时6条+可观测1条)
- [2026-06-13] STRUCTURE — Linux OS/虚拟化领域分类显式化（之前完成）
- [2026-06-13] LEARN — Harness Engineering 学习推荐（之前完成）

## Active Threads

- **五大领域landscape全覆盖**：现在有5个导航枢纽页面——Linux OS/虚拟化(linux-os-virtualization-landscape)、云原生(k8s-cloud-native-landscape)、AI Agent(agent-architecture-landscape)、LLM基础设施(llm-infra-landscape)、云原生基础设施三层架构(cloud-native-infrastructure-landscape)
- **领域间的映射关系网**：Linux→虚拟化(7条)、Linux→云原生(4条 Namespace/Cgroup/OverlayFS/Seccomp)、云原生→AI(K8s编排推理引擎)、容器vs VM(性能vs隔离的两种解)
- **index.md 五大领域分组**：Linux(OS+虚拟化+DFX)、数据结构与算法、AI(LLM+RAG+Agent+评估+安全+飞轮)、云原生(K8s+容器+可观测)

## Key Takeaways

- 云原生=Linux内核特性的拼装，4条核心映射：Namespace→容器视图隔离、Cgroup→资源限制(QoS等级)、OverlayFS→镜像层叠、Seccomp+Capabilities→安全防线(PSS)
- 容器vs VM是"性能vs隔离"的两种解——容器共享内核快但不安全，VM独立内核安全但慢，microVM(Firecracker)尝试两头兼得
- 云原生3个核心矛盾：共享vs独立内核、声明式vs命令式、服务网格vs不侵入——与Linux虚拟化4个矛盾形成类比映射
- 云原生与AI的交叉点：K8s编排推理引擎(Deployment→推理部署、Service→推理入口、HPA→弹性伸缩、Prometheus→LLM可观测)

## Flagged Contradictions

- GraphRAG"以检索为始" vs KAG"以推理为始"——不同范式而非矛盾
- 3-RAG工程全景与【17】RAG工程全景内容完全相同（同一文件出现在两个路径），不是矛盾而是副本
- Harness Engineering vs Agent框架工程：两者不是替代而是互补——框架是工具，Harness是方法论+工程体系
