原文： https://doc.embedfire.com/linux/rk356x/driver/zh/latest/linux_driver/subsystem_usb_subsystem.html

USB（Universal Serial Bus，通用串行总线）是现代计算机系统中最重要、最普及的外部总线标准之一。 从简单的鼠标、键盘，到高速的存储设备、网络适配器，USB以其热插拔、即插即用、高带宽和统一接口等特性，彻底改变了外设的连接方式。

在Linux内核中，USB子系统是一个庞大且高度模块化的架构。它不仅屏蔽了底层不同主机控制器（如xHCI、EHCI、OHCI）的硬件差异，还为上层驱动开发者提供了一套统一、标准的API。 开发者只需基于内核提供的USB核心框架、结构体、标准API，即可快速开发各类USB外设驱动。

## 5.1. USB基础知识[¶](#usb "永久链接至标题")

### 5.1.1. USB总线拓扑结构[¶](#id1 "永久链接至标题")

USB总线采用主从架构（Host-Device），遵循单向通信原则：仅USB主机（Host）可以主动发起通信，USB设备（Device）只能被动响应主机请求，不存在设备主动上报数据的情况。

标准USB拓扑层级：USB主机控制器 -> USB集线器(Hub) -> 各类USB外设，支持多级Hub级联，单总线最多支持127个USB设备挂载。

### 5.1.2. 端点[¶](#id2 "永久链接至标题")

端点（Endpoint）是USB设备最小通信单元，是设备内存中独立的数据缓冲区，所有USB数据传输都基于端点完成，设备无端点则无法进行数据交互。

端点具有以下特性：

- 每个USB设备拥有多个独立端点，端点编号唯一（0~15）。
    
- 0号端点为设备默认控制端点，所有USB设备强制标配，用于设备枚举、配置、状态查询。
    
- 端点区分传输方向：IN（设备->主机）、OUT（主机->设备）。
    

### 5.1.3. 管道[¶](#id3 "永久链接至标题")

管道（Pipe）是内核抽象的主机与端点的通信通道，由主机端软件维护，绑定固定的设备地址、端点号、传输类型。所有USB数据传输都通过对应的管道完成，内核提供专用API快速创建各类传输管道。

### 5.1.4. USB四种标准传输模式[¶](#id4 "永久链接至标题")

USB协议定义4种传输模式，适配不同外设场景，分别提供对应的URB（USB Request Block，USB通信的基本载体）传输实现：

- **控制传输（Control Transfer）**
    

可靠性最高的传输模式，带校验、重传机制，主要用于设备枚举、参数配置、状态查询、设备控制。0号端点专属传输模式，优先级最高，带宽占用极低。

- **中断传输（Interrupt Transfer）**
    

周期性、低延迟、小数据量传输，主机按固定间隔轮询设备，设备有数据则上报，无数据则空应答。适用于鼠标、键盘、触摸板、游戏手柄等HID设备。

- **批量传输（Bulk Transfer）**
    

无固定周期、大数据量、高可靠性传输，带宽动态分配，优先保障数据完整性，无实时性要求。适用于U盘、移动硬盘、USB网卡等高速数据设备。

- **同步传输（Isochronous Transfer）**
    

周期性、高实时性、允许少量丢包的传输，无重传机制，保障时序稳定。适用于USB摄像头、USB声卡等音视频实时设备。

### 5.1.5. USB设备层级结构[¶](#id5 "永久链接至标题")

Linux内核将USB设备分层抽象，层级从上至下依次为：

![../_images/subsystem_usb_subsystem_0.jpg](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/subsystem_usb_subsystem_0.jpg)

- 设备层（usb_device）：描述整个USB物理设备的全局信息。
    
- 配置层（usb_config_descriptor）：一个设备可以支持多种配置（如高功耗全速模式、低功耗省电模式），系统通常只激活其中一种。
    
- 接口层（usb_interface）：一个配置下可以有多个独立的功能接口。例如，一个USB摄像头设备可能包含一个视频流接口和一个麦克风音频接口。
    
- 端点层（usb_endpoint_descriptor）：每个接口下具体的通信管道，是数据传输的最底层承载者，如IN端点用来传数据给主机，OUT端点用来接收主机数据。
    

Linux内核的 **USB驱动基于接口匹配，而非匹配整个设备** ，这使得一个物理设备可以被多个不同的驱动程序管理。

## 5.2. USB子系统整体架构[¶](#id6 "永久链接至标题")

Linux USB子系统采用三层分层架构，底层适配硬件、中层封装协议、上层提供驱动接口。

![../_images/subsystem_usb_subsystem_1.png](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/subsystem_usb_subsystem_1.png)

- **主机控制器驱动层（HCD层）** ：硬件适配层，负责适配不同厂商的USB主机控制器（OHCI/UHCI/EHCI/XHCI），实现硬件寄存器操作、总线时序、DMA传输、中断处理等硬件底层功能，对上层完全透明，驱动开发者无需关注。
    
- **USB核心层（USB Core）**：作为调度中枢，包含总线管理与设备枚举、设备树拓扑维护、通用API与URB调度、驱动管理以及热插拔事件处理等关键功能。
    
- **设备驱动层（USB Device Driver）**：开发者编写的驱动层级，基于核心层提供的接口开发，无需适配硬件控制器，只需实现设备匹配、设备初始化、数据收发、设备释放四大核心逻辑。
    

## 5.3. USB子系统核心结构体[¶](#id7 "永久链接至标题")

### 5.3.1. USB驱动核心结构体[¶](#id8 "永久链接至标题")

USB驱动核心结构体（struct usb_driver）是USB驱动的管理结构体，用于定义驱动名称、匹配表、设备探测、断开回调等核心回调，是驱动注册的载体。

usb_driver结构体(内核源码/include/linux/usb.h)[¶](#id45 "永久链接至代码")

```c
 1  struct usb_driver {
 2      const char *name;  // 驱动名称，系统唯一标识
 3
 4      // 设备匹配成功回调：设备插入、匹配成功时执行
 5      int (*probe) (struct usb_interface *intf,
 6                  const struct usb_device_id *id);
 7
 8      // 设备断开回调：设备拔出、驱动卸载时执行
 9      void (*disconnect) (struct usb_interface *intf);
10
11      // 设备IO控制回调：处理用户态下发的ioctl命令
12      int (*unlocked_ioctl) (struct usb_interface *intf, unsigned int code,
13                  void *buf);
14
15      // 电源管理回调：设备挂起休眠
16      int (*suspend) (struct usb_interface *intf, pm_message_t message);
17      // 电源管理回调：设备正常唤醒
18      int (*resume) (struct usb_interface *intf);
19      // 复位唤醒回调：USB总线复位后恢复设备状态
20      int (*reset_resume)(struct usb_interface *intf);
21
22      // 总线复位前置回调：复位执行前触发
23      int (*pre_reset)(struct usb_interface *intf);
24      // 总线复位后置回调：复位完成后触发
25      int (*post_reset)(struct usb_interface *intf);
26
27      const struct usb_device_id *id_table;       // 设备匹配表指针
28      const struct attribute_group **dev_groups;  // 设备属性文件组
29
30      struct usb_dynids dynids;             // 动态设备ID链表，内核内部管理
31      struct usbdrv_wrap drvwrap;           // 驱动封装结构体，内核内部使用
32
33      /* 驱动特性位域标志 */
34      unsigned int no_dynamic_id:1;         // 禁止动态添加设备匹配ID
35      unsigned int supports_autosuspend:1;  // 支持设备自动休眠
36      unsigned int disable_hub_initiated_lpm:1; // 禁用集线器发起的低功耗
37      unsigned int soft_unbind:1;           // 启用软解绑模式
38  };
```

### 5.3.2. USB设备结构体[¶](#id9 "永久链接至标题")

USB设备结构体（struct usb_device）用于描述一个完整的USB物理设备，保存设备地址、速度、厂商、版本、总线信息等全局硬件信息。

usb_device结构体(内核源码/include/linux/usb.h)[¶](#id46 "永久链接至代码")

```c
 1  struct usb_device {
 2      /* 设备基础标识 */
 3      int  devnum;             // USB总线设备地址（1-127）
 4      char devpath[16];        // 设备总线路径字符串
 5      enum usb_device_state   state;  // 设备当前状态
 6      enum usb_device_speed   speed;  // 设备传输速度
 7
 8      /* 总线拓扑关联 */
 9      struct usb_device *parent;      // 父设备（上级Hub）
10      struct usb_bus *bus;            // 所属USB总线
11      struct usb_host_endpoint ep0;   // 0号控制端点
12      struct device dev;              // 内嵌标准设备模型
13
14      /* 描述符与配置 */
15      struct usb_device_descriptor descriptor; // 设备标准描述符
16      struct usb_host_config *actconfig;       // 当前激活的配置
17
18      /* 端点资源数组 */
19      struct usb_host_endpoint *ep_in[16];    // 输入端点表
20      struct usb_host_endpoint *ep_out[16];   // 输出端点表
21
22      /* 基础属性字段 */
23      unsigned short bus_mA;          // 总线供电电流上限
24      u8 portnum;                     // 上级Hub端口号
25      u8 level;                       // 总线拓扑层级深度
26
27      /* 常用状态位域 */
28      unsigned can_submit:1;          // 允许提交URB标志
29      unsigned authorized:1;          // 设备已授权
30      unsigned persist_enabled:1;     // 持久化供电使能
31
32      /* 设备字符串信息 */
33      char *product;                  // 产品名称字符串
34      char *manufacturer;             // 厂商名称字符串
35      char *serial;                   // 设备序列号字符串
36      /* 其他成员省略 */
37  };
```

### 5.3.3. USB接口结构体[¶](#id10 "永久链接至标题")

USB接口结构体（struct usb_interface）是内核驱动匹配、绑定、操作的核心对象，一个设备多个接口可对应多个驱动。

usb_interface结构体(内核源码/include/linux/usb.h)[¶](#id47 "永久链接至代码")

```c
 1  struct usb_interface {
 2      /* 接口配置集合：所有备选设置，无固定顺序 */
 3      struct usb_host_interface *altsetting;
 4      /* 当前激活生效的备选配置 */
 5      struct usb_host_interface *cur_altsetting;
 6      /* 备选配置的总数量 */
 7      unsigned num_altsetting;
 8
 9      /* 接口关联描述符：复合设备多接口分组使用 */
10      struct usb_interface_assoc_descriptor *intf_assoc;
11
12      /* 接口绑定的次设备号 */
13      int minor;
14      /* 接口绑定运行状态 */
15      enum usb_interface_condition condition;
16
17      /* 接口状态位域 */
18      unsigned unregistering:1;       /* 接口正在注销 */
19      unsigned needs_remote_wakeup:1; /* 驱动要求远程唤醒功能 */
20      unsigned authorized:1;          /* 接口已授权可用 */
21
22      /* 设备模型成员 */
23      struct device dev;          /* 接口专属设备对象 */
24      struct device *usb_dev;     /* 所属USB设备指针 */
25      /* 其他成员省略 */
26  };
```

### 5.3.4. USB接口配置结构体[¶](#id11 "永久链接至标题")

USB接口配置结构体（struct usb_host_interface）用于保存接口详细描述信息与端点列表，是probe函数中解析设备资源的核心结构体。

usb_host_interface结构体(内核源码/include/linux/usb.h)[¶](#id48 "永久链接至代码")

```c
struct usb_host_interface {
    struct usb_interface_descriptor desc;   // 接口标准描述符

    int extralen;                    // 扩展描述符总长度
    unsigned char *extra;            // 扩展描述符原始数据

    /* 接口关联的端点数组，数量等于desc.bNumEndpoints，无固定顺序 */
    struct usb_host_endpoint *endpoint;

    char *string;                    // 接口字符串描述，iInterface对应内容
};
```

### 5.3.5. USB端点描述符结构体[¶](#id12 "永久链接至标题")

USB端点描述符结构体（struct usb_endpoint_descriptor）用于描述端点属性，包含端点地址、传输类型、最大包长、传输间隔等核心通信参数。

usb_endpoint_descriptor结构体(内核源码/include/uapi/linux/usb/ch9.h)[¶](#id49 "永久链接至代码")

```c
 1  struct usb_endpoint_descriptor {
 2      __u8  bLength;              // 描述符总长度
 3      __u8  bDescriptorType;      // 描述符类型
 4
 5      __u8  bEndpointAddress;     // 端点地址：bit7为方向，低4位为端点号
 6      __u8  bmAttributes;         // 端点属性：传输类型、同步模式等
 7      __le16 wMaxPacketSize;      // 单次最大数据包长度
 8      __u8  bInterval;            // 传输轮询间隔
 9
10      /* 仅音频类端点有效，常规外设无需使用 */
11      __u8  bRefresh;             // 刷新速率
12      __u8  bSynchAddress;        // 同步端点地址
13  } __attribute__ ((packed));
```

### 5.3.6. USB设备匹配表结构体[¶](#id13 "永久链接至标题")

USB设备匹配表结构体（struct usb_device_id）用于告诉内核当前驱动支持的USB设备类型，是驱动与设备匹配的依据，支持按类、子类、协议、VID/PID等多种方式匹配。

usb_device_id结构体(内核源码/include/linux/mod_devicetable.h)[¶](#id50 "永久链接至代码")

```c
 1  struct usb_device_id {
 2      /* 匹配控制字段 */
 3      __u16   match_flags;    // 匹配标志位，指定启用哪些匹配规则
 4
 5      /* 产品级匹配字段：按VID/PID/固件版本范围精准匹配 */
 6      __u16   idVendor;       // 设备厂商ID(VID)
 7      __u16   idProduct;      // 设备产品ID(PID)
 8      __u16   bcdDevice_lo;   // 设备固件版本最低值
 9      __u16   bcdDevice_hi;   // 设备固件版本最高值
10
11      /* 设备类匹配字段：设备维度的类协议匹配 */
12      __u8    bDeviceClass;       // 设备大类
13      __u8    bDeviceSubClass;    // 设备子类
14      __u8    bDeviceProtocol;    // 设备协议
15
16      /* 接口类匹配字段：接口维度的类协议匹配 */
17      __u8    bInterfaceClass;    // 接口大类
18      __u8    bInterfaceSubClass; // 接口子类
19      __u8    bInterfaceProtocol; // 接口协议
20
21      /* 接口号匹配：厂商自定义场景使用 */
22      __u8    bInterfaceNumber;   // 指定接口号匹配
23
24      /* 驱动私有信息，不参与设备匹配 */
25      kernel_ulong_t  driver_info
26          __attribute__((aligned(sizeof(kernel_ulong_t))));
27  };
```

### 5.3.7. USB请求块结构体[¶](#id14 "永久链接至标题")

USB请求块结构体（struct urb）是USB子系统数据传输核心单元，所有USB数据收发都必须通过URB完成，用于封装传输缓冲区、长度、回调、管道等信息。

urb结构体(内核源码/include/linux/usb.h)[¶](#id51 "永久链接至代码")

```c
 1  struct urb {
 2      /* 内核与主机控制器私有：驱动开发一般不直接操作 */
 3      struct kref kref;           /* URB引用计数 */
 4      int unlinked;               /* 取消链接错误码 */
 5      void *hcpriv;               /* 主机控制器私有数据 */
 6
 7      /* 驱动可操作的公共字段 */
 8      struct usb_device *dev;     /* 绑定的USB设备 */
 9      unsigned int pipe;          /* 通信管道信息 */
10      int status;                 /* 传输完成状态 */
11      unsigned int transfer_flags;/* 传输属性标志位 */
12      void *transfer_buffer;      /* 数据传输虚拟缓冲区 */
13      dma_addr_t transfer_dma;    /* 数据传输DMA地址 */
14      u32 transfer_buffer_length; /* 缓冲区总长度 */
15      u32 actual_length;          /* 实际传输数据长度 */
16      int interval;               /* 中断/同步传输轮询间隔 */
17      void *context               /* 完成回调私有上下文 */
18      usb_complete_t complete;    /* 传输完成回调函数 */
19
20      /* 仅同步传输使用，普通外设驱动无需关注 */
21      struct usb_iso_packet_descriptor iso_frame_desc[];
22      /* 其他成员省略 */
23  };
```

## 5.4. USB子系统核心函数[¶](#id15 "永久链接至标题")

### 5.4.1. 注册USB驱动[¶](#id16 "永久链接至标题")

#### 5.4.1.1. usb_register函数[¶](#usb-register "永久链接至标题")

usb_register函数用于将自定义USB驱动结构体注册到内核USB子系统，注册成功后内核可识别该驱动，用于匹配对应USB设备。

函数原型：

```c
int usb_register(struct usb_driver *driver);
```

参数说明：

- driver：初始化完成的usb_driver驱动结构体指针。
    

返回值：成功返回0；失败返回负错误码。

### 5.4.2. 注销USB驱动[¶](#id17 "永久链接至标题")

#### 5.4.2.1. usb_deregister函数[¶](#usb-deregister "永久链接至标题")

usb_deregister函数用于从内核USB子系统注销驱动，释放驱动占用的内核资源，模块卸载时必须调用。

函数原型：

```c
void usb_deregister(struct usb_driver *driver);
```

参数说明：

- driver：待注销的usb_driver驱动结构体指针
    

### 5.4.3. 分配URB结构体[¶](#urb "永久链接至标题")

#### 5.4.3.1. usb_alloc_urb函数[¶](#usb-alloc-urb "永久链接至标题")

usb_alloc_urb函数用于动态分配URB内存结构体，是所有USB数据传输的前置操作。

函数原型：

```c
struct urb *usb_alloc_urb(int iso_packets, gfp_t mem_flags);
```

参数说明：

- iso_packets：同步传输包数量，非同步传输固定填0。
    
- mem_flags：内存分配标志，常规使用GFP_KERNEL、GFP_ATOMIC。
    

返回值：成功返回URB指针；失败返回NULL。

### 5.4.4. 释放URB结构体[¶](#id18 "永久链接至标题")

#### 5.4.4.1. usb_free_urb函数[¶](#usb-free-urb "永久链接至标题")

usb_free_urb函数用于释放已分配的URB结构体内存，设备卸载时必须调用，防止内存泄漏。

函数原型：

```c
void usb_free_urb(struct urb *urb);
```

参数说明：

- urb：待释放的URB结构体指针。
    

### 5.4.5. 初始化中断传输URB[¶](#id19 "永久链接至标题")

#### 5.4.5.1. usb_fill_int_urb函数[¶](#usb-fill-int-urb "永久链接至标题")

usb_fill_int_urb函数用于快速初始化中断传输类型URB，适配HID设备等周期性小数据传输场景。

函数原型：

```c
static inline void usb_fill_int_urb(struct urb *urb,
                                    struct usb_device *dev,
                                    unsigned int pipe,
                                    void *transfer_buffer,
                                    int buffer_length,
                                    usb_complete_t complete_fn,
                                    void *context,
                                    int interval);
```

参数说明：

- urb：待初始化的URB指针。
    
- dev：绑定的USB设备结构体。
    
- pipe：USB通信管道（由usb_rcvintpipe创建）。
    
- transfer_buffer：数据传输缓冲区。
    
- buffer_length：缓冲区长度。
    
- complete_fn：传输完成回调函数。
    
- context：回调函数私有上下文数据。
    
- interval：中断传输轮询间隔（ms）。
    

返回值：无返回值。

### 5.4.6. 提交URB传输请求[¶](#id20 "永久链接至标题")

#### 5.4.6.1. usb_submit_urb函数[¶](#usb-submit-urb "永久链接至标题")

usb_submit_urb函数用于将初始化完成的URB提交给USB核心层，启动数据传输，是数据收发的最终执行接口。

函数原型：

```c
int usb_submit_urb(struct urb *urb, gfp_t mem_flags);
```

参数说明：

- urb：已初始化完成的URB指针。
    
- mem_flags：内存分配标志，中断上下文必须用GFP_ATOMIC。
    

返回值：成功返回0；失败返回负错误码。

### 5.4.7. 强制终止URB传输[¶](#id21 "永久链接至标题")

#### 5.4.7.1. usb_kill_urb函数[¶](#usb-kill-urb "永久链接至标题")

usb_kill_urb函数用于强制终止正在排队或传输的URB，阻塞等待URB彻底停止，设备断开、驱动卸载时使用，安全释放传输资源。

函数原型：

```c
void usb_kill_urb(struct urb *urb);
```

参数说明：

- urb：需要终止的URB指针。
    

### 5.4.8. 分配USB DMA一致性缓冲区[¶](#usb-dma "永久链接至标题")

#### 5.4.8.1. usb_alloc_coherent函数[¶](#usb-alloc-coherent "永久链接至标题")

usb_alloc_coherent函数用于分配USB专用DMA一致性内存，解决内核虚拟地址与硬件DMA物理地址映射问题，避免数据缓存不一致。

函数原型：

```c
void *usb_alloc_coherent(struct usb_device *dev, size_t size, gfp_t flag, dma_addr_t *dma);
```

参数说明：

- dev：目标USB设备。
    
- size：需要分配的缓冲区大小。
    
- flag：内存分配标志。
    
- dma：输出参数，返回缓冲区物理DMA地址。
    

返回值：成功返回虚拟缓冲区地址；失败返回NULL。

### 5.4.9. 释放USB DMA缓冲区[¶](#id22 "永久链接至标题")

#### 5.4.9.1. usb_free_coherent函数[¶](#usb-free-coherent "永久链接至标题")

usb_free_coherent函数用于释放usb_alloc_coherent分配的DMA缓冲区，必须成对调用。

函数原型：

```c
void usb_free_coherent(struct usb_device *dev, size_t size, void *addr, dma_addr_t dma);
```

参数说明：

- dev：绑定的USB设备。
    
- size：缓冲区大小。
    
- addr：虚拟地址指针。
    
- dma：物理DMA地址。
    

### 5.4.10. 获取端点最大数据包长度[¶](#id23 "永久链接至标题")

#### 5.4.10.1. usb_maxpacket函数[¶](#usb-maxpacket "永久链接至标题")

usb_maxpacket函数用于根据指定管道获取对应端点支持的最大数据包长度，是URB缓冲区大小配置的依据。

函数原型：

```c
u16 usb_maxpacket(struct usb_device *dev, unsigned int pipe, int out);
```

参数说明：

- dev：目标USB设备结构体。
    
- pipe：USB通信管道。
    
- out：传输方向标志，1表示输出管道，0表示输入管道。
    

返回值：返回端点支持的最大数据包字节数。

### 5.4.11. 判断是否为中断输入端点[¶](#id24 "永久链接至标题")

#### 5.4.11.1. usb_endpoint_is_int_in函数[¶](#usb-endpoint-is-int-in "永久链接至标题")

usb_endpoint_is_int_in函数用于判断端点描述符是否为中断传输类型的输入端点，probe阶段遍历端点、筛选可用端点时常用。

函数原型：

```c
static inline int usb_endpoint_is_int_in(const struct usb_endpoint_descriptor *epd);
```

参数说明：

- epd：待判断的端点描述符指针。
    

返回值：非0表示是中断输入端点；0表示不是。

### 5.4.12. 填充输入子系统设备ID[¶](#id "永久链接至标题")

#### 5.4.12.1. usb_to_input_id函数[¶](#usb-to-input-id "永久链接至标题")

usb_to_input_id函数用于将USB设备的VID、PID、版本号等信息自动填充到输入子系统的input_id结构体中，USB输入类设备驱动注册input设备时通用。

函数原型：

```c
void usb_to_input_id(const struct usb_device *dev, struct input_id *id);
```

参数说明：

- dev：USB设备结构体。
    
- id：输出参数，待填充的输入子系统ID结构体。
    

### 5.4.13. 管道创建内联函数[¶](#id25 "永久链接至标题")

管道本质是内核编码的整型值，封装了设备地址、端点号、传输类型与传输方向，驱动无需手动位运算，调用内联函数即可生成合法通信管道。

函数原型：

```c
// 创建中断输入管道
static inline unsigned int usb_rcvintpipe(struct usb_device *dev, __u8 endpoint);

// 创建批量输入管道
static inline unsigned int usb_rcvbulkpipe(struct usb_device *dev, __u8 endpoint);

// 创建批量输出管道
static inline unsigned int usb_sndbulkpipe(struct usb_device *dev, __u8 endpoint);
```

函数说明：

- 所有命名均以主机视角定义：rcv表示主机接收数据，对应设备IN端点；snd表示主机发送数据，对应设备OUT端点。
    
- 参数endpoint直接传入端点描述符的bEndpointAddress原值即可，会自动解析端点号与方向属性。
    

管道类型必须与端点实际传输类型匹配，中断端点使用int系列宏，批量端点使用bulk系列宏，混用会导致URB提交失败。

## 5.5. USB子系统相关宏定义[¶](#id26 "永久链接至标题")

### 5.5.1. 端点类型宏定义[¶](#id27 "永久链接至标题")

```c
#define USB_ENDPOINT_XFER_CONTROL   0x00    // 控制传输
#define USB_ENDPOINT_XFER_ISOC      0x01    // 同步传输
#define USB_ENDPOINT_XFER_BULK      0x02    // 批量传输
#define USB_ENDPOINT_XFER_INT       0x03    // 中断传输
```

## 5.6. USB鼠标和键盘驱动实验[¶](#id28 "永久链接至标题")

本实验驱动基于Linux内核标准USB子系统、HID协议、输入子系统框架开发，单独实现USB设备探测、中断URB传输、HID报文解析、输入事件上报流程， 支持标准按键、鼠标位移、滚轮、侧键功能，实现纯内核态USB鼠标、键盘驱动。

本章的示例代码目录为： **linux_driver/39_usb_mouse_keyboard**

### 5.6.1. USB HID键鼠通信协议详解[¶](#usb-hid "永久链接至标题")

USB HID（Human Interface Device，人机接口设备）协议是USB总线专为输入类外设定义的上层协议标准，本驱动基于HID Boot Protocol（引导协议）开发， 区别于高级报告协议，引导协议拥有固定长度、固定字段的标准化报文，无需解析复杂报告描述符，适配性更强，是嵌入式Linux原生键鼠驱动的核心协议。

#### 5.6.1.1. HID设备层级[¶](#id29 "永久链接至标题")

USB键鼠设备遵循“USB总线->接口->端点->HID报文”通信架构：

- 总线层：遵循USB2.0全速协议（12Mbps），键鼠默认工作在全速模式；
    
- 接口层：设备上报HID类（Class=03）、引导子类（SubClass=01），区分鼠标/键盘协议；
    
- 端点层：仅配置1个中断输入端点（INT IN），无输出端点，设备单向上报数据；
    
- 报文层：基于中断传输，按固定周期上报标准化HID状态报文。
    

#### 5.6.1.2. USB键盘HID引导协议[¶](#usbhid "永久链接至标题")

##### 5.6.1.2.1. 报文结构[¶](#id30 "永久链接至标题")

标准引导协议键盘固定上报8字节数据帧，长度固定：

   
|字节偏移|字段名称|数据类型|功能说明|
|---|---|---|---|
|Byte 0|修饰键状态|8bit位|存储Ctrl/Shift/Alt/Win等组合键状态，1=按下，0=释放|
|Byte 1|保留字节|固定0x00|协议预留，无实际业务含义，驱动直接忽略|
|Byte 2~Byte 7|普通按键码数组|HID键码（1字节/个）|最多存储6个同时按下的普通按键，0x00表示空位无按键|

其中Byte 0共8个有效位，按位绑定对应修饰键，位序固定：

- BIT0：左Ctrl
    
- BIT1：左Shift
    
- BIT2：左Alt
    
- BIT3：左Win键
    
- BIT4：右Ctrl
    
- BIT5：右Shift
    
- BIT6：右Alt
    
- BIT7：右Win键
    

普通按键码规则：

- 取值范围：0x0~0x73，为USB HID协会标准化按键码；
    
- 空位标识：数组中0x00代表该位置无按键按下；
    
- 同时按键限制：Byte2-Byte7共6个位置，硬件层面限制最多6键同时按下，超出按键设备不会上报；
    
- 状态变更逻辑：按键按下时，键码填充至数组空位；按键释放时，对应位置重置为0x00。
    
- 按键状态判定：键盘无主动释放通知，驱动必须通过前后两次报文对比判定状态。新报文出现旧报文无的键码即按键按下；旧报文存在、新报文消失的键码即按键释放。
    

举例：按键A按下完整报文解析标准HID键码：按键A对应的USB HID原生键码为0x04； 仅按下键盘A键，无任何修饰键时，完整8字节上报报文：[0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00]，报文拆解如下：

- Byte0 = 0x00：所有修饰键未按下，全0；
    
- Byte1 = 0x00：协议保留字节，固定为0；
    
- Byte2 = 0x04：普通按键数组首位填入A键HID键码，标记A键按下；
    
- Byte3~Byte7 = 0x00：其余5个按键空位无按键按下；
    
- 处理逻辑：驱动读取Byte2=0x04，查询映射表，将0x04转换为Linux内核键码KEY_A，上报按键按下事件；
    
- 按键释放：松开A键后，设备上报报文变为 [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]，驱动通过新旧报文对比检测到A键消失，上报KEY_A释放事件。
    

#### 5.6.1.3. USB鼠标HID引导协议[¶](#id31 "永久链接至标题")

##### 5.6.1.3.1. 报文结构[¶](#id32 "永久链接至标题")

带滚轮标准鼠标固定上报4字节数据帧，仅包含按键与相对位移信息，无绝对坐标：

    
|字节偏移|字段名称|数据类型|取值范围|功能说明|
|---|---|---|---|---|
|Byte 0|鼠标按键位|8bit位|0x00~0x1F|5个有效按键位，其余保留|
|Byte 1|X轴相对位移|有符号int8_t|-127 ~ +127|正值向右，负值向左|
|Byte 2|Y轴相对位移|有符号int8_t|-127 ~ +127|正值向下，负值向上|
|Byte 3|滚轮相对位移|有符号int8_t|-127 ~ +127|正值上滚，负值下滚|

其中Byte 0定义如下：

- BIT0：左键（BTN_LEFT）
    
- BIT1：右键（BTN_RIGHT）
    
- BIT2：中键/滚轮按键（BTN_MIDDLE）
    
- BIT3：侧键1/前进键（BTN_SIDE）
    
- BIT4：侧键2/后退键（BTN_EXTRA）
    
- BIT5~BIT7：硬件保留位，标准值为0
    

相对位移特性：

- 无绝对坐标：鼠标上报的是移动增量，而非屏幕坐标，光标位置由系统累加增量计算；
    
- 数值范围限制：单帧最大位移±127，快速移动时设备会拆分多帧连续上报；
    
- 滚轮逻辑：仅支持纵向滚动，无横向滚轮字段，横向滚轮属于拓展报告协议。
    

#### 5.6.1.4. 中断传输机制[¶](#id33 "永久链接至标题")

USB键鼠不采用批量传输或控制传输，统一使用中断输入端点传输，是低延迟、低开销的传输方案：

- 轮询周期：端点描述符定义固定轮询间隔，标准键鼠默认10ms，保证输入实时性；
    
- 数据上报规则：设备状态变化时，下一轮询周期立即上报新报文；无状态变化时，重复上报当前状态报文；
    
- URB循环机制：主机通过提交中断URB等待数据，回调处理完成后必须重新提交URB，才能持续监听下一轮数据；
    
- 错误处理：传输超时、设备断开时终止URB重提，非致命错误自动重提URB恢复监听。
    

### 5.6.2. 驱动代码详解[¶](#id34 "永久链接至标题")

**枚举、宏定义与键码映射表**

定义设备类型、通信报文长度、键鼠键码映射关系，是驱动数据解析的基础。

枚举、宏定义与键码映射表(位于linux_driver/39_usb_mouse_keyboard/usb_mouse_keyboard.c)[¶](#id52 "永久链接至代码")

```c
 1  /* 设备类型枚举 */
 2  enum hid_device_type {
 3      DEVICE_TYPE_MOUSE,    /* 鼠标设备类型 */
 4      DEVICE_TYPE_KEYBOARD  /* 键盘设备类型 */
 5  };
 6
 7  /* 键盘相关常量 */
 8  #define KEYBOARD_REPORT_SIZE 8  /* 标准USB键盘报告长度为8字节 */
 9  #define MAX_KEYS 6              /* 标准USB键盘支持最多6键同时按下 */
10
11  /* 鼠标相关常量 */
12  #define MOUSE_REPORT_SIZE 8     /* 标准USB鼠标报告最大长度为8字节 */
13
14  /************************** 键盘功能相关代码 **************************/
15
16  /* USB HID键盘按键码到Linux输入子系统键码的转换表
17  * 索引: USB HID标准按键码(0x00-0x73)
18  * 值: Linux输入子系统定义的键码(KEY_*系列宏)
19  */
20  static const unsigned char usb_keycode_map[256] = {
21      KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_A, KEY_B,
22      KEY_C, KEY_D, KEY_E, KEY_F, KEY_G, KEY_H, KEY_I, KEY_J, KEY_K, KEY_L,
23      KEY_M, KEY_N, KEY_O, KEY_P, KEY_Q, KEY_R, KEY_S, KEY_T, KEY_U, KEY_V,
24      KEY_W, KEY_X, KEY_Y, KEY_Z, KEY_1, KEY_2, KEY_3, KEY_4, KEY_5, KEY_6,
25      KEY_7, KEY_8, KEY_9, KEY_0, KEY_ENTER, KEY_ESC, KEY_BACKSPACE,
26      KEY_TAB, KEY_SPACE, KEY_MINUS, KEY_EQUAL, KEY_LEFTBRACE,
27      KEY_RIGHTBRACE, KEY_BACKSLASH, KEY_BACKSLASH, KEY_SEMICOLON,
28      KEY_APOSTROPHE, KEY_GRAVE, KEY_COMMA, KEY_DOT, KEY_SLASH,
29      KEY_CAPSLOCK, KEY_F1, KEY_F2, KEY_F3, KEY_F4, KEY_F5, KEY_F6,
30      KEY_F7, KEY_F8, KEY_F9, KEY_F10, KEY_F11, KEY_F12, KEY_SYSRQ,
31      KEY_SCROLLLOCK, KEY_PAUSE, KEY_INSERT, KEY_HOME, KEY_PAGEUP,
32      KEY_DELETE, KEY_END, KEY_PAGEDOWN, KEY_RIGHT, KEY_LEFT, KEY_DOWN,
33      KEY_UP, KEY_NUMLOCK, KEY_KPSLASH, KEY_KPASTERISK, KEY_KPMINUS,
34      KEY_KPPLUS, KEY_KPENTER, KEY_KP1, KEY_KP2, KEY_KP3, KEY_KP4, KEY_KP5,
35      KEY_KP6, KEY_KP7, KEY_KP8, KEY_KP9, KEY_KP0, KEY_KPDOT, KEY_102ND,
36      KEY_COMPOSE, KEY_POWER, KEY_KPEQUAL, KEY_F13, KEY_F14, KEY_F15,
37      KEY_F16, KEY_F17, KEY_F18, KEY_F19, KEY_F20, KEY_F21, KEY_F22,
38      KEY_F23, KEY_F24, KEY_OPEN, KEY_HELP, KEY_PROPS, KEY_FRONT, KEY_STOP,
39      KEY_AGAIN, KEY_UNDO, KEY_CUT, KEY_COPY, KEY_PASTE, KEY_FIND, KEY_MUTE,
40      KEY_VOLUMEUP, KEY_VOLUMEDOWN, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
41      KEY_KPCOMMA, KEY_RESERVED, KEY_RO, KEY_KATAKANAHIRAGANA , KEY_YEN,
42      KEY_HENKAN, KEY_MUHENKAN, KEY_KPJPCOMMA, KEY_RESERVED, KEY_RESERVED,
43      KEY_RESERVED, KEY_HANGEUL, KEY_HANJA, KEY_KATAKANA, KEY_HIRAGANA,
44      KEY_ZENKAKUHANKAKU, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
45      KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
46      KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
47      KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
48      KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
49      KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
50      KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
51      KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
52      KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
53      KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
54      KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
55      KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
56      KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
57      KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
58      KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
59      KEY_RESERVED, KEY_RESERVED, KEY_LEFTCTRL, KEY_LEFTSHIFT, KEY_LEFTALT,
60      KEY_LEFTMETA, KEY_RIGHTCTRL, KEY_RIGHTSHIFT, KEY_RIGHTALT,
61      KEY_RIGHTMETA, KEY_PLAYPAUSE, KEY_STOPCD, KEY_PREVIOUSSONG,
62      KEY_NEXTSONG, KEY_EJECTCD, KEY_VOLUMEUP, KEY_VOLUMEDOWN, KEY_MUTE,
63      KEY_WWW, KEY_BACK, KEY_FORWARD, KEY_STOP, KEY_FIND, KEY_SCROLLUP,
64      KEY_SCROLLDOWN, KEY_EDIT, KEY_SLEEP, KEY_SCREENLOCK, KEY_REFRESH,
65      KEY_CALC, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED
66  };
67
68  /* 修饰键映射表，将USB报告中的修饰键位映射到Linux输入子系统键码
69  * 索引: USB报告第一个字节的位位置(0-7)
70  * 值: Linux输入子系统定义的键码(KEY_*系列宏)
71  */
72  static const unsigned char modifier_map[8] = {
73      KEY_LEFTCTRL, KEY_LEFTSHIFT, KEY_LEFTALT, KEY_LEFTMETA,
74      KEY_RIGHTCTRL, KEY_RIGHTSHIFT, KEY_RIGHTALT, KEY_RIGHTMETA
75  };
```

关键说明：

- 第2-5行：定义设备类型枚举，用于后续鼠标、键盘差异化初始化、差异化中断回调绑定。
    
- 第8-12行：宏定义遵循USB HID引导协议标准，键盘固定8字节报告、最多6键同按，鼠标最大8字节报告。
    
- 第20-66行：usb_keycode_map映射表，将USB标准HID键码转换为Linux内核输入子系统识别的KEY_*键码，是按键上报的依据。
    
- 第72-75行：修饰键映射表，专门适配Ctrl/Shift/Alt/Win等修饰键，按USB报告字节位序一一映射，实现组合键识别。
    

**驱动私有数据结构体**

该结构体统一封装键鼠驱动所有硬件资源、设备状态、私有数据，实现设备资源的集中管理。

驱动私有数据结构体(位于linux_driver/39_usb_mouse_keyboard/usb_mouse_keyboard.c)[¶](#id53 "永久链接至代码")

```c
 1  /* 驱动私有数据结构体 */
 2  struct usb_hid_device {
 3      struct usb_device *udev;          /* 指向USB设备对象的指针*/
 4      struct input_dev *input;          /* 指向输入设备对象的指针 */
 5      struct urb *irq_urb;              /* 指向中断URB的指针，用于接收设备的中断传输数据 */
 6      unsigned char *data;              /* DMA缓冲区的虚拟地址，存储设备发送的数据 */
 7      dma_addr_t data_dma;              /* DMA缓冲区的物理地址，供USB控制器直接访问 */
 8      char name[64];                    /* 设备名称 */
 9      char phys[64];                    /* 设备物理路径 */
10      enum hid_device_type type;        /* 设备类型，标记是鼠标还是键盘 */
11      int interface_num;                /* 当前设备对应的USB接口号 */
12
13      /* 键盘专用 */
14      unsigned char old_keys[MAX_KEYS]; /* 保存上一次的按键状态，用于检测按键释放 */
15      unsigned char old_modifiers;      /* 保存上一次的修饰键(Ctrl/Shift等)状态 */
16
17      /* 鼠标专用 */
18      int has_extra_buttons;            /* 标记鼠标是否支持额外侧键 */
19  };
```

关键说明：

- 第3行：struct usb_device指针，绑定USB底层设备，用于后续URB提交、DMA内存分配。
    
- 第4行：struct input_dev指针，绑定内核输入设备，用于向系统上报按键、位移事件。
    
- 第5行：中断URB结构体指针，是USB中断传输的载体，负责接收设备主动上报的数据。
    
- 第6-7行：DMA一致性缓冲区的虚拟地址与物理地址，供USB控制器硬件直接访问，降低CPU拷贝开销。
    
- 第14-15行：键盘历史状态缓存，保存上一次按键、修饰键状态，用于检测按下与释放事件。
    

**设备探测函数**

USB设备插入时内核自动调用，完成设备校验、资源分配、设备初始化、URB提交、设备注册流程。

设备探测函数(位于linux_driver/39_usb_mouse_keyboard/usb_mouse_keyboard.c)[¶](#id54 "永久链接至代码")

```c
  1  /* 设备探测函数 */
  2  static int usb_hid_probe(struct usb_interface *intf,
  3                          const struct usb_device_id *id)
  4  {
  5      /* 从接口获取对应的USB设备指针 */
  6      struct usb_device *udev = interface_to_usbdev(intf);
  7      /* 指向当前激活的接口设置描述符 */
  8      struct usb_host_interface *iface_desc;
  9      /* 指向端点描述符的指针 */
 10      struct usb_endpoint_descriptor *endpoint;
 11      /* 指向自定义的HID设备结构体 */
 12      struct usb_hid_device *hid_dev;
 13      /* 指向输入设备结构体 */
 14      struct input_dev *input_dev;
 15      /* USB中断接收管道号 */
 16      int pipe;
 17      /* 端点支持的最大数据包大小 */
 18      int maxp;
 19      /* 错误码变量 */
 20      int error;
 21      /* 循环计数器变量 */
 22      int i;
 23
 24      /* 获取当前接口的激活设置描述符 */
 25      iface_desc = intf->cur_altsetting;
 26
 27      /* 基础协议检查：验证是否为HID类引导子类设备 */
 28      if (iface_desc->desc.bInterfaceClass != USB_INTERFACE_CLASS_HID |
 29          iface_desc->desc.bInterfaceSubClass != USB_INTERFACE_SUBCLASS_BOOT) {
 30          return -ENODEV;
 31      }
 32
 33      /* 检查接口端点数量：标准HID引导设备只有一个中断输入端点 */
 34      if (iface_desc->desc.bNumEndpoints != 1)
 35          return -ENODEV;
 36
 37      /* 获取第一个也是唯一一个端点的描述符 */
 38      endpoint = &iface_desc->endpoint[0].desc;
 39      /* 检查该端点是否为中断输入端点 */
 40      if (!usb_endpoint_is_int_in(endpoint))
 41          return -ENODEV;
 42
 43      /* 分配通用HID设备结构体的内存，并初始化为0 */
 44      hid_dev = kzalloc(sizeof(struct usb_hid_device), GFP_KERNEL);
 45      if (!hid_dev)
 46          return -ENOMEM;
 47
 48      /* 分配输入设备结构体 */
 49      input_dev = input_allocate_device();
 50      if (!input_dev)
 51          goto fail_free_hid_dev;
 52
 53      /* 设置USB设备指针 */
 54      hid_dev->udev = udev;
 55      /* 设置输入设备指针 */
 56      hid_dev->input = input_dev;
 57      /* 保存当前接口号，用于后续控制传输 */
 58      hid_dev->interface_num = iface_desc->desc.bInterfaceNumber;
 59
 60      /* 根据接口协议类型区分是鼠标还是键盘设备 */
 61      if (iface_desc->desc.bInterfaceProtocol == USB_INTERFACE_PROTOCOL_MOUSE) {
 62          /* 设置设备类型为鼠标 */
 63          hid_dev->type = DEVICE_TYPE_MOUSE;
 64          /* 格式化鼠标设备名称 */
 65          snprintf(hid_dev->name, sizeof(hid_dev->name), "USB Mouse");
 66
 67          /* 默认支持额外侧键 */
 68          hid_dev->has_extra_buttons = 1;
 69
 70          /* 设置鼠标输入设备支持的事件类型：按键事件和相对坐标事件 */
 71          input_dev->evbit[0] = BIT_MASK(EV_KEY) | BIT_MASK(EV_REL);
 72          /* 设置鼠标支持的按键：左键、右键、中键、侧键1、侧键2 */
 73          input_dev->keybit[BIT_WORD(BTN_MOUSE)] =
 74              BIT_MASK(BTN_LEFT) | BIT_MASK(BTN_RIGHT) | BIT_MASK(BTN_MIDDLE) |
 75              BIT_MASK(BTN_SIDE) | BIT_MASK(BTN_EXTRA);
 76          /* 设置鼠标支持的相对坐标：X轴和Y轴 */
 77          input_dev->relbit[0] = BIT_MASK(REL_X) | BIT_MASK(REL_Y);
 78
 79          /* 设置鼠标滚轮相对坐标 */
 80          input_dev->relbit[0] |= BIT_MASK(REL_WHEEL);
 81
 82      } else if (iface_desc->desc.bInterfaceProtocol == USB_INTERFACE_PROTOCOL_KEYBOARD) {
 83          /* 设置设备类型为键盘 */
 84          hid_dev->type = DEVICE_TYPE_KEYBOARD;
 85          /* 格式化键盘设备名称 */
 86          snprintf(hid_dev->name, sizeof(hid_dev->name), "USB Keyboard");
 87
 88          /* 初始化按键状态数组为全0 */
 89          memset(hid_dev->old_keys, 0, MAX_KEYS);
 90          /* 初始化修饰键状态为0 */
 91          hid_dev->old_modifiers = 0;
 92
 93          /* 设置键盘输入设备支持的事件类型：按键事件 */
 94          input_dev->evbit[0] = BIT_MASK(EV_KEY);
 95
 96          /* 设置键盘支持的所有按键 */
 97          for (i = 0; i < 256; i++) {
 98              /* 如果转换表中有对应的键码，设置该按键位 */
 99              if (usb_keycode_map[i] != 0)
100                  set_bit(usb_keycode_map[i], input_dev->keybit);
101          }
102
103      } else {
104          /* 不支持的设备类型 */
105          error = -ENODEV;
106          goto fail_free_input_dev;
107      }
108
109      /* 分配DMA一致性缓冲区，用于接收设备数据 */
110      hid_dev->data = usb_alloc_coherent(udev, 8, GFP_KERNEL, &hid_dev->data_dma);
111      if (!hid_dev->data)
112          goto fail_free_input_dev;
113
114      /* 分配一个URB结构体，用于中断传输 */
115      hid_dev->irq_urb = usb_alloc_urb(0, GFP_KERNEL);
116      if (!hid_dev->irq_urb)
117          goto fail_free_buffer;
118
119      /* 创建USB中断接收管道 */
120      pipe = usb_rcvintpipe(udev, endpoint->bEndpointAddress);
121      /* 获取该端点支持的最大数据包大小 */
122      maxp = usb_hid_maxpacket(udev, pipe);
123      /* 限制最大数据包大小为8字节，只需要前8字节 */
124      if (maxp > 8)
125          maxp = 8;
126
127      /* 初始化中断URB，根据设备类型设置不同的回调函数 */
128      if (hid_dev->type == DEVICE_TYPE_MOUSE) {
129          /* 鼠标设备使用鼠标中断处理函数 */
130          usb_fill_int_urb(hid_dev->irq_urb, udev, pipe,
131                          hid_dev->data, maxp,
132                          usb_mouse_irq, hid_dev,
133                          endpoint->bInterval);
134      } else {
135          /* 键盘设备使用键盘中断处理函数 */
136          usb_fill_int_urb(hid_dev->irq_urb, udev, pipe,
137                          hid_dev->data, maxp,
138                          usb_kbd_irq, hid_dev,
139                          endpoint->bInterval);
140      }
141
142      /* 设置URB的DMA物理地址 */
143      hid_dev->irq_urb->transfer_dma = hid_dev->data_dma;
144      /* 设置URB标志，告诉USB核心不要为传输数据重新映射DMA地址 */
145      hid_dev->irq_urb->transfer_flags |= URB_NO_TRANSFER_DMA_MAP;
146
147      /* 格式化设备物理路径 */
148      snprintf(hid_dev->phys, sizeof(hid_dev->phys),
149              "usb-%s-%s/input0", udev->bus->bus_name,
150              udev->devpath);
151
152      /* 设置输入设备的名称 */
153      input_dev->name = hid_dev->name;
154      /* 设置输入设备的物理路径 */
155      input_dev->phys = hid_dev->phys;
156      /* 从USB设备信息填充输入设备的ID信息 */
157      usb_to_input_id(udev, &input_dev->id);
158      /* 设置输入设备的父设备为USB接口设备 */
159      input_dev->dev.parent = &intf->dev;
160
161      /* 注册输入设备到内核输入子系统 */
162      error = input_register_device(input_dev);
163      if (error)
164          goto fail_free_urb;
165
166      /* 将HID设备结构体指针保存到USB接口的私有数据中 */
167      usb_set_intfdata(intf, hid_dev);
168
169      /* 提交中断URB，开始接收设备数据 */
170      error = usb_submit_urb(hid_dev->irq_urb, GFP_KERNEL);
171      if (error) {
172          dev_err(&intf->dev, "Unable to submit URB, error code: %d\n", error);
173          goto fail_unregister_input;
174      }
175
176      /* 打印设备连接成功信息，包含设备名称和接口号 */
177      dev_info(&intf->dev, "%sConnected (Interface Number: %d)\n", hid_dev->name, hid_dev->interface_num);
178
179      return 0;
180
181  fail_unregister_input:
182      /* 从输入子系统注销输入设备 */
183      input_unregister_device(input_dev);
184
185  fail_free_urb:
186      /* 释放分配的URB结构体 */
187      usb_free_urb(hid_dev->irq_urb);
188
189  fail_free_buffer:
190      /* 释放分配的DMA一致性缓冲区 */
191      usb_free_coherent(udev, 8, hid_dev->data, hid_dev->data_dma);
192
193  fail_free_input_dev:
194      /* 释放分配的输入设备结构体 */
195      input_free_device(input_dev);
196
197  fail_free_hid_dev:
198      /* 释放分配的自定义HID设备结构体 */
199      kfree(hid_dev);
200
201      return error;
202  }
```

关键说明：

- 第6行：从USB接口获取USB设备句柄，用于后续URB、DMA相关操作。
    
- 第28-31行：基础协议校验，仅匹配HID类、引导子类设备，不匹配直接返回-ENODEV。
    
- 第34-35行：端点合法性校验，仅允许单中断输入端点的标准HID设备。
    
- 第61-107行：根据接口协议区分鼠标/键盘设备，分别配置输入事件与按键。
    
- 第110-112行：分配8字节DMA一致性缓冲区，作为USB中断数据的接收内存。
    
- 第115-117行：分配中断URB结构体，用于承载中断传输请求。
    
- 第120-140行：根据设备类型填充URB，分别绑定鼠标或键盘中断回调函数。
    
- 第143-145行：设置URB的DMA地址与标志位，告知USB核心层无需重新映射DMA内存。
    
- 第162-164行：注册输入设备到内核输入子系统。
    
- 第170-174行：提交中断URB，开始接收设备上报的数据。
    
- 第182-200行：错误回滚标签，初始化失败时逆序释放已申请资源，杜绝内存泄漏。
    

**设备断开函数**

设备拔出时内核自动调用，按照注册逆序释放所有内核资源，清理URB、内存、设备节点。

设备断开函数(位于linux_driver/39_usb_mouse_keyboard/usb_mouse_keyboard.c)[¶](#id55 "永久链接至代码")

```c
 1  /* 设备断开函数 */
 2  static void usb_hid_disconnect(struct usb_interface *intf)
 3  {
 4      /* 从USB接口的私有数据中获取HID设备结构体 */
 5      struct usb_hid_device *hid_dev = usb_get_intfdata(intf);
 6
 7      /* 将USB接口的私有数据指针置空 */
 8      usb_set_intfdata(intf, NULL);
 9
10      /* 检查HID设备结构体是否存在 */
11      if (hid_dev) {
12          /* 停止并杀死任何正在进行的URB传输 */
13          usb_kill_urb(hid_dev->irq_urb);
14
15          /* 释放URB结构体 */
16          usb_free_urb(hid_dev->irq_urb);
17
18          /* 释放DMA一致性缓冲区 */
19          usb_free_coherent(hid_dev->udev, 8, hid_dev->data, hid_dev->data_dma);
20
21          /* 从输入子系统注销并释放输入设备 */
22          input_unregister_device(hid_dev->input);
23
24          /* 释放自定义HID设备结构体 */
25          kfree(hid_dev);
26      }
27
28      /* 打印设备断开信息 */
29      dev_info(&intf->dev, "USB HID device has been disconnected\n");
30  }
```

关键说明：

- 第5行：从USB接口私有数据中取回驱动设备结构体。
    
- 第13行：使用usb_kill_urb杀死正在进行的中断传输，防止设备拔出后回调触发空指针异常。
    
- 第16-19行：依次释放URB结构体、DMA一致性缓冲区，回收硬件相关资源。
    
- 第22行：注销并释放输入设备，移除/dev/input下的设备节点。
    

**键盘中断处理函数**

USB键盘数据传输基于中断URB实现，该函数是键盘数据接收、解析、事件上报的入口，完成按键状态对比、键码转换、输入事件同步流程。

键盘中断处理函数(位于linux_driver/39_usb_mouse_keyboard/usb_mouse_keyboard.c)[¶](#id56 "永久链接至代码")

```c
  1  /* 键盘中断处理函数 */
  2  static void usb_kbd_irq(struct urb *urb)
  3  {
  4      /* 从URB的上下文获取自定义的HID设备结构体 */
  5      struct usb_hid_device *kbd = urb->context;
  6      /* 获取存储键盘数据的DMA缓冲区指针 */
  7      unsigned char *data = kbd->data;
  8      /* 获取输入设备指针 */
  9      struct input_dev *dev = kbd->input;
 10      /* 定义变量存储URB重新提交的返回状态 */
 11      int status;
 12      /* 循环计数器变量 */
 13      int i, j;
 14      /* 存储当前报告中的修饰键状态 */
 15      unsigned char modifiers;
 16      /* 标记按键是否仍然处于按下状态 */
 17      int key_pressed;
 18
 19      /* 检查URB传输的完成状态 */
 20      switch (urb->status) {
 21      case 0: /* 状态0表示传输成功完成，继续处理数据 */
 22          break;
 23      case -ECONNRESET:   /* 连接被重置，通常是设备被拔出 */
 24      case -ENOENT:       /* URB被主动取消 */
 25      case -ESHUTDOWN:    /* 设备正在关闭 */
 26          return;         /* 这些情况表示设备已经断开，不需要重新提交URB */
 27      default:
 28          /* 其他所有非致命错误，重新提交URB继续接收数据 */
 29          goto resubmit;
 30      }
 31
 32      /* 标准USB键盘报告格式(8字节)：
 33      * Byte 0: 修饰键状态(bit0=左Ctrl, bit1=左Shift, bit2=左Alt, bit3=左Win
 34      *                    bit4=右Ctrl, bit5=右Shift, bit6=右Alt, bit7=右Win)
 35      * Byte 1: 保留字节，始终为0
 36      * Byte 2-7: 当前按下的按键码(最多6个，0表示无按键)
 37      */
 38
 39      /* 从报告第一个字节获取当前修饰键状态 */
 40      modifiers = data[0];
 41
 42      /* 处理修饰键的状态变化 */
 43      for (i = 0; i < 8; i++) {
 44          /* 比较当前修饰键位与上一次保存的状态是否不同 */
 45          if ((modifiers & (1 << i)) != (kbd->old_modifiers & (1 << i))) {
 46              /* 上报修饰键的按下(1)或释放(0)事件 */
 47              input_report_key(dev, modifier_map[i], (modifiers & (1 << i)) ? 1 : 0);
 48          }
 49      }
 50      /* 保存当前修饰键状态，用于下一次比较 */
 51      kbd->old_modifiers = modifiers;
 52
 53      /* 处理按键释放事件：检查上一次按下的按键是否仍然按下 */
 54      for (i = 0; i < MAX_KEYS; i++) {
 55          /* 跳过0值，表示该位置没有按键 */
 56          if (kbd->old_keys[i] == 0)
 57              continue;
 58
 59          /* 初始化按键按下标记为假 */
 60          key_pressed = 0;
 61          /* 在当前报告中查找该按键是否仍然存在 */
 62          for (j = 2; j < KEYBOARD_REPORT_SIZE; j++) {
 63              if (data[j] == kbd->old_keys[i]) {
 64                  /* 找到该按键，标记为仍然按下 */
 65                  key_pressed = 1;
 66                  break;
 67              }
 68          }
 69
 70          /* 如果按键不再按下，上报释放事件 */
 71          if (!key_pressed) {
 72              /* 将USB按键码转换为Linux输入子系统键码 */
 73              unsigned int keycode = usb_keycode_map[kbd->old_keys[i]];
 74              /* 如果转换有效，上报按键释放事件(0表示释放) */
 75              if (keycode != 0)
 76                  input_report_key(dev, keycode, 0);
 77          }
 78      }
 79
 80      /* 处理按键按下事件：检查当前报告中的按键是否是新按下的 */
 81      for (i = 2; i < KEYBOARD_REPORT_SIZE; i++) {
 82          /* 跳过0值，表示该位置没有按键 */
 83          if (data[i] == 0)
 84              continue;
 85
 86          /* 初始化按键按下标记为假 */
 87          key_pressed = 0;
 88          /* 在上一次保存的按键状态中查找该按键 */
 89          for (j = 0; j < MAX_KEYS; j++) {
 90              if (kbd->old_keys[j] == data[i]) {
 91                  /* 找到该按键，说明已经按下，不需要重复上报 */
 92                  key_pressed = 1;
 93                  break;
 94              }
 95          }
 96
 97          /* 如果是新按下的按键，上报按下事件 */
 98          if (!key_pressed) {
 99              /* 将USB按键码转换为Linux输入子系统键码 */
100              unsigned int keycode = usb_keycode_map[data[i]];
101              /* 如果转换有效，上报按键按下事件(1表示按下) */
102              if (keycode != 0)
103                  input_report_key(dev, keycode, 1);
104          }
105      }
106
107      /* 保存当前按键状态，用于下一次比较 */
108      memcpy(kbd->old_keys, &data[2], MAX_KEYS);
109
110      /* 同步输入事件，通知用户空间所有事件已上报完毕 */
111      input_sync(dev);
112
113  resubmit:
114      /* 重新提交中断URB，以继续接收下一次键盘数据 */
115      status = usb_submit_urb(urb, GFP_ATOMIC);
116      if (status)
117          dev_err(&kbd->udev->dev,
118                  "Unable to resubmit keyboard URB, error code: %d\n", status);
119  }
```

关键说明：

- 第5行：从URB上下文取回驱动私有结构体，是中断回调获取设备资源的标准方式。
    
- 第20-30行：URB状态校验，区分传输成功、设备断开、非致命错误场景，设备离线时停止重新提交URB。
    
- 第40-51行：解析报告第0字节修饰键状态，通过与上一次状态逐位对比，上报修饰键的按下与释放。
    
- 第54-78行：遍历历史按键数组，检测已按下按键是否释放，释放则上报0值事件。
    
- 第81-105行：遍历当前报告按键数组，检测是否为新按下按键，新按下则上报1值事件。
    
- 第108行：保存当前按键状态到缓存，供下一次中断做对比。
    
- 第111行：input_sync同步事件，通知输入子系统本次所有事件上报完毕。
    
- 第115行：重新提交中断URB，实现设备数据的持续监听，无需轮询。
    

**鼠标中断处理函数**

对应鼠标设备的中断数据回调，解析鼠标位移、滚轮、按键状态，上报相对位移事件与按键事件。

鼠标中断处理函数(位于linux_driver/39_usb_mouse_keyboard/usb_mouse_keyboard.c)[¶](#id57 "永久链接至代码")

```c
 1  /* 鼠标中断处理函数 */
 2  static void usb_mouse_irq(struct urb *urb)
 3  {
 4      /* 从URB的上下文获取自定义的HID设备结构体 */
 5      struct usb_hid_device *mouse = urb->context;
 6      /* 获取存储鼠标数据的DMA缓冲区指针 */
 7      signed char *data = mouse->data;
 8      /* 获取输入设备指针 */
 9      struct input_dev *dev = mouse->input;
10      /* 定义变量存储URB重新提交的返回状态 */
11      int status;
12
13      /* 检查URB传输的完成状态 */
14      switch (urb->status) {
15      case 0:
16          /* 状态0表示传输成功完成，继续处理数据 */
17          break;
18      case -ECONNRESET:   /* 连接被重置，通常是设备被拔出 */
19      case -ENOENT:       /* URB被主动取消 */
20      case -ESHUTDOWN:    /* 设备正在关闭 */
21          return;         /* 这些情况表示设备已经断开，不需要重新提交URB */
22      default:
23          /* 其他所有非致命错误，重新提交URB继续接收数据 */
24          goto resubmit;
25      }
26
27      /* 标准USB鼠标报告格式(4字节，支持滚轮)：
28      * Byte 0: 按钮状态(bit0=左键, bit1=右键, bit2=中键, bit3=侧键1, bit4=侧键2)
29      * Byte 1: X轴相对位移(-127 ~ +127，正值向右，负值向左)
30      * Byte 2: Y轴相对位移(-127 ~ +127，正值向下，负值向上)
31      * Byte 3: 滚轮位移(-127 ~ +127，正值向上滚动，负值向下滚动)
32      */
33
34      /* 上报鼠标左键状态，非0表示按下，0表示释放 */
35      input_report_key(dev, BTN_LEFT,   data[0] & 0x01);
36      /* 上报鼠标右键状态 */
37      input_report_key(dev, BTN_RIGHT,  data[0] & 0x02);
38      /* 上报鼠标中键状态 */
39      input_report_key(dev, BTN_MIDDLE, data[0] & 0x04);
40
41      /* 上报鼠标侧键1状态 */
42      input_report_key(dev, BTN_SIDE,   data[0] & 0x08);
43      /* 上报鼠标侧键2状态 */
44      input_report_key(dev, BTN_EXTRA,  data[0] & 0x10);
45
46      /* 上报X轴方向的相对移动量 */
47      input_report_rel(dev, REL_X, data[1]);
48      /* 上报Y轴方向的相对移动量 */
49      input_report_rel(dev, REL_Y, data[2]);
50
51      /* 上报滚轮移动量 */
52      input_report_rel(dev, REL_WHEEL, data[3]);
53
54      /* 同步输入事件，通知用户空间所有事件已上报完毕 */
55      input_sync(dev);
56
57  resubmit:
58      /* 重新提交中断URB，以继续接收下一次鼠标数据 */
59      status = usb_submit_urb(urb, GFP_ATOMIC);
60      if (status)
61          dev_err(&mouse->udev->dev,
62                  "Unable to resubmit mouse URB, error code: %d\n", status);
63  }
```

关键说明：

- 第5行：从URB上下文取回驱动私有结构体，是中断回调获取设备资源的标准方式。
    
- 第14-25行：URB状态校验逻辑，与键盘驱动保持一致，设备断开直接返回，异常自动重提。
    
- 第35-44行：逐位解析报告第0字节，分别上报左键、右键、中键、侧键1、侧键2的按键状态。
    
- 第46-52行：解析报告第1-3字节，分别上报X轴位移、Y轴位移、滚轮位移三类相对坐标事件。
    
- 第55行：input_sync同步本次所有鼠标事件。
    
- 第59行：重新提交URB，持续接收鼠标下一次数据。
    

**设备匹配表与驱动结构体**

定义驱动支持的设备类型，注册USB驱动回调，实现设备热插拔匹配机制。

设备匹配表与驱动结构体(位于linux_driver/39_usb_mouse_keyboard/usb_mouse_keyboard.c)[¶](#id58 "永久链接至代码")

```c
 1  /* USB设备ID表 */
 2  static const struct usb_device_id usb_mouse_keyboard_id_table[] = {
 3      /* 匹配所有符合HID类、引导子类、鼠标协议的USB接口 */
 4      { USB_INTERFACE_INFO(USB_INTERFACE_CLASS_HID,
 5                          USB_INTERFACE_SUBCLASS_BOOT,
 6                          USB_INTERFACE_PROTOCOL_MOUSE) },
 7      /* 匹配所有符合HID类、引导子类、键盘协议的USB接口 */
 8      { USB_INTERFACE_INFO(USB_INTERFACE_CLASS_HID,
 9                          USB_INTERFACE_SUBCLASS_BOOT,
10                          USB_INTERFACE_PROTOCOL_KEYBOARD) },
11      { }
12  };
13  /* 导出设备ID表，使内核热插拔系统知道该驱动支持哪些设备 */
14  MODULE_DEVICE_TABLE(usb, usb_mouse_keyboard_id_table);
15
16  /* USB驱动结构体 */
17  static struct usb_driver usb_mouse_keyboard_driver = {
18      .name       = "usb-mouse-keyboard",
19      .id_table   = usb_mouse_keyboard_id_table,
20      .probe      = usb_hid_probe,        /* 探测函数指针，设备插入时调用 */
21      .disconnect = usb_hid_disconnect,   /* 断开函数指针，设备拔出时调用 */
22  };
```

关键说明：

- 第4-10行：USB_INTERFACE_INFO按类/子类/协议匹配设备，匹配鼠标与键盘两类引导协议设备。
    
- 第14行：MODULE_DEVICE_TABLE导出匹配表，供内核热插拔系统识别驱动支持的设备。
    
- 第20-21行：绑定probe与disconnect回调，实现设备插入探测、拔出清理资源。
    

**模块初始化与退出函数**

模块加载/卸载入口，完成USB驱动注册与注销。

模块初始化与退出函数(位于linux_driver/39_usb_mouse_keyboard/usb_mouse_keyboard.c)[¶](#id59 "永久链接至代码")

```c
 1  /* 模块初始化函数 */
 2  static int __init usb_mouse_keyboard_init(void)
 3  {
 4      int result;
 5
 6      /* 向USB子系统注册USB驱动 */
 7      result = usb_register(&usb_mouse_keyboard_driver);
 8      if (result)
 9          pr_err("Failed to register USB driver, error code: %d\n", result);
10
11      return result;
12  }
13
14  /* 模块退出函数 */
15  static void __exit usb_mouse_keyboard_exit(void)
16  {
17      /* 从USB子系统注销USB驱动 */
18      usb_deregister(&usb_mouse_keyboard_driver);
19
20      /* 打印模块卸载信息 */
21      pr_info("USB mouse and keyboard driver has been uninstalled\n");
22  }
23
24  module_init(usb_mouse_keyboard_init);
25  module_exit(usb_mouse_keyboard_exit);
```

关键说明：

- 第7行：usb_register向USB子系统注册驱动，驱动开始监听热插拔事件。
    
- 第18行：usb_deregister注销驱动，停止响应USB设备插拔。
    

### 5.6.3. Makefile说明[¶](#makefile "永久链接至标题")

本节实验使用的Makefile如下所示，编写该Makefile时，只需要根据实际情况修改变量KERNEL_DIR、CROSS_COMPILE和obj-m即可。

Makefile(位于linux_driver/39_usb_mouse_keyboard/Makefile)[¶](#id60 "永久链接至代码")

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
obj-m := usb_mouse_keyboard.o

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

### 5.6.4. 编译驱动[¶](#id35 "永久链接至标题")

在实验目录下输入 `make` 即可编译驱动，编译得到内核模块usb_mouse_keyboard.ko。

### 5.6.5. 移除内核自带HID驱动[¶](#id36 "永久链接至标题")

由于内核已经自带USB鼠标键盘驱动，为了避免与本实验驱动冲突，需要移除内核自带USB鼠标键盘驱动。

默认使用的通用HID驱动，相关内核配置项如下：

- CONFIG_USB_HID：USB HID传输层驱动，负责USB总线与HID设备之间的通信。
    
- CONFIG_HID_GENERIC：通用HID设备解析驱动，负责解析HID报告描述符，将硬件输入事件转换为Linux输入子系统标准事件，实际处理键盘按键、鼠标移动/点击逻辑。
    

注解

CONFIG_HID_GENERIC配置项依赖CONFIG_USB_HID配置项，因此只关闭CONFIG_USB_HID配置项即可。

#### 5.6.5.1. 修改defconfig[¶](#defconfig "永久链接至标题")

内核配置项都保存在对应的defconfig文件中，可以通过menuconfig配置界面修改配置项然后保存到新的defconfig文件，在内核源码顶层目录执行以下命令：

```bash
#这里以rk356x系列6.1.99内核配置文件为例，打开menuconfig配置界面
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- lubancat_linux_rk356x_defconfig menuconfig
```

打开的界面如下：

![../_images/subsystem_usb_subsystem_2.jpg](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/subsystem_usb_subsystem_2.jpg)

按下键盘的“/”按键打开搜索框，然后输入CONFIG_USB_HID配置项：

![../_images/subsystem_usb_subsystem_3.jpg](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/subsystem_usb_subsystem_3.jpg)

搜索框输入完后选择下方“ok”然后再按下回车就会打开搜索结果，如下图，只有一个搜索结果，可以看到配置项当前状态（为y被选择）、描述、路径、和依赖情况。

![../_images/subsystem_usb_subsystem_4.jpg](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/subsystem_usb_subsystem_4.jpg)

按下键盘的数字“1”键就会跳转到CONFIG_USB_HID配置项处，在配置项处按下空格即可选中配置项，<*>变为< >代表配置项的值从y变为n：

![../_images/subsystem_usb_subsystem_5.jpg](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/subsystem_usb_subsystem_5.jpg)

然后通过键盘方向键选择下方“Save”，再按下回车进行保存，默认保存到.config即可。

![../_images/subsystem_usb_subsystem_6.jpg](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/subsystem_usb_subsystem_6.jpg)

最后选择“Exit”，再按下回车退出界面。默认保存的.config包含了全部的配置项，不利于我们观察配置，需要生成精简的配置文件然后覆盖原来的配置文件，在内核源码顶层目录执行以下命令：

```bash
#保存defconfig精简的配置文件
make savedefconfig ARCH=arm64

#覆盖原来的配置文件，这里以rk356x系列6.1.99内核配置文件为例
cp -f defconfig arch/arm64/configs/lubancat_linux_rk356x_defconfig

#查看新添加的配置项
cat arch/arm64/configs/lubancat_linux_rk356x_defconfig | grep CONFIG_USB_HID

#信息打印如下
# CONFIG_USB_HID is not set
```

可以看到defconfig配置文件的CONFIG_USB_HID is not set，那么编译的时候Makefile里面配置实际就变成了obj-n += hid.o，从而将驱动从内核移除。

#### 5.6.5.2. 编译内核并替换[¶](#id38 "永久链接至标题")

##### 5.6.5.2.1. 编译内核[¶](#id39 "永久链接至标题")

将CONFIG_USB_HID配置项关闭后，在内核源码顶层目录执行以下命令编译内核：

```bash
#清除之前生成的所有文件和配置
make mrproper

# 这里以rk356x系列6.1.99内核配置文件为例
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- lubancat_linux_rk356x_defconfig

# 编译内核，指定平台，指定交叉编译工具，使用8线程进行编译，线程可根据电脑性能自行确定
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8
```

编译完成后在 `内核源码/arch/arm64/boot/` 目录生成的 `Image` 文件就是内核文件。

##### 5.6.5.2.2. 替换内核[¶](#id41 "永久链接至标题")

将内核先传到板卡，再拷贝到板卡的/boot/目录下。

```bash
 1  #先传输到板卡
 2
 3  #查看板卡原先内核
 4  ls /boot/Image* -l
 5
 6  #信息打印如下，可以确认当前板卡实际内核就是/boot/Image-6.1.99-rk356x
 7  lrwxrwxrwx 1 root root       19  5月19日 10:15 /boot/Image -> Image-6.1.99-rk356x
 8  -rw-r--r-- 1 root root 42213888  5月19日 10:15 /boot/Image-6.1.99-rk356x
 9
10  #替换内核，根据实际内核名字而定
11  sudo cp -f Image /boot/Image-6.1.99-rk356x
12
13  #重启系统
14  sudo reboot
15
16  #查看内核版本
17  cat /proc/version
18
19  #信息打印如下
20  Linux version 6.1.99-rk356x (guest@dev107) (aarch64-none-linux-gnu-gcc (GNU Toolchain for the A-profile Architecture 10.3-2021.07 (arm-10.29)) 10.3.1 20210621, GNU ld (GNU Toolchain for the A-profile Architecture 10.3-2021.07 (arm-10.29)) 2.36.1.20210621) #9 SMP Thu Jul  2 08:49:45 UTC 2026
21
22  #在板卡查看内核配置项
23  zcat /proc/config.gz | grep CONFIG_USB_HID
24
25  #信息打印如下
26  # CONFIG_USB_HID is not set
```

可以从编译的主机名和编译时间确认内核是否替换成功，如以上信息中“[guest@dev107](mailto:guest%40dev107)”就是作者的服务器主机，“Thu Jul 2 08:49:45 UTC 2026”就是作者编译内核的UTC世界时间，说明内核替换成功。 从板卡查看内核配置项CONFIG_USB_HID是被关闭的，说明配置成功。

### 5.6.6. 程序运行结果[¶](#id42 "永久链接至标题")

如出现 `Permission denied` 或类似字样，请注意用户权限，大部分操作硬件外设的功能，几乎都需要root用户权限，简单的解决方案是在执行语句前加入sudo或以root用户运行程序。

#### 5.6.6.1. 实验操作[¶](#id43 "永久链接至标题")

以LubanCat2板卡为例，使用以下命令加载驱动，加载驱动前先不要接入USB鼠标或键盘：

```bash
#加载驱动
sudo insmod usb_mouse_keyboard.ko

#信息输出如下
[   23.517215] usbcore: registered new interface driver usb-mouse-keyboard
```

从打印信息可以看到usb_register执行成功，驱动正式注册到内核USB热插拔框架中，内核用驱动结构体里的.name = “usb-mouse-keyboard”这个名称注册。

将USB鼠标接入板卡USB接口：

```bash
#接入USB鼠标打印如下
[   79.124976] usb 2-1: new low-speed USB device number 2 using xhci-hcd
[   79.270632] usb 2-1: New USB device found, idVendor=1c4f, idProduct=0034, bcdDevice= 1.10
[   79.270757] usb 2-1: New USB device strings: Mfr=1, Product=2, SerialNumber=0
[   79.270807] usb 2-1: Product: Usb Mouse
[   79.270848] usb 2-1: Manufacturer: SIGMACHIP
[   79.292692] input: USB Mouse as /devices/platform/usbhost/fd000000.usb/xhci-hcd.4.auto/usb2/2-1/2-1:1.0/input/input5
[   79.293157] usb-mouse-keyboard 2-1:1.0: USB MouseConnected (Interface Number: 0)
```

从打印信息可以看到：

- 第1行：检测到新设备接入USB2总线、第1个端口，设备编号分配为2，设备类型为低速USB设备（low-speed，1.5Mbps），是USB鼠标的标准速率。
    
- 第2行：读取到设备硬件ID：idVendor=1c4f（厂商ID），idProduct=0034（产品ID），bcdDevice=1.10（设备固件版本号1.10）。
    
- 第3行：普通键鼠无序列号（SerialNumber=0）。
    
- 第4-5行：读取设备字符串描述符：产品名Usb Mouse、厂商名SIGMACHIP。
    
- 第6行：成功注册输入设备，设备名为USB Mouse，系统分配为第5个输入设备input5。
    
- 第7行：本实验驱动模块探测成功打印，2-1:1.0 是USB标准路径格式=总线号-设备号:配置号.接口号。
    

将USB键盘接入板卡USB接口：

```bash
#接入USB键盘打印如下
[  102.006640] usb 5-1: new full-speed USB device number 12 using ohci-platform
[  107.438988] usb 5-1: New USB device found, idVendor=24ae, idProduct=4019, bcdDevice= 0.01
[  107.439112] usb 5-1: New USB device strings: Mfr=1, Product=2, SerialNumber=0
[  107.439315] usb 5-1: Product: Rapoo Gaming Keyboard
[  107.439364] usb 5-1: Manufacturer: RAPOO
[  107.443409] input: USB Keyboard as /devices/platform/fd840000.usb/usb5/5-1/5-1:1.0/input/input6
[  107.444899] usb-mouse-keyboard 5-1:1.0: USB KeyboardConnected (Interface Number: 0)
```

从打印信息可以看到：

- 第1行：检测到新设备接入USB5总线、第1端口，设备编号分配为12，设备类型为全速USB设备（full-speed，12Mbps），是USB键盘的标准速率。
    
- 第2行：读取到设备硬件ID：idVendor=24ae（厂商ID），idProduct=4019（产品ID），bcdDevice= 0.01（设备固件版本号0.01）。
    
- 第3行：普通键鼠无序列号（SerialNumber=0）。
    
- 第4-5行：读取设备字符串描述符：产品名Rapoo Gaming Keyboard、厂商名RAPOO。
    
- 第6行：成功注册输入设备，设备名为USB Keyboard，系统分配为第6个输入设备input6。
    
- 第7行：本实验驱动模块探测成功打印，5-1:1.0 是USB标准路径格式=总线号-设备号:配置号.接口号。
    

可以对使用evtest对鼠标进行测试：

```bash
 1  #运行evtest工具
 2  evtest
 3
 4  #信息打印如下，event5对应USB鼠标，event6对应USB键盘
 5  No device specified, trying to scan all of /dev/input/event*
 6  Available devices:
 7  /dev/input/event0:      hdmi_cec_key
 8  /dev/input/event1:      fdd70030.pwm
 9  /dev/input/event2:      rk805 pwrkey
10  /dev/input/event3:      rockchip-rk809 Headset
11  /dev/input/event4:      adc-keys
12  /dev/input/event5:      USB Mouse
13  /dev/input/event6:      USB Keyboard
14  Select the device event number [0-6]: 5   //输入数字5，测试USB鼠标
15  Input driver version is 1.0.1
16  Input device ID: bus 0x3 vendor 0x1c4f product 0x34 version 0x110
17  Input device name: "USB Mouse"
18  Supported events:
19  Event type 0 (EV_SYN)   //同步事件，SYN_REPORT表示一帧输入事件全部上报完毕，上层应用统一处理
20  Event type 1 (EV_KEY)   //按键事件，value=1代表按键按下，value=0代表按键释放
21      Event code 272 (BTN_LEFT)   //鼠标左键
22      Event code 273 (BTN_RIGHT)  //鼠标右键
23      Event code 274 (BTN_MIDDLE) //鼠标中键
24      Event code 275 (BTN_SIDE)   //鼠标侧键1
25      Event code 276 (BTN_EXTRA)  //鼠标侧键2
26  Event type 2 (EV_REL)   //相对位移事件，value为本次移动增量，正负代表移动方向
27      Event code 0 (REL_X)        //X轴水平相对位移
28      Event code 1 (REL_Y)        //Y轴垂直相对位移
29      Event code 8 (REL_WHEEL)    //鼠标滚轮垂直滚动
30  Properties:
31  Testing ... (interrupt to exit)
32                                                                          //以下按下和释放左键、右键，移动鼠标和滚动滑轮进行测试
33  //Event: time 时间戳, type 事件类型, code 事件代码, value 事件值
34  Event: time 1750950448.672039, type 1 (EV_KEY), code 272 (BTN_LEFT), value 1    // 左键按下
35  Event: time 1750950448.672039, -------------- SYN_REPORT ------------
36  Event: time 1750950448.752011, type 2 (EV_REL), code 0 (REL_X), value 1         // 向右移动1个单位
37  Event: time 1750950448.752011, -------------- SYN_REPORT ------------
38  Event: time 1750950448.824006, type 1 (EV_KEY), code 272 (BTN_LEFT), value 0    // 左键释放
39  Event: time 1750950448.824006, -------------- SYN_REPORT ------------
40  Event: time 1750950448.847947, type 2 (EV_REL), code 0 (REL_X), value -1        // 向左移动1个单位
41  Event: time 1750950448.847947, -------------- SYN_REPORT ------------
42  Event: time 1750950449.624032, type 1 (EV_KEY), code 273 (BTN_RIGHT), value 1   // 右键按下
43  Event: time 1750950449.624032, -------------- SYN_REPORT ------------
44  Event: time 1750950449.735881, type 1 (EV_KEY), code 273 (BTN_RIGHT), value 0   // 右键释放
45  Event: time 1750950449.735881, -------------- SYN_REPORT ------------
46  Event: time 1750950452.856012, type 2 (EV_REL), code 0 (REL_X), value -1
47  Event: time 1750950452.856012, -------------- SYN_REPORT ------------
48  Event: time 1750950452.896006, type 2 (EV_REL), code 0 (REL_X), value -2        // 向左移动2个单位
49  Event: time 1750950452.896006, -------------- SYN_REPORT ------------
50  Event: time 1750950452.903920, type 2 (EV_REL), code 0 (REL_X), value -1
51  Event: time 1750950452.903920, -------------- SYN_REPORT ------------
52  Event: time 1750950452.919879, type 2 (EV_REL), code 0 (REL_X), value -2
53  Event: time 1750950452.919879, type 2 (EV_REL), code 1 (REL_Y), value -1        // 向上移动1个单位
54  Event: time 1750950452.919879, -------------- SYN_REPORT ------------
55  Event: time 1750950452.927941, type 2 (EV_REL), code 0 (REL_X), value -1
56  Event: time 1750950452.927941, type 2 (EV_REL), code 1 (REL_Y), value -1
57  Event: time 1750950452.927941, -------------- SYN_REPORT ------------
58  Event: time 1750950454.695988, type 2 (EV_REL), code 8 (REL_WHEEL), value -1    // 滚轮向下滚动1格
59  Event: time 1750950454.695988, -------------- SYN_REPORT ------------
60  Event: time 1750950455.744017, type 2 (EV_REL), code 8 (REL_WHEEL), value 1     // 滚轮向上滚动1格
61  Event: time 1750950455.744017, -------------- SYN_REPORT ------------
```

从上报的事件可确定左键、右键识别正确，按下/释放状态切换正确；位移X/Y轴方向、移动增量解析无误；滚轮上下滚动事件上报正确。

可以对使用evtest对键盘进行测试：

```bash
  1  #运行evtest工具
  2  evtest
  3
  4  #信息打印如下，event5对应USB鼠标，event6对应USB键盘
  5  No device specified, trying to scan all of /dev/input/event*
  6  Available devices:
  7  /dev/input/event0:      hdmi_cec_key
  8  /dev/input/event1:      fdd70030.pwm
  9  /dev/input/event2:      rk805 pwrkey
 10  /dev/input/event3:      rockchip-rk809 Headset
 11  /dev/input/event4:      adc-keys
 12  /dev/input/event5:      USB Mouse
 13  /dev/input/event6:      USB Keyboard
 14  Select the device event number [0-6]: 6
 15  Input driver version is 1.0.1
 16  Input device ID: bus 0x3 vendor 0x24ae product 0x4019 version 0x1
 17  Input device name: "USB Keyboard"
 18  Supported events:
 19  Event type 0 (EV_SYN)
 20  Event type 1 (EV_KEY)
 21      Event code 1 (KEY_ESC)
 22      Event code 2 (KEY_1)
 23      Event code 3 (KEY_2)
 24      Event code 4 (KEY_3)
 25      Event code 5 (KEY_4)
 26      Event code 6 (KEY_5)
 27      Event code 7 (KEY_6)
 28      Event code 8 (KEY_7)
 29      Event code 9 (KEY_8)
 30      Event code 10 (KEY_9)
 31      Event code 11 (KEY_0)
 32      Event code 12 (KEY_MINUS)
 33      Event code 13 (KEY_EQUAL)
 34      Event code 14 (KEY_BACKSPACE)
 35      Event code 15 (KEY_TAB)
 36      Event code 16 (KEY_Q)
 37      Event code 17 (KEY_W)
 38      Event code 18 (KEY_E)
 39      Event code 19 (KEY_R)
 40      Event code 20 (KEY_T)
 41      Event code 21 (KEY_Y)
 42      Event code 22 (KEY_U)
 43      Event code 23 (KEY_I)
 44      Event code 24 (KEY_O)
 45      Event code 25 (KEY_P)
 46      Event code 26 (KEY_LEFTBRACE)
 47      Event code 27 (KEY_RIGHTBRACE)
 48      Event code 28 (KEY_ENTER)
 49      Event code 29 (KEY_LEFTCTRL)
 50      Event code 30 (KEY_A)
 51      Event code 31 (KEY_S)
 52      Event code 32 (KEY_D)
 53      Event code 33 (KEY_F)
 54      Event code 34 (KEY_G)
 55      Event code 35 (KEY_H)
 56      Event code 36 (KEY_J)
 57      Event code 37 (KEY_K)
 58      Event code 38 (KEY_L)
 59      Event code 39 (KEY_SEMICOLON)
 60      Event code 40 (KEY_APOSTROPHE)
 61      Event code 41 (KEY_GRAVE)
 62      Event code 42 (KEY_LEFTSHIFT)
 63      Event code 43 (KEY_BACKSLASH)
 64      Event code 44 (KEY_Z)
 65      Event code 45 (KEY_X)
 66      Event code 46 (KEY_C)
 67      Event code 47 (KEY_V)
 68      Event code 48 (KEY_B)
 69      Event code 49 (KEY_N)
 70      Event code 50 (KEY_M)
 71      Event code 51 (KEY_COMMA)
 72      Event code 52 (KEY_DOT)
 73      Event code 53 (KEY_SLASH)
 74      Event code 54 (KEY_RIGHTSHIFT)
 75      Event code 55 (KEY_KPASTERISK)
 76      Event code 56 (KEY_LEFTALT)
 77      Event code 57 (KEY_SPACE)
 78      Event code 58 (KEY_CAPSLOCK)
 79      Event code 59 (KEY_F1)
 80      Event code 60 (KEY_F2)
 81      Event code 61 (KEY_F3)
 82      Event code 62 (KEY_F4)
 83      Event code 63 (KEY_F5)
 84      Event code 64 (KEY_F6)
 85      Event code 65 (KEY_F7)
 86      Event code 66 (KEY_F8)
 87      Event code 67 (KEY_F9)
 88      Event code 68 (KEY_F10)
 89      Event code 69 (KEY_NUMLOCK)
 90      Event code 70 (KEY_SCROLLLOCK)
 91      Event code 71 (KEY_KP7)
 92      Event code 72 (KEY_KP8)
 93      Event code 73 (KEY_KP9)
 94      Event code 74 (KEY_KPMINUS)
 95      Event code 75 (KEY_KP4)
 96      Event code 76 (KEY_KP5)
 97      Event code 77 (KEY_KP6)
 98      Event code 78 (KEY_KPPLUS)
 99      Event code 79 (KEY_KP1)
100      Event code 80 (KEY_KP2)
101      Event code 81 (KEY_KP3)
102      Event code 82 (KEY_KP0)
103      Event code 83 (KEY_KPDOT)
104      Event code 85 (KEY_ZENKAKUHANKAKU)
105      Event code 86 (KEY_102ND)
106      Event code 87 (KEY_F11)
107      Event code 88 (KEY_F12)
108      Event code 89 (KEY_RO)
109      Event code 90 (KEY_KATAKANA)
110      Event code 91 (KEY_HIRAGANA)
111      Event code 92 (KEY_HENKAN)
112      Event code 93 (KEY_KATAKANAHIRAGANA)
113      Event code 94 (KEY_MUHENKAN)
114      Event code 95 (KEY_KPJPCOMMA)
115      Event code 96 (KEY_KPENTER)
116      Event code 97 (KEY_RIGHTCTRL)
117      Event code 98 (KEY_KPSLASH)
118      Event code 99 (KEY_SYSRQ)
119      Event code 100 (KEY_RIGHTALT)
120      Event code 102 (KEY_HOME)
121      Event code 103 (KEY_UP)
122      Event code 104 (KEY_PAGEUP)
123      Event code 105 (KEY_LEFT)
124      Event code 106 (KEY_RIGHT)
125      Event code 107 (KEY_END)
126      Event code 108 (KEY_DOWN)
127      Event code 109 (KEY_PAGEDOWN)
128      Event code 110 (KEY_INSERT)
129      Event code 111 (KEY_DELETE)
130      Event code 113 (KEY_MUTE)
131      Event code 114 (KEY_VOLUMEDOWN)
132      Event code 115 (KEY_VOLUMEUP)
133      Event code 116 (KEY_POWER)
134      Event code 117 (KEY_KPEQUAL)
135      Event code 119 (KEY_PAUSE)
136      Event code 121 (KEY_KPCOMMA)
137      Event code 122 (KEY_HANGUEL)
138      Event code 123 (KEY_HANJA)
139      Event code 124 (KEY_YEN)
140      Event code 125 (KEY_LEFTMETA)
141      Event code 126 (KEY_RIGHTMETA)
142      Event code 127 (KEY_COMPOSE)
143      Event code 128 (KEY_STOP)
144      Event code 129 (KEY_AGAIN)
145      Event code 130 (KEY_PROPS)
146      Event code 131 (KEY_UNDO)
147      Event code 132 (KEY_FRONT)
148      Event code 133 (KEY_COPY)
149      Event code 134 (KEY_OPEN)
150      Event code 135 (KEY_PASTE)
151      Event code 136 (KEY_FIND)
152      Event code 137 (KEY_CUT)
153      Event code 138 (KEY_HELP)
154      Event code 140 (KEY_CALC)
155      Event code 142 (KEY_SLEEP)
156      Event code 150 (KEY_WWW)
157      Event code 152 (KEY_SCREENLOCK)
158      Event code 158 (KEY_BACK)
159      Event code 159 (KEY_FORWARD)
160      Event code 161 (KEY_EJECTCD)
161      Event code 163 (KEY_NEXTSONG)
162      Event code 164 (KEY_PLAYPAUSE)
163      Event code 165 (KEY_PREVIOUSSONG)
164      Event code 166 (KEY_STOPCD)
165      Event code 173 (KEY_REFRESH)
166      Event code 176 (KEY_EDIT)
167      Event code 177 (KEY_SCROLLUP)
168      Event code 178 (KEY_SCROLLDOWN)
169      Event code 183 (KEY_F13)
170      Event code 184 (KEY_F14)
171      Event code 185 (KEY_F15)
172      Event code 186 (KEY_F16)
173      Event code 187 (KEY_F17)
174      Event code 188 (KEY_F18)
175      Event code 189 (KEY_F19)
176      Event code 190 (KEY_F20)
177      Event code 191 (KEY_F21)
178      Event code 192 (KEY_F22)
179      Event code 193 (KEY_F23)
180      Event code 194 (KEY_F24)
181  Properties:
182  Testing ... (interrupt to exit)
183  Event: time 1750951722.693216, type 1 (EV_KEY), code 30 (KEY_A), value 1    //按下键盘A键
184  Event: time 1750951722.693216, -------------- SYN_REPORT ------------
185  Event: time 1750951722.779091, type 1 (EV_KEY), code 30 (KEY_A), value 0    //松开键盘A键
186  Event: time 1750951722.779091, -------------- SYN_REPORT ------------
187  Event: time 1750951724.861094, type 1 (EV_KEY), code 48 (KEY_B), value 1    //按下键盘B键
188  Event: time 1750951724.861094, -------------- SYN_REPORT ------------
189  Event: time 1750951724.939164, type 1 (EV_KEY), code 48 (KEY_B), value 0    //松开键盘B键
190  Event: time 1750951724.939164, -------------- SYN_REPORT ------------
191  Event: time 1750951726.073052, type 1 (EV_KEY), code 46 (KEY_C), value 1    //按下键盘C键
192  Event: time 1750951726.073052, -------------- SYN_REPORT ------------
193  Event: time 1750951726.162165, type 1 (EV_KEY), code 46 (KEY_C), value 0    //松开键盘C键
194  Event: time 1750951726.162165, -------------- SYN_REPORT ------------
195  Event: time 1750951728.184164, type 1 (EV_KEY), code 42 (KEY_LEFTSHIFT), value 1    //按下键盘左SHIFT键
196  Event: time 1750951728.184164, -------------- SYN_REPORT ------------
197  Event: time 1750951728.287140, type 1 (EV_KEY), code 42 (KEY_LEFTSHIFT), value 0    //松开键盘左SHIFT键
198  Event: time 1750951728.287140, -------------- SYN_REPORT ------------
199  Event: time 1750951728.856174, type 1 (EV_KEY), code 29 (KEY_LEFTCTRL), value 1     //按下键盘左CTRL键
200  Event: time 1750951728.856174, -------------- SYN_REPORT ------------
201  Event: time 1750951728.922137, type 1 (EV_KEY), code 29 (KEY_LEFTCTRL), value 0     //松开键盘左CTRL键
202  Event: time 1750951728.922137, -------------- SYN_REPORT ------------
203  Event: time 1750951730.739144, type 1 (EV_KEY), code 56 (KEY_LEFTALT), value 1      //按下键盘左ALT键
204  Event: time 1750951730.739144, -------------- SYN_REPORT ------------
205  Event: time 1750951730.831123, type 1 (EV_KEY), code 56 (KEY_LEFTALT), value 0      //松开键盘左ALT键
206  Event: time 1750951730.831123, -------------- SYN_REPORT ------------
207  Event: time 1750951736.218098, type 1 (EV_KEY), code 28 (KEY_ENTER), value 1        //按下键盘回车键
208  Event: time 1750951736.218098, -------------- SYN_REPORT ------------
209  Event: time 1750951736.272955, type 1 (EV_KEY), code 28 (KEY_ENTER), value 0        //松开键盘回车键
210  Event: time 1750951736.272955, -------------- SYN_REPORT ------------
```

键盘按键较多可自行测试对比按下的按键和上报的事件是否一致。

如果是使用带桌面的镜像，可在桌面上直接测试鼠标、键盘，或者浏览器搜索“在线鼠标测试”、“在线键盘测试”，如键盘测试：

![../_images/subsystem_usb_subsystem_7.jpg](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/subsystem_usb_subsystem_7.jpg)

键盘测试参考网站：[https://www.zfrontier.com/lab/keyboardTester](https://www.zfrontier.com/lab/keyboardTester)

### 5.6.7. 实验注意事项[¶](#id44 "永久链接至标题")

- 协议适配：本驱动仅支持USB HID引导协议键鼠设备，不支持自定义HID协议、复合USB设备，非常规键鼠可能无法识别。
    
- 驱动冲突：系统默认自带hid-generic通用驱动，加载本驱动前需屏蔽系统HID驱动。
    
- DMA缓冲区限制：固定申请8字节DMA缓冲区，适配标准键鼠报告长度，不可随意修改，否则会导致数据解析错乱。
    
- URB重提机制：禁止删除中断回调中的URB重提机制，删除后设备只能上报一次数据，无法持续监听输入。
    
- 资源释放：设备断开、模块卸载必须完整释放URB、DMA内存、输入设备，否则会造成内核内存泄漏、设备节点残留。
    
- 按键映射：键码映射表覆盖标准按键，小众多媒体按键可能无映射，属于正常现象。