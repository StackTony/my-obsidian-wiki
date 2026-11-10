原文： https://blog.csdn.net/qq_34719392/article/details/114834467

## 全系列文章链接

[Linux x86-64 IOMMU详解（一）——IOMMU简介](https://blog.csdn.net/qq_34719392/article/details/114834467)  
[Linux x86-64 IOMMU详解（二）——SWIOTLB（软件IOMMU）](https://blog.csdn.net/qq_34719392/article/details/114873284)  
[Linux x86-64 IOMMU详解（三）——Intel IOMMU（硬件IOMMU）的功能与基本原理](https://blog.csdn.net/qq_34719392/article/details/115374606)  
[Linux x86-64 IOMMU详解（四）——启用Intel IOMMU的配置](https://blog.csdn.net/qq_34719392/article/details/116153505)  
[Linux x86-64 IOMMU详解（五）——Intel IOMMU初始化流程](https://blog.csdn.net/qq_34719392/article/details/117563480)  
[Linux x86-64 IOMMU详解（六）——Intel IOMMU参与下的DMA Coherent Mapping流程](https://blog.csdn.net/qq_34719392/article/details/117699839)

## 前言
本系列包含多篇文章，分别介绍IOMMU的基本概念、软件IOMMU（SWIOTLB）、硬件IOMMU（Intel IOMMU），以及IOMMU的初始化流程。  

## 适用环境

内核版本：Linux 5.5.4（Linux 5.x版本应该都适用）  
硬件：Intel x86-64处理器；对于硬件IOMMU的章节，要求 BIOS 能够支持Intel IOMMU

## IOMMU简介

关于IOMMU，网上的资料分析得比较详细，此处仅作简要介绍，以作为后续文章的引子。  
IOMMU (Input and Output Memory Management Unit)，其名称显然是由MMU衍生而来。之所以二者名称如此相似，是因为它们的功能非常相似。以下是一张解释IOMMU功能的经典图片：  
![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/4f37c84fdd8f91927ef25428d309c11e.jpeg#pic_center)  
从上图中不难看出，**IOMMU是DMA（直接内存访问，即设备与内存直接通信，而无需经过CPU）过程中的一个环节**。本系列的文章更多时候会把IOMMU看作一种机制，从这个角度，我们也可以说：**IOMMU是DMA的一种实现方式。**  

愿意阅读本文的读者，相信对于MMU并不陌生：MMU是将CPU虚拟地址转换为内存物理地址的硬件单元。类似地，IOMMU是将设备地址（又称总线地址）转换为内存物理地址的单元。我们完全可以参照虚拟内存机制，来理解IOMMU的作用：  
① IOMMU使得设备无法直接访问物理地址，大大增加了设备进行DMA攻击的难度。  
② 部分设备的引脚数较少，导致其位数较低，无法寻址到整个物理内存空间。
以目前主流的32位设备为例，其在物理内存中直接寻址的范围是\[0, 4GB)。但是，现代 操作系统 的内存往往大于4GB。如果设备申请DMA时，内核为设备分配的DMA buffer的地址高于4GB（以下简称为“high buffer”），则设备将无法寻址到它。  

有了IOMMU以后，IOMMU就可以在\[0, 4GB)范围内分配一段与高地址buffer长度相同的内存，让设备能够直接寻址（以下称为“low buffer”）。设备向low buffer写入后，IOMMU就会将low buffer中的内容，复制到high buffer，而后通知CPU从high buffer读取内容。反之亦然——CPU向high buffer写入后，IOMMU就会将high buffer中的内容，复制到low buffer，而后通知设备从low buffer读取内容。这样，CPU和设备都能读取到对方写入的内容。这样在high buffer和low buffer之间复制内容的操作，在IOMMU机制中被称为“sync”或“bounce”。  

![IOMMU拓展了设备的寻址空间](https://i-blog.csdnimg.cn/blog_migrate/0de70cc6fc1cf99f085106ce207972c1.png#pic_center)