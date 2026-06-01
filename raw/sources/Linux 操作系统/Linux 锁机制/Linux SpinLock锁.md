

## Linux Spinlock 介绍

### 一、核心概念

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

### 二、锁实现演进历史

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

### 三、架构相关实现

#### x86 实现

```c
// x86 使用 queued spinlock（CONFIG_QUEUED_SPINLOCKS）
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

#### ARM 实现

```c
// ARM 传统实现（ticket lock 或 simple spinlock）
typedef struct {
    union {
        u32 slock;              // 简单锁
        struct {
            u16 owner;
            u16 next;
        } ticket;               // ticket lock
    };
} arch_spinlock_t;

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
        "   wfe\n"                                // 等待事件
        "   ldaxr  %w[tmp], [%[lock]]\n"
        "   cbnz   %w[tmp], 2b\n"
        "   jmp    1b\n"
    );
}

// WFE（Wait For Event）优化
// - 不是纯粹的自旋，而是低功耗等待
// - 锁释放时发送 SEV（Send Event）唤醒等待者
```

### 四、raw_spinlock vs spinlock

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

### 五、API 变体完整详解

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
 *   示例: 
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

### 六、中断上下文使用详解

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

### 七、内核抢占与 Spinlock

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

### 八、常见错误与最佳实践

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
```

### 九、性能分析

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

// 性能测试代码
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

### 十、内核中的典型应用

```c
// ═══════════════════════════════════════════════════════════════
//                     内核典型应用场景
// ═══════════════════════════════════════════════════════════════

// 1. 网络包统计（中断上下文）
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

// 2. 定时器保护（软中断上下文）
struct timer_list my_timer;
spinlock_t timer_lock;

void timer_callback(struct timer_list *t)
{
    spin_lock(&timer_lock);
    /* 定时器处理 */
    spin_unlock(&timer_lock);
}

// 3. 驱动中断与进程共享
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

// 4. 调度器核心（raw_spinlock）
struct rq {
    raw_spinlock_t lock;       // 必须用 raw_spinlock！
    struct task_struct *curr;
    unsigned long nr_running;
};

// 调度器中的锁使用（不能睡眠）
void scheduler_tick(void)
{
    raw_spin_lock(&rq->lock);
    /* 更新运行队列 */
    raw_spin_unlock(&rq->lock);
}
```

### 十一、调试工具

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

---

## 总结

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
