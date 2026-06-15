---
title: Hot Cache
updated: 2026-06-15
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-15] INGEST — DFX网络Bonding调试日志：1个新summary页面(kernel-bonding-debug-log)+4个已有页面更新(network-debugging/tracing-frameworks/network-stack/kernel-debugging)，dynamic debug从追踪框架的边缘用法升级为独立对比项

## Active Threads

- **五大领域landscape全覆盖**：5个导航枢纽页面——Linux OS/虚拟化、云原生、AI Agent、LLM基础设施、云原生基础设施三层架构
- **DFX工具网络调试维度扩展**：原来只有tcpdump+iperf，现在新增Bonding调试日志（dynamic debug源码级打印），网络调试覆盖从"抓包+打流"到"模块级调试"
- **追踪框架从四到五**：linux-tracing-frameworks从四大框架(ftrace/kprobe/perf/bpftrace)升级为包含dynamic debug的五框架对比

## Key Takeaways

- Dynamic debug是内核源码级调试打印机制，通过`/sys/kernel/debug/dynamic_debug/control`按文件/函数/模块精确控制`pr_debug()/dev_dbg()`开关，关闭时编译为空操作，开启时仅增加打印开销——比ftrace/kprobe更轻量
- Bonding调试需要两步配合：先`echo 8 > /proc/sys/kernel/printk`放开日志级别，再通过dynamic debug开启bond_3ad/bond_main源码打印——单独调整printk或单独开启dynamic debug都不会生效
- 网络调试工具矩阵扩充：tcpdump(抓包) + iperf(打流) + dynamic debug(模块调试)——三种工具覆盖从数据包级到源码级的调试深度

## Flagged Contradictions

- GraphRAG"以检索为始" vs KAG"以推理为始"——不同范式而非矛盾
- 3-RAG工程全景与【17】RAG工程全景内容完全相同（同一文件出现在两个路径），不是矛盾而是副本
