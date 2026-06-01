### Linux内核的三种主要调度策略：
https://zhuanlan.zhihu.com/p/580170448
1，SCHED_OTHER 分时调度策略，
2，SCHED_FIFO实时调度策略，先到先服务
3，SCHED_RR实时调度策略，时间片轮转
实时进程将得到优先调用，实时进程根据实时优先级决定调度权值。分时进程则通过nice和counter值决定权值，nice越小，counter越大，被调度的概率越大，也就是曾经使用了cpu最少的进程将会得到优先调度。