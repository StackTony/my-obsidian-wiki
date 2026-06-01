## 前言
在 [LINUX软中断-softirq](https://blog.csdn.net/mxgsgtc/article/details/128718259?spm=1001.2014.3001.5501) [[Linux 软中断softirq]]的描述中，提到过ksoftirqd，这篇文章就介绍ksoftirqd

### ksoftirqd 是什么？

ksoftirqd 是个内核线程，在创建的时候是绑定cpu的，每一个core对应生成一个ksoftirqd 线程

比如当前系统有4个core

```
~# ps aux | grep ksoftirqd
root        3  0.0  0.0      0     0 ?        S    14:20   0:00 [ksoftirqd/0] //core 0
root        9  0.0  0.0      0     0 ?        S    14:20   0:00 [ksoftirqd/1] //core 1
root       12  0.0  0.0      0     0 ?        S    14:20   0:00 [ksoftirqd/2] //core 2
root       15  0.0  0.0      0     0 ?        S    14:20   0:00 [ksoftirqd/3] //core 3
```

### ksoftirqd 的作用

ksoftirqd 的作用就是处理softirq用，它的本质就是调用 \_\_do\_softirq

### ksoftirqd 的触发条件

`kernel/softirq.c` 中对 ksoftirqd 系统进行了初始化：

```c
static struct smp_hotplug_thread softirq_threads = {
      .store              = &ksoftirqd,
      .thread_should_run  = ksoftirqd_should_run,
      .thread_fn          = run_ksoftirqd,
      .thread_comm        = "ksoftirqd/%u",
};

static __init int spawn_ksoftirqd(void)
{
      register_cpu_notifier(&cpu_nfb);

      BUG_ON(smpboot_register_percpu_thread(&softirq_threads));

      return 0;
}
early_initcall(spawn_ksoftirqd);
```

看到注册了两个回调函数： `ksoftirqd_should_run` 和 `run_ksoftirqd` 。这两个函数都会从 `kernel/smpboot.c` 里调用，作为事件处理循环的一部分。

所以每个核上都有一个ksoftirqd。

`kernel/smpboot.c` 里面的代码首先调用 `ksoftirqd_should_run` 判断是否有 pending 的软中断，如果有，就执行 `run_ksoftirqd` ，后者做一些 bookeeping 工作，然后调用 `__do_softirq` 。

`__do_softirq` 做的几件事情：

- 判断哪个 softirq 被 pending
- 计算 softirq 时间，用于统计
- 更新 softirq 执行相关的统计数据
- 执行 pending softirq 的处理函数
```c
asmlinkage __visible void __do_softirq(void)
{
    unsigned long end = jiffies + MAX_SOFTIRQ_TIME;
    unsigned long old_flags = current->flags;
    int max_restart = MAX_SOFTIRQ_RESTART;
    struct softirq_action *h;
    bool in_hardirq;
    __u32 pending;
    int softirq_bit;

    /*
     * Mask out PF_MEMALLOC s current task context is borrowed for the
     * softirq. A softirq handled such as network RX might set PF_MEMALLOC
     * again if the socket is related to swap
     */
    current->flags &= ~PF_MEMALLOC;

    pending = local_softirq_pending();    //获取当前CPU的软中断寄存器__softirq_pending值到局部变量pending。
    account_irq_enter_time(current);

    __local_bh_disable_ip(_RET_IP_, SOFTIRQ_OFFSET);    //增加preempt_count中的softirq域计数，表明当前在软中断上下文中。
    in_hardirq = lockdep_softirq_start();

restart:
    /* Reset the pending bitmask before enabling irqs */
    set_softirq_pending(0);    //清除软中断寄存器__softirq_pending。

    local_irq_enable();    //打开本地中断

    h = softirq_vec;    //指向softirq_vec第一个元素，即软中断HI_SOFTIRQ对应的处理函数。

    while ((softirq_bit = ffs(pending))) {    //ffs()找到pending中第一个置位的比特位，返回值是第一个为1的位序号。这里的位是从低位开始，这也和优先级相吻合，低位优先得到执行。如果没有则返回0，退出循环。
        unsigned int vec_nr;
        int prev_count;

        h += softirq_bit - 1;    //根据sofrirq_bit找到对应的软中断描述符，即软中断处理函数。

        vec_nr = h - softirq_vec;    //软中断序号
        prev_count = preempt_count();

        kstat_incr_softirqs_this_cpu(vec_nr);

        trace_softirq_entry(vec_nr);
        h->action(h);    //执行对应软中断函数
        trace_softirq_exit(vec_nr);
        if (unlikely(prev_count != preempt_count())) {
            pr_err("huh, entered softirq %u %s %p with preempt_count %08x, exited with %08x?\n",
                   vec_nr, softirq_to_name[vec_nr], h->action,
                   prev_count, preempt_count());
            preempt_count_set(prev_count);
        }
        h++;    //h递增，指向下一个软中断
        pending >>= softirq_bit;    //pending右移softirq_bit位
    }

    rcu_bh_qs();
    local_irq_disable();    //关闭本地中断

    pending = local_softirq_pending();    //再次检查是否有软中断产生，在上一次检查至此这段时间有新软中断产生。
    if (pending) {
        if (time_before(jiffies, end) && !need_resched() && max_restart)    //再次触发软中断执行的三个条件：1.软中断处理时间不超过2jiffies，200Hz的系统对应10ms；2.当前没有有进程需要调度，即!need_resched()；3.这种循环不超过10次。
            goto restart;

        wakeup_softirqd();    //如果上面的条件不满足，则唤醒ksoftirq内核线程来处理软中断。
    }

    lockdep_softirq_end(in_hardirq);
    account_irq_exit_time(current);
    __local_bh_enable(SOFTIRQ_OFFSET);    //减少preempt_count的softirq域计数,和前面增加计数呼应。表示这段代码处于软中断上下文。
    WARN_ON_ONCE(in_interrupt());
    tsk_restore_flags(current, old_flags, PF_MEMALLOC);
}
```

查看 CPU 利用率时，si 字段对应的就是 softirq，度量（从硬中断转移过来的）软中断的 CPU 使用量。

![](https://i-blog.csdnimg.cn/blog_migrate/f5ebb0f31702b8867f0f3fc38edbb1bd.png)

### 监测

软中断的信息可以从 `/proc/softirqs` 读取：

![](https://i-blog.csdnimg.cn/blog_migrate/2db84d324d9cdff13f4d04b90cc344a9.png)

### 总结

中断是一种异步的事件处理机制，用来提高系统的并发处理能力。中断事件发生，会触发执行中断处理程序，而中断处理程序被分为上半部和下半部这两个部分。上半部对应硬中断，用来快速处理中断；下半部对应软中断，用来异步处理上半部未完成的工作。Linux 中的软中断包括网络收发、定时、调度、RCU 锁等各种类型，我们可以查看 proc 文件系统中的 /proc/softirqs ，观察软中断的运行情况。在 Linux 中，每个 CPU 都对应一个软中断内核线程，名字是 `ksoftirqd/CPU 编号。` 当软中断事件的频率过高时，内核线程也会因为 CPU 使用率过高而导致软中断处理不及时，进而引发网络收发延迟、调度缓慢等性能问题。