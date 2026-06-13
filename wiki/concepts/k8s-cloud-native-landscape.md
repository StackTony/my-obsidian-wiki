---
title: 云原生技术全景导航
category: concepts
tags: [云原生, Kubernetes, 容器, 全景图, 网络, 安全]
aliases: [云原生导航, Cloud Native Landscape, K8s全景]
summary: 云原生技术领域导航枢纽：5个子领域（K8s核心/容器运行时/网络/C安全/可观测）+ 4条Linux→云原生映射 + 3个核心矛盾 + 与Linux OS/AI的边界
source_dir: 云原生
source_files: []
provenance:
  extracted: 0.10
  inferred: 0.85
  ambiguous: 0.05
base_confidence: 0.55
lifecycle: draft
lifecycle_changed: 2026-06-13
tier: core
created: 2026-06-13
updated: 2026-06-13
relationships:
  - target: "[[concepts/k8s-architecture]]"
    type: related_to
  - target: "[[concepts/container-runtime-deep-dive]]"
    type: related_to
  - target: "[[concepts/k8s-networking]]"
    type: related_to
  - target: "[[concepts/k8s-security]]"
    type: related_to
  - target: "[[concepts/linux-namespace-cgroups]]"
    type: related_to
  - target: "[[concepts/linux-os-virtualization-landscape]]"
    type: related_to
  - target: "[[synthesis/cloud-native-infrastructure-landscape]]"
    type: extends
  - target: "[[concepts/llm-observability]]"
    type: related_to
---

# 云原生技术全景导航

云原生是**Linux内核特性→容器运行时→K8s编排**的三层架构体系。本页是云原生5个子领域的导航枢纽，帮助读者快速定位知识并理解Linux→云原生的映射关系和领域核心矛盾。

与 [[synthesis/cloud-native-infrastructure-landscape|云原生基础设施全景]] 互补——那个页面侧重三层架构的整合分析，本页侧重导航、映射和矛盾。

## 树状导航图

```
云原生技术
├── K8s 核心架构（4条）
│   ├── [[concepts/k8s-architecture|K8s架构]]              — 声明式API+协调循环+Pod/Deployment/Service
│   ├── [[concepts/k8s-networking|K8s网络]]                — 四层模型+五大CNI+iptables→IPVS→eBPF演进
│   ├── [[concepts/k8s-security|K8s安全]]                  — 五维度加固+RBAC+NetworkPolicy+PSS
│   └── [[concepts/k8s-cni-comparison|CNI对比]]            — Flannel/Calico/Cilium/Weave/Kube-router选型
│
├── 容器运行时（6条）
│   ├── [[concepts/container-runtime-deep-dive|容器运行时深度解析]] — 拼装(8种Namespace+PID1陷阱+OCI规范)
│   ├── [[concepts/cgroups-v2-deep-dive|Cgroups v2]]       — 统一层级+memory三道防线+PSI压力指标
│   ├── [[concepts/overlayfs-container-images|OverlayFS+镜像]] — 联合挂载+Copy-on-Write+overlay2驱动
│   ├── [[concepts/seccomp-capabilities|Seccomp+Capabilities]] — syscall拦截+权限拆分=纵深防御
│   ├── [[concepts/container-vs-microvm|容器vs microVM]]  — 共享内核vs独立内核+Firecracker 125ms
│   └── [[concepts/container-network-benchmarking|容器网络实测]] — veth吞吐-20%/macvlan近裸机/eBPF不受规则影响
│
├── 可观测（1条）
│   └── [[concepts/prometheus-architecture|Prometheus]]     — Pull模型+ServiceMonitor+Histogram vs Summary
│
├── 实体（2条）
│   ├── [[entities/containerd-runtime|containerd]]          — K8s≈Nova/containerd≈libvirtd/runc≈QEMU类比
│   └── [[entities/runc-oci-reference|runc]]                — nsenter C代码+三次clone+两阶段init
│
├── 摘要（3条）
│   ├── [[summaries/k8s-terminology-cheatsheet|K8s术语速查]] — 13类核心术语中文速查
│   ├── [[summaries/k8s-official-architecture|K8s官方架构]] — 控制面+数据面+四种变体
│   └── [[summaries/k8s-alibaba-cloud-principles|阿里云K8S原理]] — 网络三铁律+CNI三强+Service Mesh+GitOps
│
├── 技巧（2条）
│   ├── [[skills/k8s-security-hardening|K8s安全加固]]        — RBAC+NetworkPolicy+PSS+Secret加密实操
│   └── [[skills/container-network-benchmarking-skill|容器网络测试]] — iperf3+sockperf方法论+六种方案实测
│
└── 综合（1条已有）
    └── [[synthesis/cloud-native-infrastructure-landscape|基础设施全景]] — 三层架构：内核→运行时→编排+可观测
```

## Linux→云原生核心映射关系

云原生不是发明——是**Linux内核特性的拼装**。以下4条核心映射连接 Linux OS 和云原生两个领域：

| # | Linux内核特性 | 云原生映射 | 映射机制 |
|---|-------------|-----------|----------|
| 1 | **Namespace (8种)** → **容器视图隔离** | PID/Net/Mount/IPC/UID/UTS/Cgroup/Time→容器进程看不到宿主 | 每个容器进程在自己的Namespace中运行，看到独立的PID 1、独立网络栈、独立文件系统 |
| 2 | **Cgroups** → **容器资源限制** | cpu.max/weight+memory low/high/max→Pod resource requests/limits | Cgroups v2三道防线直接映射为K8s QoS等级（Guaranteed/Burgetable/BestEffort） |
| 3 | **OverlayFS** → **容器镜像存储** | 联合挂载+Copy-on-Write→镜像层叠+运行时层 | 镜像每层是OverlayFS的lowerdir，容器运行时修改写入upperdir，base镜像只读共享 |
| 4 | **Seccomp+Capabilities** → **容器安全防线** | syscall过滤+权限拆分→Pod Security Standards restricted | Seccomp阻止危险syscall、Capabilities去掉多余权限、K8s PSS把这两者强制标准化 |

这4条映射揭示：**容器 = 拼装而非虚拟化**——共享内核但用4道防线隔离视图、资源、存储和安全。^[inferred]

### 映射与虚拟化的对比

```
┌──────────────────────────────────────────────────┐
│ 容器路径（共享内核）                               │
│ Namespace → 视图隔离                              │
│ Cgroup    → 资源限制                              │
│ OverlayFS → 存储分层                              │
│ Seccomp   → syscall过滤                           │
│ 结果：快(125ms级)但不安全(共享内核)               │
├──────────────────────────────────────────────────┤
│ VM路径（独立内核）                                 │
│ EPT/NPT   → 内存隔离                              │
│ virtio    → IO隔离                                │
│ vCPU      → CPU隔离                               │
│ VGIC      → 中断隔离                              │
│ 结果：安全(独立内核)但慢(虚拟化开销)             │
├──────────────────────────────────────────────────┤
│ microVM路径（Firecracker）                         │
│ KVM最小化 → 125ms启动+硬件级隔离                  │
│ 结果：尝试同时获得容器级性能+VM级隔离             │
└──────────────────────────────────────────────────┘
```

## 三个核心矛盾

| # | 矛盾 | 左侧 | 右侧 | 典型权衡 |
|---|------|------|------|----------|
| 1 | **共享 vs 独立内核** | 容器共享内核——快但一个内核漏洞全部沦陷 | VM/microVM独立内核——安全但有虚拟化开销 | 微服务→容器(性能优先)；安全合规→VM(隔离优先)；Firecracker尝试两头兼得 |
| 2 | **声明式 vs 命令式** | K8s声明式API——"告诉系统你想要什么"让系统自动收敛 | 传统命令式运维——"告诉系统做什么"每步手动控制 | 声明式适合弹性伸缩和自愈；命令式适合精确控制和紧急排障 |
| 3 | **服务网格 vs 不侵入** | Service Mesh(istio/Cilium)——透明流量管理+可观测+安全但引入sidecar开销 | 不侵入——应用代码自己处理网络但运维无统一控制面 | 大规模多服务→Service Mesh(统一治理)；小规模单服务→不侵入(避免开销) |

这些矛盾与 Linux 虚拟化的矛盾（性能vs隔离、通用vs专用、硬件vs软件、完整vs增量）形成映射：容器vs VM的"共享vs独立内核"是"性能vs隔离"的云原生版本。^[inferred]

## 与 Linux OS 和 AI 的边界

### 与 Linux OS 的边界

云原生的底层就是 Linux 内核特性——理解云原生必须先理解4个内核原语：

- [[concepts/linux-namespace-cgroups|Namespace+Cgroups]] — 容器隔离的内核基础
- [[concepts/cgroups-v2-deep-dive|Cgroups v2]] — 资源限制的内核实现
- [[concepts/overlayfs-container-images|OverlayFS]] — 镜像存储的内核基础
- [[concepts/seccomp-capabilities|Seccomp+Capabilities]] — 安全防线的内核实现

这条边界在 [[concepts/linux-os-virtualization-landscape|Linux OS/虚拟化全景]] 的"与云原生的边界"章节中也有描述。

### 与 AI 的边界

云原生和AI的交叉点是**LLM推理服务化**——K8s编排推理引擎：

```
云原生(K8s编排)          AI(LLM推理)
┌──────────────┐        ┌──────────────┐
│ Deployment   │ ────→  │ 推理引擎部署   │
│ Service      │ ────→  │ 推理服务入口   │
│ HPA/VPA     │ ────→  │ 弹性伸缩      │
│ Prometheus   │ ────→  │ LLM可观测     │
│ Istio/Cilium│ ────→  │ 流量管理+安全  │
└──────────────┘        └──────────────┐
```

AI侧详见：[[concepts/llm-serving-infrastructure|推理服务化]]、[[concepts/llm-observability|LLM可观测性]]、[[concepts/llm-gateway|大模型网关]]

## 未解问题

- Service Mesh的sidecar开销是否在大规模场景下可接受？Istio 1ton开销约2-5ms P99延迟 ^[ambiguous]
- Cilium能否真正替代iptables成为K8s网络和数据面的统一方案？取决于eBPF内核版本兼容性 ^[inferred]
- containerd+shim的隔离性是否足够？还是需要走向microVM隔离（Kata Containers）？^[inferred]

## 来源

- [[synthesis/cloud-native-infrastructure-landscape]] — 三层架构整合分析
- [[concepts/linux-namespace-cgroups]] → 容器隔离（Linux→云原生映射）
- [[concepts/k8s-architecture]] → [[concepts/k8s-networking]] → [[concepts/k8s-security]] — K8s三大核心
