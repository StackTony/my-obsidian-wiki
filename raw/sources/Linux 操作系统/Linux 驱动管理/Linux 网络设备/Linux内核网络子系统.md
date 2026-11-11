原文： https://doc.embedfire.com/linux/rk356x/driver/zh/latest/linux_driver/subsystem_net_subsystem.html

Linux内核网络子系统是操作系统实现网络数据收发、协议解析、设备管理、流量调度的核心子系统，是支撑Linux服务器、嵌入式设备、网络设备联网能力的底层基石。 与用户态网络编程不同，内核网络子系统运行于内核态，直接对接硬件网卡设备、实现完整TCP/IP协议栈、负责数据包的内存管理、中断处理、流量控制、协议解析与数据转发，具有高性能、高并发、低延迟的特性。

## 9.1. 网络相关基础知识[¶](#id1 "永久链接至标题")

### 9.1.1. 网络分层模型[¶](#id2 "永久链接至标题")

网络通信通常采用分层模型，常见的模型有两种：OSI七层模型和TCP/IP四层模型，TCP/IP五层模型较为少见。Linux网络协议栈更接近TCP/IP四层模型，但在实现上可以映射到多个层次。

![../_images/subsystem_net_subsystem_0.jpg](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/subsystem_net_subsystem_0.jpg)

#### 9.1.1.1. OSI七层模型[¶](#osi "永久链接至标题")

OSI七层网络模型是国际标准化组织制定的标准化网络通信 **参考模型** ，将网络数据传输、交互、处理逻辑拆分为七个独立层级：

- 应用层：直接面向用户应用，提供各类网络服务接口。如HTTP、FTP、SMTP、DNS。
    
- 表示层：处理数据的“表示方式”：格式转换、加密解密、压缩解压缩，保证异构系统能互相读懂数据。如TLS、JPEG、ASCII。
    
- 会话层：建立、管理、终止两个进程之间的“会话”，提供对话控制（全双工/半双工）与同步断点。实际中功能大多被并入应用层。
    
- 传输层：提供端到端（进程到进程）的传输服务，通过端口号区分应用；负责分段/重组、可靠交付、流量与拥塞控制。典型协议：TCP、UDP。
    
- 网络层：负责逻辑寻址（IP地址）、路由选择、分组转发与拥塞控制，把数据包从源主机送跨网络送达目的主机。典型协议/设备：IP、ICMP、路由器。
    
- 数据链路层：把比特流组装成“帧”，负责物理寻址（MAC地址）、差错检测（CRC）、流量控制，保证相邻节点间链路上的可靠传输。典型协议/设备：以太网、交换机、网桥。
    
- 物理层：在传输介质上传输原始比特流，规定电压、接口形状、引脚定义、速率等机械/电气规范。典型设备：集线器、中继器；如RJ-45、光纤。
    

#### 9.1.1.2. TCP/IP四层模型[¶](#tcp-ip "永久链接至标题")

TCP/IP四层模型是互联网通信的 **标准模型** ，摒弃了OSI七层模型的理论化冗余分层，采用轻量化的四层架构，面向实际工程实现，是互联网真正在跑的模型。

- 应用层：合并了OSI的会话层、表示层、应用层，包含所有面向应用的协议：HTTP、HTTPS、DNS、FTP、SMTP、SSH等。
    
- 传输层：与OSI传输层相同，TCP提供面向连接的可靠传输，UDP提供无连接的尽最大努力交付。
    
- 网络层：核心是IP协议，负责编址、路由、转发，屏蔽底层网络差异，实现“异构网络互联”；配套ICMP、ARP、IGMP等。
    
- 网络接口层：合并了OSI的物理层和数据链路层，负责把IP数据报封装成帧、通过具体网络（以太网、Wi-Fi、光纤、PPP等）发送出去，处理MAC寻址、电信号等硬件细节。TCP/IP对此层不做硬性规定，从而兼容一切现有网络技术。
    

### 9.1.2. 内核网络数据流转模型[¶](#id3 "永久链接至标题")

内核网络数据分为发送流程（TX）与接收流程（RX）：

- 发送流程：用户态Socket发送数据 -> 内核协议栈逐层封装头部（TCP/UDP+IP+以太网帧） -> 网络设备驱动入队 -> 硬件网卡发送至链路。
    
- 接收流程：网卡硬件接收帧 -> 硬件中断触发 -> NAPI轮询接管 -> 驱动获取数据包 -> 逐层解封装校验 -> 协议栈处理 -> 推送至用户态Socket。
    

### 9.1.3. 网络常见协议[¶](#id4 "永久链接至标题")

#### 9.1.3.1. ARP地址解析协议[¶](#arp "永久链接至标题")

ARP（Address Resolution Protocol，地址解析协议）工作在网络层，核心作用是实现三层IP地址到二层MAC硬件地址的映射解析。 以太网通信依赖MAC地址寻址，主机仅知晓目标IP时，可通过ARP广播查询全网设备，获取对应IP的MAC地址，构建ARP缓存表，为单播数据帧收发提供二层寻址依据。

报文字段：

|   |   |   |   |   |   |   |   |   |   |
|---|---|---|---|---|---|---|---|---|---|
ARP 报文格式[¶](#id85 "永久链接至表格")
|长度（位）|16|16|8|8|16|48|32|48|32|
|长度（字节）|2|2|1|1|2|6|4|6|4|
|数据类型|硬件类型|上层协议类型|硬件地址长度|协议地址长度|操作类型|源硬件地址|源协议地址|目标硬件地址|目标协议地址|

内核收到ARP请求报文后，校验目标IP是否为本机地址，匹配成功则组装ARP应答报文，交换收发地址并回复；收到应答报文则更新本地ARP缓存。

#### 9.1.3.2. IPv4网络协议[¶](#ipv4 "永久链接至标题")

IP（Internet Protocol，网际协议）是网络层核心协议，负责跨网段逻辑寻址、路由转发、数据包分片与重组。IP协议为无连接、不可靠传输协议，不保证报文有序、不丢包，仅负责规划传输路径、转发报文，可靠性由上层TCP协议保障。

报文字段：

|   |   |   |   |   |   |   |   |   |   |   |
|---|---|---|---|---|---|---|---|---|---|---|
IPv4 报文格式[¶](#id86 "永久链接至表格")
|长度（位）|4+4|8|16|16|3+13|8|8|16|32|32|
|长度（字节）|1|1|2|2|2|1|1|2|4|4|
|数据类型|版本 + 首部长度|服务类型（DSCP/ECN）|总长度|标识|标志 + 片偏移|TTL|协议号|首部校验和|源IP|目的IP|

内核接收IP报文后，校验版本、TTL、校验和合法性，根据目标IP路由匹配，通过协议号区分上层协议，分发至TCP/UDP/ICMP处理模块；报文转发、修改后必须重新计算首部校验和。

#### 9.1.3.3. ICMP网络控制报文协议[¶](#icmp "永久链接至标题")

ICMP（Internet Control Message Protocol，网络控制报文协议）隶属于网络层，用于网络链路探测、故障诊断、报文反馈，无端口概念。日常ping命令、网络超时、路由不可达等探测功能均基于ICMP实现。

报文字段：

|   |   |   |   |   |   |   |
|---|---|---|---|---|---|---|
ICMP Echo 报文格式[¶](#id87 "永久链接至表格")
|长度（位）|8|8|16|16|16|可变|
|长度（字节）|1|1|2|2|2|可变|
|数据类型|报文类型|代码|校验和|标识|序列号|数据载荷|

内核收到ICMP请求报文后，校验合法性，自动组装对应应答报文回复。

#### 9.1.3.4. TCP传输控制协议[¶](#tcp "永久链接至标题")

TCP（Transmission Control Protocol，传输控制协议）是传输层面向连接、可靠传输协议，通过三次握手建立连接、四次挥手断开连接，具备超时重传、流量控制、拥塞控制、乱序重排、应答校验机制，适用于文件传输、网页访问、远程登录等对数据完整性要求高的场景。

报文字段：

|   |   |   |   |   |   |   |   |   |
|---|---|---|---|---|---|---|---|---|
TCP 报文格式[¶](#id88 "永久链接至表格")
|长度（位）|16|16|32|32|4+6+6|16|16|16|
|长度（字节）|2|2|4|4|2|2|2|2|
|数据类型|源端口|目的端口|序列号|确认号|数据偏移+保留+标志位|窗口大小|校验和|紧急指针|

内核TCP模块维护连接状态机，完成连接握手、数据校验、序号整理、超时重传、拥塞调控，保障端到端可靠通信，是内核协议栈最复杂的传输层协议。

#### 9.1.3.5. UDP用户数据报协议[¶](#udp "永久链接至标题")

UDP（User Datagram Protocol，用户数据报协议）是传输层无连接、不可靠、轻量化协议，无需建立连接即可直接收发数据，无重传、流控机制，传输延迟低、开销小，适用于视频直播、语音通话、DNS解析、高频推送等对实时性要求高、可容忍少量丢包的场景。

报文字段：

|   |   |   |   |   |
|---|---|---|---|---|
UDP 报文格式[¶](#id89 "永久链接至表格")
|长度（位）|16|16|16|16|
|长度（字节）|2|2|2|2|
|数据类型|源端口|目的端口|UDP长度|校验和|

内核UDP模块无连接状态维护，接收报文后直接校验、按端口分发至对应应用进程，处理逻辑简单、转发效率高，是高频轻量化网络通信的首选协议。

### 9.1.4. 以太网帧结构[¶](#id5 "永久链接至标题")

以太网帧是TCP/IP网络接口层的核心数据单元，是数据在物理链路中传输的最小完整数据帧。 Linux内核网卡驱动收发数据、skb报文解析、帧校验、协议匹配均基于标准以太网帧格式实现，目前网络设备通用以太网II帧（Ethernet II）格式，由帧头、数据载荷、帧尾校验位三部分组成：

|   |   |   |   |   |   |
|---|---|---|---|---|---|
以太网 II 帧格式[¶](#id90 "永久链接至表格")
|长度（位）|48|48|16|368~12000|32|
|长度（字节）|6|6|2|46~1500|4|
|数据类型|目的MAC地址|源MAC地址|上层协议类型/长度|数据载荷|FCS帧校验序列|

上层协议类型常见取值：0x0800为IPv4报文、0x0806为ARP报文、0x86DD为IPv6报文、0x8035为RARP报文。

### 9.1.5. NAPI中断轮询机制[¶](#napi "永久链接至标题")

传统网卡收包流程依赖硬中断：每收到一个包就触发一次中断。在高速网络下，这种方式会导致频繁中断上下文切换，性能下降。 Linux引入NAPI（New API）机制来缓解这个问题。

NAPI采用中断触发+轮询处理的混合模式：

- 空闲状态：依赖硬件中断，有数据包时触发一次中断；
    
- 繁忙状态：关闭硬件中断，启动软件轮询，批量处理队列中所有数据包；
    
- 处理完毕后重新开启中断，回归空闲监听状态。
    

这种机制可大幅减少硬件中断次数、批量处理数据包、降低CPU开销、极大提升高吞吐场景下的网络性能。 同时NAPI支持budget预算机制，限制单次轮询最大处理包数，避免CPU被网络任务独占。

### 9.1.6. 网络字节序[¶](#id6 "永久链接至标题")

网络通信统一采用大端字节序（Big-Endian），即高位字节存储在低地址，低位字节存储在高地址。 而X86、ARM等主流主机CPU默认使用小端字节序，因此所有内核协议栈组装、解析、修改报文时，必须完成主机字节序与网络字节序的转换，否则会出现字段解析错乱、通信异常问题。

## 9.2. 网络子系统整体架构[¶](#id7 "永久链接至标题")

Linux内核网络子系统采用四层分层架构，从上至下依次为用户态接口层、内核协议栈层、网络设备抽象层、硬件适配层，各层级职责清晰、接口标准化，支持物理网卡、虚拟网卡等多类型网络设备统一管理。

**用户态接口层**

面向应用程序与运维工具，提供标准化交互接口，不参与数据核心处理。 核心组件：Socket接口、sysfs调试文件系统、ethtool工具、ip/ifconfig命令、网络状态统计接口。 主要用于网络参数配置、状态查询、调试开关控制、用户态数据收发。

**内核协议栈层**

网络子系统核心，完全内核态实现，是数据解析、封装、转发的中心。 核心组件：TCP/UDP传输层协议、IP/ARP网络层协议、数据包校验模块、路由转发模块、流量控制模块、连接管理模块。 负责完成所有网络协议逻辑处理、数据包合法性校验、端到端通信管理。

**网络设备抽象层**

内核提供的标准化设备抽象层，屏蔽不同硬件、虚拟设备的差异，为上层协议栈提供统一调用接口。 核心组件：net_device设备结构体、net_device_ops设备操作集、NAPI轮询框架、skb队列管理、网络统计模块。 所有网卡均遵循该层标准接口，实现协议栈与硬件驱动的解耦。

**硬件适配驱动层**

最底层硬件适配层，对接具体网卡硬件或虚拟设备。 物理网卡驱动实现硬件寄存器读写、中断注册、DMA收发；虚拟网卡驱动纯软件模拟数据收发，无硬件依赖。 核心职责：完成数据包硬件收发、中断处理、NAPI调度、硬件状态同步。

## 9.3. 网络子系统核心结构体[¶](#id8 "永久链接至标题")

### 9.3.1. 数据包结构体[¶](#id9 "永久链接至标题")

数据包结构体（struct sk_buff）是Linux内核网络子系统的基石，全称Socket Buffer，用于统一管理所有网络数据包的内存空间、协议头部、数据长度、所属设备、状态标志等信息。 内核所有网络收发、协议解析、数据转发均基于该结构体实现。

sk_buff结构体(内核源码/include/linux/skbuff.h)[¶](#id91 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48<br>49<br>50<br>51<br>52<br>53<br>54<br>55<br>56|struct sk_buff {<br>    // 队列链表节点，用于挂载设备收发队列<br>    union {<br>        struct {<br>            struct sk_buff *next;      // 下一个skb节点<br>            struct sk_buff *prev;      // 上一个skb节点<br>            struct net_device *dev;    // 绑定当前数据包所属网络设备<br>        };<br>    };<br><br>    struct sock *sk;              /* 关联的socket，部分场景使用 */<br><br>    union {<br>        ktime_t tstamp;           // 数据包收发时间戳<br>    };<br><br>    // 数据包长度信息<br>    unsigned int len;             // 数据包总长度(头部+载荷)<br>    unsigned int data_len;        // 非线性分片数据长度<br>    __u16  mac_len;               // 二层MAC头部长度<br>    __u16  hdr_len;               // 整体基础头部总长度<br><br>    __u16  queue_mapping;         // 数据包绑定的设备队列编号<br><br>    // 数据包状态标记位<br>    __u8  cloned:1;               // 标记skb是否为克隆副本<br>    __u8  nohdr:1;                // 标记是否无协议头部<br>    __u8  peeked:1;               // 标记数据是否被预读取<br><br>    // 协议处理核心状态<br>    __u8  pkt_type:3;             // 数据包类型(单播/广播/组播/回包)<br>    __u8  ip_summed:2;            // 校验和状态标记(硬件校验/软件校验/无需校验)<br>    __u8  csum_valid:1;           // 标记校验和是否合法<br><br>    __wsum csum;                  // 数据包校验和数值<br>    __u32 priority;               // 数据包转发优先级<br>    int  skb_iif;                 // 数据包入设备接口索引<br>    __u32 hash;                   // 数据包哈希值，用于负载分发<br><br>    // 各层协议头部偏移<br>    __be16 protocol;              // 二层上层协议类型(IP/ARP等)<br>    __u16 transport_header;       // 四层传输层头部偏移<br>    __u16 network_header;         // 三层网络层头部偏移<br>    __u16 mac_header;             // 二层链路层头部偏移<br><br>    // 数据缓冲区指针与边界<br>    sk_buff_data_t tail;          // 数据尾部指针<br>    sk_buff_data_t end;           // 缓冲区结束指针<br>    unsigned char *head;          // 缓冲区起始指针<br>    unsigned char *data;          // 有效数据起始指针<br><br>    unsigned int truesize;        // skb整体实际占用内存大小<br>    refcount_t users;             // 原子引用计数，管理skb生命周期<br><br>    /* 其他成员省略 */<br>};|

### 9.3.2. 队列头管理结构体[¶](#id10 "永久链接至标题")

队列头管理结构体（struct sk_buff_head）专门用于管理sk_buff双向链表队列的头部结构体，所有网卡收发队列、协议栈缓存队列均基于该结构体实现。 其定义与sk_buff头部前两个成员对齐，保证队列遍历、入队出队操作高效统一，是skb批量管理、并发缓存的基础结构。

sk_buff结构体(内核源码/include/linux/skbuff.h)[¶](#id92 "永久链接至代码")

|   |   |
|---|---|
||struct sk_buff_head {<br>    // 双向链表头尾指针，与sk_buff头部对齐<br>    struct sk_buff *next;      // 队列首个skb节点<br>    struct sk_buff *prev;      // 队列末尾skb节点<br><br>    __u32 qlen;                // 当前队列中skb节点总数量<br>    spinlock_t lock;           // 队列并发操作自旋锁<br>};|

### 9.3.3. 网络设备结构体[¶](#id11 "永久链接至标题")

网络设备结构体（struct net_device）是Linux内核所有网络设备的统一抽象结构体，无论是物理网卡、虚拟网卡、回环设备，均基于该结构体实例化。 该结构体存储设备名称、MAC地址、MTU、链路状态、操作回调、硬件特性、统计信息，是内核管理网络设备的核心载体。

net_device结构体(内核源码/include/linux/netdevice.h)[¶](#id93 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48<br>49<br>50<br>51<br>52<br>53<br>54<br>55<br>56<br>57<br>58<br>59<br>60<br>61<br>62<br>63<br>64<br>65<br>66<br>67<br>68<br>69|struct net_device {<br>    char name[IFNAMSIZ];            // 网络设备名称，如eth0、lo<br><br>    // 硬件IO资源信息<br>    unsigned long mem_end;          // 设备内存空间结束地址<br>    unsigned long mem_start;        // 设备内存空间起始地址<br>    unsigned long base_addr;        // 设备IO物理基地址<br><br>    unsigned long state;            // 设备全局状态<br><br>    // 设备内核链表节点<br>    struct list_head dev_list;      // 全局网络设备链表<br>    struct list_head napi_list;     // NAPI设备管理链表<br>    struct list_head unreg_list;    // 设备注销处理链表<br><br>    // 设备基础属性标志<br>    unsigned int flags;             // 设备基础状态标志位<br>    unsigned long long priv_flags;  // 设备私有功能标志位<br><br>    // 核心操作回调接口<br>    const struct net_device_ops *netdev_ops; // 网络设备操作集<br>    const struct ethtool_ops *ethtool_ops;   // ethtool工具调试查询回调集<br>    const struct header_ops *header_ops;     // 二层协议头部操作接口<br><br>    int ifindex;                      // 设备全局唯一索引编号<br>    unsigned short gflags;            // 设备通用标志位<br>    unsigned short hard_header_len;   // 二层硬件头部固定长度<br><br>    // MTU与数据收发预留空间<br>    unsigned int mtu;                 // 最大传输单元，以太网默认1500<br>    unsigned short needed_headroom;   // 报文头部预留内存空间<br>    unsigned short needed_tailroom;   // 报文尾部预留内存空间<br><br>    unsigned int min_mtu;             // 设备支持的最小MTU<br>    unsigned int max_mtu;             // 设备支持的最大MTU<br>    unsigned short type;              // 设备网络类型<br>    unsigned char addr_len;           // 硬件地址长度，以太网固定6字节<br><br>    // 链路状态统计<br>    struct net_device_stats stats;    // 设备基础收发、丢包统计<br>    atomic_t carrier_up_count;        // 链路上线次数统计<br>    atomic_t carrier_down_count;      // 链路下线次数统计<br><br>    // 设备运行状态<br>    unsigned char operstate;          // 设备运行状态（开启/关闭/异常）<br>    unsigned char link_mode;          // 链路工作模式（全双工/半双工）<br><br>    // MAC地址相关信息<br>    unsigned char perm_addr[MAX_ADDR_LEN]; // 设备永久固化MAC地址<br>    const unsigned char *dev_addr;         // 设备当前生效MAC地址<br><br>    // 网络协议层私有指针<br>    struct in_device __rcu *ip_ptr;        // IPv4协议设备管理信息<br>    struct inet6_dev __rcu *ip6_ptr;       // IPv6协议设备管理信息<br><br>    // 接收队列配置<br>    struct netdev_rx_queue *_rx;           // 接收队列数组<br>    unsigned int num_rx_queues;            // 接收队列数量<br>    rx_handler_func_t __rcu *rx_handler;   // 自定义收包处理回调函数<br><br>    // 发送队列配置<br>    struct netdev_queue *_tx ____cacheline_aligned_in_smp; // 发送队列数组<br>    unsigned int num_tx_queues;            // 发送队列数量<br>    struct Qdisc __rcu *qdisc;             // 流量控制队列规则<br>    unsigned int tx_queue_len;             // 发送队列最大缓存长度<br>    spinlock_t tx_global_lock;             // 发送队列并发保护锁<br><br>    /* 其他成员省略 */<br>};|

### 9.3.4. 网络设备操作集结构体[¶](#id12 "永久链接至标题")

网络设备操作集结构体（struct net_device_ops）是网络设备的核心回调函数集，定义了设备生命周期所有核心操作接口，驱动必须实现对应回调函数，内核在对应场景自动调用，完成设备初始化、数据收发、状态配置。

net_device_ops结构体(内核源码/include/linux/netdevice.h)[¶](#id94 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46|struct net_device_ops {<br>    // 设备初始化与卸载<br>    int (*ndo_init)(struct net_device *dev);                // 设备初始化回调<br>    void (*ndo_uninit)(struct net_device *dev);             // 设备资源释放回调<br><br>    // 设备启停生命周期<br>    int (*ndo_open)(struct net_device *dev);                // 设备启动(ifup)回调<br>    int (*ndo_stop)(struct net_device *dev);                // 设备关闭(ifdown)回调<br><br>    // 核心数据收发<br>    netdev_tx_t (*ndo_start_xmit)(struct sk_buff *skb,<br>                        struct net_device *dev);            // 数据包发送核心回调<br><br>    // 设备特性与队列管理<br>    netdev_features_t (*ndo_features_check)(struct sk_buff *skb,<br>                            struct net_device *dev,<br>                            netdev_features_t features);    // 校验设备硬件特性合法性<br>    u16 (*ndo_select_queue)(struct net_device *dev,<br>                            struct sk_buff *skb,<br>                            struct net_device *sb_dev);     // 选择数据包发送队列<br><br>    // 设备参数配置<br>    int (*ndo_set_mac_address)(struct net_device *dev,<br>                            void *addr);                    // 手动设置设备MAC地址<br>    int (*ndo_validate_addr)(struct net_device *dev);       // 校验MAC地址格式合法性<br>    int (*ndo_change_mtu)(struct net_device *dev,<br>                        int new_mtu);                       // 修改设备MTU最大传输单元<br><br>    // 异常与状态处理<br>    void (*ndo_tx_timeout)(struct net_device *dev,<br>                        unsigned int txqueue);              // 发包超时异常处理<br>    int (*ndo_change_carrier)(struct net_device *dev,<br>                            bool new_carrier);              // 修改链路载波状态(上线/下线)<br><br>    // 设备信息统计<br>    void (*ndo_get_stats64)(struct net_device *dev,<br>                        struct rtnl_link_stats64 *storage); // 获取设备收发统计信息<br><br>    // 硬件特性配置<br>    netdev_features_t (*ndo_fix_features)(struct net_device *dev,<br>                            netdev_features_t features);    // 修正设备软硬件特性<br>    int (*ndo_set_features)(struct net_device *dev,<br>                            netdev_features_t features);    // 开启/关闭设备硬件卸载特性<br><br>    /* 其他成员省略 */<br>};|

### 9.3.5. 设备统计结构体[¶](#id13 "永久链接至标题")

设备统计结构体（struct net_device_stats）用于记录网卡收发报文、字节、错误、丢包、冲突等运行数据，是ethtool、ip -s、ifconfig等工具展示网络统计信息的底层数据源，所有物理/虚拟网卡均依赖该结构体维护基础状态统计。

net_device_stats结构体(内核源码/include/linux/netdevice.h)[¶](#id95 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25|struct net_device_stats {<br>    NET_DEV_STAT(rx_packets);        // 接收报文总数量<br>    NET_DEV_STAT(tx_packets);        // 发送报文总数量<br>    NET_DEV_STAT(rx_bytes);          // 接收数据总字节数<br>    NET_DEV_STAT(tx_bytes);          // 发送数据总字节数<br>    NET_DEV_STAT(rx_errors);         // 接收报文总错误数<br>    NET_DEV_STAT(tx_errors);         // 发送报文总错误数<br>    NET_DEV_STAT(rx_dropped);        // 接收端丢包总数<br>    NET_DEV_STAT(tx_dropped);        // 发送端丢包总数<br>    NET_DEV_STAT(multicast);         // 接收组播报文数量<br>    NET_DEV_STAT(collisions);        // 以太网报文冲突次数<br>    NET_DEV_STAT(rx_length_errors);  // 接收报文长度错误<br>    NET_DEV_STAT(rx_over_errors);    // 接收缓冲区溢出错误<br>    NET_DEV_STAT(rx_crc_errors);     // 接收报文CRC校验错误<br>    NET_DEV_STAT(rx_frame_errors);   // 接收帧格式错误<br>    NET_DEV_STAT(rx_fifo_errors);    // 接收FIFO队列溢出错误<br>    NET_DEV_STAT(rx_missed_errors);  // 遗漏未接收报文错误<br>    NET_DEV_STAT(tx_aborted_errors); // 发送中止错误<br>    NET_DEV_STAT(tx_carrier_errors); // 发送链路载波错误<br>    NET_DEV_STAT(tx_fifo_errors);    // 发送FIFO队列溢出错误<br>    NET_DEV_STAT(tx_heartbeat_errors);// 发送心跳异常错误<br>    NET_DEV_STAT(tx_window_errors);   // 发送滑动窗口异常错误<br>    NET_DEV_STAT(rx_compressed);     // 接收压缩报文数量<br>    NET_DEV_STAT(tx_compressed);     // 发送压缩报文数量<br>};|

### 9.3.6. 网卡调试配置回调结构体[¶](#id14 "永久链接至标题")

网卡调试配置回调结构体（struct ethtool_ops）是Linux网卡设备调试与参数配置的核心回调结构体，为ethtool工具提供底层接口支撑。 所有网卡硬件信息查询、链路参数配置、收发队列调节、功耗调试、统计信息获取等操作，均通过该结构体绑定的回调函数实现。

ethtool_ops结构体(内核源码/include/linux/netdevice.h)[¶](#id96 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35|struct ethtool_ops {<br>    // 驱动基础信息获取<br>    void (*get_drvinfo)(struct net_device *, struct ethtool_drvinfo *); // 获取驱动版本、厂商信息<br>    u32 (*get_link)(struct net_device *); // 获取网卡物理链路状态<br><br>    // 链路与速率配置<br>    int (*get_link_ksettings)(struct net_device *, struct ethtool_link_ksettings *); // 获取速率/双工模式<br>    int (*set_link_ksettings)(struct net_device *, const struct ethtool_link_ksettings *); // 设置速率/双工模式<br><br>    // 中断聚合参数配置<br>    int (*get_coalesce)(struct net_device *, struct ethtool_coalesce *,<br>                struct kernel_ethtool_coalesce *, struct netlink_ext_ack *); // 获取中断聚合参数<br>    int (*set_coalesce)(struct net_device *, struct ethtool_coalesce *,<br>                struct kernel_ethtool_coalesce *, struct netlink_ext_ack *); // 设置中断聚合参数<br><br>    // 收发队列参数配置<br>    void (*get_ringparam)(struct net_device *, struct ethtool_ringparam *,<br>                struct kernel_ethtool_ringparam *, struct netlink_ext_ack *); // 获取队列缓冲区参数<br>    int (*set_ringparam)(struct net_device *, struct ethtool_ringparam *,<br>                struct kernel_ethtool_ringparam *, struct netlink_ext_ack *); // 设置队列缓冲区参数<br><br>    // 网卡统计与自测<br>    void (*get_ethtool_stats)(struct net_device *, struct ethtool_stats *, u64 *); // 获取网卡收发统计数据<br>    void (*self_test)(struct net_device *, struct ethtool_test *, u64 *); // 网卡硬件自检测试<br><br>    // 多队列通道配置<br>    void (*get_channels)(struct net_device *, struct ethtool_channels *); // 获取网卡多队列通道数<br>    int (*set_channels)(struct net_device *, struct ethtool_channels *); // 设置网卡多队列通道数<br><br>    // 休眠唤醒配置<br>    void (*get_wol)(struct net_device *, struct ethtool_wolinfo *); // 获取网卡唤醒配置<br>    int (*set_wol)(struct net_device *, struct ethtool_wolinfo *); // 设置网卡唤醒功能<br><br>    /* 其他成员省略 */<br>};|

### 9.3.7. NAPI轮询结构体[¶](#id15 "永久链接至标题")

NAPI轮询结构体（struct napi_struct）是内核NAPI高性能收包机制的核心结构体，用于管理轮询状态、收包预算、处理函数、队列挂载。 所有支持NAPI的网卡设备均需初始化该结构体，实现中断+轮询的混合收包模式。

napi_struct结构体(内核源码/include/linux/ethtool.h)[¶](#id97 "永久链接至代码")

|   |   |
|---|---|
||struct napi_struct {<br>    struct list_head poll_list;     // NAPI全局轮询链表节点<br>    unsigned long state;            // NAPI状态位图（调度/空闲/工作中）<br>    int weight;                     // 单次轮询最大处理数据包预算<br>    int (*poll)(struct napi_struct *, int); // 核心收包轮询回调<br>    struct net_device *dev;         // 绑定所属网络设备<br>    struct sk_buff *skb;            // 临时缓存待处理skb报文<br>    struct list_head rx_list;       // 待处理普通收包报文链表<br>    int rx_count;                   // rx_list链表中报文数量<br>    unsigned int napi_id;           // NAPI唯一设备ID<br>};|

### 9.3.8. 网络相关头部结构体[¶](#id16 "永久链接至标题")

#### 9.3.8.1. 以太网头部结构体[¶](#id17 "永久链接至标题")

以太网头部结构体（struct ethhdr）用于映射二层以太网帧头格式，是驱动解析、封装、修改二层报文的核心载体。 所有网卡收发的以太网数据帧，其源目MAC、上层协议类型等字段均通过该结构体直接操作。

ethhdr结构体(内核源码/include/uapi/linux/if_ether.h)[¶](#id98 "永久链接至代码")

|   |   |
|---|---|
||struct ethhdr {<br>    unsigned char h_dest[ETH_ALEN];     // 目标MAC地址<br>    unsigned char h_source[ETH_ALEN];   // 源端MAC地址<br>    __be16 h_proto; // 上层协议类型(网络大端序)<br>} __attribute__((packed));|

#### 9.3.8.2. ARP协议头部结构体[¶](#id18 "永久链接至标题")

ARP协议头部结构体（struct arphdr）用于映射网络层ARP报文格式，是实现IP与MAC地址解析、ARP请求/应答报文封装与解析的核心数据结构。 驱动处理ARP报文翻转、协议栈解析ARP数据时，均通过该结构体直接操作报文字段。

arphdr结构体(内核源码/include/uapi/linux/if_arp.h)[¶](#id99 "永久链接至代码")

|   |   |
|---|---|
||struct arphdr {<br>    __be16 ar_hrd;        // 硬件地址类型，以太网固定为0x0001<br>    __be16 ar_pro;        // 协议地址类型，IPv4固定为0x0800<br>    unsigned char ar_hln; // 硬件地址长度，MAC地址固定6字节<br>    unsigned char ar_pln; // 协议地址长度，IPv4固定4字节<br>    __be16 ar_op;         // ARP操作码，1=请求，2=应答<br>}|

#### 9.3.8.3. IPv4协议头部结构体[¶](#id19 "永久链接至标题")

IPv4协议头部结构体（struct iphdr）用于映射标准IPv4报文头部布局，是网络层IP报文解析、封装、修改、转发的核心载体。 该结构体通过大小端位域适配不同CPU架构，兼容大小端主机，涵盖IP版本、头部长度、TTL、上层协议、源目IP、校验和等所有核心字段。

iphdr结构体(内核源码/include/uapi/linux/ip.h)[¶](#id100 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22|struct iphdr {<br>#if defined(__LITTLE_ENDIAN_BITFIELD)<br>    __u8 ihl:4,     // IP头部长度(4bit)<br>        version:4;  // IP协议版本(4bit)<br>#elif defined (__BIG_ENDIAN_BITFIELD)<br>    __u8 version:4, // IP协议版本(4bit)<br>        ihl:4;      // IP头部长度(4bit)<br>#else<br>#error "Please fix <asm/byteorder.h>"<br>#endif<br>    __u8 tos;        // 服务类型字段<br>    __be16 tot_len;  // IP报文总长度<br>    __be16 id;       // 报文唯一标识，用于分片重组<br>    __be16 frag_off; // 分片标志+分片偏移量<br>    __u8 ttl;        // 报文生存时间(路由跳数)<br>    __u8 protocol;   // 上层传输协议号<br>    __sum16 check;   // IP头部校验和<br>    __struct_group(/* no tag */, addrs, /* no attrs */,<br>        __be32 saddr; // 源IP地址<br>        __be32 daddr; // 目的IP地址<br>    );<br>};|

## 9.4. 网络子系统核心函数[¶](#id20 "永久链接至标题")

### 9.4.1. 网络设备分配与释放[¶](#id21 "永久链接至标题")

#### 9.4.1.1. alloc_netdev函数[¶](#alloc-netdev "永久链接至标题")

alloc_netdev函数用于动态分配一个网络设备结构体内存，同时预留设备私有数据空间，初始化设备基础参数，是所有网络设备创建的入口。

函数原型：

|   |   |
|---|---|
||struct net_device *alloc_netdev(size_t priv_size, const char *name,<br>                                unsigned char name_assign_type,<br>                                void (*setup)(struct net_device *));|

参数说明：

- priv_size：设备私有数据结构体大小，内核自动分配私有内存；
    
- name：设备名称模板，如eth%d，内核自动填充序号；
    
- name_assign_type：设备名称分配类型，NET_NAME_UNKNOWN为通用模式；
    
- setup：设备初始化回调函数，用于自定义设备参数、绑定回调。
    

返回值：成功返回net_device指针，失败返回NULL。

#### 9.4.1.2. free_netdev函数[¶](#free-netdev "永久链接至标题")

与alloc_netdev配对使用，用于释放动态分配的网络设备结构体内存及设备私有数据内存，需在设备注销完成后调用，彻底释放内核设备资源，避免内存泄漏。

函数原型：

|   |   |
|---|---|
||void free_netdev(struct net_device *dev);|

参数说明：

- dev：需要释放的网络设备结构体指针，必须是alloc_netdev分配且完成初始化的合法设备。
    

### 9.4.2. 网络设备注册与注销[¶](#id22 "永久链接至标题")

#### 9.4.2.1. register_netdev函数[¶](#register-netdev "永久链接至标题")

register_netdev函数用于将初始化完成、参数配置完毕的网络设备结构体，正式注册到Linux内核网络子系统。 完成注册后，设备会被内核识别，可在用户态通过ip/ifconfig命令查看、配置、启停设备，正式纳入内核网络设备管理体系。

函数原型：

|   |   |
|---|---|
||int register_netdev(struct net_device *dev);|

参数说明：

- dev：需要注册的网络设备结构体指针，必须是alloc_netdev分配且完成初始化的合法设备。
    

返回值：注册成功返回0；注册失败返回负错误码。

#### 9.4.2.2. unregister_netdev函数[¶](#unregister-netdev "永久链接至标题")

unregister_netdev函数用于将已注册的网络设备从内核网络子系统中下线注销，是register_netdev的反向操作。 注销后设备从内核设备列表移除，用户态无法再识别、操作该设备。

函数原型：

|   |   |
|---|---|
||void unregister_netdev(struct net_device *dev);|

参数说明：

- dev：需要下线注销的网络设备结构体指针，必须是已成功注册的合法设备。
    

### 9.4.3. 设备私有数据获取[¶](#id23 "永久链接至标题")

#### 9.4.3.1. netdev_priv函数[¶](#netdev-priv "永久链接至标题")

netdev_priv函数用于获取alloc_netdev分配网络设备时预留的设备私有数据内存指针。 网络设备的自定义私有参数、资源结构体均存放于该私有内存空间，驱动通过该函数快速读取/修改私有数据。

函数原型：

|   |   |
|---|---|
||static inline void *netdev_priv(const struct net_device *dev);|

参数说明：

- dev：合法的网络设备结构体指针，必须为alloc_netdev动态分配的设备。
    

返回值：void* 类型私有数据内存指针，可强制转换为驱动自定义的私有结构体类型，进而操作设备私有资源。

### 9.4.4. 以太网设备初始化[¶](#id24 "永久链接至标题")

#### 9.4.4.1. ether_setup函数[¶](#ether-setup "永久链接至标题")

ether_setup函数用于快速初始化以太网类型网络设备的默认参数，批量填充net_device结构体的以太网标准默认配置，避免手动初始化大量冗余的参数。

函数原型：

|   |   |
|---|---|
||void ether_setup(struct net_device *dev);|

参数说明：

- dev：待初始化的网络设备结构体指针，必须是alloc_netdev分配完成的合法设备，仅适配以太网设备场景。
    

### 9.4.5. 随机MAC地址初始化[¶](#mac "永久链接至标题")

#### 9.4.5.1. eth_hw_addr_random函数[¶](#eth-hw-addr-random "永久链接至标题")

eth_hw_addr_random函数用于为以太网网络设备生成并设置合法的随机本地MAC硬件地址。

函数原型：

|   |   |
|---|---|
||void eth_hw_addr_random(struct net_device *dev);|

参数说明：

- dev：待配置随机MAC的网络设备结构体指针，必须是已完成ether_setup初始化的合法以太网设备。
    

### 9.4.6. NAPI注册与注销[¶](#id25 "永久链接至标题")

#### 9.4.6.1. netif_napi_add函数[¶](#netif-napi-add "永久链接至标题")

netif_napi_add函数用于为网络设备初始化NAPI结构体，绑定轮询回调函数，注册到内核NAPI框架。

函数原型：

|   |   |
|---|---|
||void netif_napi_add(struct net_device *dev,<br>                    struct napi_struct *napi,<br>                    int (*poll)(struct napi_struct *, int));|

参数说明：

- dev：绑定的网络设备；
    
- napi：待初始化的NAPI结构体；
    
- poll：NAPI轮询回调函数。
    

#### 9.4.6.2. netif_napi_del函数[¶](#netif-napi-del "永久链接至标题")

与netif_napi_add配对使用，用于注销、删除已注册的NAPI实例，从内核NAPI框架中移除设备的轮询回调能力，释放NAPI调度资源。

函数原型：

|   |   |
|---|---|
||void netif_napi_del(struct napi_struct *napi);|

参数说明：

- napi：待注销的NAPI结构体指针，必须是已通过netif_napi_add初始化注册完成的合法NAPI实例。
    

### 9.4.7. 设备发送队列启动与停止[¶](#id26 "永久链接至标题")

#### 9.4.7.1. netif_start_queue函数[¶](#netif-start-queue "永久链接至标题")

netif_start_queue函数用于激活设备发送队列，告知内核协议栈当前设备可正常接收、发送数据包。 设备初始化完成、链路上线后必须调用该函数，否则内核不会向下下发TX报文，直接导致网卡无法发包。

函数原型：

|   |   |
|---|---|
||void netif_start_queue(struct net_device *dev);|

参数说明：

- dev：待启动发送队列的网络设备结构体指针。
    

#### 9.4.7.2. netif_stop_queue函数[¶](#netif-stop-queue "永久链接至标题")

netif_stop_queue函数用于暂停设备发送队列调度，告知内核协议栈当前设备暂时无法处理发包请求，停止向下投递TX报文。 常用于设备关闭、链路断开、队列拥堵、硬件异常场景，避免无效发包导致报文丢失、内核报错。

函数原型：

|   |   |
|---|---|
||void netif_stop_queue(struct net_device *dev);|

参数说明：

- dev：需要停止发送队列的网络设备结构体指针。
    

### 9.4.8. 链路载波开启与关闭[¶](#id27 "永久链接至标题")

#### 9.4.8.1. netif_carrier_on函数[¶](#netif-carrier-on "永久链接至标题")

netif_carrier_on函数用于标记网络设备链路为上线状态，开启设备载波信号。 内核通过载波状态判断设备链路可用性，载波开启后，系统识别网卡链路正常，允许进行网络收发、路由匹配、协议交互。

函数原型：

|   |   |
|---|---|
||void netif_carrier_on(struct net_device *dev);|

参数说明：

- dev：需要开启链路载波的网络设备指针。
    

#### 9.4.8.2. netif_carrier_off函数[¶](#netif-carrier-off "永久链接至标题")

netif_carrier_off函数用于标记网络设备链路为断开状态，关闭设备载波信号。 调用后内核判定设备链路异常，停止路由转发、终止报文收发、阻塞新的网络请求，同时同步更新设备链路统计状态。

函数原型：

|   |   |
|---|---|
||void netif_carrier_off(struct net_device *dev);|

参数说明：

- dev：需要断开链路载波的网络设备指针。
    

### 9.4.9. NAPI启用与禁用[¶](#id28 "永久链接至标题")

#### 9.4.9.1. napi_enable函数[¶](#napi-enable "永久链接至标题")

napi_enable函数用于启用已初始化的NAPI实例，将NAPI状态置为可调度状态，允许内核调度器触发轮询收包回调。 NAPI通过netif_napi_add完成结构体初始化后，默认处于禁用状态，必须调用该函数才能正式开启NAPI收包能力，是网卡设备启动、开启收包链路的关键步骤。

函数原型：

|   |   |
|---|---|
||void napi_enable(struct napi_struct *napi);|

参数说明：

- napi：已通过netif_napi_add初始化完成的合法NAPI结构体指针。
    

#### 9.4.9.2. napi_disable函数[¶](#napi-disable "永久链接至标题")

与napi_enable成对匹配使用，用于禁用已启用的NAPI实例，阻塞新的NAPI调度请求，等待当前正在执行的轮询流程结束，保证NAPI资源安全退出。

函数原型：

|   |   |
|---|---|
||void napi_disable(struct napi_struct *napi);|

参数说明：

- napi：已完成初始化、曾启用的合法NAPI结构体指针。
    

### 9.4.10. NAPI调度触发[¶](#id29 "永久链接至标题")

#### 9.4.10.1. napi_schedule函数[¶](#napi-schedule "永久链接至标题")

napi_schedule函数用于触发NAPI轮询机制，调度内核线程执行poll收包函数，批量处理队列数据包。 通常在收到新数据包、skb队列有待处理报文时调用，唤醒NAPI轮询逻辑。

函数原型：

|   |   |
|---|---|
||void napi_schedule(struct napi_struct *napi);|

参数说明：

- napi：已完成初始化、启用的合法NAPI结构体指针。
    

### 9.4.11. NAPI轮询收尾完成[¶](#id30 "永久链接至标题")

#### 9.4.11.1. napi_complete_done函数[¶](#napi-complete-done "永久链接至标题")

napi_complete_done函数用于结束单次NAPI调度轮询流程、更新NAPI工作状态、根据处理预算判断是否重新开启硬件中断。 在NAPI poll回调函数处理完数据包后必须调用，用于告知内核本轮轮询处理结束，同时平衡CPU占用与收包吞吐，避免NAPI死循环、中断永久关闭问题。

函数原型：

|   |   |
|---|---|
||bool napi_complete_done(struct napi_struct *napi, int work_done);|

参数说明：

- napi：当前正在执行轮询的NAPI结构体指针。
    
- work_done：本轮poll回调实际处理的数据包个数。
    

返回值：布尔值，true 表示本轮未耗尽预算、队列仍有数据包，内核可再次调度NAPI轮询；false 表示本轮处理完毕、队列空闲或耗尽预算，正式结束轮询并恢复硬件中断。

### 9.4.12. 网络栈收包[¶](#id31 "永久链接至标题")

#### 9.4.12.1. netif_receive_skb函数[¶](#netif-receive-skb "永久链接至标题")

netif_receive_skb函数用于驱动处理完数据包后，将合法skb推送至内核上层协议栈，完成二层解封装、三层协议解析，是驱动向上交付数据的核心API。

函数原型：

|   |   |
|---|---|
||int netif_receive_skb(struct sk_buff *skb);|

参数说明：

- skb：合法的sk_buff数据包结构体指针。
    

返回值：返回0表示数据包成功投递至内核协议栈；返回非负数值代表报文投递异常。

### 9.4.13. 以太网协议类型解析[¶](#id32 "永久链接至标题")

#### 9.4.13.1. eth_type_trans函数[¶](#eth-type-trans "永久链接至标题")

eth_type_trans函数用于解析skb报文的二层以太网协议类型，自动剥离以太网头部、校准skb数据指针、赋值skb->protocol网络协议字段，完成二层帧到三层协议的转接适配。

函数原型：

|   |   |
|---|---|
||__be16 eth_type_trans(struct sk_buff *skb, struct net_device *dev);|

参数说明：

- skb：待解析的以太网帧skb数据包指针;
    
- dev：当前收包的网络设备结构体指针。
    

返回值：网络大端序16位协议类型值，返回二层承载的上层协议标识，常见取值：0x0800(IPv4)、0x0806(ARP)、0x86DD(IPv6)，可直接赋值给skb->protocol字段。

### 9.4.14. SKB队列初始化[¶](#skb "永久链接至标题")

#### 9.4.14.1. skb_queue_head_init函数[¶](#skb-queue-head-init "永久链接至标题")

skb_queue_head_init函数用于对sk_buff_head队列头结构体做标准化初始化，清零双向链表头尾指针、队列长度计数器、并发自旋锁，将队列置为合法空闲状态。 所有自定义skb收发队列、缓存队列，在使用入队/出队/清空接口前，必须通过该函数完成初始化。

函数原型：

|   |   |
|---|---|
||static inline void skb_queue_head_init(struct sk_buff_head *list);|

参数说明：

- list：待初始化的sk_buff_head队列头结构体指针。
    

### 9.4.15. SKB队列长度获取[¶](#id33 "永久链接至标题")

#### 9.4.15.1. skb_queue_len函数[¶](#skb-queue-len "永久链接至标题")

skb_queue_len函数用于快速获取skb队列当前缓存的数据包总个数。

函数原型：

|   |   |
|---|---|
||static inline __u32 skb_queue_len(const struct sk_buff_head *list);|

参数说明：

- list：合法的skb队列头结构体指针。
    

返回值：无符号32位整型，返回队列中当前缓存的skb报文总数量，队列为空时返回0。

### 9.4.16. SKB队列入队与出队[¶](#id34 "永久链接至标题")

#### 9.4.16.1. __skb_queue_tail函数[¶](#skb-queue-tail "永久链接至标题")

__skb_queue_tail函数用于实现skb数据包尾部入队操作，将单个skb数据包挂载到skb队列尾部，完成数据包缓存存储。 该函数为无锁基础入队接口，本身不做并发保护，多线程、中断上下文调用时必须手动加自旋锁，保障队列操作并发安全

函数原型：

|   |   |
|---|---|
||void __skb_queue_tail(struct sk_buff_head *list, struct sk_buff *skb);|

参数说明：

- list：skb队列头结构体指针。
    
- skb：待入队的sk_buff数据包指针。
    

#### 9.4.16.2. __skb_dequeue函数[¶](#skb-dequeue "永久链接至标题")

__skb_dequeue函数用于实现skb数据包头部出队操作，从skb队列头部取出首个数据包，实现先进先出的队列读取逻辑。 与入队函数对应，该函数为无锁基础出队接口，并发场景下需配合自旋锁使用，保证队列读取安全。

函数原型：

|   |   |
|---|---|
||struct sk_buff *__skb_dequeue(struct sk_buff_head *list);|

参数说明：

- list：skb队列头结构体指针。
    

返回值：成功出队返回队列头部合法skb数据包指针；队列为空时返回NULL。

### 9.4.17. SKB队列清空[¶](#id35 "永久链接至标题")

#### 9.4.17.1. skb_queue_purge函数[¶](#skb-queue-purge "永久链接至标题")

skb_queue_purge函数用于批量清空队列中所有残留skb数据包，自动遍历队列节点、逐个释放skb内存、重置队列状态。

函数原型：

|   |   |
|---|---|
||void skb_queue_purge(struct sk_buff_head *list);|

参数说明：

- list：待清空的skb队列头结构体指针。
    

### 9.4.18. SKB数据包安全释放[¶](#id36 "永久链接至标题")

#### 9.4.18.1. dev_kfree_skb函数[¶](#dev-kfree-skb "永久链接至标题")

dev_kfree_skb函数用于安全销毁sk_buff数据包、回收内核报文内存。 函数内部通过原子引用计数机制管理skb生命周期，仅当引用计数归0时才彻底释放数据包缓冲区与结构体内存，可有效避免野指针访问、重复释放、内存泄漏问题。

函数原型：

|   |   |
|---|---|
||void dev_kfree_skb(struct sk_buff *skb);|

参数说明：

- skb：待释放的sk_buff数据包结构体指针。
    

## 9.5. 内核网络子系统源码解析[¶](#id37 "永久链接至标题")

以RK3588S(基于Synopsys DWMAC IP) + RTL8211F PHY进行解析，分析是如何协同完成网卡注册、链路建立以及数据收发。整个链路分为5个阶段：平台Probe与资源解析、MDIO扫描与PHY绑定、网卡Open与链路协商、数据发送(TX)、数据接收(RX)。

选取瑞芯微6.1.99版本内核进行说明，相关源码如下：

- 板卡设备树：内核源码/arch/arm64/boot/dts/rockchip/rk3588s-lubancat-4.dts
    
- SoC通用设备树：内核源码/arch/arm64/boot/dts/rockchip/rk3588s.dtsi
    
- MAC核心层驱动：内核源码/drivers/net/ethernet/stmicro/stmmac/
    
- 瑞芯微MAC平台胶水层驱动：内核源码/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
    
- PHY驱动：内核源码/drivers/net/phy/realtek.c
    
- MDIO驱动：内核源码/drivers/net/mdio/
    

### 9.5.1. MAC与PHY[¶](#macphy "永久链接至标题")

在以太网架构中，网卡控制器通常分为MAC（媒体访问控制层）和PHY（物理层）两部分：

- **MAC** (RK3588S GMAC1)：负责数据链路层功能，如以太网帧的封装/解封装、MAC地址过滤、校验和卸载以及通过DMA与系统内存交换数据，由stmmac驱动管理。
    
- **PHY** (RTL8211F)：负责物理层功能，如数字信号与模拟信号的转换、自协商速率/双工模式、链路状态检测，由realtek.c驱动管理。
    

MAC与PHY的通信接口：

- 数据通道：RGMII（Reduced Gigabit Media Independent Interface），用于MAC和PHY之间高速传输以太网帧。
    
- 控制通道：MDIO/MDC总线，用于MAC读写PHY的内部寄存器，如配置延迟、读取链路状态。
    

### 9.5.2. 设备树解析[¶](#id38 "永久链接至标题")

SoC通用设备树定义了RK3588S芯片内部GMAC1控制器的硬件属性和资源，与具体外接什么PHY无关。

SoC通用设备树gmac1和mdio1节点(位于内核源码/arch/arm64/boot/dts/rockchip/rk3588s.dtsi)[¶](#id101 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48|gmac1: ethernet@fe1c0000 {<br>    compatible = "rockchip,rk3588-gmac", "snps,dwmac-4.20a";<br>    reg = <0x0 0xfe1c0000 0x0 0x10000>;<br>    interrupts = <GIC_SPI 234 IRQ_TYPE_LEVEL_HIGH>,<br>            <GIC_SPI 233 IRQ_TYPE_LEVEL_HIGH>;<br>    interrupt-names = "macirq", "eth_wake_irq";<br>    rockchip,grf = <&sys_grf>;<br>    rockchip,php_grf = <&php_grf>;<br>    clocks = <&cru CLK_GMAC_125M>, <&cru CLK_GMAC_50M>,<br>        <&cru PCLK_GMAC1>, <&cru ACLK_GMAC1>,<br>        <&cru CLK_GMAC1_PTP_REF>;<br>    clock-names = "stmmaceth", "clk_mac_ref",<br>            "pclk_mac", "aclk_mac",<br>            "ptp_ref";<br>    resets = <&cru SRST_A_GMAC1>;<br>    reset-names = "stmmaceth";<br>    power-domains = <&power RK3588_PD_GMAC>;<br><br>    snps,mixed-burst;<br>    snps,tso;<br><br>    snps,axi-config = <&gmac1_stmmac_axi_setup>;<br>    snps,mtl-rx-config = <&gmac1_mtl_rx_setup>;<br>    snps,mtl-tx-config = <&gmac1_mtl_tx_setup>;<br>    status = "disabled";<br><br>    mdio1: mdio {<br>        compatible = "snps,dwmac-mdio";<br>        #address-cells = <0x1>;<br>        #size-cells = <0x0>;<br>    };<br><br>    gmac1_stmmac_axi_setup: stmmac-axi-config {<br>        snps,wr_osr_lmt = <4>;<br>        snps,rd_osr_lmt = <8>;<br>        snps,blen = <0 0 0 0 16 8 4>;<br>    };<br><br>    gmac1_mtl_rx_setup: rx-queues-config {<br>        snps,rx-queues-to-use = <1>;<br>        queue0 {};<br>    };<br><br>    gmac1_mtl_tx_setup: tx-queues-config {<br>        snps,tx-queues-to-use = <1>;<br>        queue0 {};<br>    };<br>};|

关键说明：

- compatible：”rockchip,rk3588-gmac”用来匹配Rockchip的平台驱动dwmac-rk.c，”dwmac-4.20a”匹配stmmac核心驱动。
    
- reg：GMAC寄存器的物理基地址和映射长度。内核通过devm_platform_ioremap_resource将其映射为虚拟地址priv->ioaddr。
    
- interrupts：定义了主中断(macirq)和唤醒中断(eth_wake_irq)。内核在stmmac_request_irq中申请这些IRQ资源。
    
- clocks/resets：定义了MAC运行所需的5路时钟（主时钟、PTP时钟等）和复位信号。驱动在Probe阶段会开启时钟并解除复位。
    
- snps,tso：开启TCP分段卸载(TSO)硬件支持。内核解析后设置plat->tso_en = true，发包时若遇到超大TCP 包，会走stmmac_tso_xmit硬件切分路径。
    
- snps,axi-config：指向AXI总线配置子节点。配置DMA引擎在AXI总线上的Burst长度（snps,blen）和Outstanding读写限制，优化内存带宽利用率。
    
- mdio1: mdio：声明该MAC内部集成了一个MDIO总线控制器，用于通过MDC/MDIO引脚与外部PHY芯片进行寄存器读写通信。
    
- snps,mtl-[*](#id39)-config：指向MTL(MAC 传输层)多队列配置。此处配置了1个RX队列和1个TX队列（snps,rx-queues-to-use = <1>），即单队列模式。
    

板卡设备树gmac1节点(位于内核源码/arch/arm64/boot/dts/rockchip/rk3588s-lubancat-4.dts)[¶](#id102 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30|&gmac1 {<br>    /* Use rgmii-rxid mode to disable rx delay inside Soc */<br>    phy-mode = "rgmii-rxid";<br>    clock_in_out = "output";<br><br>    snps,reset-gpio = <&gpio3 RK_PB2 GPIO_ACTIVE_LOW>;<br>    snps,reset-active-low;<br>    /* Reset time is 20ms, 100ms for rtl8211f */<br>    snps,reset-delays-us = <0 20000 100000>;<br><br>    pinctrl-names = "default";<br>    pinctrl-0 = <&gmac1_miim<br>            &gmac1_tx_bus2<br>            &gmac1_rx_bus2<br>            &gmac1_rgmii_clk<br>            &gmac1_rgmii_bus>;<br><br>    tx_delay = <0x1b>;<br>    /* rx_delay = <0x00>; */<br><br>    jl2xxx,tx-delay = <0x01>;<br>    jl2xxx,rx-delay = <0x01>;<br><br>    rtl8211f,tx-delay = <0x1b>;<br>    /* rtl8211f,rx-delay = <0x01>; */<br><br>    phy-handle = <&rgmii_phy1>;<br>    status = "okay";<br>};|

关键说明：

- phy-mode = “rgmii-rxid”：这是RGMII接口最关键的配置。rxid表示RX延迟由PHY内部提供(RX Internal Delay)，而TX延迟必须由MAC侧提供。
    
- tx_delay = <0x1b>：由于RX延迟交给了PHY，MAC侧需要补偿TX延迟。0x1b是Rockchip GRF（通用寄存器文件）中的特定值，通常对应约1.5ns ~ 2.0ns的时钟相位偏移，以满足RGMII的时序要求。
    
- snps,reset-gpio：定义了PHY的硬件复位引脚（GPIO3_B2，低电平有效）。
    
- 时序控制：<0 20000 100000>表示：拉低前等待0us -> 保持拉低状态20ms -> 拉高后等待100ms再开始MDIO通信，确保PHY内部PLL锁相环稳定。
    
- phy-handle = <&rgmii_phy1>：在MAC节点中将MAC与这个PHY节点绑定，建立phylink关联。
    

板卡设备树mdio1节点(位于内核源码/arch/arm64/boot/dts/rockchip/rk3588s-lubancat-4.dts)[¶](#id103 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15|&mdio1 {<br>    rgmii_phy1: phy@0 {<br>        compatible = "ethernet-phy-ieee802.3-c22";<br>        reg = <0x0>;<br>        jl2xxx,led-enable = <(JL2XXX_LED_STATIC_OP_EN \| JL1XXX_LED_MODE_EN)>;<br>        jl2xxx,led-mode = <(JL2XXX_LED1_LINK10  \| \<br>                JL2XXX_LED1_LINK100  \| \<br>                JL2XXX_LED1_LINK1000 \| \<br>                JL2XXX_LED2_LINK10   \| \<br>                JL2XXX_LED2_LINK100  \| \<br>                JL2XXX_LED2_LINK1000 \| \<br>                JL2XXX_LED2_ACTIVITY )>; //JL PHY<br>        realtek,led-data = <0x6d60>;  //8211F phy<br>    };<br>};|

关键说明：

- compatible：”ethernet-phy-ieee802.3-c22”匹配内核驱动of_mdio.c。
    
- realtek,led-data：自定义属性，用于配置RTL8211F的LED引脚行为，控制LED闪烁状态。
    

### 9.5.3. 瑞芯微MAC平台胶水层驱动解析[¶](#id41 "永久链接至标题")

stmmac是Synopsys的通用以太网MAC IP核驱动，用于所有使用dwmac IP的SoC。 但每家SoC厂商围绕这个IP核做了不同的封装——时钟配置、GRF寄存器、PHY接口选择、延迟配置等都不同。 dwmac-rk.c就是瑞芯微平台的胶水层，负责把这些RK特有配置接入stmmac通用框架。

#### 9.5.3.1. 驱动注册入口[¶](#id42 "永久链接至标题")

设备树compatible中：”rockchip,rk3588-gmac”用来匹配rk_gmac_dwmac_match表，绑定rk3588_ops。

驱动注册入口(位于内核源码/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c)[¶](#id104 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15|static const struct of_device_id rk_gmac_dwmac_match[] = {<br>    { .compatible = "rockchip,rk3588-gmac", .data = &rk3588_ops },<br>    // 其他RK芯片...<br>};<br><br>static struct platform_driver rk_gmac_dwmac_driver = {<br>    .probe  = rk_gmac_probe,    // 探测函数<br>    .remove = rk_gmac_remove,   // 移除函数<br>    .driver = {<br>        .name           = "rk_gmac-dwmac",<br>        .pm         = &rk_gmac_pm_ops,              // 电源管理<br>        .of_match_table = rk_gmac_dwmac_match,  // 设备树匹配表<br>    },<br>};<br>module_platform_driver(rk_gmac_dwmac_driver);|

匹配成功后后续通过of_device_get_match_data()取出RK3588专用的操作集。

#### 9.5.3.2. RK平台操作集[¶](#rk "永久链接至标题")

rk_gmac_ops及其在RK3588上的实例rk3588_ops，是驱动中最核心的操作集，用于屏蔽RK3588底层特有的硬件寄存器差异，向上层通用的STMMAC核心驱动提供统一的硬件配置接口。

RK平台操作集(位于内核源码/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c)[¶](#id105 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28|struct rk_gmac_ops {<br>    void (*set_to_rgmii)(struct rk_priv_data *bsp_priv,<br>                int tx_delay, int rx_delay);<br>    void (*set_to_rmii)(struct rk_priv_data *bsp_priv);<br>    void (*set_to_sgmii)(struct rk_priv_data *bsp_priv);<br>    void (*set_to_qsgmii)(struct rk_priv_data *bsp_priv);<br>    void (*set_rgmii_speed)(struct rk_priv_data *bsp_priv, int speed);<br>    void (*set_rmii_speed)(struct rk_priv_data *bsp_priv, int speed);<br>    void (*set_clock_selection)(struct rk_priv_data *bsp_priv, bool input,<br>                    bool enable);<br>    void (*integrated_phy_power)(struct rk_priv_data *bsp_priv, bool up);<br>    bool regs_valid;<br>    u32 regs[];<br>};<br><br>static const struct rk_gmac_ops rk3588_ops = {<br>    .set_to_rgmii = rk3588_set_to_rgmii,        // 配置RGMII模式<br>    .set_to_rmii = rk3588_set_to_rmii,          // 配置RMII模式<br>    .set_rgmii_speed = rk3588_set_gmac_speed,   // 设置RGMII速率<br>    .set_rmii_speed = rk3588_set_gmac_speed,    // 设置RMII速率<br>    .set_clock_selection = rk3588_set_clock_selection,  // 时钟输入/输出选择<br>    .regs_valid = true,<br>    .regs = {   // gmac0/gmac1基地址<br>        0xfe1b0000, /* gmac0 */<br>        0xfe1c0000, /* gmac1 */<br>        0x0, /* sentinel */<br>    },<br>};|

#### 9.5.3.3. probe函数[¶](#probe "永久链接至标题")

probe函数负责把SoC特有的硬件资源准备好，然后打包交给STMMAC核心驱动，最终完成网卡的注册。

rk_gmac_probe函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c)[¶](#id106 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48<br>49<br>50<br>51<br>52<br>53<br>54<br>55<br>56<br>57<br>58<br>59<br>60<br>61<br>62<br>63<br>64<br>65<br>66<br>67<br>68<br>69<br>70|static int rk_gmac_probe(struct platform_device *pdev)<br>{<br>    struct plat_stmmacenet_data *plat_dat;<br>    struct stmmac_resources stmmac_res;<br>    const struct rk_gmac_ops *data;<br>    int ret;<br><br>    // 从设备树匹配当前SOC对应的平台操作集，即取出rk3588_ops<br>    data = of_device_get_match_data(&pdev->dev);<br>    if (!data) {<br>        dev_err(&pdev->dev, "no of match data provided\n");<br>        return -EINVAL;<br>    }<br><br>    // 解析平台设备硬件资源，获取MAC基地址、中断号等资源<br>    ret = stmmac_get_platform_resources(pdev, &stmmac_res);<br>    if (ret)<br>        return ret;<br><br>    // 解析设备树通用stmmac属性，phy-mode、phy-handle、clocks、resets等<br>    plat_dat = stmmac_probe_config_dt(pdev, stmmac_res.mac);<br>    if (IS_ERR(plat_dat))<br>        return PTR_ERR(plat_dat);<br><br>    /* If the stmmac is not already selected as gmac4,<br>    * then make sure we fallback to gmac.<br>    */<br>    if (!plat_dat->has_gmac4)<br>        plat_dat->has_gmac = true;<br><br>    plat_dat->sph_disable = true;<br><br>    // 绑定rk平台特有的回调函数<br>    plat_dat->fix_mac_speed = rk_fix_speed;     // 速率变更回调<br>    plat_dat->get_eth_addr = rk_get_eth_addr;   // MAC地址获取回调<br>    plat_dat->integrated_phy_power = rk_integrated_phy_power; // PHY电源控制回调<br><br>    // 初始化rk私有数据，解析tx_delay/rx_delay，获取GRF句柄<br>    plat_dat->bsp_priv = rk_gmac_setup(pdev, plat_dat, data);<br>    if (IS_ERR(plat_dat->bsp_priv)) {<br>        ret = PTR_ERR(plat_dat->bsp_priv);<br>        goto err_remove_config_dt;<br>    }<br><br>    // 初始化芯片时钟安全单元<br>    rk_gmac_csu_init(plat_dat);<br><br>    // 获取并配置所有时钟<br>    ret = rk_gmac_clk_init(plat_dat);<br>    if (ret)<br>        goto err_remove_config_dt;<br><br>    // 以太网硬件上电，完成PHY初始化、网口模式配置、硬件复位<br>    ret = rk_gmac_powerup(plat_dat->bsp_priv);<br>    if (ret)<br>        goto err_remove_config_dt;<br><br>    // 调用内核STMMAC通用驱动，完成网卡设备内核注册、收发链路初始化<br>    ret = stmmac_dvr_probe(&pdev->dev, plat_dat, &stmmac_res);<br>    if (ret)<br>        goto err_gmac_powerdown;<br><br>    // 创建自定义sysfs调试节点，支持用户态网口参数调试<br>    ret = dwmac_rk_create_loopback_sysfs(&pdev->dev);<br>    if (ret)<br>        goto err_gmac_powerdown;<br><br>    return 0;<br><br>}|

#### 9.5.3.4. 硬件资源与设备树解析[¶](#id43 "永久链接至标题")

rk_gmac_setup的任务是从设备树中提取所有与MAC/PHY相关的硬件配置信息，填充到rk_priv_data结构体中，为后续的接口初始化、时钟配置等操作提供数据基础。

rk_gmac_setup函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c)[¶](#id107 "永久链接至代码")

|   |   |
|---|---|
|1<br>  2<br>  3<br>  4<br>  5<br>  6<br>  7<br>  8<br>  9<br> 10<br> 11<br> 12<br> 13<br> 14<br> 15<br> 16<br> 17<br> 18<br> 19<br> 20<br> 21<br> 22<br> 23<br> 24<br> 25<br> 26<br> 27<br> 28<br> 29<br> 30<br> 31<br> 32<br> 33<br> 34<br> 35<br> 36<br> 37<br> 38<br> 39<br> 40<br> 41<br> 42<br> 43<br> 44<br> 45<br> 46<br> 47<br> 48<br> 49<br> 50<br> 51<br> 52<br> 53<br> 54<br> 55<br> 56<br> 57<br> 58<br> 59<br> 60<br> 61<br> 62<br> 63<br> 64<br> 65<br> 66<br> 67<br> 68<br> 69<br> 70<br> 71<br> 72<br> 73<br> 74<br> 75<br> 76<br> 77<br> 78<br> 79<br> 80<br> 81<br> 82<br> 83<br> 84<br> 85<br> 86<br> 87<br> 88<br> 89<br> 90<br> 91<br> 92<br> 93<br> 94<br> 95<br> 96<br> 97<br> 98<br> 99<br>100<br>101<br>102<br>103<br>104<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119<br>120<br>121<br>122<br>123<br>124<br>125<br>126<br>127<br>128|static struct rk_priv_data *rk_gmac_setup(struct platform_device *pdev,<br>                    struct plat_stmmacenet_data *plat,<br>                    const struct rk_gmac_ops *ops)<br>{<br>    struct rk_priv_data *bsp_priv;<br>    struct device *dev = &pdev->dev;<br>    struct resource *res;<br>    int ret;<br>    const char *strings = NULL;<br>    int value;<br><br>    // 分配rk_priv_data结构体<br>    bsp_priv = devm_kzalloc(dev, sizeof(*bsp_priv), GFP_KERNEL);<br>    if (!bsp_priv)<br>        return ERR_PTR(-ENOMEM);<br><br>    // 从dts的phy-mode属性读取接口模式<br>    of_get_phy_mode(dev->of_node, &bsp_priv->phy_iface);<br>    // 保存芯片特定的操作集指针，如rk3588_ops<br>    bsp_priv->ops = ops;<br><br>    /* Some SoCs have multiple MAC controllers, which need<br>    * to be distinguished.<br>    */<br>    // 获取寄存器资源，对比设备的物理基地址与rk3588_ops.regs[]数组，确定当前Probe的是哪个网口<br>    res = platform_get_resource(pdev, IORESOURCE_MEM, 0);<br>    if (res && ops->regs_valid) {<br>        int i = 0;<br><br>        while (ops->regs[i]) {<br>            if (ops->regs[i] == res->start) {<br>                bsp_priv->id = i;<br>                break;<br>            }<br>            i++;<br>        }<br>    }<br><br>    // 获取PHY电源管理，后续在rk_gmac_powerup中给PHY上电<br>    bsp_priv->regulator = devm_regulator_get(dev, "phy");<br>    if (IS_ERR(bsp_priv->regulator)) {<br>        ret = PTR_ERR(bsp_priv->regulator);<br>        dev_err_probe(dev, ret, "failed to get phy regulator\n");<br>        return ERR_PTR(ret);<br>    }<br><br>    // 解析时钟方向，设置input参考时钟由PHY产生并输入给MAC，设置output参考时钟由SoC内部产生并输出给PHY<br>    ret = of_property_read_string(dev->of_node, "clock_in_out", &strings);<br>    if (ret) {<br>        dev_err(dev, "Can not read property: clock_in_out.\n");<br>        bsp_priv->clock_input = true;<br>    } else {<br>        dev_info(dev, "clock input or output? (%s).\n",<br>            strings);<br>        if (!strcmp(strings, "input"))<br>            bsp_priv->clock_input = true;<br>        else<br>            bsp_priv->clock_input = false;<br>    }<br><br>    // 解析tx_delay延迟值<br>    ret = of_property_read_u32(dev->of_node, "tx_delay", &value);<br>    if (ret) {<br>        bsp_priv->tx_delay = -1;<br>        dev_err(dev, "Can not read property: tx_delay.");<br>        dev_err(dev, "set tx_delay to 0x%x\n",<br>            bsp_priv->tx_delay);<br>    } else {<br>        dev_info(dev, "TX delay(0x%x).\n", value);<br>        bsp_priv->tx_delay = value;<br>    }<br><br>    // 解析rx_delay延迟值<br>    ret = of_property_read_u32(dev->of_node, "rx_delay", &value);<br>    if (ret) {<br>        bsp_priv->rx_delay = -1;<br>        dev_err(dev, "Can not read property: rx_delay.");<br>        dev_err(dev, "set rx_delay to 0x%x\n",<br>            bsp_priv->rx_delay);<br>    } else {<br>        dev_info(dev, "RX delay(0x%x).\n", value);<br>        bsp_priv->rx_delay = value;<br>    }<br><br>    // 获取SYS_GRF（系统通用寄存器），用来配置延迟使能、延迟值<br>    bsp_priv->grf = syscon_regmap_lookup_by_phandle(dev->of_node,<br>                            "rockchip,grf");<br>    // 获取PHP_GRF（PCIe/PHY子系统通用寄存器），用来配置接口模式、时钟分频<br>    bsp_priv->php_grf = syscon_regmap_lookup_by_phandle(dev->of_node,<br>                                "rockchip,php_grf");<br><br>    bsp_priv->xpcs = syscon_regmap_lookup_by_phandle(dev->of_node,<br>                            "rockchip,xpcs");<br>    if (!IS_ERR(bsp_priv->xpcs)) {<br>        struct phy *comphy;<br><br>        comphy = devm_of_phy_get(&pdev->dev, dev->of_node, NULL);<br>        if (IS_ERR(comphy))<br>            dev_err(dev, "devm_of_phy_get error\n");<br>        ret = phy_init(comphy);<br>        if (ret)<br>            dev_err(dev, "phy_init error\n");<br>    }<br><br>    if (plat->phy_node) {<br>        bsp_priv->integrated_phy = of_property_read_bool(plat->phy_node,<br>                                "phy-is-integrated");<br>        if (bsp_priv->integrated_phy) {<br>            unsigned char *efuse_buf;<br>            struct nvmem_cell *cell;<br>            size_t len;<br><br>            // 获取PHY复位控制<br>            bsp_priv->phy_reset = of_reset_control_get(plat->phy_node, NULL);<br>            if (IS_ERR(bsp_priv->phy_reset)) {<br>                dev_err(&pdev->dev, "No PHY reset control found.\n");<br>                bsp_priv->phy_reset = NULL;<br>            }<br>            ...<br>        }<br>    }<br>    dev_info(dev, "integrated PHY? (%s).\n",<br>        bsp_priv->integrated_phy ? "yes" : "no");<br><br>    bsp_priv->pdev = pdev;<br><br>    return bsp_priv;<br>}|

#### 9.5.3.5. GRF寄存器配置[¶](#grf "永久链接至标题")

RK3588的MAC控制器不只有MMIO寄存器，还有大量配置通过GRF（General Register File） 寄存器完成。

##### 9.5.3.5.1. 设置RGMII模式[¶](#rgmii "永久链接至标题")

通过操作GRF寄存器选择RGMII接口模式、配置RGMII时钟模式、配置TX/RX延迟，，从而让MAC控制器能够以正确的时序通过RGMII总线与外部PHY进行以太网通信。

rk3588_set_to_rgmii函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c)[¶](#id108 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31|static void rk3588_set_to_rgmii(struct rk_priv_data *bsp_priv,<br>                int tx_delay, int rx_delay)<br>{<br>    struct device *dev = &bsp_priv->pdev->dev;<br>    u32 offset_con, id = bsp_priv->id;<br><br>    if (IS_ERR(bsp_priv->grf) \| IS_ERR(bsp_priv->php_grf)) {<br>        dev_err(dev, "Missing rockchip,grf or rockchip,php_grf property\n");<br>        return;<br>    }<br><br>    // 根据网口ID选择延迟值寄存器<br>    offset_con = bsp_priv->id == 1 ? RK3588_GRF_GMAC_CON9 :<br>                    RK3588_GRF_GMAC_CON8;<br><br>    // 选择PHY接口为RGMII<br>    regmap_write(bsp_priv->php_grf, RK3588_GRF_GMAC_CON0,<br>            RK3588_GMAC_PHY_INTF_SEL_RGMII(id));<br><br>    // 设置时钟为RGMII模式<br>    regmap_write(bsp_priv->php_grf, RK3588_GRF_CLK_CON1,<br>            RK3588_GMAC_CLK_RGMII_MODE(id));<br><br>    // 使能TX/RX延迟<br>    regmap_write(bsp_priv->grf, RK3588_GRF_GMAC_CON7,<br>            DELAY_ENABLE_BY_ID(RK3588, tx_delay, rx_delay, id));<br><br>    // 设置延迟值<br>    regmap_write(bsp_priv->grf, offset_con,<br>            DELAY_VALUE(RK3588, tx_delay, rx_delay));<br>}|

##### 9.5.3.5.2. 设置速率[¶](#id44 "永久链接至标题")

当网线插上、PHY自协商完成后，内核根据协商出的速率（10M/100M/1000M），调用此函数切换MAC侧的时钟分频器，使MAC控制器输出的参考时钟频率与PHY芯片在当前速率下所要求的时钟匹配。

rk3588_set_gmac_speed函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c)[¶](#id109 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34|static void rk3588_set_gmac_speed(struct rk_priv_data *bsp_priv, int speed)<br>{<br>    struct device *dev = &bsp_priv->pdev->dev;<br>    unsigned int val = 0, id = bsp_priv->id;<br><br>    switch (speed) {<br>    case 10: // 10Mbps<br>        if (bsp_priv->phy_iface == PHY_INTERFACE_MODE_RMII)<br>            val = RK3588_GMA_CLK_RMII_DIV20(id);    // RMII:  50MHz / 20 = 2.5MHz<br>        else<br>            val = RK3588_GMAC_CLK_RGMII_DIV50(id);  // RGMII: 125MHz / 50 = 2.5MHz<br>        break;<br>    case 100: // 100Mbps<br>        if (bsp_priv->phy_iface == PHY_INTERFACE_MODE_RMII)<br>            val = RK3588_GMA_CLK_RMII_DIV2(id);     // RMII:  50MHz / 2 = 25MHz<br>        else<br>            val = RK3588_GMAC_CLK_RGMII_DIV5(id);   // RGMII: 125MHz / 5 = 25MHz<br>        break;<br>    case 1000:// 1000Mbps<br>        if (bsp_priv->phy_iface != PHY_INTERFACE_MODE_RMII)<br>            val = RK3588_GMAC_CLK_RGMII_DIV1(id);   // RGMII: 125MHz / 1 = 125MHz<br>        else<br>            goto err;   // RMII不支持1000M<br>        break;<br>    default:<br>        goto err;   // 不支持的速率<br>    }<br><br>    regmap_write(bsp_priv->php_grf, RK3588_GRF_CLK_CON1, val);<br><br>    return;<br>err:<br>    dev_err(dev, "unknown speed value for GMAC speed=%d", speed);<br>}|

### 9.5.4. MAC核心层驱动解析[¶](#id45 "永久链接至标题")

MAC核心层驱动向上对接网络协议栈，向下通过硬件抽象层操作寄存器，横向通过phylink管理PHY。

#### 9.5.4.1. 设备树解析[¶](#id46 "永久链接至标题")

stmmac_probe_config_dt函数是STMMAC平台驱动的设备树解析核心函数，它从设备树中提取MAC控制器的所有硬件配置参数， 包括PHY接口模式、FIFO深度、DMA突发长度、时钟、复位信号等，并将这些信息填充到plat_stmmacenet_data结构体中，供后续核心驱动使用。

stmmac_probe_config_dt函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/stmmac_platform.c)[¶](#id110 "永久链接至代码")

|   |   |
|---|---|
|1<br>  2<br>  3<br>  4<br>  5<br>  6<br>  7<br>  8<br>  9<br> 10<br> 11<br> 12<br> 13<br> 14<br> 15<br> 16<br> 17<br> 18<br> 19<br> 20<br> 21<br> 22<br> 23<br> 24<br> 25<br> 26<br> 27<br> 28<br> 29<br> 30<br> 31<br> 32<br> 33<br> 34<br> 35<br> 36<br> 37<br> 38<br> 39<br> 40<br> 41<br> 42<br> 43<br> 44<br> 45<br> 46<br> 47<br> 48<br> 49<br> 50<br> 51<br> 52<br> 53<br> 54<br> 55<br> 56<br> 57<br> 58<br> 59<br> 60<br> 61<br> 62<br> 63<br> 64<br> 65<br> 66<br> 67<br> 68<br> 69<br> 70<br> 71<br> 72<br> 73<br> 74<br> 75<br> 76<br> 77<br> 78<br> 79<br> 80<br> 81<br> 82<br> 83<br> 84<br> 85<br> 86<br> 87<br> 88<br> 89<br> 90<br> 91<br> 92<br> 93<br> 94<br> 95<br> 96<br> 97<br> 98<br> 99<br>100<br>101<br>102<br>103<br>104<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119<br>120<br>121<br>122<br>123<br>124<br>125<br>126<br>127<br>128<br>129<br>130<br>131<br>132<br>133<br>134<br>135<br>136<br>137<br>138<br>139<br>140<br>141<br>142<br>143<br>144<br>145<br>146<br>147<br>148<br>149<br>150<br>151|struct plat_stmmacenet_data *<br>stmmac_probe_config_dt(struct platform_device *pdev, u8 *mac)<br>{<br>    struct device_node *np = pdev->dev.of_node;<br>    struct plat_stmmacenet_data *plat;<br>    struct stmmac_dma_cfg *dma_cfg;<br>    int phy_mode;<br>    void *ret;<br>    int rc;<br><br>    // 分配平台数据结构体，使用devm_管理的内存，驱动卸载时自动释放<br>    plat = devm_kzalloc(&pdev->dev, sizeof(*plat), GFP_KERNEL);<br>    if (!plat)<br>        return ERR_PTR(-ENOMEM);<br><br>    // 从dts中读取MAC地址<br>    rc = of_get_mac_address(np, mac);<br>    if (rc) {<br>        if (rc == -EPROBE_DEFER)<br>            return ERR_PTR(rc);<br><br>        eth_zero_addr(mac);<br>    }<br><br>    // 读取phy-mode属性，对于RK3588对应rgmii-rxid<br>    phy_mode = device_get_phy_mode(&pdev->dev);<br>    if (phy_mode < 0)<br>        return ERR_PTR(phy_mode);<br><br>    plat->phy_interface = phy_mode;<br>    plat->interface = stmmac_of_get_mac_mode(np);<br>    if (plat->interface < 0)<br>        plat->interface = plat->phy_interface;<br><br>    // 解析phy-handle属性，获取PHY设备节点引用<br>    plat->phy_node = of_parse_phandle(np, "phy-handle", 0);<br><br>    // 保存PHYLINK节点，PHYLINK框架会自动解析phy-handle<br>    plat->phylink_node = np;<br><br>    // 获取最大速率限制<br>    of_property_read_u32(np, "max-speed", &plat->max_speed);<br><br>    ...<br><br>    // 读取发送FIFO深度<br>    of_property_read_u32(np, "tx-fifo-depth", &plat->tx_fifo_size);<br>    of_property_read_u32(np, "rx-fifo-depth", &plat->rx_fifo_size);<br><br>    // 获取DMA描述符环大小<br>    of_property_read_u32(np, "tx-dma-size", &plat->dma_tx_size);<br>    of_property_read_u32(np, "rx-dma-size", &plat->dma_rx_size);<br><br>    ...<br><br>    if (of_device_is_compatible(np, "snps,dwmac-4.00") \|<br>        of_device_is_compatible(np, "snps,dwmac-4.10a") \|<br>        of_device_is_compatible(np, "snps,dwmac-4.20a") \|   // 匹配dts中的compatible属性，RK3588的GMAC对应snps,dwmac-4.20a<br>        of_device_is_compatible(np, "snps,dwmac-5.10a")) {<br>        plat->has_gmac4 = 1;<br>        plat->has_gmac = 0;<br>        plat->pmt = 1;<br>        plat->tso_en = of_property_read_bool(np, "snps,tso"); //读取snps,tso属性，RK3588 dts中配置了此属性，启用TSO<br>    }<br><br>    ...<br><br>    dma_cfg = devm_kzalloc(&pdev->dev, sizeof(*dma_cfg),<br>                GFP_KERNEL);<br>    if (!dma_cfg) {<br>        stmmac_remove_config_dt(pdev, plat);<br>        return ERR_PTR(-ENOMEM);<br>    }<br>    plat->dma_cfg = dma_cfg;<br><br>    of_property_read_u32(np, "snps,pbl", &dma_cfg->pbl);<br>    if (!dma_cfg->pbl)<br>        dma_cfg->pbl = DEFAULT_DMA_PBL;<br>    of_property_read_u32(np, "snps,txpbl", &dma_cfg->txpbl);<br>    of_property_read_u32(np, "snps,rxpbl", &dma_cfg->rxpbl);<br>    dma_cfg->pblx8 = !of_property_read_bool(np, "snps,no-pbl-x8");<br><br>    dma_cfg->aal = of_property_read_bool(np, "snps,aal");<br>    dma_cfg->fixed_burst = of_property_read_bool(np, "snps,fixed-burst");<br>    dma_cfg->mixed_burst = of_property_read_bool(np, "snps,mixed-burst"); // RK3588 dts中配置了此属性，启用混合突发传输<br><br>    plat->force_thresh_dma_mode = of_property_read_bool(np, "snps,force_thresh_dma_mode");<br>    if (plat->force_thresh_dma_mode && plat->force_sf_dma_mode) {<br>        plat->force_sf_dma_mode = 0;<br>        dev_warn(&pdev->dev,<br>            "force_sf_dma_mode is ignored if force_thresh_dma_mode is set.\n");<br>    }<br><br>    of_property_read_u32(np, "snps,ps-speed", &plat->mac_port_sel_speed);<br><br>    if (of_property_read_u32(np, "snps,flow-ctrl", &plat->flow_ctrl))<br>        plat->flow_ctrl = FLOW_AUTO;<br><br>    plat->axi = stmmac_axi_setup(pdev);  // 解析snps,axi-config子节点，配置AXI总线参数<br><br>    rc = stmmac_mtl_setup(pdev, plat);  // 解析snps,mtl-rx-config/snps,mtl-tx-config子节点，配置多队列参数<br>    if (rc) {<br>        stmmac_remove_config_dt(pdev, plat);<br>        return ERR_PTR(rc);<br>    }<br><br>    /* clock setup */<br>    if (!of_device_is_compatible(np, "snps,dwc-qos-ethernet-4.10")) {<br>        plat->stmmac_clk = devm_clk_get(&pdev->dev,  // 获取主时钟，对应dts中的stmmaceth<br>                        STMMAC_RESOURCE_NAME);<br>        if (IS_ERR(plat->stmmac_clk)) {<br>            dev_warn(&pdev->dev, "Cannot get CSR clock\n");<br>            plat->stmmac_clk = NULL;<br>        }<br>        clk_prepare_enable(plat->stmmac_clk);<br>    }<br><br>    plat->pclk = devm_clk_get_optional(&pdev->dev, "pclk_mac"); // 获取APB总线时钟，对应pclk_mac<br>    if (IS_ERR(plat->pclk)) {<br>        ret = plat->pclk;<br>        goto error_pclk_get;<br>    }<br>    clk_prepare_enable(plat->pclk);<br><br>    /* Fall-back to main clock in case of no PTP ref is passed */<br>    plat->clk_ptp_ref = devm_clk_get(&pdev->dev, "ptp_ref"); // 获取PTP参考时钟<br>    if (IS_ERR(plat->clk_ptp_ref)) {<br>        plat->clk_ptp_rate = clk_get_rate(plat->stmmac_clk);<br>        plat->clk_ptp_ref = NULL;<br>        dev_info(&pdev->dev, "PTP uses main clock\n");<br>    } else {<br>        plat->clk_ptp_rate = clk_get_rate(plat->clk_ptp_ref);<br>        dev_dbg(&pdev->dev, "PTP rate %d\n", plat->clk_ptp_rate);<br>    }<br><br>    plat->stmmac_rst = devm_reset_control_get_optional(&pdev->dev,  // 获取复位控制器，对应stmmaceth复位信号<br>                            STMMAC_RESOURCE_NAME);<br>    if (IS_ERR(plat->stmmac_rst)) {<br>        ret = plat->stmmac_rst;<br>        goto error_hw_init;<br>    }<br><br>    plat->stmmac_ahb_rst = devm_reset_control_get_optional_shared(<br>                            &pdev->dev, "ahb");<br>    if (IS_ERR(plat->stmmac_ahb_rst)) {<br>        ret = plat->stmmac_ahb_rst;<br>        goto error_hw_init;<br>    }<br><br>    return plat;<br>}|

#### 9.5.4.2. 平台资源获取[¶](#id47 "永久链接至标题")

stmmac_get_platform_resources函数用于获取MAC控制器的硬件中断和内存资源。对应RK3588 dts中的interrupts和reg属性。 中断号macirq是MAC的主中断（DMA中断），eth_wake_irq是WoL（Wake-on-LAN）唤醒中断。

stmmac_get_platform_resources函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/stmmac_platform.c)[¶](#id111 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34|int stmmac_get_platform_resources(struct platform_device *pdev,<br>                struct stmmac_resources *stmmac_res)<br>{<br>    memset(stmmac_res, 0, sizeof(*stmmac_res));<br><br>    // 获取dts中interrupt-names = "macirq" 对应的中断号，RK3588为GIC_SPI 234<br>    stmmac_res->irq = platform_get_irq_byname(pdev, "macirq");<br>    if (stmmac_res->irq < 0)<br>        return stmmac_res->irq;<br><br>    // 获取唤醒中断，RK3588为GIC_SPI 233，若不存在则回退到主中断<br>    stmmac_res->wol_irq =<br>        platform_get_irq_byname_optional(pdev, "eth_wake_irq");<br>    if (stmmac_res->wol_irq < 0) {<br>        if (stmmac_res->wol_irq == -EPROBE_DEFER)<br>            return -EPROBE_DEFER;<br>        dev_info(&pdev->dev, "IRQ eth_wake_irq not found\n");<br>        stmmac_res->wol_irq = stmmac_res->irq;<br>    }<br><br>    // 获取LPI低功耗空闲中断<br>    stmmac_res->lpi_irq =<br>        platform_get_irq_byname_optional(pdev, "eth_lpi");<br>    if (stmmac_res->lpi_irq < 0) {<br>        if (stmmac_res->lpi_irq == -EPROBE_DEFER)<br>            return -EPROBE_DEFER;<br>        dev_info(&pdev->dev, "IRQ eth_lpi not found\n");<br>    }<br><br>    // 将dts中reg = <0x0 0xfe1c0000 0x0 0x10000>映射为内核虚拟地址<br>    stmmac_res->addr = devm_platform_ioremap_resource(pdev, 0);<br><br>    return PTR_ERR_OR_ZERO(stmmac_res->addr);<br>}|

#### 9.5.4.3. probe函数[¶](#id48 "永久链接至标题")

stmmac_dvr_probe函数是STMMAC驱动的核心探测函数，由瑞芯微平台胶水层驱动dwmac-rk.c的rk_gmac_probe调用。 它完成以下工作：分配网络设备、初始化硬件、注册MDIO总线、设置PHYLINK、注册网卡。

stmmac_dvr_probe函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)[¶](#id112 "永久链接至代码")

|   |   |
|---|---|
|1<br>  2<br>  3<br>  4<br>  5<br>  6<br>  7<br>  8<br>  9<br> 10<br> 11<br> 12<br> 13<br> 14<br> 15<br> 16<br> 17<br> 18<br> 19<br> 20<br> 21<br> 22<br> 23<br> 24<br> 25<br> 26<br> 27<br> 28<br> 29<br> 30<br> 31<br> 32<br> 33<br> 34<br> 35<br> 36<br> 37<br> 38<br> 39<br> 40<br> 41<br> 42<br> 43<br> 44<br> 45<br> 46<br> 47<br> 48<br> 49<br> 50<br> 51<br> 52<br> 53<br> 54<br> 55<br> 56<br> 57<br> 58<br> 59<br> 60<br> 61<br> 62<br> 63<br> 64<br> 65<br> 66<br> 67<br> 68<br> 69<br> 70<br> 71<br> 72<br> 73<br> 74<br> 75<br> 76<br> 77<br> 78<br> 79<br> 80<br> 81<br> 82<br> 83<br> 84<br> 85<br> 86<br> 87<br> 88<br> 89<br> 90<br> 91<br> 92<br> 93<br> 94<br> 95<br> 96<br> 97<br> 98<br> 99<br>100<br>101<br>102<br>103<br>104<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119<br>120<br>121<br>122<br>123<br>124<br>125<br>126<br>127<br>128<br>129<br>130<br>131<br>132<br>133<br>134<br>135<br>136<br>137<br>138<br>139<br>140<br>141<br>142<br>143<br>144<br>145<br>146<br>147<br>148<br>149<br>150<br>151<br>152<br>153<br>154<br>155<br>156<br>157<br>158<br>159<br>160<br>161<br>162<br>163<br>164<br>165<br>166<br>167<br>168<br>169<br>170<br>171<br>172<br>173<br>174<br>175<br>176<br>177<br>178<br>179<br>180<br>181<br>182<br>183<br>184<br>185<br>186<br>187<br>188<br>189<br>190<br>191<br>192<br>193<br>194<br>195<br>196<br>197<br>198<br>199<br>200<br>201<br>202<br>203<br>204<br>205<br>206<br>207<br>208<br>209<br>210<br>211<br>212<br>213<br>214<br>215<br>216<br>217<br>218<br>219<br>220<br>221<br>222<br>223<br>224<br>225<br>226<br>227<br>228<br>229<br>230<br>231<br>232<br>233<br>234<br>235<br>236<br>237<br>238<br>239<br>240<br>241<br>242<br>243<br>244<br>245<br>246<br>247<br>248<br>249<br>250<br>251<br>252<br>253<br>254<br>255<br>256<br>257<br>258<br>259<br>260<br>261<br>262<br>263<br>264<br>265<br>266<br>267<br>268<br>269<br>270<br>271<br>272<br>273<br>274<br>275<br>276<br>277<br>278<br>279<br>280<br>281<br>282|int stmmac_dvr_probe(struct device *device,<br>            struct plat_stmmacenet_data *plat_dat,<br>            struct stmmac_resources *res)<br>{<br>    struct net_device *ndev = NULL;<br>    struct stmmac_priv *priv;<br>    u32 rxq;<br>    int i, ret = 0;<br><br>    // 分配net_device和私有数据stmmac_priv<br>    ndev = devm_alloc_etherdev_mqs(device, sizeof(struct stmmac_priv),<br>                    MTL_MAX_TX_QUEUES, MTL_MAX_RX_QUEUES);<br>    if (!ndev)<br>        return -ENOMEM;<br><br>    SET_NETDEV_DEV(ndev, device);<br><br>    priv = netdev_priv(ndev);<br>    priv->device = device;<br>    priv->dev = ndev;<br><br>    stmmac_set_ethtool_ops(ndev);<br>    priv->pause = pause;<br>    priv->plat = plat_dat;<br>    priv->ioaddr = res->addr; // 保存MAC寄存器基地址，RK3588 GMAC1为0xfe1c0000<br>    priv->dev->base_addr = (unsigned long)res->addr;<br>    priv->plat->dma_cfg->multi_msi_en = priv->plat->multi_msi_en;<br><br>    priv->dev->irq = res->irq;    // MAC的主中断<br>    priv->wol_irq = res->wol_irq; // wol唤醒中断<br>    priv->lpi_irq = res->lpi_irq; // lpi低功耗空闲中断<br>    priv->sfty_ce_irq = res->sfty_ce_irq;<br>    priv->sfty_ue_irq = res->sfty_ue_irq;<br>    for (i = 0; i < MTL_MAX_RX_QUEUES; i++)<br>        priv->rx_irq[i] = res->rx_irq[i];<br>    for (i = 0; i < MTL_MAX_TX_QUEUES; i++)<br>        priv->tx_irq[i] = res->tx_irq[i];<br><br>    if (!is_zero_ether_addr(res->mac))<br>        eth_hw_addr_set(priv->dev, res->mac); // 设备树MAC地址<br><br>    dev_set_drvdata(device, priv->dev);<br><br>    /* Verify driver arguments */<br>    stmmac_verify_args();<br><br>    priv->af_xdp_zc_qps = bitmap_zalloc(MTL_MAX_TX_QUEUES, GFP_KERNEL);<br>    if (!priv->af_xdp_zc_qps)<br>        return -ENOMEM;<br><br>    /* Allocate workqueue */<br>    priv->wq = create_singlethread_workqueue("stmmac_wq");<br>    if (!priv->wq) {<br>        dev_err(priv->device, "failed to create workqueue\n");<br>        ret = -ENOMEM;<br>        goto error_wq_init;<br>    }<br><br>    INIT_WORK(&priv->service_task, stmmac_service_task);<br><br>    /* Initialize Link Partner FPE workqueue */<br>    INIT_WORK(&priv->fpe_task, stmmac_fpe_lp_task);<br><br>    /* Override with kernel parameters if supplied XXX CRS XXX<br>    * this needs to have multiple instances<br>    */<br>    if ((phyaddr >= 0) && (phyaddr <= 31))<br>        priv->plat->phy_addr = phyaddr;<br><br>    if (priv->plat->stmmac_rst) {<br>        ret = reset_control_assert(priv->plat->stmmac_rst); // 执行MAC硬件复位<br>        reset_control_deassert(priv->plat->stmmac_rst);<br>        /* Some reset controllers have only reset callback instead of<br>        * assert + deassert callbacks pair.<br>        */<br>        if (ret == -ENOTSUPP)<br>            reset_control_reset(priv->plat->stmmac_rst);<br>    }<br><br>    ret = reset_control_deassert(priv->plat->stmmac_ahb_rst);<br>    if (ret == -ENOTSUPP)<br>        dev_err(priv->device, "unable to bring out of ahb reset: %pe\n",<br>            ERR_PTR(ret));<br><br>    /* Wait a bit for the reset to take effect */<br>    udelay(10);<br><br>    /* Init MAC and get the capabilities */<br>    ret = stmmac_hw_init(priv); //初始化MAC硬件接口，读取硬件能力寄存器<br>    if (ret)<br>        goto error_hw_init;<br><br>    /* Only DWMAC core version 5.20 onwards supports HW descriptor prefetch.<br>    */<br>    if (priv->synopsys_id < DWMAC_CORE_5_20)<br>        priv->plat->dma_cfg->dche = false;<br><br>    stmmac_check_ether_addr(priv);<br><br>    ndev->netdev_ops = &stmmac_netdev_ops; // 绑定网络设备操作集，open/xmit/stop等<br><br>    ndev->hw_features = NETIF_F_SG \| NETIF_F_IP_CSUM \| NETIF_F_IPV6_CSUM \|  // 设置硬件特性<br>                NETIF_F_RXCSUM;<br><br>    ret = stmmac_tc_init(priv, priv);<br>    if (!ret) {<br>        ndev->hw_features \|= NETIF_F_HW_TC;<br>    }<br><br>    if ((priv->plat->tso_en) && (priv->dma_cap.tsoen)) {<br>        ndev->hw_features \|= NETIF_F_TSO \| NETIF_F_TSO6;  // RK3588配置了snps,tso，启用TSO硬件卸载<br>        if (priv->plat->has_gmac4)<br>            ndev->hw_features \|= NETIF_F_GSO_UDP_L4;<br>        priv->tso = true;<br>        dev_info(priv->device, "TSO feature enabled\n");<br>    }<br><br>    if (priv->dma_cap.sphen && !priv->plat->sph_disable) {<br>        ndev->hw_features \|= NETIF_F_GRO;<br>        priv->sph_cap = true;<br>        priv->sph = priv->sph_cap;<br>        dev_info(priv->device, "SPH feature enabled\n");<br>    }<br><br>    /* Ideally our host DMA address width is the same as for the<br>    * device. However, it may differ and then we have to use our<br>    * host DMA width for allocation and the device DMA width for<br>    * register handling.<br>    */<br>    if (priv->plat->host_dma_width)<br>        priv->dma_cap.host_dma_width = priv->plat->host_dma_width;<br>    else<br>        priv->dma_cap.host_dma_width = priv->dma_cap.addr64;<br><br>    if (priv->dma_cap.host_dma_width) {<br>        ret = dma_set_mask_and_coherent(device,  // 设置DMA掩码<br>                DMA_BIT_MASK(priv->dma_cap.host_dma_width));<br>        if (!ret) {<br>            dev_info(priv->device, "Using %d/%d bits DMA host/device width\n",<br>                priv->dma_cap.host_dma_width, priv->dma_cap.addr64);<br><br>            /*<br>            * If more than 32 bits can be addressed, make sure to<br>            * enable enhanced addressing mode.<br>            */<br>            if (IS_ENABLED(CONFIG_ARCH_DMA_ADDR_T_64BIT))<br>                priv->plat->dma_cfg->eame = true;<br>        } else {<br>            ret = dma_set_mask_and_coherent(device, DMA_BIT_MASK(32));<br>            if (ret) {<br>                dev_err(priv->device, "Failed to set DMA Mask\n");<br>                goto error_hw_init;<br>            }<br><br>            priv->dma_cap.host_dma_width = 32;<br>        }<br>    }<br><br>    ndev->features \|= ndev->hw_features \| NETIF_F_HIGHDMA;<br>    ndev->watchdog_timeo = msecs_to_jiffies(watchdog);<br>#ifdef STMMAC_VLAN_TAG_USED<br>    /* Both mac100 and gmac support receive VLAN tag detection */<br>    ndev->features \|= NETIF_F_HW_VLAN_CTAG_RX \| NETIF_F_HW_VLAN_STAG_RX;<br>    if (priv->dma_cap.vlhash) {<br>        ndev->features \|= NETIF_F_HW_VLAN_CTAG_FILTER;<br>        ndev->features \|= NETIF_F_HW_VLAN_STAG_FILTER;<br>    }<br>    if (priv->dma_cap.vlins) {<br>        ndev->features \|= NETIF_F_HW_VLAN_CTAG_TX;<br>        if (priv->dma_cap.dvlan)<br>            ndev->features \|= NETIF_F_HW_VLAN_STAG_TX;<br>    }<br>#endif<br>    priv->msg_enable = netif_msg_init(debug, default_msg_level);<br><br>    /* Initialize RSS */<br>    rxq = priv->plat->rx_queues_to_use;<br>    netdev_rss_key_fill(priv->rss.key, sizeof(priv->rss.key));<br>    for (i = 0; i < ARRAY_SIZE(priv->rss.table); i++)<br>        priv->rss.table[i] = ethtool_rxfh_indir_default(i, rxq);<br><br>    if (priv->dma_cap.rssen && priv->plat->rss_en)<br>        ndev->features \|= NETIF_F_RXHASH;<br><br>    /* MTU range: 46 - hw-specific max */<br>    ndev->min_mtu = ETH_ZLEN - ETH_HLEN;<br>    if (priv->plat->has_xgmac)<br>        ndev->max_mtu = XGMAC_JUMBO_LEN;<br>    else if ((priv->plat->enh_desc) \| (priv->synopsys_id >= DWMAC_CORE_4_00))<br>        ndev->max_mtu = JUMBO_LEN;<br>    else<br>        ndev->max_mtu = SKB_MAX_HEAD(NET_SKB_PAD + NET_IP_ALIGN);<br>    /* Will not overwrite ndev->max_mtu if plat->maxmtu > ndev->max_mtu<br>    * as well as plat->maxmtu < ndev->min_mtu which is a invalid range.<br>    */<br>    if ((priv->plat->maxmtu < ndev->max_mtu) &&<br>        (priv->plat->maxmtu >= ndev->min_mtu))<br>        ndev->max_mtu = priv->plat->maxmtu;<br>    else if (priv->plat->maxmtu < ndev->min_mtu)<br>        dev_warn(priv->device,<br>            "%s: warning: maxmtu having invalid value (%d)\n",<br>            __func__, priv->plat->maxmtu);<br><br>    if (flow_ctrl)<br>        priv->flow_ctrl = FLOW_AUTO;        /* RX/TX pause on */<br><br>    /* Setup channels NAPI */<br>    stmmac_napi_add(ndev);  // 为每个队列注册NAPI轮询函数<br><br>    mutex_init(&priv->lock);<br><br>    /* If a specific clk_csr value is passed from the platform<br>    * this means that the CSR Clock Range selection cannot be<br>    * changed at run-time and it is fixed. Viceversa the driver'll try to<br>    * set the MDC clock dynamically according to the csr actual<br>    * clock input.<br>    */<br>    if (priv->plat->clk_csr >= 0)<br>        priv->clk_csr = priv->plat->clk_csr;<br>    else<br>        stmmac_clk_csr_set(priv);<br><br>    stmmac_check_pcs_mode(priv);<br><br>    pm_runtime_get_noresume(device);<br>    pm_runtime_set_active(device);<br>    if (!pm_runtime_enabled(device))<br>        pm_runtime_enable(device);<br><br>    if (priv->hw->pcs != STMMAC_PCS_TBI &&<br>        priv->hw->pcs != STMMAC_PCS_RTBI) {<br>        /* MDIO bus Registration */<br>        ret = stmmac_mdio_register(ndev);  // 注册MDIO总线，使内核能扫描到RTL8211F PHY<br>        if (ret < 0) {<br>            dev_err_probe(priv->device, ret,<br>                    "%s: MDIO bus (id: %d) registration failed\n",<br>                    __func__, priv->plat->bus_id);<br>            goto error_mdio_register;<br>        }<br>    }<br><br>    if (priv->plat->speed_mode_2500)<br>        priv->plat->speed_mode_2500(ndev, priv->plat->bsp_priv);<br><br>    if (priv->plat->mdio_bus_data && priv->plat->mdio_bus_data->has_xpcs) {<br>        ret = stmmac_xpcs_setup(priv->mii);<br>        if (ret)<br>            goto error_xpcs_setup;<br>    }<br><br>    ret = stmmac_phy_setup(priv); // 创建PHYLINK实例，建立MAC与PHY的关联<br>    if (ret) {<br>        netdev_err(ndev, "failed to setup phy (%d)\n", ret);<br>        goto error_phy_setup;<br>    }<br><br>    ret = phy_register_fixup_for_uid(RTL_8211F_PHY_ID, 0xffffffff, phy_rtl8211f_led_fixup);  // 注册RTL8211F的LED配置，PHY匹配后自动调用<br>    if (ret) {<br>        pr_warn("Cannot register 8211f PHY board fixup.\n");<br>    }<br><br>    ret = register_netdev(ndev);  // 向内核注册网卡，此时ifconfig可看到ethX设备<br>    if (ret) {<br>        dev_err(priv->device, "%s: ERROR %i registering the device\n",<br>            __func__, ret);<br>        goto error_netdev_register;<br>    }<br><br>#ifdef CONFIG_DEBUG_FS<br>    stmmac_init_fs(ndev);<br>#endif<br><br>    if (priv->plat->dump_debug_regs)<br>        priv->plat->dump_debug_regs(priv->plat->bsp_priv);<br><br>    /* Let pm_runtime_put() disable the clocks.<br>    * If CONFIG_PM is not enabled, the clocks will stay powered.<br>    */<br>    pm_runtime_put(device);<br><br>    return ret;<br>}|

#### 9.5.4.4. PHYLINK实例创建[¶](#phylink "永久链接至标题")

stmmac_phy_setup函数用于创建PHYLINK实例，PHYLINK是Linux内核中管理MAC与PHY之间链路状态的标准框架。 它根据dts中的phy-mode（RK3588为rgmii-rxid）设置支持的接口模式，并根据硬件能力设置MAC支持的最大速率。 PHYLINK会自动解析phy-handle属性并在后续phylink_start时连接PHY。

stmmac_phy_setup函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)[¶](#id113 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48<br>49<br>50<br>51<br>52<br>53<br>54<br>55<br>56<br>57<br>58<br>59<br>60<br>61<br>62<br>63<br>64<br>65|static int stmmac_phy_setup(struct stmmac_priv *priv)<br>{<br>    struct stmmac_mdio_bus_data *mdio_bus_data = priv->plat->mdio_bus_data;<br>    struct fwnode_handle *fwnode = of_fwnode_handle(priv->plat->phylink_node);<br>    int max_speed = priv->plat->max_speed;<br>    int mode = priv->plat->phy_interface;<br>    struct phylink *phylink;<br><br>    priv->phylink_config.dev = &priv->dev->dev; // 关联网络设备<br>    priv->phylink_config.type = PHYLINK_NETDEV; // 表示这是一个网络设备类型的PHYLINK<br>    if (priv->plat->mdio_bus_data)<br>        priv->phylink_config.ovr_an_inband =<br>            mdio_bus_data->xpcs_an_inband;<br><br>    if (!fwnode)<br>        fwnode = dev_fwnode(priv->device);<br><br>    /* Set the platform/firmware specified interface mode */<br>    __set_bit(mode, priv->phylink_config.supported_interfaces); // 设置支持的接口模式，RK3588为PHY_INTERFACE_MODE_RGMII_RXID<br><br>    /* If we have an xpcs, it defines which PHY interfaces are supported. */<br>    if (priv->hw->xpcs)<br>        xpcs_get_interfaces(priv->hw->xpcs,<br>                    priv->phylink_config.supported_interfaces);<br><br>    priv->phylink_config.mac_capabilities = MAC_ASYM_PAUSE \| MAC_SYM_PAUSE \|<br>        MAC_10 \| MAC_100;<br><br>    if (!max_speed \| max_speed >= 1000)<br>        priv->phylink_config.mac_capabilities \|= MAC_1000;  // RK3588 GMAC支持千兆<br><br>    if (priv->plat->has_gmac4) {<br>        if (!max_speed \| max_speed >= 2500)<br>            priv->phylink_config.mac_capabilities \|= MAC_2500FD;<br>    } else if (priv->plat->has_xgmac) {<br>        if (!max_speed \| max_speed >= 2500)<br>            priv->phylink_config.mac_capabilities \|= MAC_2500FD;<br>        if (!max_speed \| max_speed >= 5000)<br>            priv->phylink_config.mac_capabilities \|= MAC_5000FD;<br>        if (!max_speed \| max_speed >= 10000)<br>            priv->phylink_config.mac_capabilities \|= MAC_10000FD;<br>        if (!max_speed \| max_speed >= 25000)<br>            priv->phylink_config.mac_capabilities \|= MAC_25000FD;<br>        if (!max_speed \| max_speed >= 40000)<br>            priv->phylink_config.mac_capabilities \|= MAC_40000FD;<br>        if (!max_speed \| max_speed >= 50000)<br>            priv->phylink_config.mac_capabilities \|= MAC_50000FD;<br>        if (!max_speed \| max_speed >= 100000)<br>            priv->phylink_config.mac_capabilities \|= MAC_100000FD;<br>    }<br><br>    /* Half-Duplex can only work with single queue */<br>    if (priv->plat->tx_queues_to_use > 1)<br>        priv->phylink_config.mac_capabilities &=<br>            ~(MAC_10HD \| MAC_100HD \| MAC_1000HD);<br>    priv->phylink_config.mac_managed_pm = true;<br><br>    phylink = phylink_create(&priv->phylink_config, fwnode, // 创建PHYLINK实例，绑定MAC操作回调<br>                mode, &stmmac_phylink_mac_ops);<br>    if (IS_ERR(phylink))<br>        return PTR_ERR(phylink);<br><br>    priv->phylink = phylink;<br>    return 0;<br>}|

#### 9.5.4.5. PHY连接[¶](#phy "永久链接至标题")

stmmac_init_phy函数负责将PHY设备连接到PHYLINK。

stmmac_init_phy函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)[¶](#id114 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48<br>49<br>50<br>51<br>52<br>53<br>54<br>55<br>56|static int stmmac_init_phy(struct net_device *dev)<br>{<br>    struct stmmac_priv *priv = netdev_priv(dev);<br>    struct fwnode_handle *phy_fwnode;<br>    struct fwnode_handle *fwnode;<br>    int ret;<br><br>    if (!phylink_expects_phy(priv->phylink)) // 检查是否需要外部PHY<br>        return 0;<br><br>    if (priv->plat->integrated_phy_power)<br>        ret = priv->plat->integrated_phy_power(priv->plat->bsp_priv, true);<br><br>    fwnode = of_fwnode_handle(priv->plat->phylink_node);<br>    if (!fwnode)<br>        fwnode = dev_fwnode(priv->device);<br><br>    if (fwnode)<br>        phy_fwnode = fwnode_get_phy_node(fwnode);  // 从phy-handle属性获取PHY节点<br>    else<br>        phy_fwnode = NULL;<br><br>    /* Some DT bindings do not set-up the PHY handle. Let's try to<br>    * manually parse it<br>    */<br>    if (!phy_fwnode \| IS_ERR(phy_fwnode)) {<br>        int addr = priv->plat->phy_addr;<br>        struct phy_device *phydev;<br><br>        if (addr < 0) {<br>            netdev_err(priv->dev, "no phy found\n");<br>            return -ENODEV;<br>        }<br><br>        phydev = mdiobus_get_phy(priv->mii, addr);<br>        if (!phydev) {<br>            netdev_err(priv->dev, "no phy at addr %d\n", addr);<br>            return -ENODEV;<br>        }<br><br>        ret = phylink_connect_phy(priv->phylink, phydev); // 备选路径，通过MDIO地址直接连接<br>    } else {<br>        fwnode_handle_put(phy_fwnode);<br>        ret = phylink_fwnode_phy_connect(priv->phylink, fwnode, 0);  // 通过fwnode连接PHY，触发PHY驱动的probe和config_init<br>    }<br><br>    if (!priv->plat->pmt) {<br>        struct ethtool_wolinfo wol = { .cmd = ETHTOOL_GWOL };<br><br>        phylink_ethtool_get_wol(priv->phylink, &wol);<br>        device_set_wakeup_capable(priv->device, !!wol.supported);<br>        device_set_wakeup_enable(priv->device, !!wol.wolopts);<br>    }<br><br>    return ret;<br>}|

对于RK3588S + RTL8211F方案，DTS中配置了phy-handle = <&rgmii_phy1>，因此走phylink_fwnode_phy_connect路径。 连接成功后，PHY驱动的config_init（即rtl8211f_config_init）会在链路启动时被调用。

#### 9.5.4.6. 链路建立回调[¶](#id49 "永久链接至标题")

stmmac_mac_link_up函数是PHYLINK框架在链路协商完成后回调的函数。当RTL8211F自协商完成，PHYLINK调用此函数配置MAC硬件。 它设置MAC控制寄存器中的速率位，并调用平台层的fix_mac_speed回调（即dwmac-rk.c中的rk_fix_speed）来配置GRF时钟分频。

stmmac_mac_link_up函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)[¶](#id115 "永久链接至代码")

|   |   |
|---|---|
|1<br>  2<br>  3<br>  4<br>  5<br>  6<br>  7<br>  8<br>  9<br> 10<br> 11<br> 12<br> 13<br> 14<br> 15<br> 16<br> 17<br> 18<br> 19<br> 20<br> 21<br> 22<br> 23<br> 24<br> 25<br> 26<br> 27<br> 28<br> 29<br> 30<br> 31<br> 32<br> 33<br> 34<br> 35<br> 36<br> 37<br> 38<br> 39<br> 40<br> 41<br> 42<br> 43<br> 44<br> 45<br> 46<br> 47<br> 48<br> 49<br> 50<br> 51<br> 52<br> 53<br> 54<br> 55<br> 56<br> 57<br> 58<br> 59<br> 60<br> 61<br> 62<br> 63<br> 64<br> 65<br> 66<br> 67<br> 68<br> 69<br> 70<br> 71<br> 72<br> 73<br> 74<br> 75<br> 76<br> 77<br> 78<br> 79<br> 80<br> 81<br> 82<br> 83<br> 84<br> 85<br> 86<br> 87<br> 88<br> 89<br> 90<br> 91<br> 92<br> 93<br> 94<br> 95<br> 96<br> 97<br> 98<br> 99<br>100<br>101<br>102<br>103<br>104<br>105<br>106<br>107<br>108|static void stmmac_mac_link_up(struct phylink_config *config,<br>                struct phy_device *phy,<br>                unsigned int mode, phy_interface_t interface,<br>                int speed, int duplex,<br>                bool tx_pause, bool rx_pause)<br>{<br>    struct stmmac_priv *priv = netdev_priv(to_net_dev(config->dev));<br>    u32 old_ctrl, ctrl;<br><br>    old_ctrl = readl(priv->ioaddr + MAC_CTRL_REG); // 读取当前MAC控制寄存器<br>    ctrl = old_ctrl & ~priv->hw->link.speed_mask;<br><br>    if (interface == PHY_INTERFACE_MODE_USXGMII) {<br>        switch (speed) {<br>        case SPEED_10000:<br>            ctrl \|= priv->hw->link.xgmii.speed10000;<br>            break;<br>        case SPEED_5000:<br>            ctrl \|= priv->hw->link.xgmii.speed5000;<br>            break;<br>        case SPEED_2500:<br>            ctrl \|= priv->hw->link.xgmii.speed2500;<br>            break;<br>        default:<br>            return;<br>        }<br>    } else if (interface == PHY_INTERFACE_MODE_XLGMII) {<br>        switch (speed) {<br>        case SPEED_100000:<br>            ctrl \|= priv->hw->link.xlgmii.speed100000;<br>            break;<br>        case SPEED_50000:<br>            ctrl \|= priv->hw->link.xlgmii.speed50000;<br>            break;<br>        case SPEED_40000:<br>            ctrl \|= priv->hw->link.xlgmii.speed40000;<br>            break;<br>        case SPEED_25000:<br>            ctrl \|= priv->hw->link.xlgmii.speed25000;<br>            break;<br>        case SPEED_10000:<br>            ctrl \|= priv->hw->link.xgmii.speed10000;<br>            break;<br>        case SPEED_2500:<br>            ctrl \|= priv->hw->link.speed2500;<br>            break;<br>        case SPEED_1000:<br>            ctrl \|= priv->hw->link.speed1000; // 设置千兆速率位<br>            break;<br>        default:<br>            return;<br>        }<br>    } else {<br>        switch (speed) {<br>        case SPEED_2500:<br>            ctrl \|= priv->hw->link.speed2500;<br>            break;<br>        case SPEED_1000:<br>            ctrl \|= priv->hw->link.speed1000;<br>            break;<br>        case SPEED_100:<br>            ctrl \|= priv->hw->link.speed100;<br>            break;<br>        case SPEED_10:<br>            ctrl \|= priv->hw->link.speed10;<br>            break;<br>        default:<br>            return;<br>        }<br>    }<br><br>    priv->speed = speed;<br><br>    if (priv->plat->fix_mac_speed)<br>        priv->plat->fix_mac_speed(priv->plat->bsp_priv, speed); // 触发rk_fix_speed，配置PHP_GRF时钟分频<br><br>    if (!duplex)<br>        ctrl &= ~priv->hw->link.duplex;<br>    else<br>        ctrl \|= priv->hw->link.duplex;<br><br>    /* Flow Control operation */<br>    if (rx_pause && tx_pause)<br>        priv->flow_ctrl = FLOW_AUTO;<br>    else if (rx_pause && !tx_pause)<br>        priv->flow_ctrl = FLOW_RX;<br>    else if (!rx_pause && tx_pause)<br>        priv->flow_ctrl = FLOW_TX;<br>    else<br>        priv->flow_ctrl = FLOW_OFF;<br><br>    stmmac_mac_flow_ctrl(priv, duplex); // 配置流控<br><br>    if (ctrl != old_ctrl)<br>        writel(ctrl, priv->ioaddr + MAC_CTRL_REG); // 写入新的MAC控制寄存器<br><br>    stmmac_mac_set(priv, priv->ioaddr, true); // 使能MAC收发<br>    if (phy && priv->dma_cap.eee) {<br>        priv->eee_active =<br>            phy_init_eee(phy, !priv->plat->rx_clk_runs_in_lpi) >= 0;<br>        priv->eee_enabled = stmmac_eee_init(priv);<br>        priv->tx_lpi_enabled = priv->eee_enabled;<br>        stmmac_set_eee_pls(priv, priv->hw, true);<br>    }<br><br>    if (priv->dma_cap.fpesel)<br>        stmmac_fpe_link_state_handle(priv, true);<br>}|

#### 9.5.4.7. 网络设备操作集[¶](#id50 "永久链接至标题")

stmmac_netdev_ops定义了STMMAC网卡驱动向内核网络子系统暴露的所有操作接口。 当用户执行ifconfig eth0 up时调用ndo_open，发送数据时调用ndo_start_xmit，ethtool命令通过ndo_eth_ioctl处理。

stmmac_netdev_ops操作集(位于内核源码/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)[¶](#id116 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22|static const struct net_device_ops stmmac_netdev_ops = {<br>    .ndo_open = stmmac_open,        // ifconfig up / ip link set up时调用<br>    .ndo_start_xmit = stmmac_xmit,  // 发送报文时调用<br>    .ndo_stop = stmmac_release,     // ifconfig down / ip link set down时调用<br>    .ndo_change_mtu = stmmac_change_mtu,    // 修改MTU时调用<br>    .ndo_fix_features = stmmac_fix_features,<br>    .ndo_set_features = stmmac_set_features,<br>    .ndo_set_rx_mode = stmmac_set_rx_mode,<br>    .ndo_tx_timeout = stmmac_tx_timeout,    // 发送超时时调用<br>    .ndo_eth_ioctl = stmmac_ioctl,          // ethtool/ioctl<br>    .ndo_setup_tc = stmmac_setup_tc,<br>    .ndo_select_queue = stmmac_select_queue, // 多队列时选择发送队列<br>#ifdef CONFIG_NET_POLL_CONTROLLER<br>    .ndo_poll_controller = stmmac_poll_controller,<br>#endif<br>    .ndo_set_mac_address = stmmac_set_mac_address, // 设置MAC地址<br>    .ndo_vlan_rx_add_vid = stmmac_vlan_rx_add_vid,<br>    .ndo_vlan_rx_kill_vid = stmmac_vlan_rx_kill_vid,<br>    .ndo_bpf = stmmac_bpf,<br>    .ndo_xdp_xmit = stmmac_xdp_xmit,<br>    .ndo_xsk_wakeup = stmmac_xsk_wakeup,<br>};|

#### 9.5.4.8. 打开网卡[¶](#id51 "永久链接至标题")

stmmac_open函数是ifconfig up的入口。它分配DMA描述符环，然后调用__stmmac_open函数完成连接PHY、初始化硬件、启动PHYLINK、请求中断、使能NAPI和DMA。对于RK3588S + RTL8211F，stmmac_init_phy会连接RTL8211F，phylink_start会触发PHY自协商。

打开网卡(位于内核源码/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)[¶](#id117 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48<br>49<br>50<br>51<br>52<br>53<br>54<br>55<br>56<br>57<br>58<br>59<br>60<br>61<br>62<br>63<br>64<br>65<br>66<br>67<br>68<br>69<br>70<br>71<br>72<br>73<br>74<br>75<br>76<br>77<br>78<br>79<br>80<br>81<br>82<br>83<br>84<br>85<br>86<br>87<br>88<br>89<br>90<br>91<br>92<br>93<br>94<br>95<br>96<br>97|static int stmmac_open(struct net_device *dev)<br>{<br>    struct stmmac_priv *priv = netdev_priv(dev);<br>    struct stmmac_dma_conf *dma_conf;<br>    int ret;<br><br>    // 根据MTU分配DMA描述符环和接收缓冲区<br>    dma_conf = stmmac_setup_dma_desc(priv, dev->mtu);<br>    if (IS_ERR(dma_conf))<br>        return PTR_ERR(dma_conf);<br><br>    // 调用__stmmac_open<br>    ret = __stmmac_open(dev, dma_conf);<br>    if (ret)<br>        free_dma_desc_resources(priv, dma_conf);<br><br>    kfree(dma_conf);<br>    return ret;<br>}<br><br>static int __stmmac_open(struct net_device *dev,<br>            struct stmmac_dma_conf *dma_conf)<br>{<br>    struct stmmac_priv *priv = netdev_priv(dev);<br>    int mode = priv->plat->phy_interface;<br>    u32 chan;<br>    int ret;<br><br>    ret = pm_runtime_resume_and_get(priv->device);<br>    if (ret < 0)<br>        return ret;<br><br>    if (priv->hw->pcs != STMMAC_PCS_TBI &&<br>        priv->hw->pcs != STMMAC_PCS_RTBI &&<br>        (!priv->hw->xpcs \|<br>        xpcs_get_an_mode(priv->hw->xpcs, mode) != DW_AN_C73)) {<br>        // 连接PHY<br>        ret = stmmac_init_phy(dev);<br>        if (ret) {<br>            netdev_err(priv->dev,<br>                "%s: Cannot attach to PHY (error: %d)\n",<br>                __func__, ret);<br>            goto init_phy_error;<br>        }<br>    }<br><br>    /* Extra statistics */<br>    memset(&priv->xstats, 0, sizeof(struct stmmac_extra_stats));<br>    priv->xstats.threshold = tc;<br><br>    priv->rx_copybreak = STMMAC_RX_COPYBREAK;<br><br>    buf_sz = dma_conf->dma_buf_sz;<br>    for (int i = 0; i < MTL_MAX_TX_QUEUES; i++)<br>        if (priv->dma_conf.tx_queue[i].tbs & STMMAC_TBS_EN)<br>            dma_conf->tx_queue[i].tbs = priv->dma_conf.tx_queue[i].tbs;<br>    memcpy(&priv->dma_conf, dma_conf, sizeof(*dma_conf));<br><br>    stmmac_reset_queues_param(priv);<br><br>    if (priv->plat->serdes_powerup) {<br>        ret = priv->plat->serdes_powerup(dev, priv->plat->bsp_priv);<br>        if (ret < 0) {<br>            netdev_err(priv->dev, "%s: Serdes powerup failed\n",<br>                __func__);<br>            goto init_error;<br>        }<br>    }<br><br>    // 初始化MAC硬件<br>    ret = stmmac_hw_setup(dev, true);<br>    if (ret < 0) {<br>        netdev_err(priv->dev, "%s: Hw setup failed\n", __func__);<br>        goto init_error;<br>    }<br><br>    stmmac_init_coalesce(priv);<br><br>    // 启动PHYLINK状态机，触发PHY自协商，协商完成后回调stmmac_mac_link_up<br>    phylink_start(priv->phylink);<br>    // 通知PHYLINK链路可能已就绪<br>    phylink_speed_up(priv->phylink);<br><br>    // 请求中断，DMA中断、WoL中断等<br>    ret = stmmac_request_irq(dev);<br>    if (ret)<br>        goto irq_error;<br><br>    // 使能所有NAPI队列<br>    stmmac_enable_all_queues(priv);<br>    // 通知协议栈可以开始发包<br>    netif_tx_start_all_queues(priv->dev);<br>    // 使能DMA中断<br>    stmmac_enable_all_dma_irq(priv);<br><br>    return 0;<br>}|

#### 9.5.4.9. 关闭网卡[¶](#id52 "永久链接至标题")

stmmac_release函数是ifconfig down的入口，执行与stmmac_open相反的操作：停止PHYLINK、断开PHY、禁用NAPI、释放中断、停止DMA、释放描述符资源、关闭MAC。

stmmac_release函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)[¶](#id118 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48<br>49<br>50<br>51<br>52<br>53<br>54<br>55<br>56<br>57|static int stmmac_release(struct net_device *dev)<br>{<br>    struct stmmac_priv *priv = netdev_priv(dev);<br>    u32 chan;<br><br>    if (device_may_wakeup(priv->device))<br>        phylink_speed_down(priv->phylink, false);<br>    // 停止PHYLINK状态机<br>    phylink_stop(priv->phylink);<br>    // 断开PHY连接<br>    phylink_disconnect_phy(priv->phylink);<br><br>    if (priv->plat->integrated_phy_power)<br>        priv->plat->integrated_phy_power(priv->plat->bsp_priv, false);<br><br>    // 禁用所有NAPI<br>    stmmac_disable_all_queues(priv);<br><br>    for (chan = 0; chan < priv->plat->tx_queues_to_use; chan++)<br>        hrtimer_cancel(&priv->dma_conf.tx_queue[chan].txtimer);<br><br>    // 停止所有发送队列<br>    netif_tx_disable(dev);<br><br>    /* Free the IRQ lines */<br>    stmmac_free_irq(dev, REQ_IRQ_ERR_ALL, 0);<br><br>    if (priv->eee_enabled) {<br>        priv->tx_path_in_lpi_mode = false;<br>        del_timer_sync(&priv->eee_ctrl_timer);<br>    }<br><br>    // 停止所有DMA通道<br>    stmmac_stop_all_dma(priv);<br><br>    /* Release and free the Rx/Tx resources */<br>    free_dma_desc_resources(priv, &priv->dma_conf);<br><br>    // 关闭MAC收发<br>    stmmac_mac_set(priv, priv->ioaddr, false);<br><br>    /* Powerdown Serdes if there is */<br>    if (priv->plat->serdes_powerdown)<br>        priv->plat->serdes_powerdown(dev, priv->plat->bsp_priv);<br><br>    // 通知协议栈链路断开<br>    netif_carrier_off(dev);<br><br>    stmmac_release_ptp(priv);<br><br>    pm_runtime_put(priv->device);<br><br>    if (priv->dma_cap.fpesel)<br>        stmmac_fpe_stop_wq(priv);<br><br>    return 0;<br>}|

#### 9.5.4.10. 发送入口[¶](#id53 "永久链接至标题")

stmmac_xmit函数是发送路径的核心函数，由协议栈通过ndo_start_xmit调用。 它将sk_buff的数据进行DMA映射，填充TX描述符环，设置OWN位将描述符交给DMA引擎，最后触发DMA发送。 对于TSO（TCP分段卸载）报文，会转到stmmac_tso_xmit处理。

stmmac_xmit函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)[¶](#id119 "永久链接至代码")

|   |   |
|---|---|
|1<br>  2<br>  3<br>  4<br>  5<br>  6<br>  7<br>  8<br>  9<br> 10<br> 11<br> 12<br> 13<br> 14<br> 15<br> 16<br> 17<br> 18<br> 19<br> 20<br> 21<br> 22<br> 23<br> 24<br> 25<br> 26<br> 27<br> 28<br> 29<br> 30<br> 31<br> 32<br> 33<br> 34<br> 35<br> 36<br> 37<br> 38<br> 39<br> 40<br> 41<br> 42<br> 43<br> 44<br> 45<br> 46<br> 47<br> 48<br> 49<br> 50<br> 51<br> 52<br> 53<br> 54<br> 55<br> 56<br> 57<br> 58<br> 59<br> 60<br> 61<br> 62<br> 63<br> 64<br> 65<br> 66<br> 67<br> 68<br> 69<br> 70<br> 71<br> 72<br> 73<br> 74<br> 75<br> 76<br> 77<br> 78<br> 79<br> 80<br> 81<br> 82<br> 83<br> 84<br> 85<br> 86<br> 87<br> 88<br> 89<br> 90<br> 91<br> 92<br> 93<br> 94<br> 95<br> 96<br> 97<br> 98<br> 99<br>100<br>101<br>102<br>103<br>104<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119<br>120<br>121<br>122<br>123<br>124<br>125<br>126<br>127<br>128<br>129<br>130<br>131<br>132<br>133<br>134<br>135<br>136<br>137<br>138<br>139<br>140<br>141<br>142<br>143<br>144<br>145<br>146<br>147<br>148<br>149<br>150<br>151<br>152<br>153<br>154<br>155<br>156<br>157<br>158<br>159<br>160<br>161<br>162<br>163<br>164<br>165<br>166<br>167<br>168<br>169<br>170<br>171<br>172<br>173<br>174<br>175<br>176<br>177<br>178<br>179<br>180<br>181<br>182<br>183<br>184<br>185<br>186<br>187<br>188<br>189<br>190<br>191<br>192<br>193<br>194<br>195<br>196<br>197<br>198<br>199<br>200<br>201<br>202<br>203<br>204<br>205<br>206<br>207<br>208<br>209<br>210<br>211<br>212<br>213<br>214<br>215<br>216<br>217<br>218<br>219<br>220<br>221<br>222<br>223<br>224<br>225<br>226<br>227<br>228<br>229<br>230<br>231<br>232<br>233<br>234<br>235<br>236<br>237<br>238<br>239<br>240<br>241<br>242<br>243<br>244<br>245<br>246<br>247<br>248<br>249<br>250<br>251<br>252<br>253<br>254<br>255<br>256<br>257<br>258<br>259|static netdev_tx_t stmmac_xmit(struct sk_buff *skb, struct net_device *dev)<br>{<br>    unsigned int first_entry, tx_packets, enh_desc;<br>    struct stmmac_priv *priv = netdev_priv(dev);<br>    unsigned int nopaged_len = skb_headlen(skb);<br>    int i, csum_insertion = 0, is_jumbo = 0;<br>    u32 queue = skb_get_queue_mapping(skb);<br>    int nfrags = skb_shinfo(skb)->nr_frags;<br>    int gso = skb_shinfo(skb)->gso_type;<br>    struct dma_edesc *tbs_desc = NULL;<br>    struct dma_desc *desc, *first;<br>    struct stmmac_tx_queue *tx_q;<br>    bool has_vlan, set_ic;<br>    int entry, first_tx;<br>    dma_addr_t des;<br><br>    tx_q = &priv->dma_conf.tx_queue[queue]; // 获取对应队列的TX队列配置结构<br>    first_tx = tx_q->cur_tx;    // 记录本次发送操作起始的描述符索引，用于后续统计<br><br>    if (priv->tx_path_in_lpi_mode && priv->eee_sw_timer_en)<br>        stmmac_disable_eee_mode(priv);<br><br>    // 检测是否为TSO报文，RK3588支持TSO<br>    if (skb_is_gso(skb) && priv->tso) {<br>        if (gso & (SKB_GSO_TCPV4 \| SKB_GSO_TCPV6))<br>            return stmmac_tso_xmit(skb, dev);<br>        if (priv->plat->has_gmac4 && (gso & SKB_GSO_UDP_L4))<br>            return stmmac_tso_xmit(skb, dev);<br>    }<br><br>    // 检查TX描述符环是否有足够空间<br>    if (unlikely(stmmac_tx_avail(priv, queue) < nfrags + 1)) {<br>        if (!netif_tx_queue_stopped(netdev_get_tx_queue(dev, queue))) {<br>            netif_tx_stop_queue(netdev_get_tx_queue(priv->dev, // 空间不足时停止发送队列<br>                                queue));<br>            /* This is a hard error, log it. */<br>            netdev_err(priv->dev,<br>                "%s: Tx Ring full when queue awake\n",<br>                __func__);<br>        }<br>        // 返回NETDEV_TX_BUSY，通知网络栈稍后重试发送<br>        return NETDEV_TX_BUSY;<br>    }<br><br>    /* Check if VLAN can be inserted by HW */<br>    has_vlan = stmmac_vlan_insert(priv, skb, tx_q);<br><br>    entry = tx_q->cur_tx;   // 获取当前可用的描述符索引<br>    first_entry = entry;    // 记录第一个描述符的索引，后续需要对其设置OWN位<br>    WARN_ON(tx_q->tx_skbuff[first_entry]);<br><br>    csum_insertion = (skb->ip_summed == CHECKSUM_PARTIAL);<br><br>    // 根据描述符类型获取第一个描述符的内存指针<br>    if (likely(priv->extend_desc))<br>        desc = (struct dma_desc *)(tx_q->dma_etx + entry);<br>    else if (tx_q->tbs & STMMAC_TBS_AVAIL)<br>        desc = &tx_q->dma_entx[entry].basic;<br>    else<br>        desc = tx_q->dma_tx + entry;<br><br>    first = desc;   // 保存第一个描述符的指针，后续统一设置OWN位以触发DMA<br><br>    if (has_vlan)<br>        stmmac_set_desc_vlan(priv, first, STMMAC_VLAN_INSERT);<br><br>    enh_desc = priv->plat->enh_desc;<br>    /* To program the descriptors according to the size of the frame */<br>    if (enh_desc)<br>        is_jumbo = stmmac_is_jumbo_frm(priv, skb->len, enh_desc);<br><br>    if (unlikely(is_jumbo)) {<br>        entry = stmmac_jumbo_frm(priv, tx_q, skb, csum_insertion);<br>        if (unlikely(entry < 0) && (entry != -EINVAL))<br>            goto dma_map_err;<br>    }<br><br>    // 遍历skb的所有分片，为每个分片映射DMA并设置对应的描述符<br>    for (i = 0; i < nfrags; i++) {<br>        const skb_frag_t *frag = &skb_shinfo(skb)->frags[i];<br>        int len = skb_frag_size(frag);<br>        bool last_segment = (i == (nfrags - 1));<br><br>        // 计算下一个描述符的索引<br>        entry = STMMAC_GET_ENTRY(entry, priv->dma_conf.dma_tx_size);<br>        WARN_ON(tx_q->tx_skbuff[entry]);<br><br>        // 获取当前分片对应的描述符指针<br>        if (likely(priv->extend_desc))<br>            desc = (struct dma_desc *)(tx_q->dma_etx + entry);<br>        else if (tx_q->tbs & STMMAC_TBS_AVAIL)<br>            desc = &tx_q->dma_entx[entry].basic;<br>        else<br>            desc = tx_q->dma_tx + entry;<br><br>        // 将分片数据映射为DMA物理地址<br>        des = skb_frag_dma_map(priv->device, frag, 0, len,<br>                    DMA_TO_DEVICE);<br>        if (dma_mapping_error(priv->device, des))<br>            goto dma_map_err; /* should reuse desc w/o issues */<br><br>        // 在TX队列的DMA信息数组中保存映射后的DMA地址<br>        tx_q->tx_skbuff_dma[entry].buf = des;<br><br>        // 将DMA地址写入硬件描述符<br>        stmmac_set_desc_addr(priv, desc, des);<br><br>        // 设置DMA映射元数据：标记为页映射、记录长度、是否为最后一段、缓冲区类型为SKB<br>        tx_q->tx_skbuff_dma[entry].map_as_page = true;<br>        tx_q->tx_skbuff_dma[entry].len = len;<br>        tx_q->tx_skbuff_dma[entry].last_segment = last_segment;<br>        tx_q->tx_skbuff_dma[entry].buf_type = STMMAC_TXBUF_T_SKB;<br><br>        // 填充描述符，地址、长度、校验和卸载标志等<br>        stmmac_prepare_tx_desc(priv, desc, 0, len, csum_insertion,<br>                priv->mode, 1, last_segment, skb->len);<br>    }<br><br>    /* Only the last descriptor gets to point to the skb. */<br>    // 只有最后一个描述符对应的数组位置保存skb指针，用于发送完成后在TX Clean中释放skb<br>    tx_q->tx_skbuff[entry] = skb;<br>    tx_q->tx_skbuff_dma[entry].buf_type = STMMAC_TXBUF_T_SKB;<br><br>/* According to the coalesce parameter the IC bit for the latest<br>* segment is reset and the timer re-started to clean the tx status.<br>* This approach takes care about the fragments: desc is the first<br>* element in case of no SG.<br>*/<br>tx_packets = (entry + 1) - first_tx;<br>tx_q->tx_count_frames += tx_packets;<br><br>if ((skb_shinfo(skb)->tx_flags & SKBTX_HW_TSTAMP) && priv->hwts_tx_en)<br>    set_ic = true;<br>else if (!priv->tx_coal_frames[queue])<br>    set_ic = false;<br>else if (tx_packets > priv->tx_coal_frames[queue])<br>    set_ic = true;<br>else if ((tx_q->tx_count_frames %<br>    priv->tx_coal_frames[queue]) < tx_packets)<br>    set_ic = true;<br>else<br>    set_ic = false;<br><br>if (set_ic) {<br>    if (likely(priv->extend_desc))<br>        desc = &tx_q->dma_etx[entry].basic;<br>    else if (tx_q->tbs & STMMAC_TBS_AVAIL)<br>        desc = &tx_q->dma_entx[entry].basic;<br>    else<br>        desc = &tx_q->dma_tx[entry];<br><br>    tx_q->tx_count_frames = 0;<br>    stmmac_set_tx_ic(priv, desc);<br>    priv->xstats.tx_set_ic_bit++;<br>}<br><br>/* We've used all descriptors we need for this skb, however,<br>* advance cur_tx so that it references a fresh descriptor.<br>* ndo_start_xmit will fill this descriptor the next time it's<br>* called and stmmac_tx_clean may clean up to this descriptor.<br>*/<br>// 推进cur_tx索引，使其指向下一个空闲的描述符<br>entry = STMMAC_GET_ENTRY(entry, priv->dma_conf.dma_tx_size);<br>tx_q->cur_tx = entry;<br><br>if (netif_msg_pktdata(priv)) {<br>    netdev_dbg(priv->dev,<br>        "%s: curr=%d dirty=%d f=%d, e=%d, first=%p, nfrags=%d",<br>        __func__, tx_q->cur_tx, tx_q->dirty_tx, first_entry,<br>        entry, first, nfrags);<br><br>    netdev_dbg(priv->dev, ">>> frame to be transmitted: ");<br>    print_pkt(skb->data, skb->len);<br>}<br><br>// 检查剩余可用描述符数量，如果小于等于最大分片数加 1，则必须停止队列<br>if (unlikely(stmmac_tx_avail(priv, queue) <= (MAX_SKB_FRAGS + 1))) {<br>    netif_dbg(priv, hw, priv->dev, "%s: stop transmitted packets\n",<br>        __func__);<br>    // 停止网络栈对该队列的发送，直到TX清理函数释放足够的描述符后再唤醒<br>    netif_tx_stop_queue(netdev_get_tx_queue(priv->dev, queue));<br>}<br><br>// 累加网卡设备的发送字节数统计<br>dev->stats.tx_bytes += skb->len;<br><br>if (priv->sarc_type)<br>    stmmac_set_desc_sarc(priv, first, priv->sarc_type);<br><br>skb_tx_timestamp(skb);<br><br>/* Ready to fill the first descriptor and set the OWN bit w/o any<br>* problems because all the descriptors are actually ready to be<br>* passed to the DMA engine.<br>*/<br>// 如果不是巨型帧，则处理线性数据部分<br>if (likely(!is_jumbo)) {<br>    bool last_segment = (nfrags == 0);<br><br>    // 将skb的线性数据部分映射为DMA物理地址<br>    des = dma_map_single(priv->device, skb->data,<br>                nopaged_len, DMA_TO_DEVICE);<br>    if (dma_mapping_error(priv->device, des))<br>        goto dma_map_err;<br><br>    // 保存DMA地址、缓冲区类型、映射方式<br>    tx_q->tx_skbuff_dma[first_entry].buf = des;<br>    tx_q->tx_skbuff_dma[first_entry].buf_type = STMMAC_TXBUF_T_SKB;<br>    tx_q->tx_skbuff_dma[first_entry].map_as_page = false;<br><br>    // 将DMA地址写入第一个描述符<br>    stmmac_set_desc_addr(priv, first, des);<br><br>    // 保存长度和是否为最后一段的标志<br>    tx_q->tx_skbuff_dma[first_entry].len = nopaged_len;<br>    tx_q->tx_skbuff_dma[first_entry].last_segment = last_segment;<br><br>    if (unlikely((skb_shinfo(skb)->tx_flags & SKBTX_HW_TSTAMP) &&<br>            priv->hwts_tx_en)) {<br>        /* declare that device is doing timestamping */<br>        skb_shinfo(skb)->tx_flags \|= SKBTX_IN_PROGRESS;<br>        stmmac_enable_tx_timestamp(priv, first);<br>    }<br><br>    /* Prepare the first descriptor setting the OWN bit too */<br>    stmmac_prepare_tx_desc(priv, first, 1, nopaged_len,<br>            csum_insertion, priv->mode, 0, last_segment,<br>            skb->len);<br>}<br><br>if (tx_q->tbs & STMMAC_TBS_EN) {<br>    struct timespec64 ts = ns_to_timespec64(skb->tstamp);<br><br>    tbs_desc = &tx_q->dma_entx[first_entry];<br>    stmmac_set_desc_tbs(priv, tbs_desc, ts.tv_sec, ts.tv_nsec);<br>}<br><br>    // 设置OWN位，将描述符所有权交给DMA硬件<br>    stmmac_set_tx_owner(priv, first);<br><br>    // 通知网络栈已入队的数据包字节数，用于动态队列限流<br>    netdev_tx_sent_queue(netdev_get_tx_queue(dev, queue), skb->len);<br><br>    // 使能DMA发送<br>    stmmac_enable_dma_transmission(priv, priv->ioaddr);<br><br>    // 更新TX尾指针寄存器，触发DMA引擎开始搬运<br>    stmmac_flush_tx_descriptors(priv, queue);<br>    // 启动TX清理定时器<br>    stmmac_tx_timer_arm(priv, queue);<br><br>    return NETDEV_TX_OK;<br><br>dma_map_err:<br>    netdev_err(priv->dev, "Tx DMA map failed\n");<br>    dev_kfree_skb(skb);<br>    priv->dev->stats.tx_dropped++;<br>    return NETDEV_TX_OK;<br>}|

#### 9.5.4.11. 发送完成清理[¶](#id54 "永久链接至标题")

stmmac_tx_clean函数由NAPI轮询函数stmmac_napi_poll_tx调用，负责回收已完成发送的TX描述符和skb。 它遍历从dirty_tx到cur_tx的描述符，检查DMA是否已完成（OWN位是否已清除），然后解除DMA映射、释放skb、更新统计信息。 如果之前队列被停止且现在有足够空间，则唤醒队列。

stmmac_tx_clean函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)[¶](#id120 "永久链接至代码")

|   |   |
|---|---|
|1<br>  2<br>  3<br>  4<br>  5<br>  6<br>  7<br>  8<br>  9<br> 10<br> 11<br> 12<br> 13<br> 14<br> 15<br> 16<br> 17<br> 18<br> 19<br> 20<br> 21<br> 22<br> 23<br> 24<br> 25<br> 26<br> 27<br> 28<br> 29<br> 30<br> 31<br> 32<br> 33<br> 34<br> 35<br> 36<br> 37<br> 38<br> 39<br> 40<br> 41<br> 42<br> 43<br> 44<br> 45<br> 46<br> 47<br> 48<br> 49<br> 50<br> 51<br> 52<br> 53<br> 54<br> 55<br> 56<br> 57<br> 58<br> 59<br> 60<br> 61<br> 62<br> 63<br> 64<br> 65<br> 66<br> 67<br> 68<br> 69<br> 70<br> 71<br> 72<br> 73<br> 74<br> 75<br> 76<br> 77<br> 78<br> 79<br> 80<br> 81<br> 82<br> 83<br> 84<br> 85<br> 86<br> 87<br> 88<br> 89<br> 90<br> 91<br> 92<br> 93<br> 94<br> 95<br> 96<br> 97<br> 98<br> 99<br>100<br>101<br>102<br>103<br>104<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119<br>120<br>121<br>122<br>123<br>124<br>125<br>126<br>127<br>128<br>129<br>130<br>131<br>132<br>133<br>134<br>135<br>136<br>137<br>138<br>139<br>140<br>141<br>142<br>143<br>144<br>145<br>146<br>147<br>148<br>149<br>150<br>151<br>152<br>153<br>154<br>155<br>156<br>157<br>158<br>159<br>160<br>161<br>162<br>163<br>164<br>165<br>166<br>167<br>168<br>169<br>170<br>171<br>172<br>173<br>174<br>175<br>176<br>177<br>178<br>179<br>180<br>181<br>182<br>183<br>184<br>185<br>186<br>187<br>188<br>189<br>190<br>191<br>192<br>193<br>194<br>195<br>196<br>197<br>198<br>199<br>200|static int stmmac_tx_clean(struct stmmac_priv *priv, int budget, u32 queue)<br>{<br>    struct stmmac_tx_queue *tx_q = &priv->dma_conf.tx_queue[queue];<br>    unsigned int bytes_compl = 0, pkts_compl = 0;<br>    unsigned int entry, xmits = 0, count = 0;<br><br>    // 获取TX队列的锁，并禁用软中断<br>    __netif_tx_lock_bh(netdev_get_tx_queue(priv->dev, queue));<br><br>    // 增加TX清理操作的统计计数<br>    priv->xstats.tx_clean++;<br><br>    tx_q->xsk_frames_done = 0;<br><br>    // 从脏描述符索引（dirty_tx）开始遍历，这是上次清理停止的位置<br>    entry = tx_q->dirty_tx;<br><br>    /* Try to clean all TX complete frame in 1 shot */<br>    // 循环遍历描述符环，直到追上当前发送指针（cur_tx）或达到环的最大大小<br>    while ((entry != tx_q->cur_tx) && count < priv->dma_conf.dma_tx_size) {<br>        struct xdp_frame *xdpf;<br>        struct sk_buff *skb;<br>        struct dma_desc *p;<br>        int status;<br><br>        // 根据缓冲区类型判断是XDP帧还是普通的SKB<br>        if (tx_q->tx_skbuff_dma[entry].buf_type == STMMAC_TXBUF_T_XDP_TX \|<br>            tx_q->tx_skbuff_dma[entry].buf_type == STMMAC_TXBUF_T_XDP_NDO) {<br>            xdpf = tx_q->xdpf[entry];<br>            skb = NULL;<br>        } else if (tx_q->tx_skbuff_dma[entry].buf_type == STMMAC_TXBUF_T_SKB) {<br>            xdpf = NULL;<br>            skb = tx_q->tx_skbuff[entry];   // 如果是普通的网络栈SKB，获取sk_buff指针<br>        } else {<br>            xdpf = NULL;<br>            skb = NULL;<br>        }<br><br>        // 根据硬件配置获取对应的DMA描述符指针<br>        if (priv->extend_desc)<br>            p = (struct dma_desc *)(tx_q->dma_etx + entry);<br>        else if (tx_q->tbs & STMMAC_TBS_AVAIL)<br>            p = &tx_q->dma_entx[entry].basic;<br>        else<br>            p = tx_q->dma_tx + entry;<br><br>        // 读取描述符的状态字，包含DMA引擎写入的发送结果<br>        status = stmmac_tx_status(priv, &priv->dev->stats,<br>                &priv->xstats, p, priv->ioaddr);<br>        // 检查OWN位，如果DMA仍然拥有该描述符，说明还没发送完，则跳出循环<br>        if (unlikely(status & tx_dma_own))<br>            break;<br><br>        // 增加已处理的描述符计数<br>        count++;<br><br>        /* Make sure descriptor fields are read after reading<br>        * the own bit.<br>        */<br>        dma_rmb();<br><br>        /* Just consider the last segment and ...*/<br>        // 只有当该描述符是数据包的最后一个分段时，才进行完整的状态统计<br>        if (likely(!(status & tx_not_ls))) {<br>            /* ... verify the status error condition */<br>            if (unlikely(status & tx_err)) {<br>                // 如果有错误，增加设备的TX错误统计<br>                priv->dev->stats.tx_errors++;<br>                if (unlikely(status & tx_err_bump_tc))<br>                    stmmac_bump_dma_threshold(priv, queue);<br>            } else {<br>                // 发送成功，增加成功包数统计<br>                priv->dev->stats.tx_packets++;<br>                priv->xstats.tx_pkt_n++;<br>                priv->xstats.txq_stats[queue].tx_pkt_n++;<br>            }<br>            // 如果是SKB且请求了硬件时间戳，则从描述符中提取并传递给网络栈<br>            if (skb)<br>                stmmac_get_tx_hwtstamp(priv, p, skb);<br>        }<br><br>        // 如果该描述符映射了DMA缓冲区<br>        if (likely(tx_q->tx_skbuff_dma[entry].buf &&<br>            tx_q->tx_skbuff_dma[entry].buf_type != STMMAC_TXBUF_T_XDP_TX)) {<br><br>            // 根据映射方式解除DMA映射<br>            if (tx_q->tx_skbuff_dma[entry].map_as_page)<br>                dma_unmap_page(priv->device,<br>                        tx_q->tx_skbuff_dma[entry].buf,<br>                        tx_q->tx_skbuff_dma[entry].len,<br>                        DMA_TO_DEVICE);<br>            else<br>                dma_unmap_single(priv->device,<br>                        tx_q->tx_skbuff_dma[entry].buf,<br>                        tx_q->tx_skbuff_dma[entry].len,<br>                        DMA_TO_DEVICE);<br>            // 清空DMA缓冲区相关的元数据<br>            tx_q->tx_skbuff_dma[entry].buf = 0;<br>            tx_q->tx_skbuff_dma[entry].len = 0;<br>            tx_q->tx_skbuff_dma[entry].map_as_page = false;<br>        }<br><br>        // 清理描述符的扩展字段<br>        stmmac_clean_desc3(priv, tx_q, p);<br><br>        // 重置该描述符的元数据标志<br>        tx_q->tx_skbuff_dma[entry].last_segment = false;<br>        tx_q->tx_skbuff_dma[entry].is_jumbo = false;<br><br>        if (xdpf &&<br>            tx_q->tx_skbuff_dma[entry].buf_type == STMMAC_TXBUF_T_XDP_TX) {<br>            xdp_return_frame_rx_napi(xdpf);<br>            tx_q->xdpf[entry] = NULL;<br>        }<br><br>        if (xdpf &&<br>            tx_q->tx_skbuff_dma[entry].buf_type == STMMAC_TXBUF_T_XDP_NDO) {<br>            xdp_return_frame(xdpf);<br>            tx_q->xdpf[entry] = NULL;<br>        }<br><br>        if (tx_q->tx_skbuff_dma[entry].buf_type == STMMAC_TXBUF_T_XSK_TX)<br>            tx_q->xsk_frames_done++;<br><br>        // 如果是普通的SKB发送<br>        if (tx_q->tx_skbuff_dma[entry].buf_type == STMMAC_TXBUF_T_SKB) {<br>            if (likely(skb)) {<br>                // 累加完成的包数和字节数<br>                pkts_compl++;<br>                bytes_compl += skb->len;<br>                dev_consume_skb_any(skb);   // 释放SKB内存<br>                tx_q->tx_skbuff[entry] = NULL;<br>            }<br>        }<br><br>        // 释放描述符，将其重置为初始状态，清除OWN位等，准备下次使用<br>        stmmac_release_tx_desc(priv, p, priv->mode);<br><br>        // 计算下一个描述符的索引<br>        entry = STMMAC_GET_ENTRY(entry, priv->dma_conf.dma_tx_size);<br>    }<br>    // 更新脏描述符索引，记录下次清理的起点<br>    tx_q->dirty_tx = entry;<br><br>    // 通知网络栈当前队列已完成的包数和字节数，以动态调整队列限流<br>    netdev_tx_completed_queue(netdev_get_tx_queue(priv->dev, queue),<br>                pkts_compl, bytes_compl);<br><br>    // 如果该TX队列之前因为环满被停止，且现在可用空间大于阈值，则唤醒队列<br>    if (unlikely(netif_tx_queue_stopped(netdev_get_tx_queue(priv->dev,<br>                                queue))) &&<br>        stmmac_tx_avail(priv, queue) > STMMAC_TX_THRESH(priv)) {<br><br>        netif_dbg(priv, tx_done, priv->dev,<br>            "%s: restart transmit\n", __func__);<br>        // 唤醒网络栈，允许其继续向该队列下发数据包<br>        netif_tx_wake_queue(netdev_get_tx_queue(priv->dev, queue));<br>    }<br><br>    if (tx_q->xsk_pool) {<br>        bool work_done;<br><br>        if (tx_q->xsk_frames_done)<br>            xsk_tx_completed(tx_q->xsk_pool, tx_q->xsk_frames_done);<br><br>        if (xsk_uses_need_wakeup(tx_q->xsk_pool))<br>            xsk_set_tx_need_wakeup(tx_q->xsk_pool);<br><br>        /* For XSK TX, we try to send as many as possible.<br>        * If XSK work done (XSK TX desc empty and budget still<br>        * available), return "budget - 1" to reenable TX IRQ.<br>        * Else, return "budget" to make NAPI continue polling.<br>        */<br>        work_done = stmmac_xdp_xmit_zc(priv, queue,<br>                        STMMAC_XSK_TX_BUDGET_MAX);<br>        if (work_done)<br>            xmits = budget - 1;<br>        else<br>            xmits = budget;<br>    }<br><br>    if (priv->eee_enabled && !priv->tx_path_in_lpi_mode &&<br>        priv->eee_sw_timer_en) {<br>        if (stmmac_enable_eee_mode(priv))<br>            mod_timer(&priv->eee_ctrl_timer, STMMAC_LPI_T(priv->tx_lpi_timer));<br>    }<br><br>    /* We still have pending packets, let's call for a new scheduling */<br>    // 如果还有未清理的描述符（dirty_tx没追上cur_tx），说明DMA还在发送或刚发完还没处理<br>    if (tx_q->dirty_tx != tx_q->cur_tx)<br>        // 启动TX清理定时器，确保即使没有中断也能在稍后继续清理，防止描述符耗尽导致死锁<br>        stmmac_tx_timer_arm(priv, queue);<br><br>    // 释放TX队列锁，恢复软中断<br>    __netif_tx_unlock_bh(netdev_get_tx_queue(priv->dev, queue));<br><br>    /* Combine decisions from TX clean and XSK TX */<br>    // 返回本次NAPI poll处理的工作量<br>    return max(count, xmits);<br>}|

#### 9.5.4.12. 主中断处理函数[¶](#id55 "永久链接至标题")

stmmac_interrupt函数是STMMAC驱动的主中断服务函数，对应dts中的macirq中断（RK3588为GIC_SPI 234）。它处理安全特性中断、通用中断（链路状态、时间戳等）和DMA中断（收发完成）。DMA中断会触发NAPI调度。

stmmac_interrupt函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)[¶](#id121 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21|static irqreturn_t stmmac_interrupt(int irq, void *dev_id)<br>{<br>    struct net_device *dev = (struct net_device *)dev_id;<br>    struct stmmac_priv *priv = netdev_priv(dev);<br><br>    // 若设备已关闭，直接返回<br>    if (test_bit(STMMAC_DOWN, &priv->state))<br>        return IRQ_HANDLED;<br><br>    // 处理安全特性中断<br>    if (stmmac_safety_feat_interrupt(priv))<br>        return IRQ_HANDLED;<br><br>    // 处理通用中断<br>    stmmac_common_interrupt(priv);<br><br>    // 处理DMA中断，调用stmmac_napi_check检查各通道状态并调度NAPI<br>    stmmac_dma_interrupt(priv);<br><br>    return IRQ_HANDLED;<br>}|

#### 9.5.4.13. RX NAPI轮询[¶](#rx-napi "永久链接至标题")

stmmac_napi_poll_rx函数是RX通道的NAPI轮询函数。DMA接收中断触发后，内核调度此函数在软中断上下文中批量处理接收报文。 它调用stmmac_rx处理报文，若处理量小于budget则调用napi_complete_done退出轮询模式并重新使能RX中断。

stmmac_napi_poll_rx函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)[¶](#id122 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22|static int stmmac_napi_poll_rx(struct napi_struct *napi, int budget)<br>{<br>    struct stmmac_channel *ch =<br>        container_of(napi, struct stmmac_channel, rx_napi);<br>    struct stmmac_priv *priv = ch->priv_data;<br>    u32 chan = ch->index;<br>    int work_done;<br><br>    priv->xstats.napi_poll++;<br><br>    // 调用接收核心函数，最多处理budget个包<br>    work_done = stmmac_rx(priv, budget, chan);<br>    if (work_done < budget && napi_complete_done(napi, work_done)) { // 若处理量小于预算，说明队列已空，退出NAPI轮询模式<br>        unsigned long flags;<br><br>        spin_lock_irqsave(&ch->lock, flags);<br>        stmmac_enable_dma_irq(priv, priv->ioaddr, chan, 1, 0); // 重新使能RX DMA中断<br>        spin_unlock_irqrestore(&ch->lock, flags);<br>    }<br><br>    return work_done;<br>}|

#### 9.5.4.14. 接收函数[¶](#id56 "永久链接至标题")

stmmac_rx函数是接收路径的核心函数，它遍历RX描述符环，从DMA已完成的描述符中取出数据，经过XDP处理后构建sk_buff，最终通过napi_gro_receive提交给协议栈。 处理完成后调用stmmac_rx_refill补充接收缓冲区。

注解

XDP（eXpress Data Path，快速数据路径）是内核提供的一种高性能数据包处理框架，它允许把一个eBPF程序挂到网卡驱动收包路径的最前端，在数据包还躺在DMA缓冲区里、内核还没分配sk_buff、还没进入协议栈之前，就对其执行用户自定义的逻辑。

stmmac_rx函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)[¶](#id123 "永久链接至代码")

|   |   |
|---|---|
|1<br>  2<br>  3<br>  4<br>  5<br>  6<br>  7<br>  8<br>  9<br> 10<br> 11<br> 12<br> 13<br> 14<br> 15<br> 16<br> 17<br> 18<br> 19<br> 20<br> 21<br> 22<br> 23<br> 24<br> 25<br> 26<br> 27<br> 28<br> 29<br> 30<br> 31<br> 32<br> 33<br> 34<br> 35<br> 36<br> 37<br> 38<br> 39<br> 40<br> 41<br> 42<br> 43<br> 44<br> 45<br> 46<br> 47<br> 48<br> 49<br> 50<br> 51<br> 52<br> 53<br> 54<br> 55<br> 56<br> 57<br> 58<br> 59<br> 60<br> 61<br> 62<br> 63<br> 64<br> 65<br> 66<br> 67<br> 68<br> 69<br> 70<br> 71<br> 72<br> 73<br> 74<br> 75<br> 76<br> 77<br> 78<br> 79<br> 80<br> 81<br> 82<br> 83<br> 84<br> 85<br> 86<br> 87<br> 88<br> 89<br> 90<br> 91<br> 92<br> 93<br> 94<br> 95<br> 96<br> 97<br> 98<br> 99<br>100<br>101<br>102<br>103<br>104<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119<br>120<br>121<br>122<br>123<br>124<br>125<br>126<br>127<br>128<br>129<br>130<br>131<br>132<br>133<br>134<br>135<br>136<br>137<br>138<br>139<br>140<br>141<br>142<br>143<br>144<br>145<br>146<br>147<br>148<br>149<br>150<br>151<br>152<br>153<br>154<br>155<br>156<br>157<br>158<br>159<br>160<br>161<br>162<br>163<br>164<br>165<br>166<br>167<br>168<br>169<br>170<br>171<br>172<br>173<br>174<br>175<br>176<br>177<br>178<br>179<br>180<br>181<br>182<br>183<br>184<br>185<br>186<br>187<br>188<br>189<br>190<br>191<br>192<br>193<br>194<br>195<br>196<br>197<br>198<br>199<br>200<br>201<br>202<br>203<br>204<br>205<br>206<br>207<br>208<br>209<br>210<br>211<br>212<br>213<br>214<br>215<br>216<br>217<br>218<br>219<br>220<br>221<br>222<br>223<br>224<br>225<br>226<br>227<br>228<br>229<br>230<br>231<br>232<br>233<br>234<br>235<br>236<br>237<br>238<br>239<br>240<br>241<br>242<br>243<br>244<br>245<br>246<br>247<br>248<br>249<br>250<br>251<br>252<br>253<br>254<br>255<br>256<br>257<br>258<br>259<br>260<br>261<br>262<br>263<br>264<br>265<br>266<br>267<br>268<br>269<br>270<br>271<br>272<br>273<br>274<br>275<br>276<br>277<br>278<br>279<br>280<br>281<br>282<br>283<br>284<br>285<br>286<br>287<br>288<br>289<br>290<br>291<br>292<br>293<br>294<br>295<br>296<br>297<br>298<br>299<br>300<br>301<br>302<br>303<br>304<br>305<br>306<br>307<br>308<br>309<br>310<br>311<br>312<br>313<br>314<br>315<br>316<br>317<br>318<br>319<br>320<br>321<br>322<br>323<br>324<br>325<br>326<br>327<br>328<br>329<br>330<br>331<br>332<br>333<br>334|static int stmmac_rx(struct stmmac_priv *priv, int limit, u32 queue)<br>{<br>    struct stmmac_rx_queue *rx_q = &priv->dma_conf.rx_queue[queue];<br>    struct stmmac_channel *ch = &priv->channel[queue];<br>    unsigned int count = 0, error = 0, len = 0;<br>    int status = 0, coe = priv->hw->rx_csum;<br>    unsigned int next_entry = rx_q->cur_rx;<br>    enum dma_data_direction dma_dir;<br>    unsigned int desc_size;<br>    struct sk_buff *skb = NULL;<br>    struct xdp_buff xdp;<br>    int xdp_status = 0;<br>    int buf_sz;<br><br>    // 从页池获取DMA映射方向，通常为DMA_FROM_DEVICE，启用XDP时可能为双向<br>    dma_dir = page_pool_get_dma_dir(rx_q->page_pool);<br>    // 将DMA缓冲区大小向上对齐到页大小，用于XDP缓冲区初始化<br>    buf_sz = DIV_ROUND_UP(priv->dma_conf.dma_buf_sz, PAGE_SIZE) * PAGE_SIZE;<br>    // 限制本次poll最多处理的描述符数量，防止超过环大小<br>    limit = min(priv->dma_conf.dma_rx_size - 1, (unsigned int)limit);<br><br>    // 如果启用了RX状态调试信息，则打印描述符环内容<br>    if (netif_msg_rx_status(priv)) {<br>        void *rx_head;<br><br>        netdev_dbg(priv->dev, "%s: descriptor ring:\n", __func__);<br>        if (priv->extend_desc) {<br>            rx_head = (void *)rx_q->dma_erx;<br>            desc_size = sizeof(struct dma_extended_desc);<br>        } else {<br>            rx_head = (void *)rx_q->dma_rx;<br>            desc_size = sizeof(struct dma_desc);<br>        }<br><br>        // 打印整个RX描述符环<br>        stmmac_display_ring(priv, rx_head, priv->dma_conf.dma_rx_size, true,<br>                    rx_q->dma_rx_phy, desc_size);<br>    }<br>    // 主循环，在NAPI预算内尽可能多地处理已接收完成的描述符<br>    while (count < limit) {<br>        unsigned int buf1_len = 0, buf2_len = 0;<br>        enum pkt_hash_types hash_type;<br>        struct stmmac_rx_buffer *buf;<br>        struct dma_desc *np, *p;<br>        int entry;<br>        u32 hash;<br><br>        // 如果是本次poll的第一次迭代，且上次poll遗留了未完成的包状态，则恢复状态<br>        if (!count && rx_q->state_saved) {<br>            skb = rx_q->state.skb;<br>            error = rx_q->state.error;<br>            len = rx_q->state.len;<br>        // 否则重置状态，开始处理新的数据包<br>        } else {<br>            rx_q->state_saved = false;<br>            skb = NULL;<br>            error = 0;<br>            len = 0;<br>        }<br><br>read_again:<br>        // 如果即将达到预算上限且预算大于1，提前退出，避免多段包处理一半导致状态复杂<br>        if ((count >= limit - 1) && limit > 1)<br>            break;<br><br>        // 重置当前描述符的两个缓冲区长度<br>        buf1_len = 0;<br>        buf2_len = 0;<br>        // 获取当前要处理的描述符索引<br>        entry = next_entry;<br>        // 获取该索引对应的软件缓冲区结构<br>        buf = &rx_q->buf_pool[entry];<br><br>        // 根据是否使用扩展描述符，获取当前描述符的硬件指针<br>        if (priv->extend_desc)<br>            p = (struct dma_desc *)(rx_q->dma_erx + entry);<br>        else<br>            p = rx_q->dma_rx + entry;<br><br>        // 读取描述符状态字，包含DMA写入的接收结果、错误标志等<br>        status = stmmac_rx_status(priv, &priv->dev->stats,<br>                &priv->xstats, p);<br>        // 如果OWN位仍为1，说明DMA引擎仍拥有该描述符，数据未收完，退出轮询<br>        if (unlikely(status & dma_own))<br>            break;<br><br>        // 推进cur_rx到下一个描述符索引<br>        rx_q->cur_rx = STMMAC_GET_ENTRY(rx_q->cur_rx,<br>                        priv->dma_conf.dma_rx_size);<br>        next_entry = rx_q->cur_rx;<br><br>        // 获取下一个描述符指针，用于预取和后续时间戳读取<br>        if (priv->extend_desc)<br>            np = (struct dma_desc *)(rx_q->dma_erx + next_entry);<br>        else<br>            np = rx_q->dma_rx + next_entry;<br><br>        // 预取下一个描述符到CPU缓存，提升性能<br>        prefetch(np);<br><br>        // 如果使用扩展描述符，额外读取扩展状态字段，如时间戳等<br>        if (priv->extend_desc)<br>            stmmac_rx_extended_status(priv, &priv->dev->stats,<br>                    &priv->xstats, rx_q->dma_erx + entry);<br>        // 如果硬件标记该帧需要丢弃，如严重CRC错误等<br>        if (unlikely(status == discard_frame)) {<br>            // 直接将该内存页归还给页池<br>            page_pool_recycle_direct(rx_q->page_pool, buf->page);<br>            buf->page = NULL;<br>            // 标记错误，后续逻辑会跳过或丢弃该包<br>            error = 1;<br>            // 如果不是为了硬件时间戳而保留错误帧，则增加错误计数<br>            if (!priv->hwts_rx_en)<br>                priv->dev->stats.rx_errors++;<br>        }<br><br>        // 如果之前有错误，且当前描述符不是最后一段，说明整个多段包都坏了，跳过剩余分段<br>        if (unlikely(error && (status & rx_not_ls)))<br>            goto read_again;<br>        // 如果是单段包错误或多段包的最后一个分段错误，释放已分配的skb并继续下一个包<br>        if (unlikely(error)) {<br>            dev_kfree_skb(skb);<br>            skb = NULL;<br>            count++;<br>            continue;<br>        }<br><br>        /* Buffer is good. Go on. */<br><br>        // 预取数据包所在内存页到CPU缓存，加速后续访问<br>        prefetch(page_address(buf->page) + buf->page_offset);<br>        if (buf->sec_page)<br>            prefetch(page_address(buf->sec_page));<br><br>        // 计算主缓冲区Buf1的有效数据长度并累加到总长度<br>        buf1_len = stmmac_rx_buf1_len(priv, p, status, len);<br>        len += buf1_len;<br>        // 计算辅助缓冲区Buf2的有效数据长度并累加到总长度<br>        buf2_len = stmmac_rx_buf2_len(priv, p, status, len);<br>        len += buf2_len;<br><br>        /* ACS is disabled; strip manually. */<br>        if (likely(!(status & rx_not_ls))) {<br>            if (buf2_len) {<br>                buf2_len -= ETH_FCS_LEN;<br>                len -= ETH_FCS_LEN;<br>            } else if (buf1_len) {<br>                buf1_len -= ETH_FCS_LEN;<br>                len -= ETH_FCS_LEN;<br>            }<br>        }<br><br>        // 如果skb为空，说明这是数据包的第一个分段，需要运行XDP程序并可能新建skb<br>        if (!skb) {<br>            unsigned int pre_len, sync_len;<br><br>            // 将主缓冲区的DMA数据同步到CPU缓存，确保CPU读取到最新数据<br>            dma_sync_single_for_cpu(priv->device, buf->addr,<br>                        buf1_len, dma_dir);<br><br>            // 初始化XDP缓冲区结构<br>            xdp_init_buff(&xdp, buf_sz, &rx_q->xdp_rxq);<br>            // 准备XDP缓冲区，指向页池中的实际数据区域<br>            xdp_prepare_buff(&xdp, page_address(buf->page),<br>                    buf->page_offset, buf1_len, false);<br><br>            // 记录XDP程序运行前的数据长度，用于后续DMA同步范围计算<br>            pre_len = xdp.data_end - xdp.data_hard_start -<br>                buf->page_offset;<br>            // 运行绑定的XDP程序，返回处理结果（PASS/DROP/TX/REDIRECT）<br>            skb = stmmac_xdp_run_prog(priv, &xdp);<br>            /* Due xdp_adjust_tail: DMA sync for_device<br>            * cover max len CPU touch<br>            */<br>            sync_len = xdp.data_end - xdp.data_hard_start -<br>                buf->page_offset;<br>            sync_len = max(sync_len, pre_len);<br><br>            /* For Not XDP_PASS verdict */<br>            // 如果XDP程序没有返回PASS，返回值为ERR_PTR<br>            if (IS_ERR(skb)) {<br>                // 解析XDP动作结果<br>                unsigned int xdp_res = -PTR_ERR(skb);<br><br>                // 如果是XDP_DROP或XDP_ABORTED<br>                if (xdp_res & STMMAC_XDP_CONSUMED) {<br>                    // 将内存页归还给页池<br>                    page_pool_put_page(rx_q->page_pool,<br>                            virt_to_head_page(xdp.data),<br>                            sync_len, true);<br>                    buf->page = NULL;<br>                    // 增加丢包统计<br>                    priv->dev->stats.rx_dropped++;<br><br>                    /* Clear skb as it was set as<br>                    * status by XDP program.<br>                    */<br>                    // 清空skb指针<br>                    skb = NULL;<br><br>                    // 如果是多段包，跳过剩余分段<br>                    if (unlikely((status & rx_not_ls)))<br>                        goto read_again;<br><br>                    count++;<br>                    continue;<br>                // 如果是XDP_TX或XDP_REDIRECT<br>                } else if (xdp_res & (STMMAC_XDP_TX \|<br>                            STMMAC_XDP_REDIRECT)) {<br>                    // 记录XDP动作状态，用于后续统一收尾，如刷新TX队列、xdp_do_flush<br>                    xdp_status \|= xdp_res;<br>                    buf->page = NULL;<br>                    skb = NULL;<br>                    count++;<br>                    continue;<br>                }<br>            }<br>        }<br><br>        // 如果XDP返回PASS，且skb仍未分配，则需要新建skb并拷贝数据<br>        if (!skb) {<br>            /* XDP program may expand or reduce tail */<br>            buf1_len = xdp.data_end - xdp.data;<br><br>            // 在NAPI上下文中分配线性sk_buff头部空间<br>            skb = napi_alloc_skb(&ch->rx_napi, buf1_len);<br>            if (!skb) {<br>                priv->dev->stats.rx_dropped++;<br>                count++;<br>                goto drain_data;<br>            }<br><br>            /* XDP program may adjust header */<br>            // 将XDP缓冲区中的数据拷贝到skb线性数据区<br>            skb_copy_to_linear_data(skb, xdp.data, buf1_len);<br>            skb_put(skb, buf1_len);<br><br>            /* Data payload copied into SKB, page ready for recycle */<br>            // 数据已拷贝到skb，原来的内存页可以直接归还给页池<br>            page_pool_recycle_direct(rx_q->page_pool, buf->page);<br>            buf->page = NULL;<br>        // 如果skb已存在，且buf1有数据，则作为分片追加到skb<br>        } else if (buf1_len) {<br>            // 同步DMA数据到CPU<br>            dma_sync_single_for_cpu(priv->device, buf->addr,<br>                        buf1_len, dma_dir);<br>            // 将该内存页作为分片追加到skb的分片列表<br>            skb_add_rx_frag(skb, skb_shinfo(skb)->nr_frags,<br>                    buf->page, buf->page_offset, buf1_len,<br>                    priv->dma_conf.dma_buf_sz);<br><br>            /* Data payload appended into SKB */<br>            // 解除页池对该页的追踪，skb接管该页生命周期<br>            page_pool_release_page(rx_q->page_pool, buf->page);<br>            buf->page = NULL;<br>        }<br><br>        // 如果启用了Split Header且辅助缓冲区有数据，同样作为分片追加<br>        if (buf2_len) {<br>            // 同步辅助页的DMA数据<br>            dma_sync_single_for_cpu(priv->device, buf->sec_addr,<br>                        buf2_len, dma_dir);<br>            // 将辅助页作为分片追加到skb<br>            skb_add_rx_frag(skb, skb_shinfo(skb)->nr_frags,<br>                    buf->sec_page, 0, buf2_len,<br>                    priv->dma_conf.dma_buf_sz);<br><br>            /* Data payload appended into SKB */<br>            // 解除页池对该页的追踪，skb接管该页生命周期<br>            page_pool_release_page(rx_q->page_pool, buf->sec_page);<br>            buf->sec_page = NULL;<br>        }<br><br>drain_data:<br>        // 如果当前描述符不是最后一段，说明大包还没收完，继续读取下一个描述符<br>        if (likely(status & rx_not_ls))<br>            goto read_again;<br>        // 如果skb为空，可能被XDP消耗或分配失败，直接继续下一个包<br>        if (!skb)<br>            continue;<br><br>        /* Got entire packet into SKB. Finish it. */<br><br>        // 如果启用了硬件RX时间戳，从描述符中提取时间戳并附加到skb<br>        stmmac_get_rx_hwtstamp(priv, p, np, skb);<br>        stmmac_rx_vlan(priv->dev, skb);<br>        // 解析以太网头部，设置协议类型（如IPv4/IPv6）和MAC地址<br>        skb->protocol = eth_type_trans(skb, priv->dev);<br><br>        // 如果硬件不支持RX校验和卸载，标记需要软件计算校验和<br>        if (unlikely(!coe))<br>            skb_checksum_none_assert(skb);<br>        else<br>            // 硬件已验证校验和，标记为无需软件重复计算<br>            skb->ip_summed = CHECKSUM_UNNECESSARY; // RK3588支持硬件校验和卸载<br><br>        if (!stmmac_get_rx_hash(priv, p, &hash, &hash_type))<br>            skb_set_hash(skb, hash, hash_type);<br><br>        // 记录接收队列索引到skb<br>        skb_record_rx_queue(skb, queue);<br>        // 将数据包提交给NAPI的GRO引擎，然后进入协议栈<br>        napi_gro_receive(&ch->rx_napi, skb);<br>        // 清空skb指针，防止重复释放<br>        skb = NULL;<br><br>        // 更新设备接收包数和字节数统计<br>        priv->dev->stats.rx_packets++;<br>        priv->dev->stats.rx_bytes += len;<br>        // 增加本次poll处理的包计数<br>        count++;<br>    }<br><br>    // 如果退出循环时当前包还未接收完或skb仍在构建中，保存状态<br>    if (status & rx_not_ls \| skb) {<br>        rx_q->state_saved = true;<br>        rx_q->state.skb = skb;<br>        rx_q->state.error = error;<br>        rx_q->state.len = len;<br>    }<br><br>    // 完成XDP收尾工作：刷新XDP_TX队列、调用xdp_do_flush等<br>    stmmac_finalize_xdp_rx(priv, xdp_status);<br><br>    // 重新填充RX描述符环，将新的内存页交还给DMA引擎<br>    stmmac_rx_refill(priv, queue);<br><br>    // 更新驱动内部扩展统计信息<br>    priv->xstats.rx_pkt_n += count;<br>    priv->xstats.rxq_stats[queue].rx_pkt_n += count;<br><br>    // 返回本次NAPI poll实际处理的工作量<br>    return count;<br>}|

#### 9.5.4.15. 接收缓冲区补充[¶](#id57 "永久链接至标题")

stmmac_rx_refill函数在每次NAPI轮询结束后调用，负责补充已消耗的接收缓冲区。它从Page Pool分配新的页面，设置DMA地址到描述符中，然后设置OWN位将描述符交还给DMA引擎，最后更新RX尾指针寄存器。

stmmac_rx_refill函数(位于内核源码/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)[¶](#id124 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48<br>49<br>50<br>51<br>52<br>53<br>54<br>55<br>56<br>57<br>58<br>59<br>60<br>61<br>62<br>63<br>64<br>65<br>66<br>67<br>68<br>69<br>70<br>71<br>72<br>73<br>74<br>75<br>76<br>77<br>78<br>79<br>80<br>81|static inline void stmmac_rx_refill(struct stmmac_priv *priv, u32 queue)<br>{<br>    struct stmmac_rx_queue *rx_q = &priv->dma_conf.rx_queue[queue];<br>    int dirty = stmmac_rx_dirty(priv, queue);<br>    unsigned int entry = rx_q->dirty_rx;<br>    gfp_t gfp = (GFP_ATOMIC \| __GFP_NOWARN);<br><br>    // 如果主机DMA地址宽度小于等于32位，限制分配的内存必须在DMA32区域<br>    if (priv->dma_cap.host_dma_width <= 32)<br>        gfp \|= GFP_DMA32;<br><br>    // 循环处理所有需要重新填充的脏描述符<br>    while (dirty-- > 0) {<br>        // 获取当前索引对应的软件缓冲区元数据结构<br>        struct stmmac_rx_buffer *buf = &rx_q->buf_pool[entry];<br>        // 硬件描述符指针<br>        struct dma_desc *p;<br>        bool use_rx_wd;<br><br>        // 根据是否使用扩展描述符，获取当前描述符的硬件指针<br>        if (priv->extend_desc)<br>            p = (struct dma_desc *)(rx_q->dma_erx + entry);<br>        else<br>            p = rx_q->dma_rx + entry;<br><br>        // 如果主缓冲区页面为空，从页池分配新的内存页<br>        if (!buf->page) {<br>            buf->page = page_pool_alloc_pages(rx_q->page_pool, gfp);<br>            if (!buf->page)<br>                break;<br>        }<br><br>        // 如果启用了Split Header且辅助页面为空，分配辅助页<br>        if (priv->sph && !buf->sec_page) {<br>            buf->sec_page = page_pool_alloc_pages(rx_q->page_pool, gfp);<br>            if (!buf->sec_page)<br>                break;<br><br>            // 获取辅助页的DMA地址<br>            buf->sec_addr = page_pool_get_dma_addr(buf->sec_page);<br>        }<br><br>        // 计算主缓冲区的DMA地址<br>        buf->addr = page_pool_get_dma_addr(buf->page) + buf->page_offset;<br><br>        // 将主缓冲区DMA地址写入描述符<br>        stmmac_set_desc_addr(priv, p, buf->addr);<br>        // 如果启用了Split Header，将辅助页DMA地址写入描述符并标记有效<br>        if (priv->sph)<br>            stmmac_set_desc_sec_addr(priv, p, buf->sec_addr, true);<br>        else<br>        // 否则清除辅助地址有效标志<br>            stmmac_set_desc_sec_addr(priv, p, buf->sec_addr, false);<br>        stmmac_refill_desc3(priv, rx_q, p);<br><br>        rx_q->rx_count_frames++;<br>        rx_q->rx_count_frames += priv->rx_coal_frames[queue];<br>        if (rx_q->rx_count_frames > priv->rx_coal_frames[queue])<br>            rx_q->rx_count_frames = 0;<br><br>        use_rx_wd = !priv->rx_coal_frames[queue];<br>        use_rx_wd \|= rx_q->rx_count_frames > 0;<br>        if (!priv->use_riwt)<br>            use_rx_wd = false;<br><br>        // 写内存屏障：确保在设置OWN位之前，所有描述符字段都已写入内存，防止DMA引擎读到旧数据<br>        dma_wmb();<br>        // 设置描述符的OWN位，将控制权交还给DMA引擎<br>        stmmac_set_rx_owner(priv, p, use_rx_wd);<br><br>        // 计算下一个描述符索引<br>        entry = STMMAC_GET_ENTRY(entry, priv->dma_conf.dma_rx_size);<br>    }<br>    // 更新脏描述符索引，记录下次填充的起点<br>    rx_q->dirty_rx = entry;<br>    // 计算新的RX尾指针物理地址<br>    rx_q->rx_tail_addr = rx_q->dma_rx_phy +<br>                (rx_q->dirty_rx * sizeof(struct dma_desc));<br>    // 将尾指针地址写入硬件寄存器，通知DMA引擎有新描述符可用，可以开始接收新数据<br>    stmmac_set_rx_tail_ptr(priv, priv->ioaddr, rx_q->rx_tail_addr, queue);<br>}|

#### 9.5.4.16. 收发数据流总结[¶](#id58 "永久链接至标题")

##### 9.5.4.16.1. 发送路径[¶](#id59 "永久链接至标题")

当用户态程序通过socket发送数据时，报文经过内核协议栈（TCP/IP）层层封装后，最终到达网络设备层，调用stmmac_xmit函数。 该函数首先检查TX描述符环是否有足够的空闲空间，若空间不足则停止发送队列并返回NETDEV_TX_BUSY。 空间充足时，驱动对skb的线性数据区和各分片分别执行DMA映射，将物理地址填充到对应的TX描述符中，同时设置校验和卸载标志、VLAN标签插入等硬件特性参数。 所有描述符填充完毕后，驱动设置第一个描述符的OWN位，将所有权移交给DMA引擎，然后通过写TX尾指针寄存器触发DMA传输。 DMA引擎将报文数据从内存搬运到MAC硬件的发送FIFO中，MAC硬件再通过RGMII接口将数据发送给PHY芯片，最终由PHY转换为电信号发送到网线。

发送完成后，DMA引擎产生发送完成中断。 该中断触发NAPI调度，进入软中断上下文执行stmmac_napi_poll_tx，其内部调用stmmac_tx_clean函数。 该函数从dirty_tx指针开始遍历已完成的描述符，检查每个描述符的状态，确认DMA已完成传输后，解除对应的DMA映射，释放skb，更新统计计数。 如果之前发送队列因描述符环满而被停止，且当前可用空间已超过阈值，则唤醒发送队列，允许协议栈继续下发数据。

##### 9.5.4.16.2. 接收路径[¶](#id60 "永久链接至标题")

当网络上的报文到达PHY芯片时，PHY将电信号转换为数字数据，通过RGMII接口传送给MAC硬件。 MAC硬件的DMA引擎将报文数据写入驱动预先分配好的RX缓冲区中（这些缓冲区通过Page Pool机制管理，每个缓冲区对应一个RX描述符，其中记录了缓冲区的物理地址）。 DMA写入完成后，产生接收中断。

接收中断触发NAPI调度，进入软中断上下文执行stmmac_napi_poll_rx，其内部调用stmmac_rx函数。 该函数在budget限制内循环处理RX描述符环：首先读取描述符状态字，判断DMA是否已完成写入（通过检查OWN位）； 若报文存在错误则丢弃并计入错误统计；若报文正常，则先执行XDP程序，然后根据XDP的处理结果决定后续动作。 对于XDP_PASS的报文，驱动构建skb：对于小包，分配新的skb并将数据拷贝进去，原页面归还Page Pool； 对于大包，直接将页面作为分片挂载到skb上，实现零拷贝。 构建完skb后，调用eth_type_trans解析以太网头、设置协议类型和包类型，然后调用napi_gro_receive将报文提交给内核协议栈，协议栈再进行GRO聚合、IP层处理、传输层分发等后续操作。

本轮轮询处理完所有已到达的报文后，驱动调用stmmac_rx_refill函数补充已消耗的接收缓冲区：从Page Pool分配新的页面，将页面的DMA地址写入描述符，设置OWN位将描述符归还给DMA引擎，并更新RX尾指针寄存器，确保DMA引擎始终有可用的缓冲区接收后续报文。 若本轮处理的报文数小于budget，说明队列已空，调用napi_complete_done退出轮询模式并重新使能接收中断。

#### 9.5.4.17. 链路管理路径总结[¶](#id61 "永久链接至标题")

当用户执行ip link set eth0 up时，内核调用stmmac_open函数。 该函数首先分配DMA描述符环和接收缓冲区，然后调用stmmac_hw_setup完成MAC硬件初始化，接着调用stmmac_init_phy通过PHYLINK框架连接PHY设备，最后调用phylink_start启动PHYLINK状态机。

PHYLINK启动后，PHY芯片开始自协商过程，与对端设备协商速率（10M/100M/1000M）和双工模式。 自协商完成后，PHYLINK检测到链路状态变化，读取PHY的状态寄存器获取协商结果，然后回调MAC侧的stmmac_mac_link_up函数。 该函数根据协商出的速率设置MAC控制寄存器中对应的速率位，配置流控参数，并使能MAC收发功能。 同时，该函数通过plat_dat->fix_mac_speed回调调用rk_fix_speed函数，进一步调用RK3588平台特有的rk3588_set_gmac_speed，向PHP_GRF配置寄存器写入对应的时钟分频值（千兆时选择125MHz，百兆时选择25MHz，十兆时选择2.5MHz），确保MAC与PHY之间的RGMII时钟频率正确匹配。 至此，链路完全就绪，网卡可以正常收发数据。

### 9.5.5. PHY驱动解析[¶](#id62 "永久链接至标题")

PHY驱动是内核网络子系统中连接MAC驱动与物理层芯片的桥梁。 它运行在MDIO总线之上，向上对接PHYLINK框架，向下操作PHY芯片寄存器，完成物理层的管理工作。

#### 9.5.5.1. 驱动注册[¶](#id63 "永久链接至标题")

realtek_drvs数组是Realtek PHY驱动的注册表，每个条目对应一款PHY芯片。 module_phy_driver()宏将数组注册到内核PHY驱动框架。 当MDIO总线扫描到PHY ID为0x001cc916的设备时，匹配到RTL8211F条目，调用对应的回调函数。

驱动注册(位于内核源码/drivers/net/phy/realtek.c)[¶](#id125 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25|static struct phy_driver realtek_drvs[] = {<br>    // ... 其他PHY型号<br>    {<br>        PHY_ID_MATCH_EXACT(0x001cc916),             // 匹配PHY ID为0x001cc916的设备<br>        .name       = "RTL8211F Gigabit Ethernet",  // 驱动名称，用于在sysfs文件系统等中显示<br>        .probe      = rtl821x_probe,                // 探测函数，在设备与驱动匹配成功时调用<br>        .config_init    = &rtl8211f_config_init,    // 初始化配置函数<br>        .read_status    = rtlgen_read_status,       // 读取状态函数<br>        .config_intr    = &rtl8211f_config_intr,    // 中断配置函数<br>        .handle_interrupt = rtl8211f_handle_interrupt, // 中断处理服务程序<br>        .suspend    = genphy_suspend,       // 挂起函数<br>        .resume     = rtl821x_resume,       // 恢复函数<br>        .read_page  = rtl821x_read_page,    // 读取页函数<br>        .write_page = rtl821x_write_page,   // 写入页函数<br>    },<br>    // ... 其他PHY型号<br>};<br>module_phy_driver(realtek_drvs);<br><br>static const struct mdio_device_id __maybe_unused realtek_tbl[] = {<br>    { PHY_ID_MATCH_VENDOR(0x001cc800) },<br>    { PHY_ID_MATCH_VENDOR(0x001ccb30) },<br>    { }<br>};<br>MODULE_DEVICE_TABLE(mdio, realtek_tbl);|

#### 9.5.5.2. PHY探测函数[¶](#id64 "永久链接至标题")

rtl821x_probe函数在MDIO总线扫描到RTL8211F（PHY ID=0x001cc916）时被调用。 它读取PHY硬件当前配置，结合设备树属性，缓存到私有结构体中，供后续config_init使用。

rtl821x_probe函数(位于内核源码/drivers/net/phy/realtek.c)[¶](#id126 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38|static int rtl821x_probe(struct phy_device *phydev)<br>{<br>    struct device *dev = &phydev->mdio.dev;<br>    struct rtl821x_priv *priv;<br>    u32 phy_id = phydev->drv->phy_id;<br>    int ret;<br><br>    priv = devm_kzalloc(dev, sizeof(*priv), GFP_KERNEL);<br>    if (!priv)<br>        return -ENOMEM;<br><br>    // 读取扩展页面0xa43的PHYCR1寄存器，获取ALDPS省电模式当前配置<br>    ret = phy_read_paged(phydev, 0xa43, RTL8211F_PHYCR1);<br>    if (ret < 0)<br>        return ret;<br><br>    priv->phycr1 = ret & (RTL8211F_ALDPS_PLL_OFF \| RTL8211F_ALDPS_ENABLE \| RTL8211F_ALDPS_XTAL_OFF);<br>    // 若DTS中配置了realtek,aldps-enable，则启用ALDPS省电模式<br>    if (of_property_read_bool(dev->of_node, "realtek,aldps-enable"))<br>        priv->phycr1 \|= RTL8211F_ALDPS_PLL_OFF \| RTL8211F_ALDPS_ENABLE \| RTL8211F_ALDPS_XTAL_OFF;<br><br>    // RTL8211F-VD型号没有PHYCR2寄存器，需特殊处理<br>    priv->has_phycr2 = !(phy_id == RTL_8211FVD_PHYID);<br>    if (priv->has_phycr2) {<br>        ret = phy_read_paged(phydev, 0xa43, RTL8211F_PHYCR2);<br>        if (ret < 0)<br>            return ret;<br><br>        priv->phycr2 = ret & RTL8211F_CLKOUT_EN;<br>        if (of_property_read_bool(dev->of_node, "realtek,clkout-disable"))<br>            priv->phycr2 &= ~RTL8211F_CLKOUT_EN;<br>    }<br><br>    // 将私有数据挂载到PHY设备<br>    phydev->priv = priv;<br><br>    return 0;<br>}|

#### 9.5.5.3. RTL8211F 初始化配置[¶](#rtl8211f "永久链接至标题")

rtl8211f_config_init函数是RTL8211F最核心的初始化函数，在PHYLINK启动链路协商时由PHY框架调用， 完成配置ALDPS省电模式、根据phydev->interface配置RGMII TX/RX延迟、配置时钟输出。

因为RK3588S的dts配置了phy-mode = “rgmii-rxid”，因此此函数会在PHY内部启用RX延迟，不启用TX延迟。

rtl8211f_config_init函数(位于内核源码/drivers/net/phy/realtek.c)[¶](#id127 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48<br>49<br>50<br>51<br>52<br>53<br>54<br>55<br>56<br>57<br>58<br>59<br>60<br>61<br>62<br>63<br>64<br>65<br>66<br>67<br>68<br>69<br>70<br>71<br>72<br>73<br>74<br>75<br>76<br>77<br>78<br>79<br>80<br>81<br>82<br>83<br>84<br>85<br>86<br>87<br>88<br>89<br>90<br>91<br>92<br>93<br>94<br>95<br>96|static int rtl8211f_config_init(struct phy_device *phydev)<br>{<br>    struct rtl821x_priv *priv = phydev->priv;<br>    struct device *dev = &phydev->mdio.dev;<br>    u16 val_txdly, val_rxdly;<br>    int ret;<br><br>    // 配置ALDPS省电模式<br>    ret = phy_modify_paged_changed(phydev, 0xa43, RTL8211F_PHYCR1,<br>                    RTL8211F_ALDPS_PLL_OFF \| RTL8211F_ALDPS_ENABLE \| RTL8211F_ALDPS_XTAL_OFF,<br>                    priv->phycr1);<br>    if (ret < 0) {<br>        dev_err(dev, "aldps mode  configuration failed: %pe\n",<br>            ERR_PTR(ret));<br>        return ret;<br>    }<br><br>    // 根据PHY与MAC之间的接口模式，决定TX和RX的内部延迟配置<br>    switch (phydev->interface) {<br>    // 标准RGMII：延迟由MAC端或PCB走线处理，PHY端不加延迟<br>    case PHY_INTERFACE_MODE_RGMII:<br>        val_txdly = 0;  // 禁用PHY的TX延迟<br>        val_rxdly = 0;  // 禁用PHY的RX延迟<br>        break;<br><br>    // RGMII_RXID：PHY端在RX方向加延迟<br>    case PHY_INTERFACE_MODE_RGMII_RXID:<br>        val_txdly = 0;<br>        val_rxdly = RTL8211F_RX_DELAY;<br>        break;<br><br>    // RGMII_TXID：PHY端在TX方向加延迟<br>    case PHY_INTERFACE_MODE_RGMII_TXID:<br>        val_txdly = RTL8211F_TX_DELAY;<br>        val_rxdly = 0;<br>        break;<br><br>    // RGMII_ID：PHY端在TX和RX方向都加延迟<br>    case PHY_INTERFACE_MODE_RGMII_ID:<br>        val_txdly = RTL8211F_TX_DELAY;<br>        val_rxdly = RTL8211F_RX_DELAY;<br>        break;<br><br>    default: /* the rest of the modes imply leaving delay as is. */<br>        return 0;<br>    }<br><br>    // 配置TX延迟寄存器<br>    ret = phy_modify_paged_changed(phydev, 0xd08, 0x11, RTL8211F_TX_DELAY,<br>                    val_txdly);<br>    if (ret < 0) {<br>        dev_err(dev, "Failed to update the TX delay register\n");<br>        return ret;<br>    } else if (ret) {<br>        dev_dbg(dev,<br>            "%s 2ns TX delay (and changing the value from pin-strapping RXD1 or the bootloader)\n",<br>            val_txdly ? "Enabling" : "Disabling");<br>    } else {<br>        dev_dbg(dev,<br>            "2ns TX delay was already %s (by pin-strapping RXD1 or bootloader configuration)\n",<br>            val_txdly ? "enabled" : "disabled");<br>    }<br><br>    // 配置RX延迟寄存器<br>    ret = phy_modify_paged_changed(phydev, 0xd08, 0x15, RTL8211F_RX_DELAY,<br>                    val_rxdly);<br>    if (ret < 0) {<br>        dev_err(dev, "Failed to update the RX delay register\n");<br>        return ret;<br>    } else if (ret) {<br>        dev_dbg(dev,<br>            "%s 2ns RX delay (and changing the value from pin-strapping RXD0 or the bootloader)\n",<br>            val_rxdly ? "Enabling" : "Disabling");<br>    } else {<br>        dev_dbg(dev,<br>            "2ns RX delay was already %s (by pin-strapping RXD0 or bootloader configuration)\n",<br>            val_rxdly ? "enabled" : "disabled");<br>    }<br><br>    // 检查该PHY型号是否有PHYCR2寄存器<br>    if (priv->has_phycr2) {<br>        // 配置CLKOUT时钟输出功能<br>        ret = phy_modify_paged(phydev, 0xa43, RTL8211F_PHYCR2,<br>                    RTL8211F_CLKOUT_EN, priv->phycr2);<br>        if (ret < 0) {<br>            dev_err(dev, "clkout configuration failed: %pe\n",<br>                ERR_PTR(ret));<br>            return ret;<br>        }<br><br>        // 配置完成后，对PHY执行一次软复位，使上述延迟和时钟配置生效<br>        return genphy_soft_reset(phydev);<br>    }<br><br>    return 0;<br>}|

#### 9.5.5.4. 中断配置[¶](#id65 "永久链接至标题")

rtl8211f_config_intr函数用于使能或禁用RTL8211F的链路状态中断。 当PHYLINK框架需要监控链路变化时，会调用此函数开启中断；当不再需要时，如轮询模式，会关闭中断。

rtl8211f_config_intr函数(位于内核源码/drivers/net/phy/realtek.c)[¶](#id128 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29|static int rtl8211f_config_intr(struct phy_device *phydev)<br>{<br>    u16 val;<br>    int err;<br><br>    // 判断内核PHY子系统请求的动作，是要启用中断还是禁用中断<br>    if (phydev->interrupts == PHY_INTERRUPT_ENABLED) {<br>        // 在开启中断前，先调用ack函数读取一次中断状态寄存器，清除可能遗留的挂起中断<br>        err = rtl8211f_ack_interrupt(phydev);<br>        if (err)<br>            return err;<br><br>        // 设置中断使能掩码<br>        val = RTL8211F_INER_LINK_STATUS;<br>        // 将配置值写入中断使能寄存器<br>        err = phy_write_paged(phydev, 0xa42, RTL821x_INER, val);<br>    } else {<br>        // 将掩码设置为0<br>        val = 0;<br>        // 写入中断使能寄存器，正式关闭中断<br>        err = phy_write_paged(phydev, 0xa42, RTL821x_INER, val);<br>        if (err)<br>            return err;<br>        // 禁用中断后，再次调用ack函数读取状态寄存器以清除挂起的中断<br>        err = rtl8211f_ack_interrupt(phydev);<br>    }<br><br>    return err;<br>}|

#### 9.5.5.5. 中断处理[¶](#id66 "永久链接至标题")

rtl8211f_handle_interrupt函数是RTL8211F的中断服务函数。 当触发中断时，此函数读取中断状态寄存器，判断是否为链路状态变化中断，若是则触发PHYLINK状态机重新协商。

rtl8211f_handle_interrupt函数(位于内核源码/drivers/net/phy/realtek.c)[¶](#id129 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21|static irqreturn_t rtl8211f_handle_interrupt(struct phy_device *phydev)<br>{<br>    int irq_status;<br><br>    // 读取RTL8211F的中断状态寄存器<br>    irq_status = phy_read_paged(phydev, 0xa43, RTL8211F_INSR);<br>    if (irq_status < 0) {<br>        phy_error(phydev);<br>        return IRQ_NONE;<br>    }<br><br>    // 检查读取到的状态字中，是否包含了链路状态变化的中断标志位<br>    if (!(irq_status & RTL8211F_INER_LINK_STATUS))<br>        return IRQ_NONE;    // 如果该位为0，说明触发的不是链路变化中断，返回IRQ_NONE<br><br>    // 确认是链路状态变化中断后，触发内核的PHY状态机<br>    phy_trigger_machine(phydev);<br><br>    // 返回IRQ_HANDLED，告诉内核中断处理完毕<br>    return IRQ_HANDLED;<br>}|

#### 9.5.5.6. 链路状态读取[¶](#id67 "永久链接至标题")

rtlgen_read_status函数是Realtek PHY驱动中用于读取并更新PHY当前链路状态的核心回调函数。

rtlgen_read_status函数(位于内核源码/drivers/net/phy/realtek.c)[¶](#id130 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12|static int rtlgen_read_status(struct phy_device *phydev)<br>{<br>    int ret;<br><br>    // 调用内核PHY子系统的通用函数，读取标准IEEE 802.3 MII寄存器<br>    ret = genphy_read_status(phydev);<br>    if (ret < 0)<br>        return ret;<br><br>    // 调用Realtek特有的私有函数来读取实际速度<br>    return rtlgen_get_speed(phydev);<br>}|

标准MII状态寄存器可能无法正确反映实际协商速率， 因此驱动通过读取扩展页面0xa43的寄存器0x12来获取真实链路速率。

rtlgen_get_speed函数(位于内核源码/drivers/net/phy/realtek.c)[¶](#id131 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39|static int rtlgen_get_speed(struct phy_device *phydev)<br>{<br>    int val;<br><br>    // 检查链路是否已建立<br>    if (!phydev->link)<br>        return 0;<br><br>    // 从扩展页0xa43的寄存器0x12中读取实际链路速度状态字<br>    val = phy_read_paged(phydev, 0xa43, 0x12);<br>    if (val < 0)<br>        return val;<br><br>    // 使用RTLGEN_SPEED_MASK掩码提取速度字段，并根据结果设置内核标准速度宏<br>    switch (val & RTLGEN_SPEED_MASK) {<br>    case 0x0000:<br>        phydev->speed = SPEED_10;<br>        break;<br>    case 0x0010:<br>        phydev->speed = SPEED_100;<br>        break;<br>    case 0x0020:<br>        phydev->speed = SPEED_1000;<br>        break;<br>    case 0x0200:<br>        phydev->speed = SPEED_10000;<br>        break;<br>    case 0x0210:<br>        phydev->speed = SPEED_2500;<br>        break;<br>    case 0x0220:<br>        phydev->speed = SPEED_5000;<br>        break;<br>    default:<br>        break;<br>    }<br><br>    return 0;<br>}|

## 9.6. 虚拟网卡回环实验[¶](#id68 "永久链接至标题")

本实验驱动基于Linux内核网络子系统框架开发，实现一款纯软件虚拟回环网卡，具备报文翻转回环、NAPI异步收包、报文完整解析打印、设备状态管理、sysfs调试配置、网络统计、ethtool信息查询等完整功能。

驱动实现原理：网卡发送的ARP/IPv4/ICMP请求报文，在驱动层完成MAC、IP、ICMP协议字段翻转，将请求伪装成应答报文，重新投递回内核网络栈，实现本地报文自收发回环效果，无需物理网卡和外部网络环境。

本章的示例代码目录为： **linux_driver/43_net_subsystem**

### 9.6.1. 驱动代码详解[¶](#id69 "永久链接至标题")

#### 9.6.1.1. 核心定义与数据结构[¶](#id70 "永久链接至标题")

核心定义与数据结构(位于linux_driver/43_net_subsystem/net_loopback.c)[¶](#id132 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14|#define DRV_NAME    "net_loopback"   /* 驱动名称 */<br>#define DRV_VERSION "1.0"            /* 驱动版本号 */<br><br>#define NAPI_BUDGET 64   /* 每次NAPI轮询最多处理64个包 */<br><br>/* 设备私有数据结构体 */<br>struct net_lb_priv {<br>    struct net_device *ndev;        /* 网络设备指针 */<br>    struct napi_struct napi;        /* NAPI轮询结构体 */<br>    struct sk_buff_head lb_queue;   /* 回环skb队列，TX包翻转后暂存于此 */<br>    spinlock_t lb_lock;             /* 保护回环队列的自旋锁 */<br>    struct net_device_stats stats;  /* 收发统计信息结构体 */<br>    bool debug;                     /* 报文详细打印开关 */<br>};|

关键说明：

- 第1-2行：定义驱动名称与版本，用于内核日志、ethtool信息打印。
    
- 第4行：定义NAPI处理预算，限制单次NAPI轮询最大处理报文数，避免CPU占用过高。
    
- 第8行：保存所属网络设备指针，实现私有数据与网卡设备绑定。
    
- 第9行：NAPI结构体，用于内核异步收包机制，替代中断轮询，提升报文处理效率。
    
- 第10行：skb报文队列，缓存发送后翻转完成的待回送报文，作为TX/RX数据中转缓冲区。
    
- 第11行：自旋锁，保护多线程并发下的报文队列操作。
    
- 第12行：设备统计结构体，记录收发包数、字节数、丢包数等流量信息。
    
- 第13行：调试开关变量，控制是否打印报文详细日志。
    

#### 9.6.1.2. 报文翻转处理函数[¶](#id71 "永久链接至标题")

net_lb_transform函数用于实现各类网络报文的协议翻转，将主机发送的请求报文（ARP请求、ICMP请求）伪装为应答报文，通过交换MAC、IP、修改协议操作码、重算校验和，完成报文回环预处理。

核心定义与数据结构(位于linux_driver/43_net_subsystem/net_loopback.c)[¶](#id133 "永久链接至代码")

|   |   |
|---|---|
|1<br>  2<br>  3<br>  4<br>  5<br>  6<br>  7<br>  8<br>  9<br> 10<br> 11<br> 12<br> 13<br> 14<br> 15<br> 16<br> 17<br> 18<br> 19<br> 20<br> 21<br> 22<br> 23<br> 24<br> 25<br> 26<br> 27<br> 28<br> 29<br> 30<br> 31<br> 32<br> 33<br> 34<br> 35<br> 36<br> 37<br> 38<br> 39<br> 40<br> 41<br> 42<br> 43<br> 44<br> 45<br> 46<br> 47<br> 48<br> 49<br> 50<br> 51<br> 52<br> 53<br> 54<br> 55<br> 56<br> 57<br> 58<br> 59<br> 60<br> 61<br> 62<br> 63<br> 64<br> 65<br> 66<br> 67<br> 68<br> 69<br> 70<br> 71<br> 72<br> 73<br> 74<br> 75<br> 76<br> 77<br> 78<br> 79<br> 80<br> 81<br> 82<br> 83<br> 84<br> 85<br> 86<br> 87<br> 88<br> 89<br> 90<br> 91<br> 92<br> 93<br> 94<br> 95<br> 96<br> 97<br> 98<br> 99<br>100<br>101<br>102<br>103<br>104<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119|/*<br>* 回环报文翻转：将TX报文转换为对端回复再回送RX<br>*<br>* 处理逻辑：<br>*   - 以太网层：交换源/目的MAC<br>*   - ARP：交换发送方/目标的IP+MAC，opcode请求变应答<br>*   - IP：交换源/目的IP<br>*   - ICMP：echo-request变echo-reply，并重算校验和<br>*<br>* 这样主机发出的请求会被伪装成对端的应答回送上来<br>*/<br>static struct sk_buff *net_lb_transform(struct net_lb_priv *priv,<br>                                        struct sk_buff *skb)<br>{<br>    /* 以太网头指针 */<br>    struct ethhdr *eth;<br>    /* 新建回送包指针 */<br>    struct sk_buff *nskb;<br>    /* MAC交换临时缓冲 */<br>    unsigned char tmp_mac[ETH_ALEN];<br>    /* IP交换临时变量 */<br>    __be32 tmp_ip;<br><br>    /* 完整拷贝原skb，拷贝后可安全修改 */<br>    nskb = skb_copy(skb, GFP_ATOMIC);<br>    if (!nskb)<br>        return NULL;<br><br>    /* 以太网层：交换源/目的 MAC */<br>    eth = (struct ethhdr *)nskb->data;              /* 指向数据起始处的以太网头 */<br>    memcpy(tmp_mac, eth->h_source, ETH_ALEN);       /* 保存源MAC到临时缓冲 */<br>    memcpy(eth->h_source, eth->h_dest, ETH_ALEN);   /* 源MAC <- 目的MAC */<br>    memcpy(eth->h_dest, tmp_mac, ETH_ALEN);         /* 目的MAC <- 原源MAC */<br><br>    /* 判断是否为ARP报文 */<br>    if (eth->h_proto == htons(ETH_P_ARP)) {<br>        /* ARP头 */<br>        struct arphdr *arp = (struct arphdr *)(nskb->data + ETH_HLEN);<br>        /* ARP中的发送方/目标IP指针 */<br>        __be32 *sip, *tip;<br>        /* ARP中的发送方/目标MAC指针 */<br>        u8 *sha, *tha;<br><br>        /* 仅处理以太网/IPv4 ARP，其他类型跳过 */<br>        if (arp->ar_hrd != htons(ARPHRD_ETHER) \|  /* 硬件类型非以太网 */<br>            arp->ar_pro != htons(ETH_P_IP))        /* 协议类型非IPv4 */<br>            goto done;<br><br>        /*<br>        *   ARP有效负载布局：<br>        *   ARP固定头  arp  8字节<br>        *   发送方MAC  sha  6字节<br>        *   发送方IP   sip  4字节<br>        *   目标方MAC  tha  6字节<br>        *   目标方IP   tip  4字节<br>        */<br><br>        /* 发送方MAC位于ARP头之后 */<br>        sha = (u8 *)(arp + 1);<br>        /* 发送方IP位于MAC之后 */<br>        sip = (__be32 *)(sha + ETH_ALEN);<br>        /* 目标MAC位于IP之后 */<br>        tha = (u8 *)sip + 4;<br>        /* 目标IP位于MAC之后 */<br>        tip = (__be32 *)(tha + ETH_ALEN);<br><br>        /* opcode：请求变应答 */<br>        if (arp->ar_op == htons(ARPOP_REQUEST))  /* 若为ARP请求 */<br>            arp->ar_op = htons(ARPOP_REPLY);     /* 改为ARP应答 */<br><br>        /* 交换发送方/目标MAC */<br>        memcpy(tmp_mac, sha, ETH_ALEN);   /* 保存发送方MAC */<br>        memcpy(sha, tha, ETH_ALEN);       /* 发送方MAC <- 目标MAC */<br>        memcpy(tha, tmp_mac, ETH_ALEN);   /* 目标MAC <- 原发送方MAC */<br><br>        /* 交换发送方/目标 IP */<br>        tmp_ip = *sip;  /* 保存发送方IP */<br>        *sip = *tip;    /* 发送方IP <- 目标IP */<br>        *tip = tmp_ip;  /* 目标IP <- 原发送方IP */<br><br>        goto done;      /* ARP处理完成，跳转返回 */<br>    }<br><br>    /* 判断是否为IPv4报文 */<br>    if (eth->h_proto == htons(ETH_P_IP)) {<br>        /* IP头 */<br>        struct iphdr *iph = (struct iphdr *)(nskb->data + ETH_HLEN);<br><br>        /* 交换源/目的IP */<br>        tmp_ip = iph->saddr;     /* 保存源IP */<br>        iph->saddr = iph->daddr; /* 源IP <- 目的IP */<br>        iph->daddr = tmp_ip;     /* 目的IP <- 原源IP */<br><br>        /* 重算IP头校验和 */<br>        iph->check = 0;                           /* 校验和字段清零 */<br>        iph->check = ip_fast_csum(iph, iph->ihl); /* 重算IP头校验和 */<br><br>        /* 判断是否为ICMP报文 */<br>        if (iph->protocol == IPPROTO_ICMP) {<br>            /* ICMP头位于IP头之后 */<br>            struct icmphdr *icmph = (struct icmphdr *)((u8 *)iph +<br>                                (iph->ihl * 4));<br>            /* 仅翻转echo-request */<br>            if (icmph->type == ICMP_ECHO) {       /* 若为echo请求 */<br>                icmph->type = ICMP_ECHOREPLY;     /* 改为echo应答 */<br><br>                /* 重算ICMP校验和 */<br>                icmph->checksum = 0;              /* 校验和字段清零 */<br>                icmph->checksum = csum_fold(      /* 折叠为16位校验和 */<br>                csum_partial(icmph, nskb->len - ETH_HLEN -<br>                                iph->ihl * 4, 0)); /* 计算ICMP部分校验和 */<br>            }<br>        }<br>    }<br><br>done:<br>    /* 返回转换后的回送包 */<br>    return nskb;<br>}|

关键说明：

- 第25行：调用skb_copy完整复制原始发送报文，避免直接修改原生skb导致内核栈异常。
    
- 第30-33行：以太网层处理，交换报文源MAC与目的MAC，实现二层链路反向。
    
- 第36行：判断报文是否为ARP协议，针对ARP请求处理翻转。
    
- 第45-47行：校验ARP报文为标准以太网+IPv4类型，过滤非法ARP报文。
    
- 第59-65行：按照ARP协议帧布局，确认发送方/目标MAC、IP字段指针。
    
- 第68-69行：将ARP请求操作码修改为应答操作码，伪装ARP响应报文。
    
- 第72-74行：交换ARP报文中的发送方与目标MAC地址。
    
- 第77-79行：交换ARP报文中的发送方与目标IP地址，完成ARP报文翻转。
    
- 第85行：判断报文为IPv4协议，进入三层IP翻转处理。
    
- 第90-92行：交换IP报文源地址与目的地址，实现三层路由反向。
    
- 第95-96行：清零IP校验和并重新计算，IP头部字段修改后必须重算校验和，否则报文校验失败被内核丢弃。
    
- 第99行：判断IP上层协议为ICMP，处理ping请求报文翻转。
    
- 第104-105行：将ICMP回声请求改为回声应答，适配ping命令应答。
    
- 第108-111行：清零并重新计算ICMP校验和，保证ICMP报文合法性。
    
- 第118行：统一出口，返回翻转完成的新报文，供后续回环投递。
    

#### 9.6.1.3. 协议名称解析工具函数[¶](#id72 "永久链接至标题")

包含4组协议码转可读字符串的工具函数，分别实现以太网协议、IP上层协议、ICMP类型、ARP操作码的文本解析，用于报文日志打印。

协议名称解析工具函数(位于linux_driver/43_net_subsystem/net_loopback.c)[¶](#id134 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47|/* 以太网协议号转可读名称 */<br>static const char *eth_proto_name(u16 proto)<br>{<br>    /* 根据协议号匹配 */<br>    switch (proto) {<br>    case ETH_P_IP:   return "IPv4";     // 宏定义在include/uapi/linux/if_ether.h<br>    case ETH_P_ARP:  return "ARP";<br>    case ETH_P_IPV6: return "IPv6";<br>    case ETH_P_RARP: return "RARP";<br>    default:         return "Other";<br>    }<br>}<br><br>/* IP上层协议号转可读名称 */<br>static const char *ip_proto_name(u8 proto)<br>{<br>    /* 根据协议号匹配 */<br>    switch (proto) {<br>    case IPPROTO_ICMP: return "ICMP";   // 宏定义在include/uapi/linux/in.h<br>    case IPPROTO_TCP:  return "TCP";<br>    case IPPROTO_UDP:  return "UDP";<br>    default:           return "?";<br>    }<br>}<br><br>/* ICMP类型转可读名称 */<br>static const char *icmp_type_name(u8 type)<br>{<br>    /* 根据类型匹配 */<br>    switch (type) {<br>    case ICMP_ECHO:         return "Echo-Request";  // 宏定义在include/uapi/linux/icmp.h<br>    case ICMP_ECHOREPLY:    return "Echo-Reply";<br>    case ICMP_DEST_UNREACH: return "Dest-Unreach";<br>    default:                return "Other";<br>    }<br>}<br><br>/* ARP opcode转可读名称 */<br>static const char *arp_op_name(u16 op)<br>{<br>    /* 根据操作码匹配 */<br>    switch (op) {<br>    case ARPOP_REQUEST: return "Request";  // 宏定义在include/uapi/linux/if_arp.h<br>    case ARPOP_REPLY:   return "Reply";<br>    default:            return "Other";<br>    }<br>}|

关键说明：

- 第5-10行：解析二层以太网协议，支持IPv4、ARP、IPv6、RARP解析，未知协议统一归类为Other。
    
- 第18-22行：解析IP上层传输层协议，支持ICMP、TCP、UDP协议解析。
    
- 第30-34行：解析ICMP报文类型，区分ping请求、应答、目的不可达等常见类型。
    
- 第42-45行：解析ARP操作码，区分ARP请求与应答报文类型。
    

#### 9.6.1.4. 报文字段逐行打印工具函数[¶](#id73 "永久链接至标题")

实现完整报文解析与日志打印，包含报文方向、设备名、长度概要，逐层解析以太网、ARP、IP、ICMP协议信息，逐字段打印原始字节与解码值，支持ICMP负载数据转储，仅在debug开关开启时生效。

net_lb_dump_skb函数(位于linux_driver/43_net_subsystem/net_loopback.c)[¶](#id135 "永久链接至代码")

|   |   |
|---|---|
|1<br>  2<br>  3<br>  4<br>  5<br>  6<br>  7<br>  8<br>  9<br> 10<br> 11<br> 12<br> 13<br> 14<br> 15<br> 16<br> 17<br> 18<br> 19<br> 20<br> 21<br> 22<br> 23<br> 24<br> 25<br> 26<br> 27<br> 28<br> 29<br> 30<br> 31<br> 32<br> 33<br> 34<br> 35<br> 36<br> 37<br> 38<br> 39<br> 40<br> 41<br> 42<br> 43<br> 44<br> 45<br> 46<br> 47<br> 48<br> 49<br> 50<br> 51<br> 52<br> 53<br> 54<br> 55<br> 56<br> 57<br> 58<br> 59<br> 60<br> 61<br> 62<br> 63<br> 64<br> 65<br> 66<br> 67<br> 68<br> 69<br> 70<br> 71<br> 72<br> 73<br> 74<br> 75<br> 76<br> 77<br> 78<br> 79<br> 80<br> 81<br> 82<br> 83<br> 84<br> 85<br> 86<br> 87<br> 88<br> 89<br> 90<br> 91<br> 92<br> 93<br> 94<br> 95<br> 96<br> 97<br> 98<br> 99<br>100<br>101<br>102<br>103<br>104<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119<br>120<br>121<br>122<br>123<br>124<br>125<br>126<br>127<br>128<br>129<br>130<br>131<br>132<br>133<br>134<br>135<br>136<br>137<br>138<br>139<br>140<br>141<br>142<br>143<br>144<br>145<br>146<br>147<br>148<br>149<br>150<br>151<br>152<br>153<br>154<br>155<br>156<br>157<br>158<br>159<br>160<br>161<br>162<br>163<br>164<br>165<br>166<br>167<br>168<br>169<br>170<br>171<br>172<br>173<br>174<br>175<br>176<br>177<br>178<br>179<br>180<br>181<br>182<br>183<br>184<br>185<br>186<br>187<br>188<br>189<br>190<br>191<br>192<br>193<br>194<br>195<br>196<br>197<br>198<br>199<br>200<br>201<br>202<br>203<br>204<br>205<br>206<br>207<br>208<br>209<br>210<br>211<br>212<br>213<br>214<br>215<br>216<br>217<br>218<br>219<br>220<br>221<br>222<br>223<br>224<br>225<br>226<br>227<br>228<br>229<br>230<br>231<br>232<br>233<br>234<br>235<br>236<br>237<br>238<br>239<br>240<br>241<br>242<br>243<br>244<br>245<br>246<br>247<br>248<br>249<br>250<br>251<br>252<br>253<br>254<br>255<br>256<br>257<br>258<br>259<br>260<br>261<br>262|/* 打印报文详细信息 */<br>static void net_lb_dump_skb(struct net_device *ndev,<br>                            const char *dir,<br>                            struct sk_buff *skb)<br>{<br>    /* 获取私有数据 */<br>    struct net_lb_priv *priv = netdev_priv(ndev);<br>    /* 指向以太网头 */<br>    struct ethhdr *eth = (struct ethhdr *)skb->data;<br>    /* 网络字节序转主机字节序协议号 */<br>    u16 proto = ntohs(eth->h_proto);<br>    /* 概要缓冲区：仅放标题与各协议单行摘要 */<br>    char hdr[512];<br>    /* 缓冲区已写入偏移量 */<br>    int n = 0;<br><br>    /* debug开关关闭时不打印 */<br>    if (!priv->debug)<br>        return;<br><br>    /* 标题行：方向、接口名、报文长度 */<br>    n += scnprintf(hdr + n, sizeof(hdr) - n,<br>        "\n---[%s]-- %s -- %u bytes --\n",<br>        dir, ndev->name, skb->len);<br><br>    /* 以太网层：目的MAC、源MAC、协议名称 */<br>    n += scnprintf(hdr + n, sizeof(hdr) - n,<br>        "\| ETH   dst=%pM  src=%pM  %s\n",<br>        eth->h_dest, eth->h_source, eth_proto_name(proto));<br><br>    /* ARP报文解析 */<br>    if (proto == ETH_P_ARP) {  /* 若为ARP协议 */<br>        struct arphdr *arp = (struct arphdr *)(skb->data + ETH_HLEN); /* ARP 头 */<br>        u8 *sha = (u8 *)(arp + 1);                /* 发送方MAC */<br>        __be32 *sip = (__be32 *)(sha + ETH_ALEN); /* 发送方IP */<br>        u8 *tha = (u8 *)sip + 4;                  /* 目标MAC */<br>        __be32 *tip = (__be32 *)(tha + ETH_ALEN); /* 目标IP */<br><br>        n += scnprintf(hdr + n, sizeof(hdr) - n,     /* 追加ARP层信息 */<br>            "\| ARP   %s  %pI4(%pM) --> %pI4(%pM)\n", /* 格式：操作码 IP(MAC) */<br>            arp_op_name(ntohs(arp->ar_op)),          /* ARP操作码名称 */<br>            sip, sha, tip, tha);                     /* IP和MAC参数 */<br>    }<br><br>    /* IP报文解析 */<br>    if (proto == ETH_P_IP) {  /* 若为IPv4协议 */<br>        struct iphdr *iph = (struct iphdr *)(skb->data + ETH_HLEN); /* IP头 */<br><br>        n += scnprintf(hdr + n, sizeof(hdr) - n,           /* 追加IP层信息 */<br>            "\| IP    %pI4 --> %pI4  %s  ttl=%u  len=%u\n", /* 格式：源IP 目的IP */<br>            &iph->saddr, &iph->daddr,                      /* 源/目的IP */<br>            ip_proto_name(iph->protocol),                  /* 上层协议名称 */<br>            iph->ttl, ntohs(iph->tot_len));                /* TTL和总长度 */<br><br>        /* ICMP报文解析 */<br>        if (iph->protocol == IPPROTO_ICMP) {  /* 若上层为ICMP */<br>            struct icmphdr *icmph = (struct icmphdr *)((u8 *)iph +<br>                                iph->ihl * 4); /* ICMP头位于IP头之后 */<br><br>            n += scnprintf(hdr + n, sizeof(hdr) - n,  /* 追加ICMP层信息 */<br>                "\| ICMP  %s  id=0x%04x  seq=%u\n",    /* 格式：类型名 id seq */<br>                icmp_type_name(icmph->type),          /* ICMP类型名称 */<br>                ntohs(icmph->un.echo.id),             /* ICMP标识符 */<br>                ntohs(icmph->un.echo.sequence));      /* ICMP序列号 */<br>        }<br>    }<br><br>    /* 解析标题 */<br>    n += scnprintf(hdr + n, sizeof(hdr) - n, "--- fields ---\n");<br><br>    /* 概要一次输出 */<br>    netdev_info(ndev, "%s", hdr);<br><br>    /* 以下字段行逐行printk输出，避免单次printk过长被截断 */<br><br>    /* 以太网层字段：目的MAC、源MAC、以太类型 */<br>    {<br>        /* 临时解码值缓冲 */<br>        char val[40];<br><br>        scnprintf(val, sizeof(val), "%pM", eth->h_dest);  /* 目的MAC */<br>        net_lb_field_line(0, "dst-mac", eth->h_dest, ETH_ALEN, val);<br><br>        scnprintf(val, sizeof(val), "%pM", eth->h_source); /* 源MAC */<br>        net_lb_field_line(ETH_ALEN, "src-mac",<br>                        eth->h_source, ETH_ALEN, val);<br><br>        scnprintf(val, sizeof(val), "0x%04x (%s)",  /* 以太类型 */<br>                proto, eth_proto_name(proto));<br>        net_lb_field_line(2 * ETH_ALEN, "ethertype",<br>                        (u8 *)&eth->h_proto, 2, val);<br>    }<br><br>    /* ARP报文字段解析 */<br>    if (proto == ETH_P_ARP) {<br>        /* ARP头 */<br>        struct arphdr *arp = (struct arphdr *)(skb->data + ETH_HLEN);<br>        /* 发送方/目标MAC、IP指针 */<br>        u8 *sha = (u8 *)(arp + 1);<br>        __be32 *sip = (__be32 *)(sha + ETH_ALEN);<br>        u8 *tha = (u8 *)sip + 4;<br>        __be32 *tip = (__be32 *)(tha + ETH_ALEN);<br>        /* 解码后的主机序字段值 */<br>        u16 ar_hrd = ntohs(arp->ar_hrd);<br>        u16 ar_pro = ntohs(arp->ar_pro);<br>        u16 ar_op = ntohs(arp->ar_op);<br>        /* 临时解码值缓冲 */<br>        char val[64];<br><br>        scnprintf(val, sizeof(val), "0x%04x (%s)", ar_hrd,  /* 硬件类型 */<br>                ar_hrd == ARPHRD_ETHER ? "Ethernet" : "?");<br>        net_lb_field_line(ETH_HLEN, "hrd-type",<br>                        (u8 *)&arp->ar_hrd, 2, val);<br><br>        scnprintf(val, sizeof(val), "0x%04x (%s)", ar_pro,  /* 协议类型 */<br>                ar_pro == ETH_P_IP ? "IPv4" : "?");<br>        net_lb_field_line(ETH_HLEN + 2, "pro-type",<br>                        (u8 *)&arp->ar_pro, 2, val);<br><br>        scnprintf(val, sizeof(val), "%u", arp->ar_hln);  /* 硬件地址长度 */<br>        net_lb_field_line(ETH_HLEN + 4, "hrd-len",<br>                        &arp->ar_hln, 1, val);<br><br>        scnprintf(val, sizeof(val), "%u", arp->ar_pln);  /* 协议地址长度 */<br>        net_lb_field_line(ETH_HLEN + 5, "pro-len",<br>                        &arp->ar_pln, 1, val);<br><br>        scnprintf(val, sizeof(val), "0x%04x (%s)", ar_op,  /* 操作码 */<br>                arp_op_name(ar_op));<br>        net_lb_field_line(ETH_HLEN + 6, "opcode",<br>                        (u8 *)&arp->ar_op, 2, val);<br><br>        scnprintf(val, sizeof(val), "%pM", sha);  /* 发送方MAC */<br>        net_lb_field_line(ETH_HLEN + 8, "sender-mac",<br>                        sha, ETH_ALEN, val);<br><br>        scnprintf(val, sizeof(val), "%pI4", sip);  /* 发送方IP */<br>        net_lb_field_line(ETH_HLEN + 14, "sender-ip",<br>                        (u8 *)sip, 4, val);<br><br>        scnprintf(val, sizeof(val), "%pM", tha);  /* 目标MAC */<br>        net_lb_field_line(ETH_HLEN + 18, "target-mac",<br>                        tha, ETH_ALEN, val);<br><br>        scnprintf(val, sizeof(val), "%pI4", tip);  /* 目标IP */<br>        net_lb_field_line(ETH_HLEN + 24, "target-ip",<br>                        (u8 *)tip, 4, val);<br>    }<br><br>    /* IPv4报文字段解析 */<br>    if (proto == ETH_P_IP) {<br>        /* IP头 */<br>        struct iphdr *iph = (struct iphdr *)(skb->data + ETH_HLEN);<br>        /* 临时解码值缓冲 */<br>        char val[64];<br><br>        scnprintf(val, sizeof(val), "v%u, ihl=%u (%u bytes)",  /* 版本/头长 */<br>                iph->version, iph->ihl, iph->ihl * 4);<br>        net_lb_field_line(ETH_HLEN, "ver/ihl", (u8 *)iph, 1, val);<br><br>        scnprintf(val, sizeof(val), "0x%02x", iph->tos);  /* 服务类型 */<br>        net_lb_field_line(ETH_HLEN + 1, "tos", &iph->tos, 1, val);<br><br>        scnprintf(val, sizeof(val), "%u", ntohs(iph->tot_len));  /* 总长度 */<br>        net_lb_field_line(ETH_HLEN + 2, "tot-len",<br>                        (u8 *)&iph->tot_len, 2, val);<br><br>        scnprintf(val, sizeof(val), "0x%04x", ntohs(iph->id));  /* 标识符 */<br>        net_lb_field_line(ETH_HLEN + 4, "id",<br>                        (u8 *)&iph->id, 2, val);<br><br>        scnprintf(val, sizeof(val), "flags=0x%x frag=%u",  /* 标志/分片 */<br>                ntohs(iph->frag_off) >> 13,<br>                ntohs(iph->frag_off) & 0x1fff);<br>        net_lb_field_line(ETH_HLEN + 6, "flags/frag",<br>                        (u8 *)&iph->frag_off, 2, val);<br><br>        scnprintf(val, sizeof(val), "%u", iph->ttl);  /* TTL */<br>        net_lb_field_line(ETH_HLEN + 8, "ttl", &iph->ttl, 1, val);<br><br>        scnprintf(val, sizeof(val), "0x%02x (%s)", iph->protocol,  /* 上层协议 */<br>                ip_proto_name(iph->protocol));<br>        net_lb_field_line(ETH_HLEN + 9, "protocol",<br>                        &iph->protocol, 1, val);<br><br>        scnprintf(val, sizeof(val), "0x%04x", ntohs(iph->check));  /* 头校验和 */<br>        net_lb_field_line(ETH_HLEN + 10, "checksum",<br>                        (u8 *)&iph->check, 2, val);<br><br>        scnprintf(val, sizeof(val), "%pI4", &iph->saddr);  /* 源IP */<br>        net_lb_field_line(ETH_HLEN + 12, "src-ip",<br>                        (u8 *)&iph->saddr, 4, val);<br><br>        scnprintf(val, sizeof(val), "%pI4", &iph->daddr);  /* 目的IP */<br>        net_lb_field_line(ETH_HLEN + 16, "dst-ip",<br>                        (u8 *)&iph->daddr, 4, val);<br><br>        /* ICMP报文字段解析 */<br>        if (iph->protocol == IPPROTO_ICMP) {<br>            /* ICMP头位于IP头之后 */<br>            struct icmphdr *icmph = (struct icmphdr *)((u8 *)iph +<br>                                iph->ihl * 4);<br>            /* ICMP字段起始偏移 */<br>            int icmp_off = ETH_HLEN + iph->ihl * 4;<br><br>            scnprintf(val, sizeof(val), "0x%02x (%s)", icmph->type,  /* 类型 */<br>                    icmp_type_name(icmph->type));<br>            net_lb_field_line(icmp_off, "type",<br>                            &icmph->type, 1, val);<br><br>            scnprintf(val, sizeof(val), "0x%02x", icmph->code);  /* 代码 */<br>            net_lb_field_line(icmp_off + 1, "code",<br>                            &icmph->code, 1, val);<br><br>            scnprintf(val, sizeof(val), "0x%04x",  /* 校验和 */<br>                    ntohs(icmph->checksum));<br>            net_lb_field_line(icmp_off + 2, "checksum",<br>                            (u8 *)&icmph->checksum, 2, val);<br><br>            scnprintf(val, sizeof(val), "0x%04x",  /* 标识符 */<br>                    ntohs(icmph->un.echo.id));<br>            net_lb_field_line(icmp_off + 4, "id",<br>                            (u8 *)&icmph->un.echo.id, 2, val);<br><br>            scnprintf(val, sizeof(val), "%u",  /* 序列号 */<br>                    ntohs(icmph->un.echo.sequence));<br>            net_lb_field_line(icmp_off + 6, "seq",<br>                            (u8 *)&icmph->un.echo.sequence, 2, val);<br><br>            /* ICMP负载数据：逐行转储剩余字节，最多显示64字节 */<br>            {<br>                int payload_off = icmp_off + 8;     /* 负载起始偏移 */<br>                int payload_len = skb->len - payload_off;  /* 负载总字节 */<br>                int show = min_t(int, payload_len, 64);    /* 最多64字节 */<br>                int i;<br><br>                /* 每16字节一行，逐行输出负载原始字节 */<br>                for (i = 0; i < show; i += 16) {<br>                    /* 本行字节数 */<br>                    int chunk = min_t(int, show - i, 16);<br><br>                    scnprintf(val, sizeof(val),<br>                            "(payload %d-%d/%d bytes)",<br>                            i, i + chunk, payload_len);<br>                    net_lb_field_line(payload_off + i,<br>                                    i == 0 ? "payload" : "cont",<br>                                    skb->data + payload_off + i,<br>                                    chunk, val);<br>                }<br>                /* 超过显示上限则提示总字节数 */<br>                if (payload_len > show) {<br>                    scnprintf(val, sizeof(val),<br>                            "(truncated, %d total bytes)",<br>                            payload_len);<br>                    net_lb_field_line(payload_off + show, "trunc",<br>                                    skb->data + payload_off + show,<br>                                    0, val);<br>                }<br>            }<br>        }<br>    }<br>}|

关键说明：

- 第6行：通过netdev_priv获取设备私有数据，读取debug全局调试开关状态。
    
- 第18-19行：判断debug开关，关闭时直接返回，不执行任何报文解析与日志输出。
    
- 第22-24行：打印报文头部概要，包含收发方向（TX/RX）、网卡设备名、报文总长度。
    
- 第27-29行：解析并打印以太网二层信息，包含源/目的MAC地址、二层协议类型。
    
- 第32-43行：解析ARP协议报文，提取ARP操作类型、发送方/目标IP与MAC映射关系。
    
- 第46-53行：解析IPv4三层报文，输出源目IP、上层传输协议、TTL生存时间、报文总长度。
    
- 第56-65行：针对ICMP协议解析，识别ping请求/应答类型，打印报文ID与序列号。
    
- 第77-92行：实现以太网字段打印，逐字节解析目的MAC、源MAC、二层协议类型。
    
- 第95-148行：ARP报文字段解析，逐一打印硬件类型、协议类型、地址长度、操作码、收发双方MAC/IP所有头部字段。
    
- 第151-196行：IPv4报文字段解析，打印IP版本、头长度、服务类型、总长度、分片标志、TTL、校验和、源目IP等标准头部字段。
    
- 第199-260行：ICMP报文字段解析与负载转储，解析ICMP类型、代码、校验和、ID、序列号，支持ICMP负载数据分页打印。
    

#### 9.6.1.5. NAPI异步收包轮询函数[¶](#id74 "永久链接至标题")

实现NAPI异步收包逻辑，从回环报文队列中取出翻转完成的报文，完成报文初始化、日志打印、协议绑定、校验和配置，将报文投递回内核网络栈，同时统计收发流量。

net_lb_napi_poll函数(位于linux_driver/43_net_subsystem/net_loopback.c)[¶](#id136 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48<br>49<br>50<br>51<br>52<br>53<br>54|/* NAPI轮询函数：从回环队列取出报文，回送网络栈 */<br>static int net_lb_napi_poll(struct napi_struct *napi, int budget)<br>{<br>    /* 取私有数据 */<br>    struct net_lb_priv *priv = container_of(napi, struct net_lb_priv, napi);<br>    /* 待回送的报文指针 */<br>    struct sk_buff *skb;<br>    /* 报文长度 */<br>    unsigned int pkt_len;<br>    /* 已处理报文计数 */<br>    int work_done = 0;<br><br>    /* 循环处理回环队列 */<br>    while (work_done < budget) {                /* 未达预算时继续处理 */<br>        spin_lock(&priv->lb_lock);              /* 加锁保护队列操作 */<br>        skb = __skb_dequeue(&priv->lb_queue);   /* 从队列头部取出一个skb */<br>        spin_unlock(&priv->lb_lock);            /* 解锁 */<br><br>        /* 取出为空，退出循环 */<br>        if (!skb)<br>            break;<br><br>        /* 设置报文关联到本网络设备 */<br>        skb->dev = priv->ndev;<br><br>        /* 打印RX报文详情 */<br>        net_lb_dump_skb(priv->ndev, "RX", skb);<br><br>        /* 解析以太网协议类型，设置skb->protocol和pkt_type */<br>        skb->protocol = eth_type_trans(skb, priv->ndev);<br>        /* 重置校验和，标记无需硬件校验 */<br>        skb->ip_summed = CHECKSUM_UNNECESSARY;<br><br>        /* 保存长度到局部变量 */<br>        pkt_len = skb->len;<br><br>        /* 回送报文到网络协议栈，模拟硬件接收，此后skb由协议栈释放 */<br>        netif_receive_skb(skb);<br><br>        /* 更新接收统计 */<br>        priv->stats.rx_packets++;        /* 接收包数+1 */<br>        priv->stats.rx_bytes += pkt_len; /* 接收字节累加 */<br>        work_done++;                     /* 已处理数+1 */<br>    }<br><br>    /* 若处理完毕且队列已空，结束NAPI轮询 */<br>    if (work_done < budget) {<br>        /* 完成NAPI并报告处理量 */<br>        napi_complete_done(napi, work_done);<br>    }<br><br>    /* 返回实际处理的报文数 */<br>    return work_done;<br>}|

关键说明：

- 第14行：循环处理报文，单次处理数量不超过NAPI_BUDGET预算。
    
- 第15-17行：加锁后从队列取出报文，保证队列操作并发安全。
    
- 第20-21行：队列为空时直接退出循环，避免无效轮询。
    
- 第24行：绑定报文所属网卡设备，保证内核网络栈识别报文来源设备。
    
- 第30行：解析二层协议类型，初始化skb协议字段，为上层协议解析提供依据。
    
- 第32行：标记报文校验和无需硬件校验，虚拟报文已完成软件校验。
    
- 第38行：调用netif_receive_skb将报文投递回内核网络栈，模拟硬件收包流程。
    
- 第41-43行：更新网卡接收流量统计数据。
    
- 第47-50行：队列处理完毕后结束NAPI轮询，释放CPU资源。
    
- 第53行：返回本次轮询实际处理报文数，供内核调度参考。
    

#### 9.6.1.6. 设备启停回调函数[¶](#id75 "永久链接至标题")

实现网卡设备打开、关闭回调，对应系统ifconfig/ip link命令启停设备操作，负责NAPI启用/禁用、载波状态切换、报文队列清空、设备状态初始化与回收。

设备启停回调函数(位于linux_driver/43_net_subsystem/net_loopback.c)[¶](#id137 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40|/* 打开网络设备：ifconfig up/ip link set up时调用 */<br>static int net_lb_ndo_open(struct net_device *ndev)<br>{<br>    /* 获取私有数据 */<br>    struct net_lb_priv *priv = netdev_priv(ndev);<br><br>    /* 启用NAPI轮询 */<br>    napi_enable(&priv->napi);<br>    /* 开启载波 */<br>    netif_carrier_on(ndev);<br>    /* 启动发送队列 */<br>    netif_start_queue(ndev);<br><br>    /* 打印打开信息 */<br>    netdev_info(ndev, "虚拟回环网卡已打开\n");<br><br>    return 0;<br>}<br><br>/* 关闭网络设备：ifconfig down/ip link set down时调用 */<br>static int net_lb_ndo_stop(struct net_device *ndev)<br>{<br>    /* 获取私有数据 */<br>    struct net_lb_priv *priv = netdev_priv(ndev);<br><br>    /* 停止发送队列 */<br>    netif_stop_queue(ndev);<br>    /* 关闭载波 */<br>    netif_carrier_off(ndev);<br>    /* 禁用NAPI */<br>    napi_disable(&priv->napi);<br><br>    /* 清空回环队列中残留报文 */<br>    skb_queue_purge(&priv->lb_queue);<br><br>    /* 打印关闭信息 */<br>    netdev_info(ndev, "虚拟回环网卡已关闭\n");<br><br>    return 0;<br>}|

关键说明：

- 第8行：启用NAPI异步收包机制，设备上线后开启报文处理能力。
    
- 第10行：开启网卡载波状态，告知内核设备链路正常。
    
- 第12行：启动网卡发送队列，允许内核下发TX报文。
    
- 第27行：停止发送队列，禁止新的报文下发。
    
- 第29行：关闭载波，标记设备链路断开。
    
- 第31行：禁用NAPI，停止异步收包轮询。
    
- 第34行：清空队列残留报文，防止设备关闭后内存泄漏、脏数据残留。
    

#### 9.6.1.7. 报文发送回调函数[¶](#id76 "永久链接至标题")

网卡发送核心回调，内核下发的所有报文都会进入该函数，完成发送日志打印、流量统计、报文翻转、队列入队、NAPI调度，实现TX报文转RX回环。

net_lb_ndo_start_xmit函数(位于linux_driver/43_net_subsystem/net_loopback.c)[¶](#id138 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38|/* 发送报文：网络栈下发数据包时调用，实现回环 */<br>static netdev_tx_t net_lb_ndo_start_xmit(struct sk_buff *skb,<br>                                        struct net_device *ndev)<br>{<br>    /* 获取私有数据 */<br>    struct net_lb_priv *priv = netdev_priv(ndev);<br>    /* 回送用的转换报文 */<br>    struct sk_buff *nskb;<br><br>    /* debug模式下打印发送报文详情 */<br>    net_lb_dump_skb(ndev, "TX", skb);<br><br>    /* 更新发送统计 */<br>    priv->stats.tx_packets++;         /* 发送包数 +1 */<br>    priv->stats.tx_bytes += skb->len; /* 发送字节累加 */<br><br>    /* 将TX报文翻转为对端应答用于回送 */<br>    nskb = net_lb_transform(priv, skb);<br>    /* 释放原始发送skb */<br>    dev_kfree_skb(skb);<br><br>    /* 转换失败则直接返回 */<br>    if (!nskb) {<br>        priv->stats.tx_dropped++;   /* 丢包计数+1 */<br>        return NETDEV_TX_OK;        /* 返回发送成功 */<br>    }<br><br>    /* 将回送报文入队 */<br>    spin_lock(&priv->lb_lock);               /* 加锁保护队列 */<br>    __skb_queue_tail(&priv->lb_queue, nskb); /* 回送包加入队列尾部 */<br>    spin_unlock(&priv->lb_lock);             /* 解锁 */<br><br>    /* 调度NAPI轮询，触发回送收包 */<br>    napi_schedule(&priv->napi);<br><br>    /* 返回发送成功 */<br>    return NETDEV_TX_OK;<br>}|

关键说明：

- 第11行：打印TX方向报文日志，记录内核下发的原始报文数据。
    
- 第14-15行：更新网卡发送流量统计，记录发包数与字节数。
    
- 第18行：调用核心翻转函数，生成反向应答报文。
    
- 第20行：释放原始skb，避免内存泄漏，原始报文无需继续使用。
    
- 第23-26行：报文翻转失败时统计丢包，返回发送成功，避免内核报错。
    
- 第29-31行：加锁将翻转后的报文加入回环队列，保证队列安全。
    
- 第34行：调度NAPI轮询，触发异步收包流程，完成报文回环。
    
- 第37行：返回TX成功状态，告知内核报文发送处理完成。
    

#### 9.6.1.8. 设备配置与统计回调函数[¶](#id77 "永久链接至标题")

实现网卡MAC地址设置、网络统计信息获取回调，适配内核标准网络设备接口，支持用户修改网卡MAC、查看设备流量统计数据。

设备配置与统计回调函数(位于linux_driver/43_net_subsystem/net_loopback.c)[¶](#id139 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26|/* 获取网络统计信息 */<br>static struct net_device_stats *net_lb_ndo_get_stats(struct net_device *ndev)<br>{<br>    /* 获取私有数据 */<br>    struct net_lb_priv *priv = netdev_priv(ndev);<br><br>    /* 返回统计结构指针 */<br>    return &priv->stats;<br>}<br><br>/* 设置MAC地址 */<br>static int net_lb_ndo_set_mac_address(struct net_device *ndev, void *addr)<br>{<br>    /* 调用通用以太网MAC设置函数，内部完成校验与dev_addr_set */<br>    return eth_mac_addr(ndev, addr);<br>}<br><br>/* net_device_ops操作集 */<br>static const struct net_device_ops net_lb_ops = {<br>    .ndo_open               = net_lb_ndo_open,            /* 打开设备回调 */<br>    .ndo_stop               = net_lb_ndo_stop,            /* 关闭设备回调 */<br>    .ndo_start_xmit         = net_lb_ndo_start_xmit,      /* 发送报文回调 */<br>    .ndo_get_stats          = net_lb_ndo_get_stats,       /* 获取统计回调 */<br>    .ndo_set_mac_address    = net_lb_ndo_set_mac_address, /* 设置MAC回调 */<br>    .ndo_validate_addr      = eth_validate_addr,          /* 校验MAC回调，使用内核通用函数 */<br>};|

关键说明：

- 第8行：返回私有数据中的统计结构体，供内核读取收发、丢包统计数据。
    
- 第15行：调用内核通用以太网MAC设置函数，自带MAC合法性校验，无需自定义。
    
- 第19-26行：绑定所有网卡核心操作回调，完成设备操作接口注册。
    

#### 9.6.1.10. sysfs调试开关[¶](#sysfs "永久链接至标题")

基于sysfs文件系统实现用户态debug调试开关，用户可通过读写/sys文件节点，动态开启/关闭报文详细日志打印，无需重新编译驱动。

sysfs调试开关(位于linux_driver/43_net_subsystem/net_loopback.c)[¶](#id141 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48<br>49<br>50<br>51<br>52<br>53|/* sysfs属性：显示debug开关状态 */<br>static ssize_t debug_show(struct device *dev,<br>                        struct device_attribute *attr, char *buf)<br>{<br>    /* 从device取net_device */<br>    struct net_device *ndev = to_net_dev(dev);<br>    /* 获取私有数据 */<br>    struct net_lb_priv *priv = netdev_priv(ndev);<br><br>    /* 输出0=关 1=开 */<br>    return sprintf(buf, "%d\n", priv->debug ? 1 : 0);<br>}<br><br>/* sysfs属性：设置debug开关 */<br>static ssize_t debug_store(struct device *dev,<br>                        struct device_attribute *attr,<br>                        const char *buf, size_t count)<br>{<br>    /* 从device取net_device */<br>    struct net_device *ndev = to_net_dev(dev);<br>    /* 获取私有数据 */<br>    struct net_lb_priv *priv = netdev_priv(ndev);<br>    /* 解析后的数值 */<br>    unsigned long val;<br><br>    /* 将字符串解析为无符号长整型 */<br>    if (kstrtoul(buf, 0, &val))<br>        return -EINVAL;<br><br>    /* 非0即开启，0为关闭 */<br>    priv->debug = val ? true : false;<br><br>    /* 打印状态 */<br>    netdev_info(ndev, "报文详细打印: %s\n", priv->debug ? "开启" : "关闭");<br><br>    /* 返回已写入字节数 */<br>    return count;<br>}<br><br>/* 读写属性宏 */<br>static DEVICE_ATTR_RW(debug);<br><br>/* sysfs属性指针数组 */<br>static struct attribute *net_lb_attrs[] = {<br>    &dev_attr_debug.attr,     /* debug开关属性 */<br>    NULL,<br>};<br><br>/* sysfs属性组 */<br>static const struct attribute_group net_lb_attr_group = {<br>    .name = "loopback",        /* 属性组目录名 */<br>    .attrs = net_lb_attrs,     /* 属性指针数组 */<br>};|

关键说明：

- 第11行：读取设备私有数据中的debug状态，格式化输出到用户态sysfs文件。
    
- 第27-37行：解析用户态写入的字符串数据，转换为内核数值类型，仅0、1可生效，非法输入直接忽略。
    
- 第41行：通过DEVICE_ATTR宏创建sysfs属性文件，配置0644权限。
    

#### 9.6.1.11. 设备初始化与资源初始化函数[¶](#id78 "永久链接至标题")

基于内核通用以太网初始化接口完成虚拟网卡基础配置，统一初始化设备私有资源、并发锁、报文队列、NAPI异步机制、设备回调接口与硬件特性参数，为设备注册上线完成资源初始化。

net_lb_netdev_setup函数(位于linux_driver/43_net_subsystem/net_loopback.c)[¶](#id142 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38|/* 网络设备初始化 */<br>static void net_lb_netdev_setup(struct net_device *ndev)<br>{<br>    /* 获取私有数据指针 */<br>    struct net_lb_priv *priv = netdev_priv(ndev);<br><br>    /* 初始化以太网标准字段 */<br>    ether_setup(ndev);<br><br>    /* 保存网络设备指针到私有数据 */<br>    priv->ndev = ndev;<br><br>    /* 初始化回环队列自旋锁 */<br>    spin_lock_init(&priv->lb_lock);<br>    /* 初始化回环skb队列 */<br>    skb_queue_head_init(&priv->lb_queue);<br><br>    /* 绑定net_device操作回调 */<br>    ndev->netdev_ops = &net_lb_ops;<br>    /* 绑定ethtool操作回调 */<br>    ndev->ethtool_ops = &net_lb_ethtool_ops;<br><br>    /* 设置设备特性 */<br>    ndev->features = 0;    /* 无硬件特性 */<br>    ndev->hw_features = 0; /* 无可切换硬件特性 */<br><br>    /* 设置MTU */<br>    ndev->mtu = ETH_DATA_LEN;  /* 标准以太网MTU 1500字节 */<br><br>    /* 设置需要的最小头空间 */<br>    ndev->needed_headroom = NET_IP_ALIGN;  /* 2字节对齐头空间 */<br><br>    /* 生成随机MAC地址 */<br>    eth_hw_addr_random(ndev);<br><br>    /* 初始化NAPI */<br>    netif_napi_add(ndev, &priv->napi, net_lb_napi_poll);<br>}|

关键说明：

- 第8行：调用内核标准ether_setup接口，批量初始化以太网设备基础字段，避免手动配置冗余参数。
    
- 第14行：初始化队列自旋锁，保障多线程并发下报文队列操作安全。
    
- 第16行：skb报文队列，构建空的回环报文缓冲队列。
    
- 第19-21行：绑定网络设备核心操作回调集与ethtool工具回调接口，完成设备功能接口注册。
    
- 第24-25行：清零设备硬件特性与可切换硬件特性，明确当前纯软件虚拟网卡无任何硬件卸载能力。
    
- 第28行：采用内核标准宏ETH_DATA_LEN配置MTU（1500字节）。
    
- 第31行：设置报文头部最小预留空间为NET_IP_ALIGN（2字节），满足内核IP报文内存对齐要求。
    
- 第34行：调用内核标准eth_hw_addr_random接口生成随机合法以太网MAC地址。
    
- 第37行：注册NAPI轮询回调函数，初始化异步收包机制，依托NAPI框架实现高效报文轮询处理，替代中断轮询模式。
    

#### 9.6.1.12. 模块初始化入口函数[¶](#id79 "永久链接至标题")

采用通用alloc_netdev动态创建自定义命名虚拟网卡，依次完成网卡分配、内核注册、sysfs属性组创建，实现设备上线。

net_lb_init函数(位于linux_driver/43_net_subsystem/net_loopback.c)[¶](#id143 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44|/* 模块加载函数 */<br>static int __init net_lb_init(void)<br>{<br>    /* 返回值 */<br>    int ret;<br><br>    /* 打印加载信息 */<br>    pr_info("虚拟回环网卡加载\n");<br><br>    /* 分配网络设备，命名为lbnetX */<br>    lb_ndev = alloc_netdev(sizeof(struct net_lb_priv), "lbnet%d",<br>                        NET_NAME_UNKNOWN, net_lb_netdev_setup);<br>    if (!lb_ndev) {<br>        pr_err("alloc_netdev 失败\n");<br>        return -ENOMEM;<br>    }<br><br>    /* 注册网络设备到内核 */<br>    ret = register_netdev(lb_ndev);<br>    if (ret) {<br>        pr_err("register_netdev 失败: %d\n", ret);<br>        goto err_free_netdev;<br>    }<br><br>    /* 创建sysfs属性组，在/sys/class/net/<dev>/loopback/下 */<br>    ret = sysfs_create_group(&lb_ndev->dev.kobj, &net_lb_attr_group);<br>    if (ret) {<br>        pr_err("sysfs 属性组创建失败: %d\n", ret);<br>        goto err_unregister_netdev;<br>    }<br><br>    return 0;<br><br>err_unregister_netdev:<br>    /* 注销已注册的设备 */<br>    unregister_netdev(lb_ndev);<br>err_free_netdev:<br>    /* 释放设备内存 */<br>    free_netdev(lb_ndev);<br>    /* 置空指针 */<br>    lb_ndev = NULL;<br>    /* 返回错误码 */<br>    return ret;<br>}|

关键说明：

- 第11-16行：调用内核通用alloc_netdev创建网络设备，设备名称自动生成lbnet0、lbnet1格式，同时绑定私有数据内存大小与net_lb_netdev_setup设备初始化回调，设备创建即完成基础参数初始化。
    
- 第19-23行：将初始化完成的虚拟网卡注册到内核网络子系统，成功后系统可识别lbnetX设备。
    
- 第26-30行：创建独立sysfs属性组，统一挂载在/sys/class/net/<设备名>/loopback/目录下。
    

#### 9.6.1.13. 模块注销退出函数[¶](#id80 "永久链接至标题")

针对初始化阶段创建的sysfs属性组、网络设备、NAPI机制、设备内存进行逐一释放，避免驱动卸载后的内核资源残留与内存泄漏问题。

net_lb_exit函数(位于linux_driver/43_net_subsystem/net_loopback.c)[¶](#id144 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21|/* 模块卸载函数 */<br>static void __exit net_lb_exit(void)<br>{<br>    /* 获取私有数据 */<br>    struct net_lb_priv *priv = netdev_priv(lb_ndev);<br><br>    /* 打印卸载信息 */<br>    pr_info("虚拟回环网卡卸载\n");<br><br>    /* 移除sysfs属性组 */<br>    sysfs_remove_group(&lb_ndev->dev.kobj, &net_lb_attr_group);<br><br>    /* 注销网络设备 */<br>    unregister_netdev(lb_ndev);<br><br>    /* 移除NAPI */<br>    netif_napi_del(&priv->napi);<br><br>    /* 释放网络设备 */<br>    free_netdev(lb_ndev);<br>}|

关键说明：

- 第11行：释放sysfs文件系统资源，避免用户态文件节点残留。
    
- 第14行：调用内核标准接口注销虚拟网络设备，从内核网络子系统中移除lbnetX设备。
    
- 第17行：删除设备NAPI异步处理结构体，彻底注销NAPI轮询机制，释放报文异步处理相关资源。
    
- 第20行：释放网络设备内存，包含设备本身内存与私有数据内存，彻底回收所有驱动占用资源。
    

### 9.6.2. Makefile说明[¶](#makefile "永久链接至标题")

本节实验使用的Makefile如下所示，编写该Makefile时，只需要根据实际情况修改变量KERNEL_DIR、CROSS_COMPILE和obj-m即可。

Makefile(位于linux_driver/43_net_subsystem/Makefile)[¶](#id145 "永久链接至代码")

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31|#指定内核路径,可以是相对路径或绝对路径<br>KERNEL_DIR=../../kernel/<br># KERNEL_DIR=/home/guest/LubanCat_Linux_Generic_Full_SDK/kernel-6.1<br># KERNEL_DIR=/home/guest/LubanCat_Linux_rk3588_SDK/kernel<br><br>#指定目标架构为arm64<br>ARCH=arm64<br><br>#指定交叉编译工具链的前缀<br>CROSS_COMPILE=aarch64-linux-gnu-<br># CROSS_COMPILE=/home/guest/LubanCat_Linux_Generic_Full_SDK/prebuilts/gcc/linux-x86/aarch64/gcc-arm-10.3-2021.07-x86_64-aarch64-none-linux-gnu/bin/aarch64-none-linux-gnu-<br><br>#导出为环境变量<br>export  ARCH  CROSS_COMPILE<br><br>#指定要编译的内核模块目标文件<br>obj-m := net_loopback.o<br><br>#all :默认目标，执行时会编译驱动模块<br>#$(MAKE) ：调用make工具<br>#-C $(KERNEL_DIR) ：指定的内核源码目录<br>#M=$(CURDIR) ：模块的源码位于当前目录<br>#modules ：编译模块<br>all:<br>    $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) modules<br><br>.PHONE:clean<br><br>#清理编译生成的文件<br>clean:<br>    $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) clean|

### 9.6.3. 编译驱动[¶](#id81 "永久链接至标题")

在实验目录下输入 `make` 即可编译驱动，编译得到内核模块net_loopback.ko。

### 9.6.4. 程序运行结果[¶](#id82 "永久链接至标题")

如出现 `Permission denied` 或类似字样，请注意用户权限，大部分操作硬件外设的功能，几乎都需要root用户权限，简单的解决方案是在执行语句前加入sudo或以root用户运行程序。

#### 9.6.4.1. 实验操作[¶](#id83 "永久链接至标题")

使用以下命令加载驱动：

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17|# 加载驱动<br>sudo insmod net_loopback.ko<br><br># 信息输出如下<br>[  158.054235] 虚拟回环网卡加载<br>[  158.283334] lbnet0: 虚拟回环网卡已打开<br><br># 查看lbnet0网卡<br>ifconfig lbnet0<br><br># 信息输出如下<br>lbnet0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500<br>    ether ae:4c:58:a4:f1:82  txqueuelen 1000  (Ethernet)<br>    RX packets 0  bytes 0 (0.0 B)<br>    RX errors 0  dropped 0  overruns 0  frame 0<br>    TX packets 0  bytes 0 (0.0 B)<br>    TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0|

可以看到虚拟网卡成功注册，设备名字为lbnet0，网卡状态<UP,BROADCAST,RUNNING,MULTICAST>分别为已启用、支持广播、载波正常、支持多播，mtu 1500和驱动配置一致，MAC地址ae:4c:58:a4:f1:82是随机生成的，每次加载模块可能不同。 因为尚未设置ip和数据收发，所以收发数据包统计都是0。

设置ip并进行ping测试：

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48<br>49<br>50<br>51<br>52<br>53<br>54<br>55<br>56<br>57|# 禁用NetworkManager对虚拟网卡控制<br>sudo nmcli device set lbnet0 managed no<br><br># 手动配置lbnet0虚拟网卡ip和掩码<br>sudo ip addr add 10.0.0.1/24 dev lbnet0<br><br># 查看lbnet0网卡<br>ifconfig lbnet0<br><br># 信息输出如下<br>lbnet0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500<br>    inet 10.0.0.1  netmask 255.255.255.0  broadcast 0.0.0.0<br>    ether ae:4c:58:a4:f1:82  txqueuelen 1000  (Ethernet)<br>    RX packets 0  bytes 0 (0.0 B)<br>    RX errors 0  dropped 0  overruns 0  frame 0<br>    TX packets 0  bytes 0 (0.0 B)<br>    TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0<br><br># 查看网关信息<br>route -n<br><br># 信息输出如下<br>Kernel IP routing table<br>Destination     Gateway         Genmask         Flags Metric Ref    Use Iface<br>10.0.0.0        0.0.0.0         255.255.255.0   U     0      0        0 lbnet0<br><br># ping命令测试，ping 10次<br>ping 10.0.0.2 -c 10<br><br># 信息输出如下<br>PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.<br>64 bytes from 10.0.0.2: icmp_seq=1 ttl=64 time=0.184 ms<br>64 bytes from 10.0.0.2: icmp_seq=2 ttl=64 time=0.203 ms<br>64 bytes from 10.0.0.2: icmp_seq=3 ttl=64 time=0.149 ms<br>64 bytes from 10.0.0.2: icmp_seq=4 ttl=64 time=0.202 ms<br>64 bytes from 10.0.0.2: icmp_seq=5 ttl=64 time=0.205 ms<br>64 bytes from 10.0.0.2: icmp_seq=6 ttl=64 time=0.210 ms<br>64 bytes from 10.0.0.2: icmp_seq=7 ttl=64 time=0.212 ms<br>64 bytes from 10.0.0.2: icmp_seq=8 ttl=64 time=0.144 ms<br>64 bytes from 10.0.0.2: icmp_seq=9 ttl=64 time=0.214 ms<br>64 bytes from 10.0.0.2: icmp_seq=10 ttl=64 time=0.201 ms<br><br>--- 10.0.0.2 ping statistics ---<br>10 packets transmitted, 10 received, 0% packet loss, time 9016ms<br>rtt min/avg/max/mdev = 0.144/0.192/0.214/0.024 ms<br><br># 查看lbnet0网卡<br>ifconfig lbnet0<br><br># 信息输出如下<br>lbnet0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500<br>        inet 10.0.0.1  netmask 255.255.255.0  broadcast 0.0.0.0<br>        ether ae:4c:58:a4:f1:82  txqueuelen 1000  (Ethernet)<br>        RX packets 11  bytes 868 (868.0 B)<br>        RX errors 0  dropped 0  overruns 0  frame 0<br>        TX packets 11  bytes 1022 (1022.0 B)<br>        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0|

设置ip地址和掩码后通过ifconfig和route命令可以看到ip、网关和掩码设置成功。使用ping命令向10.0.0.2发10个包，可以看到全部包发送成功。 由于ping 10.0.0.2时，协议栈在发送第一个ICMP请求之前，必须先知道10.0.0.2的MAC地址。因为此时内核的ARP/邻居表中没有10.0.0.2的记录，协议栈会先发出一个ARP请求，虚拟回环驱动将其翻转为ARP应答回送，因此ping 10次收发统计为11次（1 ARP + 10 ICMP）。

开启debug接口查看报文详细信息：

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48<br>49<br>50<br>51<br>52<br>53<br>54<br>55<br>56<br>57<br>58<br>59<br>60<br>61<br>62<br>63<br>64<br>65<br>66<br>67<br>68<br>69<br>70<br>71<br>72<br>73<br>74<br>75<br>76<br>77<br>78<br>79<br>80<br>81<br>82<br>83<br>84<br>85<br>86<br>87<br>88<br>89<br>90<br>91<br>92<br>93<br>94<br>95<br>96<br>97<br>98|# 开启debug信息打印<br>sudo sh -c "echo 1 > /sys/class/net/lbnet0/loopback/debug"<br><br># ping命令测试，ping 1次<br>ping 10.0.0.2 -c 1<br><br># 信息输出如下<br>[ 2118.226279] lbnet0: 报文详细打印: 开启<br>[ 2125.248503] lbnet0:<br>[ 2125.248503] ---[TX]-- lbnet0 -- 98 bytes --<br>[ 2125.248503] \| ETH   dst=00:00:00:00:00:00  src=ae:4c:58:a4:f1:82  IPv4<br>[ 2125.248503] \| IP    10.0.0.1 --> 10.0.0.2  ICMP  ttl=64  len=84<br>[ 2125.248503] \| ICMP  Echo-Request  id=0x332c  seq=1<br>[ 2125.248503] --- fields ---<br>[ 2125.248588]   0000  dst-mac      00 00 00 00 00 00        00:00:00:00:00:00<br>[ 2125.248603]   0006  src-mac      ae 4c 58 a4 f1 82        ae:4c:58:a4:f1:82<br>[ 2125.248614]   000c  ethertype    08 00                    0x0800 (IPv4)<br>[ 2125.248626]   000e  ver/ihl      45                       v4, ihl=5 (20 bytes)<br>[ 2125.248637]   000f  tos          00                       0x00<br>[ 2125.248647]   0010  tot-len      00 54                    84<br>[ 2125.248657]   0012  id           3e f0                    0x3ef0<br>[ 2125.248666]   0014  flags/frag   40 00                    flags=0x2 frag=0<br>[ 2125.248676]   0016  ttl          40                       64<br>[ 2125.248686]   0017  protocol     01                       0x01 (ICMP)<br>[ 2125.248695]   0018  checksum     e7 b6                    0xe7b6<br>[ 2125.248706]   001a  src-ip       0a 00 00 01              10.0.0.1<br>[ 2125.248716]   001e  dst-ip       0a 00 00 02              10.0.0.2<br>[ 2125.248726]   0022  type         08                       0x08 (Echo-Request)<br>[ 2125.248736]   0023  code         00                       0x00<br>[ 2125.248746]   0024  checksum     52 e6                    0x52e6<br>[ 2125.248755]   0026  id           33 2c                    0x332c<br>[ 2125.248765]   0028  seq          00 01                    1<br>[ 2125.248778]   002a  payload      7f 5d 8d 6a 00 00 00 00 a4 51 02 00 00 00 00 00 (payload 0-16/56 bytes)<br>[ 2125.248793]   003a  cont         10 11 12 13 14 15 16 17 18 19 1a 1b 1c 1d 1e 1f (payload 16-32/56 bytes)<br>[ 2125.248808]   004a  cont         20 21 22 23 24 25 26 27 28 29 2a 2b 2c 2d 2e 2f (payload 32-48/56 bytes)<br>[ 2125.248820]   005a  cont         30 31 32 33 34 35 36 37  (payload 48-56/56 bytes)<br>[ 2125.248854] lbnet0:<br>[ 2125.248854] ---[RX]-- lbnet0 -- 98 bytes --<br>[ 2125.248854] \| ETH   dst=ae:4c:58:a4:f1:82  src=00:00:00:00:00:00  IPv4<br>[ 2125.248854] \| IP    10.0.0.2 --> 10.0.0.1  ICMP  ttl=64  len=84<br>[ 2125.248854] \| ICMP  Echo-Reply  id=0x332c  seq=1<br>[ 2125.248854] --- fields ---<br>[ 2125.248869]   0000  dst-mac      ae 4c 58 a4 f1 82        ae:4c:58:a4:f1:82<br>[ 2125.248882]   0006  src-mac      00 00 00 00 00 00        00:00:00:00:00:00<br>[ 2125.248893]   000c  ethertype    08 00                    0x0800 (IPv4)<br>[ 2125.248903]   000e  ver/ihl      45                       v4, ihl=5 (20 bytes)<br>[ 2125.248913]   000f  tos          00                       0x00<br>[ 2125.248922]   0010  tot-len      00 54                    84<br>[ 2125.248931]   0012  id           3e f0                    0x3ef0<br>[ 2125.248941]   0014  flags/frag   40 00                    flags=0x2 frag=0<br>[ 2125.248951]   0016  ttl          40                       64<br>[ 2125.248960]   0017  protocol     01                       0x01 (ICMP)<br>[ 2125.248970]   0018  checksum     e7 b6                    0xe7b6<br>[ 2125.248980]   001a  src-ip       0a 00 00 02              10.0.0.2<br>[ 2125.248990]   001e  dst-ip       0a 00 00 01              10.0.0.1<br>[ 2125.249000]   0022  type         00                       0x00 (Echo-Reply)<br>[ 2125.249009]   0023  code         00                       0x00<br>[ 2125.249019]   0024  checksum     5a e6                    0x5ae6<br>[ 2125.249028]   0026  id           33 2c                    0x332c<br>[ 2125.249037]   0028  seq          00 01                    1<br>[ 2125.249050]   002a  payload      7f 5d 8d 6a 00 00 00 00 a4 51 02 00 00 00 00 00 (payload 0-16/56 bytes)<br>[ 2125.249065]   003a  cont         10 11 12 13 14 15 16 17 18 19 1a 1b 1c 1d 1e 1f (payload 16-32/56 bytes)<br>[ 2125.249079]   004a  cont         20 21 22 23 24 25 26 27 28 29 2a 2b 2c 2d 2e 2f (payload 32-48/56 bytes)<br>[ 2125.249092]   005a  cont         30 31 32 33 34 35 36 37  (payload 48-56/56 bytes)<br>[ 2130.283465] lbnet0:<br>[ 2130.283465] ---[TX]-- lbnet0 -- 42 bytes --<br>[ 2130.283465] \| ETH   dst=00:00:00:00:00:00  src=ae:4c:58:a4:f1:82  ARP<br>[ 2130.283465] \| ARP   Request  10.0.0.1(ae:4c:58:a4:f1:82) --> 10.0.0.2(00:00:00:00:00:00)<br>[ 2130.283465] --- fields ---<br>[ 2130.283673]   0000  dst-mac      00 00 00 00 00 00        00:00:00:00:00:00<br>[ 2130.283749]   0006  src-mac      ae 4c 58 a4 f1 82        ae:4c:58:a4:f1:82<br>[ 2130.283811]   000c  ethertype    08 06                    0x0806 (ARP)<br>[ 2130.283873]   000e  hrd-type     00 01                    0x0001 (Ethernet)<br>[ 2130.283933]   0010  pro-type     08 00                    0x0800 (IPv4)<br>[ 2130.283988]   0012  hrd-len      06                       6<br>[ 2130.284041]   0013  pro-len      04                       4<br>[ 2130.284099]   0014  opcode       00 01                    0x0001 (Request)<br>[ 2130.284160]   0016  sender-mac   ae 4c 58 a4 f1 82        ae:4c:58:a4:f1:82<br>[ 2130.284221]   001c  sender-ip    0a 00 00 01              10.0.0.1<br>[ 2130.284281]   0020  target-mac   00 00 00 00 00 00        00:00:00:00:00:00<br>[ 2130.284342]   0026  target-ip    0a 00 00 02              10.0.0.2<br>[ 2130.286467] lbnet0:<br>[ 2130.286467] ---[RX]-- lbnet0 -- 42 bytes --<br>[ 2130.286467] \| ETH   dst=ae:4c:58:a4:f1:82  src=00:00:00:00:00:00  ARP<br>[ 2130.286467] \| ARP   Reply  10.0.0.2(00:00:00:00:00:00) --> 10.0.0.1(ae:4c:58:a4:f1:82)<br>[ 2130.286467] --- fields ---<br>[ 2130.286649]   0000  dst-mac      ae 4c 58 a4 f1 82        ae:4c:58:a4:f1:82<br>[ 2130.286707]   0006  src-mac      00 00 00 00 00 00        00:00:00:00:00:00<br>[ 2130.286755]   000c  ethertype    08 06                    0x0806 (ARP)<br>[ 2130.286800]   000e  hrd-type     00 01                    0x0001 (Ethernet)<br>[ 2130.286845]   0010  pro-type     08 00                    0x0800 (IPv4)<br>[ 2130.286886]   0012  hrd-len      06                       6<br>[ 2130.286927]   0013  pro-len      04                       4<br>[ 2130.286969]   0014  opcode       00 02                    0x0002 (Reply)<br>[ 2130.287017]   0016  sender-mac   00 00 00 00 00 00        00:00:00:00:00:00<br>[ 2130.287062]   001c  sender-ip    0a 00 00 02              10.0.0.2<br>[ 2130.287110]   0020  target-mac   ae 4c 58 a4 f1 82        ae:4c:58:a4:f1:82<br>[ 2130.287155]   0026  target-ip    0a 00 00 01              10.0.0.1|

开启debug开关后，执行ping 10.0.0.2 -c 1命令，内核日志中依次打印了四组报文信息，分别对应一次ICMP收发和一次ARP收发的翻转过程。

**ICMP部分：**

发送方向（TX）的报文总长98字节，其中以太网头14字节、IP头20字节、ICMP头8字节、ICMP负载56字节。

以太网层中，源MAC为虚拟网卡的随机地址ae:4c:58:a4:f1:82，目的MAC为全零（因为10.0.0.2在本地不存在对应的真实邻居表项，协议栈无法填充有效的目的MAC），以太类型为0x0800表示是IPv4报文。

IP层中，源地址为10.0.0.1，目的地址为10.0.0.2，TTL为64，协议字段为0x01即ICMP，IP头校验和为0xe7b6。

ICMP层中，类型为0x08即Echo-Request，代码为0，校验和为0x52e6，标识符为0x332c，序列号为1，负载的56字节由时间戳和递增填充数据组成。

该报文经net_lb_transform()翻转后，在接收方向（RX）以回送包的形式重新进入协议栈：以太网层的源和目的MAC发生互换，IP层的源和目的地址互换为10.0.0.2 -> 10.0.0.1，由于两个地址数值相同只是交换位置，IP头校验和保持0xe7b6不变；ICMP类型从0x08（Echo-Request）变为0x00（Echo-Reply），校验和相应地从0x52e6更新为0x5ae6，标识符和序列号保持0x332c和1不变，56字节的负载数据原封不动地回送。

**ARP部分：**

发送方向的报文总长42字节，由14字节以太网头和28字节ARP载荷组成。

以太网层的目的MAC同样为全零，源MAC为虚拟网卡地址，以太类型为0x0806表示ARP。

ARP载荷中，硬件类型为以太网（0x0001），协议类型为IPv4（0x0800），硬件地址长度6，协议地址长度4，操作码为0x0001即Request，发送方为10.0.0.1（MAC ae:4c:58:a4:f1:82），目标方为10.0.0.2（MAC 全零）。

翻转后的接收方向报文中，以太网层源和目的MAC互换，ARP操作码从0x0001（Request）变为0x0002（Reply），发送方与目标方的IP和MAC全部互换，即发送方变为10.0.0.2（MAC 全零）、目标方变为10.0.0.1（MAC ae:4c:58:a4:f1:82），从而模拟了对端设备对ARP请求的应答。

整个过程中，所有字段的偏移位置、字节序和翻转均与net_lb_transform()函数的实现一一对应。

使用ethtool工具进行测试：

|   |   |
|---|---|
|1<br> 2<br> 3<br> 4<br> 5<br> 6<br> 7<br> 8<br> 9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33|# 查看驱动信息<br>ethtool -i lbnet0<br><br># 信息输出如下<br>driver: net_loopback<br>version: 1.0<br>firmware-version:<br>expansion-rom-version:<br>bus-info: virtual<br>supports-statistics: yes<br>supports-test: no<br>supports-eeprom-access: no<br>supports-register-dump: no<br>supports-priv-flags: no<br><br># 查看链路状态<br>ethtool lbnet0<br><br># 信息输出如下<br>Settings for lbnet0:<br>        Link detected: yes<br><br># 查看统计信息<br>ethtool -S lbnet0<br><br># 信息输出如下<br>NIC statistics:<br>    tx_packets: 13<br>    tx_bytes: 1162<br>    rx_packets: 13<br>    rx_bytes: 980<br>    tx_dropped: 0<br>    lb_queue_len: 0|

可以看到ethtool可以正常操作lbnet0虚拟网卡，关于ethtool工具使用和信息说明不作过多展开，感兴趣可以自行搜索资料了解。

### 9.6.5. 实验注意事项[¶](#id84 "永久链接至标题")

- 虚拟网卡默认名为lbnet0，注意与系统原生lo回环设备区分。
    
- debug开关开启后会输出大量报文日志，测试建议只ping 1个包，调试完成后及时关闭。
    
- 驱动仅对ARP、IPv4、ICMP 报文做协议翻转，其他协议仅完成二层回环。
    
- 高流量测试时可调整驱动NAPI_BUDGET预算值，平衡处理性能。