原文：[https://www.cnblogs.com/yuanqiangfei/p/17825601.html](https://www.cnblogs.com/yuanqiangfei/p/17825601.html)

### 一、概述

　　硬件中断发生频繁，是件很消耗 CPU 资源的事情，在多核 CPU 条件下如果有办法把大量硬件中断分配给不同的 CPU (core) 处理显然能很好的平衡性能。kernel 2.4 以后的版本利用可编程中断控制器的特性支持把不同的硬件中断请求（IRQs）分配到特定的 CPU 上，这个绑定技术被称为 SMP IRQ Affinity

### 二、名词解释

- IRQ: Interrupt ReQuest中断请求,IRQ号决定了需要被CPU处理的优先级。IRQ号越小意味着优先级越高
- SMP：(Symmetric Multi-Processing)对称多处理结构的简称，是指在一个计算机上汇集了一组处理器(多CPU),各CPU之间共享内存子系统以及总线结构。可以理解为系统存在多个完全相同的CPU ，所有CPU共享总线，拥有自己的寄存器。对于内存和外部设备访问，由于共享总线，所以是共享的。 Linux 操作系统多个 CPU 共享在系统空间上映射相同，是完全对等的;
- 中断:是由硬件或软件发送的一种称为IRQ的信号，是一种CPU与硬件沟通的方式（还有另外一种叫轮询）中断是一种电信号，由硬件产生，并直接送到中断控制器上，然后再由中断控制器向CPU发送信号，CPU检测到该信号后，就中断当前的工作转而去处理中断。然后，处理器会通知操作系统已经产生中断，这样操作系统就会对这个中断进行适当的处理。中断分为两个过程，中间以中断控制器作为分隔。上半部分即中断上半部，下半部分为中断下半部。上半部分大部分为所说的硬件中断，下半部分为软中断。  

                                                                                    ![](https://img2023.cnblogs.com/blog/1298835/202311/1298835-20231111094539693-128164846.png)

- 中断控制器：常见的中断控制器有两种：可编程中断控制器 8259A 和高级可编程中断控制器（APIC），传统的8259A只适合单CPU的情况，现在都是多CPU多核的 SMP 体系，所以为了充分利用SMP体系结构、把中断传递给系统上的每个CPU以便更好实现并行和提高性能。
- 硬件中断：通常由真实物理设备产生的脉冲信号作为信号源，也就是说这里的物理设备与中断控制器沟通方式是通过物理电信号来做的。往简单说就是每个硬件设备都需要和 CPU 有某种形式的通信以便 CPU 及时知道发生了什么事情，这样 CPU 可能就会放下手中的事情去处理应急事件，硬件设备主动打扰 CPU 的现象就可称为硬件中断(有时还区分非屏蔽中断(Non-maskable interrupts,即NMI)和可屏蔽中断(Maskable interrupts))软件中断：由中断控制器负责统一调度，通常硬件设备产生信号，这个信号带有中断号发送给中断控制器，中断控制器轮训收到的信号来调用对应的中断处理程序  
    上下文切换：上下文切换，发生在内核态，其诱因通常是密集型计算。system call仅仅是kernel mode switch，上下文切换有多种表现形式，如进程之间，线程之间，栈帧之间等。                     

                                                             ![](https://img2023.cnblogs.com/blog/1298835/202311/1298835-20231111094631659-211753928.png)

### 三、SMP IRQ affinity

　　　　APIC表示高级可编程中断控制器（Advanced Programmable Interrupt Controlle）,APIC是SMP体系的核心，通过APIC可以将中断分发到不同的CPU来处理.即将中断绑定CPU或者把中断处理平摊到CPU上，这个过程叫做 SMP IRQ Affinity

#### 1、使用前提

- 需要多CPU的系统，使用uname -a可以查询是否支持SMP
- 需要大于等于2.4的Linux 内核 ，使用uname -r可以查询内核版本
- 相关设置文件，设置/proc/irq/{IRQ}/smp_affinity和/proc/irq/{IRQ}/smp_affinity_list指定了哪些CPU能够关联到一个给定的IRQ源. 这两个文件包含了这些指定cpu的cpu位掩码(smp_affinity)和cpu列表(smp_affinity_list)

#### 2、绑定硬中断到CPU

- 手动绑定 IRQ 到不同 CPU，需要先停掉 IRQ 自动调节的服务进程，否则自己手动绑定做的更改将会被自动调节进程给覆盖掉。
- SMP_AFFINITY文件:在/proc/irq/{IRQ}/目录下都有一个smp_affinity文件，这个文件中，所表示的CPU核心以十六进制来表示的。

##### (1)查找硬件IRQ号

|   |   |
|---|---|
|1<br><br>2<br><br>3<br><br>4<br><br>5<br><br>6<br><br>7<br><br>8<br><br>9<br><br>10<br><br>11<br><br>12<br><br>13<br><br>14<br><br>15<br><br>16<br><br>17<br><br>18<br><br>19<br><br>20<br><br>21<br><br>22<br><br>23<br><br>24<br><br>25<br><br>26<br><br>27<br><br>28<br><br>29<br><br>30<br><br>31<br><br>32<br><br>33<br><br>34|`[root@wmstianjin16172 ~]`<br><br>           `CPU0       CPU1 ...       CPU10      CPU11`     <br><br>  `0:        151          0 ...          0          0  IR-IO-APIC-edge      timer`<br><br>  `4:          1          0 ...          0          0  IR-IO-APIC-edge`   <br><br>  `8:         65          0 ...          0          0  IR-IO-APIC-edge      rtc0`<br><br>  `9:   14986870          0 ...          0          0  IR-IO-APIC-fasteoi   acpi`<br><br> `16:         26          0 ...          0          0  IR-IO-APIC-fasteoi   ehci_hcd:usb1`<br><br> `23:        711          0 ...          0          0  IR-IO-APIC-fasteoi   ehci_hcd:usb2`<br><br> `48:          0          0 ...          0          0  DMAR_MSI-edge      dmar0`<br><br>                            `…………`<br><br> `74:          0          0 ...          0          0  IR-PCI-MSI-edge      ahci`<br><br> `75:          1          0 ...          0          0  IR-PCI-MSI-edge      eth0`<br><br> `76:    1008671   86184098 ...   34556579          0  IR-PCI-MSI-edge      eth0-TxRx-0`<br><br> `77:    1821647      29869 ...      63607          0  IR-PCI-MSI-edge      eth0-TxRx-1`<br><br> `78:         10       8431 ...  211622276          0  IR-PCI-MSI-edge      eth0-TxRx-2`<br><br> `79:         10          0 ...          0  360545261  IR-PCI-MSI-edge      eth0-TxRx-3`<br><br> `80:   77837858  229674917 ...          0          0  IR-PCI-MSI-edge      eth0-TxRx-4`<br><br> `81:  184905831   70950472 ...    4972306          0  IR-PCI-MSI-edge      eth0-TxRx-5`<br><br> `82:  112830765   16260506 ...  128387722          0  IR-PCI-MSI-edge      eth0-TxRx-6`<br><br> `83:         10          0 ...          0          0  IR-PCI-MSI-edge      eth0-TxRx-7`<br><br>`NMI:       1547        678 ...        493        698   Non-maskable interrupts`<br><br>`LOC:  424126712  457610969 ...  289672679  301760023   Local timer interrupts`<br><br>`SPU:          0          0 ...          0          0   Spurious interrupts`<br><br>`PMI:       1547        678 ...        493        698   Performance monitoring interrupts`<br><br>`IWI:          0          0 ...          0          0   IRQ work interrupts`<br><br>`RES:  387358708  463695594 ...  111027119   98766294   Rescheduling interrupts`<br><br>`CAL:       3009       5228 ...       5265       5278   Function call interrupts`<br><br>`TLB:    1432171    1441738 ...    3160227    2003518   TLB shootdowns`<br><br>`TRM:          0          0 ...          0          0   Thermal event interrupts`<br><br>`THR:          0          0 ...          0          0   Threshold APIC interrupts`<br><br>`MCE:          0          0 ...          0          0   Machine check exceptions`<br><br>`MCP:      22452      22452 ...      22452      22452   Machine check polls`<br><br>`ERR:          0`           <br><br>`MIS:          0`|

##### (2)修改/proc/irq/{IRQ}/smp_affinity

- 注意smp_affinity这个值是一个十六进制的bitmask，它和cpu No.序列的“与”运算结果就是将affinity设置在那个（那些）CPU了。（也即smp_affinity中被设置为1的位为CPU No.）

如：8个逻辑core，那么CPU#的序列为11111111 （从右到左依次为CPU0~CPU7）

- 如果cat /proc/irq/76/smp_affinity的值为：20（20是16进制对应的二进制为：00100000与11111111求与），则76这个IRQ的亲和性为#5号CPU。
- 每个IRQ的默认的smp affinity在这里：cat /proc/irq/default_smp_affinity

另外，cat /proc/irq/{IRQ}/smp_affinity_list(此文件为10进制)得到的即是CPU的一个List。

|   |   |
|---|---|
|1<br><br>2<br><br>3<br><br>4<br><br>5<br><br>6<br><br>7<br><br>8|`[root@wmstianjin16172 ~]`<br><br>`080`<br><br>`[root@wmstianjin16172 ~]`<br><br>`7`<br><br>`[root@wmstianjin16172 ~]`<br><br>`400`<br><br>`[root@wmstianjin16172 ~]`<br><br>`10`|

16进制080对应的2进制为10000000（快速算法一位16进制转换成4位2进制左边补0，即0000 1000 0000）所以对应为编号为8的CPU即CPU7（第8颗）  
同理算400编号为11的CPU即CPU10

|   |   |
|---|---|
|1<br><br>2<br><br>3<br><br>4|`[root@wmstianjin16172 ~]`<br><br>`0-11`<br><br>`[root@wmstianjin16172 ~]`<br><br>`fff`|

这是设置多颗CPU的样例：fff（1111 1111 1111）  
修改的时候可以都好隔开或者-表示范围

|   |   |
|---|---|
|1<br><br>2|`[root@wmstianjin16172 ~]`<br><br>`[root@wmstianjin16172 ~]`|

### 四、网卡负载均衡

　　对单队列网卡而言，smp_affinity和smp_affinity_list配置多CPU是没有效果的。但可以用RPS/RFS（Receive Packet Steering/Receive flow steering）来搞定：RPS/RFS主要是针对单队列网卡多CPU环境。虽然有这些虚拟队列的支撑，但是毕竟是软件模拟的，由于RPS只是单纯把数据包均衡到不同的cpu，这个时候如果应用程序所在的cpu和软中断处理的cpu不是同一个，此时对于cpu cache的影响会很大，那么RFS确保应用程序处理的cpu跟软中断处理的cpu是同一个，这样就充分利用cpu的cache。不在举例 请参考/网卡软中断过高问题优化总结/多队列网卡简介/Linux内核 RPS和RFS功能详细测试分析  
　　smp_affinity主要针对多队列网卡多CPU环境，如网卡支持多队列则可使用SMP irq affinity直接绑定硬中断，要是不支持多队列，那就用RPS解决网络软中断的负载均衡，即单个网卡的软中断分散到多个CPU处理，避免单个CPU负载过大导致性能瓶颈。

确定网卡是否支持多队列:（针对的是pci网卡，如果是usb网卡需要查看usb相关中断）

|   |   |
|---|---|
|1<br><br>2<br><br>3<br><br>4<br><br>5<br><br>6<br><br>7<br><br>8<br><br>9<br><br>10|`cat` `/proc/interrupts` `\|``grep` `eth0`<br><br> `75:          1          0 ...          0          0  IR-PCI-MSI-edge      eth0`<br><br> `76:    1008671   86184098 ...   34556579          0  IR-PCI-MSI-edge      eth0-TxRx-0`<br><br> `77:    1821647      29869 ...      63607          0  IR-PCI-MSI-edge      eth0-TxRx-1`<br><br> `78:         10       8431 ...  211622276          0  IR-PCI-MSI-edge      eth0-TxRx-2`<br><br> `79:         10          0 ...          0  360545261  IR-PCI-MSI-edge      eth0-TxRx-3`<br><br> `80:   77837858  229674917 ...          0          0  IR-PCI-MSI-edge      eth0-TxRx-4`<br><br> `81:  184905831   70950472 ...    4972306          0  IR-PCI-MSI-edge      eth0-TxRx-5`<br><br> `82:  112830765   16260506 ...  128387722          0  IR-PCI-MSI-edge      eth0-TxRx-6`<br><br> `83:         10          0 ...          0          0  IR-PCI-MSI-edge      eth0-TxRx-7`|

### 五、使用总结

1、通过手动改变smp_affinity文件中的值来将IRQ绑定到指定的CPU核心上，或者启用irqbalance服务来自动绑定IRQ到CPU核心上。没有启动irqbalance 也没有合理的做手动 irq 绑定的话会有性能问题。手动 irq 只推荐给很 heavy、很特殊的情况，比如带多网卡多硬盘的网络存储服务器，一般机器一般应用还是用irqbalance 省心  
2、在一个大量小包的系统上，irqbalance优化几乎没有效果，而且还使得cpu消耗分配的不均衡，导致机器性能得不到充分的利用，这个时候需要把它给结束掉。  
3、对于文件服务器、高流量 Web 服务器这样的应用来说，把不同的网卡 IRQ 均衡绑定到不同的 CPU 上将会减轻某个 CPU 的负担，提高多个 CPU 整体处理中断的能力；  
4、对于数据库服务器这样的应用来说，把磁盘控制器绑到一个 CPU、把网卡绑定到另一个 CPU 将会提高数据库的响应时间、优化性能。合理的根据自己的生产环境和应用的特点来平衡 IRQ 中断有助于提高系统的整体吞吐能力和性能。  
5、DB可以设置一部分CPU处理硬盘IO，一部分CPU处理网络IO，多网卡服务器可以设置对应CPU对应网卡。当然具体情况看生产情况而定。

性能优化是一个过程而不是结果，需要大量的测试、监测以及持续的观察和改进。