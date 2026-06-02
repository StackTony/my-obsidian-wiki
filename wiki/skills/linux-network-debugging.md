---
title: Linux网络调试实操手册
category: skills
tags: [linux, 网络, tcpdump, iperf, 网络分析]
aliases: [网络调试实操, tcpdump实操, iperf打流]
relationships:
  - target: "[[concepts/linux-network-stack]]"
    type: uses
source_dir: DFX工具
source_files: [==网络==/iperf打流.md, ==网络==/网络分析工具tcpdump.md]
summary: 网络调试实操手册：tcpdump抓包分析（参数/表达式/实例）和iperf打流测试（UDP带宽测试），覆盖网络问题排查的两大核心场景。
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.65
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# Linux网络调试实操手册

网络调试两大核心工具：tcpdump抓包分析 + iperf带宽测试。

## 前置条件

- root 权限执行 tcpdump
- 两台机器（iperf需要服务端+客户端）
- 理解 [[concepts/linux-network-stack]] 基础概念

## 步骤

### 1. tcpdump 抓包分析

#### 常用参数

| 参数 | 说明 |
|------|------|
| `-i <interface>` | 指定网络接口 |
| `-w <file>.pcap` | 输出到文件（结合Wireshark分析） |
| `-n` | 不解析域名（更快） |
| `-nn` | 不解析端口名（直接显示IP和端口） |
| `-v/vv` | 详细/更详细输出 |
| `-c <count>` | 收到指定数量后停止 |
| `-A` | ASCII格式打印（收集web内容） |
| `-e` | 打印链路层头部 |
| `-r <file>` | 从文件读取包 |

#### 表达式语法

格式：`tcpdump [option] 协议 + 传输方向 + 类型 + 具体值`

- **协议**：ip/arp/tcp/udp/icmp 等（默认所有协议）
- **方向**：src/dst/dst or src/dst and src（默认 src or dst）
- **类型**：host/net/port/ip proto/protochain（默认 host）
- **逻辑**：not/!、and/&&、or/||

#### 实用示例

```bash
# 包含指定主机的数据包
tcpdump host 192.0.0.19

# 指定网段
tcpdump net 192.0.0.0/24

# 指定端口
tcpdump port 9092

# TCP协议包
tcpdump tcp

# 组合过滤：源IP+目标端口
tcpdump src host 192.0.0.19 and dst port 9092

# 保存到文件
tcpdump -i eth0 -c 1000 -w backup.cap

# 从文件读取
tcpdump -r backup.cap -c 10 tcp

# 包长度过滤
tcpdump greater 50 and less 100
```

### 2. iperf 打流测试

**服务端**：
```bash
iperf -s -p 20000 -u    # UDP模式，端口20000
```

**客户端**：
```bash
iperf -c 195.168.1.31 -p 20000 -i 1 -l 1460 -t 18000 -u -b 50G
# -c: 服务端IP；-p: 端口；-i: 间隔报告；-l: 包长度；-t: 持续时间；-u: UDP；-b: 目标带宽
```

## 常见问题

| 问题 | 排查方向 |
|------|----------|
| 网络延迟增大 | tcpdump抓包分析延迟 + 检查路由 |
| UDP丢包 | iperf测试带宽 + tcpdump确认丢包位置 |
| TCP连接异常 | tcpdump tcp端口抓包 → Wireshark分析 |

## 来源

- [[concepts/linux-network-stack]] — 网络栈架构