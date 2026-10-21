---
title: Hot Cache
updated: 2026-10-21
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-10-21] INGEST — raw/sources 增量8来源（Linux 内存/调度/零拷贝/devmem 6实质 + 2工具配置备份）→ 6新页面 + 5更新。manifest 920→928条目，last_ingest → 2026-10-21
- [2026-08-03] INGEST — AI Agent 协议+平台增量：11新来源（6实质+4稀薄+1重命名）+74 CRLF重命名 → 7新页面+3更新
- [2026-06-29] INGEST — AI Agent增量：2新来源 +7修改来源 → 3新页面+7更新页面

## Active Threads

- **虚拟内存原理链落地**：新概念页 `concepts/virtual-memory-and-paging` 把"地址空间→分页/页表项→TLB→多级/倒排页表→页面置换算法"串成一条链，并与 Linux 实现（四级页表、Active/Inactive LRU、PCID）建立对应表——补上了 [[concepts/linux-memory-management]] 一直缺失的下层基础 ^[inferred]
- **TLB 成为内存子系统的第二个成本中心**：进程切换刷 TLB 与多核 TLB shootdown 是两条独立成本线，PCID/ASID 只消掉了前者，后者要靠 IPI——Linux 4.15 才全面启用 PCID
- **进程调度页置信度跃迁**：`concepts/linux-process-scheduling` base_confidence 0.538→0.77，补齐五个调度类（stop>dl>rt>fair>idle）与六种策略枚举，原"三种调度策略"表述保留并标注口径差异 ^[ambiguous]
- **零拷贝的判据统一为 CPU COPY / DMA COPY**：`concepts/zero-copy-memory-mapping` 现在从"谁在执行拷贝"出发推导 read+send(4拷贝/4切换) → sendfile 2.1(3拷贝) → sendfile+SG-DMA 2.4(0 CPU拷贝) 的演进
- **DFX 在线手段补齐**：`devmem` 进入 vmcore 概念页与实操手册，形成"事后(crash) vs 在线(devmem)"的工具对照

## Key Takeaways

- **每次抽象都在制造下一个瓶颈**：分页让访存变成两次访问 → TLB 缓存页表项；页表自身过大 → 多级/倒排页表；TLB 每核私有 → 进程切换刷新与 shootdown。零拷贝同理：消掉 CPU 拷贝后瓶颈转移到 SG-DMA 硬件能力 ^[inferred]
- **页面置换算法的工程结论**：LRU 效果好但无法低成本实现，**老化(aging)与 WSClock 是最优近似**，Linux 的 Active/Inactive 双链表属于同一族近似
- **调度是分层比较而非全局排序**：内核先比 `sched_class`（stop>dl>rt>fair>idle），再在类内按各自规则选——这才是"实时进程绝对优先"的机制根源
- **配置备份不是知识**：2个 JSON 工具配置仅登记 manifest 不建页面，避免无意义摘要污染 wiki（沿用既有 sparse 处理惯例，本次标记为 source_type="config"）

## Flagged Contradictions

- **调度策略口径冲突**：早期来源称"三种调度策略(OTHER/FIFO/RR)"，内核 `sched.h` 枚举为六个值（NORMAL=0/FIFO=1/RR=2/BATCH=3/IDLE=5/DEADLINE=6）——已按"SCHED_OTHER 是 SCHED_NORMAL 别名 + 三种后期扩展"调和 ^[ambiguous]
- **教材 vs Linux 实现的缺口**：页面置换算法章节未给出与 Linux Active/Inactive LRU + kswapd 的推导对应，仍是一处未闭合的桥 ^[inferred]
- **安全告警（待用户处置）**：`raw/sources/Obsidian使用/` 下两个 JSON 备份含明文 API token 与内网代理地址，已随 commit af72905 提交并推送至 GitHub——`raw/` 不可变，未做修改
