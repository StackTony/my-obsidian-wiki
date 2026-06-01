### 前言

关于linux的软中断的文章，在网上可以找到很多，但总觉着讲的都不够深入，打算自己写一下

### 软中断的由来

在linux下，有两种中断：

1. 硬中断  
    GIC产生一个中断后通知cpu，cpu硬件会跳到特定的地址去执行中断服务程序且不能被打断（因为linux中断服务程序在执行的时候会关本地core的中断响应, 即中断不能嵌套）,但是随之产生一个问题，中断服务程序如果执行太长，就会影响系统响应，所以为了提高系统响应，linux想提前打开本地core的中断响应，于是将中断服务程序分成两个阶段：①ISR 　②softirq 。  
    也就是说，很早之前的linux把中断响应再开的时机放在了执行完中断服务程序之后，后来分成两个处理阶段后放在了执行完 ISR之后。  
    另外，现在提到硬中断，默认指的就是ISR。
    
2. 软中断（softirq）  
    因为ISR需要快点执行完，所以仅处理一些寄存器的设置等，ISR执行完后，会进入softirq阶段（一般会把执行比较慢的部分放在了softirq的阶段), 进入softirq阶段时, 本地core的中断响应会被打开（硬件）  
    此时的系统：  
    **可以接受新的硬件中断（ISR），打断正在running的softirq。  
    问题来了：比如这时来了个tick中断，执行对应ISR进行调度处理, softirq执行流时被切到其他进程呢？**  
    因为softirq的处理毕竟属于中断服务程序的一部分，必须要尽量保持中断不能被打断的特性.  
    即 softirq阶段的处理规则是：可以响应硬件中断（提高系统响应）优先处理新来的ISR，除此以外在本core上有绝对的执行优先权，也就是说，新来的ISR处理退出后，会继续返回到被打断的softirq流中继续执行，不会在本core上被切走。  
    问题来了，如何做到不被本core上的其他任务抢占呢？需要先补充一下知识点。
    

### 基础知识

##### 运行上下文

大家都知道，在linux内核里用current_thread_info变量来表示本core上当前所运行程序的信息。

```c
union thread_union {
	struct thread_info thread_info;
	unsigned long stack[THREAD_SIZE/sizeof(long)];
};
static inline struct thread_info *current_thread_info(void) __attribute_const__;

static inline struct thread_info *current_thread_info(void)
{
	register unsigned long sp asm ("sp");
	return (struct thread_info *)(sp & ~(THREAD_SIZE - 1));
}
```

从上面的定义可以看出，thread_info与 栈 共同占用一个page，thread_info从低地址开始存放，而栈从高地址往低地址增长。由于页对齐的缘故，栈指针sp & ~(THREAD_SIZE - 1)就是thread_info。  
另外，内核程序在运行的过程中，需要有一个变量(preempt_count)

```c
//#define preempt_count()	(current_thread_info()->preempt_count)
current_thread_info()->preempt_count
```

来标明目前此程序正在运行的环境（即上下文），在linux中，用不同的整数来代表不同的上下文。

```c
//这里的 PREEMPT_SHIFT 是什么值就不做讨论了。
#define PREEMPT_OFFSET	(1UL << PREEMPT_SHIFT)
#define SOFTIRQ_OFFSET	(1UL << SOFTIRQ_SHIFT)
#define HARDIRQ_OFFSET	(1UL << HARDIRQ_SHIFT)
#define NMI_OFFSET	(1UL << NMI_SHIFT)
```

比如，来了个中断，当前运行的任务被打断，那么这时候此任务应该被标识为正运行在中断上下文中  
比如来个硬中断，

```c
//# define add_preempt_count(val)	do { preempt_count() += (val); } while (0)
//# define sub_preempt_count(val)	do { preempt_count() -= (val); } while (0)
add_preempt_count(HARDIRQ_OFFSET);
```

即把 preempt_count变量加上 HARDIRQ_OFFSET后的值，就表示current正运行在中断上下文。  
随之而来的问题就出现了，preempt_count存在的意义是什么呢？，仅仅就是为了标识当前程序所运行的上下文吗？,我们接着说。

##### linux的抢占调度

上面的问题跟linux的调度有关，我们都知道，linux内核是可抢占的，调度 算法 是CFS，其实关于内核程序之间的调度切换分为两个阶段。

1. check点(检查当前线程是否需要被调度出去)  
    比如说 tick时钟到了后， tick中断ISR中, 会通过调度算法（CFS）判断当前任务是否应该被切出去（比如运行时间到了），如果判断true，则将上面变量中的flags程序置位为需要被调度。

```c
 current_thread_info()->flags = TIF_NEED_RESCHED
```

通过代码感受一下流程

```c
//基于allwinner的平台
//sunxi_timer.c
//首先, 平台必须要注册一个定时器,用来触发tick中断用
clockevents_register_device(&sunxi_clockevent);
	clockevents_register_device(&sunxi_clockevent);
		clockevents_register_device
			list_add(&dev->list, &clockevent_devices);
			clockevents_do_notify(CLOCK_EVT_NOTIFY_ADD, dev);
				ret = nb->notifier_call(nb, val, v);
					tick_check_new_device
						tick_setup_device
							tick_setup_periodic
								tick_set_periodic_handler
									dev->event_handler = tick_handle_periodic;
//tick中断的ISR
sunxi_timer_interrupt
	evt->event_handler(evt);

//event_handler
//tick中断来到后，执行此函数
tick_handle_periodic
	tick_periodic
		update_process_times
			scheduler_tick
				//CFS算法
				curr->sched_class->task_tick(rq, curr, 0);
					task_tick_fair
						entity_tick
							//如果当前进程需要被调度出去的话，则flags置位：TIF_NEED_RESCHED
							check_preempt_tick
								resched_task
									set_tsk_need_resched
										set_tsk_thread_flag(tsk,TIF_NEED_RESCHED);
```

2. 发生抢占(实际发生线程切换的timing)  
    实际发生线程切换，发生在中断要返回的时候(当然也有别的切换点，这篇文章不考虑)，我们看一下

```c
//GIC发生中断，会调到 __irq_svc(中断向量)这里执行
__irq_svc:
        svc_entry
        irq_handler //执行中断函数 (ISR + softirq)

#ifdef CONFIG_PREEMPT
        get_thread_info tsk //得到当前运行程序的thread_info 结构体
		//接下来就是重点，如果 thread_info 的结构体中的 preempt_count 的值为0
		//并且flags的值是 TIF_NEED_RESCHED，则执行svc_preempt
        ldr     r8, [tsk, #TI_PREEMPT]          @ get preempt count
        ldr     r0, [tsk, #TI_FLAGS]            @ get flags
        teq     r8, #0                          @ if preempt count != 0
        movne   r0, #0                          @ force flags to 0
        tst     r0, #_TIF_NEED_RESCHED
        blne    svc_preempt
#endif

#ifdef CONFIG_PREEMPT
svc_preempt:
        mov     r8, lr
        //执行 preempt_schedule_irq 函数完成线程切换调度  
1:      bl      preempt_schedule_irq            @ irq en/disable is done inside
        ldr     r0, [tsk, #TI_FLAGS]            @ get new tasks TI_FLAGS
        tst     r0, #_TIF_NEED_RESCHED
        moveq   pc, r8                          @ go again
        b       1b
#endif

```

由上面的分析可知， 完成在本core上的线程切换，必须要满足

1. 当前本core执行的线程是需要被调度的（flags == TIF_NEED_RESCHED）
2. 当前本core执行的线程的是可被抢占（preempt_count == 0）

至此，我们发现， preempt_count 的作用，即在实际发生调度切换时，如果处在中断上下文中（硬中断，软中断），也就是preempt_count 不为0的话, 当前进程是不能被切走的。

##### 软中断的软件实现

接下来我们在回答一下上面的疑问：

> 如何做到不被本core上的其他任务抢占呢？

通过上面的知识，就不难分析了。  
当要执行软中断任务时，会调用__do_softirq函数，此函数刚开始就会调用 __local_bh_disable 函数将当前进程的上下文设置为 softirq环境（软中断环境）

```c
add_preempt_count(SOFTIRQ_OFFSET);
```

实际上就是：preempt_count = SOFTIRQ_OFFSET;  
设置preempt_count 变量后，接下来会执行softirq的任务链表，任务在处理的过程中是处在preempt_count 变量 非0的状态下，所以此时本core上如果在来一个tick中断，中断返回时，因为preempt_count 不为0所以当前线程（正处于softirq阶段，并且在执行软中断的任务）不会被调度出去，实现了在本core上不能被其他任务抢占的机制。  
当软中断执行结束后，会 __local_bh_enable，即 preempt_count -= SOFTIRQ_OFFSET，恢复preempt_count 为0，那么接下来在中断返回时就可以被抢占了。

##### 顺便提一嘴spinlock

其实spinlock也是一样的机制，spinlock大家都知道，核之间自旋，核内锁调度（关抢占）。  
其中核内锁调度，即不能在本core上被调度出去，也是通过preempt_count 设置了个不等于0的值来实现的。

### 基于代码，理解softirq

接下来进入正题，首先看一张图，了解下大概的软件脉络  
![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/c70247fefe85b793ee26cd08a4866135.png#pic_center)

##### softirq的初始化

内核初始化阶段，会初始化一些 数据结构 ，如上图右上部分

- softirq_vec  
    一个全局的数组，里面的每一项代表着不同种类的softirq，即对应不同的处理。  
    每一种处理函数都会被赋值在数据组项的action成员变量中，比如对于tasklet类型在初始化时会： softirq_vec[6]->action = tasklet_action
- tasklet_vec(per cpu变量)  
    tasklet_vec也是全局变量（per cpu），专门为tasklet类型的处理而生，tasklet的任务会链接到这个全局变量中。

```c
//start_kernel
//	softirq_init

void __init softirq_init(void)
{
	int cpu;

	for_each_possible_cpu(cpu) {
		per_cpu(tasklet_vec, cpu).tail =
			&per_cpu(tasklet_vec, cpu).head;
		per_cpu(tasklet_hi_vec, cpu).tail =
			&per_cpu(tasklet_hi_vec, cpu).head;
	}
	//softirq_vec[6]->action = tasklet_action
	open_softirq(TASKLET_SOFTIRQ, tasklet_action);
	open_softirq(HI_SOFTIRQ, tasklet_hi_action);
}
```

> 这里顺便多说一嘴，per cpu意思就是每个cpu都有对应的一个变量，其实本质上就是定义一个tasklet_vec变量作为per cpu变量的话，实际上在内存开辟了：  
> **n（cpu core的数量） x tasklet_vec 大小的空间**，  
> 然后以cpu的 id作为索引对其进行访问，比如说cpu 0对应的变量地址是 &tasklet_vec\[0\]， cpu1 对应变量的地址就是 &tasklet_vec\[1\]。即每个cpu都对应一个tasklet_vec变量。这个变量在tasklet_action被用，tasklet_action会执行tasklet_vec里的任务链表（每个链表项其实就是一个函数）。  
> 比如 tasklet_action在被执行的时候恰好在cpu2上，则tasklet_action会依次执行tasklet_vec上任务，这里的tasklet_vec其实是 &tasklet_vec\[2\], tasklet_action执行的是挂在 &tasklet_vec\[2\]上的任务。

##### softirq的使用

上面的初始化阶段，已经为softirq的使用创建好了条件, 对于softirq的使用，出奇的简单。只需要

1. 创建一个tasklet任务

```c
/*
void tasklet_init(struct tasklet_struct *t,
		  void (*func)(unsigned long), unsigned long data)
{
	t->next = NULL;
	t->state = 0;
	atomic_set(&t->count, 0);
	t->func = func;
	t->data = data;
}*/
tasklet_init(&smc_host->tasklet, sunxi_mci_tasklet, (unsigned long) smc_host);
```

其中的 sunxi_mci_tasklet 就是一个函数。

2. 调用**tasklet_schedule**函数将任务提交出去

```c
	tasklet_schedule(&smc_host->tasklet);
```

##### softirq的内部分析

既然softirq是属于中断服务程序处理的第二个阶段，自然最正统的做法是 在ISR快结束的时候调用  
tasklet_schedule，把tasklet任务提交出去，我们以allwinner的mci controller的 driver 为例子看一下（sd卡的 controller driver）

```c
static irqreturn_t sunxi_mci_irq(int irq, void *dev_id)
{
	...
	//读取中断控制器，判断SD卡数据等是否发送完成
	msk_int   = mci_readl(smc_host, REG_MISTA);
	...
	//如果数据发送/接收OK了，则将tasklet任务提交出去
	//smc_host->tasklet = sunxi_mci_tasklet
	//sunxi_mci_tasklet的作用就是将resp结果返回给上层
	tasklet_schedule(&smc_host->tasklet);
}
```

tasklet_schedule调用之后，发生了什么，结合上图我们在分析一下流程。

1. 当前的在cpu 0 上程序A在运行。
2. 此时cpu 0上来了一个中断，执行ISR （程序A被打断，切到ISR执行）
3. ISR（sunxi_mci_irq）中调用tasklet_schedule
4. 因为ISR执行期间还是在cpu0上（因为是硬中断）， tasklet_schedule的执行也是在cpu0上，它会将tasklet（smc_host->tasklet）放入cpu 0的softirq_vec变量中 (结合上图的step0， step1)。

```c
// t = smc_host->tasklet;
void __tasklet_schedule(struct tasklet_struct *t)
{
	unsigned long flags;
	local_irq_save(flags);
	t->next = NULL;
	//将tasklet放到本core的tasklet_vec中
	*__this_cpu_read(tasklet_vec.tail) = t;
	__this_cpu_write(tasklet_vec.tail, &(t->next));
	//设置本core上的__softirq_pending 变量的bit6 为 1.
	raise_softirq_irqoff(TASKLET_SOFTIRQ);
	local_irq_restore(flags);
}
```

5. 当ISR执行后，紧接着执行irq_exit , 标志着ISR的结束，紧接着正是进入第二阶段（do_softirq），也叫做中断下半段
6. 大名鼎鼎的do_softirq被执行  
    注意， do_softirq执行的时候，其实还没有退出中断的处理流程。我们在啰嗦一下，中断产生后，执行 中断服务程序：irq_handler ，irq_handler 执行结束后才算一个中断处理结束，即：irq_handler = ISR + do_softirq。我们结合代码感受一下。

```c
/*
 * Interrupt handling.
 */
        .macro  irq_handler
#ifdef CONFIG_MULTI_IRQ_HANDLER
        ldr     r1, =handle_arch_irq
        mov     r0, sp
        adr     lr, BSYM(9997f)
        ldr     pc, [r1]
#else
        arch_irq_handler_default
#endif

//GIC发生中断，会调到 __irq_svc(中断向量)这里执行
__irq_svc:
        svc_entry
        irq_handler //执行中断函数 (ISR + softirq)

#ifdef CONFIG_PREEMPT
        get_thread_info tsk //得到当前运行程序的thread_info 结构体
		//接下来就是重点，如果 thread_info 的结构体中的 preempt_count 的值为0
		//并且flags的值是 TIF_NEED_RESCHED，则执行svc_preempt
        ldr     r8, [tsk, #TI_PREEMPT]          @ get preempt count
        ldr     r0, [tsk, #TI_FLAGS]            @ get flags
        teq     r8, #0                          @ if preempt count != 0
        movne   r0, #0                          @ force flags to 0
        tst     r0, #_TIF_NEED_RESCHED
        blne    svc_preempt
#endif
/*
//arch/arm/mach-sunxi/sun8i.c
MACHINE_START(SUNXI, "sun8i")
        .handle_irq     = gic_handle_irq,

//arch/arm/kernel/setup.c
setup_arch
	handle_arch_irq = mdesc->handle_irq;

//irq_handler的调用流程
irq_handler
	handle_arch_irq
		gic_handle_irq
			handle_IRQ
				irq_enter //进入 ISR 上下文
				generic_handle_irq //执行ISR
				irq_exit //退出 ISR上下文
					invoke_softirq //执行softirq
*/
```

6. do_softirq函数执行开始就打开了本core上的中断，这时就有可能被新的中断打断，比如来了个tick中断，按照中断流程：tick中断的ISR处理后，又会调用新的do_softirq，不会乱码？  
    其实完全不用担心，为了能更好的解释这个问题，执行do_softirq的时候，我们视为 do_softirq1，  
    do_softirq1打开中断后，又来了一个新的中断打断了目前的中断流（do_softirq1），新的ISR执行完之后调用的do_softirq我们视为 do_softirq2. 我们先分析一下 do_softirq的代码

```c
asmlinkage void do_softirq(void)
{
	__u32 pending;
	unsigned long flags;

	//do_softirq1执行的时候，in_interrupt条件是不成立的，即，不在中断的上下文环境
	//可参考图中的 irq_exit/irq_enter
	//即进入ISR之前, 设置 preempt count 为中断上下文(硬中断)
	//离开 ISR后，复原 preempt count的值，离开中断环境
	if (in_interrupt())//①
		return;

	local_irq_save(flags);

	pending = local_softirq_pending();

	if (pending)
		__do_softirq();

	local_irq_restore(flags);
}

asmlinkage void __do_softirq(void)
{
...
	//设置当前进程A处在SOFTIRQ_OFFSET环境中(软中断上下文)
	//即处在中断上下文的环境中.
	__local_bh_disable((unsigned long)__builtin_return_address(0),SOFTIRQ_OFFSET);
...
	//打开中断。
	//打开中断后，马上本core上来了个tick中断，执行do_softirq2时
	//do_softirq2
	//它会在 do_softirq函数的in_interrupt(①的地方)判断时返回，
	//因为被中断的do_softirq1已经把进程A的状态设置成了软中断的上下文,
	//导致in_interrupt条件成立
	local_irq_enable();
...
}
```

由上面分析可知， 新来了个tick中断，因为是在中断上下文中（软中断do_softirq1正在running），它只执行了ISR就退出了，退出后，回到do_softirq1接着执行。  
其次还有个问题， 新来的tick中断退出后，即irq_handler结束后，会不会发生抢占呢？  
上面我们已经分析过，do_softirq1已经设置了进程A在本core上不可被抢占，即 preempt_count 不为0

```c
__local_bh_disable((unsigned long)__builtin_return_address(0),SOFTIRQ_OFFSET);
```

所以在本core上（cpu0）上的tick中断退出后，不会处理切换线程的流程，直接回退到被中断的 do_softirq1中继续执行。

- 好了，继续分析do_softirq

```c
asmlinkage void __do_softirq(void)
{
	//获取本core上的__softirq_pending 变量（上面可知，此变量的bit6被置1）
	pending = local_softirq_pending();
	__local_bh_disable((unsigned long)__builtin_return_address(0),
				SOFTIRQ_OFFSET);
	local_irq_enable();
	//获取数组
	h = softirq_vec;
	do {
		//循环判断__softirq_pending 的每个bit，如果被置1
		//则执行 softirq_vec[bit]->action
		if (pending & 1) {
			unsigned int vec_nr = h - softirq_vec;
			int prev_count = preempt_count();
			//执行了softirq_vec[6]->action
			//即：tasklet_action函数
			h->action(h);
		}
		h++;
		pending >>= 1;
	} while (pending);
	//上面的数组处理完了，但是如果新来的硬件中断（ISR）, 又贱贱的添加新的tasklet 把__softirq_pending 置1了怎么办？

	local_irq_disable();
	//我们会在拿一次__softirq_pending 变量看看情况
	pending = local_softirq_pending();
	//如果__softirq_pending的某个bit被置1，说明__softirq_pending不为0
	//则调用wakeup_softirqd
	if (pending) {
			//唤醒本core的 softirqd来处理tasklet
			wakeup_softirqd();
	}
	//处理完后，打开SOFTIRQ_OFFSET，即可以开抢占了。
	__local_bh_enable(SOFTIRQ_OFFSET);
}
```

- tasklet_action  
    它的任务很简单，取本core上的 tasklet_vec变量上的tasklet然后执行。

```c
static void tasklet_action(struct softirq_action *a)
{
	struct tasklet_struct *list;

	local_irq_disable();
	list = __this_cpu_read(tasklet_vec.head);
	__this_cpu_write(tasklet_vec.head, NULL);
	__this_cpu_write(tasklet_vec.tail, &__get_cpu_var(tasklet_vec).head);
	local_irq_enable();

	while (list) 
	{
		struct tasklet_struct *t = list;
		list = list->next;

		if (!test_and_clear_bit(TASKLET_STATE_SCHED, &t->state)) 
		{
			t->func(t->data);
		}
	}
}
```

上面关于softirq的流程分析完了，下面解释几个问题。

- **相同的tasklet可以同时运行吗？**  
    是不可以的，tasklet_schedule在调用的时候，会检查当前tasklet的状态是否被置位

```c
static inline void tasklet_schedule(struct tasklet_struct *t)
{
	if (!test_and_set_bit(TASKLET_STATE_SCHED, &t->state))
		__tasklet_schedule(t);
}
```

即 如果t->state == TASKLET_STATE_SCHED 的话，说明tasklet t正在运行，在调用tasklet_schedule不会做任何处理, 因为test_and_set_bit是原子操作，就算A核跟B核同时tasklet_schedule，也会有个成功，有个失败，还有一种情况，比如A核的tasklet t 在running时，B核调用tasklet_schedule（t）会发生什么呢？，我们在看一次tasklet_action函数

```c
	while (list) {
		struct tasklet_struct *t = list;

		list = list->next;

		if (tasklet_trylock(t)) {
			if (!atomic_read(&t->count)) {
			//A核在运行tasklet t（t->func）之前,要清除TASKLET_STATE_SCHED位置，清除后，此时B核可以tasklet_schedule，
			//B核调用 tasklet_schedule 将tasklet t提交到B核所在的tasklet_vec中,
			//之后B核会运行tasklet_action，但是会在在上面的tasklet_trylock处理上失败，
			//因为A核把这个tasklet的状态设置成了TASKLET_STATE_RUN(通过tasklet_trylock)
				if (!test_and_clear_bit(TASKLET_STATE_SCHED, &t->state))
					BUG();
				t->func(t->data);
				tasklet_unlock(t);
				continue;
			}
			tasklet_unlock(t);
		}

		local_irq_disable();
		t->next = NULL;
		//B核tasklet_trylock失败后，会重新将tasklet插到本核的tasklet_vec并且呼叫B核上面的ksoftirqd重新尝试执行

		*__this_cpu_read(tasklet_vec.tail) = t;
		__this_cpu_write(tasklet_vec.tail, &(t->next));
		__raise_softirq_irqoff(TASKLET_SOFTIRQ);
		local_irq_enable();
	}
}
```

所以结论就是： 同一个tasklet不能并行跑

- **临界区的保护问题**  
    tasklet在运行的时候，因为实际上它是__do_softirq在运行期间调用的，也就是说 tasklet在被处理的时候是在处在软中断的上下文，此时tasklet的执行过程中如果存在对临界资源的访问的话，对于本core上来讲是没有竞争关系的（因为tasklet在运行时在本core上不会被切走，即关抢占），但是其他core还是会访问此 临界区，从本文的例子来说，cpu0上运行进程A，因为进程A的preempt_count 不为0，所以cpu0无法在任何中断返回时切到别的程序运行，但是cpu1上可以运行其他进程，比如正在运行程序B，它是可以访问这块临界区，所以在cpu0正在运行的tasklet中，要想保护临界区，要加 spin_lock(核间锁)。另外，比如cpu0上的进程C如果也想访问这块资源怎么办，当然进程C运行时访问临界区可以用spin_lock_irqsave来锁资源 (调用此函数会关硬件中断，而__do_softirq是借助中断运行，所以__do_softirq自然也不会运行，tasklet不会被执行，就不会访问临界区)， 但是关中断有点霸道，毕竟ISR也被禁止了（ISR并不会访问这块临界区），所以可以用spin_lock_bh函数用来关__do_softirq（关softirq），即进程C在访问临界区时，可以被ISR打断，但是要访问临界资源的tasklet不会被执行(__do_softirq 判断in_interrupt时会直接退出)，当进程C退出临界区后，会调用spin_unlock_bh,此函数内部会直接呼叫do_softirq来执行tasklet。