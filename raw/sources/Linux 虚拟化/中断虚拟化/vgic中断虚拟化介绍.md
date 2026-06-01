---
tags:
  - vgic
---

中断虚拟化介绍
<https://www.cnblogs.com/LoyenWang/p/14017052.html>


<span style='color:black'>中断虚拟化，将从中断信号产生到路由到vCPU的角度来展开，包含以下三种情况：</span>
1.  <span style='color:black'>物理设备（物理真实的）产生中断信号，路由到vCPU；</span>
2.  <span style='color:black'>虚拟外设（qemu模拟的）产生中断信号，路由到vCPU；</span>
3.  <span style='color:black'>Guest OS中CPU之间产生中断信号（IPI中断）；</span>
<span style='color:black'></span>
<span style='color:black'></span>
<span style='color:black'></span>
<span style='color:black'>**VGIC介绍**</span>
<span style='color:black'></span>
<span style='color:black'>NON-VHE和VHE模式：</span><span style='color:black'></span>
GICV2中断虚拟化