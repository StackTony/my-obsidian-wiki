---
title: Hot Cache
updated: 2026-06-02
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-02] INGEST — 云原生21个源文件蒸馏为17个新wiki页面 + 1个更新：K8s架构+网络+安全+CNI+容器运行时+Cgroups v2+OverlayFS+Seccomp+microVM对比+网络性能实测+Prometheus+containerd+runc，覆盖云原生三层架构体系
- [2026-06-02] INGEST — 消息队列4个源文件蒸馏为3个新wiki页面
- [2026-06-02] INGEST — AI 人工智能50个源文件蒸馏为17个wiki页面

## Active Threads

- **云原生知识网络成型**：10个概念页+2个实体页+3个摘要页+2个技巧页+1个综合页，从Linux内核特性到K8s编排到可观测的完整链条
- **容器→microVM隔离模型讨论**：容器共享内核vs microVM独立内核，信任边界驱动选择，Firecracker 125ms与容器同量级
- **跨域连接发现**：云原生全景页连接LLM基础设施全景（三层架构结构相似性）、Linux内核已有页面（Namespace/Cgroup/IO栈/网络栈/锁机制容器视角）

## Key Takeaways

- 容器不是发明是拼装：8种Namespace(2002-2020)+Cgroup+pivot_root+OverlayFS+Seccomp+Capabilities的组合拳
- K8s声明式API+协调循环是一切能力的驱动机制——自愈、弹性、滚动更新、GitOps偏移纠正都从同一个循环推导
- Cilium eBPF可完全替换kube-proxy：iptables O(n)→IPVS O(1)→eBPF三代演进，规模是换代的驱动力
- Cgroups v2三道防线：memory.low保底→memory.high预警→memory.max兜底；CFS throttle尾延迟问题让K8s社区争论是否该设CPU limit
- Copy-on-Write是OverlayFS性能杀手：100MB文件首次写47.32ms vs 第二次0.18ms，263倍差距——数据库必须放volume
- containerd-shim是关键解耦：即使containerd崩溃容器继续运行，防止级联故障

## Flagged Contradictions

- Prometheus"开源版BorgMon"说法在社区有争议——原文明确声称但更准确说是"受BorgMon启发"
- Prometheus原文声称使用LevelDB引擎，但这可能反映v1.x；现代v2.x使用自定义TSDB实现
- K8s安全加固指南用aescbc做EncryptionConfiguration示例，但未明确推荐最优加密provider