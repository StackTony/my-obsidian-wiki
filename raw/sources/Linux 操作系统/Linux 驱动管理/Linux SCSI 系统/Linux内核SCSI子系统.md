原文： https://doc.embedfire.com/linux/rk356x/driver/zh/latest/linux_driver/subsystem_scsi_subsystem.html


在现代Linux存储架构中，尽管NVMe和SATA等协议在消费级市场占据主导，但SCSI（Small Computer System Interface，小型计算机系统接口）协议及其子系统架构依然是整个Linux存储栈的基石。 无论是企业级的SAS、光纤通道（Fibre Channel），还是网络存储（iSCSI），甚至是常见的USB大容量存储设备（USB Mass Storage），在Linux内核中最终都会被抽象并映射到SCSI子系统中进行处理。

## 7.1. SCSI基础知识[¶](#scsi "永久链接至标题")

### 7.1.1. SCSI的作用[¶](#id1 "永久链接至标题")

SCSI子系统提供统一的设备发现和I/O调度框架。它屏蔽了底层物理总线（SATA, USB, 网络）的差异，让上层的块设备层只需面对标准的SCSI命令，极大地简化了存储驱动的开发。

### 7.1.2. SCSI的发展与演进[¶](#id2 "永久链接至标题")

SCSI最初是一种并行硬件总线标准，用于连接硬盘、磁带机等外设。随着技术发展，物理总线逐渐被串行技术取代（如SAS、Fibre Channel），但SCSI命令集协议（SCSI Command Set）被保留并标准化下来。 如今，SCSI更多是指一套逻辑协议标准（如SPC-4主命令集、SBC-3块命令集），它定义了主机与存储设备之间如何进行通信。

- 初代并行SCSI：早期8/16位并行总线协议，传输速率低、抗干扰能力弱，仅用于传统机械硬盘、光驱设备，现已基本淘汰。
    
- SCSI-2/SCSI-3标准化：完善协议命令集、设备模型、错误处理机制，奠定了现代SCSI协议的基础架构，支持多设备挂载、并行I/O处理。
    
- 串行SCSI体系：衍生出SAS、SATA、FC等主流串行存储协议，均兼容SCSI命令集，保留SCSI协议核心逻辑，大幅提升传输速率和稳定性，成为当前服务器、PC存储的主流协议。
    
- SPC-4及最新规范：标准化缓存管理、数据校验、异步通知等高级功能，Linux内核SCSI子系统默认遵循SPC-4规范，本章节实验驱动也基于该规范实现设备交互。
    

### 7.1.3. SCSI的工作原理[¶](#id3 "永久链接至标题")

SCSI协议采用客户端-服务器（发起者-目标设备）模型，工作原理为：主机适配器（发起者）向SCSI设备（目标设备）发送标准化SCSI命令，设备解析命令并执行对应操作（读写数据、查询信息、设备校验等），完成后返回执行结果与状态信息，内核根据状态处理I/O请求或异常错误。

其核心概念包括：

- Initiator（发起者/主机）：发起I/O请求的一端，即服务器/PC的SCSI控制器（HBA）。
    
- Target（目标设备）：接收并执行命令的存储设备控制器。
    
- LUN（Logical Unit Number，逻辑单元号）：Target内部的具体逻辑存储实体（如一块具体的硬盘）。一个Target可以包含多个LUN。
    
- CDB（Command Descriptor Block，命令描述块）：Initiator发送给Target的命令包，包含操作码、LBA地址、扇区数量、传输长度等关键信息。例如6字节、10字节或16字节的READ/WRITE命令。
    
- Sense Data（感知数据）：当命令执行失败或出现异常时，Target返回给Initiator的详细错误信息（包含Sense Key, ASC, ASCQ），内核据此完成错误处理、重试、告警等操作。
    
- SG（散列聚合）：Linux内核I/O数据传输机制，支持将非连续内存缓冲区的数据聚合传输，适配大块存储I/O，SCSI子系统原生支持SG机制。
    

## 7.2. SCSI子系统整体架构[¶](#id4 "永久链接至标题")

Linux内核SCSI子系统采用分层架构设计，从上至下分为SCSI较高层、SCSI中间层、SCSI较低层，各层各司其职、相互协作，既保证了上层接口的统一性，又保留了底层硬件的适配灵活性。

### 7.2.1. SCSI较高层[¶](#id5 "永久链接至标题")

SCSI较高层对接Linux通用块设备层、文件系统层，负责设备抽象、请求封装、用户态交互，与硬件完全无关。 主要功能包括：SCSI设备枚举、设备节点创建、块设备请求转换为SCSI标准命令、设备属性管理、用户态ioctl接口适配、设备状态上报等。

较高层将文件系统的读写请求、用户态设备查询请求，统一封装为标准SCSI命令结构体，下发至中间层处理，屏蔽底层硬件差异。

### 7.2.2. SCSI中间层[¶](#id6 "永久链接至标题")

SCSI中间层是整个SCSI子系统的调度枢纽，承上启下，主要功能包括：SCSI主机适配器管理、SCSI命令队列调度、命令预处理/后处理、Sense错误数据解析、通用错误处理、SG散列聚合数据拷贝。

中间层屏蔽了底层硬件的私有交互逻辑，为上层提供统一的命令处理入口，同时为底层驱动提供标准化的回调接口、工具函数。

### 7.2.3. SCSI较低层[¶](#id7 "永久链接至标题")

SCSI较低层为硬件适配层，由厂商私有驱动或虚拟驱动组成，对接具体硬件设备。主要功能包括：实现中间层定义的回调函数、硬件命令下发、硬件数据读写、硬件错误处理、私有资源管理、异步命令调度等。

较低层驱动无需关心SCSI协议通用逻辑，仅需适配自身硬件特性，完成命令的硬件执行。

## 7.3. SCSI子系统核心结构体[¶](#id8 "永久链接至标题")

### 7.3.1. SCSI驱动管理结构体[¶](#id9 "永久链接至标题")

SCSI驱动管理结构体（struct scsi_driver）是SCSI较高层核心驱动管理结构体，基于内核标准设备驱动模型封装，用于抽象SCSI类型驱动的通用行为接口。 该结构体承接设备生命周期管理、命令初始化/销毁、命令完成回调、错误恢复处理等逻辑，是所有SCSI设备驱动注册、绑定、业务调度的载体。

scsi_driver结构体(内核源码/include/scsi/scsi_driver.h)[¶](#id49 "永久链接至代码")

```c
 1  struct scsi_driver {
 2      struct device_driver gendrv;        // 内核通用设备驱动基类，绑定驱动模型
 3
 4      /* 设备休眠恢复回调：设备从休眠唤醒时触发 */
 5      int (*resume)(struct device *);
 6
 7      /* 设备重扫描回调：总线重扫描、热插拔重枚举时触发 */
 8      void (*rescan)(struct device *);
 9
10      /* 命令初始化回调：SCSI命令创建后、下发前初始化 */
11      blk_status_t (*init_command)(struct scsi_cmnd *);
12
13      /* 命令销毁回调：SCSI命令完成后、释放前资源清理 */
14      void (*uninit_command)(struct scsi_cmnd *);
15
16      /* 命令完成回调：命令处理收尾、结果上报 */
17      int (*done)(struct scsi_cmnd *);
18
19      /* 错误处理回调：EH机制下执行命令重试、终止等操作 */
20      int (*eh_action)(struct scsi_cmnd *, int);
21
22      /* 错误重置回调：SCSI设备/主机异常重置时触发 */
23      void (*eh_reset)(struct scsi_cmnd *);
24  };
```

### 7.3.2. SCSI主机实例结构体[¶](#id10 "永久链接至标题")

SCSI主机实例结构体（struct Scsi_Host）用于描述、管理SCSI主机适配器的顶层核心结构体，是整个SCSI子系统的管理载体。该结构体统一维护主机硬件能力、挂载设备链表、I/O队列参数、错误恢复资源、私有数据空间，所有SCSI设备、命令调度、异常处理、主机重置操作均依托该结构体完成，是SCSI底层驱动与内核中间层交互的载体。

Scsi_Host结构体(内核源码/include/scsi/scsi_host.h)[¶](#id50 "永久链接至代码")

```c
 1  struct Scsi_Host {
 2      struct list_head __devices;            // 本机SCSI设备链表头，管理所有LUN设备
 3      struct list_head __targets;            // 本机Target目标设备链表头，管理所有设备节点
 4
 5      spinlock_t *host_lock;                 // 主机全局自旋锁，保护命令/I/O并发操作
 6      struct mutex scan_mutex;               // 设备扫描互斥锁，防止并发扫描冲突
 7
 8      struct list_head eh_abort_list;        // 错误处理：待中止命令链表
 9      struct list_head eh_cmd_q;             // 错误处理：异常待处理命令队列
10      struct task_struct *ehandler;          // 错误处理内核线程，专门处理SCSI异常恢复
11
12      struct scsi_host_template *hostt;       // 绑定本机SCSI主机模板，回调函数/能力参数载体
13      struct scsi_transport_template *transportt; // SCSI传输层模板，管理传输协议属性
14
15      struct blk_mq_tag_set tag_set;         // 块多队列标签集合，管理I/O队列深度与请求标签
16
17      atomic_t host_blocked;                 // 主机阻塞计数，控制主机启停调度状态
18      unsigned int host_no;                  // 系统全局SCSI主机唯一编号，用于标识与proc展示
19
20      unsigned int max_channel;              // 支持的最大通道号，限制设备通道寻址范围
21      unsigned int max_id;                   // 支持的最大Target ID，限制设备ID寻址范围
22      u64 max_lun;                           // 支持的最大LUN编号，限制逻辑单元寻址范围
23
24      unsigned short max_cmd_len;            // 主机支持的最大SCSI CDB命令长度
25      int this_id;                           // 本机在SCSI总线上的适配器ID
26      int can_queue;                         // 主机硬件最大并发排队命令数量
27      short cmd_per_lun;                     // 单个LUN设备允许的最大并发命令数
28      unsigned short sg_tablesize;           // 单次I/O支持的最大SG散列聚合分片数量
29      unsigned int max_sectors;              // 单条SCSI命令允许处理的最大扇区数
30
31      unsigned nr_hw_queues;                 // SCSI主机硬件队列数量，决定并发调度粒度
32
33      unsigned host_self_blocked:1;          // 位域标记：主机是否主动阻塞，暂停接收新请求
34      unsigned host_tagset:1;                // 位域标记：是否启用全局主机级标签队列
35
36      struct device shost_dev;               // SCSI主机设备模型对象，用于sysfs设备展示
37      struct device *dma_dev;                // DMA绑定设备指针，用于虚拟主机DMA寻址适配
38
39      unsigned long hostdata[] __attribute__ ((aligned (sizeof(unsigned long)))); // 柔性数组，驱动私有数据存储空间
40
41      /* 其他成员省略 */
42  };
```

### 7.3.3. SCSI主机模板结构体[¶](#id11 "永久链接至标题")

SCSI主机模板结构体（struct scsi_host_template）用于定义SCSI主机适配器的能力参数、回调函数接口，是底层驱动与SCSI中间层的绑定载体。内核通过该模板识别驱动的命令处理方式、错误处理能力、硬件参数等特性。

scsi_host_template结构体(内核源码/include/scsi/scsi_host.h)[¶](#id51 "永久链接至代码")

```c
 1  struct scsi_host_template {
 2      int (*queuecommand)(struct Scsi_Host *, struct scsi_cmnd *); // SCSI命令下发入口，底层驱动核心实现
 3
 4      int (*eh_abort_handler)(struct scsi_cmnd *);        // 命令中止处理
 5      int (*eh_host_reset_handler)(struct scsi_cmnd *);   // 主机重置处理
 6
 7      struct module *module;        // 绑定当前内核模块
 8      const char *name;             // SCSI主机适配器名称
 9
10      int can_queue;                // 主机最大并发排队命令数
11      int this_id;                  // SCSI总线主机适配器ID
12      short cmd_per_lun;            // 单个LUN最大并发命令数
13      unsigned int max_sectors;     // 单条命令最大处理扇区数
14      unsigned short sg_tablesize;  // 最大SG散列聚合分片数
15
16      unsigned emulated:1;          // 标记是否为虚拟模拟设备
17
18      /* 其他成员省略 */
19  };
```

### 7.3.4. SCSI命令结构体[¶](#id12 "永久链接至标题")

SCSI命令结构体（struct scsi_cmnd）用于封装单条SCSI命令的所有信息，包含命令描述块、传输方向、设备信息、执行结果、Sense错误缓冲区、剩余传输长度等，是SCSI命令处理的数据载体。

scsi_cmnd结构体(内核源码/include/scsi/scsi_cmnd.h)[¶](#id52 "永久链接至代码")

```c
 1  struct scsi_cmnd {
 2      struct scsi_device *device;         // 关联的SCSI设备对象
 3      unsigned long jiffies_at_alloc;     // 命令分配时间戳，用于超时统计
 4      int retries;                        // 命令重试次数
 5      unsigned short cmd_len;             // SCSI命令CDB有效长度
 6      enum dma_data_direction sc_data_direction; // 数据传输方向
 7
 8      unsigned char cmnd[32];             // SCSI命令描述块(CDB)，存储操作码+参数
 9
10      struct scsi_data_buffer sdb;        // 命令数据传输缓冲区
11
12      unsigned resid_len;                 // 未完成传输的剩余数据长度
13      unsigned sense_len;                 // Sense错误数据有效长度
14      unsigned char *sense_buffer;        // 错误感知数据缓冲区，存储异常信息
15
16      int flags;                          // 命令状态标志位
17      unsigned long state;                // 命令当前执行状态
18      int result;                         // 底层驱动返回的命令执行结果码
19
20      /* 其他成员省略 */
21  };
```

### 7.3.5. SCSI逻辑设备结构体[¶](#id13 "永久链接至标题")

SCSI逻辑设备结构体（struct scsi_device）用于抽象一个SCSI逻辑设备（LUN）。内核每扫描到一个可用SCSI磁盘/设备，都会生成一个该结构体实例， 统一管理设备属性、状态、队列参数、超时重试策略，是上层块设备与底层SCSI主机的中间映射载体。

scsi_device结构体(内核源码/include/scsi/scsi_device.h)[¶](#id53 "永久链接至代码")

```c
 1  struct scsi_device {
 2      struct Scsi_Host *host;                // 所属SCSI主机适配器指针
 3      struct scsi_target *sdev_target;       // 所属Target目标设备指针
 4      struct request_queue *request_queue;   // 设备块请求队列，管理I/O请求调度
 5
 6      struct list_head siblings;             // 同一Host下所有SCSI设备链表节点
 7      struct list_head same_target_siblings; // 同一Target下的设备链表节点
 8
 9      atomic_t device_blocked;               // 设备阻塞标记，处理QUEUE_FULL状态
10      unsigned short queue_depth;            // 当前设备I/O队列深度
11      unsigned short max_queue_depth;        // 设备支持的最大队列深度
12
13      unsigned int id;                       // 设备Target ID
14      unsigned int channel;                  // 设备总线通道号
15      u64 lun;                               // 设备逻辑单元LUN编号
16      unsigned sector_size;                  // 设备单扇区字节大小
17
18      unsigned char type;                    // SCSI设备类型（磁盘/光驱/RAID等）
19      char scsi_level;                       // 设备支持的SCSI协议版本
20      char inq_periph_qual;                  // INQUIRY外设设备有效状态标识
21
22      const char *vendor;                    // 设备厂商名称
23      const char *model;                     // 设备型号信息
24      const char *rev;                       // 设备固件版本
25
26      unsigned int eh_timeout;               // SCSI错误处理超时时间
27      unsigned removable:1;                  // 可移动设备标记
28      unsigned offline:1;                    // 设备离线状态标记
29      unsigned ready:1;                      // 设备就绪状态标记
30      unsigned tagged_supported:1;           // 设备是否支持SCSI标签队列
31
32      atomic_t iorequest_cnt;                // 累计下发I/O请求计数
33      atomic_t iodone_cnt;                   // 累计完成I/O请求计数
34      atomic_t ioerr_cnt;                    // 累计I/O错误计数
35
36      struct device sdev_dev;                // 内核设备模型对象，用于sysfs管理
37      enum scsi_device_state sdev_state;     // 设备当前运行状态枚举
38      void *hostdata;                        // 底层驱动私有数据指针
39
40      unsigned long sdev_data[] __attribute__((aligned(sizeof(unsigned long)))); // 设备私有柔性数组
41
42      /* 其他成员省略 */
43  };
```

### 7.3.6. SCSI目标设备结构体[¶](#id14 "永久链接至标题")

SCSI目标设备结构体（struct scsi_target）用于管理SCSI总线上的一个目标设备节点（Target），一个Target下可挂载多个LUN（scsi_device）。 该结构体负责统一维护Target级别的设备状态、扫描信息、资源引用，实现多LUN设备的统一管理。

scsi_target结构体(内核源码/include/scsi/scsi_device.h)[¶](#id54 "永久链接至代码")

```c
 1  struct scsi_target {
 2      struct list_head siblings;             // 同一主机下所有Target设备链表节点
 3      struct list_head devices;              // 该Target下属所有LUN设备链表头
 4      struct device dev;                     // Target内核设备模型对象，用于sysfs管理
 5      struct kref reap_ref;                  // Target设备引用计数，防止内存泄漏
 6
 7      unsigned int channel;                  // 设备所属总线通道号
 8      unsigned int id;                       // Target设备唯一ID
 9
10      atomic_t target_busy;                  // 统计底层驱动活跃命令数
11      atomic_t target_blocked;               // Target阻塞标记，处理设备繁忙状态
12
13      unsigned int can_queue;                // Target级最大并发命令数限制
14      char scsi_level;                       // 设备支持的SCSI协议版本
15      enum scsi_target_state state;          // Target当前运行状态枚举
16
17      void *hostdata;                        // 底层驱动私有数据指针
18      unsigned long starget_data[] __attribute__((aligned(sizeof(unsigned long)))); // 传输层私有柔性数组
19
20      /* 其他成员省略 */
21  };
```

### 7.3.7. SCSI数据缓冲区结构体[¶](#id15 "永久链接至标题")

SCSI数据缓冲区结构体（struct scsi_data_buffer）内嵌于scsi_cmnd，所有SCSI读写、校验、拷贝的数据传输均通过该结构体完成，统一管理线性内存与SG散列聚合内存。

scsi_data_buffer结构体(内核源码/include/scsi/scsi_device.h)[¶](#id55 "永久链接至代码")

```c
struct scsi_data_buffer {
    struct sg_table table;                 // SG散列聚合内存表，用于大块数据传输
    unsigned length;                       // 当前数据缓冲区有效长度
};
```

### 7.3.8. SCSI磁盘结构体[¶](#id16 "永久链接至标题")

SCSI磁盘结构体（struct scsi_disk）用于描述SCSI类型磁盘设备，承接上层scsi_device设备，绑定内核标准块设备gendisk，完成SCSI协议设备到系统通用磁盘设备的映射。

scsi_disk结构体(内核源码/drivers/scsi/sd.h)[¶](#id56 "永久链接至代码")

```c
 1  struct scsi_disk {
 2      struct scsi_device *device; // 关联的SCSI逻辑设备
 3      struct device   disk_dev;   // SCSI磁盘sysfs设备节点
 4      struct gendisk  *disk;      // 内核通用块设备结构体
 5
 6      atomic_t    openers;        // 设备打开引用计数
 7      sector_t    capacity;       // 磁盘有效容量
 8
 9      /* 数据传输参数约束 */
10      int max_retries;        // I/O最大重试次数
11      u32 min_xfer_blocks;    // 最小传输块数
12      u32 max_xfer_blocks;    // 最大传输块数
13      u32 opt_xfer_blocks;    // 最优传输块数
14
15      /* 磁盘硬件与块参数 */
16      unsigned int    physical_block_size;// 物理块大小
17      u8  media_present;      // 介质是否存在
18      u8  write_prot;         // 磁盘写保护状态
19
20      /* 其他成员省略 */
21  };
```

## 7.4. SCSI子系统核心函数[¶](#id17 "永久链接至标题")

### 7.4.1. 主机分配[¶](#id18 "永久链接至标题")

#### 7.4.1.1. scsi_host_alloc函数[¶](#scsi-host-alloc "永久链接至标题")

scsi_host_alloc函数用于分配SCSI主机适配器结构体内存，并预留驱动私有数据空间，是SCSI主机注册的第一步，所有SCSI驱动初始化必须调用该函数。

函数原型：

```c
struct Scsi_Host *scsi_host_alloc(const struct scsi_host_template *sht, int privsize);
```

参数说明：

- sht：SCSI主机模板结构体指针，定义主机能力与回调函数。
    
- privsize：驱动私有数据结构体大小，内核会自动预留对应内存空间。
    

返回值：成功返回Scsi_Host主机结构体指针，失败返回NULL。

### 7.4.2. 主机释放[¶](#id19 "永久链接至标题")

#### 7.4.2.1. scsi_host_put函数[¶](#scsi-host-put "永久链接至标题")

scsi_host_put函数用于释放SCSI主机适配器的引用，是scsi_host_alloc的逆操作，当驱动模块卸载、设备热拔插或主机注册失败需要回滚时调用。 它会递减主机的底层设备模型引用计数，当引用计数降为0时，内核将释放Scsi_Host结构体及其在scsi_host_alloc时预留的私有数据内存，防止内存泄漏。

函数原型：

```c
void scsi_host_put(struct Scsi_Host *shost);
```

参数说明：

- shost：需要释放引用的SCSI主机结构体指针。
    

### 7.4.3. 主机注册[¶](#id20 "永久链接至标题")

#### 7.4.3.1. scsi_add_host函数[¶](#scsi-add-host "永久链接至标题")

scsi_add_host函数用于将分配完成的SCSI主机适配器注册到内核SCSI子系统，完成设备模型初始化、资源绑定，使主机正式被内核识别。

函数原型：

```c
int scsi_add_host(struct Scsi_Host *host, struct device *dev);
```

参数说明：

- host：已分配的SCSI主机结构体指针。
    
- dev：父设备指针，虚拟设备可传入NULL。
    

返回值：成功返回0，失败返回负错误码。

### 7.4.4. 设备扫描[¶](#id21 "永久链接至标题")

#### 7.4.4.1. scsi_scan_host函数[¶](#scsi-scan-host "永久链接至标题")

scsi_scan_host函数用于扫描指定SCSI主机下挂载的所有Target/LUN设备，枚举设备、初始化设备参数、创建设备节点，是驱动加载后识别SCSI设备的核心函数。

函数原型：

```c
void scsi_scan_host(struct Scsi_Host *host);
```

参数说明：

- host：待扫描的SCSI主机结构体指针。
    

### 7.4.5. 命令收尾回调[¶](#id22 "永久链接至标题")

#### 7.4.5.1. scsi_done函数[¶](#scsi-done "永久链接至标题")

scsi_done函数是SCSI命令生命周期的终点，底层驱动完成命令硬件处理、数据拷贝、异常填充后，必须调用该函数通知SCSI中间层，标记命令执行完成，触发内核后续的I/O收尾、请求释放、上层回调等流程。

函数原型：

```c
void scsi_done(struct scsi_cmnd *cmd);
```

参数说明：

- cmd：已完成处理的SCSI命令结构体指针。
    

### 7.4.6. SG数据拷贝[¶](#sg "永久链接至标题")

#### 7.4.6.1. scsi_sg_copy_from_buffer函数[¶](#scsi-sg-copy-from-buffer "永久链接至标题")

scsi_sg_copy_from_buffer函数用于线性内存数据拷贝至SG散列缓冲区，主要适配SCSI **写操作** 场景，将内核线性连续缓冲区的数据，拆分拷贝到SCSI命令的SG离散缓冲区中，自动适配散列内存分片规则，屏蔽SG内存碎片化细节，简化底层驱动数据拷贝。

函数原型：

```c
int scsi_sg_copy_from_buffer(struct scsi_cmnd *cmd,
                                        const void *buf, int buflen);
```

参数说明：

- cmd：当前待处理的SCSI命令结构体，函数自动提取内部SG散列缓冲区信息。
    
- buf：源线性连续数据缓冲区指针。
    
- buflen：需要拷贝的数据字节长度。
    

返回值：成功返回实际拷贝字节数，失败返回0。

#### 7.4.6.2. scsi_sg_copy_to_buffer函数[¶](#scsi-sg-copy-to-buffer "永久链接至标题")

scsi_sg_copy_to_buffer函数用于SG散列缓冲区数据拷贝至线性内存，主要适配SCSI **读操作** 场景，遍历SCSI命令的SG离散内存分片，将聚合数据完整拷贝到内核线性连续缓冲区，统一离散数据输出格式。

函数原型：

```c
int scsi_sg_copy_to_buffer(struct scsi_cmnd *cmd,
                                        void *buf, int buflen);
```

参数说明：

- cmd：当前待处理的SCSI命令结构体，函数自动提取内部SG散列缓冲区信息。
    
- buf：目标线性连续数据缓冲区指针。
    
- buflen：需要拷贝的数据字节长度。
    

返回值：成功返回实际拷贝字节数，失败返回0。

### 7.4.7. 数据残余量设置[¶](#id23 "永久链接至标题")

#### 7.4.7.1. scsi_set_resid函数[¶](#scsi-set-resid "永久链接至标题")

在SCSI命令执行完成后，如果设备实际传输的数据量小于主机请求的数据量，底层驱动需要记录这个“差额”，即残余数据长度。 scsi_set_resid函数用于设置该残余量，防止上层误以为数据已全部传输完成。

函数原型：

```c
void scsi_set_resid(struct scsi_cmnd *cmd, unsigned int resid);
```

参数说明：

- cmd：指向当前处理的SCSI命令结构体的指针。
    
- resid：残余数据长度，单位字节，其计算逻辑通常为：主机请求的总传输字节数 - 设备实际成功传输的字节数。
    

## 7.5. SCSI标准命令[¶](#id24 "永久链接至标题")

### 7.5.1. SCSI命令基本原理与CDB结构[¶](#scsicdb "永久链接至标题")

SCSI命令是主机与SCSI设备交互的唯一指令，所有读写、查询、配置、校验操作均依赖标准化的SCSI命令完成。 SCSI命令以CDB（Command Description Block，命令描述块）为载体，存储于scsi_cmnd->cmnd[]数组中，由主机下发、设备解析执行。

SCSI命令根据长度分为6字节短命令与10字节长命令，还有16字节扩展命令，现代Linux内核与存储设备默认使用10字节命令，以支持更大LBA寻址空间，适配大容量磁盘。 所有CDB命令通用基础字段如下：

- Opcode（操作码）：CDB第0字节，标识SCSI命令类型，内核与驱动通过该字段分发处理逻辑。
    
- LBA地址：逻辑块寻址地址，标识磁盘读写起始扇区位置。
    
- Transfer Length：传输长度，标识本次操作的扇区数量/数据长度。
    
- Control控制位：命令结束标记，控制命令同步、链接等属性。
    

### 7.5.2. SCSI核心命令[¶](#id25 "永久链接至标题")

Linux内核所有SCSI设备（机械硬盘、SSD、光驱、U盘、RAID阵列、SAN存储等）均遵循SPC（SCSI Primary Commands）国际标准协议。 内核SCSI子系统对标准SCSI命令做了统一适配，所有合规的硬件/虚拟SCSI驱动都必须实现基础命令集，以完成内核设备枚举、I/O调度、设备管理等通用功能。

#### 7.5.2.1. 6字节基础短命令[¶](#id26 "永久链接至标题")

6字节SCSI命令为早期SCSI-2协议规范，CDB固定6字节，LBA寻址空间小、传输长度有限，不支持大容量磁盘， 仅用于设备状态查询、简单参数配置等非大数据传输场景。

- **TEST_UNIT_READY 设备就绪检测（0x00）**
    

命令作用：基础设备状态探测命令，内核高频轮询调用，用于检测SCSI设备当前是否处于就绪可用状态。该命令无数据读写、无参数配置，仅获取设备健康状态。

使用场景：设备上电初始化、总线扫描、热插拔恢复、IO超时重试后状态校验。设备正常就绪返回GOOD状态，未就绪、故障、离线则返回CHECK_CONDITION及对应错误码。

- **INQUIRY 设备查询命令（0x12）**
    

命令作用：标准6字节查询命令。用于读取设备固有静态信息，完成设备类型识别、协议版本匹配、厂商型号校验。

使用场景：主机总线扫描阶段使用，内核通过返回数据区分磁盘、光驱、RAID等设备类型，完成设备注册与绑定，是所有SCSI设备接入系统的前置。

- **MODE_SENSE_6 模式读取（6字节，0x1A）**
    

命令作用：6字节版本设备参数读取命令，用于获取SCSI设备的工作模式参数，包含缓存策略、读写超时、介质类型、硬件特性配置等。

使用场景：老旧存储设备参数查询，适配低版本SCSI协议设备，仅支持有限长度的模式页数据读取。

- **MODE_SELECT_6 模式配置（6字节，0x15）**
    

命令作用：6字节版本设备参数配置命令，与MODE_SENSE_6配对使用，用于修改设备默认工作参数，配置缓存开关、读写优先级、纠错策略等硬件特性。

使用场景：初始化阶段设备参数初始化、老旧设备模式适配，现代大容量设备基本废弃，改用10字节版本。

- **READ_6 短读命令（0x08）**
    

命令作用：标准6字节数据读取命令，CDB长度短，LBA与传输长度字段位数受限，仅支持小容量磁盘、小范围数据读取。

使用场景：兼容早期小容量SCSI设备，仅老旧设备使用，现代Linux内核默认优先使用10字节读命令。

- **WRITE_6 短写命令（0x0A）**
    

命令作用：6字节数据写入命令，与READ_6配对，用于小容量、小数据量磁盘写入操作，寻址与传输能力有限。

使用场景：老旧SCSI设备兼容写入，现代Linux内核默认优先使用10字节写命令。

#### 7.5.2.2. 10字节标准长命令[¶](#id27 "永久链接至标题")

10字节SCSI命令为SCSI-3及SPC-4主流规范，扩展32位LBA寻址，支持TB级大容量磁盘，传输长度灵活可控，是当前Linux系统SSD、SAS、FC等存储的默认命令。

- **MODE_SENSE_10 高级模式读取（0x5A）**
    

命令作用：10字节增强版模式查询命令，支持读取完整的设备模式页、缓存参数、PI校验参数、电源管理参数等高级配置。

使用场景：现代存储设备初始化参数读取、硬件特性探测、存储阵列参数校验，是主流设备的标准查询接口。

- **MODE_SELECT_10 高级模式配置（0x55）**
    

命令作用：10字节增强版模式配置命令，配套MODE_SENSE_10，支持配置完整的设备高级工作模式，适配现代存储丰富的硬件特性。

使用场景：系统初始化设备参数固化、缓存策略配置、硬件功能开关设置。

- **READ_CAPACITY_10 容量查询（0x25）**
    

命令作用：10字节磁盘容量查询标准命令，用于获取设备有效最大LBA地址与单扇区字节大小，内核据此计算磁盘总容量，初始化块设备容量参数。

使用场景：绝大多数常规容量磁盘的容量探测，是Linux内核默认的容量读取方式。

- **READ_10 标准读命令（0x28）**
    

命令作用：现代存储核心读命令，32位LBA寻址，支持大容量磁盘任意扇区读取，支持大范围连续扇区批量读取。

使用场景：系统日常文件读取、程序加载、磁盘数据读取，适配所有主流SCSI存储设备。

- **WRITE_10 标准写命令（0x2A）**
    

命令作用：现代存储核心写命令，与READ_10配对，支持大容量磁盘任意LBA扇区批量数据写入。

使用场景：文件写入、数据保存、缓存刷新写入等写IO场景。

- **VERIFY_10 数据校验命令（0x2F）**
    

命令作用：10字节磁盘数据完整性校验命令，无需主机与设备数据拷贝，仅校验指定LBA区间的扇区合法性、数据完整性、介质有效性。

使用场景：系统磁盘自检、坏块扫描、数据一致性校验等，保障存储数据可靠性。

- **SYNCHRONIZE_CACHE 缓存同步命令（0x35）**
    

命令作用：设备缓存刷新命令，强制将磁盘板载缓存中的脏数据刷入物理存储介质，防止断电数据丢失。

使用场景：系统关机、重启、文件系统同步、umount卸载、手动缓存刷盘，是数据安全持久化的关键命令。

#### 7.5.2.3. 16字节扩展命令[¶](#id28 "永久链接至标题")

16字节SCSI命令为扩展协议，支持64位超宽LBA寻址，专门适配PB级超大容量磁盘、分布式存储、SAN阵列设备。

- **READ_CAPACITY_16 扩展容量查询（0x9E）**
    

命令作用：16字节超大容量磁盘容量查询命令，提供64位LBA寻址能力，支持远超32位寻址上限的超大存储设备容量上报。

使用场景：超大容量SSD、企业级SAN存储、磁盘阵列、分布式存储设备容量探测，内核优先尝试16字节查询，失败后降级使用10字节命令。

## 7.6. 内核SCSI子系统源码解析[¶](#id29 "永久链接至标题")

内核SCSI子系统相关源码都位于内核源码/drivers/scsi/目录下，存在众多驱动文件，各层代表驱动文件如下：

![../_images/subsystem_scsi_subsystem_0.jpg](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/subsystem_scsi_subsystem_0.jpg)

### 7.6.1. 较高层驱动[¶](#id30 "永久链接至标题")

较高层驱动处理特定类型的SCSI设备，向用户空间提供标准的块设备接口（如/dev/sda）或字符设备接口（如/dev/sg0），负责设备特有的命令处理和数据转换。

以下选取 **瑞芯微6.1.99内核版本** 的sd.c进行说明。

#### 7.6.1.1. sd.c驱动解析[¶](#sd-c "永久链接至标题")

sd.c专门用于处理SCSI磁盘（TYPE_DISK），它在系统中最终呈现为我们熟悉的/dev/sda、/dev/sdb等块设备。

**核心数据结构**

sd.c通过定义一个scsi_driver结构体，向SCSI中间层注册自己的回调函数：

核心数据结构(位于内核源码/drivers/scsi/sd.c)[¶](#id57 "永久链接至代码")

```c
 1  static struct scsi_driver sd_template = {
 2      .gendrv = {
 3          .name       = "sd",
 4          .probe      = sd_probe,       // 设备发现时调用
 5          .remove     = sd_remove,      // 设备移除时调用
 6          .pm         = &sd_pm_ops,     // 电源管理回调
 7      },
 8      .init_command   = sd_init_command, // 将request转换为SCSI CDB
 9      .done           = sd_done,         // 处理SCSI命令完成后的结果
10      .eh_action      = sd_eh_action,    // 错误恢复动作
11
12      /* 省略部分成员 */
13  };
```

**设备探测**

当底层驱动调用scsi_scan_host后，中间层发送INQUIRY命令发现这是一个磁盘（TYPE_DISK），就会触发sd.c的Probe流程。

sd_probe函数(位于内核源码/drivers/scsi/sd.c)[¶](#id58 "永久链接至代码")

```c
 1  // 以下函数省略源码部分内容
 2
 3  static int sd_probe(struct device *dev) {
 4      // 分配scsi_disk和gendisk
 5      sdkp = kzalloc(sizeof(*sdkp), GFP_KERNEL);
 6      gd = blk_mq_alloc_disk_for_queue(...);
 7
 8      // 生成设备名，如sda、sdb
 9      sd_format_disk_name("sd", index, gd->disk_name, DISK_NAME_LEN);
10
11      // 设置块设备操作集
12      gd->fops = &sd_fops;
13
14      // 重新验证磁盘，读取容量、缓存等
15      sd_revalidate_disk(gd);
16
17      // 向块设备层注册设备，生成/dev/sdX节点
18      device_add_disk(dev, gd, NULL);
19  }
```

**重新验证磁盘**

sd_revalidate_disk函数通过发送一系列SCSI命令来摸清设备的底细，可以概括为“一问容量，二问特性，三问状态，四定参数”。

sd_revalidate_disk函数(位于内核源码/drivers/scsi/sd.c)[¶](#id59 "永久链接至代码")

```c
 1  // 以下函数省略源码部分内容
 2
 3  static int sd_revalidate_disk(struct gendisk *disk)
 4  {
 5      struct scsi_disk *sdkp = scsi_disk(disk);
 6      struct scsi_device *sdp = sdkp->device;
 7      // ... 变量初始化 ...
 8
 9      // 基础检查，如果设备离线则直接退出
10      if (!scsi_device_online(sdp))
11          goto out;
12
13      // 分配临时缓冲区用于接收SCSI命令的响应数据
14      buffer = kmalloc(SD_BUF_SIZE, GFP_KERNEL);
15
16      // 磁盘起转(spin up)，发送TEST_UNIT_READY命令，如果磁盘未就绪，则让磁盘电机起转，等待其准备就绪
17      sd_spinup_disk(sdkp);
18
19      // 1.读取容量，发送READ_CAPACITY_10或READ_CAPACITY_16命令，获取磁盘的总扇区数，以及逻辑/物理扇区大小
20      if (sdkp->media_present) {
21          sd_read_capacity(sdkp, buffer);
22
23          // 2.获取高级特性，如果设备支持Vital Product Data (VPD)，则读取其高级能力声明
24          if (scsi_device_supports_vpd(sdp)) {
25              sd_read_block_provisioning(sdkp);   // 是否支持精简配置
26              sd_read_block_limits(sdkp);         // I/O限制，最大传输块数、UNMAP粒度、最优传输大小等
27              sd_read_block_characteristics(sdkp);// 设备特性，是否为SSD/非旋转设备、SMR盘、ZBC磁盘
28              sd_zbc_read_zones(sdkp, buffer);    // 如果是ZBC磁盘，读取Zone(区域)的布局信息
29              sd_read_cpr(sdkp);                  // 定位多磁头/多致动器磁盘特性
30          }
31
32          // 如果与上次扫描不同，打印容量变更日志
33          sd_print_capacity(sdkp, old_capacity);
34
35          // 3.获取设备状态与缓存策略，通过发送MODE_SENSE命令读取设备的模式页面(Mode Pages)，了解其运行状态
36          sd_read_write_protect_flag(sdkp, buffer); // 检查磁盘是否被写保护 ，如SD卡的物理锁、磁带写保护
37          sd_read_cache_type(sdkp, buffer);         // 检查读写缓存策略及是否支持FUA
38          sd_read_app_tag_own(sdkp, buffer);        // 检查DIF/DIX(端到端数据保护)的ATO位
39          sd_read_write_same(sdkp, buffer);         // 探测是否支持WRITE SAME命令，用于快速清零或配合UNMAP
40          sd_read_security(sdkp, buffer);           // 检查是否支持TCG Opal等硬件加密安全协议
41          sd_config_protection(sdkp);               // 根据检查结果启用或禁用DIF/DIX数据完整性校验
42      }
43
44      // 配置Flush策略，如果开启了写缓存(WCE)，则告诉块层需要发送SYNCHRONIZE_CACHE命令来保证数据缓存同步
45      sd_set_flush_flag(sdkp);
46
47      // 4.计算并设置I/O尺寸限制，告诉块层：最小I/O 尺寸(io_min)、最优I/O尺寸 (io_opt)、单次最大传输扇区数(max_sectors)
48      // 这些参数直接决定了文件系统(如ext4)如何对齐I/O以获得最佳性能
49      dev_max = sdp->use_16_for_rw ? SD_MAX_XFER_BLOCKS : SD_DEF_XFER_BLOCKS;
50
51      // 省略中间计算逻辑...
52      q->limits.max_sectors = rw_max;
53
54      // 标记首次扫描结束，并向内核和用户态广播最新的磁盘容量，这会触发udev重新扫描分区表，如生成sda1、sda2
55      sdkp->first_scan = 0;
56      set_capacity_and_notify(disk, logical_to_sectors(sdp, sdkp->capacity));
57
58      // 配置WRITE ZEROES(快速写零)的降级策略
59      sd_config_write_same(sdkp);
60      kfree(buffer);
61
62      // 特殊设备后置处理，对于ZBC分区磁盘，必须在容量设置完成后，才能重新验证Zone的状态
63      if (sd_zbc_revalidate_zones(sdkp))
64          set_capacity_and_notify(disk, 0);
65
66  out:
67      return 0;
68  }
```

**构建SCSI命令**

当文件系统产生I/O，块层将其打包为request，SCSI中间层将其转为scsi_cmnd，然后调用sd_init_command。

sd_init_command函数(位于内核源码/drivers/scsi/sd.c)[¶](#id60 "永久链接至代码")

```c
 1  // 以下函数省略源码部分内容
 2
 3  static blk_status_t sd_init_command(struct scsi_cmnd *cmd)
 4  {
 5      struct request *rq = scsi_cmd_to_rq(cmd);
 6
 7      switch (req_op(rq)) {
 8      case REQ_OP_DISCARD:
 9          switch (scsi_disk(rq->q->disk)->provisioning_mode) {
10          case SD_LBP_UNMAP:
11              return sd_setup_unmap_cmnd(cmd);   // 构建UNMAP
12      // ...
13      case REQ_OP_WRITE_ZEROES:
14          return sd_setup_write_zeroes_cmnd(cmd);// 构建WRITE SAME
15      case REQ_OP_FLUSH:
16          return sd_setup_flush_cmnd(cmd);       // 构建SYNCHRONIZE_CACHE
17      case REQ_OP_READ:
18      case REQ_OP_WRITE:
19          return sd_setup_read_write_cmnd(cmd);  // 构建READ/WRITE(6/10/16/32)
20
21      // ... 处理ZBC分区磁盘的特殊命令
22      }
23  }
```

重点看sd_setup_read_write_cmnd函数，负责将块设备层下发的通用I/O请求，翻译并封装成底层硬件能看懂的SCSI读/写命令（CDB）。

sd_setup_read_write_cmnd函数(位于内核源码/drivers/scsi/sd.c)[¶](#id61 "永久链接至代码")

```c
  1  // 以下函数省略源码部分内容
  2
  3  static blk_status_t sd_setup_read_write_cmnd(struct scsi_cmnd *cmd)
  4  {
  5      // 提取请求核心参数
  6      struct request *rq = scsi_cmd_to_rq(cmd);
  7      struct scsi_device *sdp = cmd->device;
  8      struct scsi_disk *sdkp = scsi_disk(rq->q->disk);
  9
 10      // 将块层的扇区号转换为SCSI逻辑块地址(LBA)，并计算需要传输的块数
 11      sector_t lba = sectors_to_logical(sdp, blk_rq_pos(rq));
 12      unsigned int nr_blocks = sectors_to_logical(sdp, blk_rq_sectors(rq));
 13      bool write = rq_data_dir(rq) == WRITE; // 判断是读还是写
 14
 15      // 2. 为本次I/O分配并映射SG表，这是DMA传输的基础
 16      blk_status_t ret = scsi_alloc_sgtables(cmd);
 17      if (ret != BLK_STS_OK)
 18          return ret;
 19
 20      ret = BLK_STS_IOERR; // 默认错误状态
 21      // 3. 前置合法性检查
 22      if (!scsi_device_online(sdp) | sdp->changed) {
 23          scmd_printk(KERN_ERR, cmd, "device offline or changed\n");
 24          goto fail;
 25      }
 26      // 检查是否越界访问，如请求的结束位置超出了磁盘总容量
 27      if (blk_rq_pos(rq) + blk_rq_sectors(rq) > get_capacity(rq->q->disk)) {
 28          scmd_printk(KERN_ERR, cmd, "access beyond end of device\n");
 29          goto fail;
 30      }
 31      // 检查I/O请求是否按照设备的逻辑块大小对齐
 32      unsigned int mask = logical_to_sectors(sdp, 1) - 1;
 33      if ((blk_rq_pos(rq) & mask) | (blk_rq_sectors(rq) & mask)) {
 34          scmd_printk(KERN_ERR, cmd, "request not aligned to the logical block size\n");
 35          goto fail;
 36      }
 37
 38      // 4. 处理已知的硬件Bug
 39      // 某些劣质SD卡读卡器在访问最后1~2个逻辑块时会挂起
 40      // 如果触发了该bug标记，则主动截断请求，避免触碰危险区域
 41      threshold = sdkp->capacity - SD_LAST_BUGGY_SECTORS;
 42      if (unlikely(sdp->last_sector_bug && lba + nr_blocks > threshold)) {
 43          if (lba < threshold)
 44              nr_blocks = threshold - lba; // 截断到安全边界
 45          else
 46              nr_blocks = 1;               // 只访问单个安全块
 47      }
 48
 49      // 5. 处理ZBC分区磁盘的特殊追加写操作
 50      if (req_op(rq) == REQ_OP_ZONE_APPEND) {
 51          ret = sd_zbc_prepare_zone_append(cmd, &lba, nr_blocks);
 52          if (ret) goto fail;
 53      }
 54
 55      // 6. 配置数据完整性保护，如果设备或主机支持端到端的数据校验，防止静默数据损坏，则配置保护标志
 56      fua = rq->cmd_flags & REQ_FUA ? 0x8 : 0;
 57      dix = scsi_prot_sg_count(cmd);
 58      dif = scsi_host_dif_capable(cmd->device->host, sdkp->protection_type);
 59      if (dif | dix)
 60          protect = sd_setup_protect_cmnd(cmd, dix, dif);
 61
 62      // 7. 选择CDB命令描述块的长度
 63      // 根据LBA大小、传输块数以及设备能力，动态选择最合适的SCSI命令格式
 64      if (protect && sdkp->protection_type == T10_PI_TYPE2_PROTECTION) {
 65          // 特殊情况：Type 2保护必须使用32字节扩展CDB
 66          ret = sd_setup_rw32_cmnd(cmd, write, lba, nr_blocks, protect | fua);
 67      } else if (sdp->use_16_for_rw | (nr_blocks > 0xffff)) {
 68          // 大容量/大数据量：LBA > 2TB 或单次传输 > 65535 块，使用16字节CDB
 69          ret = sd_setup_rw16_cmnd(cmd, write, lba, nr_blocks, protect | fua);
 70      } else if ((nr_blocks > 0xff) | (lba > 0x1fffff) | sdp->use_10_for_rw | protect) {
 71          // 中等容量：LBA > 2TB(21位限制) 或单次传输 > 255 块，使用10字节CDB
 72          ret = sd_setup_rw10_cmnd(cmd, write, lba, nr_blocks, protect | fua);
 73      } else {
 74          // 小容量/小数据量：使用古老的6字节CDB
 75          ret = sd_setup_rw6_cmnd(cmd, write, lba, nr_blocks, protect | fua);
 76      }
 77
 78      if (unlikely(ret != BLK_STS_OK))
 79          goto fail;
 80
 81      // 8. 配置命令执行元数据
 82      cmd->transfersize = sdp->sector_size;           // 每次传输的基本单位大小
 83      cmd->underflow = nr_blocks << 9;                // 预期最小传输字节数
 84      cmd->allowed = sdkp->max_retries;               // 允许的最大硬件重试次数
 85      cmd->sdb.length = nr_blocks * sdp->sector_size; // 本次命令的总数据载荷长度
 86
 87      // 9. 调试日志与成功返回
 88      SCSI_LOG_HLQUEUE(1,
 89              scmd_printk(KERN_INFO, cmd,
 90                      "%s: block=%llu, count=%d\n", __func__,
 91                      (unsigned long long)blk_rq_pos(rq),
 92                      blk_rq_sectors(rq)));
 93      SCSI_LOG_HLQUEUE(2,
 94              scmd_printk(KERN_INFO, cmd,
 95                      "%s %d/%u 512 byte blocks.\n",
 96                      write ? "writing" : "reading", nr_blocks,
 97                      blk_rq_sectors(rq)));
 98
 99      /* 返回 BLK_STS_OK，表示命令已完全准备好，可以交给SCSI中间层下发给底层驱动了 */
100      return BLK_STS_OK;
101
102  fail:
103      // 失败清理：释放之前分配的SG表，防止内存泄漏
104      scsi_free_sgtables(cmd);
105      return ret;
106  }
```

**处理命令完成**

底层驱动执行完命令后，调用scsi_done，中间层最终回调sd_done。

sd_done函数(位于内核源码/drivers/scsi/sd.c)[¶](#id62 "永久链接至代码")

```c
 1  // 以下函数省略源码部分内容
 2
 3  static int sd_done(struct scsi_cmnd *SCpnt)
 4  {
 5      int result = SCpnt->result;
 6      struct scsi_sense_hdr sshdr;
 7
 8      //...
 9
10      // 1. 检查是否有错误
11      if (result) {
12          sense_valid = scsi_command_normalize_sense(SCpnt, &sshdr);
13      }
14
15      // 2. 根据Sense Key处理错误
16      switch (sshdr.sense_key) {
17      case HARDWARE_ERROR:
18      case MEDIUM_ERROR:
19          // 计算实际成功传输的字节数，处理部分完成的情况
20          good_bytes = sd_completed_bytes(SCpnt);
21          break;
22      // ...
23      case ILLEGAL_REQUEST:
24          // 如果设备不支持UNMAP或WRITE SAME，动态降级策略
25          case 0x20:  /* INVALID COMMAND OPCODE */
26          case 0x24:  /* INVALID FIELD IN CDB */
27              switch (SCpnt->cmnd[0]) {
28              case UNMAP:
29                  sd_config_discard(sdkp, SD_LBP_DISABLE);
30                  break;
31      }
32
33      // 3. 返回成功传输的字节数给中间层/块层
34      return good_bytes;
35  }
```

**电源管理**

在系统休眠(suspend)或关机(shutdown)时，sd.c会负责保护数据：

sd_shutdown函数(位于内核源码/drivers/scsi/sd.c)[¶](#id63 "永久链接至代码")

```c
 1  // 以下函数省略源码部分内容
 2
 3  static void sd_shutdown(struct device *dev)
 4  {
 5      // 1. 如果开启了写缓存，必须发送 SYNCHRONIZE_CACHE 将数据刷入磁盘
 6      if (sdkp->WCE && sdkp->media_present) {
 7          sd_sync_cache(sdkp, NULL);
 8      }
 9
10      // 2. 发送START STOP UNIT命令让磁盘电机停转，休眠磁头
11      if (sdkp->device->manage_shutdown) {
12          sd_start_stop_device(sdkp, 0); // 0表示STOP
13      }
14  }
```

**错误恢复**

当磁盘出现坏道或超时，SCSI中间层会触发EH，sd.c提供了sd_eh_action回调：

sd_eh_action函数(位于内核源码/drivers/scsi/sd.c)[¶](#id64 "永久链接至代码")

```c
// 以下函数省略源码部分内容

static int sd_eh_action(struct scsi_cmnd *scmd, int eh_disp)
{
    // 如果设备不断在读写命令上超时，但TEST UNIT READY却成功
    // sd.c会认为磁盘介质已损坏，主动将设备置为OFFLINE，防止系统卡死
    if (sdkp->medium_access_timed_out >= sdkp->max_medium_access_timeouts) {
        scsi_device_set_state(sdev, SDEV_OFFLINE);
    }
}
```

### 7.6.2. 中间层驱动[¶](#id31 "永久链接至标题")

中间层驱动有设备扫描，管理SCSI主机控制器、设备，维护命令队列，统一处理SCSI错误等职责。

#### 7.6.2.1. scsi.c驱动解析[¶](#scsi-c "永久链接至标题")

以下选取 **瑞芯微6.1.99内核版本** 的scsi.c进行说明。

**子系统初始化**

init_scsi是整个SCSI中间层启动的入口，通过subsys_initcall在系统早期执行。

init_scsi函数(位于内核源码/drivers/scsi/scsi.c)[¶](#id65 "永久链接至代码")

```c
 1  static int __init init_scsi(void)
 2  {
 3      int error;
 4
 5      // 初始化Procfs接口，如/proc/scsi/scsi
 6      error = scsi_init_procfs();
 7      if (error)
 8          goto cleanup_queue;
 9
10      // 初始化设备黑名单/quirk数据库
11      error = scsi_init_devinfo();
12      if (error)
13          goto cleanup_procfs;
14
15      // 初始化主机管理数据结构
16      error = scsi_init_hosts();
17      if (error)
18          goto cleanup_devlist;
19
20      // 初始化Sysctl接口
21      error = scsi_init_sysctl();
22      if (error)
23          goto cleanup_hosts;
24
25      // 注册Sysfs类和设备模型支持
26      error = scsi_sysfs_register();
27      if (error)
28          goto cleanup_sysctl;
29
30      // 初始化netlink通信
31      scsi_netlink_init();
32
33      printk(KERN_NOTICE "SCSI subsystem initialized\n");
34      return 0;
35
36  // 错误清理标签...
37  }
```

**命令完成的步骤**

scsi_finish_command函数是中间层最重要的函数之一。当底层驱动处理完命令并调用scsi_done后，最终会汇聚到这里。

scsi_finish_command函数(位于内核源码/drivers/scsi/scsi.c)[¶](#id66 "永久链接至代码")

```c
 1  // 以下函数省略源码部分内容
 2
 3  void scsi_finish_command(struct scsi_cmnd *cmd)
 4  {
 5      struct scsi_device *sdev = cmd->device;
 6      struct scsi_target *starget = scsi_target(sdev);
 7      struct Scsi_Host *shost = sdev->host;
 8      struct scsi_driver *drv;
 9      unsigned int good_bytes;
10
11      // 解除设备忙碌状态：告诉中间层，该设备/目标/主机现在可以接收新命令了
12      scsi_device_unbusy(sdev, cmd);
13      if (atomic_read(&shost->host_blocked)) atomic_set(&shost->host_blocked, 0);
14      if (atomic_read(&starget->target_blocked)) atomic_set(&starget->target_blocked, 0);
15      if (atomic_read(&sdev->device_blocked)) atomic_set(&sdev->device_blocked, 0);
16
17      // 默认假设所有请求的数据都成功传输了
18      good_bytes = scsi_bufflen(cmd);
19      // 如果不是透传命令，则调用较高层驱动(如sd.c)的done回调
20      if (!blk_rq_is_passthrough(scsi_cmd_to_rq(cmd))) {
21          int old_good_bytes = good_bytes;
22          drv = scsi_cmd_to_driver(cmd); // 获取sd_template
23          if (drv->done)
24              // sd_done会根据Sense数据，修正实际成功传输的字节数(good_bytes)
25              good_bytes = drv->done(cmd);
26
27          // 兼容处理，如果较高层ULD没有修改good_bytes，但底层返回了残余量(resid)，则扣除残余量
28          if (good_bytes == old_good_bytes)
29              good_bytes -= scsi_get_resid(cmd);
30      }
31
32      // 最终交还给块设备层，唤醒等待的进程
33      scsi_io_completion(cmd, good_bytes);
34  }
```

**动态队列管理**

真实的存储设备（尤其是低端磁盘）处理能力有限。如果主机发送命令过快，设备会返回QUEUE_FULL状态，中间层必须处理这种情况，而不是直接报错。

动态队列管理(位于内核源码/drivers/scsi/scsi.c)[¶](#id67 "永久链接至代码")

```c
 1  // 改变设备的队列深度
 2  int scsi_change_queue_depth(struct scsi_device *sdev, int depth)
 3  {
 4      // 限制深度不能超过主机控制器的最大能力，且不超过4096的安全上限
 5      depth = min_t(int, depth, scsi_device_max_queue_depth(sdev));
 6      if (depth > 0) {
 7          sdev->queue_depth = depth;
 8          wmb();
 9      }
10      // 同步更新块设备层的队列深度
11      if (sdev->request_queue)
12          blk_set_queue_depth(sdev->request_queue, depth);
13      sbitmap_resize(&sdev->budget_map, sdev->queue_depth);
14      return sdev->queue_depth;
15  }
16
17  // 跟踪QUEUE_FULL事件，调整队列深度
18  int scsi_track_queue_full(struct scsi_device *sdev, int depth)
19  {
20      // 防止同一jiffies内的多次QUEUE_FULL被重复计数
21      if ((jiffies >> 4) == (sdev->last_queue_full_time >> 4))
22          return 0;
23
24      sdev->last_queue_full_time = jiffies;
25
26      // 统计在特定深度下连续发生QUEUE_FULL的次数
27      if (sdev->last_queue_full_depth != depth) {
28          sdev->last_queue_full_count = 1;
29          sdev->last_queue_full_depth = depth;
30      } else {
31          sdev->last_queue_full_count++;
32      }
33
34      // 如果连续10次在该深度下都报告QUEUE_FULL，说明设备真的吃不消了
35      if (sdev->last_queue_full_count <= 10)
36          return 0;
37
38      // 触发降速，主动降低队列深度，减轻设备压力
39      return scsi_change_queue_depth(sdev, depth);
40  }
```

**设备VPD查询**

VPD(Vital Product Data)是SCSI设备提供的一组标准页面，包含设备的序列号、支持的命令、块限制等关键信息，scsi.c提供了统一的获取框架。

设备VPD查询(位于内核源码/drivers/scsi/scsi.c)[¶](#id68 "永久链接至代码")

```c
 1  // 以下函数省略源码部分内容
 2
 3  // 内部辅助函数：执行INQUIRY命令获取特定VPD页面
 4  static int scsi_vpd_inquiry(struct scsi_device *sdev, unsigned char *buffer, u8 page, unsigned len)
 5  {
 6      int result;
 7      unsigned char cmd[16];
 8
 9      if (len < 4)
10          return -EINVAL;
11
12      cmd[0] = INQUIRY;
13      cmd[1] = 1;      // EVPD=1，表示请求VPD页面而非标准INQUIRY
14      cmd[2] = page;   // 请求的页面号(如0x80序列号, 0x83设备标识, 0xB0块限制)
15      cmd[3] = len >> 8;
16      cmd[4] = len & 0xff;
17      cmd[5] = 0;
18
19      // 执行命令，超时设为30秒，最多重试3次
20      result = scsi_execute_req(sdev, cmd, DMA_FROM_DEVICE, buffer,
21              len, NULL, 30 * HZ, 3, NULL);
22
23  }
24
25  // 对外接口：安全地获取VPD页面
26  int scsi_get_vpd_page(struct scsi_device *sdev, u8 page, unsigned char *buf, int buf_len)
27  {
28      int result, vpd_len;
29
30      // 1. 先询问设备该VPD页面有多大，防止老旧设备对过大缓冲区报错
31      vpd_len = scsi_get_vpd_size(sdev, page);
32      if (vpd_len <= 0)
33          return -EINVAL;
34
35      vpd_len = min(vpd_len, buf_len);
36      memset(buf, 0, buf_len);
37
38      // 2. 使用确认的大小再次请求，获取完整数据
39      result = scsi_vpd_inquiry(sdev, buf, page, vpd_len);
40      if (result < 0)
41          return -EINVAL;
42      else if (result > vpd_len)
43          dev_warn_once(&sdev->sdev_gendev,
44                  "%s: VPD page 0x%02x result %d > %d bytes\n",
45                  __func__, page, result, vpd_len);
46
47      return 0;
48  }
49
50  // 在设备发现时，自动挂载常用的 VPD 页面到 scsi_device 结构中
51  void scsi_attach_vpd(struct scsi_device *sdev)
52  {
53      int i;
54      struct scsi_vpd *vpd_buf;
55
56      // 先获取Page 0，看看设备支持哪些页面
57      vpd_buf = scsi_get_vpd_buf(sdev, 0);
58      if (!vpd_buf)
59          return;
60
61      // 遍历支持的页面列表，自动拉取并缓存关键页面
62      for (i = 4; i < vpd_buf->len; i++) {
63          if (vpd_buf->data[i] == 0x80) scsi_update_vpd_page(sdev, 0x80, &sdev->vpd_pg80); // 序列号
64          if (vpd_buf->data[i] == 0x83) scsi_update_vpd_page(sdev, 0x83, &sdev->vpd_pg83); // 设备标识
65          if (vpd_buf->data[i] == 0xb0) scsi_update_vpd_page(sdev, 0xb0, &sdev->vpd_pgb0); // 块限制(最大传输大小等)
66          // ... 其他页面
67      }
68      kfree(vpd_buf);
69  }
```

**设备查找与引用管理**

在内核中，设备可能随时被热拔插，如果驱动正在查找设备时设备被移除，会导致空指针解引用（Kernel Panic），scsi.c提供了带引用计数保护的查找机制。

scsi_device_lookup函数(位于内核源码/drivers/scsi/scsi.c)[¶](#id69 "永久链接至代码")

```c
 1  // 带引用计数保护的设备查找
 2  struct scsi_device *scsi_device_lookup(struct Scsi_Host *shost,
 3          uint channel, uint id, u64 lun)
 4  {
 5      struct scsi_device *sdev;
 6      unsigned long flags;
 7
 8      // 1. 加锁保护链表遍历
 9      spin_lock_irqsave(shost->host_lock, flags);
10      sdev = __scsi_device_lookup(shost, channel, id, lun);
11
12      // 2. 如果找到了，尝试增加引用计数(scsi_device_get)
13      // 如果设备正在被删除，get会失败，返回NULL，确保安全
14      if (sdev && scsi_device_get(sdev))
15          sdev = NULL;
16
17      spin_unlock_irqrestore(shost->host_lock, flags);
18
19      return sdev; // 调用者使用完毕后，必须调用scsi_device_put(sdev)释放引用
20  }
```

#### 7.6.2.2. scsi_lib.c驱动解析[¶](#scsi-lib-c "永久链接至标题")

scsi_lib.c的主要职责是对接Linux块层多队列（blk-mq）架构，负责将块层的I/O请求（request）转化为SCSI命令（scsi_cmnd），管理SG列表，处理命令的完成与错误恢复，并提供同步发送SCSI命令功能。

以下选取 **瑞芯微6.1.99内核版本** 的scsi_lib.c进行说明。

**块层入口**

当块层准备好一个request时，会调用scsi_queue_rq函数，它是SCSI命令生命周期的起点。

scsi_queue_rq函数(位于内核源码/drivers/scsi/scsi_lib.c)[¶](#id70 "永久链接至代码")

```c
 1  // 以下函数省略源码部分内容
 2
 3  static blk_status_t scsi_queue_rq(struct blk_mq_hw_ctx *hctx,
 4                                  const struct blk_mq_queue_data *bd)
 5  {
 6      struct request *req = bd->rq;
 7      struct scsi_device *sdev = req->q->queuedata;
 8      struct scsi_cmnd *cmd = blk_mq_rq_to_pdu(req);
 9      int reason;
10
11      // 1. 检查设备状态，如果设备离线、被阻塞或处于恢复中，直接拒绝或重试
12      if (unlikely(sdev->sdev_state != SDEV_RUNNING)) {
13          ret = scsi_device_state_check(sdev, req);
14          if (ret != BLK_STS_OK)
15              goto out_put_budget;
16      }
17
18      ret = BLK_STS_RESOURCE;
19      // 2. 检查Target和Host的并发限制，防止压垮后端存储
20      if (!scsi_target_queue_ready(shost, sdev))
21          goto out_put_budget;
22      if (!scsi_host_queue_ready(q, shost, sdev, cmd))
23          goto out_dec_target_busy;
24
25      // 3. 初始化scsi_cmnd，分配SG 表，调用较高层 ULD(如sd.c的init_command)构建CDB
26      if (!(req->rq_flags & RQF_DONTPREP)) {
27          ret = scsi_prepare_cmd(req);
28          if (ret != BLK_STS_OK)
29              goto out_dec_host_busy;
30          req->rq_flags |= RQF_DONTPREP;
31      } else {
32          clear_bit(SCMD_STATE_COMPLETE, &cmd->state);
33      }
34
35      // 4. 标记命令开始执行，并分发给底层驱动
36      blk_mq_start_request(req);
37      reason = scsi_dispatch_cmd(cmd); // 调用底层驱动的queuecommand
38
39      // 5. 如果底层驱动拒绝，如队列满，则设置阻塞状态并让块层重试
40      if (reason) {
41          scsi_set_blocked(cmd, reason);
42          ret = BLK_STS_RESOURCE;
43          goto out_dec_host_busy;
44      }
45
46      return BLK_STS_OK;
47
48      // 错误处理标签...
49  }
```

其中scsi_dispatch_cmd负责将打包好的命令交给底层硬件驱动。

scsi_dispatch_cmd函数(位于内核源码/drivers/scsi/scsi_lib.c)[¶](#id71 "永久链接至代码")

```c
 1  // 以下函数省略源码部分内容
 2
 3  static int scsi_dispatch_cmd(struct scsi_cmnd *cmd)
 4  {
 5      struct Scsi_Host *host = cmd->device->host;
 6
 7      // 检查设备是否已被删除
 8      if (unlikely(cmd->device->sdev_state == SDEV_DEL)) {
 9          cmd->result = DID_NO_CONNECT << 16;
10          goto done;
11      }
12
13      // ...
14
15      // 检查CDB长度是否超出主机控制器的限制
16      if (cmd->cmd_len > cmd->device->host->max_cmd_len) {
17          SCSI_LOG_MLQUEUE(3, scmd_printk(KERN_INFO, cmd,
18                  "queuecommand : command too long. "
19                  "cdb_size=%d host->max_cmd_len=%d\n",
20                  cmd->cmd_len, cmd->device->host->max_cmd_len));
21          cmd->result = (DID_ABORT << 16);
22          goto done;
23      }
24
25      // ...
26
27      // 调用底层驱动(LLD)注册的queuecommand回调
28      rtn = host->hostt->queuecommand(host, cmd);
29
30      // 如果LLD返回BUSY，中间层会将其放入重试队列
31      if (rtn) {
32          atomic_dec(&cmd->device->iorequest_cnt);
33          trace_scsi_dispatch_cmd_error(cmd, rtn);
34          if (rtn != SCSI_MLQUEUE_DEVICE_BUSY &&
35              rtn != SCSI_MLQUEUE_TARGET_BUSY)
36              rtn = SCSI_MLQUEUE_HOST_BUSY;
37
38          SCSI_LOG_MLQUEUE(3, scmd_printk(KERN_INFO, cmd,
39              "queuecommand : request rejected\n"));
40      }
41      return rtn;
42  done:
43      scsi_done(cmd); // 直接完成并报错
44      return 0;
45  }
```

**块层完成回调**

当底层驱动(LLD)完成命令并调用scsi_done后，流程回到scsi_lib.c，这里需要解析硬件返回的状态，决定是成功、重试还是报错。

scsi_complete函数(位于内核源码/drivers/scsi/scsi_lib.c)[¶](#id72 "永久链接至代码")

```c
 1  // 以下函数省略源码部分内容
 2
 3  static void scsi_complete(struct request *rq)
 4  {
 5      struct scsi_cmnd *cmd = blk_mq_rq_to_pdu(rq);
 6      enum scsi_disposition disposition;
 7
 8      // ...
 9
10      // 1. 决定命令的最终处置方式 (SUCCESS, NEEDS_RETRY, ADD_TO_MLQUEUE, 或进 EH)
11      disposition = scsi_decide_disposition(cmd);
12
13      // 2. 根据处置方式分流
14      switch (disposition) {
15      case SUCCESS:
16          scsi_finish_command(cmd); // 成功：交还给较高层ULD (如sd.c的sd_done)
17          break;
18      case NEEDS_RETRY:
19          scsi_queue_insert(cmd, SCSI_MLQUEUE_EH_RETRY);    // 需要重试：重新入队
20          break;
21      case ADD_TO_MLQUEUE:
22          scsi_queue_insert(cmd, SCSI_MLQUEUE_DEVICE_BUSY); // 设备忙：延迟重试
23          break;
24      default:
25          scsi_eh_scmd_add(cmd); // 严重错误：交给SCSI错误恢复(EH)线程
26          break;
27      }
28  }
```

**I/O完成与Sense数据解析**

如果命令返回了错误，中间层需要解析Sense Data（感知数据）来决定下一步动作，降级处理、延迟重试和错误隔离等。

scsi_io_completion_action函数(位于内核源码/drivers/scsi/scsi_lib.c)[¶](#id73 "永久链接至代码")

```c
 1  // 以下函数省略源码部分内容
 2
 3  static void scsi_io_completion_action(struct scsi_cmnd *cmd, int result)
 4  {
 5      struct request *req = scsi_cmd_to_rq(cmd);
 6      int level = 0;
 7      enum {ACTION_FAIL, ACTION_REPREP, ACTION_DELAYED_REPREP,
 8          ACTION_RETRY, ACTION_DELAYED_RETRY} action;
 9      struct scsi_sense_hdr sshdr;
10      bool sense_valid;
11      bool sense_current = true;
12      blk_status_t blk_stat;
13
14      sense_valid = scsi_command_normalize_sense(cmd, &sshdr);
15      if (sense_valid)
16          sense_current = !scsi_sense_is_deferred(&sshdr);
17
18      blk_stat = scsi_result_to_blk_status(result);
19
20      if (host_byte(result) == DID_RESET) {
21          action = ACTION_RETRY;
22      } else if (sense_valid && sense_current) {
23          // 根据sense_key决定动作
24          switch (sshdr.sense_key) {
25          case UNIT_ATTENTION:
26              // 设备状态改变：如换盘、总线重置，通常直接重试
27              if (cmd->device->removable) {
28                  cmd->device->changed = 1;
29                  action = ACTION_FAIL;
30              } else {
31                  action = ACTION_RETRY;
32              }
33          case ILLEGAL_REQUEST:
34
35              // ...
36
37              // 非法请求：可能是发了设备不支持的命令，如用READ(10)访问只支持READ(6)的老设备
38              } else if (sshdr.asc == 0x20 | sshdr.asc == 0x24) {
39                  cmd->device->use_10_for_rw = 0; // 降级标记
40                  action = ACTION_REPREP;         // 重新构建CDB并重试
41              } else {
42                  action = ACTION_FAIL;
43              }
44              break;
45          case NOT_READY:
46              // 设备未就绪：如磁盘正在起转、格式化中
47              if (sshdr.asc == 0x04) {
48                  switch (sshdr.ascq) {
49                  case 0x01: /* becoming ready */
50                  case 0x04: /* format in progress */
51                  case 0x05: /* rebuild in progress */
52                  case 0x06: /* recalculation in progress */
53                  case 0x07: /* operation in progress */
54                  case 0x08: /* Long write in progress */
55                  case 0x09: /* self test in progress */
56                  case 0x11: /* notify (enable spinup) required */
57                  case 0x14: /* space allocation in progress */
58                  case 0x1a: /* start stop unit in progress */
59                  case 0x1b: /* sanitize in progress */
60                  case 0x1d: /* configuration in progress */
61                  case 0x24: /* depopulation in progress */
62                      action = ACTION_DELAYED_RETRY; // 延迟重试
63                      break;
64          // ... 其他 Sense Key 处理 ...
65          }
66      }
67
68      // 执行决定的动作：失败则截断I/O，重试则重新入队
69      switch (action) {
70      case ACTION_FAIL: scsi_end_request(req, blk_stat, ...); break;
71      case ACTION_REPREP: scsi_mq_requeue_cmd(cmd, 0); break;
72      case ACTION_RETRY: __scsi_queue_insert(cmd, SCSI_MLQUEUE_EH_RETRY, false); break;
73      }
74  }
```

**SG表与数据完整性管理**

SCSI命令的数据通常不是连续内存，scsi_lib.c负责为这些非连续内存构建Scatter-Gather列表，并处理端到端的数据保护。

scsi_alloc_sgtables函数(位于内核源码/drivers/scsi/scsi_lib.c)[¶](#id74 "永久链接至代码")

```c
 1  // 以下函数省略源码部分内容
 2
 3  blk_status_t scsi_alloc_sgtables(struct scsi_cmnd *cmd)
 4  {
 5      struct request *rq = scsi_cmd_to_rq(cmd);
 6      unsigned short nr_segs = blk_rq_nr_phys_segments(rq);
 7
 8      // 1. 分配数据SG表
 9      if (unlikely(sg_alloc_table_chained(&cmd->sdb.table, nr_segs,
10              cmd->sdb.table.sgl, SCSI_INLINE_SG_CNT)))
11          return BLK_STS_RESOURCE;
12
13      // 2. 将块层的bio映射到SG表中
14      count = __blk_rq_map_sg(rq->q, rq, cmd->sdb.table.sgl, &last_sg);
15
16      // 3. 处理DMA边界对齐和Drain缓冲
17      if (blk_rq_bytes(rq) & rq->q->dma_pad_mask) { ... }
18      if (need_drain) { ... }
19
20      // 4. 如果启用了数据完整性保护(DIF/DIX)，分配额外的保护信息SG表
21      if (blk_integrity_rq(rq)) {
22          struct scsi_data_buffer *prot_sdb = cmd->prot_sdb;
23          ivecs = blk_rq_count_integrity_sg(rq->q, rq->bio);
24          sg_alloc_table_chained(&prot_sdb->table, ivecs, ...);
25          count = blk_rq_map_integrity_sg(rq->q, rq->bio, prot_sdb->table.sgl);
26
27      }
28      return BLK_STS_OK;
29  }
```

**命令执行同步**

在设备探测（如sd_revalidate_disk）或错误恢复时，内核需要同步发送SCSI命令并等待结果，scsi_lib.c提供了支持。

__scsi_execute函数(位于内核源码/drivers/scsi/scsi_lib.c)[¶](#id75 "永久链接至代码")

```c
 1  // 以下函数省略源码部分内容
 2
 3  int __scsi_execute(struct scsi_device *sdev, const unsigned char *cmd,
 4          int data_direction, void *buffer, unsigned bufflen,
 5          unsigned char *sense, struct scsi_sense_hdr *sshdr,
 6          int timeout, int retries, blk_opf_t flags,
 7          req_flags_t rq_flags, int *resid)
 8  {
 9      struct request *req;
10      struct scsi_cmnd *scmd;
11
12      // 1. 分配一个特殊的内部Request
13      req = scsi_alloc_request(sdev->request_queue, ...);
14
15      // 2. 将内核缓冲区映射到Request
16      if (bufflen) {
17          ret = blk_rq_map_kern(sdev->request_queue, req, buffer, bufflen, GFP_NOIO);
18      }
19
20      // 3. 填充CDB和超时/重试参数
21      scmd = blk_mq_rq_to_pdu(req);
22      scmd->cmd_len = COMMAND_SIZE(cmd[0]);
23      memcpy(scmd->cmnd, cmd, scmd->cmd_len);
24      scmd->allowed = retries;
25      req->timeout = timeout;
26      req->cmd_flags |= flags;
27      req->rq_flags |= rq_flags | RQF_QUIET;
28
29      // 4. 同步阻塞执行，直到命令完成
30      blk_execute_rq(req, true);
31
32      // 5. 提取Sense数据和结果
33      if (sense && scmd->sense_len)
34          memcpy(sense, scmd->sense_buffer, SCSI_SENSE_BUFFERSIZE);
35      if (sshdr)
36          scsi_normalize_sense(scmd->sense_buffer, scmd->sense_len, sshdr);
37
38      ret = scmd->result;
39  out:
40      blk_mq_free_request(req);
41
42      return ret;
43  }
```

## 7.7. 虚拟SCSI主机驱动实验[¶](#id32 "永久链接至标题")

本实验驱动根据内核SCSI子系统框架设计，处于SCSI子系统的 **较低层** ，对上承接SCSI中间层协议调度、IO管理，对下模拟物理SCSI硬件设备行为。 本实验驱动默认创建16MB容量的虚拟SCSI磁盘，模拟SCSI设备枚举、命令交互、数据读写、异常处理， 支持SPC-4标准协议的SCSI命令，实现异步命令处理、Sense错误上报、EH错误恢复、IO数据统计等功能。

本章的示例代码目录为： **linux_driver/41_scsi_subsystem**

### 7.7.1. 驱动代码详解[¶](#id33 "永久链接至标题")

#### 7.7.1.1. 核心定义与数据结构[¶](#id34 "永久链接至标题")

完成驱动基础信息、虚拟磁盘硬件参数、标准SCSI协议命令码的宏封装，同时定义驱动核心私有数据结构体与工具宏。

核心定义与数据结构(位于linux_driver/41_scsi_subsystem/virtual_scsi_host.c)[¶](#id76 "永久链接至代码")

```c
 1  /* 虚拟磁盘配置 */
 2  #define VIRTUAL_DISK_SIZE_MB 16    /* 虚拟磁盘大小（MB） */
 3  #define VIRTUAL_SECTOR_SIZE 512    /* 扇区大小（字节） */
 4  #define VIRTUAL_DISK_SECTORS ((VIRTUAL_DISK_SIZE_MB * 1024 * 1024) / VIRTUAL_SECTOR_SIZE) /* 总扇区数 */
 5
 6  /* 虚拟主机私有数据结构体 */
 7  struct vhost_data {
 8      unsigned char *disk_buffer;      /* 内存中的虚拟磁盘缓冲区 */
 9      spinlock_t lock;                 /* 磁盘访问自旋锁 */
10      unsigned int sectors_read;       /* 统计：已读取扇区数 */
11      unsigned int sectors_written;    /* 统计：已写入扇区数 */
12      struct workqueue_struct *wq;     /* 异步命令处理工作队列 */
13  };
14
15  /* 异步命令处理工作项结构体 */
16  struct vhost_work {
17      struct work_struct work;         /* 工作结构体 */
18      struct scsi_cmnd *cmd;           /* 关联的SCSI命令 */
19  };
20
21  /* 从scsi_host获取vhost_data的宏 */
22  #define host_to_vhost(host) ((struct vhost_data *)shost_priv(host))
23
24  /* 支持的SCSI命令操作码 */
25  #define OPCODE_TEST_UNIT_READY   0x00 /* 设备就绪检测(6字节) */
26  #define OPCODE_INQUIRY           0x12 /* 查询设备信息(6字节) */
27  #define OPCODE_MODE_SENSE_6      0x1A /* 模式读取(6字节) */
28  #define OPCODE_MODE_SENSE_10     0x5A /* 模式读取(10字节) */
29  #define OPCODE_MODE_SELECT_6     0x15 /* 模式配置(6字节) */
30  #define OPCODE_MODE_SELECT_10    0x55 /* 模式配置(10字节) */
31  #define OPCODE_READ_CAPACITY_10  0x25 /* 容量查询(10字节) */
32  #define OPCODE_READ_CAPACITY_16  0x9E /* 容量查询(16字节) */
33  #define OPCODE_READ_6            0x08 /* 读命令(6字节) */
34  #define OPCODE_READ_10           0x28 /* 读命令(10字节) */
35  #define OPCODE_WRITE_6           0x0A /* 写命令(6字节) */
36  #define OPCODE_WRITE_10          0x2A /* 写命令(10字节) */
37  #define OPCODE_VERIFY_10         0x2F /* 数据校验(10字节) */
38  #define OPCODE_SYNCHRONIZE_CACHE 0x35 /* 缓存同步(10字节) */
```

关键说明：

- 第2-4行：宏定义虚拟磁盘容量、扇区大小，计算得总扇区数。
    
- 第7-13行：vhost_data私有结构体，包含虚拟磁盘内存缓冲区、并发保护锁、IO统计、异步工作队列，是虚拟磁盘硬件的载体。
    
- 第16-19行：vhost_work结构体，适配内核工作队列机制，用于封装SCSI命令与异步工作项，实现底层非阻塞IO处理。
    
- 第22行：自定义工具宏，快速从SCSI主机结构体获取底层私有数据。
    
- 第25-38行：参照SPC-4协议标准，定义主流SCSI命令操作码，规范驱动可响应的协议指令。
    

#### 7.7.1.2. 内核版本兼容[¶](#id35 "永久链接至标题")

由于Linux内核5.15版本前后SCSI命令完成回调接口发生架构变更，底层驱动直接编译会出现接口报错，该函数通过内核版本宏判断，适配新旧内核接口。

vhost_scsi_done函数(位于linux_driver/41_scsi_subsystem/virtual_scsi_host.c)[¶](#id77 "永久链接至代码")

```c
static inline void vhost_scsi_done(struct scsi_cmnd *cmd)
{
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 15, 136)
    scsi_done(cmd);
#else
    cmd->scsi_done(cmd);
#endif
}
```

#### 7.7.1.3. SCSI主机模板配置[¶](#id36 "永久链接至标题")

定义SCSI主机模板结构体，模板集中定义虚拟SCSI主机的硬件参数、并发能力、底层回调函数入口，内核通过该模板识别设备属性、调度命令、触发异常处理。

SCSI主机模板配置(位于linux_driver/41_scsi_subsystem/virtual_scsi_host.c)[¶](#id78 "永久链接至代码")

```c
 1  /*
 2  * SCSI主机模板 - 定义主机适配器能力
 3  */
 4  static struct scsi_host_template vhost_template = {
 5      .name = DRV_NAME,                                     /* 主机名称 */
 6      .module = THIS_MODULE,                                /* 所属模块 */
 7      .queuecommand = vhost_queuecommand,                   /* 队列命令处理函数 */
 8      .eh_abort_handler = vhost_eh_abort_handler,           /* 中止处理函数 */
 9      .eh_host_reset_handler = vhost_eh_host_reset_handler, /* 主机重置处理函数 */
10
11      /* 主机能力 */
12      .can_queue = 16,          /* 最大可队列命令数 */
13      .this_id = 7,             /* 主机适配器的SCSI ID */
14      .cmd_per_lun = 1,         /* 每个LUN的命令数 */
15      .max_sectors = 256,       /* 每命令最大扇区数 */
16      .sg_tablesize = 64,       /* 最大scatter-gather元素数 */
17      .emulated = 1,            /* 这是一个模拟设备 */
18  };
```

关键说明：

- 第5-7行：绑定驱动名称、模块所有者、队列命令处理回调。
    
- 第8-9行：绑定EH异常处理回调，注册底层故障恢复接口。
    
- 第12-14行：配置主机并发能力，定义最大队列命令数、单LUN并行命令数。
    
- 第15-16行：限制单命令最大传输扇区、SG散列段数。
    
- 第17行：标记为模拟设备，告知内核该设备为软件虚拟硬件。
    

#### 7.7.1.4. 模块初始化与卸载[¶](#id37 "永久链接至标题")

模块初始化依次完成主机资源分配、私有数据初始化、虚拟磁盘内存创建、工作队列初始化、设备注册与扫描枚举。 模块卸载依次完成设备注销、资源回收、状态打印等收尾工作。

模块初始化与卸载函数(位于linux_driver/41_scsi_subsystem/virtual_scsi_host.c)[¶](#id79 "永久链接至代码")

```c
  1  /* 模块初始化函数 */
  2  static int __init virtual_scsi_host_init(void)
  3  {
  4      struct Scsi_Host *host;   /* SCSI主机指针 */
  5      struct vhost_data *vhost; /* 虚拟主机私有数据指针 */
  6      int ret = 0; /* 返回值 */
  7
  8      pr_info("%s: Virtual SCSI Host Driver v%s initializing...\n", DRV_NAME, DRV_VERSION);
  9
 10      /* 分配SCSI主机，附带私有数据空间 */
 11      host = scsi_host_alloc(&vhost_template, sizeof(struct vhost_data));
 12      if (!host) {
 13          pr_err("%s: Failed to allocate SCSI host\n", DRV_NAME);
 14          return -ENOMEM; /* 返回内存不足错误 */
 15      }
 16
 17      /* 获取私有数据区域指针 */
 18      vhost = shost_priv(host);
 19
 20      /* 初始化自旋锁 */
 21      spin_lock_init(&vhost->lock);
 22
 23      /* 使用vzalloc分配虚拟磁盘缓冲区，用于大内存分配 */
 24      vhost->disk_buffer = vzalloc(VIRTUAL_DISK_SIZE_MB * 1024 * 1024);
 25      if (!vhost->disk_buffer) {
 26          pr_err("%s: Failed to allocate virtual disk buffer (%d MB)\n",
 27              DRV_NAME, VIRTUAL_DISK_SIZE_MB);
 28          ret = -ENOMEM;   /* 返回内存不足错误 */
 29          goto free_host;  /* 跳转到清理 */
 30      }
 31
 32      /* 向虚拟磁盘写入一些初始数据 */
 33      {
 34          unsigned int i;
 35          for (i = 0; i < VIRTUAL_DISK_SECTORS; i++) {
 36              unsigned char *sector = vhost->disk_buffer + i * VIRTUAL_SECTOR_SIZE; /* 扇区指针 */
 37              memset(sector, (i & 0xFF), VIRTUAL_SECTOR_SIZE); /* 用扇区号的低8位填充 */
 38          }
 39      }
 40
 41      pr_info("%s: Allocated virtual disk: %d MB (%u sectors, %d bytes/sector)\n",
 42              DRV_NAME, VIRTUAL_DISK_SIZE_MB, VIRTUAL_DISK_SECTORS, VIRTUAL_SECTOR_SIZE);
 43
 44      /* 创建工作队列用于异步命令处理 */
 45      vhost->wq = create_singlethread_workqueue(DRV_NAME);
 46      if (!vhost->wq) {
 47          pr_err("%s: Failed to create workqueue\n", DRV_NAME);
 48          ret = -ENOMEM;    /* 返回内存不足错误 */
 49          goto free_buffer; /* 跳转到清理 */
 50      }
 51
 52      /* 设置DMA掩码 */
 53      dma_set_mask(&host->shost_gendev, DMA_BIT_MASK(32));
 54
 55      /* 将主机添加到系统 */
 56      ret = scsi_add_host(host, NULL);
 57      if (ret) {
 58          pr_err("%s: Failed to add SCSI host (ret=%d)\n", DRV_NAME, ret);
 59          goto free_wq; /* 跳转到清理 */
 60      }
 61
 62      /* 扫描主机查找设备 */
 63      scsi_scan_host(host);
 64
 65      /* 保存指针用于清理 */
 66      g_host = host;
 67
 68      pr_info("%s: Virtual SCSI Host initialized successfully!\n", DRV_NAME);
 69      pr_info("%s: Statistics: sectors_read=%u, sectors_written=%u\n",
 70              DRV_NAME, vhost->sectors_read, vhost->sectors_written);
 71
 72      return 0;
 73
 74  free_wq:
 75      destroy_workqueue(vhost->wq); /* 销毁工作队列 */
 76  free_buffer:
 77      vfree(vhost->disk_buffer); /* 释放虚拟磁盘缓冲区 */
 78  free_host:
 79      scsi_host_put(host); /* 释放SCSI主机 */
 80      return ret;
 81  }
 82
 83  /* 模块卸载函数 */
 84  static void __exit virtual_scsi_host_exit(void)
 85  {
 86      struct Scsi_Host *host = g_host; /* 获取SCSI主机指针 */
 87      struct vhost_data *vhost; /* 虚拟主机数据指针 */
 88
 89      if (!host) {
 90          pr_err("%s: No SCSI host found\n", DRV_NAME);
 91          return; /* 无主机，直接返回 */
 92      }
 93
 94      vhost = shost_priv(host); /* 获取私有数据 */
 95
 96      pr_info("%s: Unloading Virtual SCSI Host Driver...\n", DRV_NAME);
 97
 98      pr_info("%s: Final statistics:\n", DRV_NAME);
 99      pr_info("%s:   Sectors read:    %u\n", DRV_NAME, vhost->sectors_read);
100      pr_info("%s:   Sectors written: %u\n", DRV_NAME, vhost->sectors_written);
101
102      /* 移除主机 */
103      scsi_remove_host(host);
104
105      /* 等待所有待处理命令完成 */
106      flush_workqueue(vhost->wq);
107
108      /* 销毁工作队列 */
109      destroy_workqueue(vhost->wq);
110
111      /* 释放虚拟磁盘缓冲区 */
112      vfree(vhost->disk_buffer);
113
114      /* 释放主机引用 */
115      scsi_host_put(host);
116
117      /* 清空全局指针 */
118      g_host = NULL;
119
120      pr_info("%s: Virtual SCSI Host Driver unloaded successfully!\n", DRV_NAME);
121  }
122
123  module_init(virtual_scsi_host_init);
124  module_exit(virtual_scsi_host_exit);
```

关键说明：

- 第11-15行：分配SCSI主机结构体与底层私有数据空间，完成设备载体创建。
    
- 第21行：初始化自旋锁，为底层并发IO操作提供保护。
    
- 第24-30行：申请16MB内核内存，作为虚拟磁盘底层存储介质。
    
- 第33-39行：按扇区编号填充数据，初始化磁盘数据，方便读写功能测试校验。
    
- 第45-50行：创建内核工作队列，为异步命令处理提供任务调度载体。
    
- 第53行：配置32位DMA掩码，虚拟驱动不需要，但SCSI子系统要求。
    
- 第56-60行：向SCSI子系统注册主机设备，完成底层硬件接入内核。
    
- 第63行：扫描枚举虚拟LUN设备，触发内核设备枚举流程。
    
- 第74-80行：异常回退，初始化失败逐级释放底层资源。
    
- 第89-92行：校验主机设备有效性，规避空指针异常。
    
- 第96-100行：打印底层IO运行统计信息，展示设备运行状态。
    
- 第103行：移除SCSI主机设备，注销底层硬件设备节点。
    
- 第106行：刷新工作队列，等待所有底层异步IO任务执行完毕。
    
- 第109-112行：销毁工作队列、释放虚拟磁盘底层内存，回收所有内核资源。
    
- 第115行：释放主机引用计数，注销底层设备载体。
    
- 第118行：清空全局指针，避免野指针问题。
    

#### 7.7.1.5. 错误Sense数据生成[¶](#sense "永久链接至标题")

该部分实现SCSI标准Sense错误数据生成，当底层设备出现非法命令、LBA越界、参数错误等异常时，该函数按照SPC-4协议标准，生成内核可识别的标准化错误信息，上报给SCSI中间层。

set_sense_data函数(位于linux_driver/41_scsi_subsystem/virtual_scsi_host.c)[¶](#id80 "永久链接至代码")

```c
 1  /*
 2  * 为错误条件生成Sense数据
 3  * @param cmd: SCSI命令结构体
 4  * @param sense_key: 感知键
 5  * @param asc: 附加感知码
 6  * @param ascq: 附加感知码限定符
 7  */
 8  static void set_sense_data(struct scsi_cmnd *cmd, int sense_key, int asc, int ascq)
 9  {
10      unsigned char *sense = cmd->sense_buffer; /* 获取Sense缓冲区指针 */
11
12      memset(sense, 0, SCSI_SENSE_BUFFERSIZE);  /* 清零Sense缓冲区 */
13
14      /* 固定格式Sense数据 (70h或71h) */
15      sense[0] = 0x70;      /* 固定格式，当前错误 */
16      sense[2] = sense_key; /* 设置感知键 */
17      sense[7] = 10;        /* 附加Sense长度 */
18      sense[12] = asc;      /* 设置附加感知码 */
19      sense[13] = ascq;     /* 设置附加感知码限定符 */
20  }
```

关键说明：

- 第10行：获取内核预置的SCSI命令Sense缓冲区，使用内核标准内存空间存储异常信息。
    
- 第12行：清零缓冲区，避免残留数据导致底层错误信息上报异常。
    
- 第15行：固定协议标识位，声明为标准SCSI当前错误格式，保证内核正常解析。
    
- 第16行：写入Sense错误大类，区分非法请求、设备未就绪等核心异常类型。
    
- 第17行：定义附加错误数据长度，遵循协议数据帧格式。
    
- 第18-19行：写入细分错误码与限定符，定位底层硬件的异常原因。
    

#### 7.7.1.6. 异步命令调度[¶](#id38 "永久链接至标题")

**命令队列处理函数**

vhost_queuecommand函数是SCSI子系统中间层与底层驱动的唯一交互入口，内核所有下发的SCSI命令都会优先进入该函数。 函数功能为接收原始命令、创建异步工作项、绑定命令上下文、推入内核工作队列，将同步上下文的命令请求转换为异步任务。

vhost_queuecommand函数(位于linux_driver/41_scsi_subsystem/virtual_scsi_host.c)[¶](#id81 "永久链接至代码")

```c
 1  /*
 2  * 队列命令处理函数 - 所有SCSI命令在这里接收
 3  * @param host: SCSI主机
 4  * @param cmd: SCSI命令
 5  * @return: 返回0表示成功
 6  */
 7  static int vhost_queuecommand(struct Scsi_Host *host, struct scsi_cmnd *cmd)
 8  {
 9      struct vhost_data *vhost = host_to_vhost(host); /* 获取虚拟主机数据 */
10      struct vhost_work *vwork; /* 工作项 */
11
12      dev_dbg(&host->shost_gendev, "Queued SCSI command: opcode 0x%02x, cmd_len=%d\n",
13              cmd->cmnd[0], cmd->cmd_len);
14
15      /* 为异步处理分配工作项 */
16      vwork = kmalloc(sizeof(struct vhost_work), GFP_ATOMIC);
17      if (!vwork) {
18          dev_err(&host->shost_gendev, "Failed to allocate work item\n");
19          cmd->result = DID_ERROR << 16; /* 设置错误结果 */
20          vhost_scsi_done(cmd); /* 完成命令 */
21          return -ENOMEM; /* 返回内存不足错误 */
22      }
23
24      /* 初始化工作结构体 */
25      vwork->cmd = cmd; /* 关联命令 */
26      INIT_WORK(&vwork->work, vhost_process_command); /* 初始化异步任务的执行回调函数 */
27
28      /* 将工作项加入工作队列 */
29      queue_work(vhost->wq, &vwork->work);
30
31      return 0; /* 返回成功 */
32  }
```

关键说明：

- 第9-13行：获取私有驱动数据与主机设备句柄，打印当前入队命令码与命令长度，用于底层调试。
    
- 第16-22行：以原子内存分配方式创建异步工作项，适配中断上下文运行环境。
    
- 第25-26行：将接收的SCSI命令结构体与工作项绑定，初始化工作队列回调函数，完成同步指令封装。
    
- 第29行：将封装完成的异步任务推入自定义工作队列，交由内核调度线程异步执行。
    

**命令异步分发处理**

vhost_process_command函数是异步任务的执行回调函数，工作队列调度触发该函数后，完成任务解析、设备合法性校验、命令码分发、异常错误封装、命令收尾与内存资源释放等工作。

vhost_process_command函数(位于linux_driver/41_scsi_subsystem/virtual_scsi_host.c)[¶](#id82 "永久链接至代码")

```c
 1  /*
 2  * 处理SCSI命令 - 从工作队列调用
 3  * @param work: 工作结构体指针
 4  */
 5  static void vhost_process_command(struct work_struct *work)
 6  {
 7      struct vhost_work *vwork = container_of(work, struct vhost_work, work); /* 获取工作项 */
 8      struct scsi_cmnd *cmd = vwork->cmd;  /* 获取SCSI命令 */
 9      struct Scsi_Host *host = cmd->device->host; /* 获取SCSI主机 */
10      unsigned char opcode = cmd->cmnd[0]; /* 获取命令操作码 */
11      int ret = 0; /* 返回值 */
12
13      /* 只处理目标ID为0和LUN为0的命令 */
14      if (cmd->device->id != 0 | cmd->device->lun != 0) {
15          set_sense_data(cmd, NO_SENSE, 0x00, 0x00); /* 设置无错误 */
16          cmd->result = (DID_NO_CONNECT << 16) | SAM_STAT_CHECK_CONDITION; /* 无连接 */
17          vhost_scsi_done(cmd); /* 完成命令 */
18          kfree(vwork); /* 释放工作项 */
19          return;
20      }
21
22      /* 根据操作码分发处理 */
23      switch (opcode) {
24      case OPCODE_TEST_UNIT_READY:       /* 0x00 - 设备就绪检测(6字节)：检查设备是否可访问 */
25          ret = do_test_unit_ready(cmd);
26          break;
27      case OPCODE_INQUIRY:               /* 0x12 - 查询设备信息(6字节)：返回厂商名、产品名等 */
28          ret = do_inquiry(cmd);
29          break;
30      case OPCODE_MODE_SENSE_6:          /* 0x1A - 模式读取(6字节)：返回设备模式页面（缓存、错误恢复等） */
31          ret = do_mode_sense_6(cmd);
32          break;
33      case OPCODE_MODE_SENSE_10:         /* 0x5A - 模式读取(10字节)：同上，支持更大的数据长度 */
34          ret = do_mode_sense_10(cmd);
35          break;
36      case OPCODE_MODE_SELECT_6:         /* 0x15 - 模式配置(6字节)：设置设备模式参数 */
37          ret = do_mode_select_6(cmd);
38          break;
39      case OPCODE_MODE_SELECT_10:        /* 0x55 - 模式配置(10字节)：同上，支持更大的数据长度 */
40          ret = do_mode_select_10(cmd);
41          break;
42      case OPCODE_READ_CAPACITY_10:      /* 0x25 - 读取容量(10字节)：返回最大LBA和扇区大小（32位） */
43          ret = do_read_capacity_10(cmd);
44          break;
45      case OPCODE_READ_CAPACITY_16:      /* 0x9E - 读取容量(16字节)：返回最大LBA和扇区大小（64位） */
46          ret = do_read_capacity_16(cmd);
47          break;
48      case OPCODE_READ_6:                /* 0x08 - 读命令(6字节)：从磁盘读取数据（LBA < 2^24） */
49      case OPCODE_READ_10:               /* 0x28 - 读命令(10字节)：从磁盘读取数据（LBA < 2^32） */
50          ret = do_read(cmd);
51          break;
52      case OPCODE_WRITE_6:               /* 0x0A - 写命令(6字节)：向磁盘写入数据（LBA < 2^24） */
53      case OPCODE_WRITE_10:              /* 0x2A - 写命令(10字节)：向磁盘写入数据（LBA < 2^32） */
54          ret = do_write(cmd);
55          break;
56      case OPCODE_VERIFY_10:             /* 0x2F - 数据校验(10字节)：验证指定扇区的数据完整性 */
57          ret = do_verify(cmd);
58          break;
59      case OPCODE_SYNCHRONIZE_CACHE:     /* 0x35 - 同步缓存(10字节)：将缓存数据刷新到磁盘 */
60          ret = do_synchronize_cache(cmd);
61          break;
62      default:                           /* 未知命令：返回非法请求错误 */
63          dev_dbg(&host->shost_gendev, "Unsupported SCSI command: 0x%02x\n", opcode);
64          set_sense_data(cmd, ILLEGAL_REQUEST, 0x20, 0x00); /* 无效命令操作码 */
65          cmd->result = (DID_OK << 16) | SAM_STAT_CHECK_CONDITION;
66          ret = 0;
67          break;
68      }
69
70      /* 异步完成命令 */
71      vhost_scsi_done(cmd);
72
73      /* 释放工作项 */
74      kfree(vwork);
75  }
```

关键说明：

- 第7-10行：通过工作结构体反向解析出绑定的SCSI命令与工作项，获取当前待处理指令信息。
    
- 第14-20行：校验设备LUN与设备编号，仅允许合法0号虚拟设备访问，拦截非法设备请求并上报标准SCSI异常信息。
    
- 第23-61行：通过Switch分支匹配所有支持的SCSI命令操作码，分流至对应的读写、查询、校验、模式配置处理函数，实现模块化命令处理。
    
- 第62-67行：捕获未知不支持的命令码，自动填充非法请求Sense错误，避免驱动崩溃。
    
- 第71行：调用统一版本兼容收尾接口，标记底层所有命令执行完毕，通知内核完成IO资源回收。
    
- 第71行：主动释放异步工作项堆内存，避免驱动内存泄漏。
    

#### 7.7.1.7. 基础设备状态查询[¶](#id39 "永久链接至标题")

该部分实现TEST_UNIT_READY设备就绪检测命令处理，通过该函数模拟硬件设备就绪状态，向上层中间层反馈设备可用性。

do_test_unit_ready函数(位于linux_driver/41_scsi_subsystem/virtual_scsi_host.c)[¶](#id83 "永久链接至代码")

```c
/*
* 执行SCSI TEST UNIT READY命令
* @param cmd: SCSI命令结构体
* @return: 返回处理状态
*/
static int do_test_unit_ready(struct scsi_cmnd *cmd)
{
    /* 虚拟磁盘总是就绪的 */
    cmd->result = DID_OK << 16; /* 设置命令结果为成功 */
    return 0;
}
```

关键说明：

- 第9行：固定赋值SCSI标准成功状态码DID_OK，标识底层设备传输无异常、设备就绪。
    

#### 7.7.1.8. 设备信息查询[¶](#id40 "永久链接至标题")

该部分实现INQUIRY查询命令处理，通过该函数向内核上报虚拟SCSI设备的厂商信息、产品型号、协议版本、固件版本等硬件身份信息，让Linux内核识别当前设备类型、完成驱动匹配与设备注册。

do_inquiry函数(位于linux_driver/41_scsi_subsystem/virtual_scsi_host.c)[¶](#id84 "永久链接至代码")

```c
 1  /*
 2  * INQUIRY命令响应数据 (SPC-4标准)
 3  * 总长度36字节，其中前4字节为标准头部，后接31字节厂商/产品信息
 4  */
 5  static unsigned char inquiry_data[] = {
 6      /* 标准INQUIRY头部 (字节0~7) */
 7      0x00,       /* 外设限定符(bit 7-5)=0 设备存在, 设备类型(bit 4-0)=0 直接访问块设备，即磁盘 */
 8      0x00,       /* RMB(bit 7)=0 介质不可移除，其余位保留 */
 9      0x06,       /* 版本: 0x06 表示SPC-4 (ANSI版本) */
10      0x02,       /* 响应数据格式: 0x02 标准格式，附加数据从字节4开始 */
11      0x1F,       /* 附加长度 = 31 (0x1F) 表示后续31字节有效，总长度=4+1+31=36 */
12      0x00, 0x00, 0x00,   /* 保留字节，填0 */
13
14      /* 厂商名："LubanCat" (8字节) */
15      0x4C, 0x75, 0x62, 0x61,   /* L u b a */
16      0x6E, 0x43, 0x61, 0x74,   /* n C a t */
17
18      /* 产品ID："VIRTUAL DISK" (16字节) */
19      0x56, 0x49, 0x52, 0x54,   /* V I R T */
20      0x55, 0x41, 0x4C, 0x20,   /* U A L (空格) */
21      0x44, 0x49, 0x53, 0x4B,   /* D I S K */
22      0x20, 0x20, 0x20, 0x20,   /* 补空格至16字节 */
23
24      /* 产品修订级别："1.0 " (4字节) */
25      0x31, 0x2E, 0x30, 0x20,   /* 1 . 0 (空格) */
26  };
27
28  /*
29  * 执行SCSI INQUIRY命令
30  * @param cmd: SCSI命令结构体
31  * @return: 返回实际传输的数据长度
32  */
33  static int do_inquiry(struct scsi_cmnd *cmd)
34  {
35      unsigned char *cdb = cmd->cmnd;                /* 获取命令描述块指针 */
36      u32 alloc_len = get_unaligned_be16(cdb + 3);   /* 主机请求的分配长度 (CDB[3:4]大端序) */
37      u32 data_len = sizeof(inquiry_data);           /* 本地INQUIRY数据总长度 (u32避免min类型警告) */
38      u32 copy_len = min(alloc_len, data_len);       /* 实际复制长度为请求长度与本地数据的最小值 */
39
40      /* 设置数据传输方向: 数据从设备流向主机 */
41      cmd->sc_data_direction = DMA_FROM_DEVICE;
42
43      /* 将INQUIRY数据复制到sg列表，只复制允许的字节数 */
44      scsi_sg_copy_from_buffer(cmd, inquiry_data, copy_len);
45
46      /* 设置剩余未传输字节数：请求长度 - 实际传输长度 */
47      scsi_set_resid(cmd, alloc_len - copy_len);
48
49      cmd->result = DID_OK << 16;     /* 命令成功完成 */
50      return copy_len;                /* 返回实际传输字节数 */
51  }
```

关键说明：

- 第1行：设置附加长度为31（0x1F），确保INQUIRY总长度为36字节。
    
- 第36行：从命令描述块的第3-4字节以大端序提取主机请求的分配长度。
    
- 第38行：使用min将实际传输长度限制为主机请求长度与本地数据总长的较小值。
    
- 第41行：指定数据传输方向为从设备到主机，与INQUIRY命令的“读取”性质一致。
    
- 第44行：通过内核标准接口将inquiry_data中copy_len字节的数据拷贝至SCSI中间层分配的scatter-gather缓冲区，完成数据向上层上报。
    
- 第47行：正确设置残留长度，向内核报告“请求了alloc_len字节，实际仅传输copy_len字节”。
    
- 第49行：标记命令成功完成，状态码置于SCSI结果的host byte字段，通知内核此INQUIRY无异常。
    
- 第50行：返回实际传输字节数，上层可据此校验或做后续处理。
    

#### 7.7.1.9. 设备容量查询[¶](#id41 "永久链接至标题")

该部分实现READ_CAPACITY 10字节/16字节容量查询命令处理，负责向上层内核上报虚拟磁盘的最大有效LBA地址与单扇区大小，是系统识别磁盘容量、完成分区与IO寻址的依据。

do_read_capacity函数(位于linux_driver/41_scsi_subsystem/virtual_scsi_host.c)[¶](#id85 "永久链接至代码")

```c
 1  /*
 2  * 执行SCSI READ CAPACITY(10)命令
 3  * @param cmd: SCSI命令结构体
 4  * @return: 返回响应数据长度
 5  */
 6  static int do_read_capacity_10(struct scsi_cmnd *cmd)
 7  {
 8      u32 last_lba = VIRTUAL_DISK_SECTORS - 1;  /* 最后一个逻辑块地址（32位） */
 9      u32 sector_size = VIRTUAL_SECTOR_SIZE;    /* 扇区大小 */
10      unsigned char buf[8]; /* 8字节响应缓冲区 */
11
12      /* READ CAPACITY(10)响应格式 - 大端序 */
13      buf[0] = (last_lba >> 24) & 0xFF; /* LBA高字节 */
14      buf[1] = (last_lba >> 16) & 0xFF;
15      buf[2] = (last_lba >> 8) & 0xFF;
16      buf[3] = last_lba & 0xFF;         /* LBA低字节 */
17
18      buf[4] = (sector_size >> 24) & 0xFF; /* 扇区大小高字节 */
19      buf[5] = (sector_size >> 16) & 0xFF;
20      buf[6] = (sector_size >> 8) & 0xFF;
21      buf[7] = sector_size & 0xFF;         /* 扇区大小低字节 */
22
23      cmd->sc_data_direction = DMA_FROM_DEVICE; /* 设置数据传输方向 */
24
25      /* 将数据复制到scatter-gather列表（DMA_FROM_DEVICE: 从buf到sg） */
26      scsi_sg_copy_from_buffer(cmd, buf, 8);
27
28      cmd->result = DID_OK << 16; /* 设置命令结果为成功 */
29      scsi_set_resid(cmd, 0); /* 没有剩余数据 */
30
31      return 8; /* 返回8字节 */
32  }
33
34  /*
35  * 执行SCSI READ CAPACITY(16)命令
36  * @param cmd: SCSI命令结构体
37  * @return: 返回响应数据长度
38  */
39  static int do_read_capacity_16(struct scsi_cmnd *cmd)
40  {
41      u64 last_lba = VIRTUAL_DISK_SECTORS - 1;  /* 最后一个逻辑块地址（64位） */
42      u32 sector_size = VIRTUAL_SECTOR_SIZE;    /* 扇区大小 */
43      unsigned char buf[32]; /* 32字节响应缓冲区 */
44
45      memset(buf, 0, 32); /* 清零缓冲区 */
46
47      /* READ CAPACITY(16)响应格式 - 大端序 */
48      /* 字节0-7: 最后一个可访问块的逻辑块地址 */
49      buf[0] = (last_lba >> 56) & 0xFF; /* LBA最高字节 */
50      buf[1] = (last_lba >> 48) & 0xFF;
51      buf[2] = (last_lba >> 40) & 0xFF;
52      buf[3] = (last_lba >> 32) & 0xFF;
53      buf[4] = (last_lba >> 24) & 0xFF;
54      buf[5] = (last_lba >> 16) & 0xFF;
55      buf[6] = (last_lba >> 8) & 0xFF;
56      buf[7] = last_lba & 0xFF;         /* LBA最低字节 */
57
58      /* 字节8-11: 逻辑块长度（字节） */
59      buf[8] = (sector_size >> 24) & 0xFF;
60      buf[9] = (sector_size >> 16) & 0xFF;
61      buf[10] = (sector_size >> 8) & 0xFF;
62      buf[11] = sector_size & 0xFF;
63
64      cmd->sc_data_direction = DMA_FROM_DEVICE; /* 设置数据传输方向 */
65
66      /* 将数据复制到scatter-gather列表（DMA_FROM_DEVICE: 从buf到sg） */
67      scsi_sg_copy_from_buffer(cmd, buf, 32);
68
69      cmd->result = DID_OK << 16; /* 设置命令结果为成功 */
70      scsi_set_resid(cmd, 0); /* 没有剩余数据 */
71
72      return 32; /* 返回32字节 */
73  }
```

关键说明：

- 第8-9行（10字节函数）：基于全局宏参数计算出磁盘最后一个有效扇区编号，作为磁盘最大寻址边界。
    
- 第10行：按照SPC-4协议标准，READ_CAPACITY_10指令固定返回8字节应答数据，因此定义长度为8的字符数组作为协议帧缓冲区。
    
- 第13-16行：SCSI协议与Linux内核设备交互使用网络大端序（大字节优先、高地址存低字节），而x86、ARM等主流CPU为小端序，对32位最大LBA地址进行逐字节移位拆分，将高位数据存入低地址、低位数据存入高地址，完成主机字节序向网络字节序的转换。
    
- 第18-21行：对512字节标准扇区大小进行四字节大端序封装，遵循READ_CAPACITY_10协议帧第4~7字节存储扇区尺寸的要求。
    
- 第23行：配置数据传输方向，明确本次交互为设备向内核主机上报数据。
    
- 第26行：调用内核标准接口，将封装完成的8字节标准容量协议帧，拷贝至SCSI命令SG散列缓冲区。
    
- 第28行：赋值DID_OK成功状态码，标记当前命令执行无误。
    
- 第29行：调用scsi_set_resid设置剩余数据为0，告知内核本次应答数据完整。
    
- 第31行：返回8字节固定协议长度，匹配READ_CAPACITY_10指令标准应答帧大小。
    
- 第41-42行（16字节函数）：采用u64 64位无符号长整型存储最大LBA地址。
    
- 第43-45行：按照SPC-4协议标准，READ_CAPACITY_16指令固定返回32字节应答数据，因此定义长度为32的字符数组作为协议帧缓冲区，并且清零缓冲区。
    
- 第49-56行：对64位超长LBA地址进行8字节逐位拆分填充，覆盖32位高位寻址空间。
    
- 第59-62行：在扩展协议指定偏移位置封装扇区大小参数，兼容新型大容量磁盘的拓展属性预留字段。
    
- 第64-72行：进行设备读数据方向配置、SG散列拷贝、成功状态赋值、剩余数据清零，与10字节函数处理方式一致。
    

#### 7.7.1.10. 设备模式配置与读取[¶](#id42 "永久链接至标题")

该部分实现MODE_SENSE模式读取、MODE_SELECT模式配置命令的处理，用于读取设备的缓存参数、错误恢复策略、硬件配置信息，支持系统对设备参数进行配置。

**6字节的MODE_SENSE/MODE_SELECT**

do_mode_sense_6和do_mode_select_6函数(位于linux_driver/41_scsi_subsystem/virtual_scsi_host.c)[¶](#id86 "永久链接至代码")

```c
  1  /*
  2  * 执行SCSI MODE SENSE(6)命令
  3  * 返回模式页面数据，包括缓存信息
  4  * @param cmd: SCSI命令结构体
  5  * @return: 返回响应数据长度
  6  */
  7  static int do_mode_sense_6(struct scsi_cmnd *cmd)
  8  {
  9      unsigned char *cdb = cmd->cmnd;  /* 获取命令描述块指针 */
 10      u32 alloc_len = cdb[4];          /* MODE SENSE(6)的alloc_len在cdb[4] */
 11      int dbd = (cdb[1] & 0x08) != 0;  /* DBD位：禁止块描述符 */
 12      int pcode = cdb[2] & 0x3F;       /* 页面代码 */
 13      int pcontrol = (cdb[2] >> 6) & 0x03;  /* 页面控制字段 */
 14      unsigned char buf[64]; /* 64字节响应缓冲区 */
 15      int offset = 0; /* 当前写入位置偏移 */
 16      int len; /* 实际响应长度 */
 17
 18      memset(buf, 0, 64); /* 清零缓冲区 */
 19
 20      /* 页面控制：0=当前值, 1=可更改值, 2=默认值, 3=保存值(不支持) */
 21      if (pcontrol == 3) {
 22          set_sense_data(cmd, ILLEGAL_REQUEST, 0x20, 0x00);
 23          cmd->result = (DID_OK << 16) | SAM_STAT_CHECK_CONDITION;
 24          return 0;
 25      }
 26
 27      /* MODE SENSE(6)响应头 */
 28      buf[0] = 0;                      /* 模式数据长度（后面设置） */
 29      buf[1] = 0;                      /* 介质类型（0=无介质） */
 30      buf[2] = 0x10;                   /* 设备特定：DPOFUA=1 */
 31      buf[3] = dbd ? 0 : 8;            /* 块描述符长度 */
 32      offset = 4; /* 头4字节已填充 */
 33
 34      /* 块描述符（8字节） */
 35      if (!dbd) {
 36          /* 块数量（大端序） */
 37          buf[offset++] = (VIRTUAL_DISK_SECTORS >> 24) & 0xFF;
 38          buf[offset++] = (VIRTUAL_DISK_SECTORS >> 16) & 0xFF;
 39          buf[offset++] = (VIRTUAL_DISK_SECTORS >> 8) & 0xFF;
 40          buf[offset++] = VIRTUAL_DISK_SECTORS & 0xFF;
 41          /* 保留 */
 42          buf[offset++] = 0;
 43          buf[offset++] = 0;
 44          /* 块长度（大端序） */
 45          buf[offset++] = (VIRTUAL_SECTOR_SIZE >> 8) & 0xFF;
 46          buf[offset++] = VIRTUAL_SECTOR_SIZE & 0xFF;
 47      }
 48
 49      /* 处理特定页面代码 */
 50      switch (pcode) {
 51      case 0x00:  /* 所有页面 */
 52      case 0x08:  /* 缓存页面 */
 53          /* 缓存页面：页面代码=0x08, 页面长度=0x12(18字节) */
 54          buf[offset++] = 0x08;  /* 页面代码 */
 55          buf[offset++] = 0x12;  /* 页面长度(18) */
 56          buf[offset++] = 0x14;  /* 缓存控制：WCE=1, RCD=1 */
 57          buf[offset++] = 0x00;  /* 缓存大小(MSB) - 未使用 */
 58          buf[offset++] = 0xff;  /* 缓存大小 */
 59          buf[offset++] = 0xff;  /* 缓存大小 */
 60          buf[offset++] = 0x00;  /* 缓存大小(LSB) */
 61          buf[offset++] = 0x00;  /* 阈值 */
 62          buf[offset++] = 0xff;  /* 预取大小 */
 63          buf[offset++] = 0xff;  /* 预取大小 */
 64          buf[offset++] = 0xff;  /* 预取上限 */
 65          buf[offset++] = 0xff;  /* 预取上限 */
 66          buf[offset++] = 0x80;  /* 缓存禁用(CD)=0, FUA=1 */
 67          buf[offset++] = 0x14;  /* 缓存控制(与字节2相同) */
 68          buf[offset++] = 0x00;  /* 保留 */
 69          buf[offset++] = 0x00;  /* 保留 */
 70          buf[offset++] = 0x00;  /* 保留 */
 71          buf[offset++] = 0x00;  /* 保留 */
 72          buf[offset++] = 0x00;  /* 保留 */
 73          break;
 74      case 0x01:  /* 读写错误恢复页面 */
 75          /* 简单的错误恢复页面 */
 76          buf[offset++] = 0x01;  /* 页面代码 */
 77          buf[offset++] = 0x0a;  /* 页面长度(10) */
 78          buf[offset++] = 0x00;  /* 错误恢复控制 */
 79          buf[offset++] = 0x00;  /* 读重试次数 */
 80          buf[offset++] = 0x00;  /* 校正跨度 */
 81          buf[offset++] = 0x00;  /* 磁头偏移次数 */
 82          buf[offset++] = 0x00;  /* 数据选通偏移次数 */
 83          buf[offset++] = 0x00;  /* 写重试次数 */
 84          buf[offset++] = 0x00;  /* 恢复时间限制 */
 85          buf[offset++] = 0x00;  /* 恢复时间限制 */
 86          buf[offset++] = 0x00;  /* 保留 */
 87          break;
 88      default:
 89          /* 未知页面 - 只返回头 */
 90          break;
 91      }
 92
 93      /* 设置总长度 */
 94      len = min(offset, (int)alloc_len);
 95      buf[0] = len - 1;  /* 模式数据长度 = 总长度 - 1 */
 96
 97      cmd->sc_data_direction = DMA_FROM_DEVICE; /* 设置数据传输方向 */
 98      scsi_sg_copy_from_buffer(cmd, buf, len);  /* 将数据复制到sg列表 */
 99      cmd->result = DID_OK << 16;               /* 设置命令结果为成功 */
100      scsi_set_resid(cmd, alloc_len - len);     /* 设置剩余长度 */
101
102      return len; /* 返回实际传输长度 */
103  }
104
105  /*
106  * 执行SCSI MODE SELECT(6)命令
107  * @param cmd: SCSI命令结构体
108  * @return: 返回0表示成功
109  */
110  static int do_mode_select_6(struct scsi_cmnd *cmd)
111  {
112      unsigned char *cdb = cmd->cmnd; /* 获取命令描述块指针 */
113      u32 param_len = cdb[4]; /* MODE SELECT(6)的参数长度在cdb[4] */
114      unsigned char *buf; /* 临时缓冲区指针 */
115
116      /* 对于虚拟磁盘，接受但忽略模式选择 */
117      cmd->sc_data_direction = DMA_TO_DEVICE; /* 设置数据传输方向 */
118
119      /* 读取并丢弃数据 */
120      buf = kmalloc(param_len, GFP_KERNEL); /* 分配临时缓冲区 */
121      if (buf) {
122          scsi_sg_copy_to_buffer(cmd, buf, param_len);     /* 从sg列表复制数据 */
123          kfree(buf); /* 释放临时缓冲区 */
124      }
125
126      cmd->result = DID_OK << 16; /* 设置命令结果为成功 */
127      scsi_set_resid(cmd, 0);     /* 没有剩余数据 */
128
129      return 0;
130  }
```

关键说明：

- 第9-16行：解析CDB，提取主机请求的分配长度(alloc_len)、禁止块描述符标志(dbd)、请求的页面代码(pcode)以及页面控制字段(pcontrol)。
    
- 第20-25行：进行协议合法性校验。若主机请求“保存值(3)”而虚拟磁盘不支持，则主动构造ILLEGAL_REQUEST的Sense数据，并返回CHECK_CONDITION状态拒绝该命令。
    
- 第28-32行：构造MODE SENSE(6)标准的4字节响应头，填充介质类型、设备特定参数以及后续块描述符的长度。
    
- 第35-47行：若主机未禁止块描述符，则继续填充8字节的块描述符，以大端序上报虚拟磁盘的总扇区数和单扇区字节数。
    
- 第50-91行：根据主机请求的页面代码(pcode)动态构造模式页面数据。支持返回缓存页面(0x08)和读写错误恢复页面(0x01)。
    
- 第94-95行：计算实际生成的响应长度，并将其截断至主机请求的alloc_len范围内，最后回填响应头第0字节的“模式数据长度”字段，协议规定为总长度减1。
    
- 第97-100行：设置DMA方向为设备到主机，调用SG拷贝接口将构造好的模式页数据上报给内核，设置成功状态并计算残余数据长度。
    
- 第112-113行：解析CDB，提取主机下发的模式参数数据总长度(param_len)。
    
- 第117行：指定数据传输方向为主机到设备。
    
- 第120-124行：分配临时内核缓冲区，调用SG拷贝接口将主机下发的模式参数数据读出并丢弃。虚拟磁盘无需真实修改硬件配置，但必须消耗掉主机发来的数据以完成协议规定的命令交互流程。
    
- 第126-127行：设置命令成功状态码(DID_OK)，并将残余数据长度(resid)置0，向内核表明主机下发的数据已被全部接收并处理完毕。
    

**10字节的MODE_SENSE/MODE_SELECT**

两者在实现逻辑上完全一致，区别仅在于协议格式上的扩展。以下黄色标注部分为和6字节差异部分。

do_mode_sense_10和do_mode_select_10函数(位于linux_driver/41_scsi_subsystem/virtual_scsi_host.c)[¶](#id87 "永久链接至代码")

```c
/*
* 执行SCSI MODE SENSE(10)命令
* 返回模式页面数据，包括缓存信息
* @param cmd: SCSI命令结构体
* @return: 返回响应数据长度
*/
static int do_mode_sense_10(struct scsi_cmnd *cmd)
{
    unsigned char *cdb = cmd->cmnd; /* 获取命令描述块指针 */
    u32 alloc_len = get_unaligned_be16(cdb + 7); /* alloc_len是cdb[7:8]的2字节大端序值 */
    int dbd = (cdb[1] & 0x08) != 0;  /* DBD位：禁止块描述符 */
    int pcode = cdb[2] & 0x3F;       /* 页面代码 */
    int pcontrol = (cdb[1] >> 6) & 0x03;  /* 页面控制字段 */
    unsigned char buf[64]; /* 64字节响应缓冲区 */
    int offset = 0; /* 当前写入位置偏移 */
    int len; /* 实际响应长度 */

    memset(buf, 0, 64); /* 清零缓冲区 */

    /* 页面控制：0=当前值, 1=可更改值, 2=默认值, 3=保存值(不支持) */
    if (pcontrol == 3) {
        set_sense_data(cmd, ILLEGAL_REQUEST, 0x20, 0x00);
        cmd->result = (DID_OK << 16) | SAM_STAT_CHECK_CONDITION;
        return 0;
    }

    /* MODE SENSE(10)响应头 */
    buf[0] = 0;                      /* 模式数据长度高字节 */
    buf[1] = 0;                      /* 模式数据长度低字节 */
    buf[2] = 0;                      /* 介质类型（0=无介质） */
    buf[3] = 0x10;                   /* 设备特定：DPOFUA=1 */
    buf[7] = dbd ? 0 : 8;            /* 块描述符长度 */
    offset = 8; /* 头8字节已填充 */
    /* 块描述符（8字节） */
    if (!dbd) {
        /* 块数量（大端序） */
        buf[offset++] = (VIRTUAL_DISK_SECTORS >> 24) & 0xFF;
        buf[offset++] = (VIRTUAL_DISK_SECTORS >> 16) & 0xFF;
        buf[offset++] = (VIRTUAL_DISK_SECTORS >> 8) & 0xFF;
        buf[offset++] = VIRTUAL_DISK_SECTORS & 0xFF;
        /* 保留 */
        buf[offset++] = 0;
        buf[offset++] = 0;
        /* 块长度（大端序） */
        buf[offset++] = (VIRTUAL_SECTOR_SIZE >> 8) & 0xFF;
        buf[offset++] = VIRTUAL_SECTOR_SIZE & 0xFF;
    }

    /* 处理特定页面代码 */
    switch (pcode) {
    case 0x00:  /* 所有页面 */
    case 0x08:  /* 缓存页面 */
        /* 缓存页面：页面代码=0x08, 页面长度=0x12(18字节) */
        buf[offset++] = 0x08;  /* 页面代码 */
        buf[offset++] = 0x12;  /* 页面长度(18) */
        buf[offset++] = 0x14;  /* 缓存控制：WCE=1, RCD=1 */
        buf[offset++] = 0x00;  /* 缓存大小(MSB) - 未使用 */
        buf[offset++] = 0xff;  /* 缓存大小 */
        buf[offset++] = 0xff;  /* 缓存大小 */
        buf[offset++] = 0x00;  /* 缓存大小(LSB) */
        buf[offset++] = 0x00;  /* 阈值 */
        buf[offset++] = 0xff;  /* 预取大小 */
        buf[offset++] = 0xff;  /* 预取大小 */
        buf[offset++] = 0xff;  /* 预取上限 */
        buf[offset++] = 0xff;  /* 预取上限 */
        buf[offset++] = 0x80;  /* 缓存禁用(CD)=0, FUA=1 */
        buf[offset++] = 0x14;  /* 缓存控制(与字节2相同) */
        buf[offset++] = 0x00;  /* 保留 */
        buf[offset++] = 0x00;  /* 保留 */
        buf[offset++] = 0x00;  /* 保留 */
        buf[offset++] = 0x00;  /* 保留 */
        buf[offset++] = 0x00;  /* 保留 */
        break;
    case 0x01:  /* 读写错误恢复页面 */
        /* 简单的错误恢复页面 */
        buf[offset++] = 0x01;  /* 页面代码 */
        buf[offset++] = 0x0a;  /* 页面长度(10) */
        buf[offset++] = 0x00;  /* 错误恢复控制 */
        buf[offset++] = 0x00;  /* 读重试次数 */
        buf[offset++] = 0x00;  /* 校正跨度 */
        buf[offset++] = 0x00;  /* 磁头偏移次数 */
        buf[offset++] = 0x00;  /* 数据选通偏移次数 */
        buf[offset++] = 0x00;  /* 写重试次数 */
        buf[offset++] = 0x00;  /* 恢复时间限制 */
        buf[offset++] = 0x00;  /* 恢复时间限制 */
        buf[offset++] = 0x00;  /* 保留 */
        break;
    default:
        /* 未知页面 - 只返回头 */
        break;
    }

    /* 设置总长度 */
    len = min(offset, (int)alloc_len);
    put_unaligned_be16(len - 2, buf);  /* 模式数据长度 = 总长度 - 2 */
    cmd->sc_data_direction = DMA_FROM_DEVICE; /* 设置数据传输方向 */
    scsi_sg_copy_from_buffer(cmd, buf, len);  /* 将数据复制到sg列表 */
    cmd->result = DID_OK << 16; /* 设置命令结果为成功 */
    scsi_set_resid(cmd, alloc_len - len); /* 设置剩余长度 */

    return len; /* 返回实际传输长度 */
}

/*
* 执行SCSI MODE SELECT(10)命令
* @param cmd: SCSI命令结构体
* @return: 返回0表示成功
*/
static int do_mode_select_10(struct scsi_cmnd *cmd)
{
    unsigned char *cdb = cmd->cmnd; /* 获取命令描述块指针 */
    u32 param_len = get_unaligned_be16(cdb + 7); /* 参数长度在cdb[7:8] */
    unsigned char *buf; /* 临时缓冲区指针 */

    /* 对于虚拟磁盘，接受但忽略模式选择 */
    cmd->sc_data_direction = DMA_TO_DEVICE; /* 设置数据传输方向 */

    /* 读取并丢弃数据 */
    buf = kmalloc(param_len, GFP_KERNEL); /* 分配临时缓冲区 */
    if (buf) {
        scsi_sg_copy_to_buffer(cmd, buf, param_len); /* 从sg列表复制数据 */
        kfree(buf); /* 释放临时缓冲区 */
    }

    cmd->result = DID_OK << 16; /* 设置命令结果为成功 */
    scsi_set_resid(cmd, 0); /* 没有剩余数据 */

    return 0;
}
```

#### 7.7.1.11. 磁盘读写命令处理[¶](#id43 "永久链接至标题")

该部分实现SCSI读写命令的处理，兼容6字节老旧读写命令与10字节标准读写命令，完成LBA地址解析、参数合法性校验、并发保护、数据拷贝、IO统计等核心操作，模拟真实磁盘硬件的数据读写行为。

do_read和do_write函数(位于linux_driver/41_scsi_subsystem/virtual_scsi_host.c)[¶](#id88 "永久链接至代码")

```c
  1  /*
  2  * 执行SCSI READ命令（6字节或10字节）
  3  * @param cmd: SCSI命令结构体
  4  * @return: 返回读取的字节数或0表示失败
  5  */
  6  static int do_read(struct scsi_cmnd *cmd)
  7  {
  8      struct vhost_data *vhost = host_to_vhost(cmd->device->host); /* 获取虚拟主机数据 */
  9      unsigned char *cdb = cmd->cmnd; /* 获取命令描述块指针 */
 10      u32 lba; /* 逻辑块地址 */
 11      u32 num_sectors; /* 扇区数量 */
 12      unsigned long offset; /* 缓冲区偏移 */
 13      int ret = 0; /* 返回值 */
 14
 15      if (cmd->cmd_len == 6) {
 16          /* READ(6)命令格式 */
 17          lba = ((cdb[1] & 0x1F) << 16) | (cdb[2] << 8) | cdb[3]; /* LBA在cdb[1:3] */
 18          num_sectors = cdb[4]; /* 扇区数在cdb[4] */
 19      } else {
 20          /* READ(10)命令格式 */
 21          lba = get_be32(&cdb[2]); /* LBA在cdb[2:5] */
 22          num_sectors = get_be16(&cdb[7]); /* 扇区数在cdb[7:8] */
 23      }
 24
 25      /* 验证LBA和扇区数量 */
 26      if (lba + num_sectors > VIRTUAL_DISK_SECTORS) {
 27          set_sense_data(cmd, ILLEGAL_REQUEST, 0x21, 0x00); /* LBA越界 */
 28          cmd->result = (DID_OK << 16) | SAM_STAT_CHECK_CONDITION;
 29          return 0;
 30      }
 31
 32      offset = lba * VIRTUAL_SECTOR_SIZE; /* 计算缓冲区偏移 */
 33      cmd->sc_data_direction = DMA_FROM_DEVICE; /* 设置数据传输方向 */
 34
 35      spin_lock(&vhost->lock); /* 获取自旋锁 */
 36
 37      /* 从虚拟磁盘复制数据到scatter-gather列表（DMA_FROM_DEVICE: 从buf到sg） */
 38      ret = scsi_sg_copy_from_buffer(cmd, vhost->disk_buffer + offset,
 39                                  num_sectors * VIRTUAL_SECTOR_SIZE);
 40
 41      spin_unlock(&vhost->lock); /* 释放自旋锁 */
 42
 43      vhost->sectors_read += num_sectors; /* 更新读取统计 */
 44
 45      if (ret < 0) {
 46          cmd->result = DID_ERROR << 16; /* 设置错误结果 */
 47          return 0;
 48      }
 49
 50      cmd->result = DID_OK << 16; /* 设置成功结果 */
 51      scsi_set_resid(cmd, 0); /* 没有剩余数据 */
 52      return ret; /* 返回读取的字节数 */
 53  }
 54
 55  /*
 56  * 执行SCSI WRITE命令（6字节或10字节）
 57  * @param cmd: SCSI命令结构体
 58  * @return: 返回写入的字节数或0表示失败
 59  */
 60  static int do_write(struct scsi_cmnd *cmd)
 61  {
 62      struct vhost_data *vhost = host_to_vhost(cmd->device->host); /* 获取虚拟主机数据 */
 63      unsigned char *cdb = cmd->cmnd; /* 获取命令描述块指针 */
 64      u32 lba; /* 逻辑块地址 */
 65      u32 num_sectors; /* 扇区数量 */
 66      unsigned long offset; /* 缓冲区偏移 */
 67      int ret = 0; /* 返回值 */
 68
 69      if (cmd->cmd_len == 6) {
 70          /* WRITE(6)命令格式 */
 71          lba = ((cdb[1] & 0x1F) << 16) | (cdb[2] << 8) | cdb[3]; /* LBA在cdb[1:3] */
 72          num_sectors = cdb[4]; /* 扇区数在cdb[4] */
 73      } else {
 74          /* WRITE(10)命令格式 */
 75          lba = get_be32(&cdb[2]); /* LBA在cdb[2:5] */
 76          num_sectors = get_be16(&cdb[7]); /* 扇区数在cdb[7:8] */
 77      }
 78
 79      /* 验证LBA和扇区数量 */
 80      if (lba + num_sectors > VIRTUAL_DISK_SECTORS) {
 81          set_sense_data(cmd, ILLEGAL_REQUEST, 0x21, 0x00); /* LBA越界 */
 82          cmd->result = (DID_OK << 16) | SAM_STAT_CHECK_CONDITION;
 83          return 0;
 84      }
 85
 86      offset = lba * VIRTUAL_SECTOR_SIZE; /* 计算缓冲区偏移 */
 87      cmd->sc_data_direction = DMA_TO_DEVICE; /* 设置数据传输方向 */
 88
 89      spin_lock(&vhost->lock); /* 获取自旋锁 */
 90
 91      /* 从scatter-gather列表复制数据到虚拟磁盘（DMA_TO_DEVICE: 从sg到buf） */
 92      ret = scsi_sg_copy_to_buffer(cmd, vhost->disk_buffer + offset,
 93                                  num_sectors * VIRTUAL_SECTOR_SIZE);
 94
 95      spin_unlock(&vhost->lock); /* 释放自旋锁 */
 96
 97      vhost->sectors_written += num_sectors; /* 更新写入统计 */
 98
 99      if (ret < 0) {
100          cmd->result = DID_ERROR << 16; /* 设置错误结果 */
101          return 0;
102      }
103
104      cmd->result = DID_OK << 16; /* 设置成功结果 */
105      scsi_set_resid(cmd, 0); /* 没有剩余数据 */
106      return ret; /* 返回写入的字节数 */
107  }
```

关键说明：

- 第15-23行：根据命令长度解析CDB。对于READ(6)，LBA分布在cdb[1:3]，扇区数在cdb[4]；对于READ(10)，LBA和扇区数分别位于cdb[2:5]和cdb[7:8]。
    
- 第26-30行：检查LBA是否超出虚拟磁盘的物理容量。若发生越界，调用set_sense_data构造SCSI标准错误码ILLEGAL_REQUEST（ASC=0x21表示Logical block address out of range），并将命令状态标记为SAM_STAT_CHECK_CONDITION。这会通知SCSI中间层“设备遇到了需要检查条件的错误”，从而触发上层的错误处理机制。
    
- 第33行：指定数据传输方向为设备到主机。
    
- 第38-39行：将设备端的连续内存数据拷贝到主机端由多个非连续物理页组成的SG列表中。
    
- 第50-52行：设置命令成功状态码(DID_OK)，并将残余数据长度(resid)置0，表明主机请求的数据量已全部成功传输，没有残余。
    
- 第69-77行：逻辑与do_read一致，负责从CDB中提取主机请求写入的目标LBA和扇区数量，为后续的内存偏移计算做准备。
    
- 第80-84行：防止主机下发恶意或错误的越界写请求。
    
- 第87行：指定数据传输方向为主机到设备。
    
- 第92-93行：将主机端分散在SG列表各个物理页中的写入数据，“汇聚”并拷贝到设备端连续的disk_buffer指定偏移处。
    
- 第104-106行：设置命令成功状态码(DID_OK)，并将残余数据长度(resid)置0，表示主机下发的所有写入数据均已被设备成功接收并写入。
    

#### 7.7.1.12. 数据校验与缓存同步[¶](#id44 "永久链接至标题")

该部分实现数据校验、缓存同步命令的处理，主要用于校验磁盘LBA读写合法性、模拟磁盘缓存数据同步操作。

do_verify和do_synchronize_cache函数(位于linux_driver/41_scsi_subsystem/virtual_scsi_host.c)[¶](#id89 "永久链接至代码")

```c
 1  /*
 2  * 执行SCSI VERIFY命令
 3  * @param cmd: SCSI命令结构体
 4  * @return: 返回0表示成功
 5  */
 6  static int do_verify(struct scsi_cmnd *cmd)
 7  {
 8      unsigned char *cdb = cmd->cmnd; /* 获取命令描述块指针 */
 9      u32 lba = get_be32(&cdb[2]); /* LBA在cdb[2:5] */
10      u32 num_sectors = get_be16(&cdb[7]); /* 扇区数在cdb[7:8] */
11
12      /* 验证LBA和扇区数量 */
13      if (lba + num_sectors > VIRTUAL_DISK_SECTORS) {
14          set_sense_data(cmd, ILLEGAL_REQUEST, 0x21, 0x00); /* LBA越界 */
15          cmd->result = (DID_OK << 16) | SAM_STAT_CHECK_CONDITION;
16          return 0;
17      }
18
19      cmd->result = DID_OK << 16; /* 设置成功结果 */
20      return 0;
21  }
22
23  /*
24  * 执行SCSI SYNCHRONIZE CACHE命令
25  * @param cmd: SCSI命令结构体
26  * @return: 返回0表示成功
27  */
28  static int do_synchronize_cache(struct scsi_cmnd *cmd)
29  {
30      /* 虚拟磁盘不需要同步缓存（没有真实缓存） */
31      cmd->result = DID_OK << 16; /* 设置成功结果 */
32      return 0;
33  }
```

关键说明：

- 第13-17行：执行LBA地址越界校验，对超出虚拟磁盘容量的非法校验请求，调用异常函数上报SCSI协议错误。
    
- 第19行：固定返回DID_OK成功状态，模拟真实磁盘数据校验无误、存储完整性的正常反馈。
    
- 第31行：虚拟设备无物理缓存，直接返回执行成功。
    

#### 7.7.1.13. EH错误处理[¶](#eh "永久链接至标题")

该部分实现SCSI标准EH错误处理回调函数，对应真实硬件的异常复位、命令中止功能，当内核检测到命令超时、设备异常时，调用本接口完成命令中止、主机重置、状态恢复等操作。

EH错误处理(位于linux_driver/41_scsi_subsystem/virtual_scsi_host.c)[¶](#id90 "永久链接至代码")

```c
 1  /*
 2  * 中止处理函数 - 当命令需要中止时调用
 3  * @param cmd: 需要中止的SCSI命令
 4  * @return: 返回SUCCESS表示成功
 5  */
 6  static int vhost_eh_abort_handler(struct scsi_cmnd *cmd)
 7  {
 8      dev_info(&cmd->device->host->shost_gendev, "Abort command: opcode 0x%02x\n",
 9              cmd->cmnd[0]);
10
11      /* 对于虚拟驱动，直接完成命令并返回错误 */
12      cmd->result = DID_ABORT << 16; /* 设置中止结果 */
13      vhost_scsi_done(cmd); /* 完成命令 */
14
15      return SUCCESS; /* 返回成功 */
16  }
17
18  /*
19  * 主机重置处理函数 - 当主机需要重置时调用
20  * @param cmd: SCSI命令，用于获取主机信息
21  * @return: 返回SUCCESS表示成功
22  */
23  static int vhost_eh_host_reset_handler(struct scsi_cmnd *cmd)
24  {
25      struct vhost_data *vhost = host_to_vhost(cmd->device->host); /* 获取虚拟主机数据 */
26
27      dev_info(&cmd->device->host->shost_gendev, "Host reset requested\n");
28
29      /* 重置统计信息 */
30      spin_lock(&vhost->lock); /* 获取自旋锁 */
31      vhost->sectors_read = 0; /* 清零读取统计 */
32      vhost->sectors_written = 0; /* 清零写入统计 */
33      spin_unlock(&vhost->lock); /* 释放自旋锁 */
34
35      return SUCCESS; /* 返回成功 */
36  }
```

关键说明：

- 第8-9行：打印异常命令信息，便于故障定位。
    
- 第12行：赋值命令中止状态码，标记底层命令异常终止。
    
- 第13行：调用命令收尾接口，完成异常IO资源回收。
    
- 第15行：返回执行成功，告知内核底层中止处理操作完成。
    
- 第30-33行：加锁清空底层IO统计数据，重置设备运行状态，模拟硬件主机软复位效果。
    
- 第35行：返回执行成功，告知内核底层异常恢复操作完成。
    

### 7.7.2. Makefile说明[¶](#makefile "永久链接至标题")

本节实验使用的Makefile如下所示，编写该Makefile时，只需要根据实际情况修改变量KERNEL_DIR、CROSS_COMPILE和obj-m即可。

Makefile(位于linux_driver/41_scsi_subsystem/Makefile)[¶](#id91 "永久链接至代码")

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
17  obj-m := virtual_scsi_host.o
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

### 7.7.3. 编译驱动[¶](#id45 "永久链接至标题")

在实验目录下输入 `make` 即可编译驱动，编译得到内核模块virtual_scsi_host.ko。

### 7.7.4. 程序运行结果[¶](#id46 "永久链接至标题")

如出现 `Permission denied` 或类似字样，请注意用户权限，大部分操作硬件外设的功能，几乎都需要root用户权限，简单的解决方案是在执行语句前加入sudo或以root用户运行程序。

#### 7.7.4.1. 实验操作[¶](#id47 "永久链接至标题")

使用以下命令加载驱动：

```bash
 1  # 加载驱动
 2  sudo insmod virtual_scsi_host.ko
 3
 4  ### 信息输出如下
 5  # 驱动初始化入口打印
 6  [   24.008222] virtual_scsi_host: Virtual SCSI Host Driver v1.0 initializing...
 7
 8  # 虚拟磁盘内存分配成功，16MB、总扇区32768、单扇区512字节
 9  [   24.035672] virtual_scsi_host: Allocated virtual disk: 16 MB (32768 sectors, 512 bytes/sector)
10
11  # 内核分配1号SCSI主机适配器host1，驱动主机注册成功
12  [   24.036243] scsi host1: virtual_scsi_host
13
14  # 驱动所有资源初始化全部完成，读写统计初始化为0
15  [   24.036729] virtual_scsi_host: Virtual SCSI Host initialized successfully!
16  [   24.036751] virtual_scsi_host: Statistics: sectors_read=0, sectors_written=0
17
18  # SCSI拓扑：host1:channel0:target0:lun0，设备类型为磁盘 Direct-Access，ANSI版本为6
19  [   24.037144] scsi 1:0:0:0: Direct-Access     LubanCat VIRTUAL DISK     1.0  PQ: 0 ANSI: 6
20
21  # 块设备层识别虚拟磁盘，分配块设备节点/dev/sda，识别总扇区32768，容量16MiB
22  [   24.039837] sd 1:0:0:0: [sda] 32768 512-byte logical blocks: (16.8 MB/16.0 MiB)
23
24  # 磁盘未开启写保护，支持读写操作
25  [   24.040010] sd 1:0:0:0: [sda] Write Protect is off
26
27  # 以下两行是信息性消息，并非错误，只是说明内核不会利用写缓存来优化写入操作，所有写操作会立即写入虚拟磁盘缓冲区
28  [   24.040091] sd 1:0:0:0: [sda] No Caching mode page found
29  [   24.040111] sd 1:0:0:0: [sda] Assuming drive cache: write through
```

查看系统SCSI总线设备和块设备节点：

```bash
 1  # 查看系统SCSI总线设备需要安装lsscsi工具
 2  sudo apt update && sudo apt install lsscsi
 3
 4  # 列出所有SCSI主机与LUN设备
 5  lsscsi
 6
 7  # 信息输出如下
 8  [1:0:0:0]    disk    LubanCat VIRTUAL DISK     1.0   /dev/sda
 9
10  # 列出所有块设备节点
11  lsblk
12
13  # 信息输出如下
14  NAME         MAJ:MIN RM  SIZE RO TYPE MOUNTPOINTS
15  sda            8:0    0   16M  0 disk
16  mmcblk0      179:0    0 29.3G  0 disk
17  ├─mmcblk0p1  179:1    0    8M  0 part
18  ├─mmcblk0p2  179:2    0  128M  0 part /boot
19  └─mmcblk0p3  179:3    0 29.2G  0 part /
20  mmcblk0boot0 179:32   0    4M  1 disk
21  mmcblk0boot1 179:64   0    4M  1 disk
22  zram0        254:0    0    0B  0 disk
```

从输出信息可以看到SCSI地址：host 1，通道 0，target 0，lun 0；设备类型磁盘；块设备文件/dev/sda，大小16M，和物理磁盘并列。

使用sg系列工具直接下发SCSI CDB，调用底层驱动queuecommand接口，验证各命令处理函数：

```bash
# 安装sg系列工具
sudo apt update && sudo apt install sg3-utils
```

INQUIRY 设备信息查询：

```bash
 1  # INQUIRY 设备信息查询验证
 2  sudo sg_inq /dev/sda
 3
 4  # 信息输出如下
 5  standard INQUIRY:
 6  PQual=0  PDT=0  RMB=0  LU_CONG=0  hot_pluggable=0  version=0x06  [SPC-4]
 7  [AERC=0]  [TrmTsk=0]  NormACA=0  HiSUP=0  Resp_data_format=2
 8  SCCS=0  ACC=0  TPGS=0  3PC=0  Protect=0  [BQue=0]
 9  EncServ=0  MultiP=0  [MChngr=0]  [ACKREQQ=0]  Addr16=0
10  [RelAdr=0]  WBus16=0  Sync=0  [Linked=0]  [TranDis=0]  CmdQue=0
11      length=36 (0x24)   Peripheral device type: disk
12  Vendor identification: LubanCat
13  Product identification: VIRTUAL DISK
14  Product revision level: 1.0
```

- PQual=0：来自inquiry_data[0]的高3位，0表示设备已连接且逻辑单元存在。
    
- PDT=0：来自inquiry_data[0]的低5位，0表示直接访问块设备，即磁盘。
    
- RMB=0：来自inquiry_data[1]的最高位，0表示介质不可移除。
    
- LU_CONG=0：逻辑单元拥塞位，保留，通常为0。
    
- hot_pluggable=0：热插拔，0表示不支持热插拔。
    
- version=0x06：ANSI版本，0x06对应SPC-4。
    

可以看到设备被正确识别为非可移除、SPC-4、直接访问块设备，厂商和产品信息与inquiry_data数组设置一致。

READ_CAPACITY 容量查询：

```bash
# 容量查询
sudo sg_readcap /dev/sda

# 信息输出如下
Read Capacity results:
Last LBA=32767 (0x7fff), Number of logical blocks=32768
Logical block length=512 bytes
Hence:
Device size: 16777216 bytes, 16.0 MiB, 0.02 GB
```

返回的Last LBA=32767、Logical block length=512，设备容量16.0 MiB，与驱动中定义的VIRTUAL_DISK_SECTORS和VIRTUAL_SECTOR_SIZE完全一致。

TEST_UNIT_READY 就绪检测：

```bash
# 就绪检测
sudo sg_turs -v /dev/sda

# 信息输出如下
test unit ready cdb: [00 00 00 00 00 00]
```

可以看到正常返回ready。

MODE_SENSE/MODE_SELECT 模式命令：

```bash
 1  # 读取缓存模式页，-p 8指定读取缓存模式页，对应0x08模式页
 2  sudo sg_modes -p 8 /dev/sda
 3
 4  ####### 信息输出如下
 5  # 从MODE_SENSE应答中携带设备厂商、产品、固件版本
 6  LubanCat  VIRTUAL DISK      1.0    peripheral_type: disk [0x0]
 7  Mode parameter header from MODE SENSE(10):
 8
 9  # 数据总长度35字节，介质类型为固定磁盘，写保护关闭，支持FUA强制写透功能，不支持超长LBA扩展标识，驱动填充8字节标准块描述符
10  Mode data length=35, medium type=0x00, WP=0, DpoFua=1, longlba=0
11  Block descriptor length=8
12
13  # 前4字节00 00 80 00（大端序）= 十进制32768，匹配宏VIRTUAL_DISK_SECTORS
14  # 后4字节00 00 02 00 = 十进制512，匹配宏VIRTUAL_SECTOR_SIZE
15  > Direct access device block descriptors:
16  Density code=0x0
17  00     00 00 80 00 00 00 02 00
18
19  # 缓存模式页
20  >> Caching, page_control: current
21  00     08 12 14 00 ff ff 00 00  ff ff ff ff 80 14 00 00
22  10     00 00 00
23  #######
24
25  # 测试MODE_SELECT，参考命令如下
26  sudo sg_wr_mode --force -p 8 -c 08,12,14 /dev/sda
```

从输出信息可以看到块描述符和缓存模式页和驱动中填充的一致。

VERIFY 扇区校验命令：

```bash
# 校验LBA 0，共1000个扇区，正常无信息输出
sudo sg_verify -l 0 -c 1000 /dev/sda

# 验证LBA越界报错，传入超出磁盘最大扇区
sudo sg_verify -l 40000 -c 10 /dev/sda

# 信息输出如下，LBA超出范围
VERIFY(10): LBA out of range
    failed near lba=40000 [0x9c40]
sg_verify failed: LBA out of range
```

SYNCHRONIZE_CACHE 缓存同步：

```bash
# 验证缓存同步，正常无信息输出
sudo sg_sync /dev/sda
```

READ/WRITE命令：

```bash
# 写入随机测试数据
sudo sg_dd if=/dev/urandom of=/dev/sda bs=512 count=10

# 读取数据到文件
sudo sg_dd if=/dev/sda of=test_data.bin bs=512 count=10

#无信息报错即为正常
```

虚拟块设备格式化与挂载测试：

```bash
 1  # 格式化为ext4文件系统
 2  sudo mkfs.ext4 /dev/sda
 3
 4  # 信息输出如下
 5  mke2fs 1.47.0 (5-Feb-2023)
 6  Creating filesystem with 16384 1k blocks and 4096 inodes
 7  Filesystem UUID: 5052d0bc-e26b-49f7-84b5-8ab8cc330d88
 8  Superblock backups stored on blocks:
 9          8193
10
11  Allocating group tables: done
12  Writing inode tables: done
13  Creating journal (1024 blocks): done
14  Writing superblocks and filesystem accounting information: done
15
16  # 挂载虚拟磁盘
17  sudo mount /dev/sda /mnt/
18
19  # 信息输出如下
20  [   40.064055] EXT4-fs (sda): mounting with "discard" option, but the device does not support discard
21  [   40.064108] EXT4-fs (sda): mounted filesystem with ordered data mode. Quota mode: disabled.
22
23  # 查看系统挂载情况
24  df -h
25
26  # 信息输出如下
27  Filesystem      Size  Used Avail Use% Mounted on
28  udev            962M  8.0K  962M   1% /dev
29  tmpfs           196M  1.2M  195M   1% /run
30  /dev/mmcblk0p3   29G  2.1G   26G   8% /
31  tmpfs           977M     0  977M   0% /dev/shm
32  tmpfs           5.0M   12K  5.0M   1% /run/lock
33  tmpfs           977M  4.0K  977M   1% /tmp
34  /dev/mmcblk0p2  124M   55M   64M  47% /boot
35  tmpfs           196M     0  196M   0% /run/user/0
36  /dev/sda         14M   14K   13M   1% /mnt
```

可以看到sda虚拟块设备可正常格式化为ext4文件系统，可以被正常挂载。

使用以下命令读写测试：

```bash
#进入挂载目录
cd /mnt/

#写入测试文件
sudo sh -c "echo virtual_scsi_host > test.txt"

#读取测试文件
cat test.txt

#信息打印如下
virtual_scsi_host
```

可以看到可以正常创建和读取文件。

使用以下命令卸载设备与模块：

```bash
 1  #返回家目录
 2  cd ~
 3
 4  #卸载挂载点
 5  sudo umount /mnt/
 6
 7  #卸载内核模块
 8  sudo rmmod virtual_scsi_host
 9
10  #信息打印如下
11  [  164.367897] virtual_scsi_host: Unloading Virtual SCSI Host Driver...
12  [  164.368012] virtual_scsi_host: Final statistics:
13  [  164.368026] virtual_scsi_host:   Sectors read:    3804
14  [  164.368039] virtual_scsi_host:   Sectors written: 4616
15  [  164.482600] virtual_scsi_host: Virtual SCSI Host Driver unloaded successfully!
```

可以从信息输出看到主机从虚拟磁盘读取了3804个扇区，因为每个扇区512字节，总共读取了约1.95 MB的数据。 主机向虚拟磁盘写入了4616个扇区，总计约2.36 MB的数据。所有资源都已正确释放，模块成功从内核移除。

### 7.7.5. 实验注意事项[¶](#id48 "永久链接至标题")

- 所有SCSI命令CDB格式、Sense错误码、数据帧长度需遵循SPC-4协议，保证与内核SCSI子系统协议适配。
    
- 统一使用网络大端序封装LBA、数据长度等参数，避免大小端字节序错乱问题。
    
- 针对非法命令、越界LBA地址，必须返回标准ILLEGAL_REQUEST错误，完善协议异常处理。
    
- 内核内存拷贝、SG散列缓冲区操作需调用内核标准接口，禁止直接裸内存读写，避免内存越界风险。
    
- 虚拟磁盘缓冲区读写操作必须加自旋锁，保障多线程并发IO的数据一致性，防止数据错乱。