---
title: 内存屏障
category: concepts
tags: [linux, 并发, 内存屏障, cpu, 缓存一致性]
aliases: [Memory Barrier, Memory Fence, smp_mb]
source_dir: "Linux 操作系统/Linux 内存管理"
source_files: [Linux 内存屏障（Memory Barrier）.md, Linux CPU Cache缓存一致性：从理论到实战.md]
summary: "内存屏障解决编译器重排与CPU乱序执行导致的内存访问乱序问题。Store Buffer/Invalid Queue引入弱缓存一致性，需读/写/全屏障精细控制，x86-TSO仅需StoreLoad屏障。"
provenance:
  extracted: 0.70
  inferred: 0.27
  ambiguous: 0.03
base_confidence: 0.61
lifecycle: draft
lifecycle_changed: 2026-11-10
tier: supporting
created: 2026-11-10
updated: 2026-11-10
relationships:
  - target: "[[concepts/cpu-cache-coherence]]"
    type: related_to
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: related_to
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
---

# 内存屏障

内存屏障（Memory Barrier / Memory Fence）是一类同步屏障指令，解决编译器重排和CPU乱序执行导致的内存访问乱序问题。它是多核系统中保证[[concepts/cpu-cache-coherence|缓存一致性]]的软件手段——硬件协议（MESI）保证最终一致性，但Store Buffer和Invalid Queue等性能优化结构引入了弱缓存一致性，需要内存屏障在需要严格顺序的场景下手动补全。

## 核心观点

- **乱序的两个来源**：编译器优化重排指令顺序 + CPU乱序执行（Out-of-order）为提升性能打乱执行顺序。有序处理器等待输入操作数可用才执行；乱序处理器将指令放入队列，操作数就绪即执行，最后重排序结果使其看起来有序。即使[[concepts/virtual-memory-and-paging|MMU将虚拟地址转为物理地址]]后，访问顺序仍可能被重排。
- **Store Buffer引入写侧乱序**：核心修改缓存前需向其他核心发Invalid消息并等待ack，等待时间漫长。引入Store Buffer后核心直接写入Buffer继续执行，无需等待。但这导致从其他核心角度看写操作被延后——变量a(需跨核同步)和b(本地E状态)的写入顺序可能颠倒。
- **Invalid Queue引入读侧乱序**：为加速Invalid ack回复，核心收到Invalid消息后立即返回ack，将消息放入Invalid Queue延迟处理。这导致核心可能读到已失效但尚未处理的旧缓存值。
- **内存屏障的本质作用**：屏障前的读写操作未完成时，后面的读写操作不能发生。写屏障标记Store Buffer中的entry阻止后续写直接入cache；读屏障清空Invalid Queue及时处理失效。
- **x86-TSO模型只暴露StoreLoad重排**：Store Buffer为FIFO队列（写写不重排），未引入Invalid Queue（读读不重排），读操作不延后（读写不重排），因此x86上只有StoreLoad屏障是有效指令，其他屏障均为no-op。

## 关键细节

### 屏障分类

**编译器屏障**：`barrier()`（`__asm__ __volatile__("" ::: "memory")`），阻止编译器重排，但不限制CPU。

**CPU内存屏障（Linux内核接口）**：

| 接口 | 类型 | 作用 |
|------|------|------|
| `mb()` / `smp_mb()` | 全屏障(Fence) | 前后所有读写不能跨越，最耗时 |
| `wmb()` / `smp_wmb()` | 写屏障 | 前后写操作不能跨越 |
| `rmb()` / `smp_rmb()` | 读屏障 | 前后读操作不能跨越 |

**细粒度屏障**（区分Load/Store组合）：

| 屏障 | 指令序列 | 保证 |
|------|----------|------|
| LoadLoad | Load1; LoadLoad; Load2 | Load1先于Load2 |
| StoreStore | Store1; StoreStore; Store2 | Store1先对其他处理器可见 |
| LoadStore | Load1; LoadStore; Store2 | Load1先于Store2刷新 |
| StoreLoad | Store1; StoreLoad; Load2 | Store1可见先于Load2，最耗时，需刷Store Buffer |

**单向屏障（ARM）**：不以读写区分，而是控制方向。`stlr`(store-release)挡前不挡后，`ldar`(load-acquire)挡后不挡前。StoreLoad只能用全屏障`dmb`代替。

### Store Buffer → Store Forwarding → Invalid Queue 的演进

1. **Store Buffer**：核心写时直接写入Buffer，发Invalid消息后继续执行，无需等待ack。引入写侧乱序。
2. **Store Forwarding**：CPU执行load时同时检查Store Buffer，有数据则用Buffer值。解决了"自己写的值自己读不到"的问题。
3. **Invalid Queue**：核心收到Invalid消息后立即ack，消息入队延迟处理。解决了Store Buffer因ack慢而被填满的问题。引入读侧乱序。

### 经典示例

```c
int a = 0, b = 0;
// CPU0          // CPU1
void foo() {     void bar() {
  a = 1;           while (b == 0) continue;
  smp_wmb();       smp_rmb();
  b = 1;           assert(a == 1);
}                }
```

不加屏障：Store Buffer导致b先于a可见，CPU1跳出while后读到a=0，断言失败。加写屏障（CPU0侧）保证a先于b写入cache；加读屏障（CPU1侧）清空Invalid Queue及时处理a的失效。 ^[inferred]

### 各架构内存模型

- **x86-TSO**：Store Buffer FIFO + 无Invalid Queue，仅StoreLoad屏障有效。`MFENCE`/`lock`前缀指令清空Store Buffer。
- **ARM**：全乱序，三种屏障指令——DMB(数据内存屏障)、DSB(数据同步屏障，等所有内存操作完成)、ISB(指令同步屏障，冲刷流水线)。
- **Alpha**：最弱模型，连读写分离的细粒度屏障也有作用。

### 典型应用场景

- **[[concepts/linux-lock-mechanisms|锁机制]]**：自旋锁、互斥锁的acquire/release需内存屏障保证临界区内操作不泄露到锁外。
- **无锁数据结构**：CAS原子操作中`lock`前缀指令隐含StoreLoad屏障效果。
- **DMA**：设备与内存间数据传输需屏障保证CPU写入对设备可见。 ^[inferred]
- **多线程标志位同步**：上述a/b模式是生产者-消费者同步的原型。

## 未解问题

- DMA场景下内存屏障的具体使用方式（`dma_wmb()` vs `wmb()`的区别）需更多来源补充。 ^[inferred]
- ARM DMB/DSB/ISB的精确语义差异和性能开销对比，来源3仅列出名称未详述行为差异。 ^[ambiguous]
- Linux内核`READ_ONCE`/`WRITE_ONCE`与内存屏障的关系来源未覆盖。

## 来源

- `raw/sources/Linux 操作系统/Linux 内存管理/Linux 内存屏障（Memory Barrier）.md` — 内存屏障定义、乱序来源、Store Buffer/Store Forwarding/Invalid Queue演进、smp_mb原理、ARM屏障指令
- `raw/sources/Linux 操作系统/Linux 内存管理/Linux CPU Cache缓存一致性：从理论到实战.md` — 屏障分类(LoadLoad/StoreStore/LoadStore/StoreLoad)、读写屏障分离、单向屏障(acquire/release)、x86-TSO模型、无锁队列实战中的屏障分析
