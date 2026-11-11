原文： https://doc.embedfire.com/linux/rk356x/driver/zh/latest/linux_driver/subsystem_dma_iommu.html

在Linux系统中，CPU是数据运算核心，而外设是数据交互核心，若所有数据搬运都由CPU参与，会产生大量内存拷贝、总线等待开销，严重占用CPU算力，降低系统吞吐与实时性。

DMA（Direct Memory Access，直接内存访问）子系统的核心作用是解放CPU，允许外设直接与内存进行数据传输，无需CPU逐字节拷贝，仅需CPU发起传输指令、等待传输完成中断即可，大幅提升大数据传输场景的效率。

而随着64位平台、大内存、多设备并发场景普及，普通DMA存在地址不隔离、32位寻址受限、物理内存碎片化访问不安全等问题。 IOMMU（Input/Output Memory Management Unit，输入输出内存管理单元）应运而生，为DMA设备提供硬件地址翻译、内存隔离、权限管控、大内存寻址能力，是现代ARM64、X86平台必不可少的I/O虚拟化与内存管理单元。

## 1.1. DMA核心概念[¶](#dma "永久链接至标题")

### 1.1.1. DMA基础定义[¶](#id1 "永久链接至标题")

DMA是Linux系统中独立于CPU的专用硬件数据搬运控制器，集成于SoC内部或外接总线控制器。其核心作用是卸载CPU的数据拷贝工作，实现内存与外设、内存与内存之间的全自动数据传输，全程无需CPU逐字节干预数据读写，仅需CPU在传输前配置参数、传输后处理中断即可。

### 1.1.2. DMA传输类型[¶](#id2 "永久链接至标题")

Linux内核DMA子系统支持三类标准传输方式，适配不同应用场景：

- 外设到内存（DEV_TO_MEM）：摄像头、麦克风、SD卡等外设采集数据，通过DMA自动写入系统内存；
    
- 内存到外设（MEM_TO_DEV）：系统内存中的图像、音频、数据，通过DMA自动推送至显示屏、喇叭、网络网口；
    
- 内存到内存（MEM_TO_MEM）：无需CPU参与，DMA直接完成两块内存区域的数据拷贝，适用于大数据内存迁移。
    

### 1.1.3. DMA内存工作类型[¶](#id3 "永久链接至标题")

Linux内核DMA子系统根据内存映射方式、缓存一致性、内存形态、传输机制，将DMA分为三大核心类型：一致性DMA（Coherent DMA）、流式DMA（Streaming DMA）、散射-聚集DMA（Scatter-Gather DMA）。

#### 1.1.3.1. 一致性DMA[¶](#id4 "永久链接至标题")

一致性DMA内存是内核为DMA设备专属分配的硬件自动缓存一致的物理连续内存。该内存由硬件保证CPU Cache与设备内存数据实时同步，软件无需手动刷新、失效缓存，CPU与DMA设备可随时读写数据且数据完全一致。

核心特性：

- 物理内存连续、IOVA虚拟地址连续，完全适配DMA硬件寻址要求；
    
- 硬件自动维护Cache一致性，无缓存脏数据问题；
    
- 分配阶段固定映射，生命周期内地址不变；
    
- 内存开销大，内核会预留对齐、冗余内存，内存利用率低。
    

适用场景：

仅适用于小数据、频繁读写、控制交互类场景：设备状态寄存器缓冲区、指令交互缓冲区、中断状态缓存、小型协议头数据，不适合大数据批量传输。

优缺点：

- 优点：开发简单、无需缓存操作、数据稳定性高、无同步异常；
    
- 缺点：内存浪费严重、不支持超大内存分配、系统长期运行易内存碎片化。
    

#### 1.1.3.2. 流式DMA[¶](#id5 "永久链接至标题")

流式DMA是基于系统普通动态内存的临时映射DMA传输机制，无固定内存预留，可直接复用内核栈内存、kmalloc内存、用户态内存，由开发者软件手动管理缓存一致性，是大数据流式传输的首选方案。

核心特性：

- 支持动态映射、临时使用、用完即释，内存利用率极高；
    
- 无硬件自动缓存同步，必须手动根据传输方向操作缓存；
    
- 单次映射对应单次传输，不支持长期持有DMA地址；
    
- 内存可以是物理连续普通内存，适配常规DMA通道。
    

适用场景：

适用于大数据、单次批量、流式收发场景：网络数据包收发、视频帧传输、音频数据流、SD卡高速读写、USB批量传输。

优缺点：

- 优点：内存利用率高、无冗余开销、支持超大批量数据传输、性能最优；
    
- 缺点：开发复杂度高，缓存同步错误会导致数据错乱、传输失败，需严格匹配数据传输方向。
    

#### 1.1.3.3. 散射-聚集DMA[¶](#id6 "永久链接至标题")

散射聚集DMA是Linux高级DMA传输机制，专门解决物理内存碎片化问题。无需连续物理内存，可将多块离散的物理内存页，通过内核SG链表整理后，一次性提交给DMA控制器完成连续传输，是高性能大数据传输的核心方案。

核心特性：

- 支持物理不连续、虚拟连续内存传输，规避内存碎片化问题；
    
- 一次配置、多块内存批量传输，减少DMA配置次数，降低CPU开销；
    
- 需要硬件DMA控制器支持SG模式，普通简易DMA控制器不兼容；
    
- 搭配IOMMU可实现极致的内存利用率与传输稳定性。
    

适用场景：

适用于超大块数据、多段缓存拼接、内存高度碎片化场景：4K视频编解码、千兆/万兆网络数据包、大型文件读写、GPU图像渲染数据传输。

优缺点：

- 优点：无需连续大块物理内存、内存利用率100%、传输效率最高、适配系统长期运行碎片化场景；
    
- 缺点：依赖硬件SG能力、驱动开发复杂度最高、需要维护SG链表结构。
    

### 1.1.4. DMA工作流程[¶](#id7 "永久链接至标题")

Linux DMA的工作逻辑可概括为：CPU配置、硬件搬运、中断收尾、资源释放4个步骤。

1. 初始化配置
    

该阶段由CPU执行，仅执行一次。驱动预先完成基础配置：配置设备DMA寻址掩码、分配对应类型的DMA内存、申请空闲DMA通道、配置传输方向与传输长度，初始化DMA硬件寄存器参数。

2. 硬件自动传输
    

该阶段由无CPU参与。开启DMA通道后，DMA控制器自动抢占总线，根据预设参数独立完成内存与外设之间的数据批量搬运，全程无需CPU干预，自主完成数据传输。

3. 中断收尾处理
    

该阶段由CPU轻量介入。数据传输完成或出现异常时，DMA触发硬件中断，CPU响应中断，完成数据校验、业务处理、清空中断标志、复位通道等收尾操作，等待下一次传输。

4. 资源释放
    

业务结束或驱动卸载时，关闭DMA通道、释放DMA内存、归还硬件通道资源、注销中断，避免内存泄漏和硬件资源占用。

## 1.2. IOMMU核心概念[¶](#iommu "永久链接至标题")

### 1.2.1. IOMMU基础定义[¶](#id8 "永久链接至标题")

IOMMU是专门为DMA设备设计的硬件内存管理单元，对标CPU侧的MMU（内存管理单元）。CPU的MMU负责CPU虚拟地址转物理地址，服务于进程内存管理； 而IOMMU负责设备IO虚拟地址（IOVA）转系统物理地址（PA），专门服务于所有DMA外设的内存访问。

现在的64位嵌入式设备、服务器全部标配IOMMU，主要用来解决普通DMA的各种短板，提升系统稳定性、安全性，同时支持虚拟机设备直通功能。

### 1.2.2. 传统裸DMA的致命缺陷[¶](#id9 "永久链接至标题")

没有IOMMU的系统，DMA设备直接裸奔访问物理内存，漏洞和缺陷非常明显：

- 大内存用不了：很多老旧DMA设备最多只能访问4GB内存，现在设备8G/16G大内存的高位空间完全无法使用；
    
- 碎片内存用不了：普通DMA必须用整块连续内存，系统运行久了内存碎片化，没有大块内存就无法传输大数据；
    
- 毫无安全性：所有设备共用同一内存空间，一个设备出问题、或者恶意程序可以随意篡改系统内核和其他设备的内存，直接导致系统崩溃；
    
- 无权限管控：所有设备默认拥有全部内存读写权限，没有任何限制，安全隐患极大
    

### 1.2.3. IOMMU核心功能[¶](#id10 "永久链接至标题")

- 地址翻译：给DMA设备用虚拟地址，IOMMU自动翻译成真实物理地址。让只能访问4GB的老旧设备，也能使用全部64位大内存，同时把零散内存拼接成整块可用内存；
    
- 设备隔离：给每个设备单独划分独立内存空间，就像给每个设备单独分配“独立房间”，互不打扰，一个设备故障不会影响其他设备和系统；
    
- 权限管控：可以单独设置某块内存只能读、不能写，禁止外设篡改系统核心内存数据，从硬件层面防崩溃、防篡改；
    
- 碎片整合：把系统零散的内存碎片，通过地址映射拼接成设备可用的连续内存，大幅提升内存利用率；
    
- 虚拟机直通：支持把物理硬件直接分配给虚拟机使用，提升虚拟机的硬件性能。
    

## 1.3. DMA与IOMMU关联与工作流程[¶](#dmaiommu "永久链接至标题")

总结二者关系：DMA是数据搬运的执行者，IOMMU是DMA访问内存的管控者与翻译者。DMA负责“搬数据”，IOMMU负责“管地址、管权限、管隔离”，二者协同完成安全、高效的I/O数据传输。

有无IOMMU系统传输流程对比：

1. 无IOMMU系统：CPU分配物理连续内存 -> 直接将物理地址告知DMA设备 -> DMA直接访问物理内存完成数据传输，无地址翻译、无权限校验。
    
2. 有IOMMU系统：CPU分配物理内存 -> IOMMU创建页表，建立“IOVA虚拟地址->物理地址”映射 -> CPU将IOVA虚拟地址下发给DMA设备 -> DMA通过IOVA发起内存访问 -> IOMMU硬件实时翻译为物理地址、校验访问权限 -> 完成数据读写传输。
    

## 1.4. DMA核心结构体[¶](#id11 "永久链接至标题")

注解

本章节主要是为了后续使用DMA子系统的复杂驱动（如DRM驱动）作前置铺垫的，以下涉及一些结构体和函数可能出现得很突兀，是为了方便后续章节出现的结构体和函数可以从本章节找到。

### 1.4.1. DMA控制器设备结构体[¶](#id12 "永久链接至标题")

DMA控制器设备结构体（struct dma_device）用于描述一个DMA控制器硬件，包含控制器属性、通道、操作函数集，是实现多DMA控制器共存、资源统一调度、标准化DMA传输开发的基础核心结构体。

dma_device结构体(内核源码/include/linux/dmaengine.h)[¶](#id45 "永久链接至代码")

```c
 1  struct dma_device {
 2      struct kref ref;                    // 设备引用计数
 3      unsigned int chancnt;               // 可用DMA通道总数
 4      struct list_head channels;          // 所属DMA通道链表
 5      struct list_head global_node;       // 全局DMA设备链表节点
 6
 7      dma_cap_mask_t  cap_mask;           // 控制器能力掩码，标识支持的传输类型
 8      enum dma_residue_granularity residue_granularity; // 传输剩余数据精度
 9
10      struct device *dev;                 // 绑定的内核设备结构体
11      struct module *owner;               // 模块所有者
12
13      /* 通道资源申请与释放 */
14      int (*device_alloc_chan_resources)(struct dma_chan *chan);
15      void (*device_free_chan_resources)(struct dma_chan *chan);
16
17      /* 核心传输预处理接口 */
18      // 内存拷贝DMA
19      struct dma_async_tx_descriptor *(*device_prep_dma_memcpy)(
20          struct dma_chan *chan, dma_addr_t dst, dma_addr_t src,
21          size_t len, unsigned long flags);
22
23      // 外设散射聚集DMA
24      struct dma_async_tx_descriptor *(*device_prep_slave_sg)(
25          struct dma_chan *chan, struct scatterlist *sgl,
26          unsigned int sg_len, enum dma_transfer_direction direction,
27          unsigned long flags, void *context);
28
29      // 循环DMA传输，音频/视频周期性传输使用
30      struct dma_async_tx_descriptor *(*device_prep_dma_cyclic)(
31          struct dma_chan *chan, dma_addr_t buf_addr, size_t buf_len,
32          size_t period_len, enum dma_transfer_direction direction,
33          unsigned long flags);
34
35      /* 设备控制接口 */
36      int (*device_config)(struct dma_chan *chan,
37                          struct dma_slave_config *config); // 通道参数配置
38      int (*device_pause)(struct dma_chan *chan);           // 暂停传输
39      int (*device_resume)(struct dma_chan *chan);          // 恢复传输
40      int (*device_terminate_all)(struct dma_chan *chan);   // 终止所有传输
41
42      /* 状态查询与任务下发 */
43      enum dma_status (*device_tx_status)(struct dma_chan *chan,
44                                          dma_cookie_t cookie,
45                                          struct dma_tx_state *txstate);
46      void (*device_issue_pending)(struct dma_chan *chan); // 下发pending任务
47      /* 其他成员省略 */
48  };
```

### 1.4.2. DMA通道结构体[¶](#id13 "永久链接至标题")

DMA通道结构体（struct dma_chan）用于抽象、描述单条DMA物理通道的全部属性、运行状态、挂载归属与私有配置，是驱动操作、管理、调度单条DMA传输通路的核心载体。

dma_chan结构体(内核源码/include/linux/dmaengine.h)[¶](#id46 "永久链接至代码")

```c
 1  struct dma_chan {
 2      struct dma_device *device;          // 所属DMA控制器设备
 3      struct device *slave;               // 绑定的从设备
 4      dma_cookie_t cookie;                // 当前传输Cookie标记
 5      dma_cookie_t completed_cookie;      // 已完成传输Cookie标记
 6
 7      /* sysfs文件系统节点属性 */
 8      int chan_id;                        // 通道唯一ID
 9      struct dma_chan_dev *dev;           // 通道设备节点
10      const char *name;                   // 通道名称
11
12      struct list_head device_node;       // 挂载到dma_device的链表节点
13      struct dma_chan_percpu __percpu *local; // 多核私有数据
14      int client_count;                   // 绑定客户端数量
15      int table_count;                    // 传输描述符表数量
16
17      /* DMA路由配置 */
18      struct dma_router *router;          // DMA路由控制器
19      void *route_data;                   // 路由私有数据
20
21      void *private;                      // 厂商自定义私有数据
22      /* 其他成员省略 */
23  };
```

### 1.4.3. DMA通道设备节点结构体[¶](#id14 "永久链接至标题")

DMA通道设备节点结构体（struct dma_chan_dev）是DMA通道对应的设备节点管理结构体，用于将抽象的DMA通道实例化为内核标准设备， 在sysfs文件系统中生成独立的通道设备节点，支撑DMA通道的用户态查询、调试与状态管理，是DMA通道设备化、可视化管理的基础结构体。

dma_chan_dev结构体(内核源码/include/linux/dmaengine.h)[¶](#id47 "永久链接至代码")

```c
struct dma_chan_dev {
    struct dma_chan *chan;        // 绑定对应的DMA通道结构体
    struct device device;         // 内核标准设备结构体
    int dev_id;                   // 通道设备唯一ID
    bool chan_dma_dev;            // 标记是否为DMA通道专属设备
};
```

### 1.4.4. DMA共享缓冲区结构体[¶](#id15 "永久链接至标题")

DMA共享缓冲区结构体（struct dma_buf）是Linux内核DMA共享缓冲区（DMA-BUF）的核心管理结构体，用于实现跨设备、跨驱动、跨进程的DMA内存共享。 统一管理一块DMA可用物理缓冲区的生命周期、设备挂载、同步与操作方法，是多媒体、GPU、摄像头、多设备协同DMA传输的核心基础结构体，支撑内存零拷贝共享传输。

dma_buf结构体(内核源码/include/linux/dma-buf.h)[¶](#id48 "永久链接至代码")

```c
 1  struct dma_buf {
 2      size_t size;                        // DMA缓冲区总大小
 3      struct file *file;                  // 文件指针，用于引用计数与跨进程共享
 4      struct list_head attachments;       // 挂载的设备附件链表，记录绑定的DMA设备
 5      const struct dma_buf_ops *ops;      // 缓冲区专属操作方法集
 6      struct mutex lock;                  // 互斥锁，保护链表、映射等操作
 7      unsigned vmapping_counter;          // 虚拟映射引用计数
 8      struct iosys_map vmap_ptr;          // 内核虚拟映射地址
 9      const char *exp_name;               // 缓冲区导出模块名称
10      struct module *owner;               // 所属内核模块，用于生命周期管理
11      struct list_head list_node;         // 全局DMA-BUF链表节点
12      void *priv;                         // 厂商自定义私有数据
13      struct dma_resv *resv;              // 缓冲区同步屏障对象，用于DMA异步同步
14      /* 其他成员省略 */
15  };
```

### 1.4.5. DMA缓冲区设备挂载结构体[¶](#id16 "永久链接至标题")

DMA缓冲区设备挂载结构体（struct dma_buf_attachment）是DMA-BUF子系统的设备挂载核心结构体，用于建立DMA共享缓冲区与外设设备的绑定关系。 每一个设备挂载一块DMA共享缓冲区时，内核都会生成一个attachment实例，用于记录设备信息、缓冲区映射表、传输方向、DMA映射属性与私有数据，是实现多设备、跨驱动零拷贝共享DMA内存的关键载体。

dma_buf_attachment结构体(内核源码/include/linux/dma-buf.h)[¶](#id49 "永久链接至代码")

```c
struct dma_buf_attachment {
    struct dma_buf *dmabuf;             // 绑定的DMA共享缓冲区
    struct device *dev;                 // 挂载的目标外设设备
    struct list_head node;              // 挂载到dmabuf的链表节点
    struct sg_table *sgt;               // 缓冲区散射聚集映射表
    enum dma_data_direction dir;        // DMA数据传输方向
    void *priv;                         // 私有扩展数据
    unsigned long dma_map_attrs;        // DMA映射属性标识
};
```

### 1.4.6. DMA缓冲区导出信息结构体[¶](#id17 "永久链接至标题")

DMA缓冲区导出信息结构体（struct dma_buf_export_info）是DMA-BUF子系统的缓冲区导出配置结构体，用于驱动创建自定义DMA共享缓冲区时，统一传入缓冲区基础配置参数。

dma_buf_export_info结构体(内核源码/include/linux/dma-buf.h)[¶](#id50 "永久链接至代码")

```c
struct dma_buf_export_info {
    const char *exp_name;               // 缓冲区导出名称
    struct module *owner;               // 所属内核模块，用于生命周期管理
    const struct dma_buf_ops *ops;      // 自定义DMA缓冲区操作方法集
    size_t size;                        // 待创建缓冲区总大小
    int flags;                          // 缓冲区创建属性标志
    struct dma_resv *resv;              // 缓冲区异步同步屏障对象
    void *priv;                         // 驱动自定义私有数据
};
```

### 1.4.7. DMA-IOMMU映射管理结构体[¶](#dma-iommu "永久链接至标题")

DMA-IOMMU映射管理结构体（struct dma_iommu_mapping）是DMA与IOMMU联动的底层映射管理核心结构体，专门用于维护DMA设备的IOMMU虚拟地址空间映射关系。负责管理IOVA地址位图分配、绑定IOMMU地址域、维护映射资源引用计数与线程锁，实现DMA设备IOVA地址的批量分配、回收与安全管控。

dma_iommu_mapping结构体(内核源码/arch/arm/include/asm/dma-iommu.h)[¶](#id51 "永久链接至代码")

```c
struct dma_iommu_mapping {
    struct iommu_domain *domain;    // 绑定的IOMMU地址域
    unsigned long   **bitmaps;      // IOVA地址分配位图数组
    unsigned int    nr_bitmaps;     // 位图数组数量
    size_t  bitmap_size;            // 单张位图大小
    dma_addr_t  base;               // IOMMU映射IOVA基地址

    spinlock_t  lock;               // 位图操作自旋锁
    struct kref kref;               // 映射资源引用计数
};
```

## 1.5. DMA子系统核心函数[¶](#id18 "永久链接至标题")

### 1.5.1. DMA掩码与一致性掩码配置[¶](#id19 "永久链接至标题")

#### 1.5.1.1. dma_set_mask_and_coherent函数[¶](#dma-set-mask-and-coherent "永久链接至标题")

dma_set_mask_and_coherent函数用于一次性设置设备DMA寻址掩码和一致性内存掩码，声明设备支持的DMA地址范围，是DMA内存分配的前置函数。

函数原型：

```c
int dma_set_mask_and_coherent(struct device *dev, u64 mask);
```

参数说明：

- dev：设备结构体指针，当前需要配置DMA能力的设备；
    
- mask：DMA地址掩码，由DMA_BIT_MASK(n)生成，代表设备支持的地址位宽。
    

返回值：

- 0：配置成功；
    
- -EINVAL：掩码不合法，设备不支持对应位宽；
    
- -ENXIO：设备无DMA能力。
    

### 1.5.2. 分配DMA一致性内存[¶](#id20 "永久链接至标题")

#### 1.5.2.1. dma_alloc_coherent函数[¶](#dma-alloc-coherent "永久链接至标题")

dma_alloc_coherent函数用于分配硬件Cache一致性的DMA内存，同时返回CPU虚拟地址与DMA设备IOVA地址，无需手动刷新缓存。

函数原型：

```c
void *dma_alloc_coherent(struct device *dev, size_t size,
                        dma_addr_t *dma_handle, gfp_t gfp);
```

参数说明：

- dev：设备结构体指针；
    
- size：需要分配的内存大小；
    
- dma_handle：出参，用于接收DMA设备使用的IOVA地址；
    
- gfp：内存分配标志，常用GFP_KERNEL（内核常规分配）。
    

返回值：

- 非NULL：分配成功，返回CPU虚拟地址；
    
- NULL：内存分配失败。
    

### 1.5.3. 释放DMA一致性内存[¶](#id21 "永久链接至标题")

#### 1.5.3.1. dma_free_coherent函数[¶](#dma-free-coherent "永久链接至标题")

dma_free_coherent函数用于释放由dma_alloc_coherent分配的一致性DMA内存，与分配函数成对使用，防止内存泄漏。

函数原型：

```c
void dma_free_coherent(struct device *dev, size_t size,
                    void *cpu_addr, dma_addr_t dma_handle);
```

参数说明:

- dev：设备结构体指针；
    
- size：释放的内存大小，必须与分配时大小一致；
    
- cpu_addr：分配得到的CPU虚拟地址；
    
- dma_handle：分配得到的DMA IOVA地址。
    

### 1.5.4. 获取带属性的SG散射聚集表[¶](#sg "永久链接至标题")

#### 1.5.4.1. dma_get_sgtable_attrs函数[¶](#dma-get-sgtable-attrs "永久链接至标题")

dma_get_sgtable_attrs函数用于根据DMA内存地址、CPU虚拟地址及内存属性，生成标准化的SG散射聚集表，用于DMA批量传输。支持自定义DMA内存属性，适配无内核虚拟映射、写合并等特殊DMA内存场景。

函数原型：

```c
int dma_get_sgtable_attrs(struct device *dev, struct sg_table *sgt,
                        void *cpu_addr, dma_addr_t dma_addr,
                        size_t size, unsigned long attrs);
```

参数说明：

- dev：绑定的设备结构体指针；
    
- sgt：出参，初始化完成的SG表结构体；
    
- cpu_addr：DMA内存对应的CPU虚拟地址；
    
- dma_addr：DMA设备访问的IOVA/物理地址；
    
- size：内存总大小；
    
- attrs：DMA内存属性（如DMA_ATTR_NO_KERNEL_MAPPING、DMA_ATTR_WRITE_COMBINE）。
    

返回值：

- 0：SG表生成成功；
    
- 负数：生成失败，返回内核标准错误码。
    

## 1.6. IOMMU核心结构体[¶](#id22 "永久链接至标题")

### 1.6.1. IOMMU硬件操作函数集结构体[¶](#id23 "永久链接至标题")

IOMMU硬件操作函数集结构体（struct iommu_ops）是硬件适配层核心操作集结构体，是实现IOMMU通用核心层与各厂商硬件差异化驱动解耦的关键载体。 该结构体统一标准化定义了IOMMU硬件必备的底层操作回调接口，屏蔽不同芯片平台IOMMU硬件的寄存器差异、映射逻辑差异、总线适配差异。

iommu_ops结构体(内核源码/include/linux/iommu.h)[¶](#id52 "永久链接至代码")

```c
 1  struct iommu_ops {
 2      /* 硬件能力校验 */
 3      bool (*capable)(struct device *dev, enum iommu_cap);
 4
 5      /* IOMMU地址域分配 */
 6      struct iommu_domain *(*domain_alloc)(unsigned iommu_domain_type);
 7
 8      /* 设备IOMMU探测、释放与收尾 */
 9      struct iommu_device *(*probe_device)(struct device *dev);
10      void (*release_device)(struct device *dev);
11      void (*probe_finalize)(struct device *dev);
12
13      /* 获取设备IOMMU分组 */
14      struct iommu_group *(*device_group)(struct device *dev);
15
16      /* 解析设备预留内存区域 */
17      void (*get_resv_regions)(struct device *dev, struct list_head *list);
18
19      /* 设备树属性解析、延迟挂载判断 */
20      int (*of_xlate)(struct device *dev, struct of_phandle_args *args);
21      bool (*is_attach_deferred)(struct device *dev);
22
23      /* IOMMU设备特性开关 */
24      int (*dev_enable_feat)(struct device *dev, enum iommu_dev_features f);
25      int (*dev_disable_feat)(struct device *dev, enum iommu_dev_features f);
26
27      /* 获取设备默认域类型 */
28      int (*def_domain_type)(struct device *dev);
29
30      /* 默认地址域操作集、硬件页掩码、模块归属 */
31      const struct iommu_domain_ops *default_domain_ops;
32      unsigned long pgsize_bitmap;
33      struct module *owner;
34
35      /* 其他成员省略 */
36  };
```

### 1.6.2. IOMMU地址域结构体[¶](#id24 "永久链接至标题")

IOMMU地址域结构体（struct iommu_domain）是实现设备地址隔离与内存映射管理的核心单元，是IOMMU硬件完成地址翻译、设备隔离的基础载体。 该结构体用于抽象一套独立的设备IOVA虚拟地址空间，每一个iommu_domain实例对应一块完全独立的I/O地址域，严格管控当前地址域内的内存映射关系与访问权限。

iommu_domain结构体(内核源码/include/linux/iommu.h)[¶](#id53 "永久链接至代码")

```c
struct iommu_domain {
    unsigned type;                          // IOMMU域类型标识
    const struct iommu_domain_ops *ops;     // 地址域专属操作方法集
    unsigned long pgsize_bitmap;            // 硬件支持的页尺寸位图
    iommu_fault_handler_t handler;          // IOMMU异常故障处理回调
    void *handler_token;                    // 异常处理回调私有参数
    struct iommu_domain_geometry geometry;  // 地址域空间孔径、范围属性
    struct iommu_dma_cookie *iova_cookie;   // IOVA地址空间管理标记
};
```

### 1.6.3. IOMMU地址域孔径几何属性结构体[¶](#id25 "永久链接至标题")

IOMMU地址域孔径几何属性结构体（struct iommu_domain_geometry）用于描述单个IOMMU地址域的有效映射地址孔径范围，限定当前地址域允许设备访问的IOVA虚拟地址区间，是IOMMU地址空间权限管控的基础配置结构体。

iommu_domain_geometry结构体(内核源码/include/linux/iommu.h)[¶](#id54 "永久链接至代码")

```c
struct iommu_domain_geometry {
    dma_addr_t aperture_start; /* 地址域可映射的首个IOVA地址 */
    dma_addr_t aperture_end;   /* 地址域可映射的末尾IOVA地址 */
    bool force_aperture;       /* 是否强制DMA仅允许在合法孔径范围内访问 */
};
```

## 1.7. IOMMU驱动核心函数[¶](#id26 "永久链接至标题")

### 1.7.1. 分配IOMMU地址域[¶](#id27 "永久链接至标题")

#### 1.7.1.1. iommu_domain_alloc函数[¶](#iommu-domain-alloc "永久链接至标题")

iommu_domain_alloc函数用于为指定总线设备分配独立的IOMMU地址映射域。

函数原型：

```c
struct iommu_domain *iommu_domain_alloc(struct bus_type *bus);
```

参数说明：

- bus：设备所属总线类型。
    

返回值：成功返回iommu_domain结构体指针，失败返回NULL。

### 1.7.2. 释放IOMMU地址域[¶](#id28 "永久链接至标题")

#### 1.7.2.1. iommu_domain_free函数[¶](#iommu-domain-free "永久链接至标题")

iommu_domain_free函数用于销毁并释放IOMMU地址域资源，与 iommu_domain_alloc 成对使用。

函数原型：

```c
void iommu_domain_free(struct iommu_domain *domain);
```

参数说明：

- domain：需要销毁释放的IOMMU地址域结构体指针。
    

### 1.7.3. IOMMU地址映射[¶](#id29 "永久链接至标题")

#### 1.7.3.1. iommu_map函数[¶](#iommu-map "永久链接至标题")

iommu_map函数用于建立IOVA虚拟地址到物理地址的映射关系。

函数原型：

```c
int iommu_map(struct iommu_domain *domain, dma_addr_t iova,
          phys_addr_t paddr, size_t size, int prot);
```

参数说明：

- domain：IOMMU地址域；
    
- iova：设备虚拟地址；
    
- paddr：物理内存地址；
    
- size：映射内存大小；
    
- prot：访问权限。
    

返回值：0成功，负数失败。

### 1.7.4. IOMMU地址解映射[¶](#id30 "永久链接至标题")

#### 1.7.4.1. iommu_unmap函数[¶](#iommu-unmap "永久链接至标题")

iommu_unmap函数用于销毁指定IOVA地址的映射关系，释放IOMMU页表资源。

函数原型：

```c
size_t iommu_unmap(struct iommu_domain *domain, dma_addr_t iova, size_t size);
```

参数说明：

- domain：待解映射的IOMMU独立地址域；
    
- iova：需要解除映射的设备IOVA虚拟起始地址；
    
- size：待解除映射的内存区域大小，需与映射时大小一致。
    

返回值：成功返回解映射的字节大小，失败返回负数。

### 1.7.5. 设备绑定IOMMU地址域[¶](#id31 "永久链接至标题")

#### 1.7.5.1. iommu_attach_device函数[¶](#iommu-attach-device "永久链接至标题")

iommu_attach_device函数用于将指定外设设备挂载绑定到目标IOMMU地址域，让设备隶属于该独立地址空间，生效当前domain的地址映射、权限管控与隔离规则，是设备启用IOMMU地址翻译的核心前置函数。

函数原型：

```c
int iommu_attach_device(struct iommu_domain *domain, struct device *dev);
```

参数说明：

- domain：待绑定的IOMMU独立地址域；
    
- dev：需要挂载到地址域的外设设备结构体。
    

返回值：0绑定成功；负数绑定失败。

### 1.7.6. 设置IOMMU异常故障回调[¶](#id32 "永久链接至标题")

#### 1.7.6.1. iommu_set_fault_handler函数[¶](#iommu-set-fault-handler "永久链接至标题")

iommu_set_fault_handler函数为指定的IOMMU地址映射域注册故障异常回调函数。如DRM显存依赖IOMMU实现虚拟IOVA映射，当显存DMA访问出现地址非法、映射失效、权限错误等异常时，内核会触发该回调。

函数原型：

```c
void iommu_set_fault_handler(struct iommu_domain *domain,
                iommu_fault_handler_t handler, void *data);
```

参数说明：

- domain：IOMMU映射域结构体。
    
- handler：自定义故障处理回调函数，用于捕获、处理IOMMU异常。
    
- data：回调函数私有入参，一般传入设备私有数据指针。
    

### 1.7.7. 预留IOMMU固定映射空间[¶](#id33 "永久链接至标题")

#### 1.7.7.1. iommu_reserve_map函数[¶](#iommu-reserve-map "永久链接至标题")

iommu_reserve_map函数用于在IOMMU虚拟地址空间中预留并锁定一段固定IOVA区间，禁止系统动态分配、覆盖该段地址。

函数原型：

```c
int iommu_reserve_map(struct iommu_domain *domain, dma_addr_t iova,
            size_t size, unsigned long prot);
```

参数说明：

- domain：IOMMU映射域，与DRM显存管理绑定的地址空间。
    
- iova：需要预留的起始虚拟IOVA地址。
    
- size：预留地址空间大小。
    
- prot：映射权限属性，配置读写、缓存、设备访问权限。
    

返回值：0 预留成功；负数 预留失败。

### 1.7.8. SG表批量IOMMU映射[¶](#sgiommu "永久链接至标题")

#### 1.7.8.1. iommu_map_sgtable函数[¶](#iommu-map-sgtable "永久链接至标题")

iommu_map_sgtable函数用于基于散射聚集SG表，批量完成多段离散物理内存的IOMMU地址映射，将碎片化物理内存统一映射为连续的IOVA虚拟地址，适配SG-DMA大数据传输场景。

函数原型：

```c
size_t iommu_map_sgtable(struct iommu_domain *domain, dma_addr_t iova,
                        struct sg_table *sgt, int prot);
```

参数说明：

- domain：目标IOMMU地址域；
    
- iova：起始IOVA虚拟地址；
    
- sgt：散射聚集内存表，存储多段离散物理内存信息；
    
- prot：内存访问权限。
    

返回值：成功返回实际映射的总字节大小，失败返回0。

### 1.7.9. 刷新全部IOTLB缓存[¶](#iotlb "永久链接至标题")

#### 1.7.9.1. iommu_flush_iotlb_all函数[¶](#iommu-flush-iotlb-all "永久链接至标题")

iommu_flush_iotlb_all函数用于强制刷新指定IOMMU地址域的全部IOTLB地址翻译缓存，清空老旧映射缓存。 在页表映射更新、解映射、权限修改后调用，避免硬件缓存残留旧地址映射导致的数据访问异常、传输失败问题。

函数原型：

```c
void iommu_flush_iotlb_all(struct iommu_domain *domain);
```

参数说明

- domain：需要刷新缓存的IOMMU地址域。
    

## 1.8. DMA一致性内存实验[¶](#id34 "永久链接至标题")

本实验进行DMA一致性内存测试，结合平台设备框架、IOMMU地址映射、DMA内存管理、字符设备等实现用户空间与内核DMA物理内存的数据交互，验证DMA一致性内存与IOMMU映射机制。

本章的示例代码目录为： **linux_driver/35_dma_iommu**

### 1.8.1. 设备树插件详解[¶](#id35 "永久链接至标题")

本实验设备树插件（lubancat-dma-iommu-overlay.dts）主要用来匹配平台驱动，完整代码如下：

lubancat-dma-iommu-overlay.dts(位于linux_driver/35_dma_iommu/lubancat-dma-iommu-overlay.dts)[¶](#id55 "永久链接至代码")

```dts
 1  /dts-v1/;
 2  /plugin/;
 3
 4  / {
 5      fragment@0 {
 6          target-path = "/";
 7
 8          __overlay__ {
 9              dma_iommu_test: dma-iommu-test {
10                  compatible = "fire,dma-iommu";
11                  status = "okay";
12              };
13          };
14      };
15  };
```

关键说明：

- 在根节点下增加dma_iommu_test节点，compatible属性标识需与驱动中of_match_table的属性完全一致，否则驱动无法匹配设备。
    

### 1.8.2. 驱动代码详解[¶](#id36 "永久链接至标题")

**核心定义与数据结构**

核心定义与数据结构(位于linux_driver/35_dma_iommu/dma_iommu.c)[¶](#id56 "永久链接至代码")

```c
 1  /* 设备名称 */
 2  #define DEVICE_NAME "dma_iommu"
 3  /* DMA缓冲区大小设置为4KB */
 4  #define DMA_BUFFER_SIZE (4 * 1024)
 5
 6  /* DMA IOMMU私有数据结构体 */
 7  struct dma_iommu_priv {
 8      dma_addr_t dma_addr;             /* DMA地址 */
 9      void *virt_addr;                 /* 虚拟地址 */
10      size_t size;                     /* 缓冲区大小 */
11      size_t actual_len;               /* 记录有效数据长度 */
12      struct mutex lock;               /* 互斥体 */
13      struct cdev cdev;                /* 字符设备 */
14      struct device *dev;              /* 设备指针 */
15      dev_t devt;                      /* 设备号 */
16      struct class *class;             /* 设备类指针 */
17  };
```

关键说明：

- 第8行：dma_addr_t为DMA专用地址类型，存储IOMMU映射后的IOVA地址，非物理地址。
    
- 第9行：CPU专属访问地址，属于内核态线性虚拟地址，用户空间不可直接访问，通过该地址完成内核侧DMA缓冲区数据读写。
    
- 第12行：互斥锁绑定设备，确保同一时间只有一个进程可读写DMA缓冲区。
    

**probe函数**

probe函数(位于linux_driver/35_dma_iommu/dma_iommu.c)[¶](#id57 "永久链接至代码")

```c
  1  /* 设备探测函数 */
  2  static int dma_iommu_probe(struct platform_device *pdev)
  3  {
  4      /* 私有数据指针 */
  5      struct dma_iommu_priv *priv;
  6      /* 设备指针 */
  7      struct device *dev = &pdev->dev;
  8      /* 返回值 */
  9      int ret;
 10
 11      /* 分配私有数据内存 */
 12      priv = devm_kzalloc(dev, sizeof(*priv), GFP_KERNEL);
 13      if (!priv)
 14          return -ENOMEM;
 15
 16      /* 设置缓冲区大小 */
 17      priv->size = DMA_BUFFER_SIZE;
 18      /* 初始化有效数据长度为0 */
 19      priv->actual_len = 0;
 20      /* 保存设备指针到私有数据 */
 21      priv->dev = dev;
 22
 23      /* 初始化互斥锁 */
 24      mutex_init(&priv->lock);
 25
 26      /* 设置DMA掩码为64位 */
 27      ret = dma_set_mask_and_coherent(dev, DMA_BIT_MASK(64));
 28      if (ret)
 29      {
 30          printk(KERN_WARNING "Cannot set DMA mask to 64 bit, trying 32 bit\n");
 31          ret = dma_set_mask_and_coherent(dev, DMA_BIT_MASK(32));
 32          /* 尝试设置32位DMA掩码 */
 33          if (ret)
 34          {
 35              printk(KERN_ERR "No suitable DMA available\n");
 36              return ret;
 37          }
 38      }
 39
 40      /* 分配DMA一致性内存 */
 41      priv->virt_addr = dma_alloc_coherent(dev, priv->size, &priv->dma_addr, GFP_KERNEL);
 42      if (!priv->virt_addr)
 43      {
 44          printk(KERN_ERR "Failed to allocate DMA memory\n");
 45          return -ENOMEM;
 46      }
 47
 48      printk(KERN_INFO "DMA memory allocated:\n");
 49      printk(KERN_INFO "  CPU Virtual address: 0x%pK\n", priv->virt_addr);  /* 打印内核虚拟地址 */
 50      printk(KERN_INFO "  Device IOVA address: %pad\n", &priv->dma_addr);   /* 打印DMA地址 */
 51
 52      /* 清空DMA缓冲区 */
 53      memset(priv->virt_addr, 0, priv->size);
 54      /* 创建设备类 */
 55      priv->class = class_create(THIS_MODULE, DEVICE_NAME);
 56      if (IS_ERR(priv->class))
 57      {
 58          printk(KERN_ERR "Failed to create class\n");
 59          ret = PTR_ERR(priv->class);
 60          goto err_free_dma;
 61      }
 62
 63      /* 动态分配字符设备号 */
 64      ret = alloc_chrdev_region(&priv->devt, 0, 1, DEVICE_NAME);
 65      if (ret)
 66      {
 67          printk(KERN_ERR "Failed to allocate char device region\n");
 68          goto err_destroy_class;
 69      }
 70
 71      /* 初始化字符设备 */
 72      cdev_init(&priv->cdev, &dma_iommu_fops);
 73      /* 设置设备所有者 */
 74      priv->cdev.owner = THIS_MODULE;
 75
 76      /* 添加字符设备 */
 77      ret = cdev_add(&priv->cdev, priv->devt, 1);
 78      if (ret)
 79      {
 80          printk(KERN_ERR "Failed to add cdev\n");
 81          goto err_unregister_region;
 82      }
 83      /* 打印设备号信息 */
 84      printk(KERN_INFO "char device major=%d, minor=%d\n", MAJOR(priv->devt), MINOR(priv->devt));
 85
 86      /* 创建设备节点 */
 87      if (device_create(priv->class, NULL, priv->devt, NULL, DEVICE_NAME) == NULL)
 88      {
 89          printk(KERN_ERR "Failed to create device\n");
 90          goto err_del_cdev;
 91      }
 92      /* 保存私有数据到平台设备 */
 93      platform_set_drvdata(pdev, priv);
 94
 95      return 0;
 96
 97  err_del_cdev:
 98      /* 删除字符设备 */
 99      cdev_del(&priv->cdev);
100  err_unregister_region:
101      /* 释放设备号 */
102      unregister_chrdev_region(priv->devt, 1);
103  err_destroy_class:
104      /* 销毁设备类 */
105      class_destroy(priv->class);
106  err_free_dma:
107      /* 释放DMA内存 */
108      dma_free_coherent(dev, priv->size, priv->virt_addr, priv->dma_addr);
109      return ret;
110  }
```

关键说明：

- 第17行：设置DMA缓冲区大小为DMA_BUFFER_SIZE，即4k大小。
    
- 第19行：初始化有效数据长度为0，默认没有数据写入DMA缓冲区。
    
- 第27-37行：优先配置64位DMA掩码，适配现代平台，失败自动降级32位。
    
- 第40行：dma_alloc_coherent核心函数，一次性返回内核虚拟地址与IOMMU设备地址。
    
- 第52行：清空DMA缓冲区，避免有脏数据残留。
    

**写入数据函数**

写入数据函数(位于linux_driver/35_dma_iommu/dma_iommu.c)[¶](#id58 "永久链接至代码")

```c
 1  /* 写入数据函数 */
 2  static ssize_t dma_iommu_write(struct file *file, const char __user *buf, size_t count, loff_t *ppos)
 3  {
 4      /* 获取私有数据 */
 5      struct dma_iommu_priv *priv = file->private_data;
 6      /* 写入长度 */
 7      size_t len;
 8
 9      /* 获取互斥锁 */
10      mutex_lock(&priv->lock);
11
12      /* 限制最大写入，留1字节给字符串结束符 */
13      len = min(count, priv->size - 1);
14
15      /* 只清空本次要用的区域 */
16      memset(priv->virt_addr, 0, len + 1);
17
18      /* 将数据从用户空间复制到内核空间 */
19      if (copy_from_user(priv->virt_addr, buf, len))
20      {
21          mutex_unlock(&priv->lock);     /* 释放互斥锁 */
22          return -EFAULT;                /* 返回错误 */
23      }
24
25      /* 添加字符串结束符 */
26      ((char *)priv->virt_addr)[len] = '\0';
27
28      /* 记录当前有效数据长度*/
29      priv->actual_len = len;
30
31      /* 打印写入信息 */
32      dev_info(priv->dev, "Written to DMA memory: \"%s\"\n", (char *)priv->virt_addr);
33
34      /* 重置文件偏移量 */
35      *ppos = 0;
36
37      /* 释放互斥锁 */
38      mutex_unlock(&priv->lock);
39
40      /* 返回写入的字节数 */
41      return len;
42  }
```

关键说明：

- 第13行：预留1字节空间，防止字符串无结束符导致内核内存乱码、越界读取。
    
- 第16行：每次写入前清空要用的缓冲区，避免新旧数据叠加污染和清空过大区域耗时过长。
    
- 第19行：将数据从用户空间复制到内核空间，写入到DMA缓冲区。
    
- 第26行：手动添加字符串结束符，保证内核打印和读取数据正常。
    
- 第29行：记录当前有效数据长度，方便读取数据函数确认可读数据长度。
    
- 第35行：重置偏移量，适配常规文件读写逻辑，下次读取从头开始。
    

**读取数据函数**

读取数据函数(位于linux_driver/35_dma_iommu/dma_iommu.c)[¶](#id59 "永久链接至代码")

```c
 1  /* 读取数据函数 */
 2  static ssize_t dma_iommu_read(struct file *file, char __user *buf, size_t count, loff_t *ppos)
 3  {
 4      /* 获取私有数据 */
 5      struct dma_iommu_priv *priv = file->private_data;
 6      /* 剩余可读数据长度 */
 7      size_t remaining;
 8      /* 本次读取长度 */
 9      size_t len;
10
11      /* 获取互斥锁 */
12      mutex_lock(&priv->lock);
13
14      /* 没有有效数据或偏移已读到末尾直接返回 */
15      if (priv->actual_len == 0 || *ppos >= priv->actual_len)
16      {
17          mutex_unlock(&priv->lock);
18          return 0;
19      }
20
21      /* 获取剩余可读字节 */
22      remaining = priv->actual_len - *ppos;
23      /* 限制本次读取数据长度不超过剩余、也不超过用户请求 */
24      len = min(count, remaining);
25
26      /* 将数据从内核空间复制到用户空间 */
27      if (copy_to_user(buf, (char *)priv->virt_addr + *ppos, len))
28      {
29          mutex_unlock(&priv->lock);     /* 释放互斥锁 */
30          return -EFAULT;                /* 返回错误 */
31      }
32
33      /* 更新文件偏移量 */
34      *ppos += len;
35
36      /* 释放互斥锁 */
37      mutex_unlock(&priv->lock);
38
39      /* 返回读取的字节数 */
40      return len;
41  }
```

关键说明：

- 第15行：DMA缓冲区没有有效数据或偏移已读到末尾直接返回，不进行读取。
    
- 第24行：通过min函数限制读取长度，防止越界访问DMA缓冲区。
    
- 第27行：copy_to_user内核态向用户态拷贝数据，禁止直接指针访问。
    
- 第34行：重置偏移量，避免数据重复读取。
    

**设备打开/关闭函数与操作集**

设备打开/关闭函数与操作集(位于linux_driver/35_dma_iommu/dma_iommu.c)[¶](#id60 "永久链接至代码")

```c
 1  /* 打开设备函数 */
 2  static int dma_iommu_open(struct inode *inode, struct file *file)
 3  {
 4      /* 获取私有数据 */
 5      struct dma_iommu_priv *priv = container_of(inode->i_cdev, struct dma_iommu_priv, cdev);
 6      /* 保存私有数据到文件指针 */
 7      file->private_data = priv;
 8
 9      return 0;
10  }
11
12  /* 关闭设备函数 */
13  static int dma_iommu_release(struct inode *inode, struct file *file)
14  {
15      return 0;
16  }
17
18  /* 字符设备的文件操作结构体 */
19  static const struct file_operations dma_iommu_fops = {
20      .owner = THIS_MODULE,
21      .open = dma_iommu_open,
22      .read = dma_iommu_read,
23      .write = dma_iommu_write,
24      .release = dma_iommu_release,
25  };
```

**设备树匹配与驱动注册**

设备树匹配与驱动注册(位于linux_driver/35_dma_iommu/dma_iommu.c)[¶](#id61 "永久链接至代码")

```c
 1  /* 设备树匹配表 */
 2  static const struct of_device_id dma_iommu_of_match[] = {
 3      { .compatible = "fire,dma-iommu" },
 4      { }
 5  };
 6  /* 声明设备树匹配表，供内核自动匹配设备 */
 7  MODULE_DEVICE_TABLE(of, dma_iommu_of_match);
 8
 9  /* 平台驱动结构体 */
10  static struct platform_driver dma_iommu_driver = {
11      .probe = dma_iommu_probe,
12      .remove = dma_iommu_remove,
13      .driver = {
14          .name = "dma-iommu-test",
15          .of_match_table = dma_iommu_of_match,
16      },
17  };
18
19  module_platform_driver(dma_iommu_driver);
```

关键说明：

- 第3行：compatible字符串必须与设备树插件完全一致，大小写敏感，否则驱动无法匹配。
    
- 第19行：module_platform_driver一键注册/注销平台驱动，简化驱动入口出口代码。
    

### 1.8.3. Makefile说明[¶](#makefile "永久链接至标题")

本节实验使用的Makefile如下所示，编写该Makefile时，只需要根据实际情况修改变量KERNEL_DIR、obj-m和test_app即可。

Makefile(位于linux_driver/35_dma_iommu/Makefile)[¶](#id62 "永久链接至代码")

```makefile
#指定内核路径,可以是相对路径或绝对路径
KERNEL_DIR=../../kernel/
# KERNEL_DIR=/home/guest/LubanCat_Linux_Generic_Full_SDK/kernel-6.1
# KERNEL_DIR=/home/guest/LubanCat_Linux_rk3588_SDK/kernel

#指定目标架构为arm64
ARCH=arm64

#指定交叉编译工具链的前缀
CROSS_COMPILE=aarch64-linux-gnu-
# CROSS_COMPILE=/home/guest/LubanCat_Linux_Generic_Full_SDK/prebuilts/gcc/linux-x86/aarch64/gcc-arm-10.3-2021.07-x86_64-aarch64-none-linux-gnu/bin/aarch64-none-linux-gnu-

#导出为环境变量
export  ARCH  CROSS_COMPILE

#指定要编译的内核模块目标文件
obj-m := dma_iommu.o

#all :默认目标，执行时会编译驱动模块
#$(MAKE) ：调用make工具
#-C $(KERNEL_DIR) ：指定的内核源码目录
#M=$(CURDIR) ：模块的源码位于当前目录
#modules ：编译模块
all:
    $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) modules

.PHONE:clean

#清理编译生成的文件
clean:
    $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) clean
```

### 1.8.4. 编译设备树和驱动[¶](#id37 "永久链接至标题")

#### 1.8.4.1. 编译设备树[¶](#id38 "永久链接至标题")

修改内核目录/arch/arm64/boot/dts/rockchip/overlays下的Makefile文件，添加我们编辑好的设备树插件，并把设备树插件文件放在和Makefile文件同级目录下，以进行设备树插件的编译。

![../_images/subsystem_dma_iommu_0.jpg](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/subsystem_dma_iommu_0.jpg)

然后在内核源码顶层目录执行以下命令编译设备树插件：

```bash
#这里以rk356x系列4.19.232内核配置文件为例
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- lubancat2_defconfig
make ARCH=arm64 -j4 CROSS_COMPILE=aarch64-linux-gnu- dtbs
```

#### 1.8.4.2. 加载设备树[¶](#id40 "永久链接至标题")

编译出来的设备树插件位于 `内核源码/arch/arm64/boot/dts/rockchip/overlay/lubancat-dma-iommu-overlay.dtbo`， 将设备树插件先传到板卡，再拷贝到板卡的 `/boot/dtb/overlay/` 目录下。

```bash
#先传输到板卡

#再拷贝到板卡的/boot/dtb/overlay/目录下
sudo cp -f lubancat-dma-iommu-overlay.dtbo /boot/dtb/overlay/
```

然后在 `/boot/uEnv/uEnv.txt` 按照格式添加我们的设备树插件，需要在#overlay_start和#overlay_end之间添加，然后重启开发板，那么系统就会加载我们编译的设备树插件。

![../_images/subsystem_dma_iommu_1.jpg](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/subsystem_dma_iommu_1.jpg)

#### 1.8.4.3. 编译驱动[¶](#id41 "永久链接至标题")

在实验目录下输入 `make` 即可编译驱动，编译得到内核模块dma_iommu.ko。

### 1.8.5. 程序运行结果[¶](#id42 "永久链接至标题")

如出现 `Permission denied` 或类似字样，请注意用户权限，大部分操作硬件外设的功能，几乎都需要root用户权限，简单的解决方案是在执行语句前加入sudo或以root用户运行程序。

#### 1.8.5.1. 实验操作[¶](#id43 "永久链接至标题")

使用以下命令加载驱动并测试内存读写：

```bash
 1  #加载驱动
 2  sudo insmod dma_iommu.ko
 3
 4  #信息输出如下，以下是DDR容量为16G的板卡
 5  [   57.792710] DMA memory allocated:
 6  [   57.792741]   CPU Virtual address: 0x0000000006f36ce1
 7  [   57.792748]   Device IOVA address: 0x000000010c66e000
 8  [   57.792837] char device major=234, minor=0
 9
10  #写入数据到DMA缓冲区
11  echo -n "hello world!" > /dev/dma_iommu
12
13  #信息打印如下
14  [  128.850827] dma-iommu-test dma-iommu-test: Written to DMA memory: "hello world!"
15
16  #读取写入的数据
17  cat /dev/dma_iommu
18
19  #信息打印如下
20  hello world!
```

可以从驱动加载信息看到，IOMMU设备IOVA地址位置为0x000000010c66e000，对应4294 MB（通过16进制地址先转10进制再除2次1024得到）内存位置，说明IOMMU地址转译功能正常，访问大于4G内存地址正常。

echo命令默认会添加换行符，增加-n参数改为不添加换行符，可以看到写入数据和读取的数据一致，说明DMA一致性内存功能正常。

提示

如果使用DDR容量小于4G的ARM64板卡，驱动也是设置的dma_set_mask_and_coherent(dev, DMA_BIT_MASK(64))，该设置是告诉内核这个设备可以访问的地址范围是64位空间。内核会根据这个掩码，给设备分配在这个范围内的内存，低4GB地址空间也是64位地址空间的一部分，因此，驱动不需要做任何修改功能也会是正常的。

### 1.8.6. 实验注意事项[¶](#id44 "永久链接至标题")

- 内存成对释放：dma_alloc_coherent分配的内存必须通过dma_free_coherent释放，模块卸载不释放会造成内核内存泄漏。
    
- 地址不可混用：CPU虚拟地址、IOVA地址、物理地址三者数值不同，不可混用，外设只能使用IOVA地址，CPU只能操作虚拟地址。
    
- 避免并发访问：所有读写缓冲区操作必须加互斥锁，避免多进程同时读写导致数据错乱。