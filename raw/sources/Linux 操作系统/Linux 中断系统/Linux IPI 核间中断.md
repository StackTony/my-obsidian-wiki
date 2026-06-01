---
tags:
  - irq
  - 中断
---
**核间中断（IPI）**
核间中断的发起最重要的一个寄存器叫ICR（interrupt command register），软件按照寄存器的使用规则往该寄存器中写信息，就可以发出IPI