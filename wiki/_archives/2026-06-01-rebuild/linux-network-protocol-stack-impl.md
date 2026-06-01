---
title: Linux 网络协议栈实现
created: 2026-06-01
updated: 2026-06-01
tags: [linux, kernel, network, tcp, ip, sk_buff, protocol-stack]
category: summaries
source_dir: Linux 操作系统/Linux 网络
source_files: [Linux 网络协议栈.md]
summary: Linux网络协议栈收发路径、sk_buff零拷贝机制与NAPI接收模型
base_confidence: 0.7
lifecycle: draft
lifecycle_changed: "2026-06-01"
tier: supporting
---

# Linux 网络协议栈实现

Linux 网络协议栈从 Socket API 到物理层，构成完整的收发路径。理解其数据结构与流程，是网络性能分析的基础。

## 发送路径

### 应用层 → 传输层

Socket 是应用与内核协议栈的接口。应用调用 send/write 时：
1. `sock_sendmsg` 获取 sock 结构，创建 message header
2. 根据协议类型调用相应发送函数：
   - TCP: `tcp_sendmsg` — 检查连接状态，获取 MSS，创建 sk_buff，从用户空间拷贝数据，构造 TCP header，计算 checksum 和 sequence number
   - UDP: `udp_sendmsg` — 封装 UDP 数据报

### IP 网络层

`ip_queue_xmit` 处理：
1. 检查路由信息（无则用 `ip_route_output` 选择）
2. 填充 IP header（版本、长度、TOS 等）
3. 若报文长度 > MTU 且 GSO 长度为零，调用 `ip_fragment` 分片；若设置 DF 标志则发送 ICMP 目的不可达并丢弃
4. `ip_finish_output2` 设置链路层报头（有缓存则拷贝，无则 ARP 获取）

### 链路层 → 物理层

Network Device 抽象层调用具体驱动的发送函数。物理层通过 DMA 将数据拷贝到内部 RAM，加入以太网协议相关 header（IFG、前导符、CRC），采用 CSMA/CD 发送。发送完成后网卡中断通知 CPU，驱动删除 skb。

## 接收路径

### 物理层 → 链路层

1. 网卡收到数据帧，DMA 传送到 rx_ring
2. 网卡中断，处理程序分配 sk_buff，从 I/O 端口拷贝数据，提取信息设置 skb->protocol
3. 发出 NET_RX_SOFTIRQ 软中断
4. NAPI 机制：驱动调用 `netif_rx_schedule`，`net_rx_action` 关中断获取 rx_ring 所有包，删除后进入 `netif_receive_skb`

### 网络层

`ip_rcv` 处理：
1. checksum 检查，必要时 IP defragment
2. Pre-routing netfilter hook
3. `ip_rcv_finish` 调用 `ip_route_input` 路由判断：
   - 发本机 → `ip_local_deliver` → 可能 de-fragment → 按协议调用 tcp_v4_rcv/udp_rcv
   - 转发 → 处理 TTL → netfilter hook → IP fragmentation → `dev_queue_xmit` 回链路层

### 传输层 → 应用层

TCP: `tcp_v4_rcv` 检查 header，`_tcp_v4_lookup` 查找 socket，状态正常则 `tcp_prequeue` 放入 socket receive queue，唤醒 socket 调用 `tcp_recvmsg` 拷贝数据到用户 buffer。

UDP: `udp_recvmsg` 从 socket buffer 拷贝数据。

## sk_buff 数据结构

sk_buff 是网络栈的核心数据结构，表示一个 packet。其设计支持 **零拷贝指针操作**：

| 操作 | 作用 |
|------|------|
| `skb_put` | 向尾部添加 payload，tail 指针移动 |
| `skb_push` | 向头部添加 header，data 指针前移 |
| `skb_pull` | 从头部删除 header，data 指针后移 |

关键成员：
- `next/prev` — 链表指针
- `sk` — 关联的 socket
- `dev` — 相关设备
- `h/nh/mac` — 各协议层 header 指针
- `len/data_len` — 长度信息
- `cb[40]` — control block，各协议层保存私有信息

## Driver Queue

IP 栈与 NIC 驱动之间存在 driver queue，实现为 FIFO ring buffer，**存储 skb 指针而非数据**。IP 栈处理完毕的包加入队列，驱动取出发送。

MTU 限制：不使用 TSO/GSO 时，IP 栈发出的包长度必须小于 MTU（以太网默认 1500 bytes）。大于 MTU 则 IP fragmentation。

## IP 分片

当 payload 为 1500 bytes，MTU 为 1000 和 600 时的分片示例：
- MTU 1000：分 2 片
- MTU 600：分 3 片

分片检查 IP_DF 标志，禁止分片则发送 ICMP 报文。

## 来源

- `Linux 操作系统/Linux 网络/Linux 网络协议栈.md` — 网络路径流程与 sk_buff 结构

## 相关概念

- [[concepts/linux-network-stack]] — 网络协议栈整体架构
- [[concepts/linux-interrupt-system]] — NET_RX_SOFTIRQ 软中断
- [[summaries/linux-softirq-detail]] — 软中断在网络接收中的应用