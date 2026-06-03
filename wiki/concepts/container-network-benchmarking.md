---
title: 容器网络性能实测
category: concepts
tags: [云原生, 容器, 网络, 性能, eBPF]
aliases: [容器网络性能, veth vs macvlan vs eBPF]
relationships:
  - target: "[[concepts/k8s-cni-comparison]]"
    type: extends
  - target: "[[concepts/k8s-networking]]"
    type: related_to
  - target: "[[concepts/linux-network-stack]]"
    type: derived_from
  - target: "[[concepts/zero-copy-memory-mapping]]"
    type: related_to
source_dir: 容器运行时/从零造容器系列
source_files: [【从零造容器】11 容器网络性能真相：veth vs macvlan vs eBPF 数据面.md]
summary: 容器网络实测数据：veth+bridge吞吐-20%/P99 4.4x；macvlan近裸机；Cilium eBPF不受iptables规则影响；P99才是真正杀人的指标；conntrack每条300字节默认65536上限→高并发表满丢包
provenance:
  extracted: 0.85
  inferred: 0.12
  ambiguous: 0.03
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# 容器网络性能实测

"P99 才是真正杀人的指标。"——平均吞吐看起来不错，但P99延迟才是在线服务真正关心的。

## 核心观点

- **veth+bridge+iptables 是 Docker 默认但性能最差**：吞吐-20%、P99延迟4.4倍（185μs vs 裸机42μs）。
- **macvlan 近裸机性能**：吞吐-1.4%、P99 58μs。但容器与宿主机不能直接通信。
- **Cilium eBPF 几乎不受 iptables 规则数影响**：10000规则下eBPF仍9.15 Gbps，iptables降至5.21 Gbps（降24%）。
- **conntrack 是性能杀手**：每条记录约300字节，默认最大65536；高并发下表满丢包。
- **Facebook Katran 用 XDP 做 L4 负载均衡**——XDP在网卡驱动层拦截，比tc更早。

## 实测性能数据

测试环境：4核 Intel Xeon E-2278G @ 3.40GHz, 32GB DDR4, Intel X550 10Gbps NIC。

| 方案 | 吞吐 | 与裸机差距 | 额外延迟 | P99延迟 | P99倍数 |
|------|------|-----------|----------|---------|---------|
| **裸机** | 9.41 Gbps | 0 | 0 | 42μs | 1x |
| **veth+bridge** | 7.52 Gbps | -20% | +18μs | 185μs | 4.4x |
| **macvlan** | 9.28 Gbps | -1.4% | +2μs | 58μs | 1.4x |
| **ipvlan** | 9.20 Gbps | -2.2% | +3μs | 62μs | 1.5x |
| **Cilium eBPF** | 9.15 Gbps | -2.8% | +5μs | 68μs | 1.6x |
| **XDP redirect** | 9.35 Gbps | -0.6% | +1μs | 46μs | 1.1x |

## iptables 规则数影响

| 规则数 | iptables吞吐 | Cilium eBPF吞吐 |
|--------|-------------|-----------------|
| 0 | 7.52 Gbps | 9.15 Gbps |
| 1000 | 6.83 Gbps | 9.15 Gbps |
| 10000 | 5.21 Gbps (-24%) | 9.15 Gbps |

**500 Service集群就有1000-2000条 iptables 规则**——规模增长后性能恶化严重。 ^[inferred]

## 各方案技术原理

### veth + bridge + iptables

包两次经过netfilter（bridge层+IP层）→ conntrack记录每条连接 → DNAT转换Service ClusterIP到Pod IP。路径最长、开销最大。

### macvlan

容器直接拥有虚拟网卡，跳过bridge/veth/NAT。性能近裸机。**限制**：容器与宿主机不能直接通信（macvlan限制）。

### ipvlan

共享MAC地址，不需要promiscuous mode。比macvlan少一个限制但性能略低。

### Cilium eBPF

eBPF map做O(1)路由查找，跳过整个netfilter栈。支持L3-L7网络策略。可完全替换kube-proxy。

### XDP (eXpress Data Path)

在网卡驱动层拦截包，比tc更早。Facebook Katran用XDP做L4负载均衡。性能最接近裸机。

## conntrack 问题

| 维度 | 数值 |
|------|------|
| 每条记录大小 | ~300字节 |
| 默认最大条目 | 65536 |
| 高并发后果 | 表满→新连接丢包 |
| Kubernetes规模 | 500 Service → 1000-2000 iptables规则 → conntrack膨胀 |

conntrack是Docker默认网络路径上的"隐形杀手"——表满后新连接直接丢包，没有错误日志。 ^[inferred]

## 测试方法论

- **iperf3**：测吞吐（TCP/UDP带宽）
- **sockperf**：测P99延迟（ping-pong模式）
- 关闭TCP offload比较公平（硬件offload掩盖软件差异）


## 延伸阅读

实操指南：[[skills/container-network-benchmarking-skill]]

## 来源

- 从零造容器系列 #11 — 六种网络方案实测数据+iptables规则影响+conntrack分析