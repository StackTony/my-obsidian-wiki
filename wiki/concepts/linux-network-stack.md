---
title: Linux网络协议栈
category: concepts
tags: [linux, 内核, 网络, TCP, IP, sk_buff]
aliases: [Linux网络栈, TCP/IP协议栈, sk_buff, NAPI]
relationships:
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: related_to
  - target: "[[concepts/linux-virtio-architecture]]"
    type: uses
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
source_dir: Linux 操作系统/Linux 网络
source_files: [Linux TCP - IP协议.md, Linux 常见的网络协议.md, Linux 网络三张表：ARP表, MAC表, 路由表.md, Linux 网络协议栈.md]
summary: Linux网络协议栈：TCP/IP四层模型简化OSI七层、三张核心表(ARP/MAC/路由)、sk_buff零拷贝数据结构、NAPI中断+轮询混合接收、数据传输中IP不变MAC逐跳变。
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: core
created: 2026-06-01
updated: 2026-06-01
---

# Linux网络协议栈

Linux网络协议栈是内核最庞大也是最性能关键的子系统之一，从硬件中断接收数据包到用户态socket读取，数据经历了完整的协议栈处理。TCP/IP四层模型是对OSI七层的工程简化，内核实现中sk_buff零拷贝设计和NAPI混合模式是两大核心优化。

## 核心观点

- TCP/IP四层模型是对OSI七层的工程简化：应用层/传输层/网络层/链路层，内核中每层有明确的入口函数和数据结构。
- 网络数据传输的核心规则：IP地址端到端不变（标识通信端点），MAC地址逐跳变化（标识链路层转发节点）。
- 三张核心表支撑路由决策：ARP表（IP→MAC映射）、MAC表（MAC→端口映射）、路由表（子网→下一跳映射）。
- sk_buff 是网络栈的核心数据结构，采用零拷贝设计——metadata与data分离、各层header用union共享空间，避免数据拷贝开销。
- NAPI 混合模式在中流量时用中断通知、高流量时自动切换到轮询，是性能与延迟的平衡方案。

## 关键细节

### TCP/IP 四层模型与内核入口

| 层次 | 协议 | 内核入口函数 | 关键数据结构 |
|------|------|-------------|-------------|
| 应用层 | HTTP/FTP/DNS等 | socket API (sys_sendmsg/sys_recvmsg) | socket, msghdr |
| 传输层 | TCP/UDP | tcp_v4_rcv / udp_rcv | tcphdr, udphdr |
| 网络层 | IP/ICMP/ARP | ip_rcv | iphdr, arphdr |
| 链路层 | Ethernet | netif_receive_skb | ethhdr |

### 三张核心表

**ARP表**：
- 功能：IP地址 → MAC地址映射
- 维护方式：动态学习（ARP请求/响应） + 静态配置
- 缓存时间：可达性确认后保持，超时后重新请求
- 查看命令：`arp -a` 或 `ip neigh show`

**MAC表（转发表）**：
- 功能：MAC地址 → 端口映射（交换机/网桥使用）
- 维护方式：从入帧源MAC动态学习
- 作用范围：仅在二层设备（交换机）上使用，主机不维护MAC表

**路由表**：
- 功能：子网 → 下一跳映射
- 查找规则：最长前缀匹配（LPM）
- 查看/配置命令：`ip route show` / `route add`

### 数据传输规则：IP不变、MAC逐跳变

这是理解网络数据包转发最关键的原则：

- **IP地址**：在整个传输路径上端到端不变（除非经过NAT），标识通信的端点（源和目的）
- **MAC地址**：每经过一个路由器（一层转发节点）就变化一次，标识当前链路段的源和目的

示例：A(192.168.1.1) → R1 → R2 → B(10.0.0.1)
- IP始终是：src=192.168.1.1, dst=10.0.0.1
- A→R1段：MAC src=A的MAC, MAC dst=R1的MAC
- R1→R2段：MAC src=R1的MAC, MAC dst=R2的MAC
- R2→B段：MAC src=R2的MAC, MAC dst=B的MAC

### 子网判断规则

判断两个IP是否在同一子网：
```
(IP1 & netmask) == (IP2 & netmask) → 同一子网（直连可达）
(IP1 & netmask) != (IP2 & netmask) → 不同子网（需路由器转发）
```

同一子网内直接ARP获取对方MAC地址；不同子网则ARP获取网关MAC，由网关转发。

### sk_buff 零拷贝设计

sk_buff 是网络栈最核心的数据结构，零拷贝设计体现在：

**metadata/data分离**：
- sk_buff 本身只存储元数据（指针、长度、协议类型等）
- 实际数据存储在独立的数据缓冲区中
- 各层处理只修改 sk_buff 的指针，不拷贝数据

**header unions**：
```c
sk_buff {
    union {
        tcphdr *th;    // 传输层各协议header共享空间
        udphdr *uh;
        icmphdr *icmph;
        ...
    } h;
    union {
        iphdr *iph;    // 网络层各协议header共享空间
        arphdr *arph;
        ...
    } nh;
    union {
        ethhdr *eth;   // 链路层header
        ...
    } mac;
}
```

各层通过修改header指针而非拷贝数据来"添加"或"剥离"协议头部，实现了真正的零拷贝。

### NAPI 混合接收模式

NAPI（New API）是 Linux 网络设备驱动的中断+轮询混合模式：

**低流量时（中断模式）**：
- 网卡收到数据包 → 触发硬中断 → ISR关闭中断 → 调度NET_RX_SOFTIRQ
- softirq中调用驱动poll方法处理收包

**高流量时（轮询模式）**：
- 中断被关闭后不再触发新中断
- softirq持续poll网卡直到队列清空或达到quota
- poll完成后重新开启中断

**优势**：低流量保持低延迟（中断），高流量避免中断风暴（轮询），自动切换无需手动调优。

这与 [[concepts/linux-interrupt-system]] 中的 softirq 机制紧密关联，NET_RX_SOFTIRQ 是 NAPI 触发 softirq 的入口。

### 内核发送与接收路径

**发送路径**：
```
用户态 sys_sendmsg → socket层封装msghdr → tcp_sendmsg封装TCP段
→ ip_queue_xmit添加IP头 → dev_queue_xmit添加MAC头 → 驱动DMA发送
```

**接收路径**：
```
网卡DMA接收 → 硬中断触发 → NAPI poll → netif_receive_skb
→ ip_rcv剥MAC头检查IP → tcp_v4_rcv剥IP头检查TCP → sock接收队列 → 用户态recv
```

## 未解问题

- eBPF/XDP 在网络栈中的位置——在 skb 创建之前介入，理论上可以跳过大部分协议栈处理。 ^[inferred]
- TCP拥塞控制算法的选择对协议栈性能的影响，来源中未深入展开。 ^[ambiguous]


## 延伸阅读

实操指南：[[skills/linux-network-debugging]]

综合分析：[[synthesis/linux-kernel-subsystem-interactions]], [[synthesis/virtio-architecture-evolution]]

## 来源

- [[summaries/linux-network-protocol-stack-impl]] — 网络协议栈实现细节
- [[summaries/linux-softirq-detail]] — NET_RX_SOFTIRQ与NAPI的关系