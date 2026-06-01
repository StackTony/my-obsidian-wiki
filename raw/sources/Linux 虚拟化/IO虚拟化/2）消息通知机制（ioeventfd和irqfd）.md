---
tags:
  - virtio
  - 中断
---
## Virtio 消息通知机制：Qemu侧代码流程分析（不包含KVM侧分析）
#### 1. 概述
Virtio 中断通知机制包含两个方向：
• Guest → Host：Guest 通知 Host 处理队列（Queue Notify）
• Host → Guest：Host 通知 Guest 处理完成（Interrupt Injection）
#### 2. Guest → Host 通知流程（Queue Notify）
##### 2.1 触发路径
Legacy PCI 模式：
Guest写入VIRTIO_PCI_QUEUE_NOTIFY (0x10)
  ↓
virtio_pci_legacy_write() [virtio-pci.c:555]
  ↓
virtio_queue_notify(vdev, val)
Modern PCI 模式：
Guest写入Notify Capability区域
  ↓
virtio_pci_notify_write() [virtio-pci.c:1795]
  ↓
virtio_queue_notify(vdev, queue)
MMIO 模式：
Guest写入VIRTIO_MMIO_QUEUE_NOTIFY (0x50)
  ↓
virtio_mmio_write() [virtio-mmio.c:411]
  ↓
virtio_queue_notify(vdev, value)
##### 2.2 核心处理函数
virtio_queue_notify() [virtio.c:2320]
```c
void virtio_queue_notify(VirtIODevice *vdev, int n)
{
    VirtQueue *vq = &vdev->vq[n];
    
    if (vq->host_notifier_enabled) {
        // 使用ioeventfd（eventfd）通知，零拷贝
        event_notifier_set(&vq->host_notifier);
    } else {
        // 直接调用回调函数
        vq->handle_output(vdev, vq);
    }
}
```

##### 2.3 ioeventfd 机制
启用条件：
• 设备状态为 VIRTIO_CONFIG_S_DRIVER_OK
• 调用 virtio_device_start_ioeventfd_impl()
处理流程：
event_notifier_set(&vq->host_notifier)
  ↓
KVM捕获eventfd事件
  ↓
virtio_queue_host_notifier_read() [virtio.c:3692]
  ↓
virtio_queue_notify_vq(vq) [virtio.c:2302]
  ↓
vq->handle_output(vdev, vq)  // 设备特定处理函数
3. Host → Guest 中断注入流程

ioeventfd机制
<https://www.cnblogs.com/haiyonghao/p/14440743.html>

（guest写pci配置空间陷出到kvm。kvm通过ioeventfd通知qemu）

<span style='color:#222222'>整个ioeventfd的逻辑流程如下：</span>
1.  <span style='color:#222222'>QEMU分配一个eventfd，并将该eventfd加入KVM维护的eventfd数组中</span>
2.  <span style='color:#222222'>QEMU向KVM发送更新eventfd数组内容的请求</span>
3.  <span style='color:#222222'>QEMU构造一个包含IO地址，IO地址范围等元素的ioeventfd结构，并向KVM发送注册ioeventfd请求</span>
4.  <span style='color:#222222'>KVM根据传入的ioeventfd参数内容确定该段IO地址所属的总线，并在该总线上注册一个ioeventfd虚拟设备，该**虚拟设备的write**方法也被注册</span>
5.  <span style='color:#222222'>Guest执行OUT类指令(包括MMIO Write操作)</span>
6.  <span style='color:#222222'>VMEXIT到KVM</span>
7.  <span style='color:#222222'>调用虚拟设备的write方法</span>
8.  <span style='color:#222222'>write方法中检查本次OUT类指令访问的IO地址和范围是否符合ioeventfd设置的要求</span>
9.  <span style='color:#222222'>如果符合则调用eventfd_signal触发一次POLLIN事件并返回Guest</span>
10. <span style='color:#222222'>QEMU监测到ioeventfd上出现了POLLIN，则调用相应的处理函数处理IO</span>

#### 3. Host → Guest 中断注入流程
##### 3.1 通知入口函数
virtio_notify() [virtio.c:2535]
```c
void virtio_notify(VirtIODevice *vdev, VirtQueue *vq)
{
    // 检查是否需要通知（避免不必要的通知）
    if (!virtio_should_notify(vdev, vq)) {
        return;
    }
    
    virtio_irq(vq);  // 触发中断
}
virtio_notify_irqfd() [virtio.c:2500]
void virtio_notify_irqfd(VirtIODevice *vdev, VirtQueue *vq)
{
    if (!virtio_should_notify(vdev, vq)) {
        return;
    }
    
    virtio_set_isr(vq->vdev, 0x1);  // 设置ISR位
    event_notifier_set(&vq->guest_notifier);  // 通过irqfd注入中断
}
```
##### 3.2 通知判断逻辑
```c
virtio_should_notify() [virtio.c:2491]
static bool virtio_should_notify(VirtIODevice *vdev, VirtQueue *vq)
{
    if (virtio_vdev_has_feature(vdev, VIRTIO_F_RING_PACKED)) {
        return virtio_packed_should_notify(vdev, vq);
    } else {
        return virtio_split_should_notify(vdev, vq);
    }
}
```
Split Ring 判断 [virtio.c:2424]
```c
static bool virtio_split_should_notify(VirtIODevice *vdev, VirtQueue *vq)
{
    // 1. 检查NOTIFY_ON_EMPTY特性
    if (virtio_vdev_has_feature(vdev, VIRTIO_F_NOTIFY_ON_EMPTY) &&
        !vq->inuse && virtio_queue_empty(vq)) {
        return true;
    }
    
    // 2. 检查NO_INTERRUPT标志
    if (!virtio_vdev_has_feature(vdev, VIRTIO_RING_F_EVENT_IDX)) {
        return !(vring_avail_flags(vq) & VRING_AVAIL_F_NO_INTERRUPT);
    }
    
    // 3. 使用EVENT_IDX特性进行精确通知
    return vring_need_event(vring_get_used_event(vq), new, old);
}
```
Packed Ring 判断 [virtio.c:2461]
```c
static bool virtio_packed_should_notify(VirtIODevice *vdev, VirtQueue *vq)
{
    // 检查event flags
    if (e.flags == VRING_PACKED_EVENT_FLAG_DISABLE) {
        return false;
    } else if (e.flags == VRING_PACKED_EVENT_FLAG_ENABLE) {
        return true;
    }
    
    // 使用event suppression机制
    return vring_packed_need_event(...);
}
```

VRING_AVAIL_F_NO_INTERRUPT是用于物理机侧抑制的，当虚拟机内部配置了这个标志位后，物理机侧判断到了就不会出发kick中断。

##### 3.3 中断注入路径
传统路径：
virtio_irq(vq) [virtio.c:2529]
  ↓
virtio_set_isr(vq->vdev, 0x1)  // 设置ISR位
  ↓
virtio_notify_vector(vq->vdev, vq->vector) [virtio.c:1843]
  ↓
k->notify(qbus->parent, vector)  // 调用bus的notify方法
  ↓
virtio_pci_notify() [virtio-pci.c]
  ↓
pci_irq_assert() / msix_notify()  // PCI中断注入
irqfd 路径（零拷贝）：
virtio_notify_irqfd(vdev, vq)
  ↓
event_notifier_set(&vq->guest_notifier)
  ↓
KVM直接注入中断到Guest（无需VM exit）
##### 3.4 irqfd 设置流程
初始化 [virtio-pci.c:1353]
```c
static int virtio_pci_set_guest_notifiers(DeviceState *d, int nvqs, bool assign)
{
    bool with_irqfd = msix_enabled(&proxy->pci_dev) &&
                      kvm_msi_via_irqfd_enabled();
    
    if (with_irqfd) {
        // 为每个vector创建irqfd
        proxy->vector_irqfd = g_malloc0(...);
        
        for (n = 0; n < nvqs; n++) {
            kvm_virtio_pci_irqfd_use(proxy, n, vector);
        }
    }
}
```
irqfd 使用 [virtio-pci.c:941]
```c
static int kvm_virtio_pci_irqfd_use(VirtIOPCIProxy *proxy,
                                    EventNotifier *n,
                                    unsigned int vector)
{
    VirtIOIRQFD *irqfd = &proxy->vector_irqfd[vector];
    // 将eventfd与KVM虚拟中断路由关联
    return kvm_irqchip_add_irqfd_notifier_gsi(kvm_state, n, NULL, irqfd->virq);
}
```
#### 4. 关键数据结构
VirtQueue [include/hw/virtio/virtio.h]
```c
struct VirtQueue {
    VirtIODevice *vdev;
    VRing vring;
    
    EventNotifier guest_notifier;  // Guest中断通知（irqfd）
    EventNotifier host_notifier;   // Host队列通知（ioeventfd）
    
    bool host_notifier_enabled;
    uint16_t vector;  // MSI-X vector
    ...
};
VirtIOIRQFD [virtio-pci.c]
typedef struct {
    int virq;           // KVM虚拟中断号
    int users;          // 引用计数
    MSIMessage msg;     // MSI消息
} VirtIOIRQFD;
```
#### 5. 性能优化机制
##### 5.1 ioeventfd（Guest → Host）
• 零拷贝：Guest 写入直接触发 Host 处理，无需 VM exit
• 批量处理：通过 memory_region_transaction_begin/commit 批量设置
##### 5.2 irqfd（Host → Guest）
• 零拷贝：Host 直接注入中断，无需 VM exit
• 条件：需要 MSI-X 支持和 KVM irqfd 功能
##### 5.3 通知抑制
• VRING_USED_F_NO_NOTIFY：Guest 设置标志抑制通知
• VIRTIO_RING_F_EVENT_IDX：精确的事件索引通知
• VIRTIO_F_NOTIFY_ON_EMPTY：仅在队列为空时通知
#### 6. 代码调用链总结
Guest → Host：
Guest写入 → PCI/MMIO寄存器 → virtio_queue_notify()
  → event_notifier_set(host_notifier) → KVM捕获
  → virtio_queue_host_notifier_read() → handle_output()
Host → Guest：
设备处理完成 → virtio_notify() → virtio_should_notify()
  → virtio_irq() → virtio_notify_vector()
  → [irqfd路径] event_notifier_set(guest_notifier) → KVM注入中断
  → [传统路径] pci_irq_assert() → VM exit → 中断注入
#### 7. 关键代码位置
功能	文件	函数	行号
Queue Notify入口	hw/virtio/virtio.c	virtio_queue_notify()	2320
Host通知处理	hw/virtio/virtio.c	virtio_queue_host_notifier_read()	3692
中断通知入口	hw/virtio/virtio.c	virtio_notify()	2535
irqfd通知	hw/virtio/virtio.c	virtio_notify_irqfd()	2500
通知判断	hw/virtio/virtio.c	virtio_should_notify()	2491
PCI通知处理	hw/virtio/virtio-pci.c	virtio_pci_notify_write()	1795
irqfd设置	hw/virtio/virtio-pci.c	kvm_virtio_pci_irqfd_use()	941
该机制通过 eventfd/irqfd 实现零拷贝通知，减少 VM exit，提升性能。


## Virtio 消息通知机制：Qemu 与 Linux KVM 侧整体代码流程

### 一、QEMU 侧代码流程（中断注入）

#### 1.1 Virtio 设备触发中断

**入口：** `hw/virtio/virtio.c:2535` - `virtio_notify()`
```c
void virtio_notify(VirtIODevice *vdev, VirtQueue *vq)
{
    if (!virtio_should_notify(vdev, vq)) {
        return;  // 检查是否需要通知
    }
    virtio_irq(vq);  // 触发中断
}
```

#### 1.2 设置 ISR 并通知向量

**函数：** `hw/virtio/virtio.c:2529` - `virtio_irq()`
```c
static void virtio_irq(VirtQueue *vq)
{
    virtio_set_isr(vq->vdev, 0x1);           // 设置ISR位
    virtio_notify_vector(vq->vdev, vq->vector); // 通知中断向量
}
```

**函数：** `hw/virtio/virtio.c:1843` - `virtio_notify_vector()`
```c
static void virtio_notify_vector(VirtIODevice *vdev, uint16_t vector)
{
    BusState *qbus = qdev_get_parent_bus(DEVICE(vdev));
    VirtioBusClass *k = VIRTIO_BUS_GET_CLASS(qbus);
    
    if (k->notify) {
        k->notify(qbus->parent, vector);  // 调用bus的notify方法
    }
}
```

#### 1.3 PCI 总线中断通知（使用 irqfd）

**函数：** `hw/virtio/virtio-pci.c:941` - `kvm_virtio_pci_irqfd_use()`
```c
static int kvm_virtio_pci_irqfd_use(VirtIOPCIProxy *proxy,
                                    EventNotifier *n,
                                    unsigned int vector)
{
    VirtIOIRQFD *irqfd = &proxy->vector_irqfd[vector];
    // 将eventfd与KVM虚拟中断路由关联
    return kvm_irqchip_add_irqfd_notifier_gsi(kvm_state, n, NULL, irqfd->virq);
}
```

**函数：** `accel/kvm/kvm-all.c:2421` - `kvm_irqchip_add_irqfd_notifier_gsi()`
```c
int kvm_irqchip_add_irqfd_notifier_gsi(KVMState *s, EventNotifier *n,
                                       EventNotifier *rn, int virq)
{
    return kvm_irqchip_assign_irqfd(s, n, rn, virq,
                                    KVM_IRQFD_FLAG_ASSIGN);
}
```

#### 1.4 构建 irqfd 结构并发送到 KVM

**函数：** `accel/kvm/kvm-all.c:2134` - `kvm_irqchip_assign_irqfd()`
```c
static int kvm_irqchip_assign_irqfd(KVMState *s, EventNotifier *event,
                                    EventNotifier *resample, int virq,
                                    unsigned int flags)
{
    int fd = event_notifier_get_fd(event);  // 获取eventfd文件描述符
    int rfd = resample ? event_notifier_get_fd(resample) : -1;
    
    struct kvm_irqfd irqfd = {
        .fd = fd,        // eventfd文件描述符
        .gsi = virq,     // 虚拟中断号(GSI)
        .flags = flags,  // KVM_IRQFD_FLAG_ASSIGN
    };
    
    // 发送KVM_IRQFD ioctl到内核
    return kvm_vm_ioctl(s, KVM_IRQFD, &irqfd);
}
```

**函数：** `accel/kvm/kvm-all.c:3237` - `kvm_vm_ioctl()`
```c
int kvm_vm_ioctl(KVMState *s, int type, ...)
{
    // 调用Linux系统调用ioctl(/dev/kvm, KVM_IRQFD, &irqfd)
    ret = ioctl(s->vmfd, type, arg);
}
```

---

### 二、Linux KVM 内核侧代码流程

#### 2.1 接收 KVM_IRQFD ioctl

**入口：** `virt/kvm/kvm_main.c` - `kvm_vm_ioctl()` → `kvm_irqfd()`

**函数：** `virt/kvm/eventfd.c:698` - `kvm_irqfd()`
```c
int kvm_irqfd(struct kvm *kvm, struct kvm_irqfd *args)
{
    // args包含: fd (eventfd), gsi (虚拟中断号), flags
    
    if (args->flags & KVM_IRQFD_FLAG_DEASSIGN)
        return kvm_irqfd_deassign(kvm, args);
    
    return kvm_irqfd_assign(kvm, args);  // 注册irqfd
}
```

#### 2.2 分配并初始化 irqfd 结构

**函数：** `virt/kvm/eventfd.c:320` - `kvm_irqfd_assign()`
```c
static int kvm_irqfd_assign(struct kvm *kvm, struct kvm_irqfd *args)
{
    struct kvm_kernel_irqfd *irqfd;
    struct eventfd_ctx *eventfd;
    
    // 1. 分配irqfd结构
    irqfd = kzalloc(sizeof(*irqfd), GFP_KERNEL_ACCOUNT);
    
    // 2. 获取eventfd上下文
    eventfd = eventfd_ctx_fdget(args->fd);
    
    // 3. 初始化irqfd
    irqfd->kvm = kvm;
    irqfd->gsi = args->gsi;
    irqfd->eventfd = eventfd;
    INIT_WORK(&irqfd->inject, irqfd_inject);  // 注册注入工作函数
    INIT_WORK(&irqfd->shutdown, irqfd_shutdown);
    
    // 4. 添加到等待队列，监听eventfd事件
    init_waitqueue_func_entry(&irqfd->wait, irqfd_wakeup);
    init_poll_funcptr(&irqfd->pt, irqfd_ptable_queue_proc);
    eventfd_ctx_add_wait_queue(eventfd, &irqfd->wait, &irqfd->pt);
    
    // 5. 更新中断路由
    irqfd_update(kvm, irqfd);
    
    // 6. 添加到irqfd列表
    list_add_tail(&irqfd->list, &kvm->irqfds.items);
    
    // 7. 检查是否有pending事件，立即触发
    events = vfs_poll(f.file, &irqfd->pt);
    if (events & EPOLLIN)
        schedule_work(&irqfd->inject);
}
```

#### 2.3 Eventfd 事件触发（用户态写入 eventfd）

当 QEMU 调用 `event_notifier_set(&vq->guest_notifier)` 时：
- 写入 eventfd 会触发等待队列回调


**函数：** `virt/kvm/eventfd.c:202` - `irqfd_wakeup()`
```c
static int irqfd_wakeup(wait_queue_entry_t *wait, unsigned mode, 
                        int sync, void *key)
{
    struct kvm_kernel_irqfd *irqfd = 
        container_of(wait, struct kvm_kernel_irqfd, wait);
    __poll_t flags = key_to_poll(key);
    
    if (flags & EPOLLIN) {
        // 事件已触发，注入中断
        idx = srcu_read_lock(&kvm->irq_srcu);
        
        // 尝试原子注入（避免VM exit）
        if (kvm_arch_set_irq_inatomic(&irq, kvm,
                                     KVM_USERSPACE_IRQ_SOURCE_ID, 1,
                                     false) == -EWOULDBLOCK)
            schedule_work(&irqfd->inject);  // 无法原子注入，使用工作队列
        srcu_read_unlock(&kvm->irq_srcu, idx);
    }
    
    return 0;
}
```

#### 2.4 中断注入（工作队列或原子路径）

**函数：** `virt/kvm/eventfd.c:42` - `irqfd_inject()`
```c
static void irqfd_inject(struct work_struct *work)
{
    struct kvm_kernel_irqfd *irqfd =
        container_of(work, struct kvm_kernel_irqfd, inject);
    struct kvm *kvm = irqfd->kvm;
    
    if (!irqfd->resampler) {
        // 标准irqfd：先assert再deassert
        kvm_set_irq(kvm, KVM_USERSPACE_IRQ_SOURCE_ID, irqfd->gsi, 1, false);
        kvm_set_irq(kvm, KVM_USERSPACE_IRQ_SOURCE_ID, irqfd->gsi, 0, false);
    } else {
        // Resampler模式（用于MSI等）
        kvm_set_irq(kvm, KVM_IRQFD_RESAMPLE_IRQ_SOURCE_ID,
                    irqfd->gsi, 1, false);
    }
}
```

#### 2.5 中断路由查找并注入到 VCPU

**函数：** `virt/kvm/irqchip.c:71` - `kvm_set_irq()`
```c
int kvm_set_irq(struct kvm *kvm, int irq_source_id, u32 irq, int level, bool line_status)
{
    struct kvm_kernel_irq_routing_entry irq_set[KVM_NR_IRQCHIPS];
    int ret = -1, i, idx;
    
    trace_kvm_set_irq(irq, level, irq_source_id);
    
    // 查找中断路由表
    idx = srcu_read_lock(&kvm->irq_srcu);
    i = kvm_irq_map_gsi(kvm, irq_set, irq);  // 根据GSI查找路由
    srcu_read_unlock(&kvm->irq_srcu, idx);
    
    // 遍历所有路由项，注入中断
    for (i--; i >= 0; i--) {
        int r;
        r = irq_set[i].set(&irq_set[i], kvm, irq_source_id, level, line_status);
        if (r < 0)
            continue;
        ret = r + ((ret < 0) ? 0 : ret);
    }
    
    return ret;
}
```

**中断路由注入：** 根据路由类型调用不同的注入函数
- `KVM_IRQ_ROUTING_IRQCHIP`: 注入到虚拟PIC/IOAPIC
- `KVM_IRQ_ROUTING_MSI`: MSI中断注入
- `KVM_IRQ_ROUTING_MSIX`: MSI-X中断注入

#### 2.6 注入到 Guest VCPU

最终通过架构相关代码（如 `arch/x86/kvm/x86.c` 或 `arch/arm64/kvm/arm.c`）将中断注入到 Guest VCPU：
- 设置 VCPU 中断标志
- 如果 VCPU 正在运行，触发中断处理
- 如果 VCPU 休眠，唤醒 VCPU

---

### 三、ioeventfd 机制（Guest → Host 通知）

#### 3.1 Guest 写入寄存器触发

Guest 写入 `VIRTIO_PCI_QUEUE_NOTIFY` 寄存器时，如果使用了 ioeventfd：

**函数：** `accel/kvm/kvm-all.c:1252` - `kvm_set_ioeventfd_mmio()`
```c
static int kvm_set_ioeventfd_mmio(int fd, hwaddr addr, uint32_t val,
                                   bool assign, uint32_t size, bool datamatch)
{
    struct kvm_ioeventfd iofd = {
        .datamatch = datamatch ? adjust_ioeventfd_endianness(val, size) : 0,
        .addr = addr,
        .len = size,
        .fd = fd,
    };
    
    if (datamatch)
        iofd.flags |= KVM_IOEVENTFD_FLAG_DATAMATCH;
    if (!assign)
        iofd.flags |= KVM_IOEVENTFD_FLAG_DEASSIGN;
    
    // 发送KVM_IOEVENTFD ioctl
    ret = kvm_vm_ioctl(kvm_state, KVM_IOEVENTFD, &iofd);
}
```

#### 3.2 KVM 内核处理 ioeventfd

KVM 内核监听 MMIO/PIO 访问，匹配地址后直接触发 eventfd，无需 VM exit，由用户态工作线程处理。

---

### 四、完整调用链总结

#### **Host → Guest 中断注入：**
```
QEMU:
virtio_notify() 
  → virtio_irq() 
  → virtio_notify_vector() 
  → virtio_pci_notify() 
  → event_notifier_set(guest_notifier)
    ↓ (eventfd_write写event注入中断)
KVM内核:
irqfd_wakeup() (等待队列回调)
  → schedule_work(&irqfd->inject)
    → irqfd_inject() (工作队列)
      → kvm_set_irq()
        → kvm_irq_map_gsi() (查找路由)
          → 架构相关中断注入函数
            → 注入到Guest VCPU
```

#### **Guest → Host 队列通知：**
```
Guest写入VIRTIO_PCI_QUEUE_NOTIFY
  ↓ (MMIO/PIO访问)
KVM内核:
匹配ioeventfd注册的地址
  → 触发eventfd
    ↓
QEMU用户态:
eventfd被poll/epoll检测到
  → virtio_queue_host_notifier_read()
    → virtio_queue_notify_vq()
      → vq->handle_output() (设备处理函数)
```


---

### 五、关键数据结构

**QEMU侧：**
- `EventNotifier`: 封装 eventfd
- `VirtIOIRQFD`: 存储 irqfd 相关信息
- `struct kvm_irqfd`: KVM ioctl 参数

**KVM内核侧：**
- `struct kvm_kernel_irqfd`: irqfd 内核结构
- `struct kvm_irq_routing_entry`: 中断路由表项
- `struct kvm`: KVM 虚拟机结构，包含中断路由表

---

### 六、性能优化要点

1. 零拷贝中断注入：irqfd 无需 VM exit，直接在 KVM 内核中注入
2. 原子中断注入：`kvm_arch_set_irq_inatomic()` 尝试原子注入，避免调度延迟
3. ioeventfd 零拷贝：Guest I/O 访问直接触发用户态，无需 VM exit
4. 批量操作：ioeventfd 支持批量注册以减少 ioctl 调用

该机制通过 eventfd 和 KVM ioctl 实现用户态与内核态协作，实现高效的中断通知。

