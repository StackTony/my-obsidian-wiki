---
tags:
  - trace
  - kprobe
  - DFX
---

kprobe使用指南：[https://blog.csdn.net/luckyapple1028/article/details/52972315](https://blog.csdn.net/luckyapple1028/article/details/52972315)


**开启方法** 查看可用的函数列表（可用于kprobe）
cat /sys/kernel/debug/tracing/available_filter_functions
===不支持的可能会echo失败===

echo "test \`date\` " > /dev/kmsg 
该命令可以将时间戳换成tracing里一样的

1）添加kprobe事件追踪要关注的函数
echo 'p:my_probe queue_work' > /sys/kernel/debug/tracing/kprobe_events
2）开启kprobe
echo 1 > /sys/kernel/debug/tracing/events/kprobes/enable
3）开启tracing
echo 1 > /sys/kernel/debug/tracing/tracing_on
**要看某个CPU核的具体stacktrace调用堆栈**
echo 1 > options/stacktrace


**关闭方法**
echo 0 > /sys/kernel/debug/tracing/events/kprobes/enable
echo 0 > /sys/kernel/debug/tracing/tracing_on
echo '' > /sys/kernel/debug/tracing/kprobe_events
