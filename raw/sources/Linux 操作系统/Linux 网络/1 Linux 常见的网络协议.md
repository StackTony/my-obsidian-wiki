
# Linux 常用网络协议

## TCP/IP 协议族分层

| 层次  | 协议                     | 作用      |
| --- | ---------------------- | ------- |
| 应用层 | HTTP、FTP、SSH、DNS、SMTP  | 用户应用交互  |
| 传输层 | TCP、UDP                | 端到端数据传输 |
| 网络层 | IP、ICMP、IGMP、ARP       | 路由与地址解析 |
| 链路层 | Ethernet、PPP、WiFi、LACP | 物理传输    |

## TCP 传输控制协议

**特点**：面向连接、可靠传输、有序、流量控制

### 三次握手

```
Client → Server: SYN (seq=x)
Server → Client: SYN+ACK (seq=y, ack=x+1)
Client → Server: ACK (ack=y+1)
```

### 四次挥手

```
Client → Server: FIN
Server → Client: ACK
Server → Client: FIN
Client → Server: ACK
```

### 内核处理

```
发送: tcp_sendmsg → 构造TCP段 → checksum → ip_queue_xmit
接收: tcp_v4_rcv → 查找socket → tcp_prequeue → receive queue
```

**适用场景**：Web服务、文件传输、邮件


## UDP 用户数据报协议

**特点**：无连接、不可靠、低延迟、无流量控制

```
发送: udp_sendmsg → 封装UDP数据报 → ip_append_data
接收: udp_rcv → 查找socket → 接收队列
```

**适用场景**：DNS查询、视频直播、游戏、VoIP


## IP 互联网协议

**功能**：路由选择、地址标识、分片重组

### IP Header 关键字段

| 字段 | 说明 |
|------|------|
| 源/目的地址 | 32位IPv4地址 |
| TTL | 生存时间（跳数限制） |
| Protocol | 上层协议号（TCP=6, UDP=17） |
| Flags | 分片控制（DF位禁止分片） |

### 分片机制

当包长度 > MTU（通常1500字节），IP层自动分片。


## ICMP 控制消息协议

**用途**：网络诊断、错误报告

| 类型 | 说明 |
|------|------|
| Echo 8/0 | ping检测 |
| Unreachable 3 | 目的不可达 |
| Time Exceeded 11 | TTL超时（traceroute） |
| Redirect 5 | 路由重定向 |


## ARP 地址解析协议

**功能**：IP地址 → MAC地址映射

```
流程:
1. ARP广播请求："谁是192.168.1.1？"
2. 目标回复："MAC是xx:xx:xx"
3. 缓存到ARP表（/proc/net/arp）
```


## IGMP 组管理协议

**用途**：多播组管理

- 主机加入/离开多播组
- 路由器查询组成员状态


## LACP协议
https://blog.csdn.net/weixin_37813152/article/details/134853338


## 其他重要协议

| 协议 | 端口 | 说明 |
|------|------|------|
| DNS | UDP 53 | 域名解析 |
| HTTP | TCP 80 | Web服务 |
| HTTPS | TCP 443 | 安全Web |
| SSH | TCP 22 | 安全远程登录 |
| DHCP | UDP 67/68 | 动态IP分配 |
| NTP | UDP 123 | 时间同步 |
| SCTP | - | 多流可靠传输（电信） |


## 协议选择原则

| 需求 | 推荐协议 |
|------|----------|
| 可靠性优先 | TCP |
| 实时性优先 | UDP |
| 多播场景 | UDP + IGMP |
| 网络诊断 | ICMP |
