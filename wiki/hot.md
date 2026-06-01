---
title: Hot Cache
updated: 2026-06-01
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-01] INGEST — Linux虚拟化源文件消化完成，13个原始文档蒸馏为10个新wiki页面+3个已有页面更新。首次覆盖skills、entities、synthesis分类
- [2026-06-01] INGEST — 首批Linux操作系统源文件消化完成，25个原始文档蒸馏为14个wiki页面

## Active Threads

- **Linux虚拟化知识网络**：virtio框架(virtio→vhost→vhost-user→vDPA四种演进)、中断虚拟化(VGIC/KVM注入)、设备直通(IOMMU/SR-IOV/VFIO)、热迁移三大领域概念页已建立，与已有内核知识交叉链接
- **跨分类首次扩展**：skills分类（virsh操作手册）、entities分类（libvirt/virsh）、synthesis分类（virtio架构演进分析）首次写入内容
- **下一步可扩展方向**：云原生（Kubernetes）、数据结构与算法、消息队列等主题尚待消化

## Key Takeaways

- Virtio核心是前后端分离+共享内存(vring)+零拷贝通知(ioeventfd/irqfd)，数据面演进从全软件模拟到硬件直通
- 中断虚拟化分三种场景：物理设备→vCPU、虚拟外设→vCPU、Guest IPI
- 热迁移三阶段：内存迭代拷贝→停机拷贝→网络恢复，脏页检测(getdirty)有性能开销
- 设备直通三大技术：IOMMU(DMA翻译+隔离)、SR-IOV(PF/VF)、VFIO(用户态驱动)

## Flagged Contradictions

- 中断虚拟化源文件偏简略（VGIC仅为片段），概念页面推断比例偏高(provenance: inferred 0.30)
- 设备直通源文件内容不完整（仅概念介绍，缺乏VFIO group/container/device三层抽象细节）
- 网络虚拟化源文件virtio-net为极简stub(168字节)，virtio-net内核态转发流程未详细展开