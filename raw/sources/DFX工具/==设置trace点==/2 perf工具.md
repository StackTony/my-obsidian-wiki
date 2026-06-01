## 2.1 简介

perf (performance 的缩写)，是 Linux 系统原生提供的性能分析工具，会返回 CPU 正在执行的函数名以及调用栈(stack)。

它基于事件采样原理，以性能事件为基础，支持针对处理器相关性能指标与操作系统相关性能指标的性能剖析，常用于性能瓶颈的查找与热点代码的定位。

CPU周期(cpu-cycles)是默认的性能事件，所谓的CPU周期是指CPU所能识别的最小时间单元，通常为亿分之几秒，是CPU执行最简单的指令时所需要的时间，例如读取寄存器中的内容，也叫做clock tick。

perf的具体原理是这样的：每隔一个固定的时间，就在CPU上（每个核上都有）产生一个中断，在中断上看看，当前是哪个pid，哪个函数，然后给对应的pid和函数加一个统计值，这样，我们就知道CPU有百分几的时间在某个pid，或者某个函数上了。
这是一种采样的模式，我们预期，运行时间越多的函数，被时钟中断击中的机会越大，从而推测，那个函数（或者pid等）的CPU占用率就越高。

## 2.2 常用子工具

**+ perf-list**

Perf-list用来查看perf所支持的性能事件，主要分为三类：

1\. Hardware Event 是由 PMU 硬件产生的事件，比如 cache 命中，当您需要了解程序对硬件特性的使用情况时，便需要对这些事件进行采样。

2\. Software Event 是内核软件产生的事件，比如进程切换，tick 数等。

3\. Tracepoint event 是内核中的静态 tracepoint 所触发的事件，这些 tracepoint 用来判断程序运行期间内核的行为细节，比如 slab 分配器的分配次数等。

hw/cache/pmu都是硬件相关的；tracepoint基于内核的ftrace；sw实际上是内核计数器。

\> 使用方法：perf list \[hw \| sw \| cache \| tracepoint \| event_glob\]

**+ perf-stat**

面对一个性能问题的时候，最好采用自顶向下的策略。先整体看看该程序运行时各种统计事件的大概，再针对某些方向深入细节。

整体监测代码性能就需要使用perf stat这个工具，该工具主要是从全局上监控，可以看到程序导致性能瓶颈主要是什么原因。perf stat通过概括精简的方式提供被调试程序运行的整体情况和汇总数据。

在默认情况下，perf stat会统计cycles、instructions、cache-misses、context-switches等对系统或软件性能影响最大的几个硬件和软件事件。通过这些统计情况，基本上就能了解软件的运行效率是受CPU影响较大还是IO影响较大，是受运算指令数影响较大还是内存访问影响较大。通过指令数、缓存访问数等统计还能大致判断软件性能是否符合对应的功能设计，是否有代码级优化的可能。

\> 使用方法：
\>
\> perf stat \[-e \<EVENT\> \| --event=EVENT\] \[-a\] \<command\>
\>
\> perf stat \[-e \<EVENT\> \| --event=EVENT\] \[-a\] - \<command\> \[\<options\>\]

即perf stat + 程序，程序运行完之后，然后使用\*\*ctrl+c\*\*来终止程序（若程序自动终止则不用），之后，perf便会打印出监控事件结果，类似如下所示：

1\. 102.97 task-clock是指程序运行期间占用了xx的任务时钟周期，该值高，说明程序的多数时间花费在CPU计算上而非IO操作。

2\. 6 context-switches是指程序运行期间发生了xx次上下文切换，记录了程序运行过程中发生了多少次进程切换，频繁的进程切换是应该避免的。（有进程进程间频繁切换，或者内核态与用户态频繁切换）

3\. 0 cpu-migrations 是指程序运行期间发生了xx次CPU迁移，即用户程序原本在一个CPU上运行，后来迁移到另一个CPU

4\. 617 page-faults 是指程序发生了xx次页错误

5\. 其他可以监控的譬如分支预测、cache命中等

**+ perf-top**

perf top可以用于观察系统和软件内性能开销最大的函数列表。通过观察不同事件的函数列表可以分析出不同函数的性能开销情况和特点，判断其优化方向。

例如如果某个函数在perf top -e instructions中排名靠后，却在perf top -e cache-misses和perf top -e cycles中排名靠前，说明函数中存在大量cache-miss造成CPU资源占用较多，就可以考虑优化该函数中的内存访问次数和策略，来减少内存访问和cache-miss次数，从而降低CPU开销。

\> 使用方法：perf top \[-e \<EVENT\> \| --event=EVENT\] \[\<options\>\]
\>
\> \> 常用参数：
\> \>
\> \> -e \<event\>：指明要分析的性能事件。
\> \>
\> \> -p \<pid\>：Profile events on existing Process ID (comma sperated list). 仅分析目标进程及其创建的线程。
\> \>
\> \> -k \<path\>：Path to vmlinux. Required for annotation functionality. 带符号表的内核映像所在的路径。
\> \>
\> \> -K：不显示属于内核或模块的符号。
\> \>
\> \> -U：不显示属于用户态程序的符号。
\> \>
\> \> -d \<n\>：界面的刷新周期，默认为2s，因为perf top默认每2s从mmap的内存区域读取一次性能数据。
\> \>
\> \> -g：得到函数的调用关系图。

\+ perf-record/perf-report

收集采样信息，并将其记录在数据文件中。随后可以通过其它工具(perf-report)对数据文件进行分析，结果类似于perf-top。

\> 使用方法：首先perf record记录并生成data文件，然后通过perf report显示。


## 相关链接

- [[perf工具抓取CPU使用率情况]]
- [[perf工具分析虚拟机的性能事件]]
- [[perf工具抓取单核CPU的进程调度轨迹]]
- [[perf工具分析slab内存占用]]