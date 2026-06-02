---
title: 容器网络性能测试实操
category: skills
tags: [云原生, 容器, 网络, 性能测试, iperf3]
source_dir: 容器运行时/从零造容器系列
source_files: [【从零造容器】11 容器网络性能真相：veth vs macvlan vs eBPF 数据面.md]
summary: 容器网络性能测试方法论：iperf3测吞吐+sockperf测P99+关闭TCP offload保证公平；六种方案实测：veth+bridge(-20%吞吐/4.4xP99)/macvlan(-1.4%)/ipvlan/Cilium eBPF/XDP redirect
provenance:
  extracted: 0.88
  inferred: 0.10
  ambiguous: 0.02
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# 容器网络性能测试实操

## 概述

"P99才是真正杀人的指标"——平均吞吐看起来不错但P99延迟才是在线服务真正关心的。本指南提供容器网络性能测试方法论和六种方案实测数据。

## 前置条件

- Linux主机（建议4核+10Gbps网卡）
- iperf3、sockperf工具已安装
- 了解veth/bridge/macvlan/Cilium基础概念

## 步骤

### 1. 吞吐量测试 (iperf3)

```bash
# 服务端
iperf3 -s

# 客户端（容器内或主机）
iperf3 -c <server_ip> -t 30 -i 5
```

### 2. P99延迟测试 (sockperf)

```bash
# 服务端
sockperf sr --ip <server_ip>

# 客户端
sockperf pp --ip <server_ip> -t 30 -i 5
```

### 3. 关闭TCP offload（公平对比）

```bash
# 在所有测试端关闭硬件offload
ethtool -K <interface> tso off gso off gro off lro off
```

**为什么关闭**：硬件offload掩盖软件差异，关闭后才能看到各方案的真实开销。

### 4. conntrack状态检查

```bash
# 查看conntrack条目数
conntrack -C

# 查看conntrack最大值
cat /proc/sys/net/netfilter/nf_conntrack_max

# 查看conntrack表满事件
dmesg | grep "nf_conntrack: table full"
```

## 六种方案实测数据

| 方案 | 吞吐 | P99延迟 | 配置难度 |
|------|------|---------|----------|
| 裸机基准 | 9.41 Gbps | 42μs | — |
| veth+bridge+iptables | 7.52 Gbps | 185μs | Docker默认 |
| macvlan | 9.28 Gbps | 58μs | 中 |
| ipvlan | 9.20 Gbps | 62μs | 中 |
| Cilium eBPF | 9.15 Gbps | 68μs | 高 |
| XDP redirect | 9.35 Gbps | 46μs | 高 |

### iptables规则数影响测试

```bash
# 添加1000条iptables规则测试
for i in $(seq 1 1000); do
  iptables -A FORWARD -s 10.0.0.$i -j ACCEPT
done
iperf3 -c <server_ip> -t 30

# 清除规则
iptables -F FORWARD
```

## 常见问题

| 问题 | 原因 | 解法 |
|------|------|------|
| veth吞吐低 | bridge-nf-call-iptables两次netfilter | 用IPVS或Cilium替换 |
| P99暴涨 | conntrack表满 | 增大nf_conntrack_max或用eBPF跳过 |
| macvlan宿主机不通 | macvlan限制 | 用ipvlan替代 |
| Cilium安装复杂 | 内核版本要求 | 确保4.10+内核 |

## 进阶用法

- Facebook Katran用XDP做L4负载均衡
- Cilium替换kube-proxy后用eBPF map做O(1)路由查找
- 大规模集群（>500 Node）必须用Cilium/IPVS替代iptables

## 来源

- 从零造容器系列 #11 — 六种方案实测+方法论+conntrack分析