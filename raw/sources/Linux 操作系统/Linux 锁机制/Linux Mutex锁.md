
## Linux Mutex 锁完整介绍

---

### 一、基本概念

**Mutex（互斥锁）** 是 Linux 内核中最常用的睡眠锁，用于保护临界区资源。

#### 核心特性

|特性|说明|
|---|---|
|**睡眠锁**|竞争失败时进程会睡眠，可被调度器切换|
|**可递归**|同一进程可多次获取（需 `CONFIG_DEBUG_MUTEXES` 检测死锁）|
|**自旋优化**|持锁时间短时，先自旋等待再睡眠|
|**优先级继承**|支持 PI，避免优先级反转|
|**进程上下文**|仅限进程上下文使用，不可用于中断|

#### 与 Spinlock 对比

```
┌────────────┬────────────────────┬───────────────────┐
│   特性      │      Mutex         │     Spinlock      │
├────────────┼────────────────────┼───────────────────┤
│ 竞争时行为  │ 睡眠等待            │ 忙等待（自旋）       │
│ 上下文限制  │ 仅进程上下文         │ 任意上下文          │
│ 持锁时间    │ 可长时间持有        │ 必须极短            │
│ 内存开销    │ 较大（等待队列）     │ 极小               │
│ 中断中使用  │ ❌ 禁止            │ ✓ 配合 _irq 版本    │
│ 适用场景    │ I/O、长时间临界区    │ 中断、极短临界区     │
└────────────┴────────────────────┴───────────────────┘
```

---

### 二、数据结构

#### 核心结构体

```c
struct mutex {
    atomic_long_t owner;      // 持有者 + 标志位（编码后）
    spinlock_t wait_lock;     // 保护等待队列的自旋锁
    struct list_head wait_list; // 等待者队列
    
#ifdef CONFIG_MUTEX_SPIN_ON_OWNER
    struct optimistic_spin_queue osq; // MCS 锁（乐观自旋）
#endif
    
#ifdef CONFIG_DEBUG_MUTEXES
    void *magic;
    struct task_struct *owner_task;  // 调试用的原始指针
    const char *name;                 // 锁名称
    void *magic;
#endif
    
#ifdef CONFIG_DEBUG_LOCK_ALLOC
    struct lockdep_map dep_map;      // 锁依赖追踪
#endif
};
```

#### 等待者结构

```c
struct mutex_waiter {
    struct list_head list;    // 链入 wait_list
    struct task_struct *task; // 等待进程
#ifdef CONFIG_DEBUG_MUTEXES
    void *magic;
#endif
};
```

#### Owner 字段编码

```
┌─────────────────────────────────────────────┬─────┐
│         task_struct 指针 (对齐到 8 字节)      │flags│
│                   高位                      │ 低3位│
└─────────────────────────────────────────────┴─────┘
                                                   │
                            ┌──────────────────────┴───────────────┐
                            │    0x01: MUTEX_FLAG_WAITERS (有等待者)│
                            │    0x02: MUTEX_FLAG_HANDOFF  (移交锁) │
                            │    0x04: MUTEX_FLAG_MUST_SPIN        │
                            └──────────────────────────────────────┘
```

---

### 三、锁操作流程

#### 1. mutex_lock() 流程

```
mutex_lock()
    │
    ▼
┌─────────────────────────┐
│ 尝试原子获取锁            │
│ (cmpxchg count: 1→0)    │
└───────────┬─────────────┘
            │
      ┌─────┴─────┐
      │ 成功?      │
      └─────┬─────┘
       Yes  │  No
       ▼    │   ▼
   [获取成功] │ ┌──────────────────────┐
             │ │ __mutex_lock_slowpath│
             │ └──────────┬───────────┘
             │            │
             │            ▼
             │    ┌────────────────────┐
             │    │ 开启乐观自旋？       │
             │    │ (MCS 锁机制)        │
             │    └────────┬───────────┘
             │             │
             │       ┌─────┴─────┐
             │       │ 自旋成功?  │
             │       └─────┬─────┘
             │        Yes  │  No
             │         ▼   │   ▼
             │    [获取成功] │ ┌──────────────────┐
             │              │ │ 加入等待队列睡眠   │
             │              │ │ schedule()       │
             │              │ └──────────────────┘
             │              │          │
             │              │          ▼
             │              │   ┌──────────────┐
             │              │   │ 被唤醒后重试   │
             │              │   └──────────────┘
             ▼              ▼
        [设置 owner = current]
```

#### 2. mutex_unlock() 流程

```
mutex_unlock()
    │
    ▼
┌─────────────────────────┐
│ 清除 owner 字段          │
└───────────┬─────────────┘
            │
            ▼
┌──────────────────────────────┐
│ 检查是否有等待者               │
│ (owner & MUTEX_FLAG_WAITERS) │
└───────────┬──────────────────┘
            │
      ┌─────┴─────┐
      │ 有等待者?  │
      └─────┬─────┘
       Yes  │        No
       ▼    │        ▼
┌───────────────┐ │ 
│ wakeup_process│ │ 直接返回
│ 唤醒队首等待者  │ │
└───────────────┘ │
```

#### 3. 乐观自旋

```
乐观自旋条件:
┌──────────────────────────────────────────┐
│ 1. CONFIG_MUTEX_SPIN_ON_OWNER 开启       │
│ 2. 锁持有者正在运行                        │
│ 3. 只有一个等待者或 MCS 队列为空            │
│ 4. 未超过自旋阈值                          │
└──────────────────────────────────────────┘

优势: 避免上下文切换开销
场景: 持锁时间极短，等待者很快就能获取
```

---

### 四、API 详解

#### 基础 API

```c
// 定义并初始化
DEFINE_MUTEX(name);                    // 静态定义
mutex_init(&mutex);                    // 动态初始化

// 锁获取
void mutex_lock(struct mutex *lock);   // 阻塞获取
int mutex_lock_interruptible(struct mutex *lock);  // 可被信号中断
int mutex_lock_killable(struct mutex *lock);      // 仅响应 SIGKILL
int mutex_trylock(struct mutex *lock); // 非阻塞尝试

// 锁释放
void mutex_unlock(struct mutex *lock);

// 状态查询
int mutex_is_locked(struct mutex *lock);  // 是否锁定
```

#### 高级 API

```c
// 带超时的获取
int mutex_lock_timeout(struct mutex *lock, unsigned long jiffies);

// 原子上下文安全检查
int atomic_dec_and_mutex_lock(atomic_t *cnt, struct mutex *lock);

// 优先级继承版本
struct mutex_pi {
    struct mutex base;
    // PI 相关字段
};
```

#### 使用模式

```c
// 基本模式
mutex_lock(&lock);
// 临界区
mutex_unlock(&lock);

// 可中断模式
if (mutex_lock_interruptible(&lock))
    return -ERESTARTSYS;
// 临界区
mutex_unlock(&lock);

// 尝试获取模式
if (!mutex_trylock(&lock))
    return -EBUSY;
// 临界区
mutex_unlock(&lock);

// 守卫模式 (Linux 6.x)
guard(mutex)(&lock);  // 自动释放
```

---

### 五、典型场景

#### 适用场景

```c
// ✓ 场景1: 长时间临界区（可能睡眠）
mutex_lock(&data->lock);
if (need_copy)
    copy_large_data();      // 可能触发页面故障
process_data();
mutex_unlock(&data->lock);

// ✓ 场景2: I/O 操作
mutex_lock(&device->lock);
write_to_device(buf, len);  // 可能阻塞
mutex_unlock(&device->lock);

// ✓ 场景3: 需要保护的复杂数据结构
mutex_lock(&fs->inode_lock);
if (!inode->initialized) {
    err = init_inode(inode);  // 可能睡眠
    if (err) goto out;
}
// 操作 inode
out:
mutex_unlock(&fs->inode_lock);
```

#### 错误使用

```c
// ✗ 错误1: 中断上下文使用
irqreturn_t my_handler(int irq, void *dev)
{
    mutex_lock(&dev->lock);  // 致命错误！
    // ...
}

// ✗ 错误2: 持锁时睡眠
mutex_lock(&lock);
msleep(100);          // 睡眠本身合法，但长时间持锁影响性能
copy_from_user(...);  // 可能睡眠，持锁时需谨慎
mutex_unlock(&lock);

// ✗ 错误3: 忘记释放
mutex_lock(&lock);
if (error)
    return -EINVAL;   // 忘记 unlock！
mutex_unlock(&lock);

// ✗ 错误4: 跨进程/线程传递锁
// mutex 与进程上下文绑定，不可跨进程传递
```

---

### 六、调试技巧

#### 1. Lockdep 检测

```bash
# 开启内核配置
CONFIG_LOCKDEP=y
CONFIG_DEBUG_MUTEXES=y

# 常见错误报告
# - 死锁检测
# - 锁顺序违规
# - 在中断上下文使用 mutex
```

#### 2. 通过 /proc 查看

```bash
# 查看被锁阻塞的进程
$ cat /proc/<pid>/stack
# 显示 mutex_lock 相关的调用栈

# 查看所有锁竞争
$ cat /proc/lockdep
$ cat /proc/lockdep_stats
```

#### 3. Crash 工具分析

```bash
# 查看 mutex 状态
crash> struct mutex <addr>

# 解码 owner 获取持有者
crash> p/x ((struct mutex *)<addr>)->owner.counter & ~0x7

# 查看等待队列
crash> list -s mutex_waiter.task <wait_list地址>

# 查找阻塞在 mutex 的进程
crash> foreach bt | grep -B10 mutex_lock
```

#### 4. Ftrace 追踪

```bash
# 启用 mutex 追踪
echo 1 > /sys/kernel/debug/tracing/events/lock/lock_acquire/enable
echo 1 > /sys/kernel/debug/tracing/events/lock/lock_release/enable

# 查看追踪结果
cat /sys/kernel/debug/tracing/trace
```

---

### 七、性能优化

#### 1. 减少锁粒度

```c
// 粗粒度（差）
mutex_lock(&global_lock);
process_all_items(array, 1000);
mutex_unlock(&global_lock);

// 细粒度（好）
for (i = 0; i < 1000; i++) {
    mutex_lock(&array[i].lock);
    process_item(&array[i]);
    mutex_unlock(&array[i].lock);
}
```

#### 2. 减少持锁时间

```c
// 差：持锁时做耗时操作
mutex_lock(&lock);
data = prepare_data();  // 不需要锁
write_data(data);       // 需要锁
mutex_unlock(&lock);

// 好：只在必要时持锁
data = prepare_data();  // 锁外准备
mutex_lock(&lock);
write_data(data);       // 只保护写入
mutex_unlock(&lock);
```

#### 3. RCU 替代读多写少场景

```c
// 读路径无锁
rcu_read_lock();
item = rcu_dereference(ptr);
use(item);
rcu_read_unlock();

// 写路径用 mutex
mutex_lock(&lock);
new = alloc_item();
old = ptr;
rcu_assign_pointer(ptr, new);
mutex_unlock(&lock);
synchronize_rcu();
free(old);
```

---

### 八、总结

```
┌─────────────────────────────────────────────────────────┐
│                    Linux Mutex 要点                      │
├─────────────────────────────────────────────────────────┤
│ ✓ 睡眠锁，仅用于进程上下文                              │
│ ✓ owner 字段编码了 task_struct 指针 + 标志位            │
│ ✓ 支持乐观自旋优化                                      │
│ ✓ 使用 lockdep 检测死锁和违规使用                       │
│ ✓ 持锁时间短用 spinlock，长用 mutex                     │
│ ✓ 读多写少考虑 RCU                                      │
└─────────────────────────────────────────────────────────┘
```

## 关键注意点

### 1. **上下文检查**

```c
// mutex 不能在中断上下文使用！
if (in_interrupt()) {
    // 错误！mutex 可能睡眠
    WARN_ON(1);
}
```
- Mutex **不可用于中断上下文**（ISR、softirq）
- 如需在中断中使用，应选择 `spinlock`

### 2. **抢占安全性**

```c
// 设置 owner 时需禁用抢占
preempt_disable();
lock->owner = current;
preempt_enable();

// 或者使用 atomic 方式
atomic_long_set(&lock->owner, (unsigned long)current);
```

### 3. **等待队列中的 task 有效性**

```c
// 唤醒等待者时，task 可能已经退出
struct mutex_waiter *waiter = list_first_entry(&lock->wait_list, ...);
struct task_struct *task = waiter->task;

// 需要 acquire semantics 防止 task 在检查后被释放
if (task && !task->state == TASK_DEAD) {
    wake_up_process(task);
}
```

### 4. **Owner 指针优化（乐观自旋）**

现代 Linux 使用带标志位的 owner 指针：

```c
// owner 指针的低几位用作标志
#define MUTEX_FLAG_WAITERS   0x01
#define MUTEX_FLAG_HANDOFF   0x02
#define MUTEX_FLAG_MUTEX_INIT 0x04

// 获取真实 task_struct
static inline struct task_struct *mutex_get_owner(struct mutex *lock)
{
    unsigned long owner = atomic_long_read(&lock->owner);
    // 清除标志位，得到真实的 task_struct 指针
    return (struct task_struct *)(owner & ~0x07);
}
```

### 5. **内存屏障的正确性**

```c
// 确保 owner 设置在锁获取之后可见
smp_store_release(&lock->owner, current);

// 锁释放时，先清除 owner，再释放锁
smp_store_release(&lock->owner, NULL);
smp_wmb();
atomic_set(&lock->count, 1);
```

## 典型陷阱

|场景|错误做法|正确做法|
|---|---|---|
|中断处理函数中使用 mutex|`mutex_lock(&lock)`|使用 `spin_lock_irqsave`|
|乐观自旋时访问 task_struct|直接解引用|检查有效性 + RCU 保护|
|设置 owner 时|普通赋值|使用 atomic + barrier|
|进程退出时持有锁|忽略|在 exit_mm 等路径处理|

## Crash 工具解析要点

### 1. 基本读取

```bash
# 查看 mutex 结构
crash> struct mutex <address>

# 直接读取 owner 字段
crash> struct mutex.owner <address>
```

### 2. 解码真实指针

```bash
# 假设 owner 值为 0xffff888123456789
# 需要清除低 3 位标志位

crash> p/x (0xffff888123456789 & ~0x7)
$1 = 0xffff888123456788

# 或者使用 crash 表达式
crash> p/x ((struct mutex *)<addr>)->owner.counter & ~0x7
```

### 3. 判断锁状态

```bash
# owner 为 0 表示未锁定
crash> p ((struct mutex *)<addr>)->owner.counter
$2 = 0x0  # 未锁定

# 非 0 值需要解码
crash> p/x ((struct mutex *)<addr>)->owner.counter
$3 = 0xffff888123456789

# 检查是否有等待者
crash> p ((struct mutex *)<addr>)->owner.counter & 0x1
$4 = 1  # 有等待者
```

### 4. 获取持有者进程信息

```bash
# 步骤：解码指针 -> 转换为 task_struct -> 查看进程

crash> set $owner = ((struct mutex *)0xffff888123456000)->owner.counter & ~0x7
crash> struct task_struct.comm,(unsigned long)$owner
  comm = "thread-name"
```
或一步到位：
```bash
crash> task -R comm ((struct task_struct *)(((struct mutex *)<addr>)->owner.counter & ~0x7))
```

### 5. 检查等待队列

```bash
# 查看等待队列
crash> struct mutex.wait_list <addr>

# 遍历等待者
crash> list -s mutex_waiter.task <wait_list地址>
```


**实际举例：**
crash\> p rtnl_mutex
rtnl_mutex = \$1 = {
owner = {
counter = -98125497684349
},

![[Pasted image 20260428144813.png]]

**注意：** 在Linux内核的mutex锁实现中，owner字段的低3位被用作状态标志位，而不是指针的一部分，因此使用crash解析owner时，必须将低3位清零，才能得到正确的task_struct


crash\> struct task_struct FFFFA6C160912E8==0== \|grep -i pid
pid = 774537,

rtnl锁持有者774537
