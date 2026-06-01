---
tags:
  - vgic
---

LAPIC（Local APIC，本地高级可编程中断控制器）
IOAPIC（I/O高级可编程中断控制器）
<https://zhuanlan.zhihu.com/p/313725721>



KVM中断注入机制
<https://blog.csdn.net/huang987246510/article/details/103397763>


**核间中断（IPI）**
核间中断的发起最重要的一个寄存器叫ICR（interrupt command register），软件按照寄存器的使用规则往该寄存器中写信息，就可以发出IPI
