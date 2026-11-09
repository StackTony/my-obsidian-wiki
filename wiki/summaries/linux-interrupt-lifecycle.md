---
title: Linux中断全链路：GIC硬件、irq_domain映射与ARM64处理
category: summaries
tags: [linux, 中断, GIC, ARM, workqueue]
relationships:
  - target: "[[concepts/linux-interrupt-system]]"
    type: related_to
  - target: "[[concepts/linux-interrupt-virtualization]]"
    type: related_to
source_dir: Linux 操作系统/Linux 中断系统
source_files: [Linux中断所有知识点.md]
summary: ARM GICv3中断全链路：Distributor/Redistributor/CPU interface三组件、SGI/PPI/SPI/LPI中断号段、irq_domain将hwirq映射为virq、request_irq注册与线程化中断、ARM64异常向量处理流程、workqueue五元组结构与调度。
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.45
lifecycle: draft
lifecycle_changed: 2026-11-09
tier: supporting
created: 2026-11-09
updated: 2026-11-09
---

# Linux中断全链路：GIC硬件、irq_domain映射与ARM64处理

中断软件侧的全部工作分两段：**静态关系建立**（GIC 驱动初始化、硬件中断号到 Linux 中断号的映射、设备驱动注册中断处理函数）与**动态处理**（中断信号到来后的异常模式切换与处理函数执行）。本文按此主线走完整条链路，并附 workqueue 下半部的深入实现。

## 核心观点

### GICv3 硬件原理

GIC（Generic Interrupt Controller）是 ARM 的通用中断控制器，接受硬件中断信号并分发给对应 CPU。GICv3 定义四类中断：

| 中断类型 | 全称 | 用途 | 硬件中断号 |
|---|---|---|---|
| SGI | Software Generated Interrupt | 软件写 GICD_SGIR 触发，核间通信（IPI 基于它） | 0-15 |
| PPI | Private Peripheral Interrupt | 每核私有（CPU 本地时钟） | 16-31 |
| SPI | Shared Peripheral Interrupt | 全系统共享外设中断（按键、触摸屏） | 32-1019 |
| LPI | Locality-specific Peripheral Interrupt | GICv3 新特性：始终基于消息、配置保存在表中而非寄存器（PCIe MSI/MSI-X） | 8192-MAX |

GICv3 控制器由三部分组成 ^[inferred]（分工即"SPO 管谁就长在哪层"）：

- **Distributor**（管理 SPI，全局侧）：全局/单源两级使能（GIC_DIST_CTRL / GIC_DIST_ENABLE_CLEAR）；把当前优先级最高的中断分发到一个或一组 CPU interface（分发到多个时 GIC 内部保证只 assert 一个）；优先级控制；触发方式设定（电平/边沿）；中断 Group 设定——Group0 安全中断支持 FIQ+IRQ，Group1 非安全中断只支持 IRQ。
- **Redistributor**（管理 SGI/PPI/LPI，每核侧）：启停/优先级/触发方式/中断组设置 SGI 与 PPI；控制其状态；LPI 相关属性与挂起状态的内存表基址；电源管理支持。
- **CPU interface**（传输给 Core）：向连接的 CPU assert 中断（nIRQCPU/nFIQCPU 信号线）；中断应答——Core ack 后 Distributor 将 pending 改为 active 或 pending and active（取决于电平是否保持），CPU interface 随即 deassert 信号线；处理完毕通知（状态改回 inactive + priority drop，放行其他 pending 中断）；优先级掩码与抢占策略设置；多中断同时到达时选最高优先级通知 CPU。

**中断状态机**：Inactive（无中断）→ Pending（已通知 GIC 待处理）→ Active（CPU 已应答处理中）→ Active and pending（处理中同源再次触发）。电平触发模式下产生中断的同时保持 Pending。

**中断路由**：GICv3 用四层 affinity 标识 core（aarch64）：`<aff3>.<aff2>.<aff1>.<aff0>`，每个 affinity 占 8bit，可从 MPIDR_EL1 寄存器读取。各层含义由 SoC 自定义（如"簇组.处理器组.处理器.核"）。配置目标核的 MPIDR 值即可把中断路由到该核；通用接口为 `irq_set_affinity`。

### GIC 驱动初始化

设备树节点示例：`compatible = "arm,gic-v3"`（匹配驱动）；reg 五段（GICD/GICR/GICC/GICH/GICV 基地址）；`#interrupt-cells = <3>`；`interrupts = <GIC_PPI 9 ...>`（maintenance 中断走 PPI 9 ^[inferred]）。初始化链路：

1. `IRQCHIP_DECLARE(gic_v3, "arm,gic-v3", gic_of_init)` 把匹配信息放入 `__irqchip_of_table` 段（链接脚本划定 `__irqchip_begin`~`__irqchip_of_end`）。
2. 内核启动时 `of_irq_init` 按设备树匹配该段，回调 `gic_of_init`。
3. `gic_of_init`：映射 GICD 地址空间 → 读 GICD_PIDR2 校验版本（bit[7:4]：0x1=GICv1、0x2=GICv2…）→ 读 redistributor-regions/stride → `gic_init_bases`。
4. `gic_init_bases`：读 GICD_TYPER 确认 SPI 最大中断号（上限 1020）→ 注册 irq_domain（hwirq→virq 映射的基础）→ `set_handle_irq(gic_handle_irq)` 设定 arch 中断处理入口 → 初始化 ITS（若支持 LPI）→ `gic_smp_init`（设置 IPI 回调 `gic_raise_softirq`）→ Distributor/CPU interface/电源管理初始化。

### 中断映射：irq_domain

单中断控制器时代硬件中断号可线性映射；多控制器时代**硬件中断号在不同控制器上重复编码**，仅凭 hwirq 无法唯一标识外设中断，因此内核引入 **irq_domain + 虚拟中断号（virq）**：每个中断控制器一个 irq_domain，级联成树，各 domain 自管自己的中断特性。

关键数据结构 ^[inferred]（左列驱动加载时建立、右列设备注册时挂接）：

| 结构 | 角色 | 关键内容 |
|---|---|---|
| `irq_desc` | 外设中断描述符 | `irq_data`（控制器硬件数据）、`handle_irq`（流控处理）、`action` 链表（多个设备可共享一个中断，故一 desc 挂多个 action） |
| `irq_data` | 中断号绑定 | `irq`（virq）+ `hwirq`（硬件中断号）+ `chip` + `domain` |
| `irq_chip` | 控制器硬件操作集 | `irq_enable/mask/ack/unmask/eoi/set_affinity/set_type/...` 回调 |
| `irq_domain` | hwirq↔virq 映射 | `ops`（match/map/xlate）、`linear_revmap[]` 反向映射表、`parent` 支持级联 |
| `irqaction` | 驱动注册的处理函数 | `handler` + `dev_id` + `flags` + `name`（/proc/interrupts 显示名） |

外设驱动建立映射的流程：`irq_of_parse_and_map` → `of_irq_parse_one` 解析 DTS → `irq_find_matching_fwspec` 遍历全局 `irq_domain_list` 找匹配 domain → `gic_irq_domain_translate` 解析出 hwirq 与触发方式 → `irq_domain_alloc_descs` 分配 virq 并创建 irq_desc → `gic_irq_domain_alloc` 写入 `irq_data->hwirq` 完成绑定 → `irq_domain_set_info` 按硬件中断号范围设置流控入口（共享中断 `handle_fasteoi_irq`，私有中断 `handle_percpu_devid_irq`）。映射结果可通过 `/proc/interrupts` 观察。

### 中断注册与线程化

- `request_irq()` 内部就是 `request_threaded_irq(irq, handler, NULL, ...)`——注册"硬中断处理 + 无线程"的普通中断。
- `request_threaded_irq()` 注册线程化中断：**把中断上下文的任务迁移到线程中执行，减少关中断时间、增强实时性**。产生的中断线程为 SCHED_FIFO 实时线程，`ps` 可见形如 `[irq/433-imx_drm]`。
- 关键 IRQF_* 标志：`IRQF_SHARED`（多设备共享一个中断号，需硬件支持）、`IRQF_ONESHOT`（一次性触发：硬件中断处理完成后才开中断；线程化中保持关闭直到所有 thread_fn 执行完）、`IRQF_PERCPU`（特定 CPU 的中断）、`IRQF_NOBALANCING`（禁止 CPU 间中断均衡）、`IRQF_NO_SUSPEND`/`IRQF_FORCE_RESUME`（休眠唤醒控制）、`IRQF_NO_THREAD`（禁止线程化）、`__IRQF_TIMER`（时钟中断）。

### ARM64 中断处理流程

中断属于**异步异常**。异常向量表 `vectors` 按 EL0/EL1 × sync/irq/fiq/error 设入口，有效入口为 el0_sync/el1_sync（同步）与 el0_irq/el1_irq（异步）。以 EL0 应用触发 IRQ 为例，处理分三段：

1. **保护现场**：硬件自动切换异常等级并跳转向量入口，保存寄存器上下文到 pt_regs。
2. **中断处理**：`gic_handle_irq` 为入口，读 CPU interface 应答中断、执行已注册的 handler；涉及线程化中断时还需唤醒中断内核线程。
3. **恢复现场**（`ret_to_user`）：`disable_daif` 屏蔽四类异常 → 检查 `thread_info.flags` 的 `_TIF_WORK_MASK`（有调度、信号处理等工作则转 `work_pending`）→ `kernel_exit 0` 弹出 pt_regs 恢复现场。

### workqueue 下半部深入

workqueue 的本质：把 work（`work_struct`，调度最小单位）交给内核线程 worker，在**进程上下文**中执行——因此允许重新调度和睡眠，解决 softirq/tasklet 执行时间长导致实时性下降的问题。

五个数据结构的关系 ^[inferred]（"工人-中介-集合-任务"分层）：

- **work_struct**：工作任务本身（`data` 存状态位与 pool 指针；`func` 回调）。
- **workqueue_struct**：work 的集合，与 work 一对多。分两类：**bound**（worker 线程绑定特定 CPU）与 **unbound**（`WQ_UNBOUND`，线程可跨处理器迁移）。
- **pool_workqueue**：中介，连接 workqueue 与 worker_pool（一对多）；`nr_active`/`max_active` 控制并发 work 数，超限的进 `delayed_works`。
- **worker_pool**：工人集合。bound 类型 per-CPU 创建，**每个 CPU 有两个 pool，对应 nice 0 和 -20 两个优先级**；unbound 类型创建后加入 unbound_pool_hash。
- **worker**：工人，对应一个 `worker_thread()` 内核线程。

初始化两阶段：`workqueue_init_early`（分配并初始化 worker_pool、workqueue_struct、pool_workqueue 并关联）→ `workqueue_init`（`create_worker` 创建 `kworker/XX:YY`（bound）或 `kworker/uXX:YY`（unbound）内核线程，XX=pool 编号，YY=worker 编号）。

work 调度流程（`schedule_work`）：挂入系统默认 system_wq → bound 按 CPU、unbound 按 node 取 pool_workqueue → 活跃数未超限入 `pool->worklist` 否则入 `delayed_works` → 无 worker 在执行时 `wake_up_worker` 唤醒。`worker_thread` 循环：设置 `PF_WQ_WORKER`（调度器特殊处理）→ recheck 判断是否需要更多 worker → 有任务则遍历 worklist 逐个 `process_one_work` 执行回调 → 无任务则进入 sleep 挂入 idle_list 让出 CPU。

内核推荐驱动使用**默认 workqueue**（`INIT_WORK` + `schedule_work`）而非新建；`kworker` 线程调度 workqueue 的原理与 `ksoftirqd` 调度 softirqs 一样，但 workqueue 可创建新线程而 softirq 不行。

## 未解问题

- GICv4 的 vLPI 直接注入（`gic_update_vlpi_properties`）与 KVM 虚拟化的配合细节文中未展开，与 [[concepts/linux-interrupt-virtualization]] 的 VGIC 侧如何衔接待补。 ^[inferred]
- workqueue 的 rescuer/mayday 机制（内存紧张时创建工作线程失败的处理）文中仅列字段未展开。
- `handle_fasteoi_irq` 与 `handle_percpu_devid_irq` 两种流控的具体差异。

## 来源

- `raw/sources/Linux 操作系统/Linux 中断系统/Linux中断所有知识点.md` — 原始文章（知乎 zhuanlan/p/528866826，blog 级可信度）
- [[concepts/linux-interrupt-system]] — 中断系统整体框架与三种延迟机制对比
- [[concepts/linux-interrupt-virtualization]] — VGIC 如何虚拟化 GIC 硬件
- [[summaries/linux-interrupt-classification]] — 中断分类框架与术语速查
