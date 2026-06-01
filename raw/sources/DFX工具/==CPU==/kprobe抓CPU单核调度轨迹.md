---
tags:
  - kprobe
---

**kprobe抓CPU单核调度轨迹**
打开调度能力，命令1：
echo 1 \> /sys/kernel/debug/tracing/events/sched/sched_wakeup/enable && echo 1 \> /sys/kernel/debug/tracing/events/sched/sched_switch/enable

过滤具体的CPU核，命令2：
echo 'cpu0 || cpu1 || cpu2' > /sys/kernel/debug/tracing/events/sched/sched_wakeup/filter

echo 'cpu0 || cpu1 || cpu2' > /sys/kernel/debug/tracing/events/sched/sched_switch/filter

开启单核的具体调用堆栈，命令3：
echo 1 \> options/stacktrace