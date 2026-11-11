原文： https://doc.embedfire.com/linux/rk356x/driver/zh/latest/linux_driver/subsystem_pci_subsystem.html

PCI（Peripheral Component Interconnect, 外设部件互连）总线自1992年由Intel提出以来，一直是PC和服务器中连接外设的主流局部总线。 随着硬件性能迭代，传统并行PCI总线逐步被串行、高速、点对点的PCIe（PCI Express）总线替代，成为当前服务器、嵌入式设备的主流外设总线。 Linux内核从早期版本开始就提供了完整的PCI子系统支持，负责总线枚举、资源配置、驱动匹配、电源管理、错误处理等核心工作。

PCIe在软件层面保持与PCI向后兼容——配置空间布局、BAR机制、驱动模型都延续了PCI的语义，因此Linux内核可以用统一的描述PCI和PCIe设备， 只是在PCIe Core层额外处理ASPM、AER、MSI-X等PCIe特有功能。

## 8.1. PCI/PCIe基础知识[¶](#pci-pcie "永久链接至标题")

### 8.1.1. PCI/PCIe发展历程[¶](#id1 "永久链接至标题")

PCI总线诞生于1992年，属于 **并行** 总线，采用共享总线架构，所有设备共用总线带宽，存在传输速率低、并行干扰、带宽争抢严重等问题，最高传输带宽仅533MB/s，无法满足高速外设的传输需求。

PCIe总线是PCI的迭代升级标准，诞生于2002年，采用 **串行** 点对点差分传输架构，以通道（Lane）为基本单元，每一条Lane由一对发送差分对和一对接收差分对组成，每个设备独立占用链路带宽，支持全双工通信、链路自适应、电源管理等高级特性。 经过多代迭代（1.0/2.0/3.0/4.0/5.0），PCIe 5.0单链路带宽可达32GT/s，适配高速网卡、固态硬盘、GPU等高性能设备，目前已全面替代传统PCI总线。

### 8.1.2. PCI/PCIe相关概念[¶](#id2 "永久链接至标题")

#### 8.1.2.1. 配置空间[¶](#id3 "永久链接至标题")

所有PCI/PCIe设备都拥有独立的配置空间，是设备的核心控制寄存器区域，用于设备识别、参数配置、状态查询，CPU可通过专用的配置读写指令进行访问。

传统PCI设备配置空间大小为256字节（0x00~0xFF），PCIe设备在此基础上扩展为4096字节，分为标准配置头、Capability能力段、扩展Capability能力段三部分。 配置空间包含厂商ID、设备ID、中断号、链路状态、电源状态等信息，是内核枚举、初始化设备的重要依据。

#### 8.1.2.2. BAR空间[¶](#bar "永久链接至标题")

BAR（Base Address Register，基地址寄存器）空间是PCI设备的资源映射空间，设备通过BAR寄存器向内核上报自身需要的IO端口或物理内存空间大小。

PCI设备最多支持6个BAR寄存器，可映射内存资源或IO资源。内核在总线枚举阶段读取BAR信息，为设备分配物理地址， 并通过pci_iomap将物理地址映射为内核虚拟地址，驱动可直接通过虚拟地址读写设备寄存器，完成数据交互。

#### 8.1.2.3. MSI/MSI-X中断机制[¶](#msi-msi-x "永久链接至标题")

传统PCI中断采用INTx边带信号（#INTA~#INTD），存在中断共享、电平冲突等问题。PCIe引入了消息信号中断（Message Signaled Interrupts, MSI）：

- MSI（消息信号中断）：基于内存写操作实现中断上报，无需硬件引脚，支持最多32个独立中断，中断响应效率更高。
    
- MSI-X（扩展消息信号中断）：MSI的增强版本，支持最多2048个独立中断，中断向量可灵活配置，适配多队列、高并发的高速外设（如千兆网卡）。
    

#### 8.1.2.4. ASPM链路电源管理[¶](#aspm "永久链接至标题")

ASPM（Active State Power Management，活动状态电源管理）是PCIe专属的电源节能机制，用于总线链路空闲时自动降低链路功耗。

ASPM支持L0（正常工作）、L1（轻度休眠）、L2（深度休眠）三种链路状态，设备空闲时自动进入低功耗状态，设备工作时快速唤醒，在不影响设备性能的前提下降低整机功耗，广泛应用于嵌入式设备、笔记本电脑。

#### 8.1.2.5. CLKREQ时钟省电机制[¶](#clkreq "永久链接至标题")

CLKREQ（Clock Request，时钟请求）是PCIe设备的硬件级时钟省电特性，属于辅助电源管理机制，常与ASPM配合使用进一步降低设备空载功耗。 该特性允许PCIe终端设备在链路空闲、无数据收发时，主动向主板时钟发生器发送时钟关闭请求，切断设备外部参考时钟输入，从硬件层面关闭时钟电路功耗。

相较于ASPM链路休眠，CLKREQ功耗降幅更大，省电效果更显著。当设备需要收发数据时，可快速请求恢复时钟，唤醒延迟极低，兼顾低功耗与设备响应性能，普遍应用于无线网卡、嵌入式PCIe外设、轻薄本设备。

#### 8.1.2.6. DBI直接后台接口机制[¶](#dbi "永久链接至标题")

DBI（Direct Backend Interface，直接后台接口）是PCIe 3.0及以上版本支持的高级扩展能力，是设备底层寄存器动态配置的专用通道。 传统PCI/PCIe仅能通过标准配置空间访问设备寄存器，而DBI接口可独立访问设备物理层、链路层、厂商自定义私有寄存器， 支持在设备正常工作、业务不中断、无需复位的前提下，动态读写、微调硬件底层参数。

#### 8.1.2.7. PCI三大系统资源空间[¶](#pci "永久链接至标题")

PCI/PCIe设备可通过BAR寄存器映射三类系统资源，内核在枚举阶段会统一分配与管理，是设备寻址的基础：

1. IO空间：传统x86架构专用的端口寻址空间，用于简单设备的轻量寄存器读写，现代高速PCIe设备基本不再使用。
    
2. 非预取内存空间：最常用的MMIO寄存器空间，不支持预读、缓存，用于设备控制寄存器、状态寄存器读写。
    
3. 预取内存空间：支持CPU预读、缓存优化，适合大容量、连续数据传输设备（如显卡显存、高速SSD），可大幅提升批量数据读写性能。
    

#### 8.1.2.8. PCIe TLP数据包传输机制[¶](#pcie-tlp "永久链接至标题")

传统PCI基于并行信号电平传输，无数据包概念；而PCIe所有数据、指令、状态均通过TLP（Transaction Layer Packet，事务层数据包）封装传输，是PCIe高速通信的核心机制。

TLP数据包由包头、数据载荷、校验尾组成，可封装内存读写、IO读写、配置读写、中断消息等所有事务。CPU与设备通信时，驱动下发的读写指令会被内核封装为标准TLP包， 通过差分串行链路发送，接收端解析数据包并执行对应操作。

TLP机制支持乱序传输、分包传输、流量控制、重传纠错，极大提升了传输效率与稳定性，也是PCIe支持MSI/MSI-X消息中断、高级错误上报的底层基础。

#### 8.1.2.9. PCIe AER高级错误上报机制[¶](#pcie-aer "永久链接至标题")

AER（Advanced Error Reporting）是PCIe专属扩展能力，属于扩展Capability，用于细化上报链路CRC错误、TLP校验错误、协议错误、数据异常等硬件错误。

传统PCI仅能上报笼统的设备异常，而AER可精准定位错误类型、错误链路、错误地址，内核可根据AER日志完成错误重试、链路重置、设备降级等容错处理，大幅提升高速设备的运行稳定性。

### 8.1.3. PCIe标准拓扑架构[¶](#pcie "永久链接至标题")

PCIe采用树状分层拓扑结构，与PCI扁平总线架构完全不同，是其高带宽、可扩展、支持多设备的原因。

![../_images/subsystem_pci_subsystem_0.jpg](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/subsystem_pci_subsystem_0.jpg)

- **根复合体(Root Complex)** ：系统的“大脑”，它直接连接着CPU​和System Memory(系统内存)，是整个PCIe树的“根节点”和流量控制中心。系统启动时，由它发起对所有PCIe设备的枚举；在运行过程中，它负责将CPU发出的内存读写请求转换成PCIe事务层数据包(TLP)，并路由给相应的设备。
    
- **根端口(Root Port)** ：可以理解为根复合体向外提供的物理插槽或逻辑端口。它是CPU访问PCIe设备的必经入口，一个根复合体通常包含多个根端口。
    
- **RCIEP(Root Complex Integrated Endpoint)** ：即根复合体集成端点。这表示某些PCIe设备（如某些板载网卡、NVMe控制器）并没有使用独立的物理插槽，而是直接将控制器集成到了根复合体芯片内部。
    
- **交换机(Switch)** ：作用就是扩展PCIe端口，允许多个设备共享同一组通道。一个标准的交换机包含一个上游端口(Upstream Port)（连接更靠近根复合体的设备，如根端口或上级交换机）和多个下游端口(Downstream Port)（连接终端设备或其他下级交换机）。其内部包含一个交叉开关矩阵(Crossbar)，负责高效地调度和转发不同端口之间的数据。
    
- **端点(Endpoint)** ：它们是PCIe拓扑的“叶子节点”，代表了系统中各种具体的功能性硬件。常见的端点设备包括独立显卡(GPU)、高速固态硬盘控制器(NVMe SSD)、有线/无线网卡、USB 控制器以及各种加速卡等。
    
- **PCI Express Link** ：连接上述所有组件的带双向箭头的实线被称为PCI Express Link(PCIe 链路)。与传统的并行PCI总线不同，PCIe采用的是点对点串行连接，这意味着图中的每一条连线都是一个独立的、全双工的专属通道。
    

## 8.2. PCI子系统整体架构[¶](#id4 "永久链接至标题")

Linux PCI子系统采用分层模块化架构，从硬件底层到用户态共分为四层，实现了硬件适配、资源管理、驱动绑定、数据交互等功能。

### 8.2.1. 硬件适配层[¶](#id5 "永久链接至标题")

该层级是PCI子系统的最底层，直接对接CPU架构与片上PCI控制器硬件，通过平台相关代码对不同架构（X86、ARM64、RISC-V）的PCI控制器在配置读写寄存器、总线扫描方式、中断路由机制、DMA寻址逻辑上存在硬件的差异进行封装屏蔽。

该层级主要实现底层基础硬件操作：包含PCI总线物理扫描、配置空间原生读写、PCI控制器初始化、硬件中断路由配置、DMA物理通道初始化、总线资源物理区间注册等。 该层级不参与设备业务逻辑管理，仅向上层内核核心层提供标准化、统一的硬件操作接口，保证上层无需修改即可适配任意硬件平台。

### 8.2.2. 总线核心管理层[¶](#id6 "永久链接至标题")

该层级是Linux PCI子系统的中枢核心，承载PCI总线与设备的管理，完全由平台无关的通用内核代码实现。 该层级基于内核设备、总线、资源管理模型，构建了标准化的PCI总线拓扑与设备管理体系，维护系统全局PCI总线树、设备链表与硬件资源树。

其核心工作包含：系统启动阶段的逐级总线枚举，递归扫描Root Complex、Bridge、Endpoint设备； 解析设备配置空间，提取厂商ID、设备ID、设备类型、版本信息； 统一分配、校验、仲裁IO端口、物理内存、预取内存三大总线资源，解决多设备资源冲突； 解析PCI/PCIe标准Capability与扩展Capability能力集，识别MSI/MSI-X中断、ASPM电源管理、AER错误上报等高级特性； 统一管理设备电源状态、链路状态、读写异常、TLP传输错误，实现设备容错与状态维护，为上层驱动提供稳定、规范的设备运行环境。

### 8.2.3. 驱动适配层[¶](#id7 "永久链接至标题")

该层级是面向PCI设备驱动开发者的标准化接口层，屏蔽了底层总线枚举、资源分配、硬件读写的复杂细节，将复杂的底层硬件操作封装为通用函数， 开发者无需关注硬件架构、PCI协议底层细节，仅需调用标准API即可完成驱动开发。

该层级提供的核心能力包含：驱动注册与注销机制、设备ID匹配机制、设备使能与禁用管理、配置空间标准读写、BAR物理资源映射与释放、MSI/MSI-X中断配置、DMA寻址掩码配置、设备挂起/唤醒回调适配等。

### 8.2.4. 用户交互层[¶](#id8 "永久链接至标题")

该层级是PCI子系统面向用户态的调试接口，基于Linux sysfs虚拟文件系统实现，是内核态与用户态双向交互的桥梁。 内核在sysfs文件系统中自动生成PCI总线、设备对应的层级目录，将内核维护的设备信息、总线拓扑、资源参数、链路状态等以文件形式暴露给用户态。

用户可通过读写对应sysfs文件，实现设备信息查看、配置空间读取、寄存器调试、设备状态监控、电源模式修改等操作。

## 8.3. PCI子系统核心结构体[¶](#id9 "永久链接至标题")

### 8.3.1. PCI设备描述结构体[¶](#id10 "永久链接至标题")

PCI设备描述结构体（struct pci_dev）用于描述单个PCI设备所有信息的核心结构体，内核每枚举到一个PCI设备，就会创建一个pci_dev实例，存储设备ID、总线号、插槽号、资源信息、中断、电源状态、能力集等全部设备属性，是所有PCI设备操作的基础载体。

pci_dev结构体(内核源码/include/linux/pci.h)[¶](#id74 "永久链接至代码")

```c
 1  struct pci_dev {
 2      // 总线拓扑关联
 3      struct list_head bus_list;     // 设备所在总线链表节点
 4      struct pci_bus  *bus;          // 设备所属PCI总线
 5      struct pci_bus  *subordinate;  // 桥设备向下拓展的子总线
 6
 7      // 设备基础标识信息
 8      unsigned int    devfn;         // 设备号+功能号编码值
 9      unsigned short  vendor;        // 厂商ID
10      unsigned short  device;        // 设备ID
11      unsigned short  subsystem_vendor; // 子系统厂商ID
12      unsigned short  subsystem_device; // 子系统设备ID
13      unsigned int    class;         // 设备类别码（基类/子类/协议）
14      u8              revision;      // 设备版本号
15      u8              hdr_type;      // 设备头类型（普通设备/桥设备）
16
17      // PCIe核心能力偏移
18      u8              pcie_cap;      // PCIe基础能力寄存器偏移
19      u8              msi_cap;       // MSI中断能力偏移
20      u8              msix_cap;      // MSI-X中断能力偏移
21      u8              pm_cap;        // 电源管理能力偏移
22
23      // 设备驱动与DMA配置
24      struct pci_driver *driver;     // 绑定的PCI驱动结构体
25      u64             dma_mask;      // 设备DMA寻址位数掩码
26      struct device_dma_parameters dma_parms; // DMA通用参数
27
28      // 电源管理状态与属性
29      pci_power_t     current_state; // 设备当前电源状态（D0~D3）
30      unsigned int    pme_support:5; // 设备支持的电源唤醒状态
31      unsigned int    d1_support:1;  // 是否支持D1低功耗状态
32      unsigned int    d2_support:1;  // 是否支持D2低功耗状态
33
34      // 链路与异常状态
35      pci_channel_state_t error_state;// 总线链路异常状态
36      struct device   dev;            // 内核通用设备基类
37
38      // 资源与中断信息
39      int             cfg_size;       // 设备配置空间总大小
40      unsigned int    irq;            // 设备绑定的硬件中断号
41      struct resource resource[DEVICE_COUNT_RESOURCE]; // BAR内存/IO资源域
42
43      // 设备功能特性标志位
44      unsigned int    multifunction:1; // 是否为多功能设备
45      unsigned int    is_busmaster:1;  // 是否支持总线主控DMA
46      unsigned int    no_msi:1;        // 是否禁用MSI中断
47      unsigned int    msi_enabled:1;   // MSI中断使能状态
48      unsigned int    msix_enabled:1;  // MSI-X中断使能状态
49      unsigned int    is_probed:1;     // 设备枚举探测状态
50
51      // 同步与锁机制
52      spinlock_t      pcie_cap_lock;   // PCIe能力寄存器读写自旋锁
53      atomic_t        enable_cnt;      // 设备使能引用计数
54
55      // 设备ROM资源
56      phys_addr_t     rom;             // 设备ROM物理地址
57      size_t          romlen;          // 设备ROM空间长度
58
59      const char      *driver_override;// 驱动强制匹配名称
60      unsigned long   priv_flags;      // PCI设备私有状态标志
61
62      /* 其他成员省略 */
63  };
```

### 8.3.2. PCI驱动结构体[¶](#id11 "永久链接至标题")

PCI驱动结构体（struct pci_driver）用于定义PCI设备驱动的回调方法与属性，是驱动注册的核心载体。 开发者通过填充该结构体的回调函数，实现设备探测、移除、挂起、唤醒等功能，内核通过该结构体完成设备与驱动的匹配绑定。

pci_driver结构体(内核源码/include/linux/pci.h)[¶](#id75 "永久链接至代码")

```c
 1  struct pci_driver {
 2      struct list_head node;    // PCI驱动全局链表节点
 3      const char  *name;        // PCI驱动名称
 4      const struct pci_device_id *id_table;  // 设备匹配ID表
 5
 6      // 设备热插入回调：设备匹配成功时执行，完成设备初始化
 7      int  (*probe)(struct pci_dev *dev, const struct pci_device_id *id);
 8      // 设备热拔出回调：设备卸载/拔出时执行，释放设备资源
 9      void (*remove)(struct pci_dev *dev);
10
11      // 系统休眠回调：设备进入挂起低功耗状态
12      int  (*suspend)(struct pci_dev *dev, pm_message_t state);
13      // 系统唤醒回调：设备从休眠状态恢复工作
14      int  (*resume)(struct pci_dev *dev);
15
16      // 系统关机回调：设备关机收尾处理
17      void (*shutdown)(struct pci_dev *dev);
18
19      // SR-IOV虚拟化：配置VF虚拟设备数量
20      int  (*sriov_configure)(struct pci_dev *dev, int num_vfs);
21      // SR-IOV虚拟化：设置VF设备MSI-X中断向量数量
22      int  (*sriov_set_msix_vec_count)(struct pci_dev *vf, int msix_vec_count);
23      // SR-IOV虚拟化：获取PF设备支持的VF总MSI-X向量数
24      u32  (*sriov_get_vf_total_msix)(struct pci_dev *pf);
25
26      const struct pci_error_handlers *err_handler; // PCI设备异常错误处理回调集
27      const struct attribute_group **groups;        // 驱动全局sysfs属性组
28      const struct attribute_group **dev_groups;    // 设备独立sysfs属性组
29
30      struct device_driver driver; // 内核通用设备驱动基类
31      struct pci_dynids dynids;    // 动态设备ID匹配管理结构体
32      bool driver_managed_dma;     // 驱动自主管理DMA资源标志
33  };
```

### 8.3.3. PCI总线结构体[¶](#id12 "永久链接至标题")

PCI总线结构体（struct pci_bus）用于描述PCI总线的整体信息，存储总线编号、总线挂载设备、父级总线、总线资源范围等属性，内核通过该结构体管理整条PCI总线的设备枚举、资源调度与层级关系。

pci_bus结构体(内核源码/include/linux/pci.h)[¶](#id76 "永久链接至代码")

```c
 1  struct pci_bus {
 2      struct list_head node;             // 全局总线链表节点，用于系统所有总线遍历
 3      struct pci_bus  *parent;           // 父总线指针，构建PCI总线层级拓扑
 4      struct list_head children;         // 该总线下属的子总线链表
 5      struct list_head devices;          // 挂载在当前总线的所有PCI设备链表
 6      struct pci_dev  *self;             // 桥设备在父总线中的设备实例
 7
 8      struct list_head slots;            // 总线下物理插槽链表
 9      struct resource *resource[PCI_BRIDGE_RESOURCE_NUM]; // 总线桥IO/内存资源数组
10      struct list_head resources;        // 当前总线管辖的地址空间资源链表
11      struct resource busn_res;          // 当前总线可路由的总线号资源区间
12
13      struct pci_ops  *ops;              // 总线配置空间读写操作函数集
14      unsigned char   number;            // 当前总线唯一编号
15      unsigned char   primary;           // 桥设备主总线编号
16      unsigned char   max_bus_speed;     // 总线支持的最大传输速率
17      unsigned char   cur_bus_speed;     // 总线当前协商运行速率
18
19      unsigned short  bridge_ctl;        // 桥设备控制寄存器参数，管理总线兼容行为
20      pci_bus_flags_t bus_flags;         // 总线状态标志，可被子总线继承
21      struct device   *bridge;           // 关联的总线桥设备结构体
22      struct device   dev;               // 内核通用设备模型基类
23
24      unsigned int    is_added:1;        // 总线是否已完成初始化添加标记
25      unsigned int    unsafe_warn:1;     // 配置空间非法读写警告标记
26
27      /* 其他成员省略 */
28  };
```

### 8.3.4. PCI设备匹配ID结构体[¶](#pciid "永久链接至标题")

设备匹配ID结构体（struct pci_device_id）用于定义驱动支持的PCI设备ID列表，内核根据该结构体的厂商ID、设备ID，将枚举到的硬件设备与驱动精准匹配，匹配成功后触发probe初始化函数。

pci_device_id结构体(内核源码/include/linux/mod_devicetable.h)[¶](#id77 "永久链接至代码")

```c
struct pci_device_id {
    __u32 vendor, device;       // 设备厂商ID、设备ID，支持PCI_ANY_ID通配
    __u32 subvendor, subdevice; // 子系统厂商ID、子系统设备ID，支持PCI_ANY_ID通配
    __u32 class, class_mask;    // 设备类别码、类别掩码，用于匹配同类设备
    kernel_ulong_t driver_data; // 驱动自定义私有数据，匹配后可传递给probe
    __u32 override_only;        // 仅驱动强制匹配时生效，限定仅覆盖匹配模式
};
```

- PCI_ANY_ID：代表不限制匹配该字段，任意设备数值均可通过匹配。
    

### 8.3.5. PCI底层硬件操作结构体[¶](#id13 "永久链接至标题")

PCI底层硬件操作结构体（struct pci_ops）封装了不同CPU架构、不同PCI控制器的配置空间读写硬件接口，屏蔽X86、ARM64、RISC-V等平台的硬件差异。 所有PCI设备配置空间读写API，最终都会调用pci_ops的底层方法。

pci_ops结构体(内核源码/include/linux/pci.h)[¶](#id78 "永久链接至代码")

```c
 1  struct pci_ops {
 2      // 总线注册回调：完成PCI总线硬件层初始化与注册
 3      int (*add_bus)(struct pci_bus *bus);
 4      // 总线移除回调：销毁PCI总线、释放底层硬件资源
 5      void (*remove_bus)(struct pci_bus *bus);
 6      // 总线地址映射：将总线配置空间偏移映射为内核虚拟地址
 7      void __iomem *(*map_bus)(struct pci_bus *bus, unsigned int devfn, int where);
 8      // 配置空间通用读接口：支持1/2/4字节读取设备配置寄存器
 9      int (*read)(struct pci_bus *bus, unsigned int devfn, int where, int size, u32 *val);
10      // 配置空间通用写接口：支持1/2/4字节写入设备配置寄存器
11      int (*write)(struct pci_bus *bus, unsigned int devfn, int where, int size, u32 val);
12  };
```

## 8.4. PCI子系统核心函数[¶](#id14 "永久链接至标题")

### 8.4.1. 驱动注册与注销[¶](#id15 "永久链接至标题")

#### 8.4.1.1. pci_register_driver函数[¶](#pci-register-driver "永久链接至标题")

pci_register_driver函数用于向内核PCI子系统注册自定义PCI驱动，注册成功后内核可根据ID表匹配对应设备。

函数原型：

```c
int pci_register_driver(struct pci_driver *drv);
```

参数说明：

- drv：自定义填充的pci_driver驱动结构体指针。
    

返回值：成功返回0，失败返回负的错误码。

#### 8.4.1.2. pci_unregister_driver函数[¶](#pci-unregister-driver "永久链接至标题")

pci_unregister_driver函数用于注销已注册的PCI驱动，释放驱动内核资源，卸载设备驱动。

函数原型：

```c
void pci_unregister_driver(struct pci_driver *drv);
```

参数说明：

- drv：待注销的PCI驱动结构体指针。
    

### 8.4.2. 设备启停[¶](#id16 "永久链接至标题")

#### 8.4.2.1. pci_enable_device函数[¶](#pci-enable-device "永久链接至标题")

pci_enable_device函数是通用PCI设备使能函数，用于初始化PCI设备、解锁设备IO空间与内存空间解码权限，激活设备基础工作能力，是绝大多数PCI设备初始化的第一步。 该函数会自动检测设备资源类型，同时使能IO端口和MMIO内存资源，适配传统PCI设备与普通PCIe设备。

函数原型：

```c
int pci_enable_device(struct pci_dev *dev);
```

参数说明：

- dev：目标PCI设备结构体指针。
    

返回值：成功返回0，失败返回负错误码。

#### 8.4.2.2. pci_enable_device_mem函数[¶](#pci-enable-device-mem "永久链接至标题")

pci_enable_device_mem专门使能PCI设备的内存资源空间，仅开启设备MMIO寄存器访问能力，不启用IO端口资源，适配无IO资源的标准PCIe设备，可规避无效IO资源检测，提升初始化效率。

函数原型：

```c
int pci_enable_device_mem(struct pci_dev *dev);
```

参数说明：

- dev：目标PCI设备结构体指针。
    

返回值：成功返回0，失败返回负错误码。

#### 8.4.2.3. pci_disable_device函数[¶](#pci-disable-device "永久链接至标题")

pci_disable_device函数与pci_enable_device_mem成对使用，用于禁用PCI设备的IO、内存解码功能，关闭设备总线主控能力，释放设备硬件占用资源，防止设备离线后非法访问总线。

函数原型：

```c
void pci_disable_device(struct pci_dev *dev);
```

参数说明：

- dev：目标PCI设备结构体指针。
    

### 8.4.3. 配置空间读写[¶](#id17 "永久链接至标题")

#### 8.4.3.1. pci_read_config_byte函数[¶](#pci-read-config-byte "永久链接至标题")

pci_read_config_byte函数用于从PCI设备配置空间指定偏移读取1字节数据。

函数原型：

```c
int pci_read_config_byte(struct pci_dev *dev, int where, u8 *val);
```

参数说明：

- dev：目标PCI设备结构体指针；
    
- where：配置空间寄存器偏移地址；
    
- val：接收读取数据的8位缓存指针。
    

返回值：读取成功返回0，读取失败返回负的错误码。

#### 8.4.3.2. pci_write_config_byte函数[¶](#pci-write-config-byte "永久链接至标题")

pci_write_config_byte函数用于向PCI设备配置空间指定偏移写入1字节数据。

函数原型：

```c
int pci_write_config_byte(struct pci_dev *dev, int where, u8 val);
```

参数说明：

- dev：目标PCI设备结构体指针；
    
- where：配置空间寄存器偏移地址；
    
- val：待写入的8位单字节数据。
    

返回值：写入成功返回0，写入失败返回负的错误码。

#### 8.4.3.3. pci_read_config_word函数[¶](#pci-read-config-word "永久链接至标题")

pci_read_config_word函数用于从PCI设备配置空间指定偏移读取2字节数据。

函数原型：

```c
int pci_read_config_word(struct pci_dev *dev, int where, u16 *val);
```

参数说明：

- dev：目标PCI设备结构体指针；
    
- where：配置空间寄存器偏移地址；
    
- val：接收读取数据的16位缓存指针。
    

返回值：读取成功返回0，读取失败返回负的错误码。

#### 8.4.3.4. pci_write_config_word函数[¶](#pci-write-config-word "永久链接至标题")

pci_write_config_word函数用于向PCI设备配置空间指定偏移写入2字节数据。

函数原型：

```c
int pci_write_config_word(struct pci_dev *dev, int where, u16 val);
```

参数说明：

- dev：目标PCI设备结构体指针；
    
- where：配置空间寄存器偏移地址；
    
- val：待写入的16位双字节数据。
    

返回值：写入成功返回0，写入失败返回负的错误码。

#### 8.4.3.5. pci_read_config_dword函数[¶](#pci-read-config-dword "永久链接至标题")

pci_read_config_dword函数用于从PCI设备配置空间指定偏移读取4字节数据。

函数原型：

```c
int pci_read_config_dword(struct pci_dev *dev, int where, u32 *val);
```

参数说明：

- dev：目标PCI设备结构体指针；
    
- where：配置空间寄存器偏移地址；
    
- val：接收读取数据的32位缓存指针。
    

返回值：成功返回0，失败返回负错误码。

#### 8.4.3.6. pci_write_config_dword函数[¶](#pci-write-config-dword "永久链接至标题")

pci_write_config_dword函数用于向PCI设备配置空间指定偏移写入4字节数据。

函数原型：

```c
int pci_write_config_dword(struct pci_dev *dev, int where, u32 val);
```

参数说明：

- dev：目标PCI设备结构体指针；
    
- where：配置空间寄存器偏移地址；
    
- val：待写入的32位4字节数据。
    

### 8.4.4. BAR资源信息读取[¶](#id18 "永久链接至标题")

#### 8.4.4.1. pci_resource_start函数[¶](#pci-resource-start "永久链接至标题")

pci_resource_start函数用于获取指定BAR寄存器对应的物理起始地址，是BAR空间映射、寄存器读写的前置查询函数。

函数原型：

```c
resource_size_t pci_resource_start(struct pci_dev *dev, int bar);
```

参数说明：

- dev：目标PCI设备结构体指针；
    
- bar：需要查询的BAR寄存器编号。
    

返回值：返回对应BAR资源的物理起始地址；若该BAR资源未分配或无效，返回0。

#### 8.4.4.2. pci_resource_len函数[¶](#pci-resource-len "永久链接至标题")

pci_resource_len函数用于获取指定BAR寄存器对应的资源空间总长度，用于判定BAR映射最大合法范围，防止越界访问。

函数原型：

```c
resource_size_t pci_resource_len(struct pci_dev *dev, int bar);
```

参数说明：

- dev：目标PCI设备结构体指针；
    
- bar：BAR寄存器编号。
    

返回值：返回对应BAR资源的空间字节长度；资源无效则返回0。

#### 8.4.4.3. pci_resource_flags函数[¶](#pci-resource-flags "永久链接至标题")

pci_resource_flags函数用于获取BAR资源属性标志，用于区分IO空间/非预取内存空间/预取内存空间，是BAR映射类型判断、硬件访问方式选择的依据。

函数原型：

```c
unsigned long pci_resource_flags(struct pci_dev *dev, int bar);
```

参数说明：

- dev：目标PCI设备结构体指针；
    
- bar：BAR寄存器编号。
    

返回值：返回资源属性标志位，包含IORESOURCE_IO、IORESOURCE_MEM、IORESOURCE_PREFETCH等核心标识，用于判别资源类型与特性。

#### 8.4.4.4. pci_request_regions函数[¶](#pci-request-regions "永久链接至标题")

pci_request_regions函数用于用于向内核正式申请占用设备所有BAR对应的IO端口、物理内存资源，标记资源为已占用状态，避免多设备、多驱动抢占同一硬件资源导致的冲突问题。

函数原型：

```c
int pci_request_regions(struct pci_dev *dev, const char *res_name);
```

参数说明：

- dev：目标PCI设备结构体指针；
    
- res_name为资源占用标识名称，一般传入驱动名称，用于内核资源树标识与故障排查。
    

返回值：资源申请成功返回0；资源已被占用、资源无效、申请失败均返回负错误码。

### 8.4.5. BAR空间映射[¶](#id19 "永久链接至标题")

#### 8.4.5.1. pci_iomap函数[¶](#pci-iomap "永久链接至标题")

pci_iomap函数用于将PCI设备BAR物理地址映射为内核虚拟地址，映射后驱动可直接通过虚拟地址读写设备寄存器。

函数原型：

```c
void __iomem *pci_iomap(struct pci_dev *dev, int bar, size_t maxlen);
```

参数说明：

- dev：目标PCI设备结构体指针；
    
- bar：BAR编号；
    
- maxlen为映射长度。
    

返回值：成功返回内核虚拟地址指针，失败返回NULL。

#### 8.4.5.2. pci_iounmap函数[¶](#pci-iounmap "永久链接至标题")

pci_iounmap函数与pci_iomap成对配套使用，用于解除PCI设备BAR空间的物理地址与内核虚拟地址映射，释放IO虚拟地址资源。

函数原型：

```c
void pci_iounmap(struct pci_dev *dev, void __iomem *addr);
```

参数说明：

- dev：目标PCI设备结构体指针；
    
- addr：pci_iomap映射成功返回的内核虚拟地址指针。
    

### 8.4.6. 设备私有数据管理[¶](#id20 "永久链接至标题")

#### 8.4.6.1. pci_set_drvdata函数[¶](#pci-set-drvdata "永久链接至标题")

pci_set_drvdata函数用于将自定义私有数据结构体绑定到pci_dev设备，实现设备与私有资源绑定。

函数原型：

```c
void pci_set_drvdata(struct pci_dev *dev, void *data);
```

参数说明：

- dev：目标PCI设备结构体指针；
    
- data：用户自定义的设备私有数据结构体指针。
    

#### 8.4.6.2. pci_get_drvdata函数[¶](#pci-get-drvdata "永久链接至标题")

pci_get_drvdata函数用于从PCI设备结构体中取出预先绑定的私有数据。

函数原型：

```c
void *pci_get_drvdata(struct pci_dev *dev);
```

参数说明：

- dev：目标PCI设备结构体指针。
    

返回值：成功返回设备绑定的私有数据指针；未绑定数据则返回NULL。

### 8.4.7. PCI能力集解析[¶](#id21 "永久链接至标题")

#### 8.4.7.1. pci_find_capability函数[¶](#pci-find-capability "永久链接至标题")

pci_find_capability函数用于遍历PCI设备标准Capability能力链表，获取指定基础能力寄存器的偏移地址，用于解析PM电源管理、MSI中断、基础PCIe特性等标准能力。

函数原型：

```c
u8 pci_find_capability(struct pci_dev *dev, int cap);
```

参数说明：

- dev：目标PCI设备结构体指针；
    
- cap：待查询的标准能力宏定义（如PCI_CAP_ID_MSI、PCI_CAP_ID_PM）。
    

返回值：成功返回对应能力寄存器的配置空间偏移地址；设备不支持该能力则返回0。

#### 8.4.7.2. pci_find_ext_capability函数[¶](#pci-find-ext-capability "永久链接至标题")

pci_find_ext_capability函数用于遍历PCIe扩展Capability能力链表，专门用于查询PCIe专属高级扩展能力，如AER高级错误上报、SR-IOV虚拟化、DPC动态端口控制、LTR延迟容忍等特性。

函数原型：

```c
u16 pci_find_ext_capability(struct pci_dev *dev, int cap);
```

参数说明：

- dev：目标PCI设备结构体指针；
    
- cap：待查询的扩展能力宏定义（如PCI_EXT_CAP_ID_AER、PCI_EXT_CAP_ID_SRIOV）。
    

返回值：成功返回对应扩展能力寄存器的偏移地址；设备无该扩展能力则返回0。

### 8.4.8. DMA总线主控控制[¶](#dma "永久链接至标题")

#### 8.4.8.1. pci_set_master函数[¶](#pci-set-master "永久链接至标题")

pci_set_master函数用于置位PCI设备命令寄存器的总线主控位，开启设备DMA总线主控权限，允许设备不经过CPU直接访问系统内存，是网卡、SSD、GPU等高速外设初始化的核心函数。

函数原型：

```c
void pci_set_master(struct pci_dev *dev);
```

参数说明：

- dev：目标PCI设备结构体指针。
    

#### 8.4.8.2. pci_clear_master函数[¶](#pci-clear-master "永久链接至标题")

pci_clear_master函数用于清除设备总线主控标志位，禁用设备DMA主动传输能力，阻止设备直接访问系统内存，驱动卸载阶段必须调用，防止设备离线后非法DMA访问导致系统异常。

函数原型：

```c
void pci_clear_master(struct pci_dev *dev);
```

参数说明：

- dev：目标PCI设备结构体指针。
    

### 8.4.9. 设备电源状态管理[¶](#id22 "永久链接至标题")

#### 8.4.9.1. pci_save_state函数[¶](#pci-save-state "永久链接至标题")

pci_save_state函数用于保存PCI设备当前完整硬件状态，包含配置空间寄存器、链路参数、电源状态、中断配置等信息，系统设备休眠前调用，用于唤醒后还原设备状态。

函数原型：

```c
int pci_save_state(struct pci_dev *dev);
```

参数说明：

- dev：目标PCI设备结构体指针。
    

返回值：状态保存成功返回0，保存失败返回负错误码。

#### 8.4.9.2. pci_restore_state函数[¶](#pci-restore-state "永久链接至标题")

pci_restore_state函数用于读取并还原pci_save_state保存的设备硬件状态，在系统设备唤醒、故障复位恢复后调用，保证设备恢复至休眠或异常前的正常工作状态。

函数原型：

```c
void pci_restore_state(struct pci_dev *dev);
```

参数说明：

- dev：目标PCI设备结构体指针。
    

## 8.5. 内核PCIE网卡驱动源码解析[¶](#id23 "永久链接至标题")

以RTL8822CE网卡驱动进行说明，只分析PCI子系统相关内容，复杂的网络协议等内容不作说明。

以下选取 **瑞芯微6.1.99内核版本** 的相关驱动进行说明：

- 内核源码/drivers/net/wireless/realtek/rtw88/pci.c
    
- 内核源码/drivers/net/wireless/realtek/rtw88/rtw8822c.c
    
- 内核源码/drivers/net/wireless/realtek/rtw88/rtw8822ce.c
    

### 8.5.1. 设备识别与驱动注册[¶](#id24 "永久链接至标题")

**PCI设备ID表**

当系统检测到PCI总线上有vendor=Realtek、device=0xC822或0xC82F的设备时，内核会自动将rtw8822ce驱动与之匹配。

PCI设备ID表(位于内核源码/drivers/net/wireless/realtek/rtw88/rtw8822ce.c)[¶](#id79 "永久链接至代码")

```c
 1  /* PCI设备ID匹配表 */
 2  static const struct pci_device_id rtw_8822ce_id_table[] = {
 3      {
 4          /* 匹配厂商ID Realtek + 设备ID 0xC822 */
 5          PCI_DEVICE(PCI_VENDOR_ID_REALTEK, 0xC822),
 6          .driver_data = (kernel_ulong_t)&rtw8822c_hw_spec
 7      },
 8      {
 9          /* 匹配厂商ID Realtek + 设备ID 0xC82F */
10          PCI_DEVICE(PCI_VENDOR_ID_REALTEK, 0xC82F),
11          .driver_data = (kernel_ulong_t)&rtw8822c_hw_spec
12      },
13      {}
14  };
15  /* 生成MODULE_DEVICE_TABLE宏，供用户态工具（如udev/modprobe）自动加载模块 */
16  MODULE_DEVICE_TABLE(pci, rtw_8822ce_id_table);
```

driver_data携带了芯片描述结构体rtw8822c_hw_spec，该结构体定义了芯片的寄存器表、Firmware名称、各种硬件能力参数等，probe时通过id->driver_data获取。

**PCI驱动结构体**

PCI驱动结构体的probe/remove/shutdown/pm四个回调覆盖了PCI设备的完整生命周期。

PCI驱动结构体(位于内核源码/drivers/net/wireless/realtek/rtw88/rtw8822ce.c)[¶](#id80 "永久链接至代码")

```c
static struct pci_driver rtw_8822ce_driver = {
    .name    = "rtw_8822ce",          /* 驱动名称 */
    .id_table = rtw_8822ce_id_table,  /* 指向上面的设备匹配表 */
    .probe   = rtw_pci_probe,         /* 设备匹配成功后的初始化入口，定义在pci.c */
    .remove  = rtw_pci_remove,        /* 设备移除时的清理入口 */
    .driver.pm = &rtw_pm_ops,         /* 电源管理操作 */
    .shutdown = rtw_pci_shutdown,     /* 系统关机时的回调 */
};

module_pci_driver(rtw_8822ce_driver);
```

所有实际处理都通过pci.c中的通用PCI层函数，实现芯片型号与PCI总线层的分离，因此rtw88目录下存在的多款PCIe网卡独立驱动文件仅仅用来设备与驱动匹配。

### 8.5.2. Probe流程[¶](#probe "永久链接至标题")

**probe函数**

实际probe函数位于pci.c，是PCI驱动最核心的函数。

probe函数(位于内核源码/drivers/net/wireless/realtek/rtw88/pci.c)[¶](#id81 "永久链接至代码")

```c
 1  int rtw_pci_probe(struct pci_dev *pdev,
 2                  const struct pci_device_id *id)
 3  {
 4      struct pci_dev *bridge = pci_upstream_bridge(pdev); /* 获取上游桥设备，用于兼容性判断 */
 5      struct ieee80211_hw *hw;
 6      struct rtw_dev *rtwdev;
 7      struct rtw_pci *rtwpci;
 8      int drv_data_size;
 9      int ret;
10
11      /* 分配驱动私有数据大小：rtw_dev + rtw_pci */
12      drv_data_size = sizeof(struct rtw_dev) + sizeof(struct rtw_pci);
13
14      /* 分配ieee80211_hw结构体及驱动私有空间 */
15      hw = ieee80211_alloc_hw(drv_data_size, &rtw_ops);
16      if (!hw) {
17          dev_err(&pdev->dev, "failed to allocate hw\n");
18          return -ENOMEM;
19      }
20
21      rtwdev = hw->priv;
22      rtwdev->hw = hw;
23      rtwdev->dev = &pdev->dev;
24      /* 从设备ID表的driver_data取出芯片描述（rtw8822c_hw_spec） */
25      rtwdev->chip = (struct rtw_chip_info *)id->driver_data;
26      rtwdev->hci.ops = &rtw_pci_ops;       /* 挂载PCI总线操作函数集 */
27      rtwdev->hci.type = RTW_HCI_TYPE_PCIE; /* 标记主机接口类型为PCIe */
28
29      rtwpci = (struct rtw_pci *)rtwdev->priv;
30      atomic_set(&rtwpci->link_usage, 1);   /* 链路使用计数初始化为1 */
31
32      /* 核心子系统初始化，非PCI部分，略 */
33      ret = rtw_core_init(rtwdev);
34      if (ret)
35          goto err_release_hw;
36
37      /* ===== PCI资源申请阶段 ===== */
38
39      /* 步骤1：使能PCI设备、设置总线主控 */
40      ret = rtw_pci_claim(rtwdev, pdev);
41      if (ret)
42          goto err_deinit_core;
43
44      /* 步骤2：IO内存映射 + DMA环初始化 */
45      ret = rtw_pci_setup_resource(rtwdev, pdev);
46      if (ret)
47          goto err_pci_declaim;
48
49      /* 步骤3：NAPI初始化，用于RX轮询，属于网络层，略 */
50      ret = rtw_pci_napi_init(rtwdev);
51      if (ret)
52          goto err_pci_declaim;
53
54      /* 步骤4：芯片信息探测，读取efuse、加载firmware等 */
55      ret = rtw_chip_info_setup(rtwdev);
56      if (ret)
57          goto err_destroy_pci;
58
59      /* 兼容性处理：8821CE + Intel桥时禁用NAPI期间的ASPM L1 */
60      if (rtwdev->chip->id == RTW_CHIP_TYPE_8821C &&
61          bridge->vendor == PCI_VENDOR_ID_INTEL)
62          rtwpci->rx_no_aspm = true;
63
64      /* 步骤5：PCIe PHY层配置，CLKREQ/ASPM等 */
65      rtw_pci_phy_cfg(rtwdev);
66
67      /* 步骤6：注册到mac80211，网络层，略 */
68      ret = rtw_register_hw(rtwdev, hw);
69      if (ret)
70          goto err_destroy_pci;
71
72      /* 步骤7：申请PCI中断 */
73      ret = rtw_pci_request_irq(rtwdev, pdev);
74      if (ret) {
75          ieee80211_unregister_hw(hw);
76          goto err_destroy_pci;
77      }
78
79      return 0;
80
81  /* 错误回退标签 */
82  err_destroy_pci:
83      rtw_pci_napi_deinit(rtwdev);
84      rtw_pci_destroy(rtwdev, pdev);
85  err_pci_declaim:
86      rtw_pci_declaim(rtwdev, pdev);
87  err_deinit_core:
88      rtw_core_deinit(rtwdev);
89  err_release_hw:
90      ieee80211_free_hw(hw);
91      return ret;
92  }
```

**PCI设备使能**

rtw_pci_claim函数(位于内核源码/drivers/net/wireless/realtek/rtw88/pci.c)[¶](#id82 "永久链接至代码")

```c
 1  static int rtw_pci_claim(struct rtw_dev *rtwdev, struct pci_dev *pdev)
 2  {
 3      int ret;
 4
 5      /* 使能PCI设备：分配MMIO/IO资源、使能BAR解码 */
 6      ret = pci_enable_device(pdev);
 7      if (ret) {
 8          rtw_err(rtwdev, "failed to enable pci device\n");
 9          return ret;
10      }
11
12      /* 设置总线主控位，允许设备发起DMA传输 */
13      pci_set_master(pdev);
14
15      /* 将hw指针存入pci_dev->driver_data，供remove/shutdown取回 */
16      pci_set_drvdata(pdev, rtwdev->hw);
17
18      /* 将PCI设备关联到ieee80211设备树 */
19      SET_IEEE80211_DEV(rtwdev->hw, &pdev->dev);
20      return 0;
21  }
```

pci_enable_device()是PCI设备使用的前提，它使能BAR空间解码；pci_set_master()设置PCI命令寄存器的Bus Master位，不开启则无法进行DMA。

**IO内存映射**

probe函数中调用的rtw_pci_setup_resource进行IO内存映射+DMA环初始化，其中IO内存映射实际调用的是rtw_pci_io_mapping函数。

rtw_pci_io_mapping函数(位于内核源码/drivers/net/wireless/realtek/rtw88/pci.c)[¶](#id83 "永久链接至代码")

```c
 1  static int rtw_pci_io_mapping(struct rtw_dev *rtwdev,
 2                              struct pci_dev *pdev)
 3  {
 4      struct rtw_pci *rtwpci = (struct rtw_pci *)rtwdev->priv;
 5      unsigned long len;
 6      u8 bar_id = 2;  /* 使用BAR2作为寄存器访问空间 */
 7      int ret;
 8
 9      /* 向内核申请该PCI设备的IO区域 */
10      ret = pci_request_regions(pdev, KBUILD_MODNAME);
11      if (ret) {
12          rtw_err(rtwdev, "failed to request pci regions\n");
13          return ret;
14      }
15
16      /* 获取BAR2的长度 */
17      len = pci_resource_len(pdev, bar_id);
18
19      /* 将物理地址映射为内核虚拟地址，后续所有寄存器读写都通过此指针 */
20      rtwpci->mmap = pci_iomap(pdev, bar_id, len);
21      if (!rtwpci->mmap) {
22          pci_release_regions(pdev);
23          rtw_err(rtwdev, "failed to map pci memory\n");
24          return -ENOMEM;
25      }
26      return 0;
27  }
```

PCI设备通过BAR暴露寄存器空间，rtl网卡使用其中的BAR2；pci_iomap()将其映射到内核虚拟地址空间，之后所有readl/writel操作都基于rtwpci->mmap偏移。

**寄存器读写封装**

这是所有芯片寄存器访问的最底层。

rtw_pci_read32/rtw_pci_write32函数(位于内核源码/drivers/net/wireless/realtek/rtw88/pci.c)[¶](#id84 "永久链接至代码")

```c
 1  /* 读取32位寄存器：基地址mmap + 偏移addr */
 2  static u32 rtw_pci_read32(struct rtw_dev *rtwdev, u32 addr)
 3  {
 4      struct rtw_pci *rtwpci = (struct rtw_pci *)rtwdev->priv;
 5      return readl(rtwpci->mmap + addr);  /* MMIO读 */
 6  }
 7
 8  /* 写入32位寄存器：基地址mmap + 偏移addr + 数据val*/
 9  static void rtw_pci_write32(struct rtw_dev *rtwdev, u32 addr, u32 val)
10  {
11      struct rtw_pci *rtwpci = (struct rtw_pci *)rtwdev->priv;
12      writel(val, rtwpci->mmap + addr);   /* MMIO写 */
13  }
14  /* 类似还有read8/write8、read16/write16 */
```

### 8.5.3. DMA环管理[¶](#id25 "永久链接至标题")

**TX/RX环初始化**

probe函数中调用的rtw_pci_setup_resource进行IO内存映射+DMA环初始化，其中DMA环初始化实际调用的是rtw_pci_init_tx_ring和rtw_pci_init_rx_ring函数。

其中rtw_pci_init_tx_ring用于TX环初始化，rtw_pci_init_rx_ring用于RX环初始化。

TX/RX环初始化(位于内核源码/drivers/net/wireless/realtek/rtw88/pci.c)[¶](#id85 "永久链接至代码")

```c
 1  /* TX环初始化 */
 2  static int rtw_pci_init_tx_ring(struct rtw_dev *rtwdev,
 3                                  struct rtw_pci_tx_ring *tx_ring,
 4                                  u8 desc_size, u32 len)
 5  {
 6      struct pci_dev *pdev = to_pci_dev(rtwdev->dev);
 7      int ring_sz = desc_size * len;  /* 环总大小 = 描述符大小 * 描述符个数 */
 8      dma_addr_t dma;
 9      u8 *head;
10
11      if (len > TRX_BD_IDX_MASK) {  /* 检查描述符数量不超过硬件索引位宽 */
12          rtw_err(rtwdev, "len %d exceeds maximum TX entries\n", len);
13          return -EINVAL;
14      }
15
16      /* 分配描述符环的一致性DMA内存 */
17      head = dma_alloc_coherent(&pdev->dev, ring_sz, &dma, GFP_KERNEL);
18      if (!head) {
19          rtw_err(rtwdev, "failed to allocate tx ring\n");
20          return -ENOMEM;
21      }
22
23      skb_queue_head_init(&tx_ring->queue);  /* 初始化待发送skb队列 */
24      tx_ring->r.head = head;       /* 环虚拟地址 */
25      tx_ring->r.dma = dma;         /* 环物理地址 */
26      tx_ring->r.len = len;         /* 描述符总数 */
27      tx_ring->r.desc_size = desc_size;
28      tx_ring->r.wp = 0;            /* 写指针 */
29      tx_ring->r.rp = 0;            /* 读指针 */
30      return 0;
31  }
32
33  /* RX环初始化 */
34  static int rtw_pci_init_rx_ring(struct rtw_dev *rtwdev,
35                                  struct rtw_pci_rx_ring *rx_ring,
36                                  u8 desc_size, u32 len)
37  {
38      struct pci_dev *pdev = to_pci_dev(rtwdev->dev);
39      struct sk_buff *skb = NULL;
40      dma_addr_t dma;
41      u8 *head;
42      int ring_sz = desc_size * len;
43      int buf_sz = RTK_PCI_RX_BUF_SIZE;  /* 每个接收缓冲区大小 */
44      int i, allocated;
45      int ret = 0;
46
47      /* 分配描述符环的一致性DMA内存 */
48      head = dma_alloc_coherent(&pdev->dev, ring_sz, &dma, GFP_KERNEL);
49      if (!head) {
50          rtw_err(rtwdev, "failed to allocate rx ring\n");
51          return -ENOMEM;
52      }
53      rx_ring->r.head = head;
54
55      /* 为每个描述符预分配一个skb作为接收缓冲区 */
56      for (i = 0; i < len; i++) {
57          skb = dev_alloc_skb(buf_sz);
58          if (!skb) {
59              allocated = i;
60              ret = -ENOMEM;
61              goto err_out;
62          }
63          memset(skb->data, 0, buf_sz);
64          rx_ring->buf[i] = skb;
65
66          /* 将skb映射为DMA地址，写入描述符 */
67          ret = rtw_pci_reset_rx_desc(rtwdev, skb, rx_ring, i, desc_size);
68          if (ret) {
69              allocated = i;
70              dev_kfree_skb_any(skb);
71              goto err_out;
72          }
73      }
74
75      rx_ring->r.dma = dma;
76      rx_ring->r.len = len;
77      rx_ring->r.desc_size = desc_size;
78      rx_ring->r.wp = 0;
79      rx_ring->r.rp = 0;
80      return 0;
81
82  err_out:
83      /* 释放已分配的skb和DMA映射 */
84      for (i = 0; i < allocated; i++) {
85          skb = rx_ring->buf[i];
86          if (!skb)
87              continue;
88          dma = *((dma_addr_t *)skb->cb);
89          dma_unmap_single(&pdev->dev, dma, buf_sz, DMA_FROM_DEVICE);
90          dev_kfree_skb_any(skb);
91          rx_ring->buf[i] = NULL;
92      }
93      dma_free_coherent(&pdev->dev, ring_sz, head, dma);
94      rtw_err(rtwdev, "failed to init rx buffer\n");
95      return ret;
96  }
```

TX/RX环是PCI网卡DMA传输的核心数据结构。描述符环本身使用dma_alloc_coherent()分配一致性内存，数据缓冲区使用dma_map_single()映射流式DMA。 TX方向是DMA_TO_DEVICE，RX方向是DMA_FROM_DEVICE。

### 8.5.4. 中断管理[¶](#id26 "永久链接至标题")

**中断申请与处理**

该部分分为PCI中断申请（rtw_pci_request_irq函数），硬中断处理（rtw_pci_interrupt_handler函数，上半部），中断线程处理（rtw_pci_interrupt_threadfn函数，下半部）。

TX/RX环初始化(位于内核源码/drivers/net/wireless/realtek/rtw88/pci.c)[¶](#id86 "永久链接至代码")

```c
 1  /* PCI中断申请 */
 2  static int rtw_pci_request_irq(struct rtw_dev *rtwdev, struct pci_dev *pdev)
 3  {
 4  #if (LINUX_VERSION_CODE >= KERNEL_VERSION(6, 10, 0))
 5      unsigned int flags = PCI_IRQ_INTX;   /* 新内核用PCI_IRQ_INTX */
 6  #else
 7      unsigned int flags = PCI_IRQ_LEGACY; /* 旧内核用PCI_IRQ_LEGACY */
 8  #endif
 9      int ret;
10
11      /* 如果未通过模块参数禁用MSI，则优先使用MSI */
12      if (!rtw_disable_msi)
13          flags |= PCI_IRQ_MSI;
14
15      /* 申请1个中断向量，MSI或回退到INTx */
16      ret = pci_alloc_irq_vectors(pdev, 1, 1, flags);
17      if (ret < 0) {
18          rtw_err(rtwdev, "failed to alloc PCI irq vectors\n");
19          return ret;
20      }
21
22      /* 注册线程化中断：
23      * - 硬中断处理函数：rtw_pci_interrupt_handler
24      * - 中断线程处理函数：rtw_pci_interrupt_threadfn
25      * IRQF_SHARED：允许共享中断线，INTx模式下可能需要 */
26      ret = devm_request_threaded_irq(rtwdev->dev, pdev->irq,
27                                      rtw_pci_interrupt_handler,
28                                      rtw_pci_interrupt_threadfn,
29                                      IRQF_SHARED, KBUILD_MODNAME, rtwdev);
30      if (ret) {
31          rtw_err(rtwdev, "failed to request irq %d\n", ret);
32          pci_free_irq_vectors(pdev);
33      }
34      return ret;
35  }
36
37  /* 硬中断处理函数 */
38  static irqreturn_t rtw_pci_interrupt_handler(int irq, void *dev)
39  {
40      struct rtw_dev *rtwdev = dev;
41      struct rtw_pci *rtwpci = (struct rtw_pci *)rtwdev->priv;
42
43      /* 立即禁用PCI中断，防止在线程处理完成前产生新中断 */
44      rtw_pci_disable_interrupt(rtwdev, rtwpci);
45
46      /* 唤醒中断线程执行实际处理 */
47      return IRQ_WAKE_THREAD;
48  }
49
50  /* 中断线程处理函数 */
51  static irqreturn_t rtw_pci_interrupt_threadfn(int irq, void *dev)
52  {
53      struct rtw_dev *rtwdev = dev;
54      struct rtw_pci *rtwpci = (struct rtw_pci *)rtwdev->priv;
55      u32 irq_status[4];
56      bool rx = false;
57
58      spin_lock_bh(&rtwpci->irq_lock);
59
60      /* 读取并清除中断状态寄存器 */
61      rtw_pci_irq_recognized(rtwdev, rtwpci, irq_status);
62
63      /* 根据中断状态分发到各TX队列的ISR */
64      if (irq_status[0] & IMR_MGNTDOK)   /* 管理队列发送完成 */
65          rtw_pci_tx_isr(rtwdev, rtwpci, RTW_TX_QUEUE_MGMT);
66      if (irq_status[0] & IMR_HIGHDOK)   /* 高优先级队列发送完成 */
67          rtw_pci_tx_isr(rtwdev, rtwpci, RTW_TX_QUEUE_HI0);
68      if (irq_status[0] & IMR_BEDOK)     /* Best Effort队列发送完成 */
69          rtw_pci_tx_isr(rtwdev, rtwpci, RTW_TX_QUEUE_BE);
70      if (irq_status[0] & IMR_BKDOK)     /* Background队列发送完成 */
71          rtw_pci_tx_isr(rtwdev, rtwpci, RTW_TX_QUEUE_BK);
72      if (irq_status[0] & IMR_VODOK)     /* Voice队列发送完成 */
73          rtw_pci_tx_isr(rtwdev, rtwpci, RTW_TX_QUEUE_VO);
74      if (irq_status[0] & IMR_VIDOK)     /* Video队列发送完成 */
75          rtw_pci_tx_isr(rtwdev, rtwpci, RTW_TX_QUEUE_VI);
76      if (irq_status[3] & IMR_H2CDOK)    /* H2C（Host-to-Chip）命令队列完成 */
77          rtw_pci_tx_isr(rtwdev, rtwpci, RTW_TX_QUEUE_H2C);
78
79      if (irq_status[0] & IMR_ROK) {     /* 接收完成 */
80          rtw_pci_rx_isr(rtwdev);        /* 调度NAPI轮询 */
81          rx = true;
82      }
83
84      if (unlikely(irq_status[0] & IMR_C2HCMD))
85          rtw_fw_c2h_cmd_isr(rtwdev);
86
87      /* 处理完毕，重新使能中断 */
88      if (rtwpci->running)
89          rtw_pci_enable_interrupt(rtwdev, rtwpci, rx);
90
91      spin_unlock_bh(&rtwpci->irq_lock);
92      return IRQ_HANDLED;
93  }
```

硬中断处理只做关中断和唤醒线程两件事，耗时极短；实际的中断状态读取、TX完成回收、RX调度都在线程上下文完成，所以可以使用自旋锁等可能睡眠的操作。

### 8.5.5. 电源管理[¶](#id27 "永久链接至标题")

**禁用ASPM省电开关**

禁用ASPM省电开关(位于内核源码/drivers/net/wireless/realtek/rtw88/pci.c)[¶](#id87 "永久链接至代码")

```c
/* 设为Y则完全禁用ASPM省电 */
static bool rtw_pci_disable_aspm;
module_param_named(disable_aspm, rtw_pci_disable_aspm, bool, 0644);
MODULE_PARM_DESC(disable_aspm, "Set Y to disable PCI ASPM support");
```

所有ASPM/CLKREQ函数入口处都会检查此标志，运行时写入 `/sys/module/rtw88_pci/parameters/disable_aspm` 即可生效。 当用户遇到省电导致的兼容性问题时，如链路频繁断连、唤醒失败，可设为Y强制禁用所有ASPM/CLKREQ操作。

**ASPM L1使能/禁用**

rtw_pci_aspm_set函数用于控制链路进入L1休眠状态。L1是PCIe链路的主要省电状态——发送器/接收器关闭、PLL停止，功耗大幅降低。

rtw_pci_aspm_set函数(位于内核源码/drivers/net/wireless/realtek/rtw88/pci.c)[¶](#id88 "永久链接至代码")

```c
 1  static void rtw_pci_aspm_set(struct rtw_dev *rtwdev, bool enable)
 2  {
 3      u8 value;
 4      int ret;
 5
 6      /* 用户禁用ASPM时直接返回 */
 7      if (rtw_pci_disable_aspm)
 8          return;
 9
10      /* 通过DBI读取链路配置寄存器 */
11      ret = rtw_dbi_read8(rtwdev, RTK_PCIE_LINK_CFG, &value);
12      if (ret) {
13          rtw_err(rtwdev, "failed to read ASPM, ret=%d", ret);
14          return;
15      }
16
17      /* 设置或清除L1软件使能位
18       * BIT_L1_SW_EN = 1：允许链路在空闲时进入L1低功耗状态
19       * BIT_L1_SW_EN = 0：禁止链路进入L1，始终保持L0活跃状态 */
20      if (enable)
21          value |= BIT_L1_SW_EN;
22      else
23          value &= ~BIT_L1_SW_EN;
24
25      /* 通过DBI写入PCIe链路配置寄存器 */
26      rtw_dbi_write8(rtwdev, RTK_PCIE_LINK_CFG, value);
27  }
```

**链路电源状态切换**

L1的进入/退出有延迟，通常几微秒，如果链路频繁在L0/L1之间切换，反而会降低性能。 因此驱动不是无条件使能L1，而是通过下面的rtw_pci_link_ps函数在合适的时机控制。

rtw_pci_link_ps函数(位于内核源码/drivers/net/wireless/realtek/rtw88/pci.c)[¶](#id89 "永久链接至代码")

```c
 1  static void rtw_pci_link_ps(struct rtw_dev *rtwdev, bool enter)
 2  {
 3      struct rtw_pci *rtwpci = (struct rtw_pci *)rtwdev->priv;
 4
 5      /* 仅当主机端已使能ASPM L1时才操作 */
 6      if (!(rtwpci->link_ctrl & PCI_EXP_LNKCTL_ASPM_L1))
 7          return;
 8
 9      /* 使用引用计数：进入时计数减到0才真正使能，退出时计数增到1才真正禁用 */
10      if ((enter && atomic_dec_if_positive(&rtwpci->link_usage) == 0) |
11          (!enter && atomic_inc_return(&rtwpci->link_usage) == 1))
12          rtw_pci_aspm_set(rtwdev, enter);
13  }
```

link_usage表示当前有多少个模块需要链路保持活跃，probe时设备刚启动初始化值为1， 任何模块需要链路活跃时调用rtw_hci_link_ps(rtwdev, false)，计数+1，任何模块允许链路休眠时调用rtw_hci_link_ps(rtwdev, true)，计数-1，只有计数归零时才真正使能L1。

**CLKREQ 使能/禁用**

rtw_pci_clkreq_set函数用于控制设备端的CLKREQ#省电逻辑模块，使能后，当链路进入L1休眠时，设备会拉高CLKREQ#请求时钟，通知主机可以关闭参考时钟；链路需要唤醒时再拉低CLKREQ#请求时钟。

rtw_pci_clkreq_set函数(位于内核源码/drivers/net/wireless/realtek/rtw88/pci.c)[¶](#id90 "永久链接至代码")

```c
 1  static void rtw_pci_clkreq_set(struct rtw_dev *rtwdev, bool enable)
 2  {
 3      u8 value;
 4      int ret;
 5
 6      /* 用户禁用ASPM时直接返回 */
 7      if (rtw_pci_disable_aspm)
 8          return;
 9
10      /* 通过DBI读取PCIe链路配置寄存器 */
11      ret = rtw_dbi_read8(rtwdev, RTK_PCIE_LINK_CFG, &value);
12      if (ret) {
13          rtw_err(rtwdev, "failed to read CLKREQ_L1, ret=%d", ret);
14          return;
15      }
16
17      /* 设置或清除CLKREQ软件使能位
18       * BIT_CLKREQ_SW_EN = 1：设备参与CLKREQ#协议，空闲时释放时钟
19       * BIT_CLKREQ_SW_EN = 0：设备始终请求时钟，不参与省电 */
20      if (enable)
21          value |= BIT_CLKREQ_SW_EN;
22      else
23          value &= ~BIT_CLKREQ_SW_EN;
24
25      /* 将修改后的值写回链路配置寄存器 */
26      rtw_dbi_write8(rtwdev, RTK_PCIE_LINK_CFG, value);
27  }
```

### 8.5.6. 设备移除与关机[¶](#id28 "永久链接至标题")

**remove函数**

rtw_pci_remove函数在模块移除时调用。

rtw_pci_remove函数(位于内核源码/drivers/net/wireless/realtek/rtw88/pci.c)[¶](#id91 "永久链接至代码")

```c
 1  void rtw_pci_remove(struct pci_dev *pdev)
 2  {
 3      struct ieee80211_hw *hw = pci_get_drvdata(pdev);  /* 取回probe时存入的hw */
 4      struct rtw_dev *rtwdev;
 5      struct rtw_pci *rtwpci;
 6
 7      if (!hw)
 8          return;
 9
10      rtwdev = hw->priv;
11      rtwpci = (struct rtw_pci *)rtwdev->priv;
12
13      rtw_unregister_hw(rtwdev, hw);             /* 从网络层注销 */
14      rtw_pci_disable_interrupt(rtwdev, rtwpci); /* 关闭所有PCI中断 */
15      rtw_pci_napi_deinit(rtwdev);               /* 销毁NAPI */
16      rtw_pci_destroy(rtwdev, pdev);             /* 释放DMA环 + IO解映射 */
17      rtw_pci_declaim(rtwdev, pdev);             /* pci_disable_device */
18      rtw_pci_free_irq(rtwdev, pdev);            /* 释放中断向量 */
19      rtw_core_deinit(rtwdev);                   /* 核心子系统清理 */
20      ieee80211_free_hw(hw);                     /* 释放hw结构体 */
21  }
```

**shutdown函数**

rtw_pci_shutdown函数在设备关机时调用。

rtw_pci_shutdown函数(位于内核源码/drivers/net/wireless/realtek/rtw88/pci.c)[¶](#id92 "永久链接至代码")

```c
 1  void rtw_pci_shutdown(struct pci_dev *pdev)
 2  {
 3      struct ieee80211_hw *hw = pci_get_drvdata(pdev);
 4      struct rtw_dev *rtwdev;
 5      const struct rtw_chip_info *chip;
 6
 7      if (!hw)
 8          return;
 9
10      rtwdev = hw->priv;
11      chip = rtwdev->chip;
12
13      /* 如果芯片驱动定义了shutdown回调则执行 */
14      if (chip->ops->shutdown)
15          chip->ops->shutdown(rtwdev);
16
17      /* 将PCI设备切换到低功耗状态 */
18      pci_set_power_state(pdev, PCI_D3hot);
19  }
```

## 8.6. PCI Explorer驱动实验[¶](#pci-explorer "永久链接至标题")

本实验驱动基于Linux PCI子系统框架设计，属于PCI设备底层探测调试驱动，适配Realtek RTL8188EE/RTL8821CE/RTL8822CE/RTL8852BE系列PCIe无线网卡设备。

本实验驱动实现PCIe设备信息探测功能，支持标准配置空间解析、标准/扩展Capability能力枚举、BAR寄存器空间解析与MMIO映射，同时提供安全的寄存器读写调试功能。 通过白名单机制限制非法寄存器写入，搭配互斥锁实现并发访问保护，基于sysfs向用户层暴露调试接口，可完成PCIe设备硬件信息查看、寄存器读写调试、链路状态分析等实验功能。

本章的示例代码目录为： **linux_driver/42_pcie_subsystem**

### 8.6.1. 驱动代码详解[¶](#id29 "永久链接至标题")

#### 8.6.1.1. 核心定义与数据结构[¶](#id30 "永久链接至标题")

完成驱动基础信息宏定义、PCIe设备私有数据结构体封装，定义寄存器读写白名单、能力字段匹配表等。

核心定义与数据结构(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id93 "永久链接至代码")

```c
 1  #define DRV_NAME    "pcie_explorer"  /* 驱动名称 */
 2  #define DRV_VERSION "1.0"            /* 驱动版本号 */
 3
 4  /* 设备私有数据结构体 */
 5  struct pcie_dev {
 6      struct pci_dev *pdev;   /* PCI设备指针 */
 7      void __iomem *bar_mmap; /* BAR2映射地址 */
 8      size_t bar_size;        /* BAR2大小 */
 9      struct mutex lock;      /* 并发访问保护锁 */
10  };
11
12  /*  配置空间可写寄存器白名单，偏移查看pci_regs.h */
13  static const u32 config_whitelist[] = {
14      0x04, 0x05,  /* PCI_COMMAND */
15      0x0C, 0x0D,  /* PCI_CACHE_LINE_SIZE/PCI_LATENCY_TIMER */
16      0x3C, 0x3D,  /* PCI_INTERRUPT_LINE/PCI_INTERRUPT_PIN */
17  };
18  #define CONFIG_WHITELIST_SIZE ARRAY_SIZE(config_whitelist)
19
20  /* BAR空间可写寄存器白名单，参考rtw88/pci.h */
21  static const u32 bar_whitelist[] = {
22      0x00B4,  /* RTK_PCI_HISR0 - 中断状态0 */
23      0x00BC,  /* RTK_PCI_HISR1 - 中断状态1 */
24      0x0300,  /* RTK_PCI_CTRL - DMA控制 */
25  };
26  #define BAR_WHITELIST_SIZE ARRAY_SIZE(bar_whitelist)
```

关键说明：

- 第1-2行：宏定义驱动名称与版本号，用于日志打印、模块标识。
    
- 第5-10行：pcie_dev私有结构体，存储PCI设备指针、BAR2内核虚拟映射地址、寄存器空间大小、并发互斥锁。
    
- 第13-17行：PCI配置空间可写白名单，仅允许操作命令寄存器、缓存配置、中断配置等安全寄存器，禁止修改设备核心硬件参数。
    
- 第21-25行：BAR寄存器空间可写白名单，适配RTL网卡，仅允许操作中断状态、DMA控制寄存器，避免非法改写。
    
- 第18、26行：通过ARRAY_SIZE自动计算白名单数组长度，用于后续动态校验处理。
    

#### 8.6.1.2. 白名单校验工具函数[¶](#id31 "永久链接至标题")

用于配置空间、BAR空间寄存器写入权限校验，遍历白名单寄存器偏移，拦截非法写入操作。

白名单校验工具函数(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id94 "永久链接至代码")

```c
 1  /* 检查偏移是否在白名单中 */
 2  static bool is_config_writable(u32 offset, u8 size)
 3  {
 4      int i, j;
 5      /* 检查写入的每一个字节是否都在白名单中 */
 6      for (j = 0; j < size; j++) {
 7          bool found = false;
 8          for (i = 0; i < CONFIG_WHITELIST_SIZE; i++) {
 9              if (config_whitelist[i] == offset + j) {
10                  found = true;
11                  break;
12              }
13          }
14          if (!found)
15              return false;
16      }
17      return true;
18  }
19
20  /* 检查BAR偏移是否在白名单中 */
21  static bool is_bar_writable(u32 offset)
22  {
23      int i;
24      for (i = 0; i < BAR_WHITELIST_SIZE; i++) {
25          if (bar_whitelist[i] == offset)
26              return true;
27      }
28      return false;
29  }
```

关键说明：

- 第2-18行：is_config_writable函数，支持1/2/4字节长度写入校验，逐字节遍历写入范围，确保写入的所有字节均在白名单内，避免非法写入。
    
- 第21-29行：is_bar_writable函数，匹配BAR空间寄存器偏移，仅白名单内的寄存器允许写入。
    

#### 8.6.1.3. Capability名称解析工具函数[¶](#capability "永久链接至标题")

用于标准/扩展Capability ID到可读字符串的映射，将内核数字ID转换为硬件能力名称。

Capability名称解析工具函数(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id95 "永久链接至代码")

```c
 1  /* Capability名称查找表  */
 2  static const char *get_cap_name(u8 cap_id)
 3  {
 4      /* 根据Capability ID返回名称 */
 5      switch (cap_id) {
 6      case PCI_CAP_ID_PM:     return "Power Management";    /* 电源管理 */
 7      case PCI_CAP_ID_AGP:    return "AGP";                 /* 加速图形端口 */
 8      case PCI_CAP_ID_VPD:    return "VPD";                 /* 关键产品数据 */
 9      case PCI_CAP_ID_SLOTID: return "Slot Identification"; /* 插槽标识 */
10      case PCI_CAP_ID_MSI:    return "MSI";                 /* 消息信号中断 */
11      case PCI_CAP_ID_MSIX:   return "MSI-X";               /* 扩展消息信号中断 */
12      case PCI_CAP_ID_EXP:    return "PCI Express";         /* PCI Express */
13      case PCI_CAP_ID_SSVID:  return "Subsystem Vendor ID"; /* 子系统厂商ID */
14      default:                return "Unknown";             /* 未知Capability */
15      }
16  }
17
18  static const char *get_ext_cap_name(u16 cap_id)
19  {
20      /* 根据扩展Capability ID返回名称 */
21      switch (cap_id) {
22      case PCI_EXT_CAP_ID_ERR:   return "Advanced Error Reporting";             /* 高级错误报告 */
23      case PCI_EXT_CAP_ID_VC:    return "Virtual Channel";                      /* 虚拟通道 */
24      case PCI_EXT_CAP_ID_DSN:   return "Device Serial Number";                 /* 设备序列号 */
25      case PCI_EXT_CAP_ID_PWR:   return "Power Budgeting";                      /* 功率预算 */
26      case PCI_EXT_CAP_ID_RCLD:  return "Root Complex Link Declaration";        /* 根复合体链路声明 */
27      case PCI_EXT_CAP_ID_RCEC:  return "Root Complex Event Collector";         /* 根复合体事件收集器 */
28      case PCI_EXT_CAP_ID_VNDR:  return "Vendor Specific";                      /* 厂商特定 */
29      case PCI_EXT_CAP_ID_L1SS:  return "L1 PM Substates";                      /* L1电源管理子状态 */
30      case PCI_EXT_CAP_ID_SRIOV: return "Single Root I/O Virtualization";       /* 单根IO虚拟化 */
31      case PCI_EXT_CAP_ID_PRI:   return "Page Request Interface";               /* 页面请求接口 */
32      case PCI_EXT_CAP_ID_ATS:   return "Address Translation Services";         /* 地址转换服务 */
33      case PCI_EXT_CAP_ID_PTM:   return "Precision Time Measurement";           /* 精确时间测量 */
34      default:                   return "Unknown";                              /* 未知扩展Capability */
35      }
36  }
```

关键说明：

- 第2-16行：get_cap_name函数，适配PCI标准Capability，覆盖电源管理、MSI/MSI-X中断、PCIe链路等硬件能力解析。
    
- 第18-36行：get_ext_cap_name函数，解析PCIe扩展Capability，支持高级错误报告、电源管理子状态、设备序列号等拓展能力解析。
    

#### 8.6.1.4. PCIe标准配置空间解析[¶](#id32 "永久链接至标题")

取PCIe设备256字节标准配置空间的所有寄存器，解析设备厂商ID、设备ID、命令状态、中断信息、缓存配置等基础硬件参数，打印设备基础信息。

PCIe标准配置空间解析(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id96 "永久链接至代码")

```c
 1  /*  配置空间解析 */
 2  static void print_config_space(struct pci_dev *pdev)
 3  {
 4      /* 配置空间标准寄存器 */
 5      u16 vendor_id, device_id, command, status;
 6      /* 配置空间字节寄存器 */
 7      u8  revision, header_type, interrupt_line, interrupt_pin;
 8      /* 延迟定时器和缓存行大小 */
 9      u8  lat_timer, cache_line_sz;
10      /* 类别代码和Capability指针 */
11      u32 class_code, cis_ptr;
12      /* 子系统厂商ID和设备ID */
13      u16 subsys_vendor, subsys_id;
14
15      /* 读取厂商ID */
16      pci_read_config_word(pdev, PCI_VENDOR_ID, &vendor_id);
17      /* 读取设备ID */
18      pci_read_config_word(pdev, PCI_DEVICE_ID, &device_id);
19      /* 读取命令寄存器 */
20      pci_read_config_word(pdev, PCI_COMMAND, &command);
21      /* 读取状态寄存器 */
22      pci_read_config_word(pdev, PCI_STATUS, &status);
23      /* 读取修订版本 */
24      pci_read_config_byte(pdev, PCI_REVISION_ID, &revision);
25      /* 读取类别代码 */
26      pci_read_config_dword(pdev, PCI_CLASS_REVISION, &class_code);
27      /* 读取缓存行大小 */
28      pci_read_config_byte(pdev, PCI_CACHE_LINE_SIZE, &cache_line_sz);
29      /* 读取延迟定时器 */
30      pci_read_config_byte(pdev, PCI_LATENCY_TIMER, &lat_timer);
31      /* 读取头类型 */
32      pci_read_config_byte(pdev, PCI_HEADER_TYPE, &header_type);
33      /* 读取中断线 */
34      pci_read_config_byte(pdev, PCI_INTERRUPT_LINE, &interrupt_line);
35      /* 读取中断引脚 */
36      pci_read_config_byte(pdev, PCI_INTERRUPT_PIN, &interrupt_pin);
37      /* 读取子系统厂商ID */
38      pci_read_config_word(pdev, PCI_SUBSYSTEM_VENDOR_ID, &subsys_vendor);
39      /* 读取子系统设备ID */
40      pci_read_config_word(pdev, PCI_SUBSYSTEM_ID, &subsys_id);
41      /* 读取Capability链表指针 */
42      pci_read_config_dword(pdev, PCI_CAPABILITY_LIST, &cis_ptr);
43
44      pr_info("      PCIe 配置空间      \n");                               /* 打印标题 */
45      pr_info("  Vendor: 0x%04X  Device: 0x%04X\n", vendor_id, device_id);  /* 打印厂商和设备ID */
46      pr_info("  Revision: 0x%02X  Header: 0x%02X %s\n",                    /* 打印修订版本和头类型 */
47          revision, header_type,
48          (header_type & 0x80) ? "Multi-function" : "Single-function");  /* 判断单功能/多功能 */
49      pr_info("  Class: 0x%08X (IF=0x%02X Sub=0x%02X Base=0x%02X)\n",    /* 打印类别代码分解 */
50          class_code,
51          (class_code >> 8) & 0xFF,   /* 接口级编程接口 */
52          (class_code >> 16) & 0xFF,   /* 子类 */
53          (class_code >> 24) & 0xFF); /* 基类 */
54      pr_info("  Command: 0x%04X [%s%s%s%s%s]\n",         /* 打印命令寄存器位域 */
55          command,
56          (command & PCI_COMMAND_IO) ? "IO " : "",      /* IO 空间访问使能 */
57          (command & PCI_COMMAND_MEMORY) ? "MEM " : "", /* 内存空间访问使能 */
58          (command & PCI_COMMAND_MASTER) ? "BM " : "",  /* 总线主控使能 */
59          (command & PCI_COMMAND_PARITY) ? "PAR " : "", /* 奇偶校验使能 */
60          (command & PCI_COMMAND_SERR) ? "SERR" : "");  /* 系统错误使能 */
61      pr_info("  Status: 0x%04X\n", status);            /* 打印状态寄存器 */
62      pr_info("  Subsys: Vendor=0x%04X Device=0x%04X\n", subsys_vendor, subsys_id); /* 打印子系统信息 */
63      pr_info("  IRQ: Line=%d Pin=%d\n", interrupt_line, interrupt_pin);            /* 打印中断信息 */
64      pr_info("  Cache: %d bytes  Latency: %d\n", cache_line_sz * 4, lat_timer);    /* 打印缓存和延迟信息 */
65      pr_info("  Capability PTR: 0x%02X\n", (u8)cis_ptr);                           /* 打印Capability指针 */
66      pr_info("                 \n");
67  }
```

关键说明：

- 第5-13行：定义各类配置空间寄存器变量，区分8/16/32位寄存器类型。
    
- 第16-42行：调用pci_read_config_xxx系列接口，读取配置空间所有核心参数，相关宏定义在内核源码/include/uapi/linux/pci_regs.h。
    
- 第46-48行：解析设备头类型，区分单功能/多功能PCIe设备，识别设备拓扑属性。
    
- 第49-53行：解析设备类别代码，展示基类、子类、编程接口，识别设备硬件类型。
    
- 第54-60行：解析命令寄存器，展示IO空间、内存空间、总线主控等功能使能状态。
    
- 第64行：缓存行大小需乘以4，按照PCI协议硬件要求，确保信息正确。
    

#### 8.6.1.5. 标准Capability链表解析[¶](#id33 "永久链接至标题")

遍历PCIe设备标准Capability链表，识别电源管理、MSI、MSI-X、PCIe链路等核心能力，解析各能力的状态参数、链路速率、中断配置等详细信息。

标准Capability链表解析(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id97 "永久链接至代码")

```c
  1  /* 解析标准Capability */
  2  static void parse_capabilities(struct pci_dev *pdev)
  3  {
  4      /* Capability ID 列表 */
  5      static const u8 cap_ids[] = {
  6          PCI_CAP_ID_PM,
  7          PCI_CAP_ID_MSI,
  8          PCI_CAP_ID_MSIX,
  9          PCI_CAP_ID_EXP,
 10          PCI_CAP_ID_VPD,
 11          PCI_CAP_ID_SSVID,
 12          PCI_CAP_ID_AGP,
 13          PCI_CAP_ID_SLOTID,
 14      };
 15      /* 循环变量 */
 16      int i, count = 0;
 17
 18      /* 打印标题 */
 19      pr_info("      Capability 链表      \n");
 20
 21      /* 遍历所有已知的Capability ID */
 22      for (i = 0; i < ARRAY_SIZE(cap_ids); i++) {
 23          int offset = pci_find_capability(pdev, cap_ids[i]);
 24          if (offset == 0)
 25              continue;
 26
 27          /* 打印Capability信息 */
 28          pr_info("  [%d] @0x%02X: ID=0x%02X (%s)\n",
 29              count, offset, cap_ids[i], get_cap_name(cap_ids[i]));
 30
 31          /* 根据Capability ID解析详细信息 */
 32          switch (cap_ids[i]) {
 33          /* 电源管理Capability */
 34          case PCI_CAP_ID_PM: {
 35              /* 电源管理控制寄存器 */
 36              u16 pm_ctrl;
 37              /* 读取PM控制寄存器 */
 38              pci_read_config_word(pdev, offset + PCI_PM_CTRL, &pm_ctrl);
 39              /* 打印PM状态信息 */
 40              pr_info("      PM: State=%d, D1=%s, D2=%s, PME=%s, PMEStatus=%s\n",
 41                  pm_ctrl & PCI_PM_CTRL_STATE_MASK,                   /* 当前电源状态 */
 42                  (pm_ctrl & PCI_PM_CAP_D1) ? "Yes" : "No",           /* D1状态支持 */
 43                  (pm_ctrl & PCI_PM_CAP_D2) ? "Yes" : "No",           /* D2状态支持 */
 44                  (pm_ctrl & PCI_PM_CAP_PME) ? "Yes" : "No",          /* PME状态支持 */
 45                  (pm_ctrl & PCI_PM_CTRL_PME_STATUS) ? "Yes" : "No"); /* PME状态 */
 46              break;
 47          }
 48          /* MSI Capability */
 49          case PCI_CAP_ID_MSI: {
 50              /* MSI控制寄存器 */
 51              u16 msg_ctrl;
 52              /* MSI地址低32位 */
 53              u32 msg_addr_lo;
 54              /* MSI数据 */
 55              u16 msg_data;
 56              /* 读取MSI控制寄存器 */
 57              pci_read_config_word(pdev, offset + PCI_MSI_FLAGS, &msg_ctrl);
 58              /* 读取MSI地址 */
 59              pci_read_config_dword(pdev, offset + PCI_MSI_ADDRESS_LO, &msg_addr_lo);
 60              /* 读取MSI数据 */
 61              pci_read_config_word(pdev, offset + PCI_MSI_DATA_32, &msg_data);
 62              /* 打印MSI信息 */
 63              pr_info("      MSI: Enable=%s, Addr64=%s, Data=0x%04X\n",
 64                  (msg_ctrl & PCI_MSI_FLAGS_ENABLE) ? "Yes" : "No",      /* MSI启用状态 */
 65                  (msg_ctrl & PCI_MSI_FLAGS_64BIT) ? "Yes" : "No",       /* 64位地址支持 */
 66                  msg_data);                                             /* MSI数据值 */
 67              break;
 68          }
 69          /* MSI-X Capability */
 70          case PCI_CAP_ID_MSIX: {
 71              /* MSI-X控制寄存器 */
 72              u16 msg_ctrl;
 73              /* MSI-X表和PBA偏移 */
 74              u32 table_off, pba_off;
 75              /* 读取MSI-X控制寄存器 */
 76              pci_read_config_word(pdev, offset + PCI_MSIX_FLAGS, &msg_ctrl);
 77              /* 读取MSI-X表偏移 */
 78              pci_read_config_dword(pdev, offset + PCI_MSIX_TABLE, &table_off);
 79              /* 读取PBA偏移 */
 80              pci_read_config_dword(pdev, offset + PCI_MSIX_PBA, &pba_off);
 81              /* 打印MSI-X信息 */
 82              pr_info("      MSI-X: Enable=%s, TotalVec=%d\n",
 83                  (msg_ctrl & PCI_MSIX_FLAGS_ENABLE) ? "Yes" : "No",  /* MSI-X启用状态 */
 84                  msg_ctrl & PCI_MSIX_FLAGS_QSIZE);                   /* MSI-X向量数量 */
 85              break;
 86          }
 87          /* PCI Express Capability */
 88          case PCI_CAP_ID_EXP: {
 89              /* 链路能力是32位，链路状态是16位 */
 90              u32 lnk_cap;
 91              u16 lnk_status;
 92              /* 解析出的速度和宽度 */
 93              u8 max_speed, max_width, cur_speed, cur_width;
 94              /* 速度字符串映射 */
 95              const char *max_spd_str, *cur_spd_str;
 96
 97              /* 读取链路能力 (Offset 0Ch, 32位寄存器, 4字节对齐) */
 98              pci_read_config_dword(pdev, offset + PCI_EXP_LNKCAP, &lnk_cap);
 99
100              /*
101              * 读取链路状态 (Offset 12h, 16位寄存器)
102              * 必须使用pci_read_config_word！因为0x12不是4字节对齐，
103              * 使用dword读取会导致硬件对齐错误，直接返回0！
104              */
105              pci_read_config_word(pdev, offset + PCI_EXP_LNKSTA, &lnk_status);
106
107              /* 调试打印，验证读取结果 */
108              pr_info("      DEBUG: LNKCAP=0x%08X, LNKSTA=0x%04X\n", lnk_cap, lnk_status);
109
110              /* 解析能力寄存器 (Bit 0-3: 速度, Bit 4-9: 宽度) */
111              max_speed = lnk_cap & 0x0F;
112              max_width = (lnk_cap >> 4) & 0x3F;
113
114              /* 解析状态寄存器 (Bit 0-3: 速度, Bit 4-9: 宽度) */
115              cur_speed = lnk_status & 0x0F;
116              cur_width = (lnk_status >> 4) & 0x3F;
117
118              /* 映射最大链路速度 (1=2.5, 2=5.0, 3=8.0) */
119              max_spd_str = (max_speed == 1) ? "2.5" :
120                          (max_speed == 2) ? "5.0" :
121                          (max_speed == 3) ? "8.0" : "?";
122              pr_info("      PCIe: MaxLanes=x%d, MaxSpeed=%sGT/s\n",    /* 打印最大链路宽度和速度 */
123                  max_width, max_spd_str);                              /* 解析能力寄存器 */
124
125              /* 映射协商链路速度 (1=2.5, 2=5.0, 3=8.0) */
126              cur_spd_str = (cur_speed == 1) ? "2.5" :
127                          (cur_speed == 2) ? "5.0" :
128                          (cur_speed == 3) ? "8.0" : "?";
129              pr_info("            NegLanes=x%d, NegSpeed=%sGT/s\n",    /* 打印协商链路宽度和速度 */
130                  cur_width, cur_spd_str);                              /* 解析状态寄存器 */
131              break;
132          }
133          default:
134              break;
135          }
136          count++;
137      }
138
139      pr_info("  共 %d 个 Capability\n", count);
140      pr_info("                       \n");
141  }
```

关键说明：

- 第5-13行：定义需要遍历的标准Capability ID列表，覆盖PCIe设备常用能力。
    
- 第22-25行：调用pci_find_capability自动遍历设备Capability链表，跳过设备不支持的能力项。
    
- 第34-47行：解析电源管理能力，识别设备支持的电源状态、PME唤醒功能。
    
- 第49-68行：解析MSI中断配置，识别中断启用状态、64位地址支持、中断数据参数。
    
- 第70-86行：解析MSI-X中断配置，获取中断向量总数、配置表偏移地址。
    
- 第88-132行：解析PCIe链路最大/协商速率、通道宽度等，将寄存器数值映射为标准GT/s速率单位，展示链路性能。
    

#### 8.6.1.6. 扩展Capability链表解析[¶](#id34 "永久链接至标题")

遍历PCIe设备扩展Capability链表，枚举高级错误报告、虚拟通道、设备序列号、电源预算等拓展硬件能力。

扩展Capability链表解析(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id98 "永久链接至代码")

```c
 1  /* 解析扩展Capability */
 2  static void parse_extended_capabilities(struct pci_dev *pdev)
 3  {
 4      /* 扩展Capability ID 列表 */
 5      static const u16 ext_cap_ids[] = {
 6          PCI_EXT_CAP_ID_ERR,
 7          PCI_EXT_CAP_ID_VC,
 8          PCI_EXT_CAP_ID_DSN,
 9          PCI_EXT_CAP_ID_PWR,
10          PCI_EXT_CAP_ID_RCLD,
11          PCI_EXT_CAP_ID_RCEC,
12          PCI_EXT_CAP_ID_VNDR,
13          PCI_EXT_CAP_ID_L1SS,
14          PCI_EXT_CAP_ID_SRIOV,
15          PCI_EXT_CAP_ID_PRI,
16          PCI_EXT_CAP_ID_ATS,
17          PCI_EXT_CAP_ID_PTM,
18      };
19      /* 循环变量 */
20      int i, count = 0;
21
22      /* 打印标题 */
23      pr_info("      Extended Capability      \n");
24
25      /* 遍历所有已知的扩展Capability ID */
26      for (i = 0; i < ARRAY_SIZE(ext_cap_ids); i++) {
27          int offset = pci_find_ext_capability(pdev, ext_cap_ids[i]);
28          if (offset == 0)
29              continue;
30
31          /* 打印扩展Capability信息 */
32          pr_info("  [%d] @0x%03X: ID=0x%04X (%s)\n",
33              count, offset, ext_cap_ids[i], get_ext_cap_name(ext_cap_ids[i]));
34          count++;
35      }
36
37      pr_info("  共 %d 个 Extended Capability\n", count);
38      pr_info("                              \n");
39  }
```

关键说明：

- 第5-18行：定义PCIe扩展Capability ID，包含虚拟化、地址转换、时间同步等高端设备能力。
    
- 第26-29行：调用pci_find_ext_capability内核接口遍历拓展能力，自动适配PCIe设备拓展配置空间。
    
- 第32-33行：结合自定义名称解析函数，打印拓展能力偏移、ID、功能名称。
    

#### 8.6.1.7. BAR空间信息解析[¶](#id35 "永久链接至标题")

遍历PCIe设备6个BAR寄存器，解析BAR空间类型（IO/内存）、地址、大小、64位标识、预取属性。

BAR空间信息解析(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id99 "永久链接至代码")

```c
 1  /* 解析BAR信息 */
 2  static void parse_bar_info(struct pcie_dev *edev)
 3  {
 4      /* 获取PCI设备指针 */
 5      struct pci_dev *pdev = edev->pdev;
 6      /* BAR索引 */
 7      int i;
 8
 9      /* 打印标题 */
10      pr_info("      BAR 空间解析      \n");
11
12      /* 遍历BAR0-BAR5 */
13      for (i = 0; i < 6; i++) {
14          /* BAR原始值 */
15          u32 bar_raw;
16          /* BAR基地址和大小 */
17          u64 bar_base, bar_size;
18          /* BAR属性标志 */
19          bool is_mem, is_prefetch, is_64bit;
20
21          /* 读取BAR寄存器 */
22          pci_read_config_dword(pdev, PCI_BASE_ADDRESS_0 + i * 4, &bar_raw);
23          /* 判断是否为内存映射BAR */
24          is_mem = !(bar_raw & 0x01);
25
26          /* I/O映射BAR */
27          if (!is_mem) {
28              /* 提取I/O基地址 */
29              bar_base = bar_raw & 0xFFFFFFFC;
30              /* 获取BAR大小 */
31              bar_size = pci_resource_len(pdev, i);
32              /* 打印I/O BAR信息 */
33              pr_info("  BAR%d: I/O  0x%08llX (size=%llu)\n",
34                  i, (unsigned long long)bar_base, (unsigned long long)bar_size);
35          /* 内存映射 BAR */
36          } else {
37              /* 判断是否支持预取 */
38              is_prefetch = (bar_raw >> 3) & 0x01;
39              /* 判断是否为64位BAR */
40              is_64bit = (bar_raw >> 2) & 0x01;
41              /* 获取BAR基地址 */
42              bar_base = pci_resource_start(pdev, i);
43              /* 获取BAR大小 */
44              bar_size = pci_resource_len(pdev, i);
45
46              /* 打印内存BAR信息，动态选择单位，避免小于1MB时显示为0 */
47              if (bar_size >= 1024 * 1024) {
48                  /* 大于等于1MB，以MB为单位 */
49                  pr_info("  BAR%d: MEM  0x%016llX (size=%llu MB)%s%s\n",
50                      i, (unsigned long long)bar_base,
51                      (unsigned long long)(bar_size / (1024 * 1024)),  /* 转换为MB */
52                      is_64bit ? " 64bit" : "",         /* 64位标志 */
53                      is_prefetch ? " Prefetch" : "");  /* 预取标志 */
54              } else {
55                  /* 小于1MB，以KB为单位 */
56                  pr_info("  BAR%d: MEM  0x%016llX (size=%llu KB)%s%s\n",
57                      i, (unsigned long long)bar_base,
58                      (unsigned long long)(bar_size / 1024),           /* 转换为KB */
59                      is_64bit ? " 64bit" : "",         /* 64位标志 */
60                      is_prefetch ? " Prefetch" : "");  /* 预取标志 */
61              }
62          }
63
64          /* 64位BAR占用两个BAR号 */
65          if (is_64bit)
66              i++;  /* 跳过下一个BAR */
67      }
68
69      pr_info("                        \n");
70  }
```

关键说明：

- 第13行：循环遍历PCIe标准6个BAR寄存器（BAR0-BAR5）。
    
- 第24-27行：通过BAR寄存器最低位判断空间类型，0为内存空间、1为IO空间。
    
- 第38-40行：内存BAR解析，通过寄存器位域识别预取属性、64位寻址属性。
    
- 第47-61行：动态单位选择处理，解决小容量BAR空间MB单位显示为0的问题。
    
- 第65-66行：64位BAR占用连续两个BAR索引，自动跳过下一个索引，避免重复解析。
    

#### 8.6.1.8. BAR2空间映射与寄存器探索[¶](#bar2 "永久链接至标题")

实现BAR2物理地址到内核虚拟地址的MMIO映射，读取BAR2空间前64字节寄存器数据，对硬件寄存器探索。

BAR2空间映射与寄存器探索(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id100 "永久链接至代码")

```c
 1  /* 映射BAR2并读取一些寄存器 */
 2  static void map_and_explore_bar(struct pcie_dev *edev)
 3  {
 4      /* 获取PCI设备指针 */
 5      struct pci_dev *pdev = edev->pdev;
 6      /* BAR起始地址和长度 */
 7      unsigned long bar_start, bar_len;
 8      /* 读取的寄存器值 */
 9      u32 val;
10      /* 循环变量 */
11      int i;
12
13      /* 获取BAR2起始地址，通常BAR2是RTL网卡的寄存器空间 */
14      bar_start = pci_resource_start(pdev, 2);
15      /* 获取BAR2长度 */
16      bar_len = pci_resource_len(pdev, 2);
17
18      /* 检查BAR2是否有效 */
19      if (bar_len == 0) {
20          pr_err("BAR2 大小为 0\n");
21          return;
22      }
23
24      /* 打印标题 */
25      pr_info("      BAR2 MMIO 探索      \n");
26      pr_info("  基地址: 0x%08lX, 大小: %lu bytes\n", bar_start, bar_len); /* 打印基地址和大小 */
27
28      /* 映射BAR2到内核虚拟地址空间(非预取内存空间) */
29      edev->bar_mmap = pci_iomap(pdev, 2, bar_len);
30      if (!edev->bar_mmap) {
31          pr_err("BAR2 映射失败\n");
32          return;
33      }
34      /* 保存BAR2大小 */
35      edev->bar_size = bar_len;
36
37      pr_info("  MMIO 虚拟地址: %p\n", edev->bar_mmap);  /* 打印虚拟地址 */
38      pr_info("  读取前64个字节的寄存器:\n");            /* 打印读取提示 */
39
40      /* 读取BAR2前64字节，每次读4字节 */
41      for (i = 0; i < 64; i += 4) {
42          /* 读取32位寄存器 */
43          val = readl(edev->bar_mmap + i);
44          /* 每行打印4个寄存器 */
45          if (i % 16 == 0)
46              pr_info("    %04X: ", i);  /* 打印偏移地址 */
47          pr_cont("%08X ", val);         /* 打印寄存器值，不换行 */
48          /* 每行最后一个寄存器 */
49          if (i % 16 == 12)
50              pr_cont("\n");  /* 换行 */
51      }
52      pr_info("\n");
53      pr_info("                         \n");
54  }
```

关键说明：

- 第14-22行：获取BAR2物理地址与空间大小，校验空间有效性。
    
- 第29行：调用pci_iomap完成物理地址到内核虚拟地址的映射。
    
- 第41-51行：按4字节读取寄存器，16字节为一行格式化输出进行打印。
    

#### 8.6.1.9. Sysfs用户交互接口[¶](#sysfs "永久链接至标题")

实现6个sysfs属性接口，支持用户层查看配置空间信息、读写配置空间寄存器、查看BAR空间信息、读写BAR寄存器的功能。

**显示配置空间信息**

配置空间查询接口，权限为0444只读，无需用户传入参数，自动遍历PCIe设备前256字节标准配置空间，以4字节为单位批量读取寄存器数值，格式化输出完整的配置空间数据。

显示完整配置空间(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id101 "永久链接至代码")

```c
 1  /* sysfs属性：显示完整配置空间 */
 2  static ssize_t config_space_show(struct device *dev,
 3                  struct device_attribute *attr, char *buf)
 4  {
 5      /* 转换为PCI设备 */
 6      struct pci_dev *pdev = to_pci_dev(dev);
 7      /* 偏移和缓冲区长度 */
 8      int pos, len = 0;
 9      /* 读取的32位值 */
10      u32 val32;
11
12      /* 打印标题 */
13      len += sprintf(buf + len, "PCIe 配置空间 (前 256 字节):\n");
14      /* 每次读4字节，共64次 */
15      for (pos = 0; pos < 0x100; pos += 4) {
16          pci_read_config_dword(pdev, pos, &val32);  /* 读取配置空间 */
17          len += sprintf(buf + len, "0x%02X: 0x%08X\n", pos, val32); /* 格式化输出 */
18      }
19
20      /* 返回写入字节数 */
21      return len;
22  }
```

**读取配置空间寄存器**

配置空间寄存器读取接口，权限为0220可写，支持1/2/4字节自定义位宽读取，用户传入参数格式为“offset size”，读取指定偏移、指定位宽的配置空间寄存器数值。

读取配置空间寄存器(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id102 "永久链接至代码")

```c
 1  /* sysfs属性：读取配置空间寄存器 */
 2  static ssize_t config_read_store(struct device *dev,
 3                  struct device_attribute *attr,
 4                  const char *buf, size_t count)
 5  {
 6      /* 获取设备私有数据 */
 7      struct pcie_dev *edev = dev_get_drvdata(dev);
 8      /* 转换为PCI设备 */
 9      struct pci_dev *pdev = to_pci_dev(dev);
10      /* 偏移和读取值 */
11      u32 offset, val;
12      /* 读取大小 */
13      u8 size;
14      int ret;
15
16      /* 检查设备私有数据 */
17      if (!edev)
18          return -ENODEV;
19
20      /* 获取锁 */
21      ret = mutex_lock_interruptible(&edev->lock);
22      if (ret)
23          return ret;
24
25      /* 解析用户输入 */
26      if (sscanf(buf, "%x %hhu", &offset, &size) != 2) {
27          pr_err("格式错误: 应为'offset size'\n");
28          mutex_unlock(&edev->lock);
29          return -EINVAL;
30      }
31
32      /* 检查参数有效性 */
33      if (offset >= 0x100 | (size != 1 && size != 2 && size != 4)) {
34          pr_err("无效参数: offset=0x%03X size=%d\n", offset, size);
35          mutex_unlock(&edev->lock);
36          return -EINVAL;
37      }
38
39      /* 根据大小读取配置空间 */
40      switch (size) {
41      /* 读取1字节 */
42      case 1: {
43          /* 8位值 */
44          u8 val8;
45          /* 读取1字节 */
46          pci_read_config_byte(pdev, offset, &val8);
47          /* 打印结果 */
48          pr_info("CONFIG[0x%02X]: 0x%02X\n", offset, val8);
49          break;
50      }
51      /* 读取2字节 */
52      case 2: {
53          /* 16位值 */
54          u16 val16;
55          /* 读取2字节 */
56          pci_read_config_word(pdev, offset, &val16);
57          /* 打印结果 */
58          pr_info("CONFIG[0x%02X]: 0x%04X\n", offset, val16);
59          break;
60      }
61      /* 读取4字节 */
62      case 4:
63          /* 读取4字节 */
64          pci_read_config_dword(pdev, offset, &val);
65          /* 打印结果 */
66          pr_info("CONFIG[0x%02X]: 0x%08X\n", offset, val);
67          break;
68      }
69
70      /* 释放锁 */
71      mutex_unlock(&edev->lock);
72
73      /* 返回读取字节数 */
74      return count;
75  }
```

**写入配置空间寄存器**

配置空间寄存器写入接口，权限为0220可写，用户传入参数格式为“offset size value”，写入前会校验配置空间可写寄存器白名单，仅允许修改PCI命令寄存器、缓存配置、中断配置等安全寄存器。

写入配置空间寄存器(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id103 "永久链接至代码")

```c
 1  /* sysfs属性：写入配置空间寄存器 */
 2  static ssize_t config_write_store(struct device *dev,
 3                  struct device_attribute *attr,
 4                  const char *buf, size_t count)
 5  {
 6      /* 获取设备私有数据 */
 7      struct pcie_dev *edev = dev_get_drvdata(dev);
 8      /* 转换为PCI设备 */
 9      struct pci_dev *pdev = to_pci_dev(dev);
10      /* 偏移和写入值 */
11      u32 offset, value;
12      /* 写入大小 */
13      u8 size;
14      int ret;
15
16      /* 检查设备私有数据 */
17      if (!edev)
18          return -ENODEV;
19
20      /* 获取锁 */
21      ret = mutex_lock_interruptible(&edev->lock);
22      if (ret)
23          return ret;
24
25      /* 解析用户输入 */
26      if (sscanf(buf, "%x %hhu %x", &offset, &size, &value) != 3) {
27          pr_err("格式错误: 应为'offset size value'\n");
28          mutex_unlock(&edev->lock);
29          return -EINVAL;
30      }
31
32      /* 检查参数有效性 */
33      if (offset >= 0x100 | (size != 1 && size != 2 && size != 4)) {
34          pr_err("无效参数: offset=0x%03X size=%d\n", offset, size);
35          mutex_unlock(&edev->lock);
36          return -EINVAL;
37      }
38
39      /* 白名单检查，防止误操作 */
40      if (!is_config_writable(offset, size)) {
41          pr_err("寄存器 0x%02X (size=%d) 不在白名单中\n", offset, size);
42          pr_info("允许写入的配置空间寄存器（绝对偏移）:\n");
43          pr_info("  0x04, 0x05 - PCI_COMMAND 命令寄存器\n");
44          pr_info("  0x0C, 0x0D - PCI_LATENCY_TIMER/PCI_CACHE_LINE_SIZE\n");
45          pr_info("  0x3C, 0x3D - PCI_INTERRUPT_LINE/PIN\n");
46          mutex_unlock(&edev->lock);
47          return -EPERM;
48      }
49
50      /* 根据大小写入配置空间 */
51      switch (size) {
52      case 1:
53          /* 写入1字节 */
54          pci_write_config_byte(pdev, offset, (u8)value);
55          break;
56      case 2:
57          /* 写入2字节 */
58          pci_write_config_word(pdev, offset, (u16)value);
59          break;  /* 跳出 switch */
60      case 4:
61          /* 写入4字节 */
62          pci_write_config_dword(pdev, offset, value);
63          break;
64      }
65
66      /* 打印写入结果 */
67      pr_info("CONFIG_WRITE[0x%02X]: 0x%08X (size=%d)\n", offset, value, size);
68
69      /* 释放锁 */
70      mutex_unlock(&edev->lock);
71
72      /* 返回写入字节数 */
73      return count;
74  }
```

**显示BAR空间信息**

BAR空间信息只读查询接口，权限为0444只读，无需用户传入参数，主动遍历设备全部6个BAR资源空间，自动识别IO/内存空间类型、64位寻址属性、预取属性，输出所有BAR的物理基地址、空间大小。

显示BAR空间信息(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id104 "永久链接至代码")

```c
 1  /* sysfs属性：显示BAR空间信息 */
 2  static ssize_t bar_info_show(struct device *dev,
 3                  struct device_attribute *attr, char *buf)
 4  {
 5      /* 转换为PCI设备 */
 6      struct pci_dev *pdev = to_pci_dev(dev);
 7      /* 获取设备私有数据 */
 8      struct pcie_dev *edev = dev_get_drvdata(dev);
 9      /* 循环变量和缓冲区长度 */
10      int i, len = 0;
11
12      /* 打印标题 */
13      len += sprintf(buf + len, "BAR 空间信息:\n");
14
15      /* 遍历BAR0-BAR5 */
16      for (i = 0; i < 6; i++) {
17          /* BAR起始地址和大小 */
18          resource_size_t start, size;
19          /* BAR标志 */
20          unsigned long flags;
21
22          /* 获取BAR起始地址 */
23          start = pci_resource_start(pdev, i);
24          /* 获取BAR大小 */
25          size = pci_resource_len(pdev, i);
26          /* 获取BAR标志 */
27          flags = pci_resource_flags(pdev, i);
28
29          /* 跳过空BAR */
30          if (size == 0)
31              continue;  /* 继续下一个 */
32
33          /* 内存映射BAR */
34          if (flags & IORESOURCE_MEM) {
35              /* 动态选择单位，避免小于1MB时显示为0 */
36              if (size >= 1024 * 1024) {
37                  /* 大于等于1MB，以MB为单位 */
38                  len += sprintf(buf + len,
39                      "BAR%d: MEM 0x%016llX (size=%llu MB)\n",
40                      i, (unsigned long long)start,
41                      (unsigned long long)(size / (1024 * 1024)));
42              } else {
43                  /* 小于1MB，以KB为单位 */
44                  len += sprintf(buf + len,
45                      "BAR%d: MEM 0x%016llX (size=%llu KB)\n",
46                      i, (unsigned long long)start,
47                      (unsigned long long)(size / 1024));
48              }
49          }
50          /* I/O映射BAR */
51          else if (flags & IORESOURCE_IO)
52              len += sprintf(buf + len,
53                  "BAR%d: I/O 0x%08llX\n",                     /* 打印I/O BAR信息 */
54                  i, (unsigned long long)start);
55      }
56
57      /* 检查BAR2是否已映射 */
58      if (edev && edev->bar_mmap)
59          len += sprintf(buf + len, "BAR2 已映射: %p (size=%zu)\n",  /* 打印BAR2映射信息 */
60              edev->bar_mmap, edev->bar_size);
61
62      /* 返回写入字节数 */
63      return len;
64  }
```

**读取BAR空间寄存器**

BAR空间寄存器读取接口，权限为0220可写，支持1/2/4字节自定义位宽读取，用户传入参数格式为“offset size”，可读取网卡中断、DMA等硬件寄存器数值。

读取BAR空间寄存器(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id105 "永久链接至代码")

```c
 1  /* sysfs属性：读取BAR空间寄存器 */
 2  static ssize_t bar_read_store(struct device *dev,
 3                  struct device_attribute *attr,
 4                  const char *buf, size_t count)
 5  {
 6      /* 获取设备私有数据 */
 7      struct pcie_dev *edev = dev_get_drvdata(dev);
 8      /* 偏移和读取值 */
 9      u32 offset, val;
10      /* 读取大小 */
11      u8 size;
12      int ret;
13
14      /* 检查BAR是否已映射 */
15      if (!edev | !edev->bar_mmap) {
16          pr_err("BAR 未映射\n");
17          return -ENODEV;
18      }
19
20      /* 获取锁 */
21      ret = mutex_lock_interruptible(&edev->lock);
22      if (ret)
23          return ret;
24
25      /* 解析用户输入 */
26      if (sscanf(buf, "%x %hhu", &offset, &size) != 2) {
27          pr_err("格式错误: 应为 'offset size'\n");
28          mutex_unlock(&edev->lock);
29          return -EINVAL;
30      }
31
32      /* 检查参数有效性 */
33      if (offset >= edev->bar_size | (size != 1 && size != 2 && size != 4)) {
34          pr_err("无效参数: offset=0x%04X size=%d\n", offset, size);
35          mutex_unlock(&edev->lock);
36          return -EINVAL;
37      }
38
39      /* 根据大小读取BAR空间 */
40      switch (size) {
41      case 1: {
42          /* 读取1字节 */
43          u8 val8 = readb(edev->bar_mmap + offset);
44          /* 打印结果 */
45          pr_info("BAR[0x%04X]: 0x%02X\n", offset, val8);
46          break;
47      }
48      /* 读取2字节 */
49      case 2: {
50          /* 读取2字节 */
51          u16 val16 = readw(edev->bar_mmap + offset);
52          /* 打印结果 */
53          pr_info("BAR[0x%04X]: 0x%04X\n", offset, val16);
54          break;
55      }
56      /* 读取4字节 */
57      case 4:
58          /* 读取4字节 */
59          val = readl(edev->bar_mmap + offset);
60          /* 打印结果 */
61          pr_info("BAR[0x%04X]: 0x%08X\n", offset, val);
62          break;
63      }
64
65      /* 释放锁 */
66      mutex_unlock(&edev->lock);
67
68      /* 返回读取字节数 */
69      return count;
70  }
```

**写入BAR空间寄存器**

BAR空间寄存器写入接口，权限为0220可写，用户传入参数格式为“offset size value”，写入前会校验BAR空间可写寄存器白名单，仅允许写入中断状态寄存器、DMA控制寄存器等安全寄存器。

写入BAR空间寄存器(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id106 "永久链接至代码")

```c
 1  /* sysfs属性：写入BAR空间寄存器 */
 2  static ssize_t bar_write_store(struct device *dev,
 3                  struct device_attribute *attr,
 4                  const char *buf, size_t count)
 5  {
 6      /* 获取设备私有数据 */
 7      struct pcie_dev *edev = dev_get_drvdata(dev);
 8      /* 偏移和写入值 */
 9      u32 offset, value;
10      /* 写入大小 */
11      u8 size;
12      int ret;
13
14      /* 检查BAR是否已映射 */
15      if (!edev | !edev->bar_mmap) {
16          pr_err("BAR 未映射\n");
17          return -ENODEV;
18      }
19
20      /* 获取锁 */
21      ret = mutex_lock_interruptible(&edev->lock);
22      if (ret)
23          return ret;
24
25      /* 解析用户输入 */
26      if (sscanf(buf, "%x %hhu %x", &offset, &size, &value) != 3) {
27          pr_err("格式错误: 应为 'offset size value'\n");
28          mutex_unlock(&edev->lock);
29          return -EINVAL;
30      }
31
32      /* 检查参数有效性 */
33      if (offset >= edev->bar_size | (size != 1 && size != 2 && size != 4)) {
34          pr_err("无效参数: offset=0x%04X size=%d\n", offset, size);
35          mutex_unlock(&edev->lock);
36          return -EINVAL;
37      }
38
39      /* 白名单检查，防止误操作 */
40      if (!is_bar_writable(offset)) {
41          pr_err("BAR寄存器 0x%04X 不在白名单中，禁止写入\n", offset);
42          pr_info("允许写入的BAR寄存器:\n");
43          pr_info("  0x00B4 - RTK_PCI_HISR0 中断状态0\n");
44          pr_info("  0x00BC - RTK_PCI_HISR1 中断状态1\n");
45          pr_info("  0x0300 - RTK_PCI_CTRL DMA控制\n");
46          mutex_unlock(&edev->lock);
47          return -EPERM;
48      }
49
50      /* 根据大小写入BAR空间 */
51      switch (size) {
52      /* 写入1字节 */
53      case 1:
54          writeb((u8)value, edev->bar_mmap + offset);
55          break;
56      /* 写入2字节 */
57      case 2:
58          writew((u16)value, edev->bar_mmap + offset);
59          break;
60      /* 写入4字节 */
61      case 4:
62          writel(value, edev->bar_mmap + offset);
63          break;
64      }
65
66      /* 打印写入结果 */
67      pr_info("BAR_WRITE[0x%04X]: 0x%08X (size=%d)\n", offset, value, size);
68
69      /* 释放锁 */
70      mutex_unlock(&edev->lock);
71
72      /* 返回写入字节数 */
73      return count;
74  }
```

**统一属性组管理接口**

依托内核ATTRIBUTE_GROUPS机制，批量统一管理上述6个功能sysfs属性文件，自动完成设备加载时的接口创建、设备卸载时的接口销毁，无需单独编写注册、注销逻辑，同时统一管控所有用户层调试接口权限，简化代码架构。

统一属性组管理接口(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id107 "永久链接至代码")

```c
 1  /* sysfs属性 */
 2  static DEVICE_ATTR(config_space, 0444, config_space_show, NULL);  /* 显示配置空间信息只读属性 */
 3  static DEVICE_ATTR(config_read, 0200, NULL, config_read_store);   /* 配置空间寄存器读取只写属性 */
 4  static DEVICE_ATTR(config_write, 0200, NULL, config_write_store); /* 配置空间寄存器写入只写属性 */
 5  static DEVICE_ATTR(bar_info, 0444, bar_info_show, NULL);          /* 显示BAR空间信息只读属性 */
 6  static DEVICE_ATTR(bar_read, 0200, NULL, bar_read_store);         /* BAR空间读取只写属性 */
 7  static DEVICE_ATTR(bar_write, 0200, NULL, bar_write_store);       /* BAR空间写入只写属性 */
 8
 9  /* 将属性数组添加到组 */
10  static struct attribute *pcie_exp_attrs[] = {
11      &dev_attr_config_space.attr,
12      &dev_attr_config_read.attr,
13      &dev_attr_config_write.attr,
14      &dev_attr_bar_info.attr,
15      &dev_attr_bar_read.attr,
16      &dev_attr_bar_write.attr,
17      NULL,
18  };
19
20  /* 属性组定义 */
21  static const struct attribute_group pcie_exp_group = {
22      .attrs = pcie_exp_attrs,
23  };
```

#### 8.6.1.10. probe函数[¶](#id36 "永久链接至标题")

probe函数是PCI驱动的核心回调入口，当内核匹配到适配的PCIe设备时自动触发，完成设备启用、内存申请、锁初始化、私有数据绑定，执行设备信息解析函数等功能。

probe函数(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id108 "永久链接至代码")

```c
 1  /* 设备探测 */
 2  static int pcie_explorer_probe(struct pci_dev *pdev,
 3                  const struct pci_device_id *id)
 4  {
 5      /* 设备私有数据指针 */
 6      struct pcie_dev *edev;
 7      /* 返回值 */
 8      int ret;
 9
10      /* 打印设备发现信息 */
11      pr_info("%s: 发现设备 %s    \n", DRV_NAME, pci_name(pdev));
12
13      /* 分配设备私有数据结构 */
14      edev = kzalloc(sizeof(*edev), GFP_KERNEL);
15      if (!edev)
16          return -ENOMEM;
17
18      /* 初始化互斥锁 */
19      mutex_init(&edev->lock);
20
21      /* 保存PCI设备指针 */
22      edev->pdev = pdev;
23      /* 将私有数据绑定到设备 */
24      pci_set_drvdata(pdev, edev);
25
26      /* 使能PCI设备内存资源 */
27      ret = pci_enable_device_mem(pdev);
28      if (ret) {
29          pr_err("pci_enable_device_mem 失败: %d\n", ret);
30          goto err_free;
31      }
32
33      pr_info("------------ 配置空间解析 ------------\n");
34      /* 解析配置空间信息 */
35      print_config_space(pdev);
36      /* 解析标准Capability */
37      parse_capabilities(pdev);
38      /* 解析扩展Capability */
39      parse_extended_capabilities(pdev);
40
41      pr_info("------------ BAR空间解析 ------------\n");
42      /* 解析BAR空间信息 */
43      parse_bar_info(edev);
44      /* 映射并探索BAR2空间 */
45      map_and_explore_bar(edev);
46
47      /* 创建sysfs属性组 */
48      ret = devm_device_add_group(&pdev->dev, &pcie_exp_group);
49      if (ret)
50          goto err_disable;
51
52      /* 打印初始化完成信息 */
53      pr_info("%s: 设备 %s 初始化完成    \n", DRV_NAME, pci_name(pdev));
54
55      return 0;
56
57  err_disable:
58      pci_disable_device(pdev);  /* 禁用PCI设备 */
59  err_free:
60      kfree(edev);  /* 释放设备私有数据 */
61      return ret;
62  }
```

关键说明：

- 第11行：通过pci_name(pdev)获取PCI设备名称并打印设备发现日志。
    
- 第14行：采用kzalloc手动申请pcie_dev私有结构体内存。
    
- 第19行：通过mutex_init初始化互斥锁，为后续所有寄存器读写、sysfs并发访问提供保护。
    
- 第27行：调用pci_enable_device_mem(pdev)仅启用PCI设备内存资源，本驱动仅操作内存寄存器。
    
- 第33-39行：调用前面讲解过的函数解析标准配置空间、标准Capability、扩展Capability。
    
- 第41-45行：调用前面讲解过的函数解析BAR空间信息、映射并探索BAR2空间。
    
- 第48行：调用devm_device_add_group接口，动态注册自定义sysfs属性组，自动完成6个sysfs交互接口的注册。
    

#### 8.6.1.11. remove函数[¶](#remove "永久链接至标题")

remove卸载函数，释放probe阶段申请的所有硬件、内存、锁、设备节点资源，避免内存泄漏与资源残留。

remove函数(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id109 "永久链接至代码")

```c
 1  static void pcie_explorer_remove(struct pci_dev *pdev)
 2  {
 3      /* 获取设备私有数据 */
 4      struct pcie_dev *edev = pci_get_drvdata(pdev);
 5
 6      /* 打印设备移除信息 */
 7      pr_info("%s: 移除设备 %s    \n", DRV_NAME, pci_name(pdev));
 8
 9      /* 检查BAR是否已映射 */
10      if (edev && edev->bar_mmap)
11          pci_iounmap(pdev, edev->bar_mmap);  /* 解除BAR映射 */
12
13      /* 移除sysfs属性组 */
14      device_remove_group(&pdev->dev, &pcie_exp_group);
15
16      /* 禁用PCI设备 */
17      pci_disable_device(pdev);
18
19      /* 销毁互斥锁 */
20      mutex_destroy(&edev->lock);
21
22      /* 释放设备私有数据 */
23      kfree(edev);
24
25      /* 打印移除完成信息 */
26      pr_info("%s: 设备 %s 已移除    \n", DRV_NAME, pci_name(pdev));
27  }
```

关键说明：

- 第7行：通过pci_name(pdev)获取设备名称并打印设备移除日志。
    
- 第10-11行：先判断私有数据与BAR映射地址是否有效，再调用pci_iounmap解除BAR2物理地址到内核虚拟地址的MMIO映射。
    
- 第14行：调用device_remove_group手动卸载设备sysfs属性组，主动清空所有用户层调试接口文件。
    
- 第17行：调用pci_disable_device(pdev)禁用PCI设备的内存与IO硬件资源，释放设备对PCI总线的占用。
    
- 第20行：调用mutex_destroy销毁probe阶段初始化的设备互斥锁，释放内核锁资源。
    
- 第23行：通过kfree手动释放kzalloc申请的私有数据内存，回收设备自定义资源。
    

#### 8.6.1.12. 电源管理[¶](#id37 "永久链接至标题")

**设备休眠**

suspend函数是PCI设备电源管理休眠回调函数，系统进入休眠、挂起、待机状态时由内核自动触发。

suspend函数(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id110 "永久链接至代码")

```c
 1  static int pcie_explorer_suspend(struct pci_dev *pdev, pm_message_t state)
 2  {
 3      /* 打印挂起信息 */
 4      pr_info("%s: suspend %s\n", DRV_NAME, pci_name(pdev));
 5
 6      /* 保存PCI设备状态 */
 7      pci_save_state(pdev);
 8      /* 禁用PCI设备 */
 9      pci_disable_device(pdev);
10
11      return 0;
12  }
```

关键说明：

- 第7行：调用pci_save_state(pdev)自动读取并保存PCIe设备当前全部配置空间寄存器状态，将设备工作参数存入内核缓存。
    
- 第9行：调用pci_disable_device(pdev)关闭PCI设备总线资源，释放设备占用的内存空间与总线通道，让设备进入低功耗休眠模式。
    

**设备唤醒**

resume函数是PCI设备电源管理唤醒回调函数，系统从休眠状态唤醒、恢复正常工作时由内核自动触发。

resume函数(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id111 "永久链接至代码")

```c
 1  static int pcie_explorer_resume(struct pci_dev *pdev)
 2  {
 3      int ret;
 4
 5      /* 打印恢复信息 */
 6      pr_info("%s: resume %s\n", DRV_NAME, pci_name(pdev));
 7
 8      /* 恢复PCI设备状态 */
 9      pci_restore_state(pdev);
10      /* 重新使能设备内存资源 */
11      ret = pci_enable_device_mem(pdev);
12      if (ret)
13          pr_err("pci_enable_device_mem 失败: %d\n", ret);
14
15      return ret;
16  }
```

关键说明：

- 第9行：调用pci_restore_state(pdev)读取休眠阶段保存的设备寄存器快照数据，批量还原设备配置空间所有参数。
    
- 第11行：调用pci_enable_device_mem(pdev)重新启用PCI设备内存资源，本驱动仅BAR2空间MMIO映射。
    

#### 8.6.1.13. PCI设备ID表与驱动注册[¶](#id38 "永久链接至标题")

PCI设备ID表与驱动注册(位于linux_driver/42_pcie_subsystem/pcie_explorer.c)[¶](#id112 "永久链接至代码")

```c
 1  /* PCI设备ID表 */
 2  static const struct pci_device_id pcie_explorer_ids[] = {
 3      { PCI_DEVICE(0x10EC, 0x8179) },  /* RTL8188EE */
 4      { PCI_DEVICE(0x10EC, 0xC821) },  /* RTL8821CE */
 5      { PCI_DEVICE(0x10EC, 0xC822) },  /* RTL8822CE */
 6      { PCI_DEVICE(0x10EC, 0xC82F) },  /* RTL8822CE */
 7      { PCI_DEVICE(0x10EC, 0xb852) },  /* RTL8852BE */
 8      { PCI_DEVICE(0x10EC, 0xb85b) },  /* RTL8852BE */
 9      { }
10  };
11  /* 导出设备ID表到用户空间 */
12  MODULE_DEVICE_TABLE(pci, pcie_explorer_ids);
13
14  static struct pci_driver pcie_explorer_driver = {
15      .name     = DRV_NAME,
16      .id_table = pcie_explorer_ids,
17      .probe    = pcie_explorer_probe,
18      .remove   = pcie_explorer_remove,
19      .suspend  = pcie_explorer_suspend,
20      .resume   = pcie_explorer_resume,
21  };
22  /* 自动注册/注销PCI驱动 */
23  module_pci_driver(pcie_explorer_driver);
```

关键说明：

- 第2-8行：通过pci_device_id结构体数组定义多款Realtek无线网卡设备ID，统一厂商VID为0x10EC，分别匹配对应的Realtek无线网卡。
    
- 第12行：通过MODULE_DEVICE_TABLE宏将自定义的PCI设备匹配表导出至内核用户空间，作用是告知系统udev设备管理器与热插拔子系统当前驱动支持的硬件列表。
    
- 第14-21行：初始化标准pci_driver核心结构体，完成各功能回调绑定。
    
- 第23行：采用module_pci_driver宏，替代传统module_init、module_exit函数的方式，内核自动生成驱动注册与注销入口代码。
    

### 8.6.2. Makefile说明[¶](#makefile "永久链接至标题")

本节实验使用的Makefile如下所示，编写该Makefile时，只需要根据实际情况修改变量KERNEL_DIR、CROSS_COMPILE和obj-m即可。

Makefile(位于linux_driver/42_pcie_subsystem/Makefile)[¶](#id113 "永久链接至代码")

```makefile
 1  #指定内核路径,可以是相对路径或绝对路径
 2  KERNEL_DIR=../../kernel/
 3  # KERNEL_DIR=/home/guest/LubanCat_Linux_Generic_Full_SDK/kernel-6.1
 4  # KERNEL_DIR=/home/guest/LubanCat_Linux_rk3588_SDK/kernel
 5
 6  #指定目标架构为arm64
 7  ARCH=arm64
 8
 9  #指定交叉编译工具链的前缀
10  CROSS_COMPILE=aarch64-linux-gnu-
11  # CROSS_COMPILE=/home/guest/LubanCat_Linux_Generic_Full_SDK/prebuilts/gcc/linux-x86/aarch64/gcc-arm-10.3-2021.07-x86_64-aarch64-none-linux-gnu/bin/aarch64-none-linux-gnu-
12
13  #导出为环境变量
14  export  ARCH  CROSS_COMPILE
15
16  #指定要编译的内核模块目标文件
17  obj-m += pcie_explorer.o
18
19  #all :默认目标，执行时会编译驱动模块
20  #$(MAKE) ：调用make工具
21  #-C $(KERNEL_DIR) ：指定的内核源码目录
22  #M=$(CURDIR) ：模块的源码位于当前目录
23  #modules ：编译模块
24  all:
25      $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) modules
26
27  .PHONE:clean
28
29  #清理编译生成的文件
30  clean:
31      $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) clean
```

### 8.6.3. 编译驱动[¶](#id39 "永久链接至标题")

在实验目录下输入 `make` 即可编译驱动，编译得到内核模块pcie_explorer.ko。

### 8.6.4. 程序运行结果[¶](#id40 "永久链接至标题")

如出现 `Permission denied` 或类似字样，请注意用户权限，大部分操作硬件外设的功能，几乎都需要root用户权限，简单的解决方案是在执行语句前加入sudo或以root用户运行程序。

#### 8.6.4.1. 实验操作[¶](#id41 "永久链接至标题")

以LubanCat2板卡搭配RTL8821CE网卡为例进行说明，先装配好PCIe网卡再给板卡上电，避免带电操作损坏板卡。

需要先确认网卡的VID和PID能够匹配本实验的驱动：

```bash
#查看网卡的VID和PID
lspci -nn

#信息输出如下
00:00.0 PCI bridge [0604]: Rockchip Electronics Co., Ltd RK3568 Remote Signal Processor [1d87:3566] (rev 01)
01:00.0 Network controller [0280]: Realtek Semiconductor Co., Ltd. RTL8821CE 802.11ac PCIe Wireless Network Adapter [10ec:c821]
```

可以从输出信息看到实际使用的RTL8821CE网卡的VID和PID是[10ec:c821]，能够匹配本实验驱动。如果不能匹配就需要自行在pci_device_id列表添加网卡实际的VID和PID。

因为系统会默认加载内核自带的网卡驱动，所以需要先卸载内核自带的网卡驱动，再加载本实验驱动：

```bash
 1  #查看当前系统加载的驱动模块
 2  lsmod
 3
 4  #4.19.232内核系统信息输出如下
 5  Module                  Size  Used by
 6  rfcomm                 61440  12
 7  bnep                   24576  2
 8  rtk_btusb              57344  0
 9  btusb                  40960  0
10  btrtl                  16384  1 btusb
11  btbcm                  16384  1 btusb
12  btintel                20480  1 btusb
13  8821ce               1859584  0
14  bluetooth             450560  39 btrtl,btintel,btbcm,bnep,btusb,rfcomm
15
16  #6.1.99内核系统信息输出如下
17  Module                  Size  Used by
18  btusb                  53248  0
19  btrtl                  28672  1 btusb
20  btbcm                  24576  1 btusb
21  rtw88_8821ce           16384  0
22  rtw88_8821c            90112  1 rtw88_8821ce
23  btintel                40960  1 btusb
24  bluetooth             716800  27 btrtl,btintel,btbcm,btusb
25  ecdh_generic           16384  2 bluetooth
26  ecc                    32768  1 ecdh_generic
27  rtw88_pci              28672  1 rtw88_8821ce
28  rtw88_core            208896  2 rtw88_pci,rtw88_8821c
29  ip_tables              32768  0
30  rtc_rk808              20480  0
31  rtc_hym8563            16384  1
```

注解

由于4.19.232内核使用的是kernel/drivers/net/wireless/rockchip_wlan/rtl8821ce驱动，6.1.99内核使用的是kernel/drivers/net/wireless/realtek/rtw88驱动，因此两个版本的内核加载的驱动名称模块不一样，但都能明显确认哪个模块是网卡驱动。

卸载对应的网卡驱动再加载本实验驱动：

```bash
 1  #4.19.232内核系统卸载8821ce模块
 2  sudo rmmod 8821ce
 3
 4  #6.1.99内核系统卸载rtw88_8821ce模块
 5  sudo rmmod rtw88_8821ce
 6
 7  #加载实验驱动
 8  sudo insmod pcie_explorer.ko
 9
10  #信息输出如下
11  [   31.814097] pcie_explorer: 发现设备 0000:01:00.0
12  [   31.814166] ------------ 配置空间解析 ------------
13  [   31.814254]       PCIe 配置空间
14  [   31.814266]   Vendor: 0x10EC  Device: 0xC821                 #VID和PID和lspci读取到的一致
15  [   31.814277]   Revision: 0x00  Header: 0x00 Single-function   #芯片修订版本A0，普通设备，单功能
16  [   31.814454]   Class: 0x02800000 (IF=0x00 Sub=0x80 Base=0x02) #IF=0x00表示无特定编程接口，Sub=0x80表示无线控制器，Base=0x02表示网络控制器
17  [   31.814463]   Command: 0x0003 [IO MEM ]      #Command寄存器0x0003即BIT(0)=1表示IO端口访问已使能，BIT(1)=1表示MMIO内存访问已使能，BIT(2)=0表示DMA未使能
18  [   31.814470]   Status: 0x0010                 #Status寄存器0x0010即BIT(4)=1表示设备有Capability链表
19  [   31.814477]   Subsys: Vendor=0x10EC Device=0xC821
20  [   31.814485]   IRQ: Line=106 Pin=1            #系统分配的中断号106，中断引脚为1
21  [   31.814492]   Cache: 32 bytes  Latency: 0    #系统缓存行大小32字节，延迟计时器值为0
22  [   31.814498]   Capability PTR: 0x40           #Capability链表从配置空间偏移0x40开始
23  [   31.814506]
24  [   31.814512]       Capability 链表
25  [   31.814541]   [0] @0x40: ID=0x01 (Power Management)
26  [   31.814554]       PM: State=0, D1=No, D2=No, PME=No, PMEStatus=No    #State=0表示当前处于D0（全功率）状态，PME Status=No表示无唤醒事件
27  [   31.814591]   [1] @0x50: ID=0x05 (MSI)
28  [   31.814614]       MSI: Enable=No, Addr64=Yes, Data=0x0000            #Enable=No表示MSI中断未使能，Addr64=Yes表示支持64位MSI地址
29  [   31.814680]   [2] @0x70: ID=0x10 (PCI Express)
30  [   31.814703]       DEBUG: LNKCAP=0x00075C11, LNKSTA=0x1011
31  [   31.814712]       PCIe: MaxLanes=x1, MaxSpeed=2.5GT/s    #LNKCAP=0x00075C11其中Bit[3:0]=0x1表示最大速度Gen1(2.5 GT/s)，Bit[9:4]=0x01表示最大宽度x1，Bit[10:11]=0x01表示支持ASPM
32  [   31.814719]             NegLanes=x1, NegSpeed=2.5GT/s    #LNKSTA=0x1011其中Bit[3:0]=0x1表示当前协商速度Gen1(2.5 GT/s)，Bit[9:4]=0x01表示当前协商宽度x1，Bit[12]=1表示使用Slot Clock
33  [   31.814835]   共 3 个 Capability
34  [   31.814841]
35  [   31.814847]       Extended Capability
36  [   31.814862]   [0] @0x100: ID=0x0001 (Advanced Error Reporting)   #高级错误报告
37  [   31.814914]   [1] @0x148: ID=0x0003 (Device Serial Number)       #设备序列号
38  [   31.815057]   [2] @0x17C: ID=0x000B (Vendor Specific)            #Realtek私有扩展功能
39  [   31.815087]   [3] @0x160: ID=0x001E (L1 PM Substates)            #L1电源管理子状态
40  [   31.815221]   [4] @0x170: ID=0x001F (Precision Time Measurement) #精确时间测量
41  [   31.815227]   共 5 个 Extended Capability
42  [   31.815233]
43  [   31.815240] ------------ BAR空间解析 ------------
44  [   31.815246]       BAR 空间解析
45  [   31.815259]   BAR0: I/O  0xF4101000 (size=256)                   #BAR0是IO端口空间，地址0xF4101000，大小256B
46  [   31.815273]   BAR1: MEM  0x0000000000000000 (size=0 KB)
47  [   31.815286]   BAR2: MEM  0x00000000F4200000 (size=64 KB) 64bit   #BAR2是主要寄存器空间，地址0xF4200000，大小64KB
48  [   31.815300]   BAR4: MEM  0x0000000000000000 (size=0 KB)          #BAR2是64位BAR，占用BAR2 + BAR3两个槽位，所以跳过了BAR3
49  [   31.815312]   BAR5: MEM  0x0000000000000000 (size=0 KB)
50  [   31.815319]
51  [   31.815325]       BAR2 MMIO 探索
52  [   31.815342]   基地址: 0xF4200000, 大小: 65536 bytes
53  [   31.816297]   MMIO 虚拟地址: 000000002309e10a
54  [   31.816309]   读取前64个字节的寄存器:
55  [   31.816329]     0000: 51DDBEE1 00030412 00203023 00000000
56  [   31.816357]     0010: 484E6B43 95A3A155 00400100 00C6A100
57  [   31.816380]     0020: 0B0102C0 5FCE1DDF 6D0EF9DE 08A30448
58  [   31.816404]     0030: B161FDFF 18000000 02001000 00000000
59  [   31.816424]
60  [   31.816433]
61  [   31.816505] pcie_explorer: 设备 0000:01:00.0 初始化完成
```

可以从信息看到当前设备0000:01:00.0(RTL8821CE 0x10EC:0xC821)，链路状态为PCIe Gen1 x1 (2.5GT/s)，BAR2空间基地址0xF4200000，大小64KB。

进入网卡对应的sysfs目录进行测试：

```bash
#进入sysyfs目录，路径根据前面打印的设备名称0000:01:00.0确定
cd /sys/bus/pci/devices/0000:01:00.0/

#显示配置空间信息
cat config_space

#信息输出如下
PCIe 配置空间 (前 256 字节):
0x00: 0xC82110EC
0x04: 0x00100003
0x08: 0x02800000
0x0C: 0x00000008
...

#读取Vendor ID，偏移0x00，2字节
sudo sh -c "echo 0x00 2 > config_read"

#信息输出如下，0x10EC就是RTL8821CE网卡的VID
[  342.970350] CONFIG[0x00]: 0x10EC

#读取Device ID，偏移0x02，2字节
sudo sh -c "echo 0x02 2 > config_read"

#信息输出如下，0xC821就是RTL8821CE网卡的PID
[  637.267519] CONFIG[0x02]: 0xC821

#读取Command寄存器，偏移0x04，2字节
sudo sh -c "echo 0x04 2 > config_read"

#信息输出如下，目前启用IO+MEM
[  667.864607] CONFIG[0x04]: 0x0003

#写入Command寄存器，偏移0x04，2字节，数据0x0007，启动IO+MEM+BusMaster
sudo sh -c "echo 0x04 2 0x0007 > config_write"

#信息输出如下
[  796.366976] CONFIG_WRITE[0x04]: 0x00000007 (size=2)

#写入非白名单配置寄存器会被拒绝
sudo sh -c "echo 0x10 4 0x00 > config_write"

#信息输出如下
[  953.018945] 寄存器 0x10 (size=4) 不在白名单中
[  953.019012] 允许写入的配置空间寄存器（绝对偏移）:
[  953.019032]   0x04, 0x05 - PCI_COMMAND 命令寄存器
[  953.019040]   0x0C, 0x0D - PCI_LATENCY_TIMER/PCI_CACHE_LINE_SIZE
[  953.019047]   0x3C, 0x3D - PCI_INTERRUPT_LINE/PIN

#显示BAR空间信息
cat bar_info

#信息输出如下
BAR 空间信息:
BAR0: I/O 0x00001000
BAR2: MEM 0x00000000F4200000 (size=64 KB)
BAR2 已映射: 00000000dce8a77b (size=65536)

#读取BAR2起始处的寄存器
sudo sh -c "echo 0x00 4 > bar_read"

#信息输出如下
[ 1203.421626] BAR[0x0000]: 0x51DDBEE1

#读取RTK_PCI_HISR0中断状态0寄存器
sudo sh -c "echo 0xB4 4 > bar_read"

#信息输出如下
[ 1382.148634] BAR[0x00B4]: 0xC0000000

#写入RTK_PCI_HISR0中断状态0寄存器，向值为1的位写入1即可清除对应中断标志，写入读取值即可全部清除，因此写入读取到的0xC0000000
sudo sh -c "echo 0xB4 4 0xC0000000 > bar_write"

#信息输出如下
[ 1635.335286] BAR_WRITE[0x00B4]: 0xC0000000 (size=4)

#再次读取RTK_PCI_HISR0中断状态0寄存器
sudo sh -c "echo 0xB4 4 > bar_read"

#信息输出如下，全部位都为0，清除全部中断标志成功
[ 1661.326507] BAR[0x00B4]: 0x00000000

#写入非白名单BAR寄存器会被拒绝
sudo sh -c "echo 0xB8 4 0x0000001 > bar_write"

#信息输出如下
[ 1771.404406] BAR寄存器 0x00B8 不在白名单中，禁止写入
[ 1771.404477] 允许写入的BAR寄存器:
[ 1771.404486]   0x00B4 - RTK_PCI_HISR0 中断状态0
[ 1771.404494]   0x00BC - RTK_PCI_HISR1 中断状态1
[ 1771.404502]   0x0300 - RTK_PCI_CTRL DMA控制
```

以上测试各sysfs接口均正常，白名单机制可防止写入非法寄存器，因此可放心操作。

### 8.6.5. 实验注意事项[¶](#id42 "永久链接至标题")

- 避免非法映射操作：驱动仅对BAR2空间进行MMIO映射，禁止修改代码映射其他BAR空间，部分BAR空间为设备只读状态，强行映射读写可能会触发硬件保护机制。
    
- 白名单机制：实验中仅可对白名单内的配置空间、BAR空间寄存器执行写入操作，禁止通过代码修改白名单强行写入核心寄存器。设备厂商ID、链路配置、硬件状态等关键寄存器被篡改后，会直接导致网卡失效。
    
- 硬件状态观察：若修改了白名单，操作其他BAR寄存器过程中，出现网卡断连、内核日志刷屏报错、设备无响应等异常，需立即停止操作并卸载驱动，重启系统恢复硬件默认状态。
    

## 8.7. PCI DMA驱动实验[¶](#pci-dma "永久链接至标题")

本实验驱动基于Linux PCI子系统与DMA子系统框架设计，适配Realtek RTL8188EE/RTL8821CE/RTL8822CE/RTL8852BE系列PCIe无线网卡设备。 实现PCI RX DMA描述符环初始化、DMA缓冲区映射、硬件DMA寄存器配置、DMA资源管理等功能，同时基于sysfs向用户层展示DMA状态、描述符环详情等调试接口。

本章的示例代码目录为： **linux_driver/42_pcie_subsystem**

注解

本实验驱动大量参考至瑞芯微6.1.99版本内核的drivers/net/wireless/realtek/rtw88/pci.c驱动，并且由于Realtek未公开相关寄存器手册，相关寄存器定义从rtw88/pci.h中获取。

注意

本实验驱动仅将主机侧的DMA描述符结构和部分寄存器搭起来了，设备实际未加载firmware，没有完成WiFi芯片真正工作所需要的完整初始化流程，DMA不会真正传输数据，要想真正实现前后还有大量的步骤！

### 8.7.1. 补充前置知识[¶](#id43 "永久链接至标题")

#### 8.7.1.1. skb缓冲区[¶](#skb "永久链接至标题")

skb（struct sk_buff，套接字缓冲区）是Linux内核网络子系统的核心数据缓冲区，专为网络帧收发设计，自带数据指针、长度、协议栈私有控制块，相较于普通kmalloc内存， 可直接对接内核网络协议栈，无需二次拷贝转换。

#### 8.7.1.2. TX/RX DMA环形队列[¶](#tx-rx-dma "永久链接至标题")

无线网卡的DMA收发体系基于环形队列（Ring Buffer）实现，分为接收RX环与发送TX环。环形队列是硬件DMA与内核软件协同工作的载体，解决了高速网络帧收发的连续调度、流水线处理、资源复用等问题。

RX接收DMA环为设备写、内核读的单向接收队列，用于网卡硬件接收空中无线帧，通过DMA直接写入系统内存。由RX描述符环（一致性DMA内存）和绑定的skb数据缓冲区组成。 工作流程为：驱动初始化时预分配所有skb、完成DMA映射、填充描述符并告知硬件基地址与队列大小；网卡收到无线帧后，根据当前硬件指针，自动将帧数据DMA写入对应skb缓冲区；写入完成后更新硬件指针，内核轮询指针变化即可读取数据。

TX发送DMA环为内核写、设备读的单向发送队列，用于内核将待发送网络帧交付给网卡，由DMA搬运至硬件发送缓冲区并空中发送。由TX描述符环（一致性DMA内存）和绑定的skb数据缓冲区组成。 工作流程为：内核将待发送帧封装skb，填充TX描述符、绑定DMA地址；更新软件写指针告知硬件有新数据包；硬件读取描述符、DMA读取内存数据、完成发送；发送完成后更新硬件读指针，内核回收skb资源。

### 8.7.2. 驱动代码详解[¶](#id44 "永久链接至标题")

#### 8.7.2.1. 核心定义与数据结构[¶](#id45 "永久链接至标题")

参考内核源码drivers/net/wireless/realtek/rtw88/pci.h中相关寄存器定义，包括DMA寄存器偏移、位掩码、缓冲区参数等； 定义DMA接收描述符结构体与设备私有数据结构体。

核心定义与数据结构(位于linux_driver/42_pcie_subsystem/pcie_dma.c)[¶](#id114 "永久链接至代码")

```c
 1  #define DRV_NAME    "pcie_dma"  /* 驱动名称 */
 2  #define DRV_VERSION "1.0"       /* 驱动版本号 */
 3
 4  /* 以下寄存器地址全部来自rtw88驱动的pci.h */
 5
 6  /* DMA控制寄存器 */
 7  #define RTK_PCI_CTRL              0x300     /* DMA控制寄存器基地址 */
 8  #define BIT_RST_TRXDMA_INTF       BIT(20)   /* 复位TX/RX DMA接口 */
 9  #define BIT_RX_TAG_EN             BIT(15)   /* 使能RX Tag */
10
11  /* RX DMA描述符环寄存器 */
12  #define RTK_PCI_RXBD_DESA_MPDUQ   0x338     /* RX环基地址 */
13  #define RTK_PCI_RXBD_NUM_MPDUQ    0x382     /* RX环描述符数量 */
14  #define RTK_PCI_RXBD_IDX_MPDUQ    0x3B4     /* RX环索引 */
15
16  /* DMA环大小寄存器 */
17  #define RTK_PCI_TXBD_NUM_VOQ      0x384     /* VO队列环大小 */
18  #define RTK_PCI_TXBD_NUM_VIQ      0x386     /* VI队列环大小 */
19  #define RTK_PCI_TXBD_NUM_BEQ      0x388     /* BE队列环大小 */
20  #define RTK_PCI_TXBD_NUM_BKQ      0x38A     /* BK队列环大小 */
21  #define RTK_PCI_TXBD_NUM_MGMTQ    0x380     /* 管理队列环大小 */
22  #define RTK_PCI_TXBD_NUM_HI0Q     0x38C     /* 高优先级队列环大小 */
23  #define RTK_PCI_TXBD_NUM_H2CQ     0x1328    /* H2C队列环大小 */
24
25  /* DMA索引寄存器*/
26  #define RTK_PCI_TXBD_IDX_VOQ      0x3A0     /* VO队列索引寄存器 */
27  #define RTK_PCI_TXBD_IDX_VIQ      0x3A4     /* VI队列索引寄存器 */
28  #define RTK_PCI_TXBD_IDX_BEQ      0x3A8     /* BE队列索引寄存器 */
29  #define RTK_PCI_TXBD_IDX_BKQ      0x3AC     /* BK队列索引寄存器 */
30  #define RTK_PCI_TXBD_IDX_MGMTQ    0x3B0     /* 管理队列索引寄存器 */
31  #define RTK_PCI_TXBD_IDX_HI0Q     0x3B8     /* 高优先级队列索引寄存器 */
32  #define RTK_PCI_TXBD_IDX_H2CQ     0x132C    /* H2C队列索引寄存器 */
33
34  /* 读写指针清零寄存器 */
35  #define RTK_PCI_TXBD_RWPTR_CLR    0x39C     /* 写0xFFFFFFFF清零所有环的读写指针 */
36
37  /* 描述符索引掩码 */
38  #define TRX_BD_IDX_MASK           GENMASK(11, 0)   /* 索引低12位有效 */
39  #define TRX_BD_HW_IDX_MASK        GENMASK(27, 16)  /* 硬件索引在bit[27:16] */
40
41  /* RX 缓冲区大小和描述符环大小 */
42  #define RTK_PCI_RX_BUF_SIZE      (11454 + 24)  /* 每个RX数据缓冲区大小11478字节 */
43  #define RTK_MAX_RX_DESC_NUM       512          /* RX描述符环最大描述符数量 */
44
45  /* RX DMA描述符结构体 */
46  struct rtw_pci_rx_buffer_desc {
47      __le16 buf_size;        /* 缓冲区容量 */
48      __le16 total_pkt_size;  /* 接收到的总包大小 */
49      __le32 dma;             /* 数据缓冲区DMA物理地址 */
50  };
51
52  /* 设备私有数据结构体  */
53  struct dma_exp_dev {
54      struct pci_dev *pdev;       /* PCI设备指针，用于访问配置空间 */
55      void __iomem *bar_mmap;     /* BAR2 MMIO映射后的虚拟地址 */
56      size_t bar_size;            /* BAR2 空间大小 */
57      struct mutex lock;          /* 互斥锁 */
58
59      /* RX描述符环，一致性DMA内存 */
60      void *rx_ring_head;        /* 描述符环的内核虚拟地址 */
61      dma_addr_t rx_ring_dma;    /* 描述符环的DMA物理地址 */
62      size_t rx_ring_size;       /* 描述符环总大小 */
63      u32 rx_ring_len;           /* 描述符环中的描述符数量 */
64
65      /* RX数据缓冲区，每个描述符对应一个skb */
66      struct sk_buff *rx_buf[RTK_MAX_RX_DESC_NUM]; /* 保存每个描述符对应的skb指针 */
67
68      /* DMA状态 */
69      bool dma_initialized; /* DMA环是否已成功初始化 */
70      u32 rx_wp;            /* 写指针，表示下一个可用描述符 */
71      u32 rx_rp;            /* 读指针，表示硬件已处理到的位置 */
72  };
```

关键说明：

- 第1-2行：定义驱动名称与版本，用于模块标识、日志打印。
    
- 第7-43行：参考rtw88驱动pci.h中的寄存器定义，分类定义相关寄存器。
    
- 第46-50行：定义RX描述符结构体，包含缓冲区容量、接收帧大小、DMA物理地址，也是参考至pci.h中定义。
    
- 第53-72行：定义设备私有结构体，包含PCI设备指针、BAR2映射地址与空间大小、并发互斥锁、DMA环资源、DMA状态等。
    

#### 8.7.2.2. 单个RX描述符重置函数[¶](#rx "永久链接至标题")

参考pci.c的rtw_pci_reset_rx_desc函数，实现单个DMA描述符初始化、skb缓冲区DMA映射、硬件描述符填充，是DMA环初始化的基础函数。

单个RX描述符重置函数(位于linux_driver/42_pcie_subsystem/pcie_dma.c)[¶](#id115 "永久链接至代码")

```c
 1  /*
 2  * 重置单个RX描述符
 3  * 参考pci.c：rtw_pci_reset_rx_desc()
 4  */
 5  static int dma_exp_reset_rx_desc(struct dma_exp_dev *edev,
 6                                  struct sk_buff *skb,
 7                                  u32 idx)
 8  {
 9      /* 获取PCI设备指针 */
10      struct pci_dev *pdev = edev->pdev;
11      /* 描述符指针 */
12      struct rtw_pci_rx_buffer_desc *buf_desc;
13      /* 缓冲区大小 */
14      int buf_sz = RTK_PCI_RX_BUF_SIZE;
15      /* DMA物理地址 */
16      dma_addr_t dma;
17
18      /* 检查skb是否有效 */
19      if (!skb)
20          return -EINVAL;
21
22      /*
23      * 将skb数据区映射为DMA地址
24      * 参考pci.c：rtw_pci_reset_rx_desc()
25      *   dma = dma_map_single(&pdev->dev, skb->data, buf_sz, DMA_FROM_DEVICE);
26      *
27      * DMA_FROM_DEVICE：表示数据流方向是设备写入内存（RX方向）
28      */
29      dma = dma_map_single(&pdev->dev, skb->data, buf_sz,
30                          DMA_FROM_DEVICE);
31      if (dma_mapping_error(&pdev->dev, dma))  /* 检查映射是否成功 */
32          return -EBUSY;
33
34      /*
35      * 将DMA地址暂存在skb->cb控制块中
36      * 参考pci.c：rtw_pci_reset_rx_desc()
37      *   *((dma_addr_t *)skb->cb) = dma;
38      *
39      * 后续释放时需要用此地址调用dma_unmap_single
40      */
41      *((dma_addr_t *)skb->cb) = dma;
42
43      /*
44      * 定位到描述符环中第idx个描述符并填写
45      * 参考pci.c：rtw_pci_reset_rx_desc()
46      *  buf_desc = (struct rtw_pci_rx_buffer_desc *)(rx_ring->r.head +
47      *                          idx * desc_sz);
48      *  memset(buf_desc, 0, sizeof(*buf_desc));
49      *  buf_desc->buf_size = cpu_to_le16(RTK_PCI_RX_BUF_SIZE);
50      *  buf_desc->dma = cpu_to_le32(dma);
51      */
52      buf_desc = (struct rtw_pci_rx_buffer_desc *)
53              (edev->rx_ring_head +                          /* 环起始虚拟地址 */
54                  idx * sizeof(struct rtw_pci_rx_buffer_desc)); /* 偏移到第idx个 */
55      memset(buf_desc, 0, sizeof(*buf_desc));                   /* 清零描述符 */
56      buf_desc->buf_size = cpu_to_le16(buf_sz);                 /* 写入缓冲区容量，小端 */
57      buf_desc->dma = cpu_to_le32(dma);                         /* 写入DMA物理地址，小端 */
58
59      return 0;
60  }
```

关键说明：

- 第29-30行：调用dma_map_single完成内核skb缓冲区到物理DMA地址的映射，指定DMA_FROM_DEVICE模式，适应网卡接收数据、设备写内存的RX传输场景。
    
- 第41行：将DMA地址暂存在skb->cb控制块中，为后续资源清理提供依据。
    
- 第52-57行：按索引偏移定位环形描述符，清零后填充缓冲区大小与DMA地址，通过大小端转换适配硬件字节序，保证硬件可正常读取描述符参数。
    

#### 8.7.2.3. RX DMA描述符环整体初始化[¶](#rx-dma "永久链接至标题")

参考pci.c的rtw_pci_init_rx_ring函数，完成一致性DMA环内存分配、批量skb缓冲区创建、所有描述符初始化、指针归零，搭建完整的RX DMA环形队列。

RX DMA描述符环整体初始化(位于linux_driver/42_pcie_subsystem/pcie_dma.c)[¶](#id116 "永久链接至代码")

```c
  1  /*
  2  * RX环完整初始化
  3  * 参考 pci.c：rtw_pci_init_rx_ring()
  4  */
  5  static int dma_exp_rx_ring_init(struct dma_exp_dev *edev)
  6  {
  7      /* PCI设备指针 */
  8      struct pci_dev *pdev = edev->pdev;
  9      /* 临时skb指针 */
 10      struct sk_buff *skb;
 11      /* 描述符环总大小 */
 12      int ring_sz;
 13      /* 每个缓冲区大小 */
 14      int buf_sz = RTK_PCI_RX_BUF_SIZE;
 15      /* 描述符数量 */
 16      u32 len = RTK_MAX_RX_DESC_NUM;
 17      /* 循环变量和已分配计数 */
 18      int i, allocated;
 19      /* 返回值 */
 20      int ret = 0;
 21
 22      pr_info("  [RX环] 描述符数量: %u\n", len);             /* 打印描述符数量 */
 23      pr_info("  [RX环] 描述符大小: %zu bytes\n",            /* 打印单个描述符大小 */
 24              sizeof(struct rtw_pci_rx_buffer_desc));
 25      pr_info("  [RX环] 数据缓冲区: %d bytes/个\n", buf_sz); /* 打印每个缓冲区大小 */
 26
 27      /*
 28      * 步骤1：分配描述符环（一致性DMA内存）
 29      *
 30      * 参考pci.c：rtw_pci_init_rx_ring()
 31      *   head = dma_alloc_coherent(&pdev->dev, ring_sz, &dma, GFP_KERNEL);
 32      */
 33      ring_sz = sizeof(struct rtw_pci_rx_buffer_desc) * len;       /* 计算环总大小 */
 34      edev->rx_ring_head = dma_alloc_coherent(&pdev->dev, ring_sz, /* 分配一致性DMA内存 */
 35                                              &edev->rx_ring_dma,
 36                                              GFP_KERNEL);
 37      if (!edev->rx_ring_head) {
 38          pr_err("  [RX环] 描述符环分配失败\n");
 39          return -ENOMEM;
 40      }
 41      /* 保存环总大小 */
 42      edev->rx_ring_size = ring_sz;
 43      /* 保存描述符数量 */
 44      edev->rx_ring_len = len;
 45
 46      pr_info("  [RX环] 虚拟地址: %p\n", edev->rx_ring_head);   /* 打印虚拟地址 */
 47      pr_info("  [RX环] DMA地址:  %pad\n", &edev->rx_ring_dma); /* 打印DMA物理地址 */
 48      pr_info("  [RX环] 总大小:   %d bytes\n", ring_sz);        /* 打印环总大小 */
 49
 50      /*
 51      * 步骤2：为每个描述符分配数据缓冲区并映射DMA
 52      *
 53      * 参考 pci.c：rtw_pci_init_rx_ring() 中的循环
 54      *   for (i = 0; i < len; i++) {
 55      *       skb = dev_alloc_skb(buf_sz);
 56      *       if (!skb) { allocated = i; ret = -ENOMEM; goto err_out; }
 57      *       memset(skb->data, 0, buf_sz);
 58      *       rx_ring->buf[i] = skb;
 59      *       ret = rtw_pci_reset_rx_desc(rtwdev, skb, rx_ring, i, desc_size);
 60      *       if (ret) { allocated = i; dev_kfree_skb_any(skb); goto err_out; }
 61      *   }
 62      */
 63      for (i = 0; i < (int)len; i++) {                       /* 遍历每个描述符 */
 64          skb = dev_alloc_skb(buf_sz);                       /* 分配一个网络缓冲区 */
 65          if (!skb) {                                        /* 判断是否分配失败 */
 66              allocated = i;                                 /* 记录已分配到第几个 */
 67              ret = -ENOMEM;                                 /* 设置错误码 */
 68              goto err_out;                                  /* 跳转到错误处理 */
 69          }
 70          memset(skb->data, 0, buf_sz);                      /* 清零缓冲区数据 */
 71          edev->rx_buf[i] = skb;                             /* 保存skb指针到数组 */
 72
 73          ret = dma_exp_reset_rx_desc(edev, skb, i);         /* 映射DMA并填写描述符 */
 74          if (ret) {                                         /* 判断是否映射失败 */
 75              allocated = i;                                 /* 记录已分配到第几个 */
 76              dev_kfree_skb(skb);                            /* 释放当前skb */
 77              edev->rx_buf[i] = NULL;                        /* 清空指针 */
 78              goto err_out;                                  /* 跳转到错误处理 */
 79          }
 80
 81          /* 只打印前4个描述符的详细信息，避免日志过多 */
 82          if (i < 4) {                                       /* 前4个描述符 */
 83              struct rtw_pci_rx_buffer_desc *desc =          /* 获取描述符指针 */
 84                  (struct rtw_pci_rx_buffer_desc *)
 85                  (edev->rx_ring_head +
 86                  i * sizeof(struct rtw_pci_rx_buffer_desc));
 87              pr_info("  [RX环] 前4个描述符的详细信息: \n");
 88              pr_info("  [RX环] 描述符[%d]: dma=0x%08X buf_size=%d\n",
 89                      i,                                     /* 描述符索引 */
 90                      le32_to_cpu(desc->dma),                /* DMA地址 */
 91                      le16_to_cpu(desc->buf_size));          /* 缓冲区大小 */
 92          }
 93      }
 94      pr_info("  [RX环] 共%u个描述符已初始化\n", len);       /* 打印初始化完成信息 */
 95
 96      /* 初始化写指针为0 */
 97      edev->rx_wp = 0;
 98      /* 初始化读指针为0 */
 99      edev->rx_rp = 0;
100
101      return 0;
102
103  err_out:
104      /*
105      * 回退：释放已分配的资源
106      *
107      * 参考pci.c：rtw_pci_init_rx_ring() 的err_out标签
108      *   for (i = 0; i < allocated; i++) {
109      *       skb = rx_ring->buf[i];
110      *       if (!skb) continue;
111      *       dma = *((dma_addr_t *)skb->cb);
112      *       dma_unmap_single(&pdev->dev, dma, buf_sz, DMA_FROM_DEVICE);
113      *       dev_kfree_skb_any(skb);
114      *       rx_ring->buf[i] = NULL;
115      *   }
116      *   dma_free_coherent(&pdev->dev, ring_sz, head, dma);
117      */
118      for (i = 0; i < allocated; i++) {                      /* 遍历已分配的描述符 */
119          dma_addr_t dma;                                    /* 临时DMA地址 */
120          skb = edev->rx_buf[i];                             /* 获取skb指针 */
121          if (!skb)                                          /* 跳过空的 */
122              continue;
123          dma = *((dma_addr_t *)skb->cb);                    /* 从cb中取出DMA地址 */
124          dma_unmap_single(&pdev->dev, dma, buf_sz,          /* 解除DMA映射 */
125                          DMA_FROM_DEVICE);
126          dev_kfree_skb(skb);                                /* 释放skb */
127          edev->rx_buf[i] = NULL;                            /* 清空指针 */
128      }
129      dma_free_coherent(&pdev->dev, ring_sz,                 /* 释放描述符环一致性内存 */
130                      edev->rx_ring_head, edev->rx_ring_dma);
131      edev->rx_ring_head = NULL;                             /* 清空环指针 */
132      pr_err("  [RX环] 初始化失败\n");                       /* 打印错误信息 */
133      return ret;                                            /* 返回错误码 */
134  }
```

关键说明：

- 第33-36行：使用dma_alloc_coherent分配一致性DMA内存，是DMA描述符环的标准内存分配方式。
    
- 第63-79行：循环批量分配skb数据缓冲区，逐个调用描述符重置函数完成DMA映射与参数填充，构建完整的DMA环形队列。
    
- 第82-92行：只打印前4个描述符的详细信息，避免日志过多。
    
- 第97-99行：DMA读写指针置零，初始化环形队列状态，为后续硬件调度提供初始状态。
    
- 第118-133行：按分配顺序逆向释放skb缓冲区、解除DMA映射、释放一致性内存，避免资源泄漏。
    

#### 8.7.2.4. DMA硬件寄存器配置函数[¶](#id46 "永久链接至标题")

参考pci.c的rtw_pci_reset_buf_desc、rtw_pci_dma_reset函数，完成DMA环基地址、环大小写入、指针清零、DMA引擎复位，实现硬件DMA模块初始化配置。

DMA硬件寄存器配置函数(位于linux_driver/42_pcie_subsystem/pcie_dma.c)[¶](#id117 "永久链接至代码")

```c
 1  /*
 2  * 配置硬件DMA寄存器
 3  * 参考pci.c：rtw_pci_reset_buf_desc()、rtw_pci_dma_reset()
 4  */
 5  static void dma_exp_configure_hw(struct dma_exp_dev *edev)
 6  {
 7      pr_info("  [HW配置] 写入DMA寄存器:\n");              /* 打印标题 */
 8
 9      /*
10      * 写RX环基地址，告诉硬件描述符环在哪个物理地址
11      *
12      * 参考pci.c：rtw_pci_reset_buf_desc()
13      *   dma = rtwpci->rx_rings[RTW_RX_QUEUE_MPDU].r.dma;
14      *   rtw_write32(rtwdev, RTK_PCI_RXBD_DESA_MPDUQ, dma);
15      *
16      * 硬件通过此地址找到描述符环，再逐个读取描述符获取数据缓冲区地址
17      */
18      writel((u32)edev->rx_ring_dma,                         /* 写入DMA物理地址 */
19          edev->bar_mmap + RTK_PCI_RXBD_DESA_MPDUQ);         /* 寄存器偏移0x338 */
20      pr_info("    REG[0x%04X] RX环基地址 = 0x%08X\n",       /* 打印写入结果 */
21              RTK_PCI_RXBD_DESA_MPDUQ,                       /* 寄存器地址 */
22              (u32)edev->rx_ring_dma);                       /* 写入的值 */
23
24      /*
25      * 写RX环大小，告诉硬件环中有多少个描述符
26      *
27      * 参考pci.c：rtw_pci_reset_buf_desc()
28      *   len = rtwpci->rx_rings[RTW_RX_QUEUE_MPDU].r.len;
29      *   rtw_write16(rtwdev, RTK_PCI_RXBD_NUM_MPDUQ,
30      *               len & TRX_BD_IDX_MASK);
31      *
32      * 硬件根据此值判断环的边界，防止越界访问
33      */
34      writew((u16)(edev->rx_ring_len & TRX_BD_IDX_MASK),     /* 写入描述符数量 */
35          edev->bar_mmap + RTK_PCI_RXBD_NUM_MPDUQ);          /* 寄存器偏移0x382 */
36      pr_info("    REG[0x%04X] RX环大小   = %u\n",           /* 打印写入结果 */
37              RTK_PCI_RXBD_NUM_MPDUQ,                        /* 寄存器地址 */
38              edev->rx_ring_len);                            /* 写入的值 */
39
40      /*
41      * 清零读写指针，复位所有DMA环的索引
42      *
43      * 参考 pci.c：rtw_pci_reset_buf_desc()
44      *   rtw_write32(rtwdev, RTK_PCI_TXBD_RWPTR_CLR, 0xffffffff);
45      *
46      * 写0xFFFFFFFF会将所有TX/RX环的读写指针归零
47      */
48      writel(0xffffffff,                                      /* 写入全1清零所有指针 */
49          edev->bar_mmap + RTK_PCI_TXBD_RWPTR_CLR);           /* 寄存器偏移0x39C */
50      pr_info("    REG[0x%04X] 读写指针=0xFFFFFFFF (清零)\n", /* 打印写入结果 */
51              RTK_PCI_TXBD_RWPTR_CLR);                        /* 寄存器地址 */
52
53      /*
54      * 复位DMA引擎并使能RX Tag
55      *
56      * 参考pci.c：rtw_pci_dma_reset()
57      *   static void rtw_pci_dma_reset(struct rtw_dev *rtwdev,
58      *                                 struct rtw_pci *rtwpci)
59      *   {
60      *       rtw_write32_set(rtwdev, RTK_PCI_CTRL,
61      *                       BIT_RST_TRXDMA_INTF | BIT_RX_TAG_EN);
62      *       rtwpci->rx_tag = 0;
63      *   }
64      *
65      * BIT_RST_TRXDMA_INTF：复位DMA引擎状态机
66      * BIT_RX_TAG_EN：使能RX Tag校验，用于检测DMA超时
67      */
68      {
69          u32 ctrl = readl(edev->bar_mmap + RTK_PCI_CTRL);   /* 先读取当前控制寄存器值 */
70          ctrl |= BIT_RST_TRXDMA_INTF | BIT_RX_TAG_EN;       /* 置位复位和RX Tag位 */
71          writel(ctrl, edev->bar_mmap + RTK_PCI_CTRL);       /* 写回控制寄存器 */
72          pr_info("    REG[0x%04X] DMA控制    = 0x%08X (复位+RX Tag)\n", /* 打印结果 */
73                  RTK_PCI_CTRL,                              /* 寄存器地址 */
74                  ctrl);                                     /* 写入的值 */
75      }
76
77      pr_info("  [HW配置] 完成\n");                          /* 打印完成信息 */
78
79      /*
80      * 设备未加载firmware，DMA不会真正传输数据，并且前后还有大量必需步骤才能真正实现
81      * 但描述符环和寄存器配置是完整的
82      */
83  }
```

关键说明：

- 第18-19行：向硬件寄存器写入DMA描述符环物理地址，建立硬件与软件DMA环的映射关系，硬件通过该地址读取描述符。
    
- 第34-35行：写入描述符环数量，配合位掩码限制硬件访问范围，防止DMA越界访问内存。
    
- 第48-49行：写入全1数值清零所有DMA读写指针，复位环形队列硬件状态。
    
- 第69-71行：读取并修改DMA控制寄存器，复位DMA引擎状态机、开启RX Tag超时校验，保障DMA传输稳定性。
    

重要

设备未加载firmware，DMA不会真正传输数据，并且前后还有大量必需步骤才能真正实现。如芯片电源时序控制、MAC初始化、firmware下载、TX/RX queue完整配置、WiFi MAC DMA状态机、中断和完成处理等等等。

#### 8.7.2.5. DMA资源清理函数[¶](#id47 "永久链接至标题")

参考pci.c的rtw_pci_free_rx_ring_skbs、rtw_pci_free_rx_ring函数，逆向释放所有DMA资源，解除缓冲区DMA映射、释放skb、销毁一致性内存，避免内存泄漏与资源残留。

DMA资源清理函数(位于linux_driver/42_pcie_subsystem/pcie_dma.c)[¶](#id118 "永久链接至代码")

```c
 1  /*
 2  * DMA子系统清理
 3  *
 4  * 参考pci.c：rtw_pci_free_rx_ring_skbs()、rtw_pci_free_rx_ring()
 5  */
 6  static void dma_exp_cleanup(struct dma_exp_dev *edev)
 7  {
 8      /* PCI设备指针 */
 9      struct pci_dev *pdev = edev->pdev;
10      /* 缓冲区大小 */
11      int buf_sz = RTK_PCI_RX_BUF_SIZE;
12      /* 循环变量 */
13      int i;
14
15      /* 未初始化则直接返回 */
16      if (!edev->dma_initialized)
17          return;
18
19      /*
20      * 释放每个描述符的数据缓冲区
21      *
22      * 参考pci.c：rtw_pci_free_rx_ring_skbs()
23      *   for (i = 0; i < rx_ring->r.len; i++) {
24      *       skb = rx_ring->buf[i];
25      *       if (!skb) continue;
26      *       dma = *((dma_addr_t *)skb->cb);
27      *       dma_unmap_single(&pdev->dev, dma, buf_sz, DMA_FROM_DEVICE);
28      *       dev_kfree_skb(skb);
29      *       rx_ring->buf[i] = NULL;
30      *   }
31      */
32      for (i = 0; i < (int)edev->rx_ring_len; i++) {         /* 遍历每个描述符 */
33          dma_addr_t dma;                                    /* 临时DMA地址 */
34          if (!edev->rx_buf[i])                              /* 跳过空的缓冲区 */
35              continue;
36          dma = *((dma_addr_t *)edev->rx_buf[i]->cb);        /* 从cb取出DMA地址 */
37          dma_unmap_single(&pdev->dev, dma, buf_sz,          /* 解除DMA映射 */
38                          DMA_FROM_DEVICE);
39          dev_kfree_skb(edev->rx_buf[i]);                    /* 释放skb */
40          edev->rx_buf[i] = NULL;                            /* 清空指针 */
41      }
42
43      /*
44      * 释放描述符环
45      *
46      * 参考pci.c：rtw_pci_free_rx_ring()
47      *   dma_free_coherent(&pdev->dev, ring_sz, head, rx_ring->r.dma);
48      */
49      if (edev->rx_ring_head) {                              /* 检查环是否已分配 */
50          dma_free_coherent(&pdev->dev,                      /* 释放一致性DMA内存 */
51                          edev->rx_ring_size,              /* 环大小 */
52                          edev->rx_ring_head,              /* 虚拟地址 */
53                          edev->rx_ring_dma);              /* DMA物理地址 */
54          edev->rx_ring_head = NULL;                         /* 清空指针 */
55      }
56
57      edev->dma_initialized = false;                         /* 标记为未初始化 */
58      pr_info("DMA资源已释放\n");                            /* 打印完成信息 */
59  }
```

关键说明：

- 第32-41行：逆向遍历所有缓冲区，从skb cb中取出DMA地址，先解除映射再释放skb，清空指针。
    
- 第49-55行：调用dma_free_coherent释放一致性DMA内存，回收内核DMA内存资源。
    
- 第57行：重置DMA初始化标记，同步设备状态。
    

#### 8.7.2.6. sysfs用户交互接口[¶](#id48 "永久链接至标题")

实现两个只读sysfs调试接口，分别用于查看DMA全局状态、打印RX描述符环详细内容。

**显示DMA总体信息**

汇总输出DMA初始化状态、描述符环软硬件地址、队列大小、读写指针，同时实时读取硬件寄存器值，对比软件与硬件DMA状态，直观展示DMA配置是否正常。

显示DMA总体信息(位于linux_driver/42_pcie_subsystem/pcie_dma.c)[¶](#id119 "永久链接至代码")

```c
 1  /* sysfs属性接口: 显示DMA总体信息 */
 2  static ssize_t dma_info_show(struct device *dev,
 3                              struct device_attribute *attr,
 4                              char *buf)
 5  {
 6      /* 获取设备私有数据 */
 7      struct dma_exp_dev *edev = dev_get_drvdata(dev);
 8      /* 已写入长度 */
 9      int len = 0;
10
11      /* 检查私有数据 */
12      if (!edev)
13          return -ENODEV;
14
15      len += sprintf(buf + len, "------PCI DMA信息------\n");  /* 标题 */
16      len += sprintf(buf + len, "DMA是否始化: %s\n",         /* 初始化状态 */
17                  edev->dma_initialized ? "Yes" : "No");
18
19      if (!edev->dma_initialized)                            /* 未初始化则提前返回 */
20          return len;
21
22      len += sprintf(buf + len, "\nRX 描述符环:\n");         /* 描述符环信息标题 */
23      len += sprintf(buf + len, "  虚拟地址:   %p\n",        /* 虚拟地址 */
24                  edev->rx_ring_head);
25      len += sprintf(buf + len, "  DMA地址:    %pad\n",      /* DMA物理地址 */
26                  &edev->rx_ring_dma);
27      len += sprintf(buf + len, "  环大小:     %zu bytes\n", /* 环总大小 */
28                  edev->rx_ring_size);
29      len += sprintf(buf + len, "  描述符数:   %u\n",        /* 描述符数量 */
30                  edev->rx_ring_len);
31      len += sprintf(buf + len, "  描述符大小: %zu bytes\n", /* 单个描述符大小 */
32                  sizeof(struct rtw_pci_rx_buffer_desc));
33      len += sprintf(buf + len, "  WP: %u  RP: %u\n",        /* 读写指针 */
34                  edev->rx_wp, edev->rx_rp);
35
36      /* 读取硬件RX索引寄存器 */
37      if (edev->bar_mmap) {                                  /* BAR已映射 */
38          u32 rx_idx = readl(edev->bar_mmap +                /* 读取RX索引寄存器 */
39                          RTK_PCI_RXBD_IDX_MPDUQ);
40          len += sprintf(buf + len, "\n硬件寄存器:\n");      /* 硬件寄存器标题 */
41          len += sprintf(buf + len, "  RX_IDX [0x%04X] = 0x%08X\n", /* 索引寄存器值 */
42                      RTK_PCI_RXBD_IDX_MPDUQ, rx_idx);
43          len += sprintf(buf + len, "    HW WP: %u\n",       /* 硬件写指针 */
44                      (u32)((rx_idx >> 16) & TRX_BD_IDX_MASK)); /* bit[27:16] */
45          len += sprintf(buf + len, "    Host RP: %u\n",     /* 主机读指针 */
46                      (u32)(rx_idx & TRX_BD_IDX_MASK));   /* bit[11:0] */
47          len += sprintf(buf + len, "  RX_DESA [0x%04X] = 0x%08X\n", /* 环基地址读回 */
48                      RTK_PCI_RXBD_DESA_MPDUQ,
49                      readl(edev->bar_mmap + RTK_PCI_RXBD_DESA_MPDUQ));
50          len += sprintf(buf + len, "  RX_NUM  [0x%04X] = 0x%04X\n", /* 环大小读回 */
51                      RTK_PCI_RXBD_NUM_MPDUQ,
52                      readw(edev->bar_mmap + RTK_PCI_RXBD_NUM_MPDUQ));
53      }
54
55      /* 返回写入的总字节数 */
56      return len;
57  }
```

**显示RX描述符环内容**

格式化展示前16个描述符的缓冲区大小、帧长度、DMA地址，自动完成大小端转换，展示描述符初始化结果。

显示RX描述符环内容(位于linux_driver/42_pcie_subsystem/pcie_dma.c)[¶](#id120 "永久链接至代码")

```c
 1  /* sysfs属性接口: 显示RX描述符环内容 */
 2  static ssize_t dma_ring_show(struct device *dev,
 3                              struct device_attribute *attr,
 4                              char *buf)
 5  {
 6      /* 获取设备私有数据 */
 7      struct dma_exp_dev *edev = dev_get_drvdata(dev);
 8      /* 已写入长度 */
 9      int len = 0;
10      /* 循环变量和显示数量 */
11      int i, show_count;
12
13      /* 未初始化检查 */
14      if (!edev | !edev->dma_initialized)
15          return sprintf(buf, "DMA未初始化\n");
16
17      /* 只显示前16个 */
18      show_count = min_t(int, edev->rx_ring_len, 16);
19
20      len += sprintf(buf + len,                              /* 打印标题 */
21                  "RX 描述符环 (显示前 %d / %u 个):\n",
22                  show_count, edev->rx_ring_len);
23      len += sprintf(buf + len,                              /* 打印表头 */
24                  "%-6s %-12s %-12s %-12s\n",
25                  "IDX", "buf_size", "total_pkt", "dma_addr");
26      len += sprintf(buf + len,                              /* 打印分隔线 */
27                  "----------------------------------------------\n");
28
29      /* 遍历要显示的描述符 */
30      for (i = 0; i < show_count; i++) {
31          /* 获取描述符指针 */
32          struct rtw_pci_rx_buffer_desc *desc =
33              (struct rtw_pci_rx_buffer_desc *)
34              (edev->rx_ring_head +
35              i * sizeof(struct rtw_pci_rx_buffer_desc));
36
37          len += sprintf(buf + len, "%-6d %-12u %-12u 0x%08X\n", /* 格式化输出 */
38                      i,                                  /* 描述符索引 */
39                      le16_to_cpu(desc->buf_size),        /* 缓冲区容量 */
40                      le16_to_cpu(desc->total_pkt_size),  /* 接收包大小 */
41                      le32_to_cpu(desc->dma));            /* DMA地址 */
42      }
43
44      /* 返回写入的总字节数 */
45      return len;
46  }
```

**统一属性组管理接口**

所有sysfs接口配置0444只读权限，通过属性组统一管理接口，自动完成创建与销毁。

统一属性组管理接口(位于linux_driver/42_pcie_subsystem/pcie_dma.c)[¶](#id121 "永久链接至代码")

```c
 1  /* sysfs属性定义 */
 2  static DEVICE_ATTR(dma_info, 0444, dma_info_show, NULL);   /* DMA信息，只读 */
 3  static DEVICE_ATTR(dma_ring, 0444, dma_ring_show, NULL);   /* 描述符环内容，只读 */
 4
 5  /* 属性数组 */
 6  static struct attribute *dma_exp_attrs[] = {
 7      &dev_attr_dma_info.attr,                               /* dma_info属性 */
 8      &dev_attr_dma_ring.attr,                               /* dma_ring属性 */
 9      NULL,                                                  /* 数组结束标记 */
10  };
11
12  /* 属性组定义 */
13  static const struct attribute_group dma_exp_group = {
14      .attrs = dma_exp_attrs,                                /* 指向属性数组 */
15  };
```

#### 8.7.2.7. probe函数[¶](#id49 "永久链接至标题")

probe函数是PCI驱动的核心回调入口，当内核匹配到适配的PCIe设备时自动触发，实现PCI设备匹配后的初始化、资源映射、DMA初始化等。

probe函数(位于linux_driver/42_pcie_subsystem/pcie_dma.c)[¶](#id122 "永久链接至代码")

```c
  1  /*
  2  * 设备探测函数
  3  *
  4  * 参考pci.c：rtw_pci_probe()
  5  */
  6  static int dma_exp_probe(struct pci_dev *pdev,
  7                          const struct pci_device_id *id)
  8  {
  9      /* 设备私有数据 */
 10      struct dma_exp_dev *edev;
 11      /* 返回值 */
 12      int ret;
 13
 14      /* 打印发现信息 */
 15      pr_info("%s: 发现设备 %s\n", DRV_NAME, pci_name(pdev));
 16
 17      /* 分配并清零私有数据 */
 18      edev = kzalloc(sizeof(*edev), GFP_KERNEL);
 19      if (!edev)
 20          return -ENOMEM;
 21
 22      /* 初始化互斥锁 */
 23      mutex_init(&edev->lock);
 24      /* 保存PCI设备指针 */
 25      edev->pdev = pdev;
 26      /* 绑定私有数据到PCI设备 */
 27      pci_set_drvdata(pdev, edev);
 28
 29      /* 使能PCI设备 */
 30      ret = pci_enable_device(pdev);
 31      if (ret) {
 32          pr_err("pci_enable_device 失败: %d\n", ret);
 33          goto err_free;
 34      }
 35      /* 设置总线主控 */
 36      pci_set_master(pdev);
 37
 38      /* 申请PCI区域 */
 39      ret = pci_request_regions(pdev, DRV_NAME);
 40      if (ret) {
 41          pr_err("pci_request_regions 失败: %d\n", ret);
 42          goto err_disable;
 43      }
 44
 45      /*
 46      * 映射BAR2
 47      *
 48      * 参考 pci.c：rtw_pci_io_mapping()
 49      *   len = pci_resource_len(pdev, bar_id);
 50      *   rtwpci->mmap = pci_iomap(pdev, bar_id, len);
 51      *   if (!rtwpci->mmap) { pci_release_regions(pdev); return -ENOMEM; }
 52      */
 53      /* 获取BAR2大小 */
 54      edev->bar_size = pci_resource_len(pdev, 2);
 55      if (edev->bar_size == 0) {
 56          pr_err("BAR2大小为0\n");
 57          ret = -ENODEV;
 58          goto err_release;
 59      }
 60      /* 映射BAR2到虚拟地址 */
 61      edev->bar_mmap = pci_iomap(pdev, 2, edev->bar_size);
 62      if (!edev->bar_mmap) {
 63          pr_err("BAR2映射失败\n");
 64          ret = -ENOMEM;
 65          goto err_release;
 66      }
 67      /* 打印映射信息 */
 68      pr_info("  BAR2 映射: 物理=0x%llx 虚拟=%p 大小=%zu\n",
 69              (unsigned long long)pci_resource_start(pdev, 2), /* 物理地址 */
 70              edev->bar_mmap,                                  /* 虚拟地址 */
 71              edev->bar_size);                                 /* 大小 */
 72
 73      pr_info("----------DMA初始化----------\n");
 74
 75      /* 初始化RX DMA环 */
 76      ret = dma_exp_rx_ring_init(edev);
 77      if (ret) {
 78          pr_err("RX 环初始化失败: %d\n", ret);
 79          goto err_unmap;
 80      }
 81
 82      /* 配置硬件DMA寄存器 */
 83      dma_exp_configure_hw(edev);
 84
 85      /* 标记DMA已初始化 */
 86      edev->dma_initialized = true;
 87
 88      /* 创建sysfs属性组 */
 89      ret = devm_device_add_group(&pdev->dev, &dma_exp_group);
 90      if (ret)
 91          goto err_dma_cleanup;
 92
 93      pr_info("%s: 设备 %s 初始化完成\n",
 94              DRV_NAME, pci_name(pdev));
 95      return 0;
 96
 97  err_dma_cleanup:
 98      /* 释放DMA资源 */
 99      dma_exp_cleanup(edev);
100  err_unmap:
101      /* 解除BAR映射 */
102      pci_iounmap(pdev, edev->bar_mmap);
103  err_release:
104      /* 释放PCI区域 */
105      pci_release_regions(pdev);
106  err_disable:
107      /* 禁用PCI设备 */
108      pci_disable_device(pdev);
109  err_free:
110      /* 释放私有数据 */
111      kfree(edev);
112      /* 返回错误码 */
113      return ret;
114  }
```

关键说明：

- 第18-27行：调用kzalloc分配设备私有内存并清零，初始化互斥锁，绑定PCI设备指针与私有数据，完成驱动设备基础资源初始化。
    
- 第30-36行：调用pci_enable_device启用PCI设备硬件，校验设备启动状态，通过pci_set_master开启总线主控模式，授予硬件DMA直接访问内存权限。
    
- 第39行：调用pci_request_regions申请PCI寄存器资源区域，独占硬件寄存器操作权限，避免多驱动抢占硬件资源引发冲突。
    
- 第54-66行：读取BAR2空间大小并校验合法性，通过pci_iomap完成硬件寄存器物理地址到内核虚拟地址的映射。
    
- 第76-86行：依次执行RX DMA环初始化、硬件DMA寄存器配置，标记DMA初始化完成状态。
    
- 第89行：注册sysfs设备属性组，向用户层提供sysfs调试接口。
    

#### 8.7.2.8. remove函数[¶](#id50 "永久链接至标题")

remove卸载函数，释放probe阶段申请的所有硬件、内存、锁、设备节点资源，避免内存泄漏与资源残留。

remove函数(位于linux_driver/42_pcie_subsystem/pcie_dma.c)[¶](#id123 "永久链接至代码")

```c
 1  /*
 2  * 设备移除函数
 3  *
 4  * 参考pci.c：rtw_pci_remove()
 5  */
 6  static void dma_exp_remove(struct pci_dev *pdev)
 7  {
 8      /* 获取私有数据 */
 9      struct dma_exp_dev *edev = pci_get_drvdata(pdev);
10
11      /* 空指针检查 */
12      if (!edev)
13          return;
14
15      /* 移除sysfs属性组 */
16      device_remove_group(&pdev->dev, &dma_exp_group);
17      /* 释放DMA资源 */
18      dma_exp_cleanup(edev);
19
20      /* 判断BAR是否映射 */
21      if (edev->bar_mmap) {
22          /* 解除BAR映射 */
23          pci_iounmap(pdev, edev->bar_mmap);
24          /* 清空指针 */
25          edev->bar_mmap = NULL;
26      }
27
28      /* 释放PCI区域 */
29      pci_release_regions(pdev);
30      /* 禁用PCI设备 */
31      pci_disable_device(pdev);
32      /* 销毁互斥锁 */
33      mutex_destroy(&edev->lock);
34      /* 释放私有数据 */
35      kfree(edev);
36
37      pr_info("%s: 设备 %s 已移除\n", DRV_NAME, pci_name(pdev));
38  }
```

关键说明：

- 第4行：通过pci_get_drvdata获取设备私有数据。
    
- 第16行：移除sysfs用户交互接口，清理用户层调试节点。
    
- 第18行：调用dma_exp_cleanup函数释放所有DMA资源，解除缓冲区DMA映射、释放skb、销毁一致性内存，避免内存泄漏与资源残留。
    
- 第21-26行：调用pci_iounmap解除硬件寄存器虚拟映射，回收内核虚拟地址资源。
    
- 第29-31行：释放PCI寄存器独占资源、禁用PCI设备硬件，回收总线层硬件资源。
    
- 第33-35行：销毁设备互斥锁、释放私有数据内存，清空设备所有内核资源。
    

#### 8.7.2.9. 电源管理[¶](#id51 "永久链接至标题")

**设备休眠**

suspend函数是PCI设备电源管理休眠回调函数，系统进入休眠、挂起、待机状态时由内核自动触发。

suspend函数(位于linux_driver/42_pcie_subsystem/pcie_dma.c)[¶](#id124 "永久链接至代码")

```c
 1  /* 系统挂起回调 */
 2  static int dma_exp_suspend(struct device *dev)
 3  {
 4      /* 转换为PCI设备 */
 5      struct pci_dev *pdev = to_pci_dev(dev);
 6
 7      /* 打印挂起信息 */
 8      pr_info("%s: suspend\n", DRV_NAME);
 9      /* 保存PCI配置空间状态 */
10      pci_save_state(pdev);
11      /* 禁用PCI设备 */
12      pci_disable_device(pdev);
13      return 0;
14  }
```

关键说明：

- 第10行：调用pci_save_state自动读取并保存PCIe设备当前全部配置空间寄存器状态，将设备工作参数存入内核缓存。
    
- 第12行：调用pci_disable_device关闭PCI设备总线资源，释放设备占用的内存空间与总线通道，让设备进入低功耗休眠模式。
    

**设备唤醒**

resume函数是PCI设备电源管理唤醒回调函数，系统从休眠状态唤醒、恢复正常工作时由内核自动触发。

resume函数(位于linux_driver/42_pcie_subsystem/pcie_dma.c)[¶](#id125 "永久链接至代码")

```c
 1  /* 系统恢复回调 */
 2  static int dma_exp_resume(struct device *dev)
 3  {
 4      /* 转换为PCI设备 */
 5      struct pci_dev *pdev = to_pci_dev(dev);
 6      /* 返回值 */
 7      int ret;
 8
 9      /* 打印恢复信息 */
10      pr_info("%s: resume\n", DRV_NAME);
11      /* 恢复PCI配置空间状态 */
12      pci_restore_state(pdev);
13      /* 重新使能PCI设备 */
14      ret = pci_enable_device(pdev);
15      if (ret)
16          /* 使能失败，打印错误 */
17          pr_err("resume: pci_enable_device 失败: %d\n", ret);
18      else
19          /* 使能成功，重新设置总线主控 */
20          pci_set_master(pdev);
21      return ret;
22  }
```

关键说明：

- 第12行：调用pci_restore_state还原休眠前保存的PCI寄存器状态，恢复DMA、总线等硬件原始配置。
    
- 第14行：调用pci_enable_device启用PCI硬件设备，恢复设备基础通信能力。
    
- 第20行：设备使能成功后重新调用pci_set_master开启总线主控，重新授予硬件DMA访问内存权限。
    

**dev_pm_ops接口**

调用内核标准宏SIMPLE_DEV_PM_OPS定义电源管理操作结构体，快速绑定挂起、恢复回调函数。

dev_pm_ops接口(位于linux_driver/42_pcie_subsystem/pcie_dma.c)[¶](#id126 "永久链接至代码")

```c
/* 使用dev_pm_ops接口定义电源管理回调 */
static SIMPLE_DEV_PM_OPS(dma_exp_pm_ops,    /* PM操作结构体名 */
                        dma_exp_suspend,   /* 挂起回调 */
                        dma_exp_resume);   /* 恢复回调 */
```

#### 8.7.2.10. PCI设备ID表与驱动注册[¶](#id52 "永久链接至标题")

PCI设备ID表与驱动注册(位于linux_driver/42_pcie_subsystem/pcie_dma.c)[¶](#id127 "永久链接至代码")

```c
 1  /* PCI设备ID匹配表 */
 2  static const struct pci_device_id dma_exp_ids[] = {
 3      { PCI_DEVICE(0x10EC, 0x8179) },  /* RTL8188EE */
 4      { PCI_DEVICE(0x10EC, 0xC821) },  /* RTL8821CE */
 5      { PCI_DEVICE(0x10EC, 0xC822) },  /* RTL8822CE */
 6      { PCI_DEVICE(0x10EC, 0xC82F) },  /* RTL8822CE */
 7      { PCI_DEVICE(0x10EC, 0xb852) },  /* RTL8852BE */
 8      { PCI_DEVICE(0x10EC, 0xb85b) },  /* RTL8852BE */
 9      { }
10  };
11  /* 导出设备ID表到用户空间 */
12  MODULE_DEVICE_TABLE(pci, dma_exp_ids);
13
14  /* PCI驱动结构体 */
15  static struct pci_driver dma_exp_driver = {
16      .name      = DRV_NAME,             /* 驱动名称 */
17      .id_table  = dma_exp_ids,          /* 设备匹配表 */
18      .probe     = dma_exp_probe,        /* 设备匹配成功后的初始化入口 */
19      .remove    = dma_exp_remove,       /* 设备移除时的清理入口 */
20      .driver.pm = &dma_exp_pm_ops,      /* 电源管理操作 */
21  };
22
23  /* 自动注册/注销PCI驱动 */
24  module_pci_driver(dma_exp_driver);
```

关键说明：

- 第2-8行：通过pci_device_id结构体数组定义多款Realtek无线网卡设备ID，统一厂商VID为0x10EC，分别匹配对应的Realtek无线网卡。
    
- 第12行：通过MODULE_DEVICE_TABLE宏将自定义的PCI设备匹配表导出至内核用户空间，作用是告知系统udev设备管理器与热插拔子系统当前驱动支持的硬件列表。
    
- 第15-21行：初始化标准pci_driver核心结构体，完成各功能回调绑定。
    
- 第24行：采用module_pci_driver宏，替代传统module_init、module_exit函数的方式，内核自动生成驱动注册与注销入口代码。
    

### 8.7.3. Makefile说明[¶](#id53 "永久链接至标题")

本节实验使用的Makefile如下所示，编写该Makefile时，只需要根据实际情况修改变量KERNEL_DIR、CROSS_COMPILE和obj-m即可。

Makefile(位于linux_driver/42_pcie_subsystem/Makefile)[¶](#id128 "永久链接至代码")

```makefile
 1  #指定内核路径,可以是相对路径或绝对路径
 2  KERNEL_DIR=../../kernel/
 3  # KERNEL_DIR=/home/guest/LubanCat_Linux_Generic_Full_SDK/kernel-6.1
 4  # KERNEL_DIR=/home/guest/LubanCat_Linux_rk3588_SDK/kernel
 5
 6  #指定目标架构为arm64
 7  ARCH=arm64
 8
 9  #指定交叉编译工具链的前缀
10  CROSS_COMPILE=aarch64-linux-gnu-
11  # CROSS_COMPILE=/home/guest/LubanCat_Linux_Generic_Full_SDK/prebuilts/gcc/linux-x86/aarch64/gcc-arm-10.3-2021.07-x86_64-aarch64-none-linux-gnu/bin/aarch64-none-linux-gnu-
12
13  #导出为环境变量
14  export  ARCH  CROSS_COMPILE
15
16  #指定要编译的内核模块目标文件
17  obj-m += pcie_dma.o
18
19  #all :默认目标，执行时会编译驱动模块
20  #$(MAKE) ：调用make工具
21  #-C $(KERNEL_DIR) ：指定的内核源码目录
22  #M=$(CURDIR) ：模块的源码位于当前目录
23  #modules ：编译模块
24  all:
25      $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) modules
26
27  .PHONE:clean
28
29  #清理编译生成的文件
30  clean:
31      $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) clean
```

### 8.7.4. 编译驱动[¶](#id54 "永久链接至标题")

在实验目录下输入 `make` 即可编译驱动，编译得到内核模块pcie_dma.ko。

### 8.7.5. 程序运行结果[¶](#id55 "永久链接至标题")

如出现 `Permission denied` 或类似字样，请注意用户权限，大部分操作硬件外设的功能，几乎都需要root用户权限，简单的解决方案是在执行语句前加入sudo或以root用户运行程序。

#### 8.7.5.1. 实验操作[¶](#id56 "永久链接至标题")

以LubanCat2板卡搭配RTL8821CE网卡为例进行说明，先装配好PCIe网卡再给板卡上电，避免带电操作损坏板卡。

需要先确认网卡的VID和PID能够匹配本实验的驱动：

```bash
#查看网卡的VID和PID
lspci -nn

#信息输出如下
00:00.0 PCI bridge [0604]: Rockchip Electronics Co., Ltd RK3568 Remote Signal Processor [1d87:3566] (rev 01)
01:00.0 Network controller [0280]: Realtek Semiconductor Co., Ltd. RTL8821CE 802.11ac PCIe Wireless Network Adapter [10ec:c821]
```

可以从输出信息看到实际使用的RTL8821CE网卡的VID和PID是[10ec:c821]，能够匹配本实验驱动。如果不能匹配就需要自行在pci_device_id列表添加网卡实际的VID和PID。

因为系统会默认加载内核自带的网卡驱动，所以需要先卸载内核自带的网卡驱动，再加载本实验驱动：

```bash
 1  #查看当前系统加载的驱动模块
 2  lsmod
 3
 4  #4.19.232内核系统信息输出如下
 5  Module                  Size  Used by
 6  rfcomm                 61440  12
 7  bnep                   24576  2
 8  rtk_btusb              57344  0
 9  btusb                  40960  0
10  btrtl                  16384  1 btusb
11  btbcm                  16384  1 btusb
12  btintel                20480  1 btusb
13  8821ce               1859584  0
14  bluetooth             450560  39 btrtl,btintel,btbcm,bnep,btusb,rfcomm
15
16  #6.1.99内核系统信息输出如下
17  Module                  Size  Used by
18  btusb                  53248  0
19  btrtl                  28672  1 btusb
20  btbcm                  24576  1 btusb
21  rtw88_8821ce           16384  0
22  rtw88_8821c            90112  1 rtw88_8821ce
23  btintel                40960  1 btusb
24  bluetooth             716800  27 btrtl,btintel,btbcm,btusb
25  ecdh_generic           16384  2 bluetooth
26  ecc                    32768  1 ecdh_generic
27  rtw88_pci              28672  1 rtw88_8821ce
28  rtw88_core            208896  2 rtw88_pci,rtw88_8821c
29  ip_tables              32768  0
30  rtc_rk808              20480  0
31  rtc_hym8563            16384  1
```

注解

由于4.19.232内核使用的是kernel/drivers/net/wireless/rockchip_wlan/rtl8821ce驱动，6.1.99内核使用的是kernel/drivers/net/wireless/realtek/rtw88驱动，因此两个版本的内核加载的驱动名称模块不一样，但都能明显确认哪个模块是网卡驱动。

卸载对应的网卡驱动再加载本实验驱动：

```bash
 1  #4.19.232内核系统卸载8821ce模块
 2  sudo rmmod 8821ce
 3
 4  #6.1.99内核系统卸载rtw88_8821ce模块
 5  sudo rmmod rtw88_8821ce
 6
 7  #加载实验驱动
 8  sudo insmod pcie_dma.ko
 9
10  #信息输出如下
11  [   34.761875] pcie_dma: 发现设备 0000:01:00.0
12  [   34.763218]   BAR2 映射: 物理=0xf4200000 虚拟=00000000c9cc0a15 大小=65536
13  [   34.763252] ----------DMA初始化----------
14  [   34.763261]   [RX环] 描述符数量: 512
15  [   34.763268]   [RX环] 描述符大小: 8 bytes
16  [   34.763275]   [RX环] 数据缓冲区: 11478 bytes/个
17  [   34.765599]   [RX环] 虚拟地址: 00000000941f7280
18  [   34.765638]   [RX环] DMA地址:  0x000000007ee04000
19  [   34.765651]   [RX环] 总大小:   4096 bytes
20  [   34.765689]   [RX环] 前4个描述符的详细信息:
21  [   34.765702]   [RX环] 描述符[0]: dma=0x573C0040 buf_size=11478
22  [   34.765718]   [RX环] 前4个描述符的详细信息:
23  [   34.765726]   [RX环] 描述符[1]: dma=0x54CAC040 buf_size=11478
24  [   34.765741]   [RX环] 前4个描述符的详细信息:
25  [   34.765749]   [RX环] 描述符[2]: dma=0x57278040 buf_size=11478
26  [   34.765767]   [RX环] 前4个描述符的详细信息:
27  [   34.765779]   [RX环] 描述符[3]: dma=0x57340040 buf_size=11478
28  [   34.770369]   [RX环] 共512个描述符已初始化
29  [   34.770410]   [HW配置] 写入DMA寄存器:
30  [   34.770424]     REG[0x0338] RX环基地址 = 0x7EE04000
31  [   34.770435]     REG[0x0382] RX环大小   = 512
32  [   34.770445]     REG[0x039C] 读写指针=0xFFFFFFFF (清零)
33  [   34.770458]     REG[0x0300] DMA控制    = 0xF713FEFF (复位+RX Tag)
34  [   34.770468]   [HW配置] 完成
35  [   34.770532] pcie_dma: 设备 0000:01:00.0 初始化完成
```

可以从打印信息看到DMA描述符环已经准备好，RX数据缓冲区已经映射给设备，RX环基地址和大小已经写入硬件，DMA控制寄存器被配置。

进入网卡对应的sysfs目录进行测试：

```bash
 1  #进入sysyfs目录，路径根据前面打印的设备名称0000:01:00.0确定
 2  cd /sys/bus/pci/devices/0000:01:00.0/
 3
 4  #显示DMA总体信息
 5  cat dma_info
 6
 7  #信息输出如下
 8  ------PCI DMA信息------
 9  DMA是否始化: Yes
10
11  RX 描述符环:
12  虚拟地址:   00000000941f7280
13  DMA地址:    0x000000007ee04000
14  环大小:     4096 bytes
15  描述符数:   512
16  描述符大小: 8 bytes
17  WP: 0  RP: 0
18
19  硬件寄存器:
20  RX_IDX [0x03B4] = 0x00000000
21      HW WP: 0
22      Host RP: 0
23  RX_DESA [0x0338] = 0x7EE04000
24  RX_NUM  [0x0382] = 0x0200
25
26  #显示RX描述符环内容
27  cat dma_ring
28
29  #信息输出如下
30  RX 描述符环 (显示前 16 / 512 个):
31  IDX    buf_size     total_pkt    dma_addr
32  ----------------------------------------------
33  0      11478        0            0x573C0040
34  1      11478        0            0x54CAC040
35  2      11478        0            0x57278040
36  3      11478        0            0x57340040
37  4      11478        0            0x5731C040
38  5      11478        0            0x54CB8040
39  6      11478        0            0x54C98040
40  7      11478        0            0x7514C040
41  8      11478        0            0x7410C040
42  9      11478        0            0x54C28040
43  10     11478        0            0x54D14040
44  11     11478        0            0x737F8040
45  12     11478        0            0x77610040
46  13     11478        0            0x77608040
47  14     11478        0            0x733E8040
48  15     11478        0            0x731B8040
```

以上测试各sysfs接口均正常，可以看到DMA总体信息以及前16个RX描述符环内容。

注解

正如前面驱动源码解析所说的，因为要实现真正的DMA传输还要大量的步骤，因此即使硬件产生RX DMA，实验驱动也不会把数据交给网络协议栈。

### 8.7.6. 实验注意事项[¶](#id57 "永久链接至标题")

- DMA映射：需区分DMA_FROM_DEVICE与DMA_TO_DEVICE方向，RX接收场景必须使用设备写内存模式。
    
- 大小端转换：所有硬件描述符参数必须完成CPU与设备字节序转换，直接写入原生字节会导致硬件解析描述符失败。
    

## 8.8. PCI IRQ驱动实验[¶](#pci-irq "永久链接至标题")

本实验驱动基于Linux PCI子系统与中断子系统框架设计，适配Realtek RTL8188EE/RTL8821CE/RTL8822CE/RTL8852BE系列PCIe无线网卡设备。 实现完整的PCIe中断申请、注册、触发、解析、清理与电源管理功能。通过内核中断子系统完成硬件中断响应，并提供sysfs用户层调试接口，支持手动使能/禁用、手动触发中断、实时查看中断状态。

本章的示例代码目录为： **linux_driver/42_pcie_subsystem**

注解

本实验驱动大量参考至瑞芯微6.1.99版本内核的drivers/net/wireless/realtek/rtw88/pci.c驱动，并且由于Realtek未公开相关寄存器手册，相关寄存器定义从rtw88/pci.h中获取。

### 8.8.1. 驱动代码详解[¶](#id58 "永久链接至标题")

#### 8.8.1.1. 核心定义与数据结构[¶](#id59 "永久链接至标题")

参考内核源码drivers/net/wireless/realtek/rtw88/pci.h中相关寄存器定义，包括中断掩码寄存器、IMR 0/1/2位定义和irq_mask的定义；定义设备私有数据结构体。

核心定义与数据结构(位于linux_driver/42_pcie_subsystem/pcie_irq.c)[¶](#id129 "永久链接至代码")

```c
 1  #define DRV_NAME    "pcie_irq"  /* 驱动名称 */
 2  #define DRV_VERSION "1.0"       /* 驱动版本号 */
 3
 4  /* 以下寄存器地址全部来自rtw88驱动的pci.h */
 5
 6  /* 中断掩码寄存器 */
 7  #define RTK_PCI_HIMR0       0x0B0   /* 中断掩码寄存器0 */
 8  #define RTK_PCI_HISR0       0x0B4   /* 中断状态寄存器0 */
 9  #define RTK_PCI_HIMR1       0x0B8   /* 中断掩码寄存器1 */
10  #define RTK_PCI_HISR1       0x0BC   /* 中断状态寄存器1 */
11  #define RTK_PCI_HIMR3       0x10B8  /* 中断掩码寄存器3 */
12  #define RTK_PCI_HISR3       0x10BC  /* 中断状态寄存器3 */
13
14  /* IMR 0 位定义（HIMR0/HISR0） */
15  #define IMR_ROK             BIT(0)    /* 接收DMA完成 */
16  #define IMR_RDU             BIT(1)    /* 接收描述符不可用 */
17  #define IMR_VODOK           BIT(2)    /* VO队列发送DMA完成 */
18  #define IMR_VIDOK           BIT(3)    /* VI队列发送DMA完成 */
19  #define IMR_BEDOK           BIT(4)    /* BE队列发送DMA完成 */
20  #define IMR_BKDOK           BIT(5)    /* BK队列发送DMA完成 */
21  #define IMR_MGNTDOK         BIT(6)    /* 管理队列发送DMA完成 */
22  #define IMR_HIGHDOK         BIT(7)    /* 高优先级队列DMA完成 */
23  #define IMR_CPWM            BIT(8)    /* 电源模式切换 */
24  #define IMR_CPWM2           BIT(9)    /* 电源模式切换2 */
25  #define IMR_C2HCMD          BIT(10)   /* 固件C2H命令中断 */
26  #define IMR_BCNDMAINT_E     BIT(14)   /* Beacon DMA中断 */
27
28  /* IMR 1 位定义（HIMR1/HISR1） */
29  #define IMR_TXFOVW          BIT(9)    /* TX FIFO溢出 */
30
31  /* IMR 3 位定义（HIMR3/HISR3） */
32  #define IMR_H2CDOK          BIT(16)   /* H2C队列DMA完成 */
33
34  /* 参考pci.c：rtw_pci_init()中irq_mask的定义
35  *   rtwpci->irq_mask[0] = IMR_HIGHDOK | IMR_MGNTDOK |
36  *                         IMR_BKDOK | IMR_BEDOK |
37  *                         IMR_VIDOK | IMR_VODOK |
38  *                         IMR_ROK | IMR_BCNDMAINT_E |
39  *                         IMR_C2HCMD;
40  *   rtwpci->irq_mask[1] = IMR_TXFOVW;
41  *   rtwpci->irq_mask[3] = IMR_H2CDOK;
42  */
43
44  #define EXP_IRQ_MASK0  (IMR_HIGHDOK | IMR_MGNTDOK | \
45                          IMR_BKDOK | IMR_BEDOK | \
46                          IMR_VIDOK | IMR_VODOK | \
47                          IMR_ROK | IMR_BCNDMAINT_E | \
48                          IMR_C2HCMD)
49  #define EXP_IRQ_MASK1  (IMR_TXFOVW)
50  #define EXP_IRQ_MASK3  (IMR_H2CDOK)
51
52  /* 设备私有数据结构体  */
53
54  struct irq_exp_dev {
55      struct pci_dev *pdev;   /* PCI设备指针，用于访问配置空间 */
56      void __iomem *bar_mmap; /* BAR2 MMIO映射后的虚拟地址 */
57      size_t bar_size;        /* BAR2 空间大小 */
58
59      /* 中断相关字段 */
60      int irq_vector;         /* 分配到的中断向量号 */
61      bool irq_registered;    /* 中断处理函数是否已注册 */
62      bool irq_enabled;       /* 中断是否已使能 */
63      atomic_t irq_count;     /* 中断触发总计数 */
64      u32 last_hisr0;         /* 最后一次中断时的HISR0值 */
65      u32 last_hisr1;         /* 最后一次中断时的HISR1值 */
66      u32 last_hisr3;         /* 最后一次中断时的HISR3值 */
67      spinlock_t irq_lock;    /* 中断操作自旋锁 */
68      struct mutex lock;      /* 互斥锁 */
69  };
```

关键说明：

- 第1-2行：定义驱动名称与版本，用于模块标识、日志打印。
    
- 第7-12行：定义三组中断掩码/状态寄存器偏移地址，HIMR为中断使能掩码，HISR为中断状态寄存器。
    
- 第15-26行：定义HIMR0中断位，包括接收DMA完成、电源切换、固件命令等中断。
    
- 第29行：定义HIMR1 TX FIFO溢出中断，用于监控发送队列异常状态。
    
- 第32行：定义HIMR3 H2C主机固件通信DMA完成中断。
    
- 第44-50行：参考原厂默认中断掩码，用于批量使能网卡的全部中断。
    
- 第55-57行：存储PCI设备指针、BAR2映射虚拟地址与空间大小，保存硬件操作基础资源。
    
- 第61-62行：状态标记变量，区分中断注册、使能状态，防止重复初始化与非法清理。
    
- 第63行：原子变量统计中断触发次数，保证中断上下文计数安全。
    
- 第64-66行：缓存上一次中断的状态寄存器值，供sysfs查询。
    
- 第67-68行：中断自旋锁，保护中断上下文寄存器读写操作；设备互斥锁，保护设备初始化、卸载、sysfs等进程上下文操作。
    

#### 8.8.1.2. 硬中断处理函数[¶](#id60 "永久链接至标题")

参考pci.c的rtw_pci_interrupt_handler函数，中断触发后立即关闭所有硬件中断掩码，避免后续中断嵌套，然后唤醒下半部线程完成耗时的解析工作。

硬中断处理函数(位于linux_driver/42_pcie_subsystem/pcie_irq.c)[¶](#id130 "永久链接至代码")

```c
 1  /*
 2  * 硬中断处理函数（上半部）
 3  *
 4  * 参考pci.c：rtw_pci_interrupt_handler()
 5  */
 6  static irqreturn_t irq_exp_hard_handler(int irq, void *dev_id)
 7  {
 8      /* 获取设备私有数据 */
 9      struct irq_exp_dev *edev = dev_id;
10
11      /*
12      * 立即关闭所有中断掩码
13      *
14      * 参考pci.c：rtw_pci_disable_interrupt()
15      *   rtw_write32(rtwdev, RTK_PCI_HIMR0, 0);
16      *   rtw_write32(rtwdev, RTK_PCI_HIMR1, 0);
17      *   rtw_write32(rtwdev, RTK_PCI_HIMR3, 0);
18      */
19      writel(0, edev->bar_mmap + RTK_PCI_HIMR0);      /* 关闭中断掩码0 */
20      writel(0, edev->bar_mmap + RTK_PCI_HIMR1);      /* 关闭中断掩码1 */
21      writel(0, edev->bar_mmap + RTK_PCI_HIMR3);      /* 关闭中断掩码3 */
22
23      /* 唤醒中断线程执行实际处理 */
24      return IRQ_WAKE_THREAD;
25  }
```

关键说明：

- 第19-21行：清零三组中断掩码寄存器，硬件层面临时关闭所有中断，避免中断嵌套。
    
- 第24行：返回IRQ_WAKE_THREAD内核标记，自动唤醒下半部线程处理复杂业务。
    

#### 8.8.1.3. 中断线程处理函数[¶](#id61 "永久链接至标题")

参考pci.c的rtw_pci_interrupt_threadfn函数，完成读取中断状态寄存器、W1C机制清除中断标志、统计中断次数、解析具体中断源、重新恢复中断掩码等处理。

中断线程处理函数(位于linux_driver/42_pcie_subsystem/pcie_irq.c)[¶](#id131 "永久链接至代码")

```c
  1  /*
  2  * 中断线程处理函数（下半部）
  3  *
  4  * 参考 pci.c：rtw_pci_interrupt_threadfn()
  5  */
  6  static irqreturn_t irq_exp_thread_handler(int irq, void *dev_id)
  7  {
  8      /* 获取设备私有数据 */
  9      struct irq_exp_dev *edev = dev_id;
 10      /* 保存中断标志 */
 11      unsigned long flags;
 12      /* 中断状态寄存器值 */
 13      u32 hisr0, hisr1, hisr3;
 14
 15      /* 获取自旋锁并保存中断状态 */
 16      spin_lock_irqsave(&edev->irq_lock, flags);
 17
 18      /*
 19      * 步骤1：读取中断状态
 20      *
 21      * 参考 pci.c：rtw_pci_irq_recognized()
 22      *   irq_status[0] = rtw_read32(rtwdev, RTK_PCI_HISR0);
 23      *   irq_status[1] = rtw_read32(rtwdev, RTK_PCI_HISR1);
 24      *   irq_status[3] = rtw_read32(rtwdev, RTK_PCI_HISR3);
 25      */
 26      hisr0 = readl(edev->bar_mmap + RTK_PCI_HISR0);      /* 读取中断状态0 */
 27      hisr1 = readl(edev->bar_mmap + RTK_PCI_HISR1);      /* 读取中断状态1 */
 28      hisr3 = readl(edev->bar_mmap + RTK_PCI_HISR3);      /* 读取中断状态3 */
 29
 30      edev->last_hisr0 = hisr0;                           /* 保存HISR0供sysfs查询 */
 31      edev->last_hisr1 = hisr1;                           /* 保存HISR1供sysfs查询 */
 32      edev->last_hisr3 = hisr3;                           /* 保存HISR3供sysfs查询 */
 33
 34      /*
 35      * 步骤2：W1C清除中断状态
 36      *
 37      * 参考 pci.c：rtw_pci_irq_recognized()
 38      *   rtw_write32(rtwdev, RTK_PCI_HISR0, irq_status[0]);
 39      *   rtw_write32(rtwdev, RTK_PCI_HISR1, irq_status[1]);
 40      *   rtw_write32(rtwdev, RTK_PCI_HISR3, irq_status[3]);
 41      *
 42      * W1C即向某位写1清除该位，写0无影响
 43      */
 44      writel(hisr0, edev->bar_mmap + RTK_PCI_HISR0);       /* W1C清除中断状态0 */
 45      writel(hisr1, edev->bar_mmap + RTK_PCI_HISR1);       /* W1C清除中断状态1 */
 46      writel(hisr3, edev->bar_mmap + RTK_PCI_HISR3);       /* W1C清除中断状态3 */
 47
 48      /* 递增中断计数 */
 49      atomic_inc(&edev->irq_count);
 50
 51      /*
 52      * 步骤3：解析中断源
 53      *
 54      * 参考 pci.c：rtw_pci_interrupt_threadfn()
 55      *   if (irq_status[0] & IMR_MGNTDOK)
 56      *       rtw_pci_tx_isr(rtwdev, rtwpci, RTW_TX_QUEUE_MGMT);
 57      *   ...
 58      *   if (irq_status[0] & IMR_ROK) {
 59      *       rtw_pci_rx_isr(rtwdev);
 60      *       rx = true;
 61      *   }
 62      */
 63      if (atomic_read(&edev->irq_count) <= 20) {
 64          pr_info("%s: IRQ #%d  HISR0=0x%08X HISR1=0x%08X HISR3=0x%08X\n",
 65                  DRV_NAME, atomic_read(&edev->irq_count),
 66                  hisr0, hisr1, hisr3);
 67
 68          /* HISR0 位解析 */
 69          if (hisr0 & IMR_ROK)
 70              pr_info("  -> HISR0 BIT(0)  IMR_ROK           接收DMA完成\n");
 71          if (hisr0 & IMR_RDU)
 72              pr_info("  -> HISR0 BIT(1)  IMR_RDU           接收描述符不可用\n");
 73          if (hisr0 & IMR_VODOK)
 74              pr_info("  -> HISR0 BIT(2)  IMR_VODOK         VO队列发送完成\n");
 75          if (hisr0 & IMR_VIDOK)
 76              pr_info("  -> HISR0 BIT(3)  IMR_VIDOK         VI队列发送完成\n");
 77          if (hisr0 & IMR_BEDOK)
 78              pr_info("  -> HISR0 BIT(4)  IMR_BEDOK         BE队列发送完成\n");
 79          if (hisr0 & IMR_BKDOK)
 80              pr_info("  -> HISR0 BIT(5)  IMR_BKDOK         BK队列发送完成\n");
 81          if (hisr0 & IMR_MGNTDOK)
 82              pr_info("  -> HISR0 BIT(6)  IMR_MGNTDOK       管理队列发送完成\n");
 83          if (hisr0 & IMR_HIGHDOK)
 84              pr_info("  -> HISR0 BIT(7)  IMR_HIGHDOK       高优先级发送完成\n");
 85          if (hisr0 & IMR_CPWM)
 86              pr_info("  -> HISR0 BIT(8)  IMR_CPWM          电源模式切换\n");
 87          if (hisr0 & IMR_CPWM2)
 88              pr_info("  -> HISR0 BIT(9)  IMR_CPWM2         电源模式切换2\n");
 89          if (hisr0 & IMR_C2HCMD)
 90              pr_info("  -> HISR0 BIT(10) IMR_C2HCMD        固件C2H命令\n");
 91          if (hisr0 & BIT(11))
 92              pr_info("  -> HISR0 BIT(11) IMR_HISR1_IND_INT HISR1中断指示\n");
 93          if (hisr0 & BIT(12))
 94              pr_info("  -> HISR0 BIT(12) IMR_ATIMEND       ATIM结束\n");
 95          if (hisr0 & IMR_BCNDMAINT_E)
 96              pr_info("  -> HISR0 BIT(14) IMR_BCNDMAINT_E   Beacon DMA中断\n");
 97          if (hisr0 & BIT(15))
 98              pr_info("  -> HISR0 BIT(15) IMR_HSISR_IND_ON  HSISR中断指示\n");
 99          if (hisr0 & BIT(16))
100              pr_info("  -> HISR0 BIT(16) IMR_BCNDOK0       Beacon DMA完成0\n");
101          if (hisr0 & BIT(20))
102              pr_info("  -> HISR0 BIT(20) IMR_BCNDMAINT0    Beacon DMA中断0\n");
103          if (hisr0 & BIT(24))
104              pr_info("  -> HISR0 BIT(24) IMR_TSF_BIT32     TSF bit32翻转\n");
105          if (hisr0 & BIT(25))
106              pr_info("  -> HISR0 BIT(25) IMR_TBDOK         TBDOK\n");
107          if (hisr0 & BIT(26))
108              pr_info("  -> HISR0 BIT(26) IMR_TBDER         TBDER\n");
109          if (hisr0 & BIT(27))
110              pr_info("  -> HISR0 BIT(27) IMR_GTINT3        GTINT3\n");
111          if (hisr0 & BIT(28))
112              pr_info("  -> HISR0 BIT(28) IMR_GTINT4        GTINT4\n");
113          if (hisr0 & BIT(29))
114              pr_info("  -> HISR0 BIT(29) IMR_PSTIMEOUT     省电超时\n");
115          if (hisr0 & BIT(30))
116              pr_info("  -> HISR0 BIT(30) IMR_TIMER1        定时器1\n");
117          if (hisr0 & BIT(31))
118              pr_info("  -> HISR0 BIT(31) IMR_TIMER2        定时器2\n");
119
120          /* HISR1 位解析 */
121          if (hisr1 & BIT(0))
122              pr_info("  -> HISR1 BIT(0)  保留位\n");
123          if (hisr1 & BIT(1))
124              pr_info("  -> HISR1 BIT(1)  IMR_CPUMGQ_TX_TIMER CPU管理队列TX定时器\n");
125          if (hisr1 & BIT(2))
126              pr_info("  -> HISR1 BIT(2)  IMR_PS_TIMER_A 省电定时器A\n");
127          if (hisr1 & BIT(3))
128              pr_info("  -> HISR1 BIT(3)  IMR_PS_TIMER_B 省电定时器B\n");
129          if (hisr1 & BIT(4))
130              pr_info("  -> HISR1 BIT(4)  IMR_PS_TIMER_C 省电定时器C\n");
131          if (hisr1 & BIT(5))
132              pr_info("  -> HISR1 BIT(5)  IMR_CPU_MGQ_TXDONE CPU管理队列TX完成\n");
133          if (hisr1 & BIT(8))
134              pr_info("  -> HISR1 BIT(8)  IMR_RXFOVW RX FIFO溢出\n");
135          if (hisr1 & IMR_TXFOVW)
136              pr_info("  -> HISR1 BIT(9)  IMR_TXFOVW TX FIFO溢出\n");
137          if (hisr1 & BIT(10))
138              pr_info("  -> HISR1 BIT(10) IMR_RXERR RX错误\n");
139          if (hisr1 & BIT(11))
140              pr_info("  -> HISR1 BIT(11) IMR_TXERR TX错误\n");
141          if (hisr1 & BIT(12))
142              pr_info("  -> HISR1 BIT(12) IMR_ATIMEND ATIM结束\n");
143          if (hisr1 & BIT(29))
144              pr_info("  -> HISR1 BIT(29) IMR_BTON_STS_UPDATE BT状态更新\n");
145          if (hisr1 & BIT(30))
146              pr_info("  -> HISR1 BIT(30) IMR_TXFIFO_TH_INT TX FIFO阈值中断\n");
147
148          /* HISR3 位解析 */
149          if (hisr3 & IMR_H2CDOK)
150              pr_info("  -> HISR3 BIT(16) IMR_H2CDOK H2C DMA完成\n");
151      }
152
153      /*
154      * 步骤4：重新使能中断
155      *
156      * 参考pci.c：rtw_pci_interrupt_threadfn()
157      *   if (rtwpci->running)
158      *       rtw_pci_enable_interrupt(rtwdev, rtwpci, rx);
159      */
160
161      writel(EXP_IRQ_MASK0, edev->bar_mmap + RTK_PCI_HIMR0); /* 使能全部HIMR0中断 */
162      writel(EXP_IRQ_MASK1, edev->bar_mmap + RTK_PCI_HIMR1); /* 使能TX FIFO溢出 */
163      writel(EXP_IRQ_MASK3, edev->bar_mmap + RTK_PCI_HIMR3); /* 使能H2C DMA完成 */
164
165      /* 释放自旋锁并恢复中断状态 */
166      spin_unlock_irqrestore(&edev->irq_lock, flags);
167
168      /* 返回中断已处理 */
169      return IRQ_HANDLED;
170  }
```

关键说明：

- 第16行：调用spin_lock_irqsave加锁，关闭本地中断，保护寄存器读写。
    
- 第26-28行：读取三组硬件中断状态寄存器，获取本次触发的具体中断源。
    
- 第30-32行：缓存中断状态值，为用户层sysfs查询提供数据。
    
- 第44-46行：按照W1C（写1清零）机制，写入读取到的状态值，硬件自动清除中断标志。
    
- 第49行：原子递增中断计数，统计设备总中断触发次数。
    
- 第63-151行：限制仅前20次中断打印日志，避免频繁刷屏，解析具体中断源进行打印。
    
- 第161-163行：重新写入中断掩码，恢复硬件中断使能。
    
- 第166行：解锁并恢复本地中断状态，退出临界区。
    
- 第169行：返回IRQ_HANDLED，告知内核中断处理完成。
    

#### 8.8.1.4. 中断子系统初始化函数[¶](#id62 "永久链接至标题")

参考pci.c的rtw_pci_request_irq函数，优先申请MSI中断，兼容传统INTx中断，完成线程化中断注册、硬件中断掩码配置、中断状态标记等处理。

中断子系统初始化函数(位于linux_driver/42_pcie_subsystem/pcie_irq.c)[¶](#id132 "永久链接至代码")

```c
 1  /*
 2  * 中断子系统初始化
 3  *
 4  * 参考pci.c：rtw_pci_request_irq() + rtw_pci_init()
 5  */
 6  static int irq_exp_init(struct irq_exp_dev *edev)
 7  {
 8      /* 获取PCI设备指针 */
 9      struct pci_dev *pdev = edev->pdev;
10      /* 返回值 */
11      int ret;
12
13      pr_info("--------- 中断子系统初始化 ---------\n");
14
15      /*
16      * 步骤1：申请中断向量
17      *
18      * 参考pci.c：rtw_pci_request_irq()
19      *   unsigned int flags = PCI_IRQ_LEGACY;  // 旧内核
20      *   unsigned int flags = PCI_IRQ_INTX;    // 新内核 >= 6.10
21      *   if (!rtw_disable_msi)
22      *       flags |= PCI_IRQ_MSI;
23      *   ret = pci_alloc_irq_vectors(pdev, 1, 1, flags);
24      *
25      * 优先MSI，回退INTx
26      */
27  #if (LINUX_VERSION_CODE >= KERNEL_VERSION(6, 10, 0))         /* 内核版本判断 */
28      ret = pci_alloc_irq_vectors(pdev, 1, 1,                  /* 申请1个中断向量 */
29                                  PCI_IRQ_MSI | PCI_IRQ_INTX); /* MSI优先，INTx回退 */
30  #else                                                        /* 旧内核 */
31      ret = pci_alloc_irq_vectors(pdev, 1, 1,                  /* 申请1个中断向量 */
32                                  PCI_IRQ_MSI | PCI_IRQ_LEGACY); /* MSI优先，LEGACY回退 */
33  #endif
34      if (ret < 0) {                                           /* 申请失败 */
35          pr_err("中断向量申请失败: %d\n", ret);
36          return ret;
37      }
38
39      edev->irq_vector = pci_irq_vector(pdev, 0);              /* 获取第0个向量的IRQ号 */
40      pr_info("中断向量申请成功: IRQ=%d\n", edev->irq_vector); /* 打印IRQ号 */
41
42      /*
43      * 步骤2：注册线程化中断
44      *
45      * 参考pci.c：rtw_pci_request_irq()
46      *   ret = devm_request_threaded_irq(rtwdev->dev, pdev->irq,
47      *                                   rtw_pci_interrupt_handler,
48      *                                   rtw_pci_interrupt_threadfn,
49      *                                   IRQF_SHARED, KBUILD_MODNAME,
50      *                                   rtwdev);
51      *
52      * 硬中断：irq_exp_hard_handler
53      * 线程：irq_exp_thread_handler
54      */
55      ret = request_threaded_irq(edev->irq_vector,            /* IRQ号 */
56                              irq_exp_hard_handler,        /* 硬中断处理函数 */
57                              irq_exp_thread_handler,      /* 线程处理函数 */
58                              IRQF_SHARED,                 /* 允许共享中断 */
59                              DRV_NAME,                    /* 中断名称 */
60                              edev);                       /* 传递给handler的参数 */
61      if (ret) {                                              /* 注册失败 */
62          pr_err("中断注册失败: %d\n", ret);                  /* 打印错误 */
63          pci_free_irq_vectors(pdev);                         /* 释放中断向量 */
64          return ret;                                         /* 返回错误码 */
65      }
66      /* 标记中断已注册 */
67      edev->irq_registered = true;
68      pr_info("线程化中断注册成功\n");
69
70      /* 打印掩码值 */
71      pr_info("默认中断掩码: HIMR0=0x%08X HIMR1=0x%08X HIMR3=0x%08X\n",
72              (u32)EXP_IRQ_MASK0, (u32)EXP_IRQ_MASK1, (u32)EXP_IRQ_MASK3);
73
74      /*
75      * 步骤3：使能中断
76      *
77      * 参考pci.c：rtw_pci_enable_interrupt()
78      *   rtw_write32(rtwdev, RTK_PCI_HIMR0, rtwpci->irq_mask[0]);
79      *   rtw_write32(rtwdev, RTK_PCI_HIMR1, rtwpci->irq_mask[1]);
80      *   rtw_write32(rtwdev, RTK_PCI_HIMR3, rtwpci->irq_mask[3]);
81      */
82      writel(EXP_IRQ_MASK0, edev->bar_mmap + RTK_PCI_HIMR0); /* 使能全部HIMR0中断 */
83      writel(EXP_IRQ_MASK1, edev->bar_mmap + RTK_PCI_HIMR1); /* 使能TX FIFO溢出 */
84      writel(EXP_IRQ_MASK3, edev->bar_mmap + RTK_PCI_HIMR3); /* 使能H2C DMA完成 */
85      /* 标记中断已使能 */
86      edev->irq_enabled = true;
87      /* 打印提示 */
88      pr_info("中断已使能，等待设备触发...\n");
89
90      /*
91      * 设备未加载firmware，可能不会产生中断，并且前后还有大量必需步骤才能真正实现
92      */
93
94      return 0;
95  }
```

关键说明：

- 第27行：通过内核版本宏区分新旧内核，区分6.10以上INTx与旧版LEGACY中断标识。
    
- 第28、31行：申请1个中断向量，优先MSI中断，失败自动回退传统中断模式。
    
- 第39行：获取最终分配的中断向量号，作为后续中断注册的标识。
    
- 第55-60行：调用内核标准线程化中断注册接口，绑定上下半部处理函数，开启共享中断模式。
    
- 第67行：标记中断注册状态，防止重复初始化。
    
- 第82-84行：写入中断掩码，硬件层面开启对应中断源。
    
- 第86行：标记中断使能状态，完成中断子系统初始化。
    

重要

设备未加载firmware，可能不会产生中断，并且前后还有大量必需步骤才能真正实现。如芯片电源时序控制、MAC初始化、firmware下载、TX/RX queue完整配置、WiFi MAC DMA状态机等等等。

#### 8.8.1.5. 中断资源清理函数[¶](#id63 "永久链接至标题")

负责释放所有中断相关硬件与内核资源，包括关闭硬件中断、同步未处理完的中断、释放中断处理函数、回收中断向量、统计中断次数，保证设备卸载无资源泄漏。

中断资源清理函数(位于linux_driver/42_pcie_subsystem/pcie_irq.c)[¶](#id133 "永久链接至代码")

```c
 1  /* 中断子系统清理 */
 2  static void irq_exp_cleanup(struct irq_exp_dev *edev)
 3  {
 4      /* 获取PCI设备指针 */
 5      struct pci_dev *pdev = edev->pdev;
 6
 7      /* 未注册则直接返回 */
 8      if (!edev->irq_registered)
 9          return;
10
11      /* BAR是否映射 */
12      if (edev->bar_mmap) {
13          writel(0, edev->bar_mmap + RTK_PCI_HIMR0);          /* 关闭中断掩码0 */
14          writel(0, edev->bar_mmap + RTK_PCI_HIMR1);          /* 关闭中断掩码1 */
15          writel(0, edev->bar_mmap + RTK_PCI_HIMR3);          /* 关闭中断掩码3 */
16      }
17      /* 标记中断已禁用 */
18      edev->irq_enabled = false;
19
20      /* 等待正在处理的中断完成 */
21      synchronize_irq(edev->irq_vector);
22
23      /* 释放中断处理函数 */
24      free_irq(edev->irq_vector, edev);
25      /* 标记中断未注册 */
26      edev->irq_registered = false;
27
28      /* 释放中断向量 */
29      pci_free_irq_vectors(pdev);
30
31      /* 打印释放信息 */
32      pr_info("%s:中断资源已释放，总中断次数: %d\n",
33              DRV_NAME, atomic_read(&edev->irq_count));
34  }
```

关键说明：

- 第8行：状态校验，未注册中断直接退出，防止非法清理。
    
- 第12-16行：清零中断掩码，硬件关闭所有中断，终止新中断触发。
    
- 第21行：调用synchronize_irq同步中断，等待当前正在执行的中断处理流程结束。
    
- 第24-26行：释放注册的中断处理函数，解除中断与设备的绑定关系，清空中断注册状态标记。
    
- 第29行：释放PCI申请的中断向量资源。
    
- 第32-33行：打印最终中断统计信息，方便实验统计。
    

#### 8.8.1.6. sysfs用户交互接口[¶](#id64 "永久链接至标题")

实现三组用户层调试接口，支持只读查询中断状态、只写使能/禁用中断、只写手动触发中断。

**显示中断状态信息**

该接口为只读状态查询接口，主要功能为实时读取并汇总设备全部中断运行信息与硬件寄存器数据，包括设备中断向量号、中断注册与使能状态、累计中断触发次数，同时展示上一次中断触发的状态寄存器缓存值、当前实时硬件寄存器数值。

显示中断状态信息(位于linux_driver/42_pcie_subsystem/pcie_irq.c)[¶](#id134 "永久链接至代码")

```c
 1  /* sysfs属性接口：显示中断状态信息 */
 2  static ssize_t irq_info_show(struct device *dev,
 3                              struct device_attribute *attr,
 4                              char *buf)
 5  {
 6      /* 获取设备私有数据 */
 7      struct irq_exp_dev *edev = dev_get_drvdata(dev);
 8      /* 已写入长度 */
 9      int len = 0;
10
11      /* 空指针检查 */
12      if (!edev)
13          return -ENODEV;
14
15      len += sprintf(buf + len, "--------- PCI中断信息 ---------\n");    /* 标题 */
16      len += sprintf(buf + len, "中断向量:   %d\n", edev->irq_vector);        /* IRQ号 */
17      len += sprintf(buf + len, "已注册:     %s\n",            /* 注册状态 */
18                  edev->irq_registered ? "Yes" : "No");
19      len += sprintf(buf + len, "已使能:     %s\n",            /* 使能状态 */
20                  edev->irq_enabled ? "Yes" : "No");
21      len += sprintf(buf + len, "中断计数:   %d\n",            /* 中断计数 */
22                  atomic_read(&edev->irq_count));
23      len += sprintf(buf + len, "\n");                        /* 空行 */
24      len += sprintf(buf + len, "最后中断状态:\n");           /* 最后中断状态标题 */
25      len += sprintf(buf + len, "  HISR0 = 0x%08X\n", edev->last_hisr0); /* HISR0 */
26      len += sprintf(buf + len, "  HISR1 = 0x%08X\n", edev->last_hisr1); /* HISR1 */
27      len += sprintf(buf + len, "  HISR3 = 0x%08X\n", edev->last_hisr3); /* HISR3 */
28
29      /* BAR已映射时读取实时值 */
30      if (edev->bar_mmap) {
31          len += sprintf(buf + len, "\n当前寄存器值:\n");     /* 实时寄存器标题 */
32          len += sprintf(buf + len, "  HISR0 [0x%04X] = 0x%08X\n", /* 实时HISR0 */
33                      RTK_PCI_HISR0,
34                      readl(edev->bar_mmap + RTK_PCI_HISR0));
35          len += sprintf(buf + len, "  HIMR0 [0x%04X] = 0x%08X\n", /* 实时HIMR0 */
36                      RTK_PCI_HIMR0,
37                      readl(edev->bar_mmap + RTK_PCI_HIMR0));
38          len += sprintf(buf + len, "  HISR1 [0x%04X] = 0x%08X\n", /* 实时HISR1 */
39                      RTK_PCI_HISR1,
40                      readl(edev->bar_mmap + RTK_PCI_HISR1));
41          len += sprintf(buf + len, "  HIMR1 [0x%04X] = 0x%08X\n", /* 实时HIMR1 */
42                      RTK_PCI_HIMR1,
43                      readl(edev->bar_mmap + RTK_PCI_HIMR1));
44      }
45
46      /* 返回写入的总字节数 */
47      return len;
48  }
```

**使能/禁用中断**

该接口为只写功能控制接口，支持用户传入0/1数值指令，实现中断的实时禁用与使能：传入1时，批量写入中断掩码，开启所有中断使能；传入0时，清零全部硬件中断掩码，关闭所有中断。

使能/禁用中断(位于linux_driver/42_pcie_subsystem/pcie_irq.c)[¶](#id135 "永久链接至代码")

```c
 1  /* 使能/禁用中断 */
 2  static ssize_t irq_enable_store(struct device *dev,
 3                                  struct device_attribute *attr,
 4                                  const char *buf,
 5                                  size_t count)
 6  {
 7      /* 获取设备私有数据 */
 8      struct irq_exp_dev *edev = dev_get_drvdata(dev);
 9      /* 使能/禁用标志 */
10      int enable;
11
12      /* 空指针检查 */
13      if (!edev | !edev->bar_mmap)
14          return -ENODEV;
15
16      /* 解析用户输入 */
17      if (kstrtoint(buf, 10, &enable))
18          return -EINVAL;
19
20      if (enable) { /* 使能中断 */
21          writel(EXP_IRQ_MASK0, edev->bar_mmap + RTK_PCI_HIMR0); /* 使能全部HIMR0中断 */
22          writel(EXP_IRQ_MASK1, edev->bar_mmap + RTK_PCI_HIMR1); /* 使能TX FIFO溢出 */
23          writel(EXP_IRQ_MASK3, edev->bar_mmap + RTK_PCI_HIMR3); /* 使能H2C DMA完成 */
24          edev->irq_enabled = true;
25          pr_info("%s: 全部中断已使能 (HIMR0=0x%08X)\n",
26                  DRV_NAME, (u32)EXP_IRQ_MASK0);
27      } else {     /* 禁用中断 */
28          /*
29          * 参考pci.c：rtw_pci_disable_interrupt()
30          *   rtw_write32(rtwdev, RTK_PCI_HIMR0, 0);
31          */
32          writel(0, edev->bar_mmap + RTK_PCI_HIMR0);          /* 关闭掩码0 */
33          writel(0, edev->bar_mmap + RTK_PCI_HIMR1);          /* 关闭掩码1 */
34          writel(0, edev->bar_mmap + RTK_PCI_HIMR3);          /* 关闭掩码3 */
35          edev->irq_enabled = false;                          /* 标记已禁用 */
36          pr_info("%s: 中断已禁用\n", DRV_NAME);              /* 打印禁用信息 */
37      }
38
39      /* 返回写入的总字节数 */
40      return count;
41  }
```

**手动触发中断**

该接口为只写手动触发调试接口，为无firmware下的中断功能验证。功能为读取硬件当前已置位的中断状态标志，将有效中断标志同步写入中断掩码寄存器，主动触发硬件中断流程。

手动触发中断(位于linux_driver/42_pcie_subsystem/pcie_irq.c)[¶](#id136 "永久链接至代码")

```c
 1  /*
 2  * 手动触发中断
 3  *
 4  * 原理：将HIMR设置为HISR中已置位的位
 5  * 使HISR & HIMR从0变为非0，硬件触发MSI中断。
 6  *
 7  * 触发后的完整流程：
 8  *   1. 硬件检测到HISR & HIMR != 0 -> 触发MSI
 9  *   2. 硬中断irq_exp_hard_handler：写HIMR=0 关闭中断
10  *   3. 线程irq_exp_thread_handler：读HISR -> W1C清除 -> 打印中断信息 -> 重新使能
11  *
12  * 额外说明：
13  *   上电或卸载内核自带网卡驱动时残留的HISR位，如IMR_CPWM、IMR_BCNDMAINT0
14  *   在无firmware时不会再次置位，所以只触发一次。
15  */
16  static ssize_t irq_trigger_store(struct device *dev,
17                                  struct device_attribute *attr,
18                                  const char *buf,
19                                  size_t count)
20  {
21      /* 获取设备私有数据 */
22      struct irq_exp_dev *edev = dev_get_drvdata(dev);
23      /* 中断状态寄存器值 */
24      u32 hisr0, hisr1, hisr3;
25      /* 触发标志 */
26      int trigger;
27
28      /* 空指针检查 */
29      if (!edev | !edev->bar_mmap)
30          return -ENODEV;     /* 返回无设备错误 */
31
32      /* 解析用户输入 */
33      if (kstrtoint(buf, 10, &trigger))
34          return -EINVAL;    /* 解析失败返回错误 */
35
36      /* 只接受写入1 */
37      if (trigger != 1)
38          return count;      /* 忽略其他值 */
39
40      /*
41      * 步骤1：读取当前HISR状态，找到已置位的位
42      */
43      hisr0 = readl(edev->bar_mmap + RTK_PCI_HISR0);  /* 读取HISR0 */
44      hisr1 = readl(edev->bar_mmap + RTK_PCI_HISR1);  /* 读取HISR1 */
45      hisr3 = readl(edev->bar_mmap + RTK_PCI_HISR3);  /* 读取HISR3 */
46
47      /* 没有已置位的中断 */
48      if (!hisr0 && !hisr1 && !hisr3) {
49          pr_info("%s: HISR中没有已置位的中断位，无法触发\n", DRV_NAME);
50          pr_info("  当前HISR0=0x00000000 HISR1=0x00000000 HISR3=0x00000000\n");
51          return count;
52      }
53
54      pr_info("%s: --------- 手动触发中断 ---------\n", DRV_NAME);
55      pr_info("  当前 HISR0=0x%08X HISR1=0x%08X HISR3=0x%08X\n", /* 打印当前状态 */
56              hisr0, hisr1, hisr3);
57
58      /*
59      * 步骤2：将HIMR设置为HISR中已置位的位
60      *
61      * 此时HISR & HIMR != 0，硬件触发MSI中断
62      *
63      * 参考pci.c的中断使能：
64      *   rtw_write32(rtwdev, RTK_PCI_HIMR0, rtwpci->irq_mask[0]);
65      *   rtw_write32(rtwdev, RTK_PCI_HIMR1, rtwpci->irq_mask[1]);
66      *   rtw_write32(rtwdev, RTK_PCI_HIMR3, rtwpci->irq_mask[3]);
67      *
68      * 这里我们用HISR值代替irq_mask，确保HISR & HIMR != 0
69      */
70      writel(hisr0, edev->bar_mmap + RTK_PCI_HIMR0);          /* 写入HIMR0 */
71      writel(hisr1, edev->bar_mmap + RTK_PCI_HIMR1);          /* 写入HIMR1 */
72      writel(hisr3, edev->bar_mmap + RTK_PCI_HIMR3);          /* 写入HIMR3 */
73
74      pr_info("已写入 HIMR0=0x%08X HIMR1=0x%08X HIMR3=0x%08X\n", /* 打印写入值 */
75              hisr0, hisr1, hisr3);
76      pr_info("等待硬件触发MSI中断...\n");                    /* 打印等待提示 */
77
78      /* 返回写入的总字节数 */
79      return count;
80  }
```

关键说明：

- 第33-38行：解析用户空间传入的数值，限定仅接收写入数值1，忽略所有其他输入。
    
- 第43-45行：读取三组硬件中断状态寄存器HISR，抓取硬件上电、驱动卸载残留的未清除中断标志位。
    
- 第48-52行：若所有HISR寄存器无任何置位中断位，直接终止触发流程并打印提示，避免无效寄存器操作.
    
- 第55-56行：打印当前硬件完整中断状态，展示待触发的中断源。
    
- 第70-72行：手动触发中断实现，将HISR已置位的中断标志值直接写入对应的HIMR中断掩码寄存器，使硬件满足HISR & HIMR != 0的中断触发条件，主动触发MSI硬件中断。
    
- 第74-76行：打印最终写入的中断掩码配置，反馈手动触发配置结果。
    

注解

以上操作将HISR状态寄存器的值写入HIMR掩码寄存器，HISR & HIMR结果必不为0，只有当HISR & HIMR != 0时，硬件才认为有一个“已发生且未被屏蔽”的中断，从而触发MSI中断。中断进入中断线程时HIMR掩码寄存器会恢复正确的值，因此不会影响正常的中断响应。

**统一属性组管理接口**

通过属性组统一管理接口，自动完成创建与销毁。

统一属性组管理接口(位于linux_driver/42_pcie_subsystem/pcie_irq.c)[¶](#id137 "永久链接至代码")

```c
 1  /* sysfs属性定义 */
 2  static DEVICE_ATTR(irq_info,    0444, irq_info_show,    NULL); /* 中断信息，只读 */
 3  static DEVICE_ATTR(irq_enable,  0200, NULL,             irq_enable_store);  /* 使能/禁用，只写 */
 4  static DEVICE_ATTR(irq_trigger, 0200, NULL,             irq_trigger_store); /* 手动触发，只写 */
 5
 6  /* 属性数组 */
 7  static struct attribute *irq_exp_attrs[] = {
 8      &dev_attr_irq_info.attr,               /* irq_info属性 */
 9      &dev_attr_irq_enable.attr,             /* irq_enable属性 */
10      &dev_attr_irq_trigger.attr,            /* irq_trigger 属性 */
11      NULL,                                  /* 数组结束标记 */
12  };
13
14  /* 属性组定义 */
15  static const struct attribute_group irq_exp_group = {
16      .attrs = irq_exp_attrs,                /* 指向属性数组 */
17  };
```

#### 8.8.1.7. probe函数[¶](#id65 "永久链接至标题")

probe函数是PCI设备匹配成功后的初始化入口，实现私有内存分配、硬件使能、总线主控开启、BAR寄存器映射、中断子系统初始化、sysfs接口注册等。

probe函数(位于linux_driver/42_pcie_subsystem/pcie_irq.c)[¶](#id138 "永久链接至代码")

```c
  1  /*
  2  * 设备探测函数
  3  *
  4  * 参考 pci.c：rtw_pci_probe()
  5  */
  6  static int irq_exp_probe(struct pci_dev *pdev,
  7                          const struct pci_device_id *id)
  8  {
  9      /* 设备私有数据指针 */
 10      struct irq_exp_dev *edev;
 11      /* 返回值 */
 12      int ret;
 13
 14      /* 打印发现信息 */
 15      pr_info("%s: 发现设备 %s\n", DRV_NAME, pci_name(pdev));
 16
 17      /* 分配并清零私有数据 */
 18      edev = kzalloc(sizeof(*edev), GFP_KERNEL);
 19      if (!edev)
 20          return -ENOMEM;
 21
 22      /* 初始化互斥锁 */
 23      mutex_init(&edev->lock);
 24      /* 初始化自旋锁 */
 25      spin_lock_init(&edev->irq_lock);
 26      /* 中断计数初始化为0 */
 27      atomic_set(&edev->irq_count, 0);
 28      /* 保存PCI设备指针 */
 29      edev->pdev = pdev;
 30      /* 绑定私有数据到PCI设备 */
 31      pci_set_drvdata(pdev, edev);
 32
 33      /* 使能PCI设备 */
 34      ret = pci_enable_device(pdev);
 35      if (ret) {
 36          pr_err("pci_enable_device 失败: %d\n", ret);
 37          goto err_free;
 38      }
 39      /* 设置总线主控 */
 40      pci_set_master(pdev);
 41
 42      /* 申请PCI区域 */
 43      ret = pci_request_regions(pdev, DRV_NAME);
 44      if (ret) {
 45          pr_err("pci_request_regions 失败: %d\n", ret);
 46          goto err_disable;
 47      }
 48
 49      /*
 50      * 映射BAR2
 51      *
 52      * 参考 pci.c：rtw_pci_io_mapping()
 53      *   len = pci_resource_len(pdev, bar_id);
 54      *   rtwpci->mmap = pci_iomap(pdev, bar_id, len);
 55      *   if (!rtwpci->mmap) { pci_release_regions(pdev); return -ENOMEM; }
 56      */
 57      /* 获取BAR2大小 */
 58      edev->bar_size = pci_resource_len(pdev, 2);
 59      if (edev->bar_size == 0) {
 60          pr_err("BAR2大小为 0\n");
 61          ret = -ENODEV;
 62          goto err_release;
 63      }
 64      /* 映射BAR2到虚拟地址 */
 65      edev->bar_mmap = pci_iomap(pdev, 2, edev->bar_size);
 66      if (!edev->bar_mmap) {
 67          pr_err("BAR2映射失败\n");
 68          ret = -ENOMEM;
 69          goto err_release;
 70      }
 71      /* 打印映射信息 */
 72      pr_info("  BAR2 映射: 物理=0x%llx 虚拟=%p 大小=%zu\n",
 73              (unsigned long long)pci_resource_start(pdev, 2), /* 物理地址 */
 74              edev->bar_mmap,                                  /* 虚拟地址 */
 75              edev->bar_size);                                 /* 大小 */
 76
 77      /* 初始化中断子系统 */
 78      ret = irq_exp_init(edev);
 79      if (ret) {
 80          pr_err("中断初始化失败: %d\n", ret);
 81          goto err_unmap;
 82      }
 83
 84      /* 创建sysfs属性组 */
 85      ret = devm_device_add_group(&pdev->dev, &irq_exp_group);
 86      if (ret)
 87          goto err_irq_cleanup;
 88
 89      pr_info("%s: 设备 %s 初始化完成\n",
 90              DRV_NAME, pci_name(pdev));
 91      return 0;
 92
 93  err_irq_cleanup:
 94      /* 释放中断资源 */
 95      irq_exp_cleanup(edev);
 96  err_unmap:
 97      /* 解除BAR映射 */
 98      pci_iounmap(pdev, edev->bar_mmap);
 99  err_release:
100      /* 释放PCI区域 */
101      pci_release_regions(pdev);
102  err_disable:
103      /* 禁用PCI设备 */
104      pci_disable_device(pdev);
105  err_free:
106      /* 释放私有数据 */
107      kfree(edev);
108      /* 返回错误码 */
109      return ret;
110  }
```

关键说明：

- 第18-31行：调用kzalloc分配设备私有内存并清零，初始化互斥锁、自旋锁与原子变量，绑定PCI设备指针与私有数据，完成驱动设备基础资源初始化。
    
- 第34-40行：调用pci_enable_device启用PCI设备硬件，校验设备启动状态，通过pci_set_master开启总线主控模式，授予硬件DMA直接访问内存权限。
    
- 第43行：调用pci_request_regions申请PCI寄存器资源区域，独占硬件寄存器操作权限，避免多驱动抢占硬件资源引发冲突。
    
- 第58-70行：读取BAR2空间大小并校验合法性，通过pci_iomap完成硬件寄存器物理地址到内核虚拟地址的映射。
    
- 第78行：调用中断初始化函数，完成驱动中断功能配置。
    
- 第85行：注册sysfs设备属性组，向用户层提供sysfs调试接口。
    

#### 8.8.1.8. remove函数[¶](#id66 "永久链接至标题")

设备卸载回调函数，依次清理用户接口、中断资源、硬件映射、PCI总线资源、设备私有内存，避免内存泄漏与资源残留。

remove函数(位于linux_driver/42_pcie_subsystem/pcie_irq.c)[¶](#id139 "永久链接至代码")

```c
 1  /*
 2  * 设备移除函数
 3  *
 4  * 参考pci.c：rtw_pci_remove()
 5  */
 6  static void irq_exp_remove(struct pci_dev *pdev)
 7  {
 8      /* 获取私有数据 */
 9      struct irq_exp_dev *edev = pci_get_drvdata(pdev);
10
11      /* 空指针检查 */
12      if (!edev)
13          return;
14
15      /* 移除sysfs属性组 */
16      device_remove_group(&pdev->dev, &irq_exp_group);
17      /* 释放中断资源 */
18      irq_exp_cleanup(edev);
19
20      /* 判断BAR是否映射 */
21      if (edev->bar_mmap) {
22          /* 解除BAR映射 */
23          pci_iounmap(pdev, edev->bar_mmap);
24          /* 清空指针 */
25          edev->bar_mmap = NULL;
26      }
27
28      /* 释放PCI区域 */
29      pci_release_regions(pdev);
30      /* 禁用PCI设备 */
31      pci_disable_device(pdev);
32      /* 销毁互斥锁 */
33      mutex_destroy(&edev->lock);
34      /* 释放私有数据 */
35      kfree(edev);
36
37      pr_info("%s:设备 %s 已移除\n", DRV_NAME, pci_name(pdev));
38  }
```

关键说明：

- 第9行：通过pci_get_drvdata获取设备私有数据。
    
- 第16行：移除sysfs用户交互接口，清理用户层调试节点。
    
- 第18行：调用统一中断清理函数，释放所有中断相关内核与硬件资源。
    
- 第21-26行：调用pci_iounmap解除硬件寄存器虚拟映射，回收内核虚拟地址资源。
    
- 第29-31行：释放PCI寄存器独占资源、禁用PCI设备硬件，回收总线层硬件资源。
    
- 第33行：销毁互斥锁资源，完成内核同步资源回收。
    
- 第35行：释放设备私有内存，清空设备所有运行数据。
    

#### 8.8.1.9. 电源管理[¶](#id67 "永久链接至标题")

**设备休眠**

suspend函数是PCI设备电源管理休眠回调函数，系统进入休眠、挂起、待机状态时由内核自动触发。

suspend函数(位于linux_driver/42_pcie_subsystem/pcie_irq.c)[¶](#id140 "永久链接至代码")

```c
 1  /* 系统挂起回调 */
 2  static int irq_exp_suspend(struct device *dev)
 3  {
 4      /* 转换为PCI设备 */
 5      struct pci_dev *pdev = to_pci_dev(dev);
 6      /* 获取私有数据 */
 7      struct irq_exp_dev *edev = pci_get_drvdata(pdev);
 8
 9      /* 打印挂起信息 */
10      pr_info("%s: suspend\n", DRV_NAME);
11
12      /* 空指针检查 */
13      if (!edev)
14          return 0;
15
16      /* BAR已映射且中断已使能 */
17      if (edev->bar_mmap && edev->irq_enabled) {
18          writel(0, edev->bar_mmap + RTK_PCI_HIMR0);          /* 关闭中断掩码0 */
19          writel(0, edev->bar_mmap + RTK_PCI_HIMR1);          /* 关闭中断掩码1 */
20          writel(0, edev->bar_mmap + RTK_PCI_HIMR3);          /* 关闭中断掩码3 */
21      }
22
23      /* 保存PCI配置空间状态 */
24      pci_save_state(pdev);
25      /* 禁用PCI设备 */
26      pci_disable_device(pdev);
27
28      return 0;
29  }
```

关键说明：

- 第17-21行：若BAR已映射且中断已使能，主动清零所有中断掩码，关闭硬件中断，防止系统休眠期间触发无效中断导致系统异常。
    
- 第24行：调用pci_save_state自动读取并保存PCIe设备当前全部配置空间寄存器状态，将设备工作参数存入内核缓存。
    
- 第26行：调用pci_disable_device关闭PCI设备总线资源，释放设备占用的内存空间与总线通道，让设备进入低功耗休眠模式。
    

**resume函数**

resume函数是PCI设备电源管理唤醒回调函数，系统从休眠状态唤醒、恢复正常工作时由内核自动触发。

resume函数(位于linux_driver/42_pcie_subsystem/pcie_irq.c)[¶](#id141 "永久链接至代码")

```c
 1  /* 系统恢复回调 */
 2  static int irq_exp_resume(struct device *dev)
 3  {
 4      /* 转换为PCI设备 */
 5      struct pci_dev *pdev = to_pci_dev(dev);
 6      /* 获取私有数据 */
 7      struct irq_exp_dev *edev = pci_get_drvdata(pdev);
 8      /* 返回值 */
 9      int ret;
10
11      /* 打印恢复信息 */
12      pr_info("%s: resume\n", DRV_NAME);
13
14      /* 空指针检查 */
15      if (!edev)
16          return 0;
17
18      /* 恢复PCI配置空间状态 */
19      pci_restore_state(pdev);
20
21      /* 重新使能PCI设备 */
22      ret = pci_enable_device(pdev);
23      if (ret) {
24          pr_err("resume: pci_enable_device 失败: %d\n", ret);
25          return ret;
26      }
27      /* 重新设置总线主控 */
28      pci_set_master(pdev);
29
30      /* BAR已映射且中断已注册 */
31      if (edev->bar_mmap && edev->irq_registered) {
32          writel(EXP_IRQ_MASK0, edev->bar_mmap + RTK_PCI_HIMR0); /* 使能全部HIMR0中断 */
33          writel(EXP_IRQ_MASK1, edev->bar_mmap + RTK_PCI_HIMR1); /* 使能TX FIFO溢出 */
34          writel(EXP_IRQ_MASK3, edev->bar_mmap + RTK_PCI_HIMR3); /* 使能H2C DMA完成 */
35          edev->irq_enabled = true;                              /* 标记中断已使能 */
36      }
37
38      return 0;
39  }
```

关键说明：

- 第19行：调用pci_restore_state还原休眠前保存的PCI寄存器状态，恢复DMA、总线等硬件原始配置。
    
- 第22行：调用pci_enable_device启用PCI硬件设备，恢复设备基础通信能力。
    
- 第28行：调用pci_set_master开启总线主控，恢复设备总线读写、中断发起能力。
    
- 第31-36行：重新写入全局中断掩码，恢复所有中断使能，让设备唤醒后可正常响应硬件中断。
    

**dev_pm_ops接口**

调用内核标准宏SIMPLE_DEV_PM_OPS定义电源管理操作结构体，快速绑定挂起、恢复回调函数。

dev_pm_ops接口(位于linux_driver/42_pcie_subsystem/pcie_irq.c)[¶](#id142 "永久链接至代码")

```c
/* 使用dev_pm_ops接口定义电源管理回调 */
static SIMPLE_DEV_PM_OPS(irq_exp_pm_ops,    /* PM操作结构体名 */
                        irq_exp_suspend,   /* 挂起回调 */
                        irq_exp_resume);   /* 恢复回调 */
```

#### 8.8.1.10. PCI设备ID表与驱动注册[¶](#id68 "永久链接至标题")

PCI设备ID表与驱动注册(位于linux_driver/42_pcie_subsystem/pcie_irq.c)[¶](#id143 "永久链接至代码")

```c
 1  /* PCI 设备 ID 匹配表 */
 2  static const struct pci_device_id irq_exp_ids[] = {
 3      { PCI_DEVICE(0x10EC, 0x8179) },  /* RTL8188EE */
 4      { PCI_DEVICE(0x10EC, 0xC821) },  /* RTL8821CE */
 5      { PCI_DEVICE(0x10EC, 0xC822) },  /* RTL8822CE */
 6      { PCI_DEVICE(0x10EC, 0xC82F) },  /* RTL8822CE */
 7      { PCI_DEVICE(0x10EC, 0xb852) },  /* RTL8852BE */
 8      { PCI_DEVICE(0x10EC, 0xb85b) },  /* RTL8852BE */
 9      { }
10  };
11  /* 导出设备ID表到用户空间 */
12  MODULE_DEVICE_TABLE(pci, irq_exp_ids);
13
14  /* PCI驱动结构体 */
15  static struct pci_driver irq_exp_driver = {
16      .name      = DRV_NAME,             /* 驱动名称 */
17      .id_table  = irq_exp_ids,          /* 设备匹配表 */
18      .probe     = irq_exp_probe,        /* 设备匹配成功后的初始化入口 */
19      .remove    = irq_exp_remove,       /* 设备移除时的清理入口 */
20      .driver.pm = &irq_exp_pm_ops,      /* 电源管理操作 */
21  };
22
23  /* 自动注册/注销PCI驱动 */
24  module_pci_driver(irq_exp_driver);
```

关键说明：

- 第2-8行：通过pci_device_id结构体数组定义多款Realtek无线网卡设备ID，统一厂商VID为0x10EC，分别匹配对应的Realtek无线网卡。
    
- 第12行：通过MODULE_DEVICE_TABLE宏将自定义的PCI设备匹配表导出至内核用户空间，作用是告知系统udev设备管理器与热插拔子系统当前驱动支持的硬件列表。
    
- 第15-21行：初始化标准pci_driver核心结构体，完成各功能回调绑定。
    
- 第24行：采用module_pci_driver宏，替代传统module_init、module_exit函数的方式，内核自动生成驱动注册与注销入口代码。
    

### 8.8.2. Makefile说明[¶](#id69 "永久链接至标题")

本节实验使用的Makefile如下所示，编写该Makefile时，只需要根据实际情况修改变量KERNEL_DIR、CROSS_COMPILE和obj-m即可。

Makefile(位于linux_driver/42_pcie_subsystem/Makefile)[¶](#id144 "永久链接至代码")

```makefile
 1  #指定内核路径,可以是相对路径或绝对路径
 2  KERNEL_DIR=../../kernel/
 3  # KERNEL_DIR=/home/guest/LubanCat_Linux_Generic_Full_SDK/kernel-6.1
 4  # KERNEL_DIR=/home/guest/LubanCat_Linux_rk3588_SDK/kernel
 5
 6  #指定目标架构为arm64
 7  ARCH=arm64
 8
 9  #指定交叉编译工具链的前缀
10  CROSS_COMPILE=aarch64-linux-gnu-
11  # CROSS_COMPILE=/home/guest/LubanCat_Linux_Generic_Full_SDK/prebuilts/gcc/linux-x86/aarch64/gcc-arm-10.3-2021.07-x86_64-aarch64-none-linux-gnu/bin/aarch64-none-linux-gnu-
12
13  #导出为环境变量
14  export  ARCH  CROSS_COMPILE
15
16  #指定要编译的内核模块目标文件
17  obj-m += pcie_irq.o
18
19  #all :默认目标，执行时会编译驱动模块
20  #$(MAKE) ：调用make工具
21  #-C $(KERNEL_DIR) ：指定的内核源码目录
22  #M=$(CURDIR) ：模块的源码位于当前目录
23  #modules ：编译模块
24  all:
25      $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) modules
26
27  .PHONE:clean
28
29  #清理编译生成的文件
30  clean:
31      $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) clean
```

### 8.8.3. 编译驱动[¶](#id70 "永久链接至标题")

在实验目录下输入 `make` 即可编译驱动，编译得到内核模块pcie_irq.ko。

### 8.8.4. 程序运行结果[¶](#id71 "永久链接至标题")

如出现 `Permission denied` 或类似字样，请注意用户权限，大部分操作硬件外设的功能，几乎都需要root用户权限，简单的解决方案是在执行语句前加入sudo或以root用户运行程序。

#### 8.8.4.1. 实验操作[¶](#id72 "永久链接至标题")

以LubanCat2板卡搭配RTL8821CE网卡为例进行说明，先装配好PCIe网卡再给板卡上电，避免带电操作损坏板卡。

需要先确认网卡的VID和PID能够匹配本实验的驱动：

```bash
#查看网卡的VID和PID
lspci -nn

#信息输出如下
00:00.0 PCI bridge [0604]: Rockchip Electronics Co., Ltd RK3568 Remote Signal Processor [1d87:3566] (rev 01)
01:00.0 Network controller [0280]: Realtek Semiconductor Co., Ltd. RTL8821CE 802.11ac PCIe Wireless Network Adapter [10ec:c821]
```

可以从输出信息看到实际使用的RTL8821CE网卡的VID和PID是[10ec:c821]，能够匹配本实验驱动。如果不能匹配就需要自行在pci_device_id列表添加网卡实际的VID和PID。

因为系统会默认加载内核自带的网卡驱动，所以需要先卸载内核自带的网卡驱动，再加载本实验驱动：

```bash
 1  #查看当前系统加载的驱动模块
 2  lsmod
 3
 4  #4.19.232内核系统信息输出如下
 5  Module                  Size  Used by
 6  rfcomm                 61440  12
 7  bnep                   24576  2
 8  rtk_btusb              57344  0
 9  btusb                  40960  0
10  btrtl                  16384  1 btusb
11  btbcm                  16384  1 btusb
12  btintel                20480  1 btusb
13  8821ce               1859584  0
14  bluetooth             450560  39 btrtl,btintel,btbcm,bnep,btusb,rfcomm
15
16  #6.1.99内核系统信息输出如下
17  Module                  Size  Used by
18  btusb                  53248  0
19  btrtl                  28672  1 btusb
20  btbcm                  24576  1 btusb
21  rtw88_8821ce           16384  0
22  rtw88_8821c            90112  1 rtw88_8821ce
23  btintel                40960  1 btusb
24  bluetooth             716800  27 btrtl,btintel,btbcm,btusb
25  ecdh_generic           16384  2 bluetooth
26  ecc                    32768  1 ecdh_generic
27  rtw88_pci              28672  1 rtw88_8821ce
28  rtw88_core            208896  2 rtw88_pci,rtw88_8821c
29  ip_tables              32768  0
30  rtc_rk808              20480  0
31  rtc_hym8563            16384  1
```

注解

由于4.19.232内核使用的是kernel/drivers/net/wireless/rockchip_wlan/rtl8821ce驱动，6.1.99内核使用的是kernel/drivers/net/wireless/realtek/rtw88驱动，因此两个版本的内核加载的驱动名称模块不一样，但都能明显确认哪个模块是网卡驱动。

卸载对应的网卡驱动再加载本实验驱动：

```bash
 1  #4.19.232内核系统卸载8821ce模块
 2  sudo rmmod 8821ce
 3
 4  #6.1.99内核系统卸载rtw88_8821ce模块
 5  sudo rmmod rtw88_8821ce
 6
 7  #加载实验驱动
 8  sudo insmod pcie_irq.ko
 9
10  #信息输出如下
11  [   31.420973] pcie_irq: 发现设备 0000:01:00.0
12  [   31.422397]   BAR2 映射: 物理=0xf4200000 虚拟=00000000ca1f508a 大小=65536
13  [   31.422428] --------- 中断子系统初始化 ---------
14  [   31.422783] 中断向量申请成功: IRQ=117
15  [   31.423216] 线程化中断注册成功
16  [   31.423231] 默认中断掩码: HIMR0=0x000044FD HIMR1=0x00000200 HIMR3=0x00010000
17  [   31.423242] 中断已使能，等待设备触发...
18  [   31.423273] pcie_irq: 设备 0000:01:00.0 初始化完成
```

可以从信息打印中看到，BAR2已成功映射，中断向量申请成功，IRQ号是117，线程化中断注册成功，中断已使能，等待设备触发中断。

进入网卡对应的sysfs目录进行测试：

```bash
 1  #进入sysyfs目录，路径根据前面打印的设备名称0000:01:00.0确定
 2  cd /sys/bus/pci/devices/0000:01:00.0/
 3
 4  #显示中断状态信息
 5  cat irq_info
 6
 7  #信息输出如下
 8  --------- PCI中断信息 ---------
 9  中断向量:   117
10  已注册:     Yes
11  已使能:     Yes
12  中断计数:   0
13
14  最后中断状态:
15  HISR0 = 0x00000000
16  HISR1 = 0x00000000
17  HISR3 = 0x00000000
18
19  当前寄存器值:
20  HISR0 [0x00B4] = 0xC0000000
21  HIMR0 [0x00B0] = 0x000044FD
22  HISR1 [0x00BC] = 0x20000001
23  HIMR1 [0x00B8] = 0x00000200
```

可以看到中断计数为0，说明从驱动加载到现在，还没有进入过中断线程处理函数；最后中断状态全是0，因为还没有发生过中断，所以都是0。 HISR0、HISR1寄存器值不为0是之前驱动/固件残留下来的硬件中断状态，因此可以用来触发一次中断。

通过irq_trigger接口来触发中断：

```bash
 1  #手动触发中断
 2  sudo sh -c "echo 1 > irq_trigger"
 3
 4  #信息输出如下
 5  [   86.311273] pcie_irq: --------- 手动触发中断 ---------
 6  [   86.311386]   当前 HISR0=0xC0000000 HISR1=0x20000001 HISR3=0x00000001
 7  [   86.311417] 已写入 HIMR0=0xC0000000 HIMR1=0x20000001 HIMR3=0x00000001
 8  [   86.311535] 等待硬件触发MSI中断...
 9  [   86.311624] pcie_irq: IRQ #1  HISR0=0xC0000000 HISR1=0x20000001 HISR3=0x00000001
10  [   86.311679]   -> HISR0 BIT(30) IMR_TIMER1        定时器1
11  [   86.311737]   -> HISR0 BIT(31) IMR_TIMER2        定时器2
12  [   86.311794]   -> HISR1 BIT(0)  保留位
13  [   86.311820]   -> HISR1 BIT(29) IMR_BTON_STS_UPDATE BT状态更新
```

可以看到触发了中断，中断线程被唤醒，打印了对应的中断源，展开HISR0=0xC0000000正是BIT(30)、BIT(31)为1，展开HISR1=0x20000001正是BIT(0)、BIT(29)为1都能被正确解析，由于驱动只解析HISR3的BIT(9)位因此没有打印HISR3的中断源。

再次查看中断状态信息：

```bash
 1  #再次查看中断状态信息
 2  cat irq_info
 3
 4  #信息输出如下
 5  --------- PCI中断信息 ---------
 6  中断向量:   117
 7  已注册:     Yes
 8  已使能:     Yes
 9  中断计数:   1
10
11  最后中断状态:
12  HISR0 = 0xC0000000
13  HISR1 = 0x20000001
14  HISR3 = 0x00000001
15
16  当前寄存器值:
17  HISR0 [0x00B4] = 0x00000000
18  HIMR0 [0x00B0] = 0x000044FD
19  HISR1 [0x00BC] = 0x00000000
20  HIMR1 [0x00B8] = 0x00000200
```

可以看到中断计数为1，触发了一次中断；最后中断状态值从之前的全0被记录为上一次中断状态实际值；当前HISR0和HISR1中断状态寄存器值全0说明没有产生新中断。

注解

正如前面驱动源码解析所说的，设备未加载firmware，可能不会产生中断，并且前后还有大量必需步骤才能真正实现新中断产生，因此利用驱动卸载残留的未清除中断标志位，只能触发一次中断，再次向irq_trigger写入1是无法再触发中断的。

如果需要重新触发中断需要重启系统，卸载内核自带的网卡驱动，然后加载实验驱动重新进行操作。

中断禁用/使能sysfs接口测试：

```bash
 1  #禁用中断
 2  sudo sh -c "echo 0 > irq_enable"
 3
 4  #信息输出如下
 5  [  739.529063] pcie_irq: 中断已禁用
 6
 7  #查看中断状态信息
 8  cat irq_info
 9
10  #信息输出如下
11  --------- PCI中断信息 ---------
12  中断向量:   117
13  已注册:     Yes
14  已使能:     No
15  中断计数:   1
16
17  最后中断状态:
18  HISR0 = 0xC0000000
19  HISR1 = 0x20000001
20  HISR3 = 0x00000001
21
22  当前寄存器值:
23  HISR0 [0x00B4] = 0x00000000
24  HIMR0 [0x00B0] = 0x00000000
25  HISR1 [0x00BC] = 0x00000000
26  HIMR1 [0x00B8] = 0x00000000
27
28  #使能中断
29  sudo sh -c "echo 1 > irq_enable"
30
31  #信息输出如下
32  [  785.265590] pcie_irq: 全部中断已使能 (HIMR0=0x000044FD)
33
34  #查看中断状态信息
35  cat irq_info
36
37  #信息输出如下
38  --------- PCI中断信息 ---------
39  中断向量:   117
40  已注册:     Yes
41  已使能:     Yes
42  中断计数:   1
43
44  最后中断状态:
45  HISR0 = 0xC0000000
46  HISR1 = 0x20000001
47  HISR3 = 0x00000001
48
49  当前寄存器值:
50  HISR0 [0x00B4] = 0x00000000
51  HIMR0 [0x00B0] = 0x000044FD
52  HISR1 [0x00BC] = 0x00000000
53  HIMR1 [0x00B8] = 0x00000200
```

可以看到向irq_enable写入0禁用中断后，HIMR0和HIMR1中断掩码寄存器的值都为0；向irq_enable写入1使能中断后，HIMR0和HIMR1中断掩码寄存器的值都恢复，说明sysfs接口功能正常。

### 8.8.5. 实验注意事项[¶](#id73 "永久链接至标题")

- 手动中断触发前提：使用irq_trigger接口手动触发中断时，硬件HISR中断状态寄存器必须存在置位标志，无残留中断位时无法触发中断。
    
- sysfs接口使用：irq_enable仅支持0/1写入、irq_trigger仅支持写入1，传入其他数值会被接口直接忽略。