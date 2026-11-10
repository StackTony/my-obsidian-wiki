---
title: Linux网络协议栈实现
category: summaries
tags: [linux, 内核, network, TCP, IP, sk_buff, 协议栈]
source_dir: Linux 操作系统/Linux 网络
source_files: [Linux 网络协议栈.md, Linux TCP - IP协议.md]
summary: Linux网络栈收发路径完整实现：sk_buff零拷贝数据结构贯穿全栈、NAPI中断+轮询混合接收、内核发送/接收路径每层入口函数、驱动队列与MTU分片机制。
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.775
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-11-10
---

# Linux网络协议栈实现

Linux网络协议栈的内核实现细节——从应用层socket API到物理层DMA，sk_buff贯穿全栈。

## 核心观点

### 内核发送路径

发送端从应用层到物理层的完整处理流程：

```
应用层: sock_sendmsg → tcp_sendmsg/udp_sendmsg
传输层: 构造TCP段 → 计算 checksum → ip_queue_xmit
        TCP: 检查连接状态→获取MSS→创建skb→从用户空间拷贝数据→构造TCP头→计算校验和和序号
        UDP: 封装UDP数据报 → ip_append_data
网络层: ip_route_output选择路由 → 填充IP头(TOS/TTL/版本) → 计算IP checksum
        → IP分片(若长度>MTU且GSO长度为0则ip_fragment，否则ip_finish_output2)
        → neigh_resolve_output(ARP获取下一跳MAC)
链路层: dev_queue_xmit → 驱动队列 → DMA到网卡
物理层: DMA拷贝至网卡内部RAM → 加入以太网header(前导符/IFG/CRC) → CSMA/CD发送
```

发送完成后网卡产生中断通知CPU，驱动中断处理程序删除已发送的skb。

**IP分片处理**：当报文长度大于MTU时，ip_fragment检查IP_DF标志位。若禁止分片，则调用icmp_send发送"需要分片而设置了不分片标志"的目的不可达ICMP报文，丢弃报文并返回消息过长错误码。

### 内核接收路径

接收端从物理层到应用层的完整处理流程：

```
物理层: 网卡DMA到rx_ring → 触发硬中断
链路层: ISR → alloc_skb分配skb → 从网卡I/O端口拷贝数据帧到skb缓冲区
        → 提取帧信息设置skb参数(如skb->protocol) → 调度NET_RX_SOFTIRQ
        → NAPI poll(net_rx_action) → 从rx_ring取包 → netif_receive_skb
网络层: ip_rcv → checksum检查/IP defrag → Pre-routing netfilter hook
        → ip_rcv_finish → ip_route_input路由决策
        → 本机: ip_local_deliver → 可能IP defrag合并
           → 按protocol number分发: tcp_v4_rcv(TCP)/udp_rcv(UDP)/icmp_rcv/igmp_rcv
        → 转发: ip_forward → TTL处理 → dst_input
           → Netfilter Hook → IP fragmentation → dev_queue_xmit
传输层: tcp_v4_rcv → TCP header检查 → _tcp_v4_lookup查找socket
        → 检查socket和connection状态 → tcp_prequeue放入receive queue
应用层: read/recvmsg → sys_recv → sock_recvmsg → tcp_recvmsg
        → 从socket buffer拷贝数据到user buffer
```

netif_receive_skb是链路层接收数据的最后一站，根据全局数组ptype_all和ptype_base中注册的网络层协议类型，将数据报递交给ip_rcv或arp_rcv等网络层接收函数。

### sk_buff核心结构

`sk_buff`是网络栈核心数据结构，一个skb代表一个数据包：

- **元数据与数据分离**：skb结构体指针指向数据区，各层添加/删除header只需移动指针
- **零拷贝**：各层处理仅操作skb指针，不拷贝数据本身，显著提升网络处理速度
- **Header unions**：`h`(TCP/UDP/ICMP)、`nh`(IP/ARP)、`mac`(MAC)分别指向各层header，共享内存空间
- **控制块**：`cb[40]`存储各协议层私有信息，如TCP的顺序号和帧重发状态
- **三个队列**：struct sock的rx/tx/err队列保存skb
- **路由信息**：`dst_entry *dst`指向该packet的路由目的结构

**skb主要操作**：
- `alloc_skb(len, GFP_KERNEL)` — 分配skb
- `skb_put(skb, user_data_len)` — 添加payload
- `skb->push` — 添加protocol header（向下扩展空间）
- `skb->pull` — 删除header（回收空间）

### 驱动队列与MTU

IP栈与NIC驱动之间存在驱动队列（driver queue）：

- **实现**：FIFO ring buffer，固定大小，保存skb指针（非数据本身）
- **MTU限制**：以太网默认MTU=1500字节，支持巨帧时可达9000字节；非TSO/GSO情况下IP栈发到队列的包长度必须小于MTU
- **分片触发**：应用写入2000字节到TCP socket → IP栈创建两个IP packet保持每个≤1500字节 → IP fragmentation
- **输入**：本机应用产生的包或进入本机又被路由转发的包

### NAPI混合接收模式

- 高负载时：中断触发后切换到poll轮询模式，关闭中断，批量处理rx_ring中多个包
- 低负载时：恢复中断模式及时响应
- 驱动队列：FIFO环形缓冲区存skb指针（不是数据），MTU决定最大包大小
- NAPI与传统的netif_rx两种通知内核方式并存

NAPI依赖 [[concepts/linux-interrupt-system]] 中的NET_RX_SOFTIRQ软中断机制。网络收发的I/O模型理念与 [[concepts/linux-io-models]] 相通。 ^[inferred]

## 来源

- [[concepts/linux-network-stack]] — 网络栈整体框架
- [[concepts/linux-interrupt-system]] — NAPI依赖NET_RX_SOFTIRQ软中断
- `raw/sources/Linux 操作系统/Linux 网络/Linux 网络协议栈.md` — 内核收发路径、sk_buff结构、驱动队列
- `raw/sources/Linux 操作系统/Linux 网络/Linux TCP - IP协议.md` — TCP/IP分层模型、数据封装分用、TCP报文格式
