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
  - target: "[[concepts/linux-io-models]]"
    type: related_to
source_dir: Linux 操作系统/Linux 网络
source_files: [Linux TCP - IP协议.md, 1 Linux 常见的网络协议.md, Linux 网络三张表：ARP表, MAC表, 路由表.md, Linux 网络协议栈.md, "Linux 操作系统/Linux 驱动管理/Linux 网络设备 系统/Linux内核网络子系统.md"]
summary: Linux网络协议栈：TCP/IP四层模型简化OSI七层、三张核心表(ARP/MAC/路由)、sk_buff零拷贝数据结构、NAPI中断+轮询混合接收、数据传输中IP不变MAC逐跳变、TCP三次握手四次挥手、数据封装与分用。
provenance:
  extracted: 0.78
  inferred: 0.17
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: core
created: 2026-06-01
updated: 2026-11-11
---

# Linux网络协议栈

Linux网络协议栈是内核最庞大也是最性能关键的子系统之一，从硬件中断接收数据包到用户态socket读取，数据经历了完整的协议栈处理。TCP/IP四层模型是对OSI七层的工程简化，内核实现中sk_buff零拷贝设计和NAPI混合模式是两大核心优化。

## 核心观点

- TCP/IP四层模型是对OSI七层的工程简化：应用层/传输层/网络层/链路层，内核中每层有明确的入口函数和数据结构。
- 网络数据传输的核心规则：IP地址端到端不变（标识通信端点），MAC地址逐跳变化（标识链路层转发节点）。
- 三张核心表支撑路由决策：ARP表（IP→MAC映射）、MAC表（MAC→端口映射）、路由表（子网→下一跳映射）。三张表都是"被逼出来的"——主机多了需交换机分组（MAC表），子网多了需路由器跨网段（路由表），IP与MAC分属不同层需翻译（ARP表）。 ^[inferred]
- sk_buff 是网络栈的核心数据结构，采用[[concepts/zero-copy-memory-mapping|零拷贝]]设计——metadata与data分离、各层header用union共享空间，避免数据拷贝开销。
- NAPI 混合模式在中流量时用中断通知、高流量时自动切换到轮询，是性能与延迟的平衡方案。
- 数据封装与分用：发送端每经过一层添加该层首部，接收端每经过一层删除该层首部——分层管理的核心机制。 ^[inferred]
- TCP通过三次握手建立连接、四次挥手释放连接，连接建立及拆除至少7次通信，成本较高。

## 关键细节

### TCP/IP 四层模型与内核入口

| 层次 | 协议 | 内核入口函数 | 关键数据结构 |
|------|------|-------------|-------------|
| 应用层 | HTTP/FTP/DNS/SSH/SMTP等 | socket API (sys_sendmsg/sys_recvmsg) | socket, msghdr |
| 传输层 | TCP/UDP | tcp_v4_rcv / udp_rcv | tcphdr, udphdr |
| 网络层 | IP/ICMP/IGMP/ARP | ip_rcv | iphdr, arphdr |
| 链路层 | Ethernet/PPP/WiFi/LACP | netif_receive_skb | ethhdr |

### 三张核心表

**ARP表**：
- 功能：IP地址 → MAC地址映射
- 维护方式：动态学习（ARP请求/响应） + 静态配置
- 表项类型：S（静态配置）、D（动态学习，有老化时间）、I（接口本身的ARP表项）
- 缓存位置：`/proc/net/arp`，查看命令：`arp -a` 或 `ip neigh show`
- 老化机制：表项达到老化时间自动删除，再次通信时由ARP协议重新添加
- 请求广播、响应单播

**MAC表（转发表）**：
- 功能：MAC地址 → 端口映射（交换机/网桥使用）
- 维护方式：从入帧源MAC动态学习，空表时广播，收到响应后记录映射
- 作用范围：仅在二层设备（交换机）上使用，主机不维护MAC表
- 老化机制：动态更新，设备换端口或网卡后旧记录超时自动清除

**路由表**：
- 功能：子网 → 下一跳映射
- 查找规则：最长前缀匹配（LPM）
- CIDR表示：子网掩码用前缀长度表示，如 `192.168.0.0/24`
- 表项分类：静态路由（手动添加/直连路由）、动态路由（路由协议自动获取）
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

### 各节点视角的传输模型

从不同设备的视角理解数据包转发：

- **电脑视角**：通过子网掩码判断是否同子网 → 同子网ARP获取对方MAC → 不同子网ARP获取网关MAC → 发包
- **交换机视角**：收到包查MAC表 → 查到映射从指定端口发 → 查不到广播所有端口
- **路由器视角**：收到包查路由表 → 查到映射从指定端口发 → 查不到返回路由不可达

### 子网判断规则

判断两个IP是否在同一子网：
```
(IP1 & netmask) == (IP2 & netmask) → 同一子网（直连可达）
(IP1 & netmask) != (IP2 & netmask) → 不同子网（需路由器转发）
```

同一子网内直接ARP获取对方MAC地址；不同子网则ARP获取网关MAC，由网关转发。默认网关是主机配置的一个IP地址，用于跨子网通信时发送目标。

### ICMP 与网络诊断

| 类型 | 说明 | 典型用途 |
|------|------|----------|
| Echo 8/0 | 回显请求/响应 | ping连通性检测 |
| Unreachable 3 | 目的不可达 | 路由/端口不可达报告 |
| Time Exceeded 11 | TTL超时 | traceroute路径追踪 |
| Redirect 5 | 路由重定向 | 更优路径通知 |

### IP头部关键字段

| 字段 | 说明 |
|------|------|
| 源/目的地址 | 32位IPv4地址，端到端不变 |
| TTL | 生存时间，每经一跳减1，为0时丢弃 |
| Protocol | 上层协议号（TCP=6, UDP=17, ICMP=1, IGMP=2） |
| Flags | 分片控制（DF位禁止分片） |

当包长度 > MTU（通常1500字节）时，IP层自动分片；若设置DF标志且超MTU，则发送ICMP不可达报文并丢弃。

### TCP连接管理

**三次握手（建立连接）**：
```
Client → Server: SYN (seq=x)           — Client进入SYN_SENT
Server → Client: SYN+ACK (seq=y, ack=x+1) — Server进入SYN_RCVD
Client → Server: ACK (ack=y+1)          — 双方进入ESTABLISHED
```
握手过程中协商MSS（最大报文段长度），SYN报文中携带。三次握手完成两个功能：双方确认对方已准备好、双方完成初始SN序列号协商。

**四次挥手（释放连接）**：
```
主动方 → 被动方: FIN              — 主动方进入FIN_WAIT_1
被动方 → 主动方: ACK              — 被动方进入CLOSE_WAIT，主动方进入FIN_WAIT_2
被动方 → 主动方: FIN+ACK          — 被动方进入LAST_ACK
主动方 → 被动方: ACK              — 主动方进入TIME_WAIT，等待2MSL后关闭
```

四次挥手的原因：被动方收到FIN时可能还有数据未发完，只能先回ACK，发完数据后再发FIN。而三次握手中Server的ACK和SYN可合二为一（中间无其他报文需发送）。 ^[inferred]

TIME_WAIT等待2MSL的原因：确保被动方能收到最终ACK（若丢失可重传），且防止旧连接的失效报文出现在新连接中。 ^[inferred]

### 数据封装与分用

数据封装和分用是TCP/IP分层管理的核心机制：

- **封装（发送）**：数据每经过一层添加该层首部——应用数据 → TCP/UDP头（含16位端口号）→ IP头（含8位协议域）→ 以太网帧头（含16位类型域）
- **分用（接收）**：接收端每经过一层删除对应首部，根据首部中的协议标识交给上层处理
- 各层首部中的协议标识：传输层用端口号、网络层IP首部用协议域（TCP=6/UDP=17/ICMP=1/IGMP=2）、链路层以太网帧首部用类型域（IPv4/ARP/IPv6）
- 分层管理的好处：各层内部设计可自由改动，只需保持层间接口不变

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

各层通过修改header指针而非拷贝数据来"添加"或"剥离"协议头部，实现了真正的零拷贝。详细的skb操作（alloc_skb/skb_put/skb_push/skb_pull）见 [[summaries/linux-network-protocol-stack-impl]]。

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

这与 [[concepts/linux-interrupt-system]] 中的 softirq 机制紧密关联，NET_RX_SOFTIRQ 是 NAPI 触发 softirq 的入口。NAPI的接收模型与 [[concepts/linux-io-models]] 中的I/O模型理念相通。 ^[inferred]

### 设备抽象层：net_device 与驱动 API

协议栈与硬件之间还有一层"网络设备抽象"，是网卡驱动实际面对的对象（详见 [[summaries/linux-network-device-subsystem]]）：

| 对象 | 作用 |
|---|---|
| `net_device` | 所有网卡（物理/虚拟/lo）的统一抽象：名称、MAC、MTU、链路状态、统计 |
| `net_device_ops` | 硬件操作回调集，发包入口是 `ndo_start_xmit` |
| `napi_struct` | NAPI 实例（轮询回调 + budget） |
| `sk_buff_head` | skb 双向链表头，与 sk_buff 前两成员对齐，`qlen` + 自旋锁 |

驱动侧 API 分四组：分配注册（`alloc_etherdev`/`register_netdev`）、队列与链路（`netif_start_queue`/`netif_carrier_on`）、NAPI（`netif_napi_add`/`napi_schedule`/`napi_complete_done`）、收包交栈（`eth_type_trans` → `netif_receive_skb`）。四层架构（用户态接口 / 协议栈 / 设备抽象 / 硬件适配）即由此层划分。^[inferred]

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

### 协议选择与常用端口

| 需求 | 推荐协议 |
|------|----------|
| 可靠性优先 | TCP |
| 实时性优先 | UDP |
| 多播场景 | UDP + IGMP |
| 网络诊断 | ICMP |

常用端口参考：DNS(UDP 53)、HTTP(TCP 80)、HTTPS(TCP 443)、SSH(TCP 22)、DHCP(UDP 67/68)、NTP(UDP 123)。

## 未解问题

- eBPF/XDP 在网络栈中的位置——在 skb 创建之前介入，理论上可以跳过大部分协议栈处理。 ^[inferred]
- TCP拥塞控制算法的选择对协议栈性能的影响，来源中未深入展开。 ^[ambiguous]
- LACP（链路聚合控制协议）在链路层与内核 Bonding 模块的关系——LACP是802.3ad标准协议，内核 bond_3ad.c 负责实现，可通过 dynamic debug 开启调试日志排查聚合异常。 ^[inferred]
- SCTP（流控制传输协议）在电信场景的多流可靠传输应用，来源中仅简略提及。 ^[inferred]


## 延伸阅读

实操指南：[[skills/linux-network-debugging]]

综合分析：[[synthesis/linux-kernel-subsystem-interactions]], [[synthesis/virtio-architecture-evolution]]

## 来源

- [[summaries/linux-network-protocol-stack-impl]] — 网络协议栈实现细节
- [[summaries/linux-softirq-detail]] — NET_RX_SOFTIRQ与NAPI的关系
- [[summaries/kernel-bonding-debug-log]] — Bonding 调试日志开启方法
