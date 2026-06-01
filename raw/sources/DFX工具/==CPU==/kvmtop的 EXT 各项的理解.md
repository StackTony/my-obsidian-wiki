---
tags:
  - kvmtop
  - EXT
---

**kvmtop的各个EXT项代表 KVM虚拟机退出（VM-Exit）原因的统计指标**

1） EXThvc
虚拟机主动调用Hypervisor（HVC指令）

2） EXTwfe / EXTwfi
等待事件/中断（ARM架构的WFE/WFI指令），此外关注halt-polling特性

3） EXTmmioU / EXTmmioK
内存映射I/O访问退出，IOMMU相关操作

4） EXTfp
浮点/向量指令导致的退出

==5） EXTirq==
虚拟机内的核间中断高
手段：虚拟机内部能登录进去可以看下irqtop或者cat /proc/interrupts对比下问题时间和非问题时间的中断量的差异

\# 1. 在虚拟机内查看中断统计
irqtop \# 或 cat /proc/interrupts

\# 2. 查看具体中断类型
\# 关注：
\# - IPI（核间中断）：如"Rescheduling interrupts"
\# - 设备中断：如virtio设备

\# 3. 对比分析
\# 正常时期和问题时期的差异：
\# 重点检查：
\# - IPI_RESCHEDULE（调度中断）
\# - IPI_CALL_FUNC（函数调用中断）
\# - virtio相关设备中断

==6） EXTsys64==
64位系统调用（ARM的SVC指令），比如 应用发起系统调用（如read/write）

7） EXTmabt
内存访问异常，一般是缺页访问

以上均可以通过开启trace抓取确认，如下：\[076\]代表76号CPU上的