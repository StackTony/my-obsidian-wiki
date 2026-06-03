---
title: 容器 vs microVM
category: concepts
tags: [云原生, 容器, microVM, Firecracker, KVM, 安全]
aliases: [容器与microVM, Firecracker]
relationships:
  - target: "[[concepts/container-runtime-deep-dive]]"
    type: replaces  # 修正：原为contradicts，microVM是容器的替代隔离方案而非矛盾 ^[inferred]
  - target: "[[concepts/seccomp-capabilities]]"
    type: related_to
  - target: "[[concepts/linux-virtio-architecture]]"
    type: uses
  - target: "[[concepts/linux-interrupt-virtualization]]"
    type: related_to
source_dir: 容器运行时/从零造容器系列
source_files: [【从零造容器】10 容器 vs microVM：Firecracker 凭什么 125ms 启动.md]
summary: 容器共享内核(单点故障) vs microVM独立内核(硬件隔离)；Firecracker 125ms启动与容器同一量级(5ms VMM+10ms加载kernel+80ms guest boot+30ms init)；QEMU 200万行vs Firecracker 5万行Rust；Kata Containers=OCI接口+microVM隔离
provenance:
  extracted: 0.80
  inferred: 0.18
  ambiguous: 0.02
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# 容器 vs microVM

容器的 Namespace 隔离共享内核（单点故障），microVM 用硬件虚拟化独立内核（硬件隔离）。这是两种根本不同的隔离模型——不是"谁更好"，而是"信任边界不同"。

## 核心观点

- **容器共享内核 vs microVM独立内核**：容器进程与宿主机共享内核，300+syscall中不少能搞崩机器；microVM有自己的内核，攻击面限制在KVM ~5万行代码。
- **Firecracker 125ms启动与容器同一量级**：VMM初始化~5ms + 加载kernel~10ms + guest kernel boot~80ms + init~30ms = ~125ms。Docker冷启动~300ms，镜像缓存~100ms，crun~50ms。
- **Firecracker用Rust是因为安全**：内存安全 + 更少代码 = 更小攻击面。unsafe代码约占总代码2%，限于KVM ioctl和MMIO映射。
- **Kata Containers = OCI容器接口 + microVM隔离**：外部看起来是容器，内部是VM。
- **VM exit代价~1-5μs**：对高频小包场景（Redis）影响显著。

## 隔离模型对比

| 维度 | 容器 (Namespace) | microVM (KVM) |
|------|-------------------|----------------|
| **隔离方式** | 内核Namespace视图隔离 | 硬件虚拟化（VT-x/AMD-V） |
| **内核** | 共享宿主机内核 | 独立Guest内核 |
| **攻击面** | 内核syscall路径数百万行 | KVM ~5万行 |
| **故障传播** | 容器bug可影响宿主机 | VM故障不影响宿主机 |
| **启动时间** | 50-300ms | 125ms (Firecracker) |
| **性能损耗** | 低（共享内核无虚拟化开销） | VM exit ~1-5μs |
| **适用场景** | 可信代码/企业内部 | 多租户/不可信代码 |

## Firecracker 极简设计

AWS Lambda 的 microVM。去掉QEMU中不需要的：BIOS/UEFI/ACPI/PCI/VGA/USB/audio，只保留需要的。

### 核心取舍

| QEMU保留 | Firecracker去掉 | 原因 |
|----------|-----------------|------|
| virtio-mmio | PCI总线 | 跳过PCI枚举，设备直接映射固定内存地址 |
| 串口 | VGA/USB/audio | 不需要图形和多媒体 |
| 网络设备 | 硬盘控制器的复杂模拟 | 极简IO |
| balloon driver | 大量设备模拟 | 减少攻击面 |

### virtio-mmio vs PCI

传统QEMU用virtio-pci（需PCI总线枚举），Firecracker用virtio-mmio（跳过PCI总线，设备直接映射到固定内存地址）。更简单更快。 ^[inferred]

### 代码量对比

| 项目 | 代码量 | 语言 |
|------|--------|------|
| QEMU | ~200万行 | C |
| Firecracker | ~5万行 | Rust |
| KVM | ~5万行 | C |

## Kata Containers：两种模型的桥

Kata Containers 把两种模型桥接起来：
- **外部接口**：OCI容器接口（kubectl/docker命令都能用）
- **内部隔离**：microVM（独立内核+硬件虚拟化）
- **优势**：运维体验不变但隔离等级跃升
- **代价**：启动慢、资源开销大、VM exit性能损耗

## 启动时间拆解

| 阶段 | Firecracker | Docker (runc) | Docker (crun) |
|------|-------------|---------------|---------------|
| VMM/runtime初始化 | ~5ms | ~20ms | ~5ms |
| 加载内核/镜像 | ~10ms | ~250ms(冷) | ~250ms(冷) |
| Guest内核启动 | ~80ms | — | — |
| 应用init | ~30ms | ~30ms | ~30ms |
| **总计** | **~125ms** | **~300ms(冷)** | **~50ms(缓存)** |

Cloud Hypervisor ~100ms启动，与Firecracker同一量级。

## 安全事件驱动的思考

- CVE-2019-5736：容器内进程可通过runc逃逸到宿主机
- CVE-2022-0185：User Namespace增加内核攻击面
- 2024 eBPF逃逸漏洞

这些事件不断提醒：共享内核模型下，容器安全永远有边界。 ^[inferred]

## 未解问题

- microVM在高频小包场景（Redis/数据库）的性能量化影响？
- Kata Containers在K8s中的资源开销和调度效率？
- Firecracker与Cloud Hypervisor的长期竞争力？

## 来源

- 从零造容器系列 #10 — 容器vs microVM隔离模型对比+Firecracker拆解+启动时间对比