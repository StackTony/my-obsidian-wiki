---
title: Linux网络协议栈
category: concepts
tags: [linux, 网络, TCP/IP, 内核]
aliases: [Linux TCP/IP, Linux网络栈]
relationships:
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: related_to
source_dir: Linux 操作系统/Linux 网络
source_files: [Linux TCP - IP协议.md, Linux 常见的网络协议.md, Linux 网络三张表：ARP表, MAC表, 路由表.md, Linux 网络协议栈.md]
summary: Linux网络协议栈：TCP/IP四层模型。三张核心表——ARP表(IP→MAC)、MAC表(MAC→端口)、路由表(子网→下一跳)。传输中IP不变、MAC逐跳变。sk_buff零拷贝数据结构。
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.775
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# Linux网络协议栈

## 核心观点

### TCP/IP四层模型

简化OSI七层模型为四层：

| 层次 | 协议示例 | 内核处理入口 |
|---|---|---|
| 应用层 | HTTP/FTP/SSH/DNS | Socket API |
| 传输层 | TCP/UDP | tcp_v4_rcv/udp_rcv |
| 网络层 | IP/ICMP/ARP | ip_rcv/arp_rcv |
| 链路层 | Ethernet/PPP | netif_receive_skb |

### 三张核心表

网络通信依赖三张核心表协同：

**ARP表(IP→MAC)**：
- 主机ARP缓存：IP地址到MAC地址映射
- 获取方式：广播ARP请求，目标单播响应
- 老化时间：动态表项约20分钟^[inferred]

**MAC表(MAC→端口)**：
- 交换机内部维护：MAC地址到端口映射
- 学习机制：收到帧后记录源MAC+入端口
- 转发规则：查表命中则定向转发，未命中则广播

**路由表(子网→下一跳)**：
- 路由器维护：目的网段到出口/下一跳映射
- 匹配规则：最长前缀匹配
- 类型：静态路由(手动配置)、动态路由(协议学习)

### 数据传输关键规律

**传输中IP地址不变、MAC地址逐跳变化**：

```
A → 路由器1 → 路由器2 → F
各段链路层封装：
  A→路由器1: 源MAC=A, 目MAC=路由器1
  路由器1→路由器2: 源MAC=路由器1, 目MAC=路由器2
  路由器2→F: 源MAC=路由器2, 目MAC=F
全程网络层: 源IP=A, 目IP=F (不变)
```

### 内核发送路径

```
应用层: send/write → sock_sendmsg
传输层: tcp_sendmsg → 构造TCP段 → checksum → ip_queue_xmit
网络层: ip_queue_xmit → 路由查找 → 填充IP头 → ip_finish_output2
链路层: neigh_resolve_output → ARP获取MAC → dev_queue_xmit
物理层: DMA拷贝到网卡 → 发送
```

### 内核接收路径

```
物理层: 网卡收到帧 → DMA到rx_ring → 触发中断
链路层: 中断处理 → NAPI poll → netif_receive_skb
网络层: ip_rcv → checksum检查 → ip_route_input → 路由决策
        → 本机: ip_local_deliver → tcp_v4_rcv/udp_rcv
        → 转发: ip_forward → dev_queue_xmit
传输层: tcp_v4_rcv → 查socket → tcp_prequeue → receive queue
应用层: read/recvmsg → tcp_recvmsg → 拷贝到用户空间
```

### sk_buff零拷贝设计

`sk_buff`是Linux网络栈核心数据结构：

- **元数据与数据分离**：skb结构体指针指向数据区，添加/删除header只需移动指针
- **避免拷贝**：各层处理仅操作skb指针，不拷贝数据本身
- **三个队列**：struct sock的rx/tx/err队列保存skb

### NAPI中断+轮询混合

现代高性能网卡使用NAPI(New API)：

- 高负载时：中断触发后切换到poll轮询模式，批量处理多个包
- 低负载时：恢复中断模式，及时响应
- 优势：减少中断频率，提高吞吐^[inferred]

### 子网判断规则

通过子网掩码判断是否同子网：

```
源IP & 子网掩码 == 目IP & 子网掩码
  → 相等: 同子网，直接ARP获取MAC发送
  → 不等: 不同子网，发给默认网关
```

## 未解问题

- eBPF在网络栈中的hook点与性能影响？
- TCP拥塞控制算法 Cubic/BBR 的内核实现差异？

## 来源

- `raw/sources/Linux 操作系统/Linux 网络/Linux TCP - IP协议.md` — TCP/IP分层、三次握手/四次挥手、子网判断
- `raw/sources/Linux 操作系统/Linux 网络/Linux 常见的网络协议.md` — 协议表格、端口对照
- `raw/sources/Linux 操作系统/Linux 网络/Linux 网络三张表：ARP表, MAC表, 路由表.md` — 三张表原理、使用流程、跨网段通信
- `raw/sources/Linux 操作系统/Linux 网络/Linux 网络协议栈.md` — sk_buff结构、内核发送/接收路径、NAPI机制