---
title: Hot Cache
updated: 2026-06-02
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-02] INGEST — DFX工具29个源文件蒸馏为16个新wiki页面+1个更新，覆盖CPU/IO/内存/网络/追踪/vmcore/gdb六大调试领域
- [2026-06-01] INGEST-STEP5 — 补做Ingest第5步跨分类更新，新增3个skills页面和1个synthesis页面

## Active Threads

- **DFX调试知识网络成型**：4个概念页 + 4个实体页 + 7个摘要页 + 6个技巧页 + 1个综合页，覆盖从工具属性到实操场景到全景图的三层架构
- **工具实体化趋势**：perf-tool、crash-tool、gdb-tool、flamegraph-tool四个实体页建立工具身份，概念页和技巧页引用实体而非直接描述工具属性
- **跨领域连接发现**：DFX工具全景图(synthesis)揭示了六大领域×三种模式的分析矩阵，以及perf↔火焰图、ftrace↔kprobe、perf↔crash等工具互补关系

## Key Takeaways

- 寄存器是崩溃分析的起点：RIP/PC定位崩溃指令、RDI/X0解析函数入参、RBP/X29回溯调用栈——x86和ARM64完全不同的调用约定体系
- VM-Exit是虚拟化CPU性能问题的核心诊断入口：EXTirq(中断退出)最常见性能问题源，可通过VM内irqtop对比问题期与非问题期
- %ST双维度：top的Steal(物理机) vs kvmtop的ST(虚拟机)——阈值不同(10% vs 20%)，采集原理不同
- DFX工具设计遵循"分层递进"哲学：监控→追踪→深入三级工具，先量化再定性
- ftrace和kprobe通过`/sys/kernel/debug/tracing/`统一接口操作，但定位完全不同——ftrace是广角镜头，kprobe是显微镜

## Flagged Contradictions

- bpftrace在源文件中仅简略提及(树状图)，缺少详细使用方式，概念页推断比例偏高(inferred 0.30)
- 调度sched源文件仅描述概念缺少结构体字段，vmcore中调度分析需要更多资料
- iotop和blktrace的详细使用方法在源文件中缺失
- IO领域源文件仅1篇(iostat为主)，confidence偏低(0.55)