## Linux RCU 锁完整介绍

---
### 一、核心概念

**RCU（Read-Copy-Update）** 是 Linux 内核中最独特的同步机制，实现了"读者零开销"的极致性能。

#### 核心思想

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RCU 核心哲学                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  传统锁的困境:                                                        │
│    ┌─────────────────────────────────────────────────────────────┐ │
│    │ 读者: lock → 读 → unlock     （即使无冲突也有开销）          │ │
│    │ 写者: lock → 写 → unlock     （与读者串行化）                │ │
│    │ 问题: 读多写少场景下，读者开销成为瓶颈                       │ │
│    └─────────────────────────────────────────────────────────────┘ │
│                              ↓                                      │
│  RCU 的突破:                                                         │
│    ┌─────────────────────────────────────────────────────────────┐ │
│    │ 读者: 直接读（无锁！）           → 读侧几乎零开销            │ │
│    │ 写者: 复制 → 修改副本 → 替换指针 → 等待旧读者 → 释放旧数据  │ │
│    │ 代价: 写者延迟释放数据         → 内存占用短暂增加           │ │
│    └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  关键洞察:                                                           │
│    "读操作不需要与写操作同步，只需要看到一致的数据版本"              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 与其他锁对比

```
┌──────────────┬────────────────────┬────────────────────┬────────────────────┐
│     特性      │      Spinlock      │      Mutex         │       RCU          │
├──────────────┼────────────────────┼────────────────────┼────────────────────┤
│ 读侧开销      │ 有（获取/释放锁）   │ 有（获取/释放锁）   │ 几乎为零           │
│ 写侧开销      │ 小                 │ 中等               │ 较大（复制+等待）   │
│ 上下文限制    │ 任意               │ 仅进程上下文        │ 任意（读侧）        │
│ 内存开销      │ 极小               │ 小                 │ 短暂增加           │
│ 适用场景      │ 读写对称           │ 读写对称           │ 读极多写极少       │
│ 数据一致性    │ 立即               │ 立即               │ 最终一致           │
│ 读侧可睡眠    │ 否                 │ 是                 │ 经典RCU否，SRCU可  │
│ 写侧并发      │ 串行               │ 串行               │ 可并行（用锁保护）  │
└──────────────┴────────────────────┴────────────────────┴────────────────────┘
```

---

### 二、RCU 工作原理详解

#### 宽限期概念

```
┌─────────────────────────────────────────────────────────────────────┐
│                        宽限期（Grace Period）                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  定义: 从写者替换指针开始，到所有旧读者退出临界区的时间段            │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 时间轴:                                                      │   │
│  │                                                             │   │
│  │    t0       t1       t2       t3       t4       t5         │   │
│  │     │        │        │        │        │        │          │   │
│  │     ▼        ▼        ▼        ▼        ▼        ▼          │   │
│  │  ┌──┐    ┌──────────────────────────────────────────┐      │   │
│  │  │写│    │            宽限期（Grace Period）         │      │   │
│  │  │者│    │                                             │      │   │
│  │  │替│    │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐         │      │   │
│  │  │换│    │  │读者1│ │读者2│ │读者3│ │读者4│         │      │   │
│  │  │指│    │  │进入 │ │进入 │ │进入 │ │进入 │         │      │   │
│  │  │针│    │  └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘         │      │   │
│  │  └──┘    │     │       │       │       │            │      │   │
│  │          │     ▼       ▼       ▼       ▼            │      │   │
│  │          │  [退出]  [退出]  [退出]  [退出]          │      │   │
│  │          │                                     │      │   │
│  │          └─────────────────────────────────────┘      │   │
│  │                                             │          │   │
│  │                                             ▼          │   │
│  │                                        [释放旧数据]     │   │
│  │                                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  宽限期结束条件: 所有在替换指针前进入的读者都已退出                  │
│  注意: 替换指针后进入的读者看到新数据，不影响宽限期                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 写者操作流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                        写者更新数据流程                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  步骤分解:                                                           │
│                                                                     │
│  1. 复制旧数据                                                       │
│     ┌───────────────────────────────────────────────────────────┐ │
│     │ struct foo *old = global_ptr;                              │ │
│     │ struct foo *new = kmalloc(sizeof(*new), GFP_KERNEL);      │ │
│     │ *new = *old;           // 复制旧数据到新副本               │ │
│     └───────────────────────────────────────────────────────────┘ │
│                              ↓                                      │
│  2. 修改副本                                                         │
│     ┌───────────────────────────────────────────────────────────┐ │
│     │ new->field = new_value;   // 只修改副本，不影响旧数据       │ │
│     │ // 此时读者仍在安全访问 old                                │ │
│     └───────────────────────────────────────────────────────────┘ │
│                              ↓                                      │
│  3. 替换指针（原子操作）                                             │
│     ┌───────────────────────────────────────────────────────────┐ │
│     │ rcu_assign_pointer(global_ptr, new);                      │ │
│     │ // 从此刻起，新读者看到 new，旧读者可能还在访问 old        │ │
│     └───────────────────────────────────────────────────────────┘ │
│                              ↓                                      │
│  4. 等待宽限期                                                       │
│     ┌───────────────────────────────────────────────────────────┐ │
│     │ synchronize_rcu();        // 等待所有旧读者退出             │ │
│     │ // 或 call_rcu(&old->rcu, free_func);  // 异步回调         │ │
│     └───────────────────────────────────────────────────────────┘ │
│                              ↓                                      │
│  5. 释放旧数据                                                       │
│     ┌───────────────────────────────────────────────────────────┐ │
│     │ kfree(old);               // 现在可以安全释放               │ │
│     │ // 或在回调函数中释放                                      │ │
│     └───────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 读者操作流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                        读者访问数据流程                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  rcu_read_lock()                                                    │
│      │                                                              │
│      │  ┌───────────────────────────────────────────────────────┐ │
│      │  │ 实际上: preempt_disable() 或类似操作                   │ │
│      │  │ 作用: 防止在此期间被调度出去                           │ │
│      │  │          让当前 CPU 上的读者无法"消失"                 │ │
│      │  │ 注意: 不是真正的锁，没有原子操作开销                   │ │
│      │  └───────────────────────────────────────────────────────┘ │
│      ▼                                                              │
│  p = rcu_dereference(global_ptr)                                   │
│      │                                                              │
│      │  ┌───────────────────────────────────────────────────────┐ │
│      │  │ 实际上: 带内存屏障的指针读取                           │ │
│      │  │ 作用: 确保看到最新的指针值                             │ │
│      │  │ 实现: smp_load_acquire() 或类似                       │ │
│      │  └───────────────────────────────────────────────────────┘ │
│      ▼                                                              │
│  使用数据 (只读)                                                     │
│      │                                                              │
│      │  ┌───────────────────────────────────────────────────────┐ │
│      │  │ val = p->field;                                        │ │
│      │  │ process(val);                                          │ │
│      │  │ 关键: 只读不写！不能修改 p 指向的数据                   │ │
│      │  └───────────────────────────────────────────────────────┘ │
│      ▼                                                              │
│  rcu_read_unlock()                                                  │
│      │                                                              │
│      │  ┌───────────────────────────────────────────────────────┐ │
│      │  │ 实际上: preempt_enable() 或类似操作                    │ │
│      │  │ 作用: 标记读者退出，宽限期可能结束                      │ │
│      │  └───────────────────────────────────────────────────────┘ │
│      ▼                                                              │
│  [结束]                                                              │
│                                                                     │
│  总开销: 约 3-10 CPU cycles（接近零）                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 三、RCU 宽限期检测机制

#### 经典实现：基于抢占计数

```
┌─────────────────────────────────────────────────────────────────────┐
│                   经典 RCU 宽限期检测                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  核心思想:                                                           │
│    rcu_read_lock() → preempt_disable()                             │
│    抢占计数 > 0 → 该 CPU 上有活跃的 RCU 读者                         │
│    抢占计数 = 0 → 该 CPU 上下文切换 → 旧读者已退出                   │
│                                                                     │
│  检测宽限期:                                                         │
│    ┌───────────────────────────────────────────────────────────┐   │
│    │ for_each_online_cpu(cpu) {                                │   │
│    │     if (cpu_quiescent_state(cpu))                         │   │
│    │         continue;  // 该 CPU 已通过静止点                  │   │
│    │     else                                                  │   │
│    │         still_waiting++;  // 该 CPU 还有活跃读者           │   │
│    │ }                                                         │   │
│    │ if (still_waiting == 0)                                   │   │
│    │     grace_period_done();                                  │   │
│    └───────────────────────────────────────────────────────────┘   │
│                                                                     │
│  静止点（Quiescent State）:                                          │
│    - 上下文切换（schedule）                                          │
│    - 进入 idle 状态                                                  │
│    - 进入用户态                                                      │
│    - 这些时刻一定不在 RCU 读临界区                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 现代 Tree RCU 实现

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Tree RCU 结构                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  问题: 大规模系统（数百 CPU）宽限期检测开销大                         │
│  解决: 分层树状结构，各级汇总静止状态                                 │
│                                                                     │
│  结构示意:                                                           │
│                                                                     │
│                         ┌─────────────┐                             │
│                         │  RCU root   │                             │
│                         │  (Node 0)   │                             │
│                         └──────┬──────┘                             │
│                                │                                    │
│              ┌─────────────────┼─────────────────┐                 │
│              │                 │                 │                 │
│        ┌─────▼─────┐     ┌─────▼─────┐     ┌─────▼─────┐           │
│        │ Node 1    │     │ Node 2    │     │ Node 3    │           │
│        │ (Level 1) │     │ (Level 1) │     │ (Level 1) │           │
│        └─────┬─────┘     └─────┬─────┘     └─────┬─────┘           │
│              │                 │                 │                 │
│     ┌────────┼────────┐  ┌────┴────┐  ┌────────┼────────┐         │
│     │        │        │  │         │  │        │        │         │
│  ┌──▼──┐ ┌──▼──┐ ┌──▼──┐│         │┌──▼──┐ ┌──▼──┐ ┌──▼──┐       │
│  │CPU0│ │CPU1│ │CPU2││         ││CPU8│ │CPU9│ │CPU10│       │
│  │    │ │    │ │    ││         ││    │ │    │ │     │       │
│  └────┘ └────┘ └────┘│         │└────┘ └────┘ └─────┘       │
│                                                                     │
│  检测流程:                                                           │
│    CPU 报告静止 → 叶节点汇总 → 上层节点汇总 → 根节点完成             │
│    复杂度: O(log N) 而非 O(N)                                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 宽限期回调队列

```
┌─────────────────────────────────────────────────────────────────────┐
│                    RCU Callback 机制                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  synchronize_rcu():                                                  │
│    阻塞等待宽限期结束                                                │
│    适用: 写者较少、可接受阻塞                                         │
│                                                                     │
│  call_rcu():                                                         │
│    注册回调，宽限期结束后异步执行                                     │
│    适用: 写者频繁、不能阻塞                                           │
│                                                                     │
│  回调队列结构:                                                        │
│    ┌───────────────────────────────────────────────────────────┐   │
│    │                 per-CPU callback queues                   │   │
│    │                                                           │   │
│    │  CPU0: [cb1]→[cb2]→[cb3]→NULL                            │   │
│    │  CPU1: [cb4]→[cb5]→NULL                                  │   │
│    │  CPU2: [cb6]→NULL                                        │   │
│    │  ...                                                      │   │
│    │                                                           │   │
│    │  rcu_softirq 负责执行已就绪的回调                         │   │
│    └───────────────────────────────────────────────────────────┘   │
│                                                                     │
│  回调执行时机:                                                       │
│    - RCU softirq（RCU_SOFTIRQ）                                     │
│    - 在静止点检测完成后触发                                          │
│    - 通常在上下文切换、idle 进入等时刻                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 四、RCU 变体详解

```
┌─────────────────────────────────────────────────────────────────────┐
│                      RCU 变体对比                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┬────────────────────┬───────────────────────┐ │
│  │      变体         │      读侧特点       │      适用场景         │ │
│  ├──────────────────┼────────────────────┼───────────────────────┤ │
│  │ Classic RCU      │ 不可睡眠            │ 内核通用同步         │ │
│  │ SRCU             │ 可睡眠              │ 需要在读侧睡眠       │ │
│  │ RCU-sched        │ 禁用抢占            │ 调度器相关           │ │
│  │ RCU-bh           │ 禁用软中断          │ 网络软中断路径       │ │
│  │ RCU-irq          │ 禁用中断            │ 硬中断上下文         │ │
│  │ Tasks-RCU        │ 任务级追踪          │ 特殊任务同步         │ │
│  │ Tiny RCU         │ 单 CPU 优化         │ 嵌入式/单核系统      │ │
│  └──────────────────┴────────────────────┴───────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### Classic RCU

```c
// 最常用的 RCU 变体
// 读侧: 禁用抢占，不可睡眠
// 写侧: synchronize_rcu() 或 call_rcu()

// 读侧 API
void rcu_read_lock(void);        // 实际是 preempt_disable()
void rcu_read_unlock(void);      // 实际是 preempt_enable()

// 指针访问
#define rcu_dereference(p)       // 带内存屏障的指针读取
#define rcu_dereference_check(p, c)  // 带条件检查
#define rcu_dereference_protected(p, lockdep)  // 已有锁保护

// 写侧 API
void synchronize_rcu(void);      // 阻塞等待宽限期
void call_rcu(struct rcu_head *head, rcu_callback_t func);  // 异步回调

// 指针更新
#define rcu_assign_pointer(p, v)  // 带内存屏障的指针赋值

// 使用示例
struct foo *global_ptr;

// 读者
int read_value(void)
{
    int val;
    
    rcu_read_lock();                    // 标记进入
    struct foo *p = rcu_dereference(global_ptr);
    val = p->value;                     // 只读访问
    rcu_read_unlock();                  // 标记退出
    
    return val;
}

// 写者（阻塞版本）
void update_value(int new_val)
{
    struct foo *old, *new;
    
    new = kmalloc(sizeof(*new), GFP_KERNEL);
    old = global_ptr;
    
    // 复制并修改
    *new = *old;
    new->value = new_val;
    
    // 替换指针
    rcu_assign_pointer(global_ptr, new);
    
    // 等待宽限期
    synchronize_rcu();
    
    // 释放旧数据
    kfree(old);
}
```

#### SRCU（Sleepable RCU）

```c
// 可睡眠的 RCU 变体
// 读侧: 使用 srcu_read_lock/unlock，可以睡眠
// 写侧: synchronize_srcu()，开销较大

struct srcu_struct my_srcu;      // 需要显式定义

// 初始化
int init_srcu_struct(struct srcu_struct *ssp);
void cleanup_srcu_struct(struct srcu_struct *ssp);

// 读侧 API（返回索引）
int srcu_read_lock(struct srcu_struct *ssp);
void srcu_read_unlock(struct srcu_struct *ssp, int idx);

// 写侧 API
void synchronize_srcu(struct srcu_struct *ssp);
void call_srcu(struct srcu_struct *ssp, 
               struct rcu_head *head, rcu_callback_t func);

// 使用示例
static struct srcu_struct net_srcu;

// 读者（可睡眠！）
int read_network_config(void)
{
    int idx;
    int config;
    
    idx = srcu_read_lock(&net_srcu);    // 可以睡眠
    
    struct net_config *p = srcu_dereference(net_config, &net_srcu);
    
    // 这里可以调用可能睡眠的函数
    msleep(10);                         // 合法！
    copy_to_user(buf, p->data, len);    // 合法！
    
    config = p->value;
    
    srcu_read_unlock(&net_srcu, idx);
    return config;
}

// 写者
void update_network_config(struct net_config *new)
{
    struct net_config *old;
    
    old = net_config;
    srcu_assign_pointer(&net_config, new, &net_srcu);
    
    synchronize_srcu(&net_srcu);        // 等待所有读者
    kfree(old);
}

// 适用场景:
// - 需要在读侧调用 copy_from_user/copy_to_user
// - 读侧可能触发页面故障
// - 读侧需要等待 I/O
```

#### RCU-sched

```c
// 用于调度器相关路径
// 读侧: preempt_disable()，更严格的语义

void rcu_read_lock_sched(void);        // preempt_disable()
void rcu_read_unlock_sched(void);      // preempt_enable()

void synchronize_sched(void);          // 等待调度器静止点

// 适用场景:
// - 调度器内部数据结构
// - 需要严格禁用抢占的场景
```

#### RCU-bh

```c
// 用于网络软中断路径
// 读侧: local_bh_disable()

void rcu_read_lock_bh(void);           // local_bh_disable()
void rcu_read_unlock_bh(void);         // local_bh_enable()

void synchronize_rcu_bh(void);

// 适用场景:
// - 网络软中断上下文
// - 需要禁用软中断的场景
```

#### Tiny RCU

```c
// 单 CPU 或小系统的简化实现
// 无需复杂的树状结构
// CONFIG_TINY_RCU 或 CONFIG_TINY_PREEMPT_RCU

// 优势:
// - 代码简单
// - 内存占用小
// - 无 per-CPU 队列

// 适用:
// - 嵌入式系统
// - 单核处理器
// - 资源受限环境
```

---

### 五、RCU 数据结构

#### 核心结构体

```c
// RCU 回调头（嵌入在被保护对象中）
struct rcu_head {
    struct rcu_head *next;      // 链表指针
    void (*func)(struct rcu_head *head);  // 回调函数
};

// 使用方式
struct foo {
    int value;
    struct rcu_head rcu;        // 嵌入 rcu_head
};

// 回调函数
static void free_foo_rcu(struct rcu_head *rcu)
{
    struct foo *p = container_of(rcu, struct foo, rcu);
    kfree(p);
}

// 使用
call_rcu(&old->rcu, free_foo_rcu);

// 或使用简化宏
kfree_rcu(old, rcu);            // 直接释放，无需自定义回调
```

#### Tree RCU 内部结构

```c
// RCU 节点（树状结构）
struct rcu_node {
    raw_spinlock_t lock;        // 保护本节点
    unsigned long gp_seq;       // 宽限期序列号
    unsigned long qsmask;       // 需要报告静止的 CPU mask
    struct rcu_node *parent;    // 父节点
    
    // 等待队列
    struct list_head blkd_tasks; // 阻塞的任务
};

// RCU 数据结构
struct rcu_state {
    struct rcu_node *node;      // 树状节点数组
    int levelcnt[MAX_LEVELS];   // 各层节点数
    unsigned long gp_seq;       // 当前宽限期序号
    unsigned long gp_state;     // 宽限期状态
    
    // 配置
    int gp_duration;            // 预期宽限期时长
    int boost_prio;             // 优先级提升（CONFIG_RCU_BOOST）
};

// Per-CPU 数据
struct rcu_data {
    unsigned long gp_seq;       // 本 CPU 看到的宽限期
    bool cpu_no_qs;             // 是否已报告静止
    bool core_need_qs;          // 是否需要报告静止
    
    // 回调队列
    struct rcu_head *nxtlist;   // 待处理回调链表
    struct rcu_head **nxttail[N_RCU_LVLS];  // 各级队列尾部
    
    unsigned long n_cbs_invoked; // 统计: 已执行回调数
    unsigned long n_nxts;        // 统计: 当前回调数
};
```

---

### 六、RCU API 完整详解

#### 读侧 API

```c
// ═══════════════════════════════════════════════════════════════
//                    RCU 读侧 API
// ═══════════════════════════════════════════════════════════════

/*
 * rcu_read_lock() / rcu_read_unlock()
 *   - 标记读临界区开始/结束
 *   - 经典 RCU: preempt_disable/enable
 *   - SRCU: 获取/释放索引
 *   - 注意: 临界区内不可睡眠（经典 RCU）
 */

void rcu_read_lock(void);
void rcu_read_unlock(void);

/*
 * rcu_dereference()
 *   - 安全读取 RCU 保护的数据
 *   - 包含必要的内存屏障
 *   - 确保看到最新的指针值
 */

#define rcu_dereference(p) \
    ({ \
        typeof(p) __p = READ_ONCE(p); \
        smp_load_acquire(&__p); \
        __p; \
    })

/*
 * rcu_dereference_check()
 *   - 额外条件检查的读取
 *   - 用于有额外锁保护的场景
 */

#define rcu_dereference_check(p, c) \
    ({ \
        RCU_LOCKDEP_WARN(!(c), "suspicious rcu_dereference_check()"); \
        rcu_dereference(p); \
    })

// 示例: 已有锁保护时的读取
mutex_lock(&lock);
p = rcu_dereference_protected(global_ptr, lockdep_is_held(&lock));
// 此时可以安全修改 p，因为已有锁保护
mutex_unlock(&lock);
```

#### 写侧 API

```c
// ═══════════════════════════════════════════════════════════════
//                    RCU 写侧 API
// ═══════════════════════════════════════════════════════════════

/*
 * synchronize_rcu()
 *   - 阻塞等待宽限期结束
 *   - 保证所有旧读者都已退出
 *   - 可睡眠，仅进程上下文使用
 *   - 开销: 通常 10-100ms
 */

void synchronize_rcu(void);

// 等待多个宽限期（可选）
void synchronize_rcu_expedited(void);  // 快速版本，开销更大

/*
 * call_rcu()
 *   - 异步回调，宽限期结束后执行
 *   - 不阻塞，适合高频更新
 *   - 回调在 RCU softirq 中执行
 */

void call_rcu(struct rcu_head *head, void (*func)(struct rcu_head *head));

// 回调函数示例
static void my_rcu_callback(struct rcu_head *rcu)
{
    struct my_data *data = container_of(rcu, struct my_data, rcu);
    kfree(data);
}

// 使用
call_rcu(&old_data->rcu, my_rcu_callback);

/*
 * kfree_rcu()
 *   - 简化版本，直接调用 kfree
 *   - 无需自定义回调函数
 */

kfree_rcu(old_data, rcu);  // 相当于 call_rcu(&old->rcu, kfree_rcu_callback)

/*
 * rcu_assign_pointer()
 *   - 原子替换指针
 *   - 包含必要的内存屏障
 *   - 确保新数据对读者可见
 */

#define rcu_assign_pointer(p, v) \
    do { \
        smp_store_release(&p, v); \
    } while (0)

// 使用
rcu_assign_pointer(global_ptr, new_data);
```

#### 链表操作 API

```c
// ═══════════════════════════════════════════════════════════════
//                    RCU 链表 API
// ═══════════════════════════════════════════════════════════════

// RCU 保护的链表头
struct list_head my_list;

// 添加节点（写者，需锁保护）
void list_add_rcu(struct list_head *new, struct list_head *head);
void list_add_tail_rcu(struct list_head *new, struct list_head *head);

// 删除节点（写者，需锁保护）
void list_del_rcu(struct list_head *entry);

// 替换节点
void list_replace_rcu(struct list_head *old, struct list_head *new);

// 遍历（读者，无锁）
#define list_for_each_entry_rcu(pos, head, member) \
    for (pos = list_entry_rcu((head)->next, typeof(*pos), member); \
         &(pos)->member != (head); \
         pos = list_entry_rcu(&(pos)->member.next, typeof(*pos), member))

// 使用示例
struct my_node {
    int value;
    struct list_head list;
};

static DEFINE_MUTEX(list_mutex);  // 写者保护
static LIST_HEAD(my_list);

// 读者：遍历链表
void traverse_list(void)
{
    struct my_node *node;
    
    rcu_read_lock();
    list_for_each_entry_rcu(node, &my_list, list) {
        printk("value = %d\n", node->value);
    }
    rcu_read_unlock();
}

// 写者：添加节点
void add_node(int value)
{
    struct my_node *new = kmalloc(sizeof(*new), GFP_KERNEL);
    new->value = value;
    
    mutex_lock(&list_mutex);
    list_add_rcu(&new->list, &my_list);
    mutex_unlock(&list_mutex);
}

// 写者：删除节点
void remove_node(struct my_node *old)
{
    mutex_lock(&list_mutex);
    list_del_rcu(&old->list);
    mutex_unlock(&list_mutex);
    
    kfree_rcu(old, rcu);  // 或 synchronize_rcu() + kfree(old)
}

// 哈希表链表（hlist）
struct hlist_head my_hash_table[HASH_SIZE];

void hlist_add_head_rcu(struct hlist_node *node, struct hlist_head *head);
void hlist_del_rcu(struct hlist_node *node);
void hlist_del_init_rcu(struct hlist_node *node);

#define hlist_for_each_entry_rcu(pos, head, member) \
    for (pos = hlist_entry_safe(rcu_dereference(head->first), \
                                typeof(*(pos)), member); \
         pos; \
         pos = hlist_entry_safe(rcu_dereference((pos)->member.next), \
                                typeof(*(pos)), member))
```

---

### 七、典型使用场景

#### 场景 1：全局配置/策略数据

```c
// 读极多写极少的配置数据
struct system_config {
    int max_connections;
    int timeout_ms;
    char server_name[64];
    struct rcu_head rcu;
};

struct system_config __rcu *current_config;

// 读者：获取配置（极高频）
int get_timeout(void)
{
    int timeout;
    
    rcu_read_lock();
    struct system_config *cfg = rcu_dereference(current_config);
    timeout = cfg->timeout_ms;
    rcu_read_unlock();
    
    return timeout;
}

// 写者：更新配置（极低频）
void update_config(struct system_config *new_cfg)
{
    struct system_config *old = rcu_dereference(current_config);
    
    rcu_assign_pointer(current_config, new_cfg);
    synchronize_rcu();
    kfree(old);
}

// 适用原因:
// - 配置读取极其频繁（每个请求都需要）
// - 配置更新极其罕见（管理员手动修改）
// - 读侧零开销，性能极致优化
```

#### 场景 2：网络路由表

```c
// 路由查找极高频，路由更新低频
struct route_entry {
    uint32_t dest_ip;
    uint32_t next_hop;
    int metric;
    struct rcu_head rcu;
};

struct route_table __rcu *routing_table;

// 读者：路由查找（每个数据包）
struct route_entry *lookup_route(uint32_t dest_ip)
{
    struct route_entry *entry = NULL;
    struct route_table *tbl;
    
    rcu_read_lock();
    tbl = rcu_dereference(routing_table);
    
    // 查找路由（哈希或 radix tree）
    entry = find_route(tbl, dest_ip);
    
    rcu_read_unlock();
    return entry;
}

// 写者：更新路由表
void update_route_table(struct route_table *new_table)
{
    struct route_table *old = rcu_dereference(routing_table);
    
    rcu_assign_pointer(routing_table, new_table);
    call_rcu(&old->rcu, free_route_table);
}

// 适用原因:
// - 每个数据包都需要路由查找（百万级/秒）
// - 路由更新相对罕见
// - 读侧零开销对网络性能至关重要
```

#### 场景 3：内核数据结构

```c
// VFS dentry 缓存
// 进程 task_struct 的某些字段
// 网络设备列表
// 文件系统 superblock

// 示例：查找 dentry
struct dentry *d_lookup(struct dentry *parent, const struct qstr *name)
{
    struct dentry *dentry;
    
    rcu_read_lock();
    dentry = __d_lookup_rcu(parent, name);
    if (dentry)
        dentry = dentry->d_inode;  // 使用数据
    rcu_read_unlock();
    
    return dentry;
}
```

#### 场景 4：设备驱动

```c
// 设备配置读取
struct device_config {
    int mode;
    int speed;
    struct rcu_head rcu;
};

struct my_device {
    struct device_config __rcu *config;
    spinlock_t config_lock;  // 写者保护
};

// 读者：获取配置（ISR 或进程上下文）
int get_device_mode(struct my_device *dev)
{
    int mode;
    
    rcu_read_lock();
    struct device_config *cfg = rcu_dereference(dev->config);
    mode = cfg->mode;
    rcu_read_unlock();
    
    return mode;
}

// 写者：更新配置（进程上下文）
void set_device_mode(struct my_device *dev, int new_mode)
{
    struct device_config *old, *new;
    
    new = kmalloc(sizeof(*new), GFP_KERNEL);
    
    spin_lock(&dev->config_lock);
    old = rcu_dereference_protected(dev->config, 
                                     lockdep_is_held(&dev->config_lock));
    *new = *old;
    new->mode = new_mode;
    rcu_assign_pointer(dev->config, new);
    spin_unlock(&dev->config_lock);
    
    synchronize_rcu();
    kfree(old);
}
```

---

### 八、常见错误与陷阱

#### 错误 1：读侧修改数据

```c
// ✗ 错误：读者修改数据
void wrong_reader(void)
{
    rcu_read_lock();
    struct foo *p = rcu_dereference(global_ptr);
    p->value = new_value;  // 错误！写操作
    rcu_read_unlock();
}

// 问题:
// - 多个读者可能并发修改，数据损坏
// - 写者也在修改，冲突
// - RCU 只适用于读操作

// ✓ 正确：读者只读
void correct_reader(void)
{
    int val;
    
    rcu_read_lock();
    struct foo *p = rcu_dereference(global_ptr);
    val = p->value;  // 只读
    rcu_read_unlock();
    
    return val;
}
```

#### 错误 2：过早释放数据

```c
// ✗ 错误：替换后立即释放
void wrong_release(void)
{
    struct foo *old = global_ptr;
    struct foo *new = alloc_and_init();
    
    rcu_assign_pointer(global_ptr, new);
    kfree(old);  // 错误！可能有读者还在访问 old
    
    synchronize_rcu();  // 无意义，数据已释放
}

// 问题:
// - 替换指针后，旧读者可能还在访问旧数据
// - 立即释放会导致读者访问已释放内存
// - 严重的内存安全问题

// ✓ 正确：等待宽限期后释放
void correct_release(void)
{
    struct foo *old = global_ptr;
    struct foo *new = alloc_and_init();
    
    rcu_assign_pointer(global_ptr, new);
    synchronize_rcu();  // 先等待
    kfree(old);         // 后释放
}

// 或使用异步回调
void correct_release_async(void)
{
    struct foo *old = global_ptr;
    struct foo *new = alloc_and_init();
    
    rcu_assign_pointer(global_ptr, new);
    kfree_rcu(old, rcu);  // 宽限期结束后自动释放
}
```

#### 错误 3：经典 RCU 中睡眠

```c
// ✗ 错误：经典 RCU 读侧睡眠
void wrong_sleep(void)
{
    rcu_read_lock();
    struct foo *p = rcu_dereference(global_ptr);
    
    msleep(100);  // 错误！睡眠
    
    // 或 copy_from_user（可能睡眠）
    copy_from_user(buf, user_buf, len);
    
    rcu_read_unlock();
}

// 问题:
// - 经典 RCU 基于 preempt_disable
// - 睡眠会导致调度，违反 RCU 语义
// - 可能导致宽限期无法结束

// ✓ 正确：使用 SRCU
void correct_sleep(void)
{
    int idx = srcu_read_lock(&my_srcu);
    struct foo *p = srcu_dereference(global_ptr, &my_srcu);
    
    msleep(100);  // SRCU 允许睡眠
    copy_from_user(buf, user_buf, len);
    
    srcu_read_unlock(&my_srcu, idx);
}
```

#### 错误 4：忘记 rcu_dereference

```c
// ✗ 错误：直接读取指针
void wrong_dereference(void)
{
    struct foo *p;
    
    rcu_read_lock();
    p = global_ptr;  // 错误！没有内存屏障
    val = p->value;
    rcu_read_unlock();
}

// 问题:
// - 某些架构可能看到旧指针值
// - 编译器优化可能导致乱序
// - 数据不一致

// ✓ 正确：使用 rcu_dereference
void correct_dereference(void)
{
    struct foo *p;
    
    rcu_read_lock();
    p = rcu_dereference(global_ptr);  // 正确的内存屏障
    val = p->value;
    rcu_read_unlock();
}
```

#### 错误 5：忘记 rcu_assign_pointer

```c
// ✗ 错误：直接赋值指针
void wrong_assign(void)
{
    struct foo *new = alloc_new();
    
    global_ptr = new;  // 错误！没有内存屏障
    synchronize_rcu();
    kfree(old);
}

// 问题:
// - 读者可能暂时看不到新指针
// - 编译器/CPU 优化可能导致乱序
// - 数据不一致

// ✓ 正确：使用 rcu_assign_pointer
void correct_assign(void)
{
    struct foo *new = alloc_new();
    
    rcu_assign_pointer(global_ptr, new);  // 正确的内存屏障
    synchronize_rcu();
    kfree(old);
}
```

#### 错误 6：链表遍历中删除节点

```c
// ✗ 错误：遍历中删除（无锁）
void wrong_delete(void)
{
    struct my_node *node;
    
    rcu_read_lock();
    list_for_each_entry_rcu(node, &my_list, list) {
        if (should_delete(node)) {
            list_del_rcu(&node->list);  // 错误！无锁删除
            kfree(node);
        }
    }
    rcu_read_unlock();
}

// 问题:
// - 写者必须有锁保护
// - RCU 读侧不能修改数据结构
// - 可能导致链表损坏

// ✓ 正确：写者用锁保护
void correct_delete(void)
{
    struct my_node *node, *tmp;
    LIST_HEAD(to_free);
    
    mutex_lock(&list_mutex);  // 写者保护
    list_for_each_entry_safe(node, tmp, &my_list, list) {
        if (should_delete(node)) {
            list_del_rcu(&node->list);
            list_add(&node->list, &to_free);  // 暂存待释放
        }
    }
    mutex_unlock(&list_mutex);
    
    // 批量释放
    list_for_each_entry_safe(node, tmp, &to_free, list) {
        list_del(&node->list);
        kfree_rcu(node, rcu);
    }
}
```

---

### 九、调试与分析工具

#### 内核配置

```bash
# RCU 调试配置
CONFIG_RCU_TRACE=y            # RCU 追踪
CONFIG_RCU_CPU_STALL_TIMEOUT=60  # Stall 检测超时（秒）
CONFIG_DEBUG_OBJECTS_RCU_HEAD=y  # RCU 回调对象检测
CONFIG_PROVE_RCU=y            # RCU 语义验证（lockdep）
CONFIG_RCU_STRICT_GRACE_PERIOD=y  # 严格宽限期检查

# RCU Boost（实时系统）
CONFIG_RCU_BOOST=y            # 优先级提升
CONFIG_RCU_BOOST_PRIO=1       # 提升后的优先级
```

#### RCU Stall 检测

```bash
# RCU Stall 警告（宽限期无法结束）
# 内核会打印警告信息:
# "INFO: rcu_sched detected stalls on CPUs/tasks: ..."

# 常见原因:
# 1. 读临界区时间过长（超过 stall timeout）
# 2. CPU 被长时间禁用抢占
# 3. 某 CPU 长时间处于内核态无调度
# 4. 回调队列积压过多

# 调整检测超时
echo 120 > /sys/module/rcupdate/parameters/rcu_cpu_stall_timeout

# 查看 RCU 状态
cat /sys/kernel/debug/rcu/rcu_data
cat /sys/kernel/debug/rcu/rcu_exp
cat /sys/kernel/debug/rcu/rcu_gp
```

#### Ftrace 追踪

```bash
# 启用 RCU 追踪事件
echo 1 > /sys/kernel/debug/tracing/events/rcu/enable

# 常用追踪点
# - rcu_grace_period: 宽限期开始/结束
# - rcu_fqs: 强制静止状态检测
# - rcu_callback: 回调执行
# - rcu_unlock_preempt: 读侧退出

# 查看追踪结果
cat /sys/kernel/debug/tracing/trace

# 分析宽限期时长
cat /sys/kernel/debug/tracing/events/rcu/rcu_grace_period/enable
```

#### /proc 和 /sys 接口

```bash
# RCU 统计信息
cat /proc/stat | grep rcu

# 各 CPU 的 RCU 状态
cat /sys/kernel/debug/rcu/rcu_data/cpu*/stats

# 回调队列信息
cat /sys/kernel/debug/rcu/rcucbs

# Tree RCU 节点状态
cat /sys/kernel/debug/rcu/rcu_node

# 查看宽限期序号
cat /sys/kernel/debug/rcu/rcu_gp

# RCU expedited 信息
cat /sys/kernel/debug/rcu/rcu_exp
```

#### Lockdep RCU 检测

```c
// CONFIG_PROVE_RCU 开启后，lockdep 会检测:
// - 读侧使用了需要保护的 API 但没有 rcu_read_lock
// - 错误的 RCU 变体混用
// - 读侧可能的睡眠操作

// 常见警告:
// "RCU used illegally from extended quiescent state"
// "suspicious rcu_dereference_check() usage"

// 强制检查
RCU_LOCKDEP_WARN(condition, message);
```

#### Crash 工具分析

```bash
# 查看 RCU 状态
crash> p rcu_state
crash> p rcu_scheduler_active

# 查看 per-CPU RCU 数据
crash> p rcu_data
crash> struct rcu_data <addr>

# 查看回调队列
crash> struct rcu_data.nxtlist <addr>

# 查看当前宽限期
crash> p rcu_state.gp_seq

# 查看 RCU stall 相关进程
crash> foreach bt | grep -i rcu
```

---

### 十、性能分析与优化

#### 读侧开销分析

```
┌─────────────────────────────────────────────────────────────────────┐
│                     RCU 读侧开销分析                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  rcu_read_lock():                                                   │
│    preempt_disable(): ~3-5 cycles                                   │
│    (某些架构可能只需要 barrier)                                      │
│                                                                     │
│  rcu_dereference():                                                 │
│    READ_ONCE + smp_load_acquire: ~10-20 cycles                      │
│    (取决于架构和编译器优化)                                          │
│                                                                     │
│  rcu_read_unlock():                                                 │
│    preempt_enable(): ~3-5 cycles                                    │
│                                                                     │
│  总计: 约 15-30 cycles                                              │
│                                                                     │
│  对比其他锁:                                                         │
│    spin_lock/unlock: ~100-200 cycles                                │
│    mutex_lock/unlock: ~200-500 cycles                               │
│    rwlock_read_lock/unlock: ~50-100 cycles                          │
│                                                                     │
│  RCU 读侧开销仅为传统锁的 1/10 ~ 1/20                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 写侧开销分析

```
┌─────────────────────────────────────────────────────────────────────┐
│                     RCU 写侧开销分析                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  数据复制:                                                           │
│    kmalloc + memcpy: ~1-10 μs（取决于数据大小）                       │
│                                                                     │
│  指针替换:                                                           │
│    rcu_assign_pointer: ~10-20 cycles                                │
│                                                                     │
│  等待宽限期:                                                         │
│    synchronize_rcu():                                               │
│      - 正常: ~10-100 ms（取决于系统负载和 CPU 数）                    │
│      - expedited: ~1-10 ms（但消耗更多 CPU）                         │
│                                                                     │
│  call_rcu():                                                        │
│    回调注册: ~10-20 cycles                                           │
│    宽限期延迟: ~10-100 ms                                            │
│    回调执行: 在 RCU softirq 中                                       │
│                                                                     │
│  总写侧开销: 比传统锁大得多                                           │
│  适用条件: 写操作频率 << 读操作频率                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 适用条件判断

```
┌─────────────────────────────────────────────────────────────────────┐
│                    RCU 适用条件                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  RCU 收益 > RCU 开销 的条件:                                          │
│                                                                     │
│  设:                                                                 │
│    R = 读操作频率                                                    │
│    W = 写操作频率                                                    │
│    T_read = 读侧开销                                                 │
│    T_write = 写侧开销                                                │
│    T_lock = 传统锁开销                                               │
│                                                                     │
│  条件:                                                               │
│    R × T_read + W × T_write < (R + W) × T_lock                      │
│                                                                     │
│  简化:                                                               │
│    R × (T_lock - T_read) > W × (T_write - T_lock)                   │
│    读侧收益总和 > 写侧额外开销                                        │
│                                                                     │
│  经验法则:                                                           │
│    R/W > 100: RCU 明显优于传统锁                                     │
│    R/W > 10: RCU 可能优于传统锁                                      │
│    R/W < 10: 需要具体分析                                            │
│    R/W < 1: 传统锁更合适                                             │
│                                                                     │
│  其他因素:                                                           │
│    - 数据大小（复制开销）                                            │
│    - 读侧是否需要睡眠（是否需要 SRCU）                                │
│    - 内存压力（宽限期期间的额外内存）                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 优化策略

```c
// ═══════════════════════════════════════════════════════════════
//                    RCU 使用优化策略
// ═══════════════════════════════════════════════════════════════

// 1. 减少数据结构大小
struct config {
    int value;  // 小数据结构，复制快
    struct rcu_head rcu;
};

// 2. 使用 call_rcu 代替 synchronize_rcu（高频写）
void high_frequency_update(void)
{
    call_rcu(&old->rcu, free_callback);  // 异步，不阻塞
}

// 3. 批量更新
void batch_update(void)
{
    // 一次更新多个配置，只等待一次宽限期
    rcu_assign_pointer(config1, new1);
    rcu_assign_pointer(config2, new2);
    rcu_assign_pointer(config3, new3);
    
    synchronize_rcu();  // 只等待一次
    
    kfree(old1);
    kfree(old2);
    kfree(old3);
}

// 4. 使用 expedited 版本（紧急场景）
void urgent_update(void)
{
    rcu_assign_pointer(ptr, new);
    synchronize_rcu_expedited();  // 更快但消耗更多 CPU
    kfree(old);
}

// 5. 合适的 RCU 变体
// - 经典 RCU: 默认选择
// - SRCU: 需要睡眠时
// - RCU-sched: 调度器相关
// - RCU-bh: 网络软中断

// 6. 减少读临界区长度
void optimized_reader(void)
{
    int val;
    
    rcu_read_lock();
    val = rcu_dereference(ptr)->value;  // 尽快退出
    rcu_read_unlock();
    
    // 复杂处理在锁外进行
    process_value(val);
}
```

---

### 十一、RCU 与其他机制对比

#### RCU vs RWLock vs RW Semaphore

```
┌────────────────┬─────────────────┬─────────────────┬─────────────────┐
│     特性       │     RWLock      │     RW Sem      │      RCU        │
├────────────────┼─────────────────┼─────────────────┼─────────────────┤
│ 读侧开销       │ ~50-100 cycles  │ ~100-200 cycles │ ~15-30 cycles   │
│ 读侧可睡眠     │ 否              │ 是              │ 经典否，SRCU可  │
│ 读侧并发       │ 是              │ 是              │ 是（完全无锁）  │
│ 写侧开销       │ 小              │ 中等            │ 较大            │
│ 写者等待       │ 自旋            │ 睡眠            │ 复制+宽限期     │
│ 内存开销       │ 小              │ 小              │ 短暂增加        │
│ 适用场景       │ 读多写少，短临界│ 读多写少，长临界│ 读极多写极少    │
│ 数据一致性     │ 立即            │ 立即            │ 最终一致        │
│ 上下文限制     │ 任意            │ 仅进程          │ 任意（读）      │
└────────────────┴─────────────────┴─────────────────┴─────────────────┘

选择指南:
  读频率极高（>100x写） → RCU
  读频率中等（10-100x写）+ 短临界区 → RWLock
  读频率中等（10-100x写）+ 长临界区 → RW Semaphore
  读写频率相近 → Mutex 或 Spinlock
```

#### RCU vs Seqlock

```
┌────────────────┬─────────────────┬─────────────────┐
│     特性       │    Seqlock      │      RCU        │
├────────────────┼─────────────────┼─────────────────┤
│ 读侧开销       │ 极小（无锁）     │ 极小（无锁）    │
│ 读侧重试       │ 可能需要重试     │ 不需要重试      │
│ 写侧开销       │ 极小             │ 较大            │
│ 数据结构       │ 简单数据         │ 可复杂          │
│ 指针/链表      │ 不适用           │ 完美适用        │
│ 适用场景       │ 时间、统计计数   │ 配置、链表      │
│ 读侧睡眠       │ 否               │ SRCU可          │
└────────────────┴─────────────────┴─────────────────┘

// Seqlock 适用: 简单数值，如时间戳
// RCU 适用: 复杂结构，如配置对象、链表
```

---

### 十二、内核中的典型应用

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Linux 内核 RCU 应用实例                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. VFS 层                                                          │
│     - dentry 缓存查找                                               │
│     - inode 查找                                                    │
│     - superblock 列表                                               │
│                                                                     │
│  2. 网络子系统                                                       │
│     - 路由表查找                                                    │
│     - 网络设备列表                                                  │
│     - packet_type 列表                                              │
│     - 邻居表（neighbour cache）                                     │
│                                                                     │
│  3. 进程管理                                                         │
│     - task_struct 的某些字段                                        │
│     - PID 查找                                                      │
│     - cgroup 管理                                                   │
│                                                                     │
│  4. 定时器                                                           │
│     - timer_base 管理                                               │
│     - hrtimer                                                       │
│                                                                     │
│  5. 文件系统                                                         │
│     - 文件锁管理                                                    │
│     - 文件描述符表                                                  │
│                                                                     │
│  6. 内存管理                                                         │
│     - mm_struct 部分字段                                            │
│     - VMA 管理                                                      │
│                                                                     │
│  7. 安全子系统                                                       │
│     - LSM（Linux Security Module）钩子                              │
│     - SELinux 策略                                                 │
│                                                                     │
│  8. 驱动                                                             │
│     - 设备列表管理                                                  │
│     - 中断处理相关                                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 十三、总结

```
┌─────────────────────────────────────────────────────────────────────┐
│                      RCU 使用口诀                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  读极多写极少，RCU 是首选。                                          │
│  读侧零开销，写侧复制改。                                            │
│  宽限期等旧读，过后释旧数。                                          │
│  读者只读不改，切记莫睡眠。                                          │
│  写者锁保护，指针原子换。                                            │
│  deref 必使用，assign 不能忘。                                      │
│  SRCU 可睡眠，经典不可睡。                                           │
│  Stall 看超时，回调队列积。                                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      RCU 快速选择指南                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  读/写比例？                                                         │
│  ├─ > 100:1      → RCU（明显优势）                                  │
│  ├─ 10:1 - 100:1 → 考虑 RCU（需分析）                               │
│  ├─ < 10:1       → RWLock 或 RW Sem                                │
│  └─ ~1:1         → Mutex 或 Spinlock                               │
│                                                                     │
│  读侧需要睡眠？                                                      │
│  ├─ 是           → SRCU                                             │
│  └─ 否           → Classic RCU                                      │
│                                                                     │
│  数据结构？                                                          │
│  ├─ 简单数值      → 可能 Seqlock 更好                               │
│  ├─ 指针/链表    → RCU 完美适用                                     │
│  ├─ 复杂结构     → RCU 适用                                         │
│  └─ 大数据       → 考虑复制开销                                     │
│                                                                     │
│  宽限期需求？                                                        │
│  ├─ 可阻塞        → synchronize_rcu()                               │
│  ├─ 不可阻塞      → call_rcu()                                      │
│  └─ 紧急          → synchronize_rcu_expedited()                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 关键注意点

### 1. **读侧必须只读**

```c
// RCU 读临界区内只能读取数据
rcu_read_lock();
p = rcu_dereference(ptr);
val = p->field;      // ✓ 只读
p->field = new_val;  // ✗ 错误！修改操作
rcu_read_unlock();
```

### 2. **宽限期的本质**

```
宽限期 = 等待所有"在替换指针前进入"的读者退出

关键理解:
- 不是等待"所有"读者
- 只等待"看到旧数据版本"的读者
- 替换指针后进入的读者看到新数据，不影响宽限期

静止点（Quiescent State）:
- 上下文切换
- 用户态执行
- idle 状态
- 这些时刻一定不在 RCU 读临界区
```

### 3. **内存屏障的重要性**

```c
// rcu_dereference 和 rcu_assign_pointer 包含必要的内存屏障
// 这是 RCU 正确性的关键

// 写者
rcu_assign_pointer(ptr, new);  // 确保 new 已完全初始化后再替换

// 读者
p = rcu_dereference(ptr);      // 确保看到最新的指针值

// 没有这些屏障:
// - 编译器优化可能导致乱序
// - CPU 缓存可能看到旧值
// - 数据不一致和内存安全问题
```

### 4. **SRCU vs Classic RCU**

```c
// Classic RCU
// - 读侧: preempt_disable/enable
// - 不可睡眠
// - 开销更小
// - 适用: 大多数内核场景

// SRCU
// - 读侧: 获取/释放索引
// - 可以睡眠
// - 开销更大
// - 适用: 需要调用 copy_to_user、等待 I/O 等

// 选择原则:
// 能用 Classic RCU 就用 Classic
// 只有确实需要睡眠时才用 SRCU
```

### 5. **RCU 回调注意事项**

```c
// call_rcu 回调执行环境
// - 在 RCU softirq 中执行
// - 不能睡眠
// - 执行顺序与注册顺序相同（同 CPU）

// 回调设计要点
static void my_rcu_callback(struct rcu_head *rcu)
{
    struct my_data *data = container_of(rcu, struct my_data, rcu);
    
    // ✓ 可以: kfree、简单的清理
    kfree(data);
    
    // ✗ 不能: 睡眠、复杂的操作
    // msleep(100);          // 错误！
    // mutex_lock(&lock);    // 错误！可能睡眠
}

// 需要复杂操作时，使用 workqueue
static void my_rcu_callback(struct rcu_head *rcu)
{
    struct my_data *data = container_of(rcu, struct my_data, rcu);
    INIT_WORK(&data->work, complex_cleanup_work);
    schedule_work(&data->work);
}
```

## 典型陷阱汇总

| 场景 | 错误做法 | 正确做法 |
|------|----------|----------|
| 读侧操作 | 修改数据 | 只读访问 |
| 数据释放 | 替换后立即释放 | 等待宽限期后释放 |
| 经典 RCU 睡眠 | msleep/copy_from_user | 使用 SRCU |
| 指针读取 | 直接读取 `p = ptr` | 使用 `rcu_dereference(ptr)` |
| 指针更新 | 直接赋值 `ptr = new` | 使用 `rcu_assign_pointer(ptr, new)` |
| 链表删除 | 读侧无锁删除 | 写侧用锁保护后删除 |
| 回调函数 | 在回调中睡眠 | 在回调中触发 workqueue |
| SRCU 初始化 | 忽略初始化 | 必须调用 `init_srcu_struct` |

## Crash 工具解析要点

```bash
# 查看 RCU 状态
crash> p rcu_state
crash> p rcu_state.gp_seq

# 查看 per-CPU 回调队列
crash> struct rcu_data.nxtlist -a

# 查看宽限期状态
crash> p rcu_state.gp_state

# 查看是否有 stall
crash> p rcu_state.gp_activity

# 查看 RCU 节点树
crash> struct rcu_node -a
```

---