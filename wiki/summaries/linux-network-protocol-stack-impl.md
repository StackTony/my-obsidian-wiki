---
title: Linux网络协议栈实现
category: summaries
tags: [linux, 内核, network, TCP, IP, sk_buff, 协议栈]
source_dir: Linux 操作系统/Linux 网络
source_files: [Linux 网络协议栈.md]
summary: Linux网络栈收发路径完整实现：sk_buff零拷贝数据结构贯穿全栈、NAPI中断+轮询混合接收、内核发送/接收路径每层入口函数。
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.775
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# Linux网络协议栈实现

Linux网络协议栈的内核实现细节——从应用层socket API到物理层DMA，sk_buff贯穿全栈。

## 核心观点

### 内核发送路径

```
应用层: sock_sendmsg → tcp_sendmsg/udp_sendmsg
传输层: 构造TCP段/UDP包 → checksum → ip_queue_xmit
网络层: 路由查找 → 填充IP头 → ip_finish_output2 → neigh_resolve_output(ARP获取MAC)
链路层: dev_queue_xmit → 驱动队列 → DMA到网卡
```

### 内核接收路径

```
物理层: 网卡DMA到rx_ring → 触发中断
链路层: ISR → alloc_skb → NAPI poll → netif_receive_skb
网络层: ip_rcv → checksum/defrag → 路由决策
        → 本机: ip_local_deliver → tcp_v4_rcv/udp_rcv
        → 转发: ip_forward → dev_queue_xmit
传输层: tcp_v4_rcv → 查socket → tcp_prequeue → receive queue
应用层: read/recvmsg → tcp_recvmsg → 拷贝到用户空间
```

### sk_buff核心结构

`sk_buff`是网络栈核心数据结构，一个skb代表一个数据包：
- **元数据与数据分离**：skb结构体指针指向数据区，各层添加/删除header只需移动指针
- **零拷贝**：各层处理仅操作skb指针，不拷贝数据本身
- **Header unions**：`h`(TCP/UDP)、`nh`(IP)、`mac`(MAC)分别指向各层header
- **控制块**：`cb[40]`存储各层私有数据
- **三个队列**：struct sock的rx/tx/err队列保存skb

### NAPI混合接收模式

- 高负载时：中断触发后切换到poll轮询模式，批量处理多个包
- 低负载时：恢复中断模式及时响应
- 驱动队列：FIFO环形缓冲区存skb指针（不是数据），MTU决定最大包大小

## 来源

- [[concepts/linux-network-stack]] — 网络栈整体框架
- [[concepts/linux-interrupt-system]] — NAPI依赖NET_RX_SOFTIRQ软中断
- `raw/sources/Linux 操作系统/Linux 网络/Linux 网络协议栈.md`