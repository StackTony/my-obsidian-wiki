---
tags:
  - virtio
---
## **virtio整体框架**
 <https://cloud.tencent.com/developer/article/1540284>

（*<u>Virtio完成的就是guest和qemu的IO请求数据的交互，后续的qemu模拟设备的IO调度和虚拟中断是在Virtio之后发生的</u>*）

以下所有的类型，**控制面始终经过 QEMU**：设备初始化、配置、热迁移等仍由 QEMU 管理（保持虚拟化功能完整性）

## 综合对比表
| 架构         | 控制面是否过 QEMU | 控制面是否过 KVM | 数据面是否过 QEMU | 数据面是否过内核 KVM 协议栈 |
| ---------- | ----------- | ---------- | ----------- | ---------------- |
| 传统 virtio  | ✅ 过         | ✅ 过        | ✅ 过         | ✅ 过              |
| vhost-net  | ✅ 过         | ✅ 过        | ❌ 不过        | ✅ 过              |
| vhost-user | ✅ 过         | ✅ 过        | ❌ 不过        | ❌ 不过             |
| vDPA       | ✅ 过         | ❌ 不过       | ❌ 不过        | ❌ 不过             |
#### 一、virtio-net 设备
Virtio网络设备是一种虚拟的以太网卡，支持多队列的网络包收发。熟悉virtio的读者应该知道，在virtio的架构中有前后端之分。在virtio 网络中，所谓的前端即是虚拟机中的virtio-net网卡驱动。而后端的实现多种多样，后端的变化往往标志着virtio网络的演化。图1中的后端即是QEMU的实现版本，也是最原始的virtio-net后端（设备）。virtio标准将其对于队列的抽象称为Virtqueue。Vring即是对Virtqueue的具体实现。一个Virtqueue由一个Available Ring和Used Ring组成。前者用于前端向后端发送数据，而后者反之。而在virtio网络中的TX/RX Queue均由一个Virtqueue实现。所有的I/O通信架构都有数据平面与控制平面之分。而对于virtio来说，通过PCI传输协议实现的virtio控制平面正是为了确保Vring能够用于前后端正常通信，并且配置好自定义的设备特性。而数据平面正是使用这些通过共享内存实现的Vring来实现虚拟机与主机之间的通信。举例来说，当virtio-net驱动发送网络数据包时，会将数据放置于Available Ring中之后，会触发一次通知（Notification）。这时QEMU会接管控制，将此网络包传递到TAP设备。接着QEMU将数据放于Used Ring中，并发出一次通知，这次通知会触发虚拟中断的注入。虚拟机收到这个中断后，就会到Used Ring中取得后端已经放置的数据。至此一次发送操作就完成了。接收网络数据包的行为也是类似，只不过这次virtio-net驱动是将空的buffer放置于队列之中，以便后端将收到的数据填充完成而已。


**整体流程**

从代码上看，virtio的代码主要分两个部分：QEMU和内核驱动程序。Virtio设备的模拟就是通过QEMU完成的，QEMU代码在虚拟机启动之前，创建虚拟设备。虚拟机启动后检测到设备，调用内核的virtio设备驱动程序来加载这个virtio设备。

对于KVM虚拟机，都是通过QEMU这个用户空间程序创建的，每个KVM虚拟机都是一个QEMU进程，虚拟机的virtio设备是QEMU进程模拟的，虚拟机的内存也是从QEMU进程的地址空间内分配的。

VRING是由虚拟机virtio设备驱动创建的用于数据传输的共享内存，QEMU进程通过这块共享内存获取前端设备递交的IO请求。

HOST和客户机也正是通过VirtQueue来操作buffer。每个buffer包含一个VRing结构，对buffer的操作实际上是通过VRing来管理的。

两个生产者-消费者模型:
前端驱动可以看做请求的生产者和响应的消费者
后端驱动看做请求的消费者和响应的生产者

如下图所示，虚拟机IO请求的整个流程：

![[774036-20211126153504501-1486553797.png]]

   1) 虚拟机产生的IO请求会被前端的virtio设备接收，并存放在virtio设备散列表scatterlist里；
   2) Virtio设备的virtqueue提供add_buf将散列表中的数据映射至前后端数据共享区域Vring中；
   3) Virtqueue通过kick函数来通知后端qemu进程。Kick通过写pci配置空间的寄存器产生kvm_exit；
   4) Qemu端注册ioport_write/read函数监听PCI配置空间的改变，获取前端的通知消息；
   5) Qemu端维护的virtqueue队列从数据共享区vring中获取数据
   6) Qemu将数据封装成virtioreq;
   7) Qemu进程将请求发送至硬件层。

前后端主要通过PCI配置空间的寄存器完成前后端的通信，而IO请求的数据地址则存在vring中，并通过共享vring这个区域来实现IO请求数据的共享。

从上图中可以看到，Virtio设备的驱动分为前端与后端：前端是虚拟机的设备驱动程序，后端是host上的QEMU用户态程序。为了实现虚拟机中的IO请求从前端设备驱动传递到后端QEMU进程中，Virtio框架提供了两个核心机制：前后端消息通知机制和数据共享机制。

**[^1]消息通知机制**，前端驱动设备产生IO请求后，可以通知后端QEMU进程去获取这些IO请求，递交给硬件。

**[^2]数据共享机制**，前端驱动设备在虚拟机内申请一块内存区域，将这个内存区域共享给后端QEMU进程，前端的IO请求数据就放入这块共享内存区域，QEMU接收到通知消息后，直接从共享内存取数据。由于KVM虚拟机就是一个QEMU进程，虚拟机的内存都是QEMU申请和分配的，属于QEMU进程的线性地址的一部分，因此虚拟机只需将这块内存共享区域的地址传递给QEMU进程，QEMU就能直接从共享区域存取数据。


**整体流程**

前后端主要通过PCI配置空间的寄存器完成前后端的通信，而IO请求的数据地址则存在vring中，并通过共享vring这个区域来实现IO请求数据的共享。
Virtio设备的驱动分为前端与后端：前端是虚拟机的设备驱动程序，后端是host上的QEMU用户态程序。为了实现虚拟机中的IO请求从前端设备驱动传递到后端QEMU进程中，Virtio框架提供了两个核心机制：<u>前后端消息通知机制</u>和<u>数据共享机制</u>。

virtio从前端到后端的virtio IO请求/处理的整体流程：
1、guest通过对已经注册了ioeventfd的一块区域进行写入操作导致guest/host切换，vcpu从guest mode陷出到KVM
2、vcpu线程在KVM模块中通过eventfd_signal来唤醒IO thread的poll，此时vcpu线程陷入返回到guest mode
3、IO thread被唤醒，在内核态调度执行返回用户态
4、从avail vring中取出请求下发
5、aio系统调用
6、通过host 的device driver将数据传到物理设备
7、硬件处理完IO请求之后通过物理中断唤醒IO主线程
8、IO主线程再次从内核被调度返回用户态
9、根据IO处理的结果在used vring中保存记录
10、向注册过irqfd的fd进行写入操作
11、KVM中irqfd的等待队列被唤醒，向目标vcpu添加一个request请求，然后判断vcpu是否在物理cpu上运行，如果是就让vcpu退出guest mode，方便中断注入
12、vcpu陷出到host mode之后，再次调用vcpu_enter_guest回到guest mode时，从request中读出注入中断的请求，写入vmcs的IRQ寄存器，来真正注入中断，vcpu回到guest mode之后会调用guest中注册的中断处理函数进行处理

![[Pasted image 20260425085956.png]]
图一   virtio设备和驱动

| 架构        | 控制面是否过 QEMU                      | 控制面是否过 KVM                | 数据面是否过 QEMU | 数据面是否过内核 KVM 协议栈 |
| --------- | -------------------------------- | ------------------------- | ----------- | ---------------- |
| 传统 virtio | ✅ 过，负责设备枚举、特性协商、队列配置、状态变更等所有控制操作 | ✅ 过，负责前端陷入、中断注入、eventfd传递 | ✅ 过         | ✅ 过              |


#### 二、vhost-net 设备（内核态架构）

处于内核态的后端

QEMU实现的virtio网络后端带来的网络性能并不如意，究其原因是因为频繁的上下文切换，低效的数据拷贝、线程间同步等。于是，内核实现了一个新的virtio网络后端驱动，名为vhost-net。

与之而来的是一套新的vhost协议。vhost协议可以将允许VMM将virtio的数据面offload到另一个组件上，而这个组件正是vhost-net。在这套实现中，QEMU和vhost-net内核驱动使用ioctl来交换vhost消息，并且用eventfd来实现前后端的通知。当vhost-net内核驱动加载后，它会暴露一个字符设备在/dev/vhost-net。而QEMU会打开并初始化这个字符设备，并调用ioctl来与vhost-net进行控制面通信，其内容包含virtio的特性协商，将虚拟机内存映射传递给vhost-net等。对比最原始的virtio网络实现，控制平面在原有的基础上转变为vhost协议定义的ioctl操作（对于前端而言仍是通过PCI传输层协议暴露的接口），基于共享内存实现的Vring转变为virtio-net与vhost-net共享，数据平面的另一方转变为vhost-net，并且前后端通知方式也转为基于eventfd的实现。

如图2所示，可以注意到，vhost-net仍然通过读写TAP设备来与外界进行数据包交换。而读到这里的读者不禁要问，那虚拟机是如何与本机上的其他虚拟机与外界的主机通信的呢？答案就是通过类似Open vSwitch (OVS)之类的软件交换机实现的。OVS相关的介绍这里就不再赘述。

![[Pasted image 20260425091148.png]]
图 2 vhost-net为后端的virtio网络架构

| 架构        | 控制面是否过 QEMU                                     | 控制面是否过 KVM                       | 数据面是否过 QEMU | 数据面是否过内核 KVM 协议栈 |
| --------- | ----------------------------------------------- | -------------------------------- | ----------- | ---------------- |
| vhost-net | ✅ 过，通过ioctl与/dev/vhost-net交互，完成特性协商、内存映射、队列初始化等 | ✅ 过，负责前端陷入、中断注入、eventfd/irqfd 绑定 | ❌ 不过        | ✅ 过              |

#### 三、vhost-user 设备（DPDK轮询架构）

使用DPDK加速的后端

DPDK社区一直致力于加速数据中心的网络数据平面，而virtio网络作为当今云环境下数据平面必不可少的一环，自然是DPDK优化的方向。而vhost-user就是结合DPDK的各方面优化技术得到的用户态virtio网络后端。这些优化技术包括：处理器亲和性，巨页的使用，轮询模式驱动等。除了vhost-user，DPDK还有自己的virtio PMD作为高性能的前端，本文将以vhost-user作为重点介绍。

基于vhost协议，DPDK设计了一套新的用户态协议，名为vhost-user协议，这套协议允许qemu将virtio设备的网络包处理offload到任何DPDK应用中（例如OVS-DPDK）。vhost-user协议和vhost协议最大的区别其实就是通信信道的区别。Vhost协议通过对vhost-net字符设备进行ioctl实现，而vhost-user协议则通过unix socket进行实现。通过这个unix socket，vhost-user协议允许QEMU通过以下重要的操作来配置数据平面的offload：

1. 特性协商：virtio的特性与vhost-user新定义的特性都可以通过类似的方式协商，而所谓协商的具体实现就是QEMU接收vhost-user的特性，与自己支持的特性取交集。
2. 内存区域配置：QEMU配置好内存映射区域，vhost-user使用mmap接口来映射它们。
3. Vring配置：QEMU将Virtqueue的个数与地址发送给vhost-user，以便vhost-user访问。
4. 通知配置：vhost-user仍然使用eventfd来实现前后端通知。

基于DPDK的Open vSwitch(OVS-DPDK)一直以来就对vhost-user提供了支持，读者可以通过在OVS-DPDK上创建vhost-user端口来使用这种高效的用户态后端。

![[Pasted image 20260425091340.png]]
图 3 DPDK vhost-user架构

| 架构         | 控制面是否过 QEMU                                                                | 控制面是否过 KVM                 | 数据面是否过 QEMU | 数据面是否过内核 KVM 协议栈 |
| ---------- | -------------------------------------------------------------------------- | -------------------------- | ----------- | ---------------- |
| vhost-user | ✅ 过，通过 vhost-user 协议（Unix Socket）与用户态后端（如 OVS-DPDK、SPDK）通信，传递控制指令与内存映射QEMU | ✅ 过，负责前端陷入、中断注入、eventfd 传递 | ❌ 不过        | ❌ 不过             |

如下图所示，
1）右侧的VM内部使用dpdk方式轮询取包，内部的进程100%cpu占用。
2）左侧的VM内部不使用dpdk方式，采用virtio_net，走KVM侧注入中断通知虚拟机内部去取包，经过virtio_pci_set_guest_notifiers函数。

![[resources/Diagram 1.svg]]


#### 四、vDPA 直通

使用硬件加速数据面

Virtio作为一种半虚拟化的解决方案，其性能一直不如设备的pass-through，即将物理设备（通常是网卡的VF）直接分配给虚拟机，其优点在于数据平面是在虚拟机与硬件之间直通的，几乎不需要主机的干预。而virtio的发展，虽然带来了性能的提升，可终究无法达到pass-through的I/O性能，始终需要主机（主要是软件交换机）的干预。

vDPA(vhost Data Path Acceleration)即是让virtio数据平面不需主机干预的解决方案。从图中可以看到virtio的控制平面仍需要vDPA driver进行传递，也就是说QEMU，或者虚拟机仍然使用原先的控制平面协议作为接口，而这些控制信息被传递到硬件中，硬件会通过这些信息配置好数据平面。而数据平面上，经过配置后的数据平面可以在虚拟机和网卡之间直通。鉴于现在后端的数据处理其实完全在硬件中，原先的前后端通知方式也可以几乎完全规避主机的干预，以中断为例，原先中断必须由主机处理，主机通过软件交换机得知中断的目的地之后，将虚拟中断注入到虚拟机中，而在vDPA中，网卡可以直接将中断发送到虚拟机中。总体来看，vDPA的数据平面与SR-IOV设备直通的数据平面非常接近，并且在性能数据上也能达到后者的水准。更重要的是vDPA框架保有virtio这套标准的接口，使云服务提供商在不改变virtio接口的前提下，得到更高的性能。

需要注意的是，vDPA框架中利用到的硬件必须至少支持virtio ring的标准，否则可想而知，硬件是无法与前端进行正确通信的。另外，原先软件交换机提供的交换功能，也转而在硬件中实现。

![[Pasted image 20260425091444.png]]

![[resources/Diagram.svg]]
图 4 vDPA架构

| 架构   | 控制面是否过 QEMU     | 控制面是否过 KVM | 数据面是否过 QEMU | 数据面是否过内核 KVM 协议栈 |
| ---- | --------------- | ---------- | ----------- | ---------------- |
| vDPA | ✅ 过，负责特性协商、队列配置 | ❌ 不过       | ❌ 不过        | ❌ 不过             |


## 相关链接

- [[1）设备初始化流程]]
- [[2）消息通知机制（ioeventfd和irqfd）]]
- [[3）数据共享机制（vring环）]]
- [[设备直通 iommu+sriov、vfio]]
- [[virtio-blk和virtio-scsi的理解]]

[^1]: [[2）消息通知机制（ioeventfd和irqfd）]]
[^2]: [[3）数据共享机制（vring环）]]
