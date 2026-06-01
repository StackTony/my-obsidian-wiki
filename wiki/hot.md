---
title: Hot Cache
updated: 2026-06-01
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-01] INGEST-STEP5 — 补做Ingest第5步跨分类更新，新增3个skills页面(kernel-debugging/ipc-programming/lock-selection)和1个synthesis页面(kernel-subsystem-interactions)
- [2026-06-01] REBUILD — Linux操作系统14个旧wiki页面归档重建，25个源文件重新蒸馏为14个新页面
- [2026-06-01] INGEST — Linux虚拟化13个源文件蒸馏为10个新页面+3个更新

## Active Threads

- **Linux内核知识网络完整成型**：9个OS概念页 + 3个虚拟化概念页 + 4个skills实操页 + 2个synthesis综合页，覆盖从理论→实操→跨领域洞察的完整链条
- **跨分类覆盖扩展**：skills从1个(virsh)增至4个(新增kernel-debugging/ipc-programming/lock-selection)；synthesis从1个增至2个(新增kernel-subsystem-interactions)
- **下一步可扩展方向**：云原生(Kubernetes)、数据结构与算法、消息队列、AI、DFX工具等主题尚待消化

## Key Takeaways

- Ingest第5步触发条件表真正有用：16个源文件触发skills、12个触发synthesis——远远不是"没有机会"
- preempt_count是内核最核心的跨子系统共享机制：一个32-bit整数同时约束中断/软中断/调度三种行为
- softirq枚举本身就是跨子系统地图：NET_RX/BLOCK/SCHED/RCU_SOFTIRQ分别是网络/IO/调度/锁子系统的延迟入口
- Page Cache是IO+MM+文件系统+IPC的四子系统交汇点（Shmem的双重归属最典型）
- 内核设计偏好"共享机制"：preempt_count/softirq/Page Cache分别服务3+、6+、4+子系统

## Flagged Contradictions

- 中断虚拟化源文件偏简略（VGIC仅为片段），推断比例偏高(inferred 0.30)
- 设备直通源文件缺乏VFIO group/container/device三层抽象细节
- 网络虚拟化virtio-net为极简stub(168字节)
- 进程调度仅有2个简短源文件，概念页推断比例高(inferred 0.35)