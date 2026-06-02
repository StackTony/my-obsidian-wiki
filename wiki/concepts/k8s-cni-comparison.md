---
title: Kubernetes CNI 插件对比
category: concepts
tags: [云原生, Kubernetes, CNI, 网络, eBPF]
aliases: [CNI对比, K8s CNI选型]
relationships:
  - target: "[[concepts/k8s-networking]]"
    type: extends
  - target: "[[concepts/container-network-benchmarking]]"
    type: related_to
  - target: "[[concepts/linux-network-stack]]"
    type: derived_from
  - target: "[[concepts/k8s-architecture]]"
    type: related_to
source_dir: Kubernetes（K8s）
source_files: [1-K8s 核心术语速查表.md, K8s云原生-阿里云-K8S技术原理.md, Kubernetes网络/K8s网络整体架构-腾讯云.md]
summary: 五大CNI对比：Flannel VXLAN(简单小集群)/Calico BGP(大规模高性能)/Cilium eBPF(现代首选,可替换kube-proxy)/Weave Net(加密)/Kube-router(简化BGP)；iptables O(n)是大规模杀手→IPVS或Cilium eBPF是出路
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# Kubernetes CNI 插件对比

CNI（Container Network Interface）是 K8s 定义的网络标准，插件实现具体方案。选型取决于三个维度：网络可靠性、性能、安全。没有一个"最佳"方案——**选型先确认瓶颈再选工具**。 ^[inferred]

## 核心观点

- **iptables O(n) 是大规模集群的性能杀手**：500 Service → 1000-2000条 iptables 规则 → 规则数增长后吞吐和P99严重恶化。IPVS O(1) 和 Cilium eBPF 是出路。
- **Cilium 可完全替换 kube-proxy**：eBPF map做O(1)路由查找，跳过整个netfilter栈。支持L3-L7 NetworkPolicy（HTTP方法级别过滤）。
- **Flannel VXLAN 有 MTU 损失**：50字节VXLAN头封装。简单但有性能开销。
- **Calico BGP 近裸机性能**：纯L3路由无封装。但跨子网需要IP-in-IP或VXLAN隧道。

## 五大 CNI 详解

### Flannel — 简单Overlay

- **核心技术**：VXLAN隧道封装（"包中包"）
- **优势**：配置简单，适合入门小集群
- **劣势**：VXLAN封装开销、MTU损失（50字节）、不支持NetworkPolicy
- **组件**：依赖etcd管理网络状态
- **健康检查端口**：8285

### Calico — BGP纯路由

- **核心技术**：BGP协议，纯L3路由
- **优势**：近裸机性能、支持NetworkPolicy、可扩展到大规模
- **劣势**：跨子网需要IP-in-IP隧道；BGP路由表规模需关注
- **组件**：Felix（每Node代理配置路由+iptables/eBPF策略）+ BIRD（每Node BGP客户端广播路由）
- **适用**：大规模高性能生产集群

### Cilium — eBPF下一代

- **核心技术**：eBPF程序注入内核钩子
- **优势**：可替换kube-proxy、L3-L7 NetworkPolicy（HTTP GET vs DELETE）、微秒级处理延迟
- **劣势**：需要较新内核版本（4.10+）、学习曲线较高
- **特性**：多协议兼容（BGP/IP-in-IP/HTTP/gRPC）、Prometheus/Grafana集成
- **适用**：现代生产首选

### Weave Net — 加密Overlay

- **核心技术**：VXLAN/UDP Overlay + 自动节点发现 + 加密通信
- **优势**：安全场景友好、自动发现
- **劣势**：封装开销
- **适用**：安全要求高的场景

### Kube-router — 简化BGP

- **核心技术**：BGP协议
- **优势**：架构简化、灵活拓扑（flat/mesh/point-to-point）
- **健康检查端口**：20244

## 性能对比

| 方案 | 与裸机差距 | iptables规则影响 |
|------|-----------|----------------|
| Flannel VXLAN | 封装开销+MTU损失 | 不解决 |
| Calico BGP | 近裸机 | 用iptables/eBPF策略 |
| Cilium eBPF | 微秒级额外开销 | 几乎不受规则数影响 |
| iptables 1000规则 | 吞吐降~8% | — |
| iptables 10000规则 | 吞吐降~24% | — |

详见 [[concepts/container-network-benchmarking]] 的实测数据。

## iptables → IPVS → eBPF 演进路径

| 阶段 | 技术 | 复杂度 | 规则规模影响 | K8s组件 |
|------|------|--------|-------------|---------|
| 第一代 | iptables | O(n) | 规则增长→P99暴涨 | kube-proxy iptables mode |
| 第二代 | IPVS | O(1) | 不受影响 | kube-proxy IPVS mode |
| 第三代 | eBPF | O(1) | 几乎不受影响 | Cilium替换kube-proxy |

**Cilium eBPF 替换 kube-proxy 的理由**：官方文档指出kube-proxy是可选的——当CNI插件提供等效Service流量代理行为时。Cilium用eBPF map做O(1)路由查找，跳过整个netfilter栈。 ^[inferred]

## 选型决策树

```
集群规模?
├── < 50 Node → Flannel（简单够用）
├── 50-500 Node → Calico（BGP高性能）
└── > 500 Node → Cilium（eBPF+可替换kube-proxy）

安全要求?
├── NetworkPolicy L3/L4 → Calico/Cilium
├── NetworkPolicy L7 → Cilium
└── 加密通信 → Weave Net

跨子网?
├── 同子网 → Calico BGP直连
└── 跨子网 → Calico IP-in-IP 或 Cilium
```

## 来源

- [[summaries/k8s-terminology-cheatsheet]] — CNI术语定义
- [[summaries/k8s-alibaba-cloud-principles]] — iptables/IPVS/eBPF对比
- 腾讯云K8s网络架构 — 四层模型+五CNI详解