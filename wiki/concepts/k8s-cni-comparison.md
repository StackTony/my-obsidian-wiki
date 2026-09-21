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
source_dir: 云原生/Kubernetes（K8s）
source_files: [1-K8s 核心术语速查表.md, K8s云原生-阿里云-K8S技术原理.md, Kubernetes网络/K8s网络整体架构-腾讯云.md]
  # Self learn 补充（credibility: low）
  # source_dir: Self learn/K8s和容器
  # source_files: [Cilium替代Calico实践-腾讯云.md, Cilium高性能CNI详解-博客园.md, Cilium替换KubeProxy-博客园.md]
summary: 五大CNI对比：Flannel VXLAN(简单小集群)/Calico BGP(大规模高性能)/Cilium eBPF(现代首选,可替换kube-proxy)/Weave Net(加密)/Kube-router(简化BGP)；iptables O(n)是大规模杀手→IPVS或Cilium eBPF是出路
provenance:
  extracted: 0.70
  inferred: 0.25
  ambiguous: 0.05
base_confidence: 0.72
lifecycle: draft
lifecycle_changed: 2026-09-16
tier: supporting
created: 2026-06-02
updated: 2026-09-16
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

**Cilium eBPF 替换 kube-proxy 的理由**：官方文档指出kube-proxy是可选的——当CNI插件提供等效Service流量代理行为时。Cilium用eBPF map做O(1)路由查找，跳过整个[[concepts/linux-network-stack|Linux网络协议栈]]的netfilter栈。 ^[inferred]

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


## Self learn 补充：Cilium 深度实践（2026-09-16，credibility: low）

来源：`raw/sources/Self learn/K8s和容器/`（Cilium替代Calico实践/Cilium高性能CNI详解/Cilium替换KubeProxy 三篇）。

### Cilium 组件体系

| 组件 | 角色 | 关键特性 |
|------|------|----------|
| **Cilium Operator** | 管理平面 | **不在转发/策略决策关键路径上**——即使暂时不可用，集群继续运行 |
| **Cilium Agent** | 数据平面（DaemonSet） | 管理节点 eBPF 程序、与 K8s API 同步、按需创建 DNS/Envoy、启用 Hubble 时暴露 gRPC |
| **Cilium CLI** | 诊断代理 | 检查 Agent 与 eBPF map 状态（每节点 pod 内置） |
| **CNI Plugin** | 二进制（独立于 Agent） | 通过主机文件系统 socket 与 Agent 通信 |
| **Hubble Server** | 每节点可见性 | 检索基于 eBPF 的流量数据 |
| **Hubble Relay** | 集群级聚合 | 连接所有节点 Hubble Server 的 gRPC API，提供全局视图 |
| **Hubble UI** | 可视化 | 图形化服务依赖与连接图 |

数据存储：Agent 间状态传播用 K8s CRD 或 etcd（可复用集群 etcd 或专用集群）。

### CiliumIdentity：基于标签的安全身份

这是 Cilium 高效工作的核心概念——**身份由标签决定而非 IP**：

- 共享同一组安全标签的端点共享同一身份（如两个 coredns Pod 同为 ID 9223）
- 身份对应唯一数字标识符，**eBPF 程序在数据路径中用数字 ID 做 O(1) 快速查找**
- 数据包进/出节点时，eBPF 把源/目标 IP 映射到身份 ID，再按引用 ID 的策略决定数据路径动作
- 这解决了微服务环境 IP 频繁变动的根本问题：策略跟着身份走，不跟着 IP 走 ^[inferred]

Hubble 的 Kubernetes 感知可观测性正是建立在此之上。

### 网络模式与虚拟网卡

**Overlay 封装协议选择**：

| 协议 | 头部开销 | 内核要求 | 适用 |
|------|----------|----------|------|
| VXLAN（默认） | 50 字节 | 4.9+ | 通用，兼容性优先 |
| Geneve | 可变（最小 20 字节） | 5.10+ | 高性能/自定义隧道元数据（多租户隔离） |

**Underlay 两种模式**：Native Routing（同二层网络直连，无封装，吞吐最大）与 BGP 模式（跨子网，节点跑 BGP 客户端把 Pod CIDR 发布给物理路由器）。

安装后节点新增的虚拟网卡：`cilium_net`（Pod↔节点桥接网关）、`cilium_host`（出/入节点流量的 SNAT 与策略校验点）、`cilium_vxlan`（隧道封装/解封装）、`tunl0`（ipip，默认不启用）、`lxc_health`（健康检查端点）。

### 与传统 Overlay 方案对比

| 特性 | Cilium Overlay (eBPF) | Flannel VXLAN | Calico VXLAN |
|------|----------------------|---------------|--------------|
| 封装位置 | 内核态 eBPF（TC/XDP） | 用户态 agent | 内核态 iptables |
| CPU 开销 | **低（降 40%-60%）** | 高 | 中 |
| 网络策略 | L3-L7 全栈 | 无 | L3-L4 |
| 负载均衡 | 内置（替代 kube-proxy） | 依赖 kube-proxy | 依赖 kube-proxy |
| 加密 | 内核态 WireGuard | 无 | 需配置 IPsec |
| 大规模 | 1000+ 节点/100K+ Pod | 500 节点内 | 800 节点内 |

### 替换 kube-proxy 实操（K3s 实测）

kube-proxy 承担四种流量路由：ClusterIP / NodePort / ExternalIP / LoadBalancer——Cilium 全部实现且性能更优（DSR 模式进一步降低 NodePort 延迟）。

关键步骤：
```bash
# K3s 安装时禁用 flannel/network-policy/kube-proxy/servicelb
--flannel-backend=none --disable-network-policy --disable-kube-proxy
# Cilium 安装时启用替换（strict=严格模式；disabled 默认仅集群内 ClusterIP 负载均衡）
helm install cilium cilium/cilium --set kubeProxyReplacement=strict \
  --set tunnel=disabled --set ipv4NativeRoutingCIDR=10.0.0.0/22
# 验证
kubectl -n kube-system exec ds/cilium -- cilium status | grep KubeProxyReplacement
```

验证输出显示 Socket LB Enabled、ClusterIP/NodePort/LoadBalancer/externalIPs/HostPort 全 Enabled。

**内核版本决定功能开关**（麒麟 4.19 内核实例）：Bandwidth Manager 需 5.1+、BPF host routing 需 5.10+（否则回退 Legacy iptables）、WireGuard 加密需 5.6+、IPv6 BIG TCP 需 5.19+——**内核不够新时 Cilium 部分高级功能静默降级**，装完必查 `cilium status`。 ^[inferred]

**性能实测**（Native Routing，iperf3）：VM 间 1101 MB/s vs 容器间 1104 MB/s——Cilium 转发开销接近零。连通性验证用 `cilium connectivity test`。

### Cilium L7 能力速览

网络策略四层：L3/L4（标签+协议+端口）、L7（HTTP 方法/URL 路径/header/gRPC）、FQDN（域名级，免解析 IP）、CIDR。服务网格：无 Sidecar 的 eBPF 数据平面（mTLS/故障注入/流量镜像/Gateway API 深度集成）。多集群：ClusterMesh 跨集群全局 Service（同 namespace+service 名自动合并）。

## 延伸阅读

实操指南：[[skills/container-network-benchmarking-skill]]、[[skills/k8s-network-troubleshooting]]

综合分析：[[synthesis/cloud-native-infrastructure-landscape]]

## 来源

- [[summaries/k8s-terminology-cheatsheet]] — CNI术语定义
- [[summaries/k8s-alibaba-cloud-principles]] — iptables/IPVS/eBPF对比
- 腾讯云K8s网络架构 — 四层模型+五CNI详解
- Self learn 三篇（credibility: low）：Cilium替代Calico实践-腾讯云（组件/身份/安装）、Cilium高性能CNI详解-博客园（网络模式/对比表/L7能力）、Cilium替换KubeProxy-博客园（K3s 实操）