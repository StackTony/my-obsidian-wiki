Linux 内核中，Soft Lockup 和 Hard Lockup 都是指 CPU 被长时间异常占用、无法正常处理其他任务的死锁或“卡死”状态，但它们的根本原因、表现及检测机制有所不同：

## 一句话速记

- **Softlockup：中断还能跑，调度切不动线程（抢占关了 / 内核死循环）**
- **Hardlockup：本地 IRQ 直接关掉，tick 中断卡死，只能靠 NMI 来抓**

| 维度   | Soft Lockup（软死锁）                                                                                                                            | Hard Lockup（硬死锁 / NMI Watchdog）                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| 根本原因 | CPU 在内核态**开启中断**的前提下，长时间不主动调度（抢占关闭、死循环、自旋锁长时间持有），调度器无法切走当前上下文                                                                               | CPU **关中断（local_irq_disable）** 后死循环，普通中断完全无法进入，时钟中断也进不来                                                             |
| 中断状态 | ✅ 可以响应硬件中断、时钟中断；只是调度器没机会跑                                                                                                                   | ❌ 普通中断被屏蔽；**只有 NMI 能进来**                                                                                            |
| 检测主体 | per-cpu `watchdog` 内核线程（高优先级 SCHED_FIFO）                                                                                                    | per-cpu NMI 处理函数（PMU 硬件计数器触发 NMI）                                                                                   |
| 检测逻辑 | watchdog 线程每次运行更新 `watchdog_touch_ts`；内核时钟中断（tick）检查：距离上次 touch 超过 `2*watchdog_thresh` → 报软死锁<br><br>👉 本质：**中断能跑，但调度器没法把 watchdog 线程调度起来** | PMU 硬件定时触发 NMI；NMI 里检查：上一次 NMI 到现在，tick 有没有前进；超时 `watchdog_thresh` → 硬死锁<br><br>👉 本质：**普通中断 /tick 都停了，只有 NMI 能探查** |
| 默认阈值 | `watchdog_thresh=10` → 软死锁 20s                                                                                                              | `watchdog_thresh=10` → 硬死锁 10s                                                                                      |
| 严重度  | 较轻，CPU 还在处理中断，只是用户进程 / 其他内核线程跑不了；可配置 `softlockup_panic` 决定是否 panic                                                                          | 极严重，本地 CPU 中断通路卡死，常规内核恢复手段失效；`hardlockup_panic` 控制 panic                                                            |
| 典型场景 | 自旋锁循环等待、内核大循环没加 cond_resched、抢占关闭长时间执行                                                                                                      | spin_lock_irq /local_irq_disable 之后死循环、硬件异常导致中断入口卡死                                                                 |


## 检测原理梳理（内核原版逻辑，5.x/6.x 通用）

### ✅ Soft Lockup 检测

1. 每个 CPU 启动一个**SCHED_FIFO 最高优先级的 watchdog 线程**
2. 线程逻辑很简单：`touch_softlockup_watchdog()` 更新本 CPU 时间戳，然后 sleep
3. **时钟中断（tick 中断上下文）** 里做检查：
    - 读取当前时间，对比 `watchdog_touch_ts`
    - 超过 `2*watchdog_thresh` 没更新 → 打印 soft lockup 栈回溯

> 重点：**唤醒 watchdog 的不是 hrtimer，是调度器；tick 中断负责检查，不是唤醒** 只要中断还能进，tick 就能跑；但如果 CPU 一直跑在内核态、抢占关闭，调度器没有机会切到 watchdog 线程，时间戳就不会更新。

### ✅ Hard Lockup（NMI Watchdog）检测

> 前提：依赖硬件 PMU，部分虚拟机 / 部分 ARM 平台不支持 NMI watchdog

1. 内核配置 PMU 硬件计数器，周期性触发 NMI（不可屏蔽中断，`local_irq_disable` 拦不住）
2. NMI handler 里：
    - 记录上一次 tick 计数；对比当前 tick
    - 如果连续 `watchdog_thresh` 时间，tick 完全不增长 → 判定硬死锁
3. 为什么不用普通中断：硬死锁场景就是**本地 IRQ 被关掉，tick 中断根本进不来，tick 计数器停滞**

> 误区纠正：不是去查 hrtimer 计数器，是看全局 tick 有没有推进；NMI 是唯一能在关 IRQ 场景下跑的探查入口。