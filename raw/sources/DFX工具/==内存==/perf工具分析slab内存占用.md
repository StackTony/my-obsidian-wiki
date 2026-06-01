---
title: perf工具分析slab内存占用
updated: 2026-04-14T14:45:59
created: 2026-04-14T14:42:56
---

收集slab分配器的事件，比如内存分配、释放等，可以用来研究程序在哪里分配了大 量的内存，或者在什么地方产生内存碎片。

perf kmem --alloc --caller record sleep 1 采集一秒内的slab分配和释放情况。

perf kmem --alloc --caller stat 显示出之前收集的slab分配和释放情况。
