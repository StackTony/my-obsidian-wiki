
## Linux 内核锁机制全景介绍

---

### 一、锁机制总览

```
                        Linux 内核同步机制
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼────┐           ┌─────▼─────┐         ┌──────▼──────┐
   │ 忙等待锁 │           │  睡眠锁    │         │  无锁机制    │
   └────┬────┘           └─────┬─────┘         └──────┬──────┘
        │                      │                      │
   ┌────┴────┐           ┌─────┴─────┐          ┌─────┴─────┐
   │spinlock │           │ mutex     │          │ RCU       │
   │seqlock  │           │ semaphore │          │ atomic    │
   │bit spin │           │ rwsem     │          │ per-cpu   │
   └─────────┘           │ rt_mutex  │          │ seqcount  │
                         │ ww_mutex  │          │ lockless  │
                         └───────────┘          └───────────┘
```

#### 核心对比表

| 锁类型 | 等待方式 | 上下文限制 | 开销 | 适用场景 |
|--------|----------|------------|------|----------|
| **Spinlock** | 忙等待 | 任意上下文 | 极小 | 中断、极短临界区 |
| **Mutex** | 睡眠 | 仅进程上下文 | 中等 | 一般互斥、可睡眠 |
| **RWLock** | 忙等待 | 任意上下文 | 小 | 读多写少、短临界区 |
| **RW Semaphore** | 睡眠 | 仅进程上下文 | 中等 | 读多写少、长临界区 |
| **Seqlock** | 忙等待 | 任意上下文 | 小 | 读远多于写 |
| **RCU** | 无锁 | 任意上下文 | 读零 | 读极多写极少 |
| **Semaphore** | 睡眠 | 仅进程上下文 | 大 | 资源计数、同步 |
| **Atomic** | 原子操作 | 任意上下文 | 极小 | 简单计数/标志 |

---

### 二、Spinlock（自旋锁）

#### 核心概念

```
┌─────────────────────────────────────────────────────────────────┐
│                    Spinlock 核心思想                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  "忙等待"（Busy Waiting）：                                      │
│    获取失败 → 不睡眠，持续检查锁状态 → 占用 CPU                  │
│                                                                 │
│  适用条件：                                                      │
│    1. 持锁时间极短（通常 < 100 条指令，微秒级）                  │
│    2. 等待时间 < 上下文切换开销（~5-10μs）                       │
│    3. 可用于任意上下文（中断、软中断、进程）                     │
│                                                                 │
│  核心原则：                                                      │
│    "快进快出，绝不睡眠"                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 基本原理

```
┌─────────────────────────────────────┐
│         CPU1 获取锁                  │
│         lock->locked = 1            │
└─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│    CPU2 尝试获取 → 失败               │
│    while (lock->locked)             │
│        cpu_relax();  // 自旋等待     │
└─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│    CPU1 释放锁                       │
│    lock->locked = 0                 │
└─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│    CPU2 获取成功                     │
└─────────────────────────────────────┘
```

#### 锁实现演进历史

```
┌─────────────────────────────────────────────────────────────────┐
│              Spinlock 实现演进（解决公平性问题）                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  第1代: 简单 Test-And-Set 锁                                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ while (test_and_set(&lock->locked)) {                     │ │
│  │     cpu_relax();                                          │ │
│  │ }                                                         │ │
│  │ 问题: 无公平性，可能导致饥饿                              │ │
│  │       后来的等待者可能先获得锁                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                          ↓                                      │
│  第2代: Ticket Lock（排队锁，Linux 早期采用）                    │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ struct ticket_lock {                                      │ │
│  │     unsigned int next;    // 下一个可用的 ticket          │ │
│  │     unsigned int owner;   // 当前持有者的 ticket          │ │
│  │ };                                                        │ │
│  │                                                           │ │
│  │ // 获取锁                                                  │ │
│  │ my_ticket = atomic_fetch_add(&next, 1);                   │ │
│  │ while (atomic_read(&owner) != my_ticket)                  │ │
│  │     cpu_relax();                                          │ │
│  │                                                           │ │
│  │ // 释放锁                                                  │ │
│  │ atomic_inc(&owner);                                       │ │
│  │                                                           │ │
│  │ 优势: FIFO 公平性，按获取顺序排队                          │ │
│  │ 问题: 所有等待者检查同一 owner 变量                        │ │
│  │       缓存行竞争严重（cache line contention）              │ │
│  └───────────────────────────────────────────────────────────┘ │
│                          ↓                                      │
│  第3代: MCS Lock / Queued Spinlock（现代 Linux，x86）            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 每个 CPU 在自己的本地节点上自旋                            │ │
│  │ 通过链表传递锁，避免缓存行竞争                              │ │
│  │                                                           │ │
│  │ struct mcs_node {                                         │ │
│  │     struct mcs_node *next;                                │ │
│  │     int locked;           // 本地自旋变量                  │ │
│  │ };                                                        │ │
│  │                                                           │ │
│  │ 优势: 每个等待者在本地变量上自旋                            │ │
│  │       大幅减少缓存行争用                                   │ │
│  │       NUMA 系统性能优异                                    │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 数据结构

```c
typedef struct spinlock {
    union {
        struct raw_spinlock rlock;  // 架构相关实现
#ifdef CONFIG_DEBUG_SPINLOCK
        unsigned int magic, owner_cpu;
        void *owner;
#endif
    };
} spinlock_t;

struct raw_spinlock {
    arch_spinlock_t raw_lock;  // 架构相关
#ifdef CONFIG_DEBUG_SPINLOCK
    unsigned int magic, owner_cpu;
    void *owner;
#endif
};

// x86 queued spinlock 结构
typedef struct qspinlock {
    union {
        atomic_t val;          // 综合状态值
        struct {
            u8    locked;      // 0: 未锁, 1: 已锁
            u8    pending;     // 等待成为下一个持有者
            u16   tail;        // 队列尾部 CPU 编码
        };
    };
} arch_spinlock_t;
```

#### 架构相关实现（x86）

```c
// x86 使用 queued spinlock（CONFIG_QUEUED_SPINLOCKS）

// 获取锁流程
static __always_inline void queued_spin_lock(struct qspinlock *lock)
{
    // 快速路径：尝试直接获取
    if (atomic_try_cmpxchg_acquire(&lock->val, 0, 1))
        return;                 // 成功获取
    
    // 慢速路径：加入等待队列
    queued_spin_lock_slowpath(lock);
}

// 慢速路径核心逻辑
void queued_spin_lock_slowpath(struct qspinlock *lock, u32 val)
{
    struct mcs_spinlock *node;
    
    // 1. 获取本地 MCS 节点
    node = this_cpu_ptr(&mcs_nodes[0]);
    node->locked = 0;
    node->next = NULL;
    
    // 2. 加入队列尾部
    tail = encode_tail(cpu, idx);
    old = atomic_xchg_tail(&lock->tail, tail);
    
    if (old) {                  // 队列非空，需要等待
        // 3. 链接到前一个节点
        prev = decode_tail(old);
        WRITE_ONCE(prev->next, node);
        
        // 4. 在本地变量上自旋（避免缓存争用！）
        while (!READ_ONCE(node->locked))
            cpu_relax();
    }
    
    // 5. 现在轮到自己，等待 pending 位清除
    while (atomic_read(&lock->val) & _Q_PENDING_MASK)
        cpu_relax();
    
    // 6. 获取锁
    atomic_set_release(&lock->locked, 1);
}
```

#### 架构相关实现（ARM）

```c
// ARM64 使用 LSE 扩展指令（更高效）
static inline void arch_spin_lock(arch_spinlock_t *lock)
{
    unsigned int tmp;
    
    // 使用 LSE 的 CAS 指令
    asm volatile(
        "1: ldaxr   %w[tmp], [%[lock]]\n"         // 加载并获取独占
        "   cbnz    %w[tmp], 2f\n"                // 已锁，跳转等待
        "   stxr    %w[tmp], %w[val], [%[lock]]\n" // 尝试写入 1
        "   cbnz    %w[tmp], 1b\n"                // 写入失败，重试
        "   ret\n"
        "2: sevl\n"                               // 发送事件
        "   wfe\n"                                // 等待事件（低功耗！）
        "   ldaxr  %w[tmp], [%[lock]]\n"
        "   cbnz   %w[tmp], 2b\n"
        "   jmp    1b\n"
    );
}

// WFE（Wait For Event）优化：
//   - 不是纯粹的自旋，而是低功耗等待
//   - 锁释放时发送 SEV（Send Event）唤醒等待者
//   - 比 pure spinning 更节能
```

#### raw_spinlock vs spinlock

```c
/*
 * raw_spinlock: "真正的"自旋锁
 *   - 绝不自旋期间睡眠
 *   - 用于关键路径（如中断、调度器）
 *   - 不受 PREEMPT_RT 影响
 *
 * spinlock: 可能被 RT 内核转换为 rt_mutex
 *   - CONFIG_PREEMPT_RT 下自动变为可睡眠锁
 *   - 用于一般内核代码
 *   - 保持 API 兼容性
 */

// 定义
typedef struct spinlock {
    struct raw_spinlock rlock;
} spinlock_t;

// 在 RT 内核中
#ifdef CONFIG_PREEMPT_RT
typedef struct {
    struct rt_mutex_base lock;
} spinlock_t;
#endif

// 使用规则:
// - 调度器、中断核心代码 → 必须用 raw_spinlock
// - 一般驱动、文件系统 → 用 spinlock
// - 在 raw_spinlock 中禁止调用任何可能睡眠的函数
```

#### API 及变体完整详解

```c
// ═══════════════════════════════════════════════════════════════
//                     Spinlock API 变体矩阵
// ═══════════════════════════════════════════════════════════════

//                    基础版本    禁用中断版本    禁用下半部版本
//                    ──────────────────────────────────────────
// 非保存/恢复        spin_lock     spin_lock_irq    spin_lock_bh
//                    spin_unlock   spin_unlock_irq  spin_unlock_bh
//
// 保存/恢复          -             spin_lock_irqsave    -
//                    -             spin_unlock_irqrestore
//
// 尝试获取           spin_trylock  spin_trylock_irq    spin_trylock_bh
//                                  spin_trylock_irqsave

// ═══════════════════════════════════════════════════════════════
//                     基础 API
// ═══════════════════════════════════════════════════════════════

// 基础 API
void spin_lock(spinlock_t *lock);
void spin_unlock(spinlock_t *lock);
int spin_trylock(spinlock_t *lock);

// 禁用本地中断
void spin_lock_irq(spinlock_t *lock);
void spin_unlock_irq(spinlock_t *lock);
void spin_lock_irqsave(spinlock_t *lock, unsigned long flags);
void spin_unlock_irqrestore(spinlock_t *lock, unsigned long flags);

// 禁用下半部
void spin_lock_bh(spinlock_t *lock);
void spin_unlock_bh(spinlock_t *lock);

// ═══════════════════════════════════════════════════════════════
//                     各变体适用场景
// ═══════════════════════════════════════════════════════════════

/*
 * spin_lock / spin_unlock
 *   场景: 与中断无交集，或已在中断上下文中
 *   示例: 同 CPU 上的软中断之间、进程上下文（无中断共享）
 */

/*
 * spin_lock_irq / spin_unlock_irq
 *   场景: 进程上下文与中断共享数据
 *   问题: 会无差别启用所有中断（危险！）
 */

void dangerous_example(void) {
    spin_lock_irq(&lock);
    /* ... */
    spin_unlock_irq(&lock);   // 启用所有中断，可能改变外部状态
}

/*
 * spin_lock_irqsave / spin_unlock_irqrestore
 *   场景: 进程上下文与中断共享数据（推荐）
 *   优势: 保存并恢复原始中断状态，安全
 */

void safe_example(void) {
    unsigned long flags;
    spin_lock_irqsave(&lock, flags);
    /* ... */
    spin_unlock_irqrestore(&lock, flags);  // 恢复原始状态
}

/*
 * spin_lock_bh / spin_unlock_bh
 *   场景: 进程上下文与软中断共享数据
 *   操作: 禁用软中断（local_bh_disable）
 *   注意: 不禁用硬件中断
 */

void softirq_example(void) {
    spin_lock_bh(&lock);
    /* 与软中断共享的数据 */
    spin_unlock_bh(&lock);
}

// ═══════════════════════════════════════════════════════════════
//                     变体选择决策树
// ═══════════════════════════════════════════════════════════════

/*
 * 是否与硬件中断共享数据？
 *   是 → spin_lock_irqsave
 *   否 → 是否与软中断共享数据？
 *         是 → spin_lock_bh
 *         否 → spin_lock
 *
 * 已在中断上下文中？
 *   硬件中断 → spin_lock（无需再禁用）
 *   软中断   → spin_lock（已在软中断中）
 */
```

#### 中断上下文使用详解

```c
// 硬件中断处理函数
irqreturn_t my_irq_handler(int irq, void *dev_id)
{
    // 在中断上下文，中断已被禁用
    // 无需 spin_lock_irqsave
    spin_lock(&my_lock);
    
    /* 处理共享数据 */
    
    spin_unlock(&my_lock);
    return IRQ_HANDLED;
}

// 进程上下文与中断共享
void process_shared_with_irq(void)
{
    unsigned long flags;
    
    // 必须禁用本地中断
    // 否则：持锁期间中断到来 → 中断处理函数尝试获取同一锁 → 死锁
    spin_lock_irqsave(&my_lock, flags);
    
    /* 操作共享数据 */
    
    spin_unlock_irqrestore(&my_lock, flags);
}

// 软中断示例
void softirq_handler(struct softirq_action *h)
{
    spin_lock(&softirq_lock);
    /* ... */
    spin_unlock(&softirq_lock);
}

// 进程上下文与软中断共享
void process_shared_with_softirq(void)
{
    // 只需禁用软中断，不禁用硬件中断
    spin_lock_bh(&softirq_lock);
    /* ... */
    spin_unlock_bh(&softirq_lock);
}

// 多 CPU 中断竞争（关键点！）
/*
 * spin_lock_irqsave 只禁用【本地 CPU】的中断
 * 其他 CPU 的中断仍可运行
 * 
 * 因此：锁提供跨 CPU 互斥
 *       irqsave 防止【同 CPU】递归获取死锁
 */
```

#### 内核抢占与 Spinlock

```c
/*
 * CONFIG_PREEMPT（可抢占内核）:
 *   进程可在持锁时被抢占
 *   spin_lock 自动调用 preempt_disable
 *   spin_unlock 自动调用 preempt_enable
 *
 * CONFIG_PREEMPT_RT（实时内核）:
 *   spinlock 被转换为 rt_mutex
 *   可以睡眠，但保持了 API 兼容性
 */

// preempt 内核下的 spin_lock 展开
static inline void spin_lock(spinlock_t *lock)
{
    raw_spin_lock(&lock->rlock);
    // 内部已包含 preempt_disable
}

// preempt_count 状态
/*
 * preempt_count 布局:
 *   bit 0-7:  preempt count（ preempt_disable 层数）
 *   bit 8-15: softirq count（local_bh_disable 层数）
 *   bit 16-23: hardirq count（irq 层数）
 *   bit 24:    NMI count
 *
 * spin_lock → preempt_count++
 * spin_unlock → preempt_count--
 * preempt_count > 0 → 不可抢占
 */

// 检查当前上下文
int in_interrupt(void);      // preempt_count & (hardirq | softirq)
int in_irq(void);            // preempt_count & hardirq
int in_softirq(void);        // preempt_count & softirq
int preempt_count(void);     // 返回完整计数
```

#### 使用场景示例

```c
// ✓ 场景1: 中断处理函数与进程上下文共享数据
spinlock_t my_lock;

// 进程上下文
void process_context(void) {
    unsigned long flags;
    spin_lock_irqsave(&my_lock, flags);    // 禁用中断并保存状态
    /* 访问共享数据 */
    spin_unlock_irqrestore(&my_lock, flags);
}

// 中断上下文
irqreturn_t my_handler(int irq, void *dev) {
    spin_lock(&my_lock);        // 中断中无需禁用中断
    /* 访问共享数据 */
    spin_unlock(&my_lock);
    return IRQ_HANDLED;
}

// ✓ 场景2: 极短临界区
spin_lock(&lock);
counter++;      // 单个操作
spin_unlock(&lock);

// ✓ 场景3: 网络包统计（中断上下文）
struct net_device_stats {
    spinlock_t lock;
    unsigned long rx_packets;
    unsigned long tx_packets;
};

irqreturn_t net_irq_handler(int irq, void *dev)
{
    struct net_device *ndev = dev;
    
    spin_lock(&ndev->stats.lock);
    ndev->stats.rx_packets++;
    spin_unlock(&ndev->stats.lock);
    
    return IRQ_HANDLED;
}

// ✓ 场景4: 驱动中断与进程共享
struct my_device {
    spinlock_t irq_lock;
    void *data;
};

// 进程上下文
ssize_t device_read(struct file *f, char __user *buf, size_t len, loff_t *off)
{
    struct my_device *dev = f->private_data;
    unsigned long flags;
    
    spin_lock_irqsave(&dev->irq_lock, flags);
    /* 从 dev->data 读取 */
    spin_unlock_irqrestore(&dev->irq_lock, flags);
    
    return len;
}

// ✓ 场景5: 调度器核心（raw_spinlock）
struct rq {
    raw_spinlock_t lock;       // 必须用 raw_spinlock！
    struct task_struct *curr;
    unsigned long nr_running;
};

void scheduler_tick(void)
{
    raw_spin_lock(&rq->lock);
    /* 更新运行队列 */
    raw_spin_unlock(&rq->lock);
}
```

#### 常见错误示例

```c
// ═══════════════════════════════════════════════════════════════
//                       常见错误示例
// ═══════════════════════════════════════════════════════════════

// 错误1: 在 spinlock 中睡眠
spin_lock(&lock);
kmalloc(size, GFP_KERNEL);      // 可能睡眠！
spin_unlock(&lock);
// GFP_ATOMIC 才是安全的

// 错误2: 持锁时间过长
spin_lock(&lock);
for (i = 0; i < 10000; i++) {
    complex_operation();        // 每次迭代耗时
}
spin_unlock(&lock);
// 应改用 mutex

// 错误3: 错误的中断处理
void process_context(void) {
    spin_lock(&lock);           // 没禁用中断
    /* 如果此时中断到来并尝试获取 lock，死锁 */
    spin_unlock(&lock);
}

// 错误4: 单 CPU 上递归获取
void func_a(void) {
    spin_lock(&lock);
    func_b();                    // func_b 也获取 lock → 死锁
    spin_unlock(&lock);
}

// 错误5: 错误使用 spin_unlock_irq
void nested_irq_example(void) {
    spin_lock_irqsave(&lock1, flags1);
    spin_lock_irq(&lock2);       // 禁用中断（已是禁用状态）
    /* ... */
    spin_unlock_irq(&lock2);     // 启用中断！但 flags1 仍要求禁用
    // 此时中断可能打断，破坏 lock1 的保护
    spin_unlock_irqrestore(&lock1, flags1);
}

// ✗ 错误: 在 spinlock 中睡眠
spin_lock(&lock);
copy_from_user(buf, ...);  // 可能睡眠！
spin_unlock(&lock);
```

#### 最佳实践

```c
// ═══════════════════════════════════════════════════════════════
//                       最佳实践
// ═══════════════════════════════════════════════════════════════

// 最佳实践1: 最小临界区
spin_lock(&lock);
shared_var++;                   // 仅操作共享变量
spin_unlock(&lock);

// 最佳实践2: 使用 irqsave 而非 irq
unsigned long flags;
spin_lock_irqsave(&lock, flags);
/* ... */
spin_unlock_irqrestore(&lock, flags);

// 最佳实践3: 嵌套锁时，irqsave 放在最外层
spin_lock_irqsave(&outer_lock, flags);
spin_lock(&inner_lock);
/* ... */
spin_unlock(&inner_lock);
spin_unlock_irqrestore(&outer_lock, flags);

// 最佳实践4: 使用 GFP_ATOMIC
spin_lock(&lock);
ptr = kmalloc(size, GFP_ATOMIC);   // 安全
spin_unlock(&lock);

// 最佳实践5: 使用 trylock 避免死锁风险
if (spin_trylock(&lock)) {
    /* 获取成功 */
    spin_unlock(&lock);
} else {
    /* 做其他工作，稍后重试 */
}

// 最佳实践6: 明确注释锁的保护范围
/*
 * @lock: 保护 shared_counter 和 shared_list
 *        在修改这两个变量前必须获取
 */
spinlock_t shared_lock;
int shared_counter;
struct list_head shared_list;

// 规则总结:
// 1. 持锁时间必须极短（微秒级）
// 2. 绝对不能睡眠
// 3. 注意死锁（同一 CPU 递归获取）
// 4. 选择正确的变体
// 5. 嵌套锁保持统一顺序
// 6. 尽量缩短持锁时间
```

#### 性能分析

```c
// ═══════════════════════════════════════════════════════════════
//                     性能开销分析
// ═══════════════════════════════════════════════════════════════

/*
 * 无竞争时（单 CPU 或快速路径）:
 *   spin_lock:      ~50-100 CPU cycles
 *   spin_unlock:    ~10-20 CPU cycles
 * 
 * 有竞争时（多 CPU 等待）:
 *   传统 spinlock:  持续消耗 CPU，等待者都检查同一变量
 *   queued lock:    等待者在本地变量自旋，减少缓存争用
 * 
 * 缓存行争用分析:
 *   传统锁: N 个等待者 × 每 N 次检查 × 缓存失效
 *   queued: 每个等待者 × 仅检查自己的本地变量 × 无争用
 */

// 性能测试代码示例
static spinlock_t test_lock;
static unsigned long counter;

void benchmark_spinlock(void)
{
    int i;
    unsigned long start, end;
    
    start = rdtsc();
    for (i = 0; i < 1000000; i++) {
        spin_lock(&test_lock);
        counter++;
        spin_unlock(&test_lock);
    }
    end = rdtsc();
    
    printk("spinlock cycles per op: %lu\n", (end - start) / 1000000);
}

// ═══════════════════════════════════════════════════════════════
//                     与其他锁性能对比
// ═══════════════════════════════════════════════════════════════

/*
 * 相对开销（无竞争，单次操作）:
 *
 * atomic_inc:          ████ 3x
 * spin_lock/unlock:    ████████████ 4x
 * mutex_lock/unlock:   ████████████████████ 8x
 * semaphore:           ████████████████████████ 10x
 *
 * 持锁时间 vs 锁选择:
 *
 * < 100 cycles:    atomic 或无锁
 * < 1μs:           spinlock
 * > 1μs:           mutex（考虑上下文切换）
 * > 10μs:          mutex（spinlock 浪费 CPU）
 * > 1ms:           mutex 或 semaphore
 */
```

#### 调试工具

```c
// ═══════════════════════════════════════════════════════════════
//                     Spinlock 调试配置
// ═══════════════════════════════════════════════════════════════

/*
 * CONFIG_DEBUG_SPINLOCK:
 *   - 检测递归获取
 *   - 检测未初始化使用
 *   - 检测错误释放
 *   - 记录 owner_cpu 和 owner
 */

/*
 * CONFIG_DEBUG_LOCK_ALLOC:
 *   - 使用 lockdep 检测锁依赖
 *   - 检测潜在的锁顺序死锁
 */

/*
 * CONFIG_LOCK_STAT:
 *   - 统计锁持有时间
 *   - 统计等待时间
 *   - 统计争用次数
 */

// lockdep 使用示例
static DEFINE_SPINLOCK(lock1);
static DEFINE_SPINLOCK(lock2);

void test_lockdep(void)
{
    spin_lock(&lock1);
    spin_lock(&lock2);    // lockdep 记录顺序: lock1 → lock2
    spin_unlock(&lock2);
    spin_unlock(&lock1);
}

void bad_order(void)
{
    spin_lock(&lock2);    // lockdep 检测到: lock2 → lock1
    spin_lock(&lock1);    // 与之前顺序相反，报告潜在死锁
    spin_unlock(&lock1);
    spin_unlock(&lock2);
}

// 查看锁统计信息
// cat /proc/lock_stat
// 或使用 lockdep 的 debugfs 接口
```

#### Spinlock 总结口诀

```
┌─────────────────────────────────────────────────────────────────┐
│                   Spinlock 使用口诀                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  中断共享 irqsave，软中断共享 bh。                               │
│  纯进程上下文用基础版本。                                        │
│  持锁时间要极短，绝不能睡眠。                                    │
│  嵌套锁要有序，irqsave 放外层。                                  │
│  调度器用 raw_spinlock，RT 内核自动变 mutex。                    │
│  高竞争用 queued lock，缓存争用要避免。                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   快速选择指南                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  上下文类型？                                                    │
│  ├─ 硬件中断    → spin_lock（中断已禁用）                        │
│  ├─ 软中断      → spin_lock（在软中断中）                        │
│  └─ 进程上下文  → 共享对象？                                     │
│                   ├─ 与硬件中断  → spin_lock_irqsave             │
│                   ├─ 与软中断    → spin_lock_bh                  │
│                   └─ 无共享      → spin_lock                     │
│                                                                 │
│  持锁时间？                                                      │
│  ├─ < 1μs       → spinlock                                      │
│  ├─ > 1μs       → 考虑 mutex                                    │
│  └─ > 10μs      → 必须用 mutex                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 三、Mutex（互斥锁）

#### 原理

```
┌─────────────────────────────────────────────────────────────┐
│                      Mutex 核心状态                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│    状态0 ( unlocked )    ──────→    状态1 ( locked )        │
│         │                               │                   │
│    无持有者                        有持有者                   │
│    可被获取                        需要等待                   │
│                                                             │
│    获取: atomic_dec_return() == 0 ? 成功 : 等待              │
│    释放: atomic_inc_return() → 唤醒等待者                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘

获取锁流程:
┌─────────────────────────────────────┐
│     Task A 尝试获取 mutex           │
│     mutex_lock(&m)                  │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│     atomic 尝试将 count 减 1        │
│     if (count == 0)                 │
│         → 成功获取，设置 owner      │
│     else                            │
│         → 需要等待                  │
└─────────────────────────────────────┘
                │
        ┌───────┴───────┐
        │               │
    成功获取         需要等待
        │               │
        ▼               ▼
┌───────────────┐ ┌─────────────────────────────────────┐
│ 进入临界区     │ │ 进入等待队列                          │
│ 持有锁        │ │ TASK_ON_RQ                           │
│ 设置 owner    │ │ schedule() → 睡眠让出 CPU             │
└───────────────┘ └─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────┐
│     Task A 释放 mutex               │
│     mutex_unlock(&m)                │
│     atomic_inc(count)               │
│     唤醒等待队列中的首个任务         │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│     Task B 唤醒                    │
│     从等待队列移除                   │
│     设置 owner = Task B             │
│     进入临界区                      │
└─────────────────────────────────────┘
```

#### 数据结构

```c
struct mutex {
    atomic_long_t       owner;         // 持有者（含锁状态信息）
    atomic_t            count;         // 计数器：0=未锁，1=已锁
    spinlock_t          wait_lock;     // 保护等待队列
    struct list_head    wait_list;     // 等待队列
#ifdef CONFIG_DEBUG_MUTEXES
    void                *magic;        // 调试魔数
    struct task_struct  *owner_task;   // 调试：持有者
    const char          *name;         // 调试：锁名
    void                *dep_map;      // 锁依赖图
#endif
#ifdef CONFIG_MUTEX_SPIN_ON_OWNER
    struct optimistic_spin_queue osq;  // 乐观自旋队列
#endif
};

/*
 * owner 字段编码:
 *   - 低2位: 标志位
 *     bit 0: MUTEX_FLAG_WAITERS - 有等待者
 *     bit 1: MUTEX_FLAG_HANDOFF  - 正在交接
 *   - 高位: task_struct 指针（持有者）
 */
```

#### API

```c
// 定义与初始化
DEFINE_MUTEX(name);                    // 静态定义
void mutex_init(struct mutex *lock);   // 动态初始化

// 基础操作
void mutex_lock(struct mutex *lock);   // 获取锁（不可中断）
void mutex_unlock(struct mutex *lock); // 释放锁
int mutex_trylock(struct mutex *lock); // 非阻塞尝试获取

// 可中断版本
int mutex_lock_interruptible(struct mutex *lock);   // 可被信号中断
int mutex_lock_killable(struct mutex *lock);        // 仅可被 SIGKILL 中断

// 带超时版本
int mutex_lock_io(struct mutex *lock);              // I/O 超时版本（5min）

// 条件判断
int mutex_is_locked(struct mutex *lock);            // 检查是否被持有
```

#### 使用示例

```c
static DEFINE_MUTEX(data_mutex);
struct shared_data *global_data;

// 基本用法
void update_data(int new_value) {
    mutex_lock(&data_mutex);
    global_data->value = new_value;   // 临界区，可以睡眠
    mutex_unlock(&data_mutex);
}

// 可中断版本（用户空间调用）
long my_ioctl(struct file *file, unsigned int cmd, unsigned long arg) {
    if (mutex_lock_interruptible(&data_mutex))
        return -ERESTARTSYS;          // 被信号中断，返回重启
    
    /* 临界区操作 */
    copy_from_user(buf, arg, size);   // 可安全睡眠！
    
    mutex_unlock(&data_mutex);
    return 0;
}

// trylock 非阻塞
void try_update(void) {
    if (!mutex_trylock(&data_mutex)) {
        /* 锁不可用，做其他事 */
        schedule_other_work();
        return;
    }
    /* 临界区 */
    do_update();
    mutex_unlock(&data_mutex);
}

// 正确的返回路径处理
int safe_operation(void) {
    int ret = 0;
    
    if (mutex_lock_interruptible(&data_mutex))
        return -ERESTARTSYS;
    
    if (check_condition_failed()) {
        ret = -EINVAL;
        goto out;                     // 正确跳转到释放
    }
    
    if (allocate_failed()) {
        ret = -ENOMEM;
        goto out;
    }
    
    /* 正常处理 */
    ret = do_operation();
    
out:
    mutex_unlock(&data_mutex);        // 统一释放点
    return ret;
}
```

#### 乐观自旋（Optimistic Spinning）

```
┌─────────────────────────────────────────────────────────────┐
│                    乐观自旋优化策略                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  传统 mutex 等待:                                           │
│    获取失败 → 加入等待队列 → schedule() → 睡眠             │
│    问题: 上下文切换开销大（~5-10μs）                        │
│                                                             │
│  乐观自旋优化:                                               │
│    获取失败 → 先短时间自旋等待 → 仍失败才加入等待队列      │
│    优势: 如果持有者很快释放，避免上下文切换                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘

自旋条件检查:
┌─────────────────────────────────────┐
│ 1. 持有者正在运行（其他 CPU）       │  // 可能很快释放
│ 2. 只有一个等待者                   │  // 自旋有意义
│ 3. 没有更高优先级任务等待           │
│ 4. 自旋次数未超限                   │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ while (条件满足 && !获取成功)       │
│     cpu_relax();                    │  // 短暂自旋
└─────────────────────────────────────┘
        │
        ▼ (自旋超限或条件不满足)
┌─────────────────────────────────────┐
│ 加入等待队列，真正睡眠              │
└─────────────────────────────────────┘

相关配置:
CONFIG_MUTEX_SPIN_ON_OWNER    // 启用乐观自旋
CONFIG_LOCK_SPIN_ON_OWNER     // 通用的乐观自旋框架
```

#### Mutex 特殊特性

```c
/*
 * 1. 优先级继承（Priority Inheritance）
 *    - rt_mutex 内嵌在 mutex 中（CONFIG_RT_MUTEX）
 *    - 当高优先级任务等待低优先级持有者时，
 *      暂时提升持有者优先级，防止优先级反转
 *
 * 2. 所有权语义
 *    - mutex 有明确的 owner（持有者）
 *    - 只有持有者才能释放锁（严格所有权）
 *    - 便于调试和死锁检测
 *
 * 3. 递归支持（可选）
 *    - CONFIG_MUTEX_DEBUG 下支持递归检测
 *    - 同一任务多次获取同一 mutex 会死锁
 *
 * 4. 锁依赖检测
 *    - CONFIG_LOCKDEP 下跟踪锁获取顺序
 *    - 检测潜在的锁顺序死锁
 */

// 优先级反转示意:
// Task H (高优先级) → 等待 mutex → Task L (低优先级) 持有
// Task M (中优先级) 抢占 Task L → Task H 被 M 间接阻塞
//
// 优先级继承:
// Task L 持有 mutex, Task H 等待
// → 系统暂时提升 L 到 H 的优先级
// → L 快速完成并释放
// → H 获取锁，L 恢复原优先级
```

#### 注意事项

```c
// ✓ 正确: 进程上下文使用
void process_context_func(void) {
    mutex_lock(&lock);
    copy_from_user(buf, ...);   // 可以睡眠
    mutex_unlock(&lock);
}

// ✗ 错误: 中断上下文使用
irqreturn_t irq_handler(int irq, void *dev) {
    mutex_lock(&lock);          // 死锁！中断不能睡眠
    /* ... */
    mutex_unlock(&lock);
    return IRQ_HANDLED;
}

// ✗ 错误: 持有者之外释放
void wrong_release(void) {
    mutex_unlock(&lock);        // 当前任务不持有锁！
    // 可能导致: 等待者错误唤醒、锁状态混乱
}

// ✗ 错误: 递归获取
void recursive_bad(void) {
    mutex_lock(&lock);
    inner_func();               // 内部再次 mutex_lock(&lock) → 死锁
    mutex_unlock(&lock);
}

// ✓ 正确: 嵌套不同锁（注意顺序）
void nested_locks(void) {
    mutex_lock(&lock1);
    mutex_lock(&lock2);         // 不同锁，但要保持全局顺序
    /* ... */
    mutex_unlock(&lock2);
    mutex_unlock(&lock1);
}

// 规则总结:
// 1. 只在进程上下文使用
// 2. 可以在持锁期间睡眠
// 3. 只有持有者可以释放
// 4. 不允许递归获取同一锁
// 5. 嵌套锁保持统一顺序
// 6. 尽量缩短持锁时间
```

#### Mutex vs Spinlock vs Semaphore

```
┌──────────────────────────────────────────────────────────────────┐
│                     三种锁核心对比                                │
├────────────────┬─────────────────┬─────────────────┬─────────────┤
│     特性       │    Spinlock     │     Mutex       │  Semaphore  │
├────────────────┼─────────────────┼─────────────────┼─────────────┤
│ 等待方式       │ 忙等待（自旋）   │ 睡眠等待        │ 睡眠等待    │
│ 上下文限制     │ 任意上下文      │ 仅进程上下文    │ 仅进程上下文│
│ 所有权         │ 无              │ 有（严格）      │ 无          │
│ 计数语义       │ 0/1（二值）     │ 0/1（二值）     │ 任意正整数  │
│ 递归获取       │ 需要特殊处理    │ 不支持          │ 不支持      │
│ 优先级继承     │ 不支持          │ 支持（rt_mutex）│ 不支持      │
│ 乐观自旋       │ 内置            │ 支持（可选）    │ 不支持      │
│ 持锁时睡眠     │ 绝对禁止        │ 允许            │ 允许        │
│ 开销           │ 极小            │ 中等            │ 较大        │
│ 适用场景       │ 中断/极短临界区 │ 一般互斥        │ 资源计数    │
└────────────────┴─────────────────┴─────────────────┴─────────────┘

典型开销对比（无竞争时）:
┌─────────────────────────────────────┐
│ spin_lock:    ~50-100 cycles        │
│ mutex_lock:   ~100-200 cycles       │
│ semaphore:    ~200-300 cycles       │
│                                     │
│ 竞争时:                              │
│ spinlock:     持续消耗 CPU          │
│ mutex:        短暂自旋 + 上下文切换 │
│ semaphore:    直接上下文切换        │
└─────────────────────────────────────┘
```

---

### 四、RWLock（读写自旋锁）

#### 原理

```
读锁获取：
┌─────────────────────────────────┐
│  lock->readers++                │
│  if (lock->writer) fail        │
└─────────────────────────────────┘

写锁获取：
┌─────────────────────────────────┐
│  if (lock->readers == 0 &&     │
│      !lock->writer)             │
│      lock->writer = 1           │
│  else fail                      │
└─────────────────────────────────┘

特点: 多读者可并行，写者独占
```

#### API

```c
// 初始化
DEFINE_RWLOCK(name);
rwlock_init(&lock);

// 读锁
void read_lock(rwlock_t *lock);
void read_unlock(rwlock_t *lock);
void read_lock_irq(rwlock_t *lock);
void read_unlock_irq(rwlock_t *lock);
void read_lock_irqsave(rwlock_t *lock, unsigned long flags);
void read_unlock_irqrestore(rwlock_t *lock, unsigned long flags);

// 写锁
void write_lock(rwlock_t *lock);
void write_unlock(rwlock_t *lock);
void write_lock_irq(rwlock_t *lock);
void write_unlock_irq(rwlock_t *lock);
void write_lock_irqsave(rwlock_t *lock, unsigned long flags);
void write_unlock_irqrestore(rwlock_t *lock, unsigned long flags);

// 尝试获取
int read_trylock(rwlock_t *lock);
int write_trylock(rwlock_t *lock);
```

#### 使用示例

```c
rwlock_t data_lock;
struct shared_data data;

// 读路径（可并发）
void read_data(void) {
    unsigned long flags;
    read_lock_irqsave(&data_lock, flags);
    /* 读取共享数据 */
    int val = data.value;
    read_unlock_irqrestore(&data_lock, flags);
    return val;
}

// 写路径（独占）
void write_data(int new_val) {
    unsigned long flags;
    write_lock_irqsave(&data_lock, flags);
    /* 修改共享数据 */
    data.value = new_val;
    write_unlock_irqrestore(&data_lock, flags);
}
```

#### 缺点

```
问题1: 写者饥饿
┌────────────────────────────────────┐
│ 读者A获取读锁                       │
│ 读者B获取读锁                       │
│ 写者W等待...                        │
│ 读者C获取读锁（写者仍在等）          │
│ 读者D获取读锁...                    │
│ 写者可能永远等待                     │
└────────────────────────────────────┘

问题2: 读侧开销
┌────────────────────────────────────┐
│ 每次 read_lock 都要原子更新计数器   │
│ 高并发读时缓存行激烈争用            │
└────────────────────────────────────┘
```

---

### 五、RW Semaphore（读写信号量）

#### 特性

```
┌─────────────────────────────────────┐
│ 睡眠锁版本                           │
│ 支持读写并发                         │
│ 进程上下文专用                       │
│ 适合长时间持锁                       │
└─────────────────────────────────────┘
```

#### 数据结构

```c
struct rw_semaphore {
    atomic_long_t count;          // 计数器
    atomic_long_t owner;          // 写者/读者
    struct list_head wait_list;   // 等待队列
#ifdef CONFIG_RWSEM_SPIN_ON_OWNER
    struct optimistic_spin_queue osq;  // 乐观自旋
#endif
};
```

#### API

```c
// 初始化
DECLARE_RWSEM(name);
void init_rwsem(struct rw_semaphore *sem);

// 读锁（可睡眠）
void down_read(struct rw_semaphore *sem);
int down_read_trylock(struct rw_semaphore *sem);
int down_read_interruptible(struct rw_semaphore *sem);
int down_read_killable(struct rw_semaphore *sem);
void up_read(struct rw_semaphore *sem);

// 写锁（可睡眠）
void down_write(struct rw_semaphore *sem);
int down_write_trylock(struct rw_semaphore *sem);
int down_write_killable(struct rw_semaphore *sem);
void up_write(struct rw_semaphore *sem);

// 降级写锁为读锁
void downgrade_write(struct rw_semaphore *sem);
```

#### 使用示例

```c
static DECLARE_RWSEM(policy_rwsem);

// 读路径
struct policy *get_policy(void) {
    down_read(&policy_rwsem);
    struct policy *p = current_policy;
    up_read(&policy_rwsem);
    return p;
}

// 写路径
void update_policy(struct policy *new) {
    down_write(&policy_rwsem);
    old = current_policy;
    current_policy = new;
    up_write(&policy_rwsem);
    free_policy(old);
}

// 降级：写完后继续读
void modify_and_read(void) {
    down_write(&policy_rwsem);
    /* 修改数据 */
    modify_policy();
    /* 降级为读锁 */
    downgrade_write(&policy_rwsem);
    /* 继续读取 */
    read_policy();
    up_read(&policy_rwsem);
}
```

---

### 六、Seqlock（顺序锁）

#### 原理

```
写者:
┌─────────────────────────────────────┐
│ 1. seq++ (奇数，表示正在写入)        │
│ 2. 写入数据                          │
│ 3. seq++ (偶数，表示写入完成)        │
└─────────────────────────────────────┘

读者（无锁）:
┌─────────────────────────────────────┐
│ 1. seq1 = read_seqbegin()            │
│ 2. 读取数据                          │
│ 3. if (read_seqretry(seq1))         │
│       goto 1; // 重试               │
└─────────────────────────────────────┘

关键: 读者通过检查 seq 是否变化来判断读取是否有效
```

#### 数据结构

```c
typedef struct {
    unsigned sequence;     // 序列号
    spinlock_t lock;       // 保护写者
} seqlock_t;
```

#### API

```c
// 初始化
DEFINE_SEQLOCK(name);
seqlock_init(&seqlock);

// 写锁
void write_seqlock(seqlock_t *sl);
void write_sequnlock(seqlock_t *sl);
int write_tryseqlock(seqlock_t *sl);

// 读锁（实际无锁）
unsigned read_seqbegin(seqlock_t *sl);     // 返回序列号
int read_seqretry(seqlock_t *sl, unsigned start);  // 检查是否需要重试

// 中断安全版本
write_seqlock_irqsave(seqlock_t *sl, flags);
write_sequnlock_irqrestore(seqlock_t *sl, flags);
unsigned read_seqbegin_irqsave(seqlock_t *sl, unsigned long *flags);
int read_seqretry_irqrestore(seqlock_t *sl, unsigned start, unsigned long flags);
```

#### 使用示例

```c
seqlock_t time_seqlock;
struct timespec64 current_time;

// 写者（更新时间）
void update_time(struct timespec64 new_time) {
    write_seqlock(&time_seqlock);
    current_time = new_time;
    write_sequnlock(&time_seqlock);
}

// 读者（读取时间，无锁）
struct timespec64 get_time(void) {
    struct timespec64 ts;
    unsigned seq;
    
    do {
        seq = read_seqbegin(&time_seqlock);
        ts = current_time;  // 可能读到不一致的数据
    } while (read_seqretry(&time_seqlock, seq));
    
    return ts;  // 返回一致的数据
}
```

#### 适用场景

```
✓ 适合:
┌─────────────────────────────────────┐
│ 读操作远多于写操作                   │
│ 读操作快速                          │
│ 写操作不需要与读者同步               │
│ 数据可以容忍短暂不一致后重试         │
│ 经典应用: 时间读取、统计计数器       │
└─────────────────────────────────────┘

✗ 不适合:
┌─────────────────────────────────────┐
│ 读者需要修改共享数据                 │
│ 数据结构复杂（指针、链表等）         │
│ 写操作频繁                          │
│ 读者不能容忍重试开销                │
└─────────────────────────────────────┘
```

---

### 七、RCU（Read-Copy-Update）

#### 原理

```
传统锁:
┌─────────────────────────────────────┐
│ 读者: lock → 读 → unlock            │
│ 写者: lock → 写 → unlock            │
│ 问题: 读者和写者串行化               │
└─────────────────────────────────────┘

RCU:
┌─────────────────────────────────────┐
│ 读者: 直接读（无锁）                 │
│ 写者: 复制 → 修改副本 → 替换指针    │
│       → 等待旧读者 → 释放旧数据     │
│ 优势: 读者零开销                     │
└─────────────────────────────────────┘

时间线:
     读者1    读者2    读者3    写者
       │        │        │        │
       ▼        ▼        ▼        ▼
   ┌─────────────────────────────────┐
   │ 读旧数据  读旧数据        │
   │    ↓         ↓          │
   │    │         │     复制+修改    │
   │    │         │          ↓      │
   │    │         │     替换指针     │
   │    │         │          ↓      │
   │ 读新数据  读新数据     │
   │    ↓         ↓          ↓      │
   │ 退出      退出     等待宽限期    │
   │                       ↓        │
   │                  释放旧数据    │
   └─────────────────────────────────┘
```

#### API

```c
// 读侧（无锁）
rcu_read_lock();                    // 标记读侧临界区开始
p = rcu_dereference(ptr);           // 安全读取指针
use(p);                             // 使用数据
rcu_read_unlock();                  // 标记读侧临界区结束

// 写侧
p = alloc_new_data();               // 分配新数据
copy_from_old(p, old);              // 复制旧数据
modify(p);                          // 修改副本
rcu_assign_pointer(ptr, p);         // 原子替换指针
synchronize_rcu();                  // 等待宽限期
free(old);                          // 释放旧数据

// 或使用回调方式
call_rcu(&old->rcu_head, free_func); // 宽限期后回调释放
```

#### 使用示例

```c
// 数据结构
struct foo {
    int a;
    int b;
    struct rcu_head rcu;  // 用于延迟释放
};

struct foo *global_ptr;

// 读者（无锁！）
int read_value(void) {
    int val;
    
    rcu_read_lock();
    struct foo *p = rcu_dereference(global_ptr);
    val = p->a + p->b;
    rcu_read_unlock();
    
    return val;
}

// 写者（更新）
void update_value(int new_a, int new_b) {
    struct foo *old = global_ptr;
    struct foo *new = kmalloc(sizeof(*new), GFP_KERNEL);
    
    // 复制旧数据
    new->a = new_a;
    new->b = new_b;
    
    // 替换指针
    rcu_assign_pointer(global_ptr, new);
    
    // 等待宽限期后释放
    kfree_rcu(old, rcu);  // 或 synchronize_rcu() + kfree()
}

// 链表操作
struct list_head rcu_list;

// 插入
void insert_node(struct node *new) {
    spin_lock(&lock);
    list_add_rcu(&new->list, &rcu_list);
    spin_unlock(&lock);
}

// 删除
void remove_node(struct node *old) {
    spin_lock(&lock);
    list_del_rcu(&old->list);
    spin_unlock(&lock);
    kfree_rcu(old, rcu);
}

// 遍历（无锁）
rcu_read_lock();
list_for_each_entry_rcu(node, &rcu_list, list) {
    process(node);
}
rcu_read_unlock();
```

#### RCU 变体

```c
// 经典 RCU
rcu_read_lock() / rcu_read_unlock()
synchronize_rcu()
call_rcu()

// 可睡眠 RCU
srcu_read_lock() / srcu_read_unlock()
synchronize_srcu()
call_srcu()

// 加速 RCU（用于小型临界区）
rcu_read_lock_sched() / rcu_read_unlock_sched()

// 任务 RCU
rcu_read_lock_trace() / rcu_read_unlock_trace()
```

#### 注意事项

```c
// ✓ 正确: 读者只读
rcu_read_lock();
p = rcu_dereference(ptr);
val = p->field;  // 只读访问
rcu_read_unlock();

// ✗ 错误: 读者修改数据
rcu_read_lock();
p = rcu_dereference(ptr);
p->field = new_val;  // 错误！可能与其他写者冲突
rcu_read_unlock();

// ✓ 正确: 写者用锁保护
spin_lock(&lock);
new = copy_and_modify(old);
rcu_assign_pointer(ptr, new);
spin_unlock(&lock);
kfree_rcu(old, rcu);

// ✗ 错误: 宽限期内访问已释放数据
rcu_assign_pointer(ptr, new);
kfree(old);  // 太早！可能有读者还在访问
synchronize_rcu();  // 无意义，数据已释放
```

---

### 八、Semaphore（信号量）

#### 原理

```
计数信号量:
┌─────────────────────────────────────┐
│          计数器           │
│    count > 0: 可获取                 │
│    count = 0: 需等待                 │
└─────────────────────────────────────┘

获取:
if (count > 0)
    count--;
else
    sleep();  // 加入等待队列

释放:
count++;
if (有等待者)
    wakeup();
```

#### 数据结构

```c
struct semaphore {
    raw_spinlock_t lock;
    unsigned int count;
    struct list_head wait_list;
};
```

#### API

```c
// 初始化
DEFINE_SEMAPHORE(name, count);
void sema_init(struct semaphore *sem, int val);

// 获取
void down(struct semaphore *sem);              // 不可中断
int down_interruptible(struct semaphore *sem); // 可被信号中断
int down_killable(struct semaphore *sem);      // 可被 SIGKILL 中断
int down_trylock(struct semaphore *sem);        // 非阻塞

// 释放
void up(struct semaphore *sem);

// 带超时
int down_timeout(struct semaphore *sem, long jiffies);
```

#### 使用示例

```c
// 互斥信号量（计数=1）
static DEFINE_SEMAPHORE(my_mutex, 1);

void protected_operation(void) {
    if (down_interruptible(&my_mutex))
        return -ERESTARTSYS;
    /* 临界区 */
    up(&my_mutex);
}

// 计数信号量（资源池）
#define MAX_CONNECTIONS 10
static DEFINE_SEMAPHORE(conn_pool, MAX_CONNECTIONS);

struct connection *get_connection(void) {
    if (down_interruptible(&conn_pool))
        return ERR_PTR(-ERESTARTSYS);
    return allocate_connection();
}

void release_connection(struct connection *conn) {
    free_connection(conn);
    up(&conn_pool);
}
```

#### Mutex vs Semaphore

```
┌────────────────┬─────────────────┬─────────────────┐
│     特性       │     Mutex       │   Semaphore     │
├────────────────┼─────────────────┼─────────────────┤
│ 计数           │ 0/1             │ 任意正整数      │
│ 所有权         │ 有（owner）     │ 无              │
│ 递归           │ 支持            │ 不支持          │
│ 优先级继承     │ 支持            │ 不支持          │
│ 自旋优化       │ 支持            │ 不支持          │
│ 适用场景       │ 互斥            │ 计数/同步       │
└────────────────┴─────────────────┴─────────────────┘
```

---

### 九、Atomic 操作

#### 类型

```c
// 整数原子操作
atomic_t v = ATOMIC_INIT(0);
atomic_long_t lv = ATOMIC_LONG_INIT(0);

// 位操作
unsigned long flags;

// 引用计数
refcount_t ref = REFCOUNT_INIT(1);
```

#### API

```c
// 基本操作
int atomic_read(atomic_t *v);
void atomic_set(atomic_t *v, int i);

// 加减
void atomic_add(int i, atomic_t *v);
void atomic_sub(int i, atomic_t *v);
void atomic_inc(atomic_t *v);
void atomic_dec(atomic_t *v);

// 带返回值
int atomic_add_return(int i, atomic_t *v);
int atomic_sub_return(int i, atomic_t *v);
int atomic_inc_return(atomic_t *v);
int atomic_dec_return(atomic_t *v);

// 条件操作
int atomic_add_unless(atomic_t *v, int a, int u);  // v!=u时加a
int atomic_inc_not_zero(atomic_t *v);

// 比较交换
int atomic_cmpxchg(atomic_t *v, int old, int new);
int atomic_xchg(atomic_t *v, int new);

// 位操作
void set_bit(int nr, unsigned long *addr);
void clear_bit(int nr, unsigned long *addr);
void change_bit(int nr, unsigned long *addr);
int test_and_set_bit(int nr, unsigned long *addr);
int test_and_clear_bit(int nr, unsigned long *addr);

// 引用计数
void refcount_set(refcount_t *r, int n);
int refcount_read(refcount_t *r);
void refcount_inc(refcount_t *r);
bool refcount_dec_and_test(refcount_t *r);  // 返回是否变为0
bool refcount_inc_not_zero(refcount_t *r);
```

#### 使用示例

```c
// 计数器
static atomic_t counter = ATOMIC_INIT(0);

void increment(void) {
    atomic_inc(&counter);
}

int get_count(void) {
    return atomic_read(&counter);
}

// 标志位
static atomic_t initialized = ATOMIC_INIT(0);

void init_once(void) {
    if (atomic_cmpxchg(&initialized, 0, 1) == 0) {
        // 第一次调用，执行初始化
        do_init();
    }
}

// 引用计数
struct my_object {
    refcount_t refcount;
    void (*release)(struct my_object *);
};

struct my_object *obj_get(struct my_object *obj) {
    if (refcount_inc_not_zero(&obj->refcount))
        return obj;
    return NULL;
}

void obj_put(struct my_object *obj) {
    if (refcount_dec_and_test(&obj->refcount))
        obj->release(obj);
}
```

---

### 十、Per-CPU 变量

#### 原理

```
传统共享变量:
┌─────────────────────────────────────┐
│        CPU1 ────┐                   │
│        CPU2 ────┼──→ 共享变量 ←─ 锁 │
│        CPU3 ────┘                   │
│        问题: 缓存行竞争              │
└─────────────────────────────────────┘

Per-CPU 变量:
┌─────────────────────────────────────┐
│ CPU1 → per_cpu(var, 0) [独立副本]   │
│ CPU2 → per_cpu(var, 1) [独立副本]   │
│ CPU3 → per_cpu(var, 2) [独立副本]   │
│ 优势: 无竞争、缓存友好              │
└─────────────────────────────────────┘
```

#### 定义与访问

```c
// 静态定义
DEFINE_PER_CPU(int, my_counter);
DEFINE_PER_CPU_READ_MOSTLY(int, config);  // 读多写少

// 动态分配
int __percpu *ptr = alloc_percpu(int);
void free_percpu(void __percpu *ptr);

// 访问
int val = this_cpu_read(my_counter);      // 当前 CPU 的副本
this_cpu_write(my_counter, 42);
this_cpu_add(my_counter, 1);
this_cpu_inc(my_counter);

// 安全版本（禁用抢占）
int val = this_cpu_read_safe(my_counter);  // 或 per_cpu_read
this_cpu_write_safe(my_counter, val);

// 指针操作
int __percpu *ptr = alloc_percpu(int);
int val = this_cpu_read(*ptr);
this_cpu_write(*ptr, 42);

// 遍历所有 CPU
int total = 0;
for_each_possible_cpu(cpu)
    total += per_cpu(my_counter, cpu);
```

#### 使用示例

```c
// 高性能计数器
DEFINE_PER_CPU(unsigned long, event_counter);

void record_event(void) {
    this_cpu_inc(event_counter);  // 无锁递增
}

unsigned long get_total_events(void) {
    unsigned long total = 0;
    int cpu;
    
    for_each_possible_cpu(cpu)
        total += per_cpu(event_counter, cpu);
    return total;
}

// Per-CPU 缓存
struct data_cache {
    void *data;
    unsigned long hits;
    unsigned long misses;
};
DEFINE_PER_CPU(struct data_cache, cache);

void *get_cached_data(void) {
    struct data_cache *c = this_cpu_ptr(&cache);
    if (c->data) {
        c->hits++;
        return c->data;
    }
    c->misses++;
    c->data = allocate_data();
    return c->data;
}
```

---

### 十一、其他锁机制

#### 1. RT Mutex（实时互斥锁）

```c
// 支持优先级继承，用于实时系统
struct rt_mutex {
    raw_spinlock_t wait_lock;
    struct rb_root_cached waiters;
    struct task_struct *owner;
};

// API
void rt_mutex_init(struct rt_mutex *lock);
void rt_mutex_lock(struct rt_mutex *lock);
int rt_mutex_lock_interruptible(struct rt_mutex *lock);
void rt_mutex_unlock(struct rt_mutex *lock);

// 特性: 优先级继承，防止优先级反转
```

#### 2. WW Mutex（Wound-Wait Mutex）

```c
// 用于 GPU/图形驱动的多锁获取
// 解决死锁问题（所有上下文按统一顺序获取）

struct ww_mutex {
    struct mutex base;
    struct ww_acquire_ctx *ctx;
};

// 使用模式
ww_acquire_init(&ctx, &ww_class);
retry:
ww_mutex_lock(&lock1, &ctx);
if (ww_mutex_lock_slow(&lock2, &ctx)) {
    ww_mutex_unlock(&lock1);
    goto retry;
}
/* 临界区 */
ww_mutex_unlock(&lock2);
ww_mutex_unlock(&lock1);
ww_acquire_fini(&ctx);
```

#### 3. Local Lock

```c
// 用于禁用抢占和中断的包装器
// 替代隐式的 preempt_disable/local_irq_disable

struct local_lock {
    // 架构相关
};

// API
local_lock_init(&lock);
local_lock(&lock);         // 禁用抢占
local_unlock(&lock);       // 启用抢占
local_lock_irq(&lock);     // 禁用中断
local_unlock_irq(&lock);   // 启用中断
local_lock_irqsave(&lock, flags);
local_unlock_irqrestore(&lock, flags);
```

#### 4. Bit Spinlock

```c
// 在单个位上的自旋锁
// 节省内存

void bit_spin_lock(int bit, unsigned long *addr);
void bit_spin_unlock(int bit, unsigned long *addr);
int bit_spin_trylock(int bit, unsigned long *addr);

// 用于 page->flags 等位域
```

---

### 十二、选择指南

#### 决策树

```
                        需要同步？
                           │
            ┌──────────────┴──────────────┐
            │                             │
        是，共享数据                  否，不需要锁
            │
    ┌───────┴───────┐
    │               │
  中断上下文？    进程上下文？
    │               │
    ▼               ▼
 Spinlock         持锁时间？
    │         ┌─────┴─────┐
    │       极短        较长
    │         │           │
    │         ▼           ▼
    │     Spinlock     Mutex/Semaphore
    │         │
    │   读多写少？
    │    │
    │  ┌─┴─┐
    │  是  否
    │  │   │
    │  ▼   ▼
    │ RWLock  Spinlock
    │
  需要禁用中断？
    │
  ┌─┴─┐
  是  否
  │   │
  ▼   ▼
spin_lock_irq  spin_lock
spin_lock_irqsave
```

#### 场景匹配表

| 场景 | 推荐锁 | 理由 |
|------|--------|------|
| 中断处理函数 | spin_lock_irqsave | 安全禁用中断 |
| 极短临界区（<100条指令） | spinlock | 开销最小 |
| 可能睡眠的操作 | mutex | 睡眠安全 |
| I/O 操作 | mutex | 长时间持锁 |
| 读多写少，短临界区 | rwlock | 读并发 |
| 读多写少，长临界区 | rwsem | 睡眠 + 读并发 |
| 读极多写极少 | RCU | 读零开销 |
| 时间读取、统计 | seqlock | 读无锁 |
| 资源池管理 | semaphore | 计数语义 |
| 简单计数器 | atomic/per-cpu | 无锁高效 |
| 实时系统 | rt_mutex | 优先级继承 |
| 多锁死锁避免 | ww_mutex | 顺序无关 |

---

### 十三、性能对比

```
开销比较（相对值，越低越好）:

无操作:           ████ 1x
atomic_inc:      ████████████ 3x
per-cpu:         ██████████ 2.5x
spinlock:        ████████████████ 4x
seqlock(读):     ████████████ 3x
RCU(读):         ████████████ 3x
rwlock(读):      ██████████████████ 5x
rwsem(读):       ████████████████████ 6x
mutex:           ████████████████████ 6x
semaphore:       ████████████████████████ 8x

注意: 实际性能取决于硬件、竞争程度、持锁时间
```

---

### 十四、总结

```
┌─────────────────────────────────────────────────────────────────┐
│                     Linux 锁机制选择口诀                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  中断上下文用自旋，进程上下文看时间。              │
│  极短临界自旋锁，长久睡眠选 mutex。                              │
│  读多写少分两路，短用 rwlock 长用 rwsem。                        │
│  读极多时上 RCU，时间统计用 seqlock。                            │
│  资源计数用信号量，简单计数原子化。                              │
│  性能极致 per-cpu，无锁编程是王道。                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```


## 相关链接

- [[Linux RCU锁]]
- [[Linux SpinLock锁]]
- [[Linux Mutex锁]]