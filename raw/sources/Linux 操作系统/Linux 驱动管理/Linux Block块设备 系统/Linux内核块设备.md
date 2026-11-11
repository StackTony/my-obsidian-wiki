原文： https://doc.embedfire.com/linux/rk356x/driver/zh/latest/linux_driver/subsystem_block_device.html

块设备是Linux内核三大设备类型（字符设备、块设备、网络设备）中最重要的存储类设备，是操作系统数据持久化的核心载体。 不同于字符设备的字节流读写模式，块设备以数据块/扇区为最小读写单位，支持随机访问、缓存缓存、IO调度、请求合并，广泛应用于磁盘、U盘、SD卡、EMMC、RAMDISK等存储硬件。

## 4.1. 块设备核心概念[¶](#id1 "永久链接至标题")

### 4.1.1. 块设备定义[¶](#id2 "永久链接至标题")

块设备（Block Device）：是指以固定大小的数据块为单位进行数据读写的硬件设备，支持随机寻址访问，内核会为块设备建立页缓存、块缓存，通过IO调度器优化读写请求顺序，减少硬件寻道时间，提升IO吞吐效率。

块设备最小读写单位为扇区（Sector），内核IO操作最小处理单位为逻辑块（Block），标准Linux系统默认扇区大小512Byte，逻辑块大小1024Byte/4KB。

### 4.1.2. 块设备相关专业名词[¶](#id3 "永久链接至标题")

在深入驱动框架前，需理解块设备子系统中的几个核心抽象概念：

- 扇区(Sector)：块设备硬件寻址的最小单位，传统上为512字节，现代高级格式化磁盘多为4096字节，内核中通常以512字节为逻辑扇区基准。
    
- 块(Block)：文件系统与内核交互的最小单位，通常是内存页（Page，通常为4KB）的整数倍。
    
- Bio(Block I/O)：内核中表示一个I/O操作的基本数据结构。一个Bio包含了一个或多个内存页，以及目标扇区号和操作类型（读/写/丢弃等）。
    
- Request(请求)：I/O调度器将多个指向相邻扇区的Bio合并后形成的数据结构，代表一次提交给底层驱动的实际硬件I/O任务。
    
- I/O调度器(I/O Scheduler)：位于块层和驱动之间，负责重新排序和合并Request，以优化磁盘磁头移动或提升并发性能。
    

## 4.2. 块设备驱动框架[¶](#id4 "永久链接至标题")

现代Linux内核（4.x后期及以后版本）全面采用了blk-mq(Multi-Queue Block Layer)架构，以消除传统单队列块层的锁竞争瓶颈，充分发挥多核CPU和多队列硬件（如NVMe）的性能。

### 4.2.1. blk-mq多队列机制原理[¶](#blk-mq "永久链接至标题")

blk-mq多队列架构是内核为解决多核IO瓶颈设计的新型调度模型，采用软件队列+硬件队列双层队列架构，解决全局单队列锁竞争问题。

- 软件队列（mq_ctx）：每一个CPU核独立分配一个私有软件队列，CPU仅操作自身队列，无跨核锁竞争，请求入队无阻塞，极大提升IO入队效率。
    
- 硬件队列（hw_ctx）：对应硬件设备支持的并发通道，数量可配置（通常等于CPU核数或硬件通道数），负责汇总软件队列请求、下发硬件处理，支持并行IO处理。
    

### 4.2.2. 数据流向与框架层次[¶](#id5 "永久链接至标题")

![../_images/subsystem_block_device_0.png](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/subsystem_block_device_0.png)

1. 用户空间：发起read/write系统调用。
    
2. VFS & 文件系统层：将文件偏移量转换为逻辑块号，生成Bio结构。
    
3. 块设备层(Block Layer)：接收Bio，通过I/O调度器将其合并为Request，并放入硬件队列。
    
4. 块设备驱动层 (Block Device Driver)：通过注册blk_mq_ops中的queue_rq回调函数，从硬件队列中取出Request，直接操作硬件寄存器或内存缓冲区。
    
5. 硬件层：执行实际的物理读写操作，完成后触发中断。
    
6. 驱动层：在中断处理或轮询中调用blk_mq_end_request，通知块层该请求已完成，唤醒等待的进程。
    

## 4.3. 块设备核心结构体[¶](#id6 "永久链接至标题")

### 4.3.1. 磁盘设备主体结构体[¶](#id7 "永久链接至标题")

磁盘设备主体结构体（struct gendisk）用于描述一个完整的磁盘设备，包含设备号、设备名称、请求队列、操作集、容量信息等核心属性，是块设备注册的核心结构体。

gendisk结构体(内核源码/include/linux/blkdev.h)[¶](#id36 "永久链接至代码")

```c
 1  struct gendisk {
 2      int major;                          // 主设备号
 3      int first_minor;                    // 起始次设备号
 4      int minors;                         // 次设备号数量，决定最大分区数
 5
 6      char disk_name[DISK_NAME_LEN];      // 块设备名称
 7
 8      const struct block_device_operations *fops; // 块设备文件操作回调集
 9      struct request_queue *queue;        // 设备IO请求队列
10      void *private_data;                 // 驱动自定义私有数据指针
11
12      sector_t capacity;                  // 设备总容量，单位扇区
13      int flags;                          // 设备基础状态标志位
14      unsigned long state;                // 设备运行状态位图
15
16      /* 设备状态宏定义 */
17  #define GD_NEED_PART_SCAN   0           // 需要重新扫描分区
18  #define GD_READ_ONLY        1           // 设备只读模式
19  #define GD_DEAD             2           // 设备已失效/卸载
20  #define GD_ADDED            4           // 设备已注册至内核
21
22      struct mutex open_mutex;            // 设备打开/关闭互斥锁
23      unsigned open_partitions;           // 当前打开的分区数量
24      struct backing_dev_info *bdi;       // 设备后端缓存信息
25      struct kobject *slave_dir;          // 设备sysfs节点目录
26      int node_id;                        // 设备所属NUMA节点
27      struct lockdep_map lockdep_map;     // 锁调试检测映射
28      u64 diskseq;                        // 设备全局唯一序列号
29      /* 其他成员省略 */
30  };
```

### 4.3.2. 块设备操作集结构体[¶](#id8 "永久链接至标题")

块设备操作集结构体（struct block_device_operations）定义了用户空间或内核其他子系统对该块设备执行特定操作时的回调函数。

block_device_operations结构体(内核源码/include/linux/blkdev.h)[¶](#id37 "永久链接至代码")

```c
 1  struct block_device_operations {
 2      void (*submit_bio)(struct bio *bio);                        // 提交bio IO请求
 3      int (*open)(struct block_device *, fmode_t);                // 设备打开回调
 4      void (*release)(struct gendisk *, fmode_t);                 // 设备关闭释放回调
 5      int (*ioctl)(struct block_device *, fmode_t, unsigned, unsigned long);          // ioctl命令
 6      unsigned int (*check_events)(struct gendisk *disk, unsigned int clearing);      // 检测设备热插拔/状态事件
 7      int (*getgeo)(struct block_device *, struct hd_geometry *); // 获取磁盘几何参数
 8      int (*set_read_only)(struct block_device *bdev, bool ro);   // 设置设备只读/可写模式
 9      char *(*devnode)(struct gendisk *disk, umode_t *mode);      // 自定义设备节点属性
10      struct module *owner;                                       // 模块所有者
11
12      /* 其他成员省略 */
13  };
```

### 4.3.3. 磁盘几何信息结构体[¶](#id9 "永久链接至标题")

磁盘几何信息结构体（struct hd_geometry）定义模拟传统机械磁盘的物理参数，供内核上层工具识别磁盘规格，固态硬盘/虚拟磁盘可自定义模拟参数。

hd_geometry结构体(内核源码/include/uapi/linux/hdreg.h)[¶](#id38 "永久链接至代码")

```c
struct hd_geometry {
    unsigned char heads;        // 磁头数量
    unsigned char sectors;      // 每磁道扇区数
    unsigned short cylinders;   // 柱面数量
    unsigned long start;        // 磁盘起始扇区偏移
};
```

### 4.3.4. Blk-MQ标签集结构体[¶](#id10 "永久链接至标题")

Blk-MQ标签集结构体（struct blk_mq_tag_set）用于管理硬件队列数量、请求深度、IO操作集、私有数据，是Blk-MQ架构初始化的基础。

blk_mq_tag_set结构体(内核源码/include/linux/blk-mq.h)[¶](#id39 "永久链接至代码")

```c
 1  struct blk_mq_tag_set {
 2      struct blk_mq_queue_map map[HCTX_MAX_TYPES];// 硬件队列映射关系
 3      unsigned int        nr_maps;                // 有效队列映射数量
 4      const struct blk_mq_ops *ops;               // Blk-MQ请求操作回调集
 5      unsigned int        nr_hw_queues;           // 硬件队列数量，通常等于CPU核数
 6      unsigned int        queue_depth;            // 单队列最大并发请求深度
 7      unsigned int        reserved_tags;          // 预留标签数量，特殊IO保留
 8      unsigned int        cmd_size;               // 自定义命令私有数据大小
 9      int     numa_node;                          // 绑定NUMA节点编号
10      unsigned int        timeout;                // IO请求超时时间
11      unsigned int        flags;                  // 队列特性标志位
12      void    *driver_data;                       // 驱动私有数据指针
13
14      /* 其他成员省略 */
15  };
```

### 4.3.5. Blk-MQ操作回调集结构体[¶](#id11 "永久链接至标题")

Blk-MQ操作回调集结构体（struct blk_mq_ops）用于多队列IO请求处理核心回调，唯一必需接口为队列请求处理函数，负责解析并处理所有读写IO请求。

blk_mq_ops结构体(内核源码/include/linux/blk-mq.h)[¶](#id40 "永久链接至代码")

```c
 1  struct blk_mq_ops {
 2      // 单请求IO派发核心入口，驱动必须实现
 3      blk_status_t (*queue_rq)(struct blk_mq_hw_ctx *,
 4                              const struct blk_mq_queue_data *);
 5
 6      // 批量请求硬件提交收尾，适配批量下发场景
 7      void (*commit_rqs)(struct blk_mq_hw_ctx *);
 8
 9      // 批量IO请求派发，优化高并发IO吞吐
10      void (*queue_rqs)(struct request **rqlist);
11
12      // 请求超时处理，IO异常容错回调
13      enum blk_eh_timer_return (*timeout)(struct request *);
14
15      // 硬件队列初始化，多核队列资源分配
16      int (*init_hctx)(struct blk_mq_hw_ctx *, void *, unsigned int);
17
18      // 硬件队列资源释放
19      void (*exit_hctx)(struct blk_mq_hw_ctx *, unsigned int);
20
21      // 单个请求私有资源初始化
22      int (*init_request)(struct blk_mq_tag_set *set, struct request *,
23                          unsigned int, unsigned int);
24
25      // 单个请求私有资源释放
26      void (*exit_request)(struct blk_mq_tag_set *set, struct request *,
27                          unsigned int);
28
29      /* 其他成员省略 */
30  };
```

### 4.3.6. 块设备IO请求结构体[¶](#io "永久链接至标题")

块设备IO请求结构体（struct request）用于定义上层下发的IO请求封装体，包含读写方向、扇区位置、数据长度、队列信息，是驱动层处理IO的核心对象。

blk_mq_ops结构体(内核源码/include/linux/blk-mq.h)[¶](#id41 "永久链接至代码")

```c
 1  struct request {
 2      struct request_queue *q;        // 所属IO请求队列
 3      struct blk_mq_ctx *mq_ctx;      // 软件队列上下文
 4      struct blk_mq_hw_ctx *mq_hctx;  // 硬件队列上下文
 5
 6      blk_opf_t cmd_flags;            // 请求操作类型与标志
 7      req_flags_t rq_flags;           // 请求状态标志位
 8
 9      int tag;                        // 请求唯一标签ID
10      unsigned int timeout;           // 请求超时时间
11
12      unsigned int __data_len;        // 请求总数据长度
13      sector_t __sector;              // 请求起始扇区
14
15      struct bio *bio;                // 请求首个bio片段
16      struct bio *biotail;            // 请求末尾bio片段
17
18      union {
19          struct list_head queuelist; // 队列链表节点
20          struct request *rq_next;    // 下一个请求指针
21      };
22
23      struct block_device *part;      // 关联的块设备分区
24      enum mq_rq_state state;         // 请求当前状态
25      atomic_t ref;                   // 请求引用计数
26
27      unsigned short nr_phys_segments;// 物理聚合段数量
28      unsigned short ioprio;          // IO优先级
29
30      rq_end_io_fn *end_io;           // IO完成回调函数
31      void *end_io_data;              // IO完成回调私有数据
32
33      /* 其他成员省略 */
34  };
```

### 4.3.7. 块设备最小IO单元结构体[¶](#id12 "永久链接至标题")

块设备最小IO单元结构体（struct bio）用于描述一段连续/分散的读写数据。一个request可包含多个bio，是驱动层面遍历处理数据的核心载体。

bio结构体(内核源码/include/linux/blk_types.h)[¶](#id42 "永久链接至代码")

```c
 1  struct bio {
 2      struct bio      *bi_next;        // 指向下一个bio，构成请求bio链表
 3      struct block_device *bi_bdev;    // 关联的目标块设备
 4      blk_opf_t       bi_opf;          // IO操作类型、读写标志
 5      unsigned short  bi_flags;        // BIO状态标志位
 6      unsigned short  bi_ioprio;       // IO优先级
 7      blk_status_t    bi_status;       // 当前IO处理状态
 8
 9      struct bvec_iter    bi_iter;     // IO迭代器（扇区偏移、长度）
10      bio_end_io_t    *bi_end_io;      // bio单独完成回调
11      void            *bi_private;     // 驱动自定义私有数据
12
13      unsigned short  bi_vcnt;         // 当前有效数据段数量
14      unsigned short  bi_max_vecs;     // 最大支持数据段数量
15      atomic_t        __bi_cnt;        // bio引用计数
16
17      struct bio_vec  *bi_io_vec;      // 分散聚合数据段数组
18      struct bio_set  *bi_pool;        // bio内存池
19
20      // 内嵌数据段，避免小IO重复内存分配
21      struct bio_vec  bi_inline_vecs[];
22
23      /* 其他成员省略 */
24  };
```

### 4.3.8. IO分散聚合数据段单元结构体[¶](#id13 "永久链接至标题")

IO分散聚合数据段单元结构体（struct bio_vec）用于描述一段位于物理页中的内存缓冲区，多个bio_vec组成bio的完整读写数据缓冲区。

bio_vec结构体(内核源码/include/linux/bvec.h)[¶](#id43 "永久链接至代码")

```c
struct bio_vec {
    struct page *bv_page;          // 物理页结构体指针
    unsigned int    bv_len;        // 当前数据段有效长度
    unsigned int    bv_offset;     // 数据在页内的偏移地址
};
```

### 4.3.9. 请求迭代器结构体[¶](#id14 "永久链接至标题")

请求迭代器结构体（struct req_iterator）用于遍历request中所有bio、bio_vec的迭代器结构体，是驱动中循环处理IO数据段的核心辅助结构体，配合内核遍历宏快速读写数据。

req_iterator结构体(内核源码/include/linux/blk-mq.h)[¶](#id44 "永久链接至代码")

```c
struct req_iterator {
    struct bvec_iter iter;  // bio数据段迭代偏移信息
    struct bio *bio;        // 当前遍历的bio对象
};
```

## 4.4. 块设备核心函数[¶](#id15 "永久链接至标题")

### 4.4.1. 注册块设备号[¶](#id16 "永久链接至标题")

#### 4.4.1.1. register_blkdev函数[¶](#register-blkdev "永久链接至标题")

register_blkdev函数用于向内核注册块设备主设备号，支持静态指定或动态分配。动态分配传入major=0，内核自动分配空闲主设备号。

函数原型：

```c
int register_blkdev(unsigned int major, const char *name);
```

参数说明：

- major：需要注册的主设备号，传0表示动态分配。
    
- name：块设备名称。
    

返回值：成功返回主设备号；失败返回负数错误码。

### 4.4.2. 注销块设备号[¶](#id17 "永久链接至标题")

#### 4.4.2.1. unregister_blkdev函数[¶](#unregister-blkdev "永久链接至标题")

unregister_blkdev函数用于反向注销已注册的块设备主设备号，释放设备号资源，与register_blkdev成对使用。

函数原型：

```c
void unregister_blkdev(unsigned int major, const char *name);
```

参数说明：

- major：已注册的主设备号。
    
- name：块设备名称。
    

### 4.4.3. 分配MQ标签集资源[¶](#mq "永久链接至标题")

#### 4.4.3.1. blk_mq_alloc_tag_set函数[¶](#blk-mq-alloc-tag-set "永久链接至标题")

blk_mq_alloc_tag_set函数用于初始化并分配Blk-MQ多队列标签集核心资源，创建硬件队列、请求标签管理池，是多队列驱动初始化的核心前置函数。

函数原型：

```c
int blk_mq_alloc_tag_set(struct blk_mq_tag_set *set);
```

参数说明：

- set：已配置参数的blk_mq_tag_set结构体指针。
    

返回值：0 成功；负数 失败。

### 4.4.4. 释放MQ标签集[¶](#id18 "永久链接至标题")

#### 4.4.4.1. blk_mq_free_tag_set函数[¶](#blk-mq-free-tag-set "永久链接至标题")

blk_mq_free_tag_set函数用于释放Blk-MQ标签集占用的内核资源、队列内存、标签池，与blk_mq_alloc_tag_set成对使用。

函数原型：

```c
void blk_mq_free_tag_set(struct blk_mq_tag_set *set);
```

参数说明：

- set：需要释放的标签集结构体指针。
    

### 4.4.5. 分配gendisk结构体和请求队列[¶](#gendisk "永久链接至标题")

#### 4.4.5.1. blk_mq_alloc_disk函数[¶](#blk-mq-alloc-disk "永久链接至标题")

blk_mq_alloc_disk函数是Linux 5.14及以上内核版本新API，一次性分配gendisk磁盘结构体+初始化多队列请求队列，简化驱动初始化流程。

函数原型：

```c
struct gendisk *blk_mq_alloc_disk(struct blk_mq_tag_set *set, void *queuedata);
```

参数说明：

- set：已初始化的Blk-MQ标签集。
    
- queuedata：队列私有数据，指向驱动设备结构体。
    

返回值：成功返回gendisk指针；失败返回错误指针。

### 4.4.6. 分配gendisk结构体[¶](#id19 "永久链接至标题")

#### 4.4.6.1. alloc_disk函数[¶](#alloc-disk "永久链接至标题")

alloc_disk函数是Linux 5.13及以下旧内核版本API，单独分配gendisk磁盘结构体，需要手动初始化请求队列。

函数原型：

```c
struct gendisk *alloc_disk(int minors);
```

参数说明：

- minors：支持的次设备号数量（分区数量）。
    

返回值：成功返回gendisk指针；失败返回NULL。

### 4.4.7. 初始化多队列请求队列[¶](#id20 "永久链接至标题")

#### 4.4.7.1. blk_mq_init_queue函数[¶](#blk-mq-init-queue "永久链接至标题")

blk_mq_init_queue函数是Linux 5.13及以下旧内核版本API，基于已初始化的Blk-MQ标签集手动创建、初始化多队列请求队列。搭配alloc_disk使用，为gendisk绑定IO队列，是旧版本块设备驱动队列初始化的核心接口。

函数原型：

```c
struct request_queue *blk_mq_init_queue(struct blk_mq_tag_set *set);
```

参数说明：

- set：已完成配置与初始化的blk_mq_tag_set标签集结构体。
    

返回值：成功返回request_queue队列指针；失败返回错误指针（需通过IS_ERR判断）。

### 4.4.8. 清理销毁请求队列[¶](#id21 "永久链接至标题")

#### 4.4.8.1. blk_cleanup_queue函数[¶](#blk-cleanup-queue "永久链接至标题")

blk_cleanup_queue函数用于安全清理、销毁请求队列资源，停止队列调度、释放队列内存，仅用于5.13及以下旧内核。新内核由blk_mq_alloc_disk自动管理队列生命周期，无需手动调用。

函数原型：

```c
void blk_cleanup_queue(struct request_queue *q);
```

参数说明：

- q：需要销毁的request_queue队列指针。
    

### 4.4.9. 注册磁盘设备到内核[¶](#id22 "永久链接至标题")

#### 4.4.9.1. add_disk函数[¶](#add-disk "永久链接至标题")

add_disk函数用于将初始化完成的gendisk设备注册到内核，创建设备节点、sysfs节点，设备正式可用。

函数原型：

```c
// 5.15及以上内核
int add_disk(struct gendisk *disk);

// 5.14及以下内核
void add_disk(struct gendisk *disk);
```

参数说明:

- disk：已完成参数配置的gendisk结构体。
    

返回值：5.15+内核版本返回0成功、负数失败；旧版本无返回值。

### 4.4.10. 从内核移除磁盘设备[¶](#id23 "永久链接至标题")

#### 4.4.10.1. del_gendisk函数[¶](#del-gendisk "永久链接至标题")

del_gendisk函数用于反向注销磁盘设备，删除设备节点、释放内核设备资源，驱动卸载核心接口。

函数原型：

```c
void del_gendisk(struct gendisk *disk);
```

参数说明：

- disk：需要注销的gendisk结构体。
    

### 4.4.11. 设置设备容量[¶](#id24 "永久链接至标题")

#### 4.4.11.1. set_capacity函数[¶](#set-capacity "永久链接至标题")

set_capacity函数用于设置块设备总容量，内核自动同步至sysfs和用户态，单位为扇区。

函数原型：

```c
static inline void set_capacity(struct gendisk *disk, sector_t size);
```

参数说明：

- disk：目标磁盘设备结构体。
    
- size：设备总扇区数量。
    

### 4.4.12. 标记请求开始处理[¶](#id25 "永久链接至标题")

#### 4.4.12.1. blk_mq_start_request函数[¶](#blk-mq-start-request "永久链接至标题")

blk_mq_start_request函数用于标记IO请求开始处理，更新请求状态、计时，防止内核超时判定。

函数原型：

```c
void blk_mq_start_request(struct request *rq);
```

参数说明：

- rq：待处理的IO请求结构体。
    

### 4.4.13. 结束IO请求[¶](#id26 "永久链接至标题")

#### 4.4.13.1. blk_mq_end_request函数[¶](#blk-mq-end-request "永久链接至标题")

blk_mq_end_request函数用于完成IO请求处理，上报处理状态，释放请求资源，是驱动IO处理的收尾核心接口。

函数原型：

```c
void blk_mq_end_request(struct request *rq, blk_status_t status);
```

参数说明：

- rq：处理完成的IO请求。
    
- status：处理状态，BLK_STS_OK成功，其余为错误。
    

### 4.4.14. 判断透传请求[¶](#id27 "永久链接至标题")

#### 4.4.14.1. blk_rq_is_passthrough函数[¶](#blk-rq-is-passthrough "永久链接至标题")

blk_rq_is_passthrough函数用于判断当前IO请求是否为硬件透传请求（直通请求）。此类请求绕过内核文件系统与IO调度，多用于SCSI/SD/EMMC硬件指令透传、自定义控制命令，常规磁盘读写业务不会产生该类请求，通用块设备驱动可直接屏蔽。

函数原型：

```c
static inline bool blk_rq_is_passthrough(const struct request *rq);
```

参数说明：

- rq：待判断的IO请求结构体。
    

返回值：true-是硬件透传请求；false-普通读写IO请求。

### 4.4.15. 设置逻辑块大小[¶](#id28 "永久链接至标题")

#### 4.4.15.1. blk_queue_logical_block_size函数[¶](#blk-queue-logical-block-size "永久链接至标题")

blk_queue_logical_block_size函数用于设置块设备逻辑块大小，是内核文件系统识别的最小读写单位，常规块设备默认配置为512Byte。该参数会上报至用户态，影响文件系统格式化、IO对齐策略。

函数原型：

```c
static inline void blk_queue_logical_block_size(struct request_queue *q, unsigned int size);
```

参数说明：

- q：设备对应的请求队列。
    
- size：逻辑块大小，必须为2的幂次（512/1024/2048/4096）。
    

### 4.4.16. 设置物理块大小[¶](#id29 "永久链接至标题")

#### 4.4.16.1. blk_queue_physical_block_size函数[¶](#blk-queue-physical-block-size "永久链接至标题")

blk_queue_physical_block_size函数用于设置块设备物理块大小，对应硬件底层最小操作单元，用于内核IO对齐优化，避免非对齐读写造成的性能损耗。机械硬盘、SSD多为4KB，虚拟设备可与逻辑块保持一致。

函数原型：

```c
static inline void blk_queue_physical_block_size(struct request_queue *q, unsigned int size);
```

参数说明：

- q：设备对应的请求队列。
    
- size：物理块大小，必须大于等于逻辑块大小，2的幂次。
    

### 4.4.17. 设置单次最大IO扇区数[¶](#id30 "永久链接至标题")

#### 4.4.17.1. blk_queue_max_hw_sectors函数[¶](#blk-queue-max-hw-sectors "永久链接至标题")

blk_queue_max_hw_sectors函数用于限制硬件单次IO请求支持的最大扇区数量，用于约束单次读写数据上限，防止超大IO请求导致硬件溢出、DMA超限。默认常规设备设置1024扇区（512KB）。

函数原型：

```c
static inline void blk_queue_max_hw_sectors(struct request_queue *q, unsigned int max_sectors);
```

参数说明：

- q：设备对应的请求队列。
    
- max_sectors：单次IO最大支持扇区数。
    

## 4.5. RAM模拟块设备实验[¶](#ram "永久链接至标题")

本实验驱动基于Linux内核标准blk-mq多队列块设备框架开发，实现纯内存模拟的虚拟RAM磁盘块设备，无需物理存储介质，依靠内核内存空间模拟磁盘读写功能。 驱动默认创建16MB容量的虚拟块设备，兼容Linux 4.19~6.1+内核版本，支持标准块设备打开/释放、IO读写、IOCTL控制、磁盘几何信息查询等功能。

本章的示例代码目录为： **linux_driver/38_ram_block**

### 4.5.1. 驱动代码详解[¶](#id31 "永久链接至标题")

**核心定义与数据结构**

核心定义与数据结构(位于linux_driver/38_ram_block/ram_block.c)[¶](#id45 "永久链接至代码")

```c
 1  /* 定义RAM块设备的名称 */
 2  #define RAMDISK_NAME        "ram_block"
 3  /* 定义RAM磁盘的默认大小为16MB */
 4  #define RAMDISK_SIZE_MB     16
 5  /* 定义扇区大小为512字节 */
 6  #define KERNEL_SECTOR_SIZE  512
 7
 8  /* 驱动私有数据结构体 */
 9  struct ramdisk_dev {
10      u8                  *data;      /* 指向RAM磁盘数据缓冲区的指针，存储实际的磁盘数据 */
11      size_t              size;       /* RAM磁盘的总大小，单位为字节 */
12      sector_t            capacity;   /* RAM磁盘的总容量，单位为扇区数 */
13      struct gendisk      *gd;        /* 指向关联的gendisk结构体 */
14      struct blk_mq_tag_set tag_set;  /* blk-mq标签集，管理多队列的请求标签和资源 */
15      spinlock_t          lock;       /* 自旋锁，保护设备数据缓冲区的并发访问 */
16      atomic_t            refcnt;     /* 原子引用计数，跟踪设备的打开次数 */
17  };
18
19  /* 全局设备指针 */
20  static struct ramdisk_dev *ramdisk_dev;
21
22  /* 动态分配的主设备号 */
23  static int major_num;
```

关键说明：

- 第2-6行：定义设备名称ram_block，默认RAM磁盘大小为16MB，扇区大小固定为512字节。
    
- 第9-17行：驱动私有设备管理结构体，保存单个RAM磁盘运行资源。
    
- 第23行：动态分配块设备的主设备号。
    

**块设备打开/释放操作函数**

块设备打开/释放操作函数(位于linux_driver/38_ram_block/ram_block.c)[¶](#id46 "永久链接至代码")

```c
 1  /* 块设备打开操作函数 */
 2  static int ramdisk_open(struct block_device *bdev, fmode_t mode)
 3  {
 4      /* 从块设备的gendisk结构体中获取驱动私有数据 */
 5      struct ramdisk_dev *dev = bdev->bd_disk->private_data;
 6
 7      /* 原子递增设备引用计数 */
 8      atomic_inc(&dev->refcnt);
 9      /* 打印调试信息，显示当前引用计数 */
10      pr_debug("ramdisk: Device opened, refcnt=%d\n", atomic_read(&dev->refcnt));
11
12      return 0;
13  }
14
15  /* 块设备释放操作函数 */
16  static void ramdisk_release(struct gendisk *disk, fmode_t mode)
17  {
18      /* 从gendisk结构体中获取驱动私有数据 */
19      struct ramdisk_dev *dev = disk->private_data;
20
21      /* 原子递减设备引用计数 */
22      atomic_dec(&dev->refcnt);
23      /* 打印调试信息，显示当前引用计数 */
24      pr_debug("ramdisk: Device released, refcnt=%d\n", atomic_read(&dev->refcnt));
25  }
```

关键说明：

- 第8、22行：open设备时原子递增引用计数，close设备时原子递减引用计数，保证并发安全。
    

**获取磁盘几何信息**

获取磁盘几何信息(位于linux_driver/38_ram_block/ram_block.c)[¶](#id47 "永久链接至代码")

```c
 1  /* 获取磁盘几何信息函数 */
 2  static int ramdisk_getgeo(struct block_device *bdev, struct hd_geometry *geo)
 3  {
 4      /* 从块设备的gendisk结构体中获取驱动私有数据 */
 5      struct ramdisk_dev *dev = bdev->bd_disk->private_data;
 6      /* 获取设备总扇区数 */
 7      unsigned long capacity = dev->capacity;
 8
 9      /* 模拟磁头数，设置为16 */
10      geo->heads = 16;
11      /* 模拟每磁道扇区数，设置为63 */
12      geo->sectors = 63;
13      /* 计算并模拟柱面数：总扇区数 / (磁头数 * 每磁道扇区数) */
14      geo->cylinders = (unsigned short)(capacity / (geo->heads * geo->sectors));
15      /* 磁盘起始扇区，设置为0 */
16      geo->start = 0;
17
18      return 0;
19  }
```

关键说明：

- 第10-16行：模拟老式磁盘磁头/扇区/柱面参数，fdisk等老式分区工具依赖该接口识别磁盘硬件参数。
    

**块设备IOCTL控制操作函数**

块设备IOCTL控制操作函数(位于linux_driver/38_ram_block/ram_block.c)[¶](#id48 "永久链接至代码")

```c
 1  /* 块设备IOCTL控制操作函数 */
 2  static int ramdisk_ioctl(struct block_device *bdev, fmode_t mode,
 3                          unsigned int cmd, unsigned long arg)
 4  {
 5      /* 从块设备的gendisk结构体中获取驱动私有数据 */
 6      struct ramdisk_dev *dev = bdev->bd_disk->private_data;
 7
 8      /* 根据不同的IOCTL命令进行处理 */
 9      switch (cmd) {
10      /* BLKGETSIZE命令：获取设备总扇区数 */
11      case BLKGETSIZE:
12          /* 将设备容量复制到用户空间 */
13          return put_user((unsigned long)dev->capacity, (unsigned long __user *)arg);
14      /* BLKGETSIZE64命令：获取设备总字节数 */
15      case BLKGETSIZE64:
16          /* 将设备总字节数复制到用户空间 */
17          return put_user((u64)dev->capacity << 9, (u64 __user *)arg);
18      /* 不支持的IOCTL命令 */
19      default:
20          /* 返回不支持的命令错误码 */
21          return -ENOTTY;
22      }
23  }
```

关键说明：

- 第11行：获取设备总扇区数（32位）命令。
    
- 第13行：put_user将内核数据拷贝至用户空间，返回32bit扇区总数。
    
- 第15行：获取设备总字节数（64位）命令。
    
- 第17行：扇区号 << 9 将扇区转换为字节偏移，返回64位磁盘容量。
    

**块设备操作集**

块设备操作集(位于linux_driver/38_ram_block/ram_block.c)[¶](#id49 "永久链接至代码")

```c
/* 块设备操作函数集 */
static const struct block_device_operations ramdisk_fops = {
    .owner      = THIS_MODULE,
    .open       = ramdisk_open,
    .release    = ramdisk_release,
    .ioctl      = ramdisk_ioctl,
    .getgeo     = ramdisk_getgeo,   /* 获取磁盘几何信息函数指针 */
};
```

把上述四个回调函数挂载到内核块设备操作结构体。

**blk-mq请求处理函数**

ramdisk_queue_rq函数是blk-mq收到读写IO请求的唯一入口，实现内存盘和用户缓冲区的数据拷贝，处理流程为：获取IO请求->校验非直通请求->加自旋锁->遍历IO分散内存段->扇区转字节偏移->边界越界检查->memcpy读写内存->解锁自旋锁->通知内核IO完成。

blk-mq请求处理函数(位于linux_driver/38_ram_block/ram_block.c)[¶](#id50 "永久链接至代码")

```c
 1  /* blk-mq请求处理主函数 */
 2  static blk_status_t ramdisk_queue_rq(struct blk_mq_hw_ctx *hctx,
 3                                      const struct blk_mq_queue_data *bd)
 4  {
 5      /* 获取当前要处理的请求结构体 */
 6      struct request *rq = bd->rq;
 7      /* 从请求队列的私有数据中获取设备结构体 */
 8      struct ramdisk_dev *dev = rq->q->queuedata;
 9      /* 请求迭代器，用于遍历请求中的所有bio段 */
10      struct req_iterator iter;
11      /* bio向量结构体，存储单个数据段的信息 */
12      struct bio_vec bvec;
13      /* 当前处理的起始扇区号 */
14      sector_t sector = blk_rq_pos(rq);
15      /* 用于保存中断状态的变量 */
16      unsigned long flags;
17      /* 请求处理状态，初始化为成功 */
18      blk_status_t status = BLK_STS_OK;
19
20      /* 标记请求开始处理，更新请求状态 */
21      blk_mq_start_request(rq);
22
23      /* 检查是否为透传请求 */
24      if (blk_rq_is_passthrough(rq)) {
25          /* 打印警告信息，不支持透传请求 */
26          pr_warn("ramdisk: Passthrough requests not supported\n");
27          /* 设置状态为不支持 */
28          status = BLK_STS_NOTSUPP;
29          /* 跳转到请求完成处理 */
30          goto out;
31      }
32
33      /* 获取自旋锁并禁用本地中断，保护数据缓冲区 */
34      spin_lock_irqsave(&dev->lock, flags);
35
36      /* 遍历请求中的所有bio数据段 */
37      rq_for_each_segment(bvec, rq, iter) {
38          /* 获取数据段在内存中的虚拟地址 */
39          void *buf = page_address(bvec.bv_page) + bvec.bv_offset;
40          /* 获取数据段的长度，单位为字节 */
41          size_t len = bvec.bv_len;
42          /* 计算数据段在RAM磁盘中的偏移量 */
43          loff_t offset = (loff_t)sector << 9;
44
45          /* 边界检查：确保IO操作不超出设备范围 */
46          if (offset + len > dev->size) {
47              /* 打印错误信息，显示越界的IO参数 */
48              pr_err("ramdisk: I/O beyond device end (offset=%lld, len=%zu, size=%zu)\n",
49                  offset, len, dev->size);
50              /* 设置状态为IO错误 */
51              status = BLK_STS_IOERR;
52              /* 跳出循环，终止处理 */
53              break;
54          }
55
56          /* 根据请求方向处理读写操作 */
57          if (rq_data_dir(rq) == READ) {
58              /* 读操作：从RAM磁盘复制数据到内核缓冲区 */
59              memcpy(buf, dev->data + offset, len);
60          } else {
61              /* 写操作：从内核缓冲区复制数据到RAM磁盘 */
62              memcpy(dev->data + offset, buf, len);
63          }
64
65          /* 更新下一个要处理的扇区号 */
66          sector += len >> 9;
67      }
68
69      /* 释放自旋锁并恢复中断状态 */
70      spin_unlock_irqrestore(&dev->lock, flags);
71
72  out:
73      /* 完成请求处理，通知blk-mq框架 */
74      blk_mq_end_request(rq, status);
75      /* 返回处理状态 */
76      return BLK_STS_OK;
77  }
78
79  /* blk-mq操作函数集 */
80  static const struct blk_mq_ops ramdisk_mq_ops = {
81      /* 请求处理函数指针，blk-mq的入口 */
82      .queue_rq = ramdisk_queue_rq,
83  };
```

关键说明：

- 第21行：标记IO请求开始进入处理流程。
    
- 第24-31行：拒绝透传请求，如SCSI命令。
    
- 第37行：内核标准遍历宏，一个IO请求可能由多段不连续内存组成，循环逐个处理分段数据。
    
- 第43行：sector << 9 即扇区号x512，换算成RAM内存缓冲区的字节偏移地址。
    
- 第46-54行：边界检查，防止越界。
    
- 第59行：读操作，从虚拟磁盘内存拷贝数据到用户IO缓冲区。
    
- 第62行：写操作：用户写入的数据拷贝到内核虚拟磁盘内存。
    
- 第74行：完成请求并通知块层，内核回收本次请求资源。
    
- 第76行：函数总是返回BLK_STS_OK，实际状态通过blk_mq_end_request传递。
    
- 第80-83行：blk-mq操作集，仅提供queue_rq入口，无其他回调。
    

**设备资源初始化函数**

模块加载时初始化硬件资源：分配磁盘内存->初始化锁与计数->配置blk-mq多队列->按内核版本差异化创建gendisk->配置块设备参数->注册设备到内核生成/dev/ram_block。

设备资源初始化函数(位于linux_driver/38_ram_block/ram_block.c)[¶](#id51 "永久链接至代码")

```c
  1  /* 初始化RAM磁盘设备 */
  2  static int __init ramdisk_init_device(struct ramdisk_dev *dev)
  3  {
  4      /* 函数返回值 */
  5      int ret;
  6      /* 硬件队列数量 */
  7      unsigned int hw_queues;
  8
  9      /* 计算设备总大小：MB转换为字节 */
 10      dev->size = RAMDISK_SIZE_MB * 1024 * 1024;
 11      /* 计算设备总容量：总字节数 / 扇区大小 */
 12      dev->capacity = dev->size / KERNEL_SECTOR_SIZE;
 13
 14      /* 分配RAM磁盘数据缓冲区，使用vzalloc分配大内存并清零 */
 15      dev->data = vzalloc(dev->size);
 16      if (!dev->data) {
 17          /* 打印错误信息，显示分配失败的内存大小 */
 18          pr_err("ramdisk: Failed to allocate %zu bytes of memory\n", dev->size);
 19          /* 返回内存不足错误码 */
 20          return -ENOMEM;
 21      }
 22
 23      /* 初始化保护数据的自旋锁 */
 24      spin_lock_init(&dev->lock);
 25      /* 初始化设备引用计数为0 */
 26      atomic_set(&dev->refcnt, 0);
 27
 28      /* 硬件队列数固定等于系统在线CPU数量 */
 29      hw_queues = num_online_cpus();
 30      /* 打印信息，显示使用的硬件队列数量 */
 31      pr_info("ramdisk: Using %u hardware queues\n", hw_queues);
 32
 33      /* 初始化blk-mq标签集结构体，清零所有字段 */
 34      memset(&dev->tag_set, 0, sizeof(dev->tag_set));
 35      /* 设置blk-mq操作函数集 */
 36      dev->tag_set.ops = &ramdisk_mq_ops;
 37      /* 设置硬件队列数量 */
 38      dev->tag_set.nr_hw_queues = hw_queues;
 39      /* 设置每个硬件队列的最大请求深度 */
 40      dev->tag_set.queue_depth = 128;
 41      /* 设置NUMA节点为无特定节点 */
 42      dev->tag_set.numa_node = NUMA_NO_NODE;
 43      /* 设置blk-mq标志：允许请求合并，提高性能 */
 44      dev->tag_set.flags = BLK_MQ_F_SHOULD_MERGE;
 45      /* 设置标签集的驱动私有数据，指向设备结构体 */
 46      dev->tag_set.driver_data = dev;
 47
 48      /* 分配blk-mq标签集资源 */
 49      ret = blk_mq_alloc_tag_set(&dev->tag_set);
 50      if (ret) {
 51          /* 打印错误信息 */
 52          pr_err("ramdisk: Failed to allocate blk-mq tag set\n");
 53          /* 跳转到错误处理，释放已分配的数据缓冲区 */
 54          goto free_data;
 55      }
 56
 57  /* 内核版本判断：Linux 5.14及以上版本使用新API */
 58  #if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 14, 0)
 59      /* 使用blk_mq_alloc_disk一步分配gendisk和请求队列 */
 60      dev->gd = blk_mq_alloc_disk(&dev->tag_set, dev);
 61      if (IS_ERR(dev->gd)) {
 62          /* 获取错误码 */
 63          ret = PTR_ERR(dev->gd);
 64          /* 打印错误信息 */
 65          pr_err("ramdisk: Failed to allocate gendisk\n");
 66          /* 跳转到错误处理，释放已分配的标签集 */
 67          goto free_tag_set;
 68      }
 69
 70  /* 内核版本判断：Linux 4.19-5.13版本使用传统API */
 71  #else
 72      /* 先分配gendisk结构体，参数为支持的次设备号数量 */
 73      dev->gd = alloc_disk(1);
 74      if (!dev->gd) {
 75          /* 打印错误信息 */
 76          pr_err("ramdisk: Failed to allocate gendisk\n");
 77          /* 设置错误码为内存不足 */
 78          ret = -ENOMEM;
 79          /* 跳转到错误处理，释放已分配的标签集 */
 80          goto free_tag_set;
 81      }
 82
 83      /* 初始化blk-mq请求队列 */
 84      dev->gd->queue = blk_mq_init_queue(&dev->tag_set);
 85      if (IS_ERR(dev->gd->queue)) {
 86          /* 获取错误码 */
 87          ret = PTR_ERR(dev->gd->queue);
 88          /* 打印错误信息 */
 89          pr_err("ramdisk: Failed to initialize blk-mq queue\n");
 90          /* 跳转到错误处理，释放已分配的gendisk */
 91          goto put_disk;
 92      }
 93
 94      /* 设置请求队列的私有数据，指向设备结构体 */
 95      dev->gd->queue->queuedata = dev;
 96  #endif
 97
 98      /* 设置gendisk的主设备号 */
 99      dev->gd->major = major_num;
100      /* 设置gendisk的第一个次设备号 */
101      dev->gd->first_minor = 0;
102      /* 设置gendisk支持的次设备号数量 */
103      dev->gd->minors = 1;
104      /* 设置gendisk的块设备操作函数集 */
105      dev->gd->fops = &ramdisk_fops;
106      /* 设置gendisk的私有数据，指向设备结构体 */
107      dev->gd->private_data = dev;
108      /* 设置gendisk的设备名称 */
109      snprintf(dev->gd->disk_name, DISK_NAME_LEN, RAMDISK_NAME);
110
111      /* 设置设备容量 */
112      set_capacity(dev->gd, dev->capacity);
113      /* 设置队列的逻辑块大小 */
114      blk_queue_logical_block_size(dev->gd->queue, KERNEL_SECTOR_SIZE);
115      /* 设置队列的物理块大小 */
116      blk_queue_physical_block_size(dev->gd->queue, KERNEL_SECTOR_SIZE);
117      /* 设置队列支持的最大硬件扇区数 */
118      blk_queue_max_hw_sectors(dev->gd->queue, 1024);
119
120  #if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 15, 0)
121      /* Linux 5.15及以上版本add_disk有返回值 */
122      ret = add_disk(dev->gd);
123      if (ret) {
124          /* 打印错误信息 */
125          pr_err("ramdisk: Failed to add disk: %d\n", ret);
126          /* 跳转到错误处理，释放已分配的gendisk */
127          goto put_disk;
128      }
129  #else
130      /* Linux 4.19-5.14版本add_disk返回void，不会失败 */
131      add_disk(dev->gd);
132
133      /* 设置返回值为成功 */
134      ret = 0;
135  #endif
136
137      /* 打印设备注册成功信息 */
138      pr_info("ramdisk: Device registered successfully\n");
139      /* 打印设备大小信息 */
140      pr_info("ramdisk: Size: %d MB (%zu bytes, %llu sectors)\n",
141          RAMDISK_SIZE_MB, dev->size, (unsigned long long)dev->capacity);
142
143      return 0;
144
145  /* 释放gendisk结构体 */
146  put_disk:
147      put_disk(dev->gd);
148  /* 释放blk-mq标签集 */
149  free_tag_set:
150      blk_mq_free_tag_set(&dev->tag_set);
151  /* 释放RAM数据缓冲区 */
152  free_data:
153      vfree(dev->data);
154
155      return ret;
156  }
```

关键说明：

- 第15行：使用vzalloc分配大块连续虚拟内存并清零。
    
- 第29行：硬件IO队列数量等于CPU核心数，实现多队列并行。
    
- 第49行：向Linux内核申请blk-mq多队列资源。
    
- 第60行：Linux5.14新增API，一步分配gendisk和队列。
    
- 第73、84、95行：旧内核分别调用alloc_disk和blk_mq_init_queue分配gendisk和队列，并手动设置queuedata。
    
- 第112行：向内核上报磁盘总扇区，lsblk、df等命令通过该参数读取磁盘大小。
    
- 第114-118行：设置设备逻辑/物理块大小（512字节）、最大硬件扇区数（1024扇区=512KB）。
    
- 第122、131行：add_disk块设备最终注册函数，调用成功后系统自动生成/dev/ram_block设备文件。
    

**设备资源清理函数**

模块卸载时逆序释放全部资源，防止内存泄漏。

设备资源清理函数(位于linux_driver/38_ram_block/ram_block.c)[¶](#id52 "永久链接至代码")

```c
 1  /* 清理RAM磁盘设备 */
 2  static void ramdisk_cleanup_device(struct ramdisk_dev *dev)
 3  {
 4      /* 检查设备指针是否有效 */
 5      if (!dev)
 6          return;
 7
 8      /* 检查gendisk是否已分配 */
 9      if (dev->gd) {
10          /* 从系统中删除块设备 */
11          del_gendisk(dev->gd);
12  /* 内核版本判断：4.19-5.17版本需要显式清理队列 */
13  #if LINUX_VERSION_CODE < KERNEL_VERSION(5, 18, 0)
14          /* 清理blk-mq请求队列 */
15          blk_cleanup_queue(dev->gd->queue);
16  #endif
17          /* 释放gendisk结构体 */
18          put_disk(dev->gd);
19      }
20
21      /* 释放blk-mq标签集 */
22      blk_mq_free_tag_set(&dev->tag_set);
23
24      /* 检查数据缓冲区是否已分配 */
25      if (dev->data) {
26          /* 释放RAM数据缓冲区 */
27          vfree(dev->data);
28          /* 将指针置空，防止野指针 */
29          dev->data = NULL;
30      }
31
32      /* 释放设备私有数据结构体 */
33      kfree(dev);
34  }
```

关键说明：

- 第11行：从内核设备中注销块设备，/dev/ram_block节点消失。
    
- 第27行：释放vzalloc申请的磁盘缓冲区内存。
    

**模块初始化函数**

模块初始化函数(位于linux_driver/38_ram_block/ram_block.c)[¶](#id53 "永久链接至代码")

```c
 1  /* 模块初始化函数 */
 2  static int __init ramdisk_init(void)
 3  {
 4      /* 函数返回值 */
 5      int ret;
 6      /* 内核版本号的三个组成部分 */
 7      unsigned int major, minor, patch;
 8
 9      /* 从编译时内核版本号中解析主版本号 */
10      major = (LINUX_VERSION_CODE >> 16) & 0xFF;
11      /* 解析次版本号 */
12      minor = (LINUX_VERSION_CODE >> 8) & 0xFF;
13      /* 解析补丁版本号 */
14      patch = LINUX_VERSION_CODE & 0xFF;
15
16      /* 动态分配块设备主设备号 */
17      major_num = register_blkdev(0, RAMDISK_NAME);
18      if (major_num < 0) {
19          /* 打印错误信息 */
20          pr_err("ramdisk: Failed to register block device\n");
21          /* 返回错误码 */
22          return major_num;
23      }
24
25      /* 分配设备私有数据结构体，使用kzalloc分配并清零 */
26      ramdisk_dev = kzalloc(sizeof(struct ramdisk_dev), GFP_KERNEL);
27      if (!ramdisk_dev) {
28          /* 设置错误码为内存不足 */
29          ret = -ENOMEM;
30          /* 跳转到错误处理，注销已分配的主设备号 */
31          goto unregister_blkdev;
32      }
33
34      /* 初始化RAM磁盘设备 */
35      ret = ramdisk_init_device(ramdisk_dev);
36      if (ret) {
37          /* 跳转到错误处理，释放已分配的设备结构体 */
38          goto free_dev;
39      }
40
41      /* 打印模块加载成功信息 */
42      pr_info("ramdisk: Module loaded successfully\n");
43
44      return 0;
45
46  /* 释放设备私有数据结构体 */
47  free_dev:
48      kfree(ramdisk_dev);
49  /* 注销块设备主设备号 */
50  unregister_blkdev:
51      unregister_blkdev(major_num, RAMDISK_NAME);
52
53      return ret;
54  }
```

关键说明：

- 第10-14行：LINUX_VERSION_CODE版本号位于内核源码/include/generated/uapi/linux/version.h，通过内核源码顶层Makefile编译生成，如#define LINUX_VERSION_CODE 393571，393571转16进制为0x60163，对应0x06 01 63分为高、中、低8位，高8位0x06对应十进制6，中间8位0x01对应十进制1，低8位0x63对应十进制99，即6.1.99内核。
    
- 第17行：register_blkdev传入0代表动态随机分配主设备号。
    
- 第26行：kzalloc分配设备私有数据结构体，自动清零。
    

**模块退出函数**

模块退出函数(位于linux_driver/38_ram_block/ram_block.c)[¶](#id54 "永久链接至代码")

```c
/* 模块退出函数 */
static void __exit ramdisk_exit(void)
{
    /* 清理RAM磁盘设备所有资源 */
    ramdisk_cleanup_device(ramdisk_dev);
    /* 注销块设备主设备号 */
    unregister_blkdev(major_num, RAMDISK_NAME);
    /* 打印模块卸载成功信息 */
    pr_info("ramdisk: Module unloaded successfully\n");
}
```

关键说明：

- 第5行：清理设备资源。
    
- 第7行：注销主设备号。
    

### 4.5.2. Makefile说明[¶](#makefile "永久链接至标题")

本节实验使用的Makefile如下所示，编写该Makefile时，只需要根据实际情况修改变量KERNEL_DIR、CROSS_COMPILE和obj-m即可。

Makefile(位于linux_driver/38_ram_block/Makefile)[¶](#id55 "永久链接至代码")

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
17  obj-m := ram_block.o
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

### 4.5.3. 编译驱动[¶](#id32 "永久链接至标题")

在实验目录下输入 `make` 即可编译驱动，编译得到内核模块ram_block.ko。

### 4.5.4. 程序运行结果[¶](#id33 "永久链接至标题")

如出现 `Permission denied` 或类似字样，请注意用户权限，大部分操作硬件外设的功能，几乎都需要root用户权限，简单的解决方案是在执行语句前加入sudo或以root用户运行程序。

#### 4.5.4.1. 实验操作[¶](#id34 "永久链接至标题")

以LubanCat2板卡为例，使用以下命令加载驱动：

```bash
#加载驱动
sudo insmod ram_block.ko

#信息输出如下
[   67.274483] ramdisk: Using 4 hardware queues
[   67.276909] ramdisk: Device registered successfully
[   67.276968] ramdisk: Size: 16 MB (16777216 bytes, 32768 sectors)
[   67.276978] ramdisk: Module loaded successfully
```

可以看到驱动使用了4个硬件队列对应RK3568芯片4核CPU，内存磁盘容量初始化正常，16MB总空间，16777216字节，32768个扇区。

使用以下命令查看虚拟块设备：

```bash
 1  #查看系统所有块设备
 2  lsblk
 3
 4  #信息输出如下
 5  NAME         MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT
 6  mmcblk0      179:0    0  7.3G  0 disk
 7  ├─mmcblk0p1  179:1    0    8M  0 part
 8  ├─mmcblk0p2  179:2    0  128M  0 part /boot
 9  └─mmcblk0p3  179:3    0  7.2G  0 part /
10  mmcblk0boot0 179:32   0    4M  1 disk
11  mmcblk0boot1 179:64   0    4M  1 disk
12  ram_block    252:0    0   16M  0 disk
13
14  #查看磁盘详细信息
15  sudo fdisk -l /dev/ram_block
16
17  #信息输出如下
18  Disk /dev/ram_block: 16 MiB, 16777216 bytes, 32768 sectors
19  Units: sectors of 1 * 512 = 512 bytes
20  Sector size (logical/physical): 512 bytes / 512 bytes
21  I/O size (minimum/optimal): 512 bytes / 512 bytes
```

执行lsblk可正常识别出ram_block 16MB虚拟块设备，与板卡原生MMC磁盘并列展示，设备主设备号252、次设备号0。

执行fdisk可查看到磁盘总容量16MiB、总字节数16777216、总扇区数32768，标准扇区大小512字节，无参数异常。

使用以下命令格式化与挂载测试：

```bash
 1  #格式化为ext4文件系统
 2  sudo mkfs.ext4 /dev/ram_block
 3
 4  #信息输出如下
 5  mke2fs 1.44.5 (15-Dec-2018)
 6  Creating filesystem with 16384 1k blocks and 4096 inodes
 7  Filesystem UUID: fdf23f04-32ff-4f05-bd65-da578d27fd64
 8  Superblock backups stored on blocks:
 9          8193
10
11  Allocating group tables: done
12  Writing inode tables: done
13  Creating journal (1024 blocks): done
14  Writing superblocks and filesystem accounting information: done
15
16  #挂载虚拟磁盘
17  sudo mount /dev/ram_block /mnt/
18
19  #信息输出如下
20  [  718.238154] EXT4-fs (ram_block): mounted filesystem with ordered data mode. Opts: (null)
```

可以看到ram_block虚拟块设备可正常格式化为ext4文件系统，可以被正常挂载。

使用以下命令读写测试：

```bash
#进入挂载目录
cd /mnt/

#写入测试文件
sudo sh -c "echo RAM Block Device Test > test.txt"

#读取测试文件
cat test.txt

#信息打印如下
RAM Block Device Test
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
 8  sudo rmmod ram_block
 9
10  #信息打印如下
11  [  994.557159] ramdisk: Module unloaded successfully
12
13  #查看系统所有块设备
14  lsblk
15
16  #信息打印如下
17  NAME         MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT
18  mmcblk0      179:0    0  7.3G  0 disk
19  ├─mmcblk0p1  179:1    0    8M  0 part
20  ├─mmcblk0p2  179:2    0  128M  0 part /boot
21  └─mmcblk0p3  179:3    0  7.2G  0 part /
22  mmcblk0boot0 179:32   0    4M  1 disk
23  mmcblk0boot1 179:64   0    4M  1 disk
```

驱动卸载后ram_block虚拟块设备消失。

### 4.5.5. 实验注意事项[¶](#id35 "永久链接至标题")

- 内存分配：16MB属于大块内存，必须使用vzalloc分配虚拟连续内存，禁止使用kmalloc，kmalloc仅支持小块内存分配，否则会分配失败。
    
- 扇区大小：Linux系统标准硬件扇区为512字节，修改该宏可能会导致容量错误，磁盘无法识别等。
    
- 内核版本兼容：不同内核gendisk、add_disk、队列初始化API不同，删除版本判断宏会导致编译报错或运行崩溃。
    
- 数据易失性：本实验设备为内存虚拟磁盘，所有数据存储在RAM中，卸载模块、重启设备后数据全部丢失，不可用于持久化数据存储。