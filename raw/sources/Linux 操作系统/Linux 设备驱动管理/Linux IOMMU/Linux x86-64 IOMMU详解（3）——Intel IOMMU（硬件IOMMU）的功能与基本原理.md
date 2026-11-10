## 前言

本系列的第一篇文章已经提到，IOMMU分别有软件和硬件实现方式。软件IOMMU就是SWIOTLB，上一篇文章已经进行过详尽的介绍。而对于硬件IOMMU，有多个厂商都设计了自己的IOMMU。由于我的开发机器为Intel x86平台，因此接触的是Intel IOMMU。  
刚开始，我也找过网上很多资料，但是它们要么是基于较旧的Linux内核版本，要么理解不够深入。因此，即使我并没有深入地掌握Intel IOMMU的每一处细节，我还是愿意将自己所了解的知识，以尽可能浅显的形式展现出来。  
本文的三张截图，均来自《Intel VT-d SPEC》，它是Intel IOMMU的官方文档。  
关于Intel IOMMU，我打算分两篇文章来写。本文介绍Intel IOMMU的功能与基本原理，而下一篇文章（不知道咕咕咕到哪天发）将会介绍Intel IOMMU的配置及一些核心代码。并且，随着学习的深入，这两篇文章发布之后可能还会更新。

### 预备知识

如果读者了解如下知识（能深入理解当然更好），你将会更容易理解本文：

1. 了解DMA（直接内存访问）的基本原理。
2. 了解虚拟内存中的页表机制。
3. 使用过虚拟机（例如VMWare Workstation）。
4. 了解SWIOTLB原理（可翻阅本系列[[Linux x86-64 IOMMU详解（2）——SWIOTLB（软件IOMMU）]]）。

### 术语汇总

本文涉及到诸多术语，在此先进行汇总。

1. **Intel IOMMU**：全称为Intel Input/Output Memory Management Unit。根据语境，该术语在本文中，既可表示IOMUU的一种实现方式，也可表示Intel IOMMU硬件。在《Intel VT-d SPEC》中，这两种含义，都有等价表述——前者的等价表述是Intel VT-d（全称为Intel Virtualization Technology for Direct I/O），后者的等价表述是Remapping Hardware。
2. **虚拟机（Guest）**：顾名思义，启用虚拟化（运行虚拟机）时的虚拟机器。
3. **宿主机（Host）**：启用虚拟化时，虚拟机运行所基于的物理机器，称为宿主机。
4. **HPA**：Host Physical Address，在宿主机上的物理地址。不启动虚拟化时，设备看到的就是HPA。
5. **GPA**：Guest Physical Address，在虚拟机上的物理地址。启用虚拟化时，设备看到的是GPA。Intel IOMMU负责将GPA映射为HPA。
6. **Domain**：一个虚拟机所拥有的所有资源（在本文中主要是涉及内存和CPU），称为这个虚拟机的Domain。
7. **重映射（Remapping）**：启用虚拟化时，设备发出的DMA和中断请求，不会直接被物理机器接收，而是会被Intel IOMMU所截获，而后发送到它对应的Guest虚拟机，之后再映射到宿主机的内存或CPU。这个过程称为重映射。

## Intel IOMMU与SWIOTLB的比较

Intel IOMMU与SWIOTLB同为IOMMU的实现方式，二者在目的上存在共性——都能够解决“设备无法直接寻址到内核分配给它的DMA buffer”这一问题。  
二者的不同点在于：

1. 功能。Intel IOMMU最大的功能，并不是用来解决“设备寻址能力有限”这一问题——解决上述问题仅仅是Intel IOMMU顺便附带的一个功能。事实上，Intel IOMMU只是我们从功能角度的称谓，它的全称叫做**Intel Virtualization Technology for Direct I/O**，简称为**Intel VT-d**。其核心功能是**重映射（Remapping）**，指的是在启用虚拟化技术（Virtualization Technology，可以简单理解为开启虚拟机）的机器上，对I/O操作（包括DMA和中断）进行重映射。关于什么是重映射，后文将会详细介绍。
2. 实现方式。SWIOTLB底层是用memcpy()实现的，需要CPU的参与；而Intel IOMMU是通过专门的硬件实现的。

## 什么是重映射

我们先举例说明重映射的应用场景。以最常见的虚拟机软件 VMWare Workstation 为例，经常使用它的用户一定会有这样的经历：你在一台Windows机器上，使用VMWare Workstation，开启了一台Linux虚拟机。为了方便表述，本文称此时的物理机（**Host**，Windows机器）为**宿主机**，而虚拟机（**Guest**，Linux机器）仍称为**虚拟机**。  
然后，你往机箱上插入一个U盘。U盘就是一个设备，它将会进行I/O操作。这时，系统将会弹出对话框，询问你要把U盘连接到哪台机器，你可以选择连接到Windows机器（宿主机）或是Linux机器（虚拟机）。如果你选择连接到虚拟机，那么该U盘之后的I/O操作，就会触发重映射。

为了理解重映射，我们首先考虑没有启用虚拟化（即没有启动虚拟机）的机器。对于这样的机器，设备发起DMA请求，得到的就是机器物理地址；设备的中断请求，也会被CPU直接接收，而后通过中断向量表，找到对应的中断服务程序，处理该中断请求。这个过程是没有重映射的。

现在，假设一台宿主机上开启了虚拟机（甚至可以开启多个虚拟机），并且设备连接到其中某一台虚拟机。这就意味着，设备能访问到的，只有它所连接的虚拟机的所有资源（**一个虚拟机的所有资源，称为一个Domain**），而不会访问到其他虚拟机，更不能直接访问宿主机。因此，我们必须确保：

1. 设备发起DMA请求时，操作系统返回给它的，不能是**宿主机物理地址（Host Physical Address，HPA）**，而只能是**虚拟机物理地址（Guest Physical Address，GPA）**。Intel IOMMU维护从GPA到HPA的映射关系。
2. 设备的DMA和中断请求，只能被它所连接的虚拟机接收，而不能被其他虚拟机接收，也不能被宿主机直接接收。

这个过程对于设备来说应当是透明的。从设备的视角来看，它发起DMA请求，得到一个内存物理地址，并向该地址读写内容；或者，它发起中断请求，最终得到某个中断服务程序的响应。这一切都应该正常发生，与设备所连接的是虚拟机还是宿主机无关——事实上，设备只知道自己连接的是一台“机器”，而根本不知道自己连接的机器是虚拟机还是宿主机。

在这个过程中，Intel IOMMU完成如下功能：

1. **DMA重映射**：Intel IOMMU截获设备的DMA请求，将它重定位到设备所连接的虚拟机。而后，该虚拟机将DMA请求传递给宿主机，宿主机分配DMA Buffer，并返回用于DMA Buffer的HPA。Intel IOMMU将HPA转换为GPA，而后返回GPA给设备。之后，设备向GPA进行DMA操作，Intel IOMMU又将GPA映射为HPA。
2. **中断重映射**：Intel IOMMU截获设备的中断请求，将它重定位到设备所连接的虚拟机。而后，找到该虚拟机所占有的CPU，将中断请求转发给这些CPU，而后这些CPU找到适用于该虚拟机的中断重映射表（Interrupt Remapping Table，IRT，原理与中断向量表相同，只是每个虚拟机都有一份），通过中断号索引到对应的中断服务程序并执行。

## DMA重映射中的I/O页表

对于DMA重映射，我们完全可以仿照 虚拟内存 机制（将内存虚拟地址转换为内存物理地址）来理解。事实上，Intel IOMMU硬件维护了一套用于DMA重映射的I/O页表机制，它与虚拟内存机制中的多级页表原理基本一致，只有一点不同——其中的顶级I/O页表，并不是直接用于寻址（Address Translation），而是用于将DMA请求映射到不同的虚拟机Domain。从次级I/O页表开始，才是真正的寻址过程。  
![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/854caf564d7cb0646841a3ede5c3219f.png#pic_center)  
具体来说，设备发起DMA请求时，除了常规参数以外，还会附带一系列标识符（称为 Request Identifier或Source ID），包括Bus/Device/Function。Intel IOMMU根据这些标识符，在顶级I/O页表中进行索引，找到对应的次级I/O页表。事实上，顶级I/O页表又可分为两部分——Root Table和Context Table，如下图所示。Intel IOMMU先根据Request Identifier的Bus区段，在Root Table中索引；而后，再根据Device和Function区段，在Context Table中索引，从而找到对应的次级页表（下图中的Second-Level Page Table）。  
从次级页表开始，寻址过程就与内存虚拟地址转换为物理地址的过程，完全相同了。  
此外，下图中，有两个Context Table都指向了同一个Domain——Domain A。这表明，不同的设备最终连接到同一个虚拟机，这也是合情合理的——一台机器当然可以连接多个设备，不是吗？  
![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/3ea05d46b475384b46d13dba411c22c4.png#pic_center)  
如果上述解释还不够详细，请看《Intel VT-d SPEC》中的原文截图，其中重要语句已用红色下划线标注：  
![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/6d5f5d04c919770a77b925e7845d7dae.png#pic_center)