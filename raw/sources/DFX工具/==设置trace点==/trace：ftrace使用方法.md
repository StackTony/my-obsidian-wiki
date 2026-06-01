---
tags:
  - trace
  - ftrace
  - DFX
---

**相关问题：**
出现现象时：
“-bash: echo: write error: Device or resource busy”
需要关闭服务：
systemctl stop rasdaemon.service


**ftrace使用方式：**
例如：
cd /sys/kernel/debug/tracing/ 
echo > trace //清空缓存
echo 0 > tracing_on
echo function_graph > current_tracer
echo cma_alloc > set_graph_function
(echo cma_alloc > set_ftrace_filter  与上一条函数一致，过滤其余函数的打印，因为每打印一条都会耗时)
echo 1 > tracing_on


**开启方法**
cd /sys/kernel/debug/tracing/
echo "stop_machine_cpuslocked" > set_ftrace_filter
echo function > current_tracer
echo 1 > tracing_on
**查看总体或每个CPU的trace：**
cat trace
cat per_cpu/cpu0/trace

**关闭方法**
echo 0 > tracing_on
echo > set_ftrace_filter   // 清空之前设置的过滤器（非常重要，否则会影响后续追踪）
echo nop > current_tracer    // 将当前追踪器设置为 nop (即无操作)，这是最安全也是默认的状态




**脚本实现：**（使用方法 xxx.sh + 要抓的函数名）
```
func=$1
echo "trace function: $func"
tracepath="/sys/kernel/debug/tracing"
state=`cat /sys/kernel/debug/tracing/events/kprobes/enable`
if [[ $state -eq 1 ]];then
    echo "disable kprobes"
    echo 0 > /sys/kernel/debug/tracing/events/kprobes/enable
else
    echo "kprobes not effect"
fi

echo "p:$func $func" >> /sys/kernel/debug/tracing/kprobe_events

if [[ $? -ne 0 ]];then
    echo "trace failed"
exit 1

fi
echo $func > /sys/kernel/debug/tracing/set_event
echo stacktrace > /sys/kernel/debug/tracing/trace_options
echo 1 > /sys/kernel/debug/tracing/events/kprobes/enable & echo "trace already enable"
echo > /sys/kernel/debug/tracing/trace
```
