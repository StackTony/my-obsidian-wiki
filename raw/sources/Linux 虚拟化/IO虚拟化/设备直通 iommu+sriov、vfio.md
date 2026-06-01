---
tags:
  - virtio
  - vfio
  - 直通
  - iommu
  - sriov
---

IOMMU和VFIO
<https://www.cnblogs.com/yi-mu-xi/p/12370626.html>

<https://blog.csdn.net/halcyonbaby/article/details/37776211?spm=1001.2101.3001.6650.1&utm_medium=distribute.pc_relevant.none-task-blog-2%7Edefault%7ECTRLIST%7ERate-1-37776211-blog-109117488.235%5Ev38%5Epc_relevant_anti_t3_base&depth_1-utm_source=distribute.pc_relevant.none-task-blog-2%7Edefault%7ECTRLIST%7ERate-1-37776211-blog-109117488.235%5Ev38%5Epc_relevant_anti_t3_base&utm_relevant_index=2>

PF：即使用vfio方式，将主机的物理设备直接给vm使用，配置后主机侧将看不到对应物理设备的信息，vm侧可以看到
VF：即使用SR-IOV方式，先将主机侧的物理设备虚拟出多个设备，然后配置给vm使用

<span style='background:white'>Qemu 虚拟机 pci 设备透传 —— 网卡</span>
<https://winddoing.github.io/post/b3396e6f.html>
