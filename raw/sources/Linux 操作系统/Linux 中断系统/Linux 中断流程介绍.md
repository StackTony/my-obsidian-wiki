原文： https://zhuanlan.zhihu.com/p/528866826

## **GIC 硬件原理**

GIC，Generic Interrupt Controller。是ARM公司提供的一个通用的中断控制器。主要作用为：接受硬件中断信号，并经过一定处理后，分发给对应的CPU进行处理。

当前GIC 有四个版本，GIC v1~v4, 本文主要介绍GIC v3控制器。

### **GIC v3中断类别**

GICv3定义了以下中断类型：

- SGI (Software Generated Interrupt)：软件触发的中断。软件可以通过写 GICD_SGIR 寄存器来触发一个中断事件，一般用于核间通信，内核中的 IPI：inter-processor interrupts 就是基于 SGI。
- PPI (Private Peripheral Interrupt)：私有外设中断。这是每个核心私有的中断。PPI会送达到指定的CPU上，应用场景有CPU本地时钟。
- SPI (Shared Peripheral Interrupt)：公用的外部设备中断，也定义为共享中断。中断产生后，可以分发到某一个CPU上。比如按键触发一个中断，手机触摸屏触发的中断。
- LPI (Locality-specific Peripheral Interrupt)：LPI 是 GICv3 中的新特性，它们在很多方面与其他类型的中断不同。LPI 始终是基于消息的中断，它们的配置保存在表中而不是寄存器。比如 PCIe 的 MSI/MSI-x 中断。

|中断类型|硬件中断号|
|---|---|
|SGI|0-15|
|PPI|16-31|
|SPI|32-1019|
|reserved|......|
|LPI|8192-MAX|

### **GIC v3 组成**

![](https://pic3.zhimg.com/v2-47b1fab64ebc6b830cbb55a4cfbe92ee_1440w.jpg)

GICv3 控制器由以下三部分组成:

- Distributor：SPI 中断的管理，将中断发送给 Redistributor

1. 打开或关闭每个中断。Distributor对中断的控制分成两个级别。一个是全局中断的控制（GIC_DIST_CTRL）。一旦关闭了全局的中断，那么任何的中断源产生的中断事件都不会被传递到 CPU interface。另外一个级别是对针对各个中断源进行控制（GIC_DIST_ENABLE_CLEAR），关闭某一个中断源会导致该中断事件不会分发到 CPU interface，但不影响其他中断源产生中断事件的分发。
2. 控制将当前优先级最高的中断事件分发到一个或者一组 CPU interface。当一个中断事件分发到多个 CPU interface 的时候，GIC 的内部逻辑应该保证只 assert 一个CPU。
3. 优先级控制。
4. interrupt属性设定。设置每个外设中断的触发方式：电平触发、边缘触发；
5. interrupt group的设定。设置每个中断的 Group，其中 Group0 用于安全中断，支持 FIQ 和 IRQ，Group1 用于非安全中断，只支持 IRQ；

- Redistributor：SGI，PPI，LPI 中断的管理，将中断发送给 CPU interface

1. 启用和禁用 SGI 和 PPI。
2. 设置 SGI 和 PPI 的优先级。
3. 将每个 PPI 设置为电平触发或边缘触发。
4. 将每个 SGI 和 PPI 分配给中断组。
5. 控制 SGI 和 PPI 的状态。
6. 内存中数据结构的基址控制，支持 LPI 的相关中断属性和挂起状态。
7. 电源管理支持。

- CPU interface：传输中断给 Core

1. 打开或关闭 CPU interface 向连接的 CPU assert 中断事件。对于 ARM，CPU interface 和 CPU 之间的中断信号线是 nIRQCPU 和 nFIQCPU。如果关闭了中断，即便是 Distributor 分发了一个中断事件到 CPU interface，也不会 assert 指定的 nIRQ 或者 nFIQ 通知 Core。
2. 中断的确认。Core 会向 CPU interface 应答中断（应答当前优先级最高的那个中断），中断一旦被应答，Distributor 就会把该中断的状态从 pending 修改成 active 或者 pending and active（这是和该中断源的信号有关，例如如果是电平中断并且保持了该 asserted 电平，那么就是 pending and active）。ack 了中断之后，CPU interface 就会 deassert nIRQCPU 和 nFIQCPU 信号线。
3. 中断处理完毕的通知。当 interrupt handler 处理完了一个中断的时候，会向写 CPU interface 的寄存器通知 GIC CPU 已经处理完该中断。做这个动作一方面是通知 Distributor 将中断状态修改为 deactive，另外一方面，CPU interface 会 priority drop，从而允许其他的 pending 的中断向 CPU 提交。
4. 为 CPU 设置中断优先级掩码。通过 priority mask，可以 mask 掉一些优先级比较低的中断，这些中断不会通知到 CPU。
5. 设置 CPU 的中断抢占（preemption）策略。
6. 在多个中断事件同时到来的时候，选择一个优先级最高的通知 CPU。

GICv3 控制器内部模块和各中断类型的关系如下图所示：

![](https://pic4.zhimg.com/v2-f46f5f26989a6c70b09d4d1ca7f7012b_1440w.jpg)

### **中断路由**

GICv3 使用 hierarchy 来标识一个具体的 core, 如下图是一个四层的结构(aarch64)：

![](https://pic3.zhimg.com/v2-b74c32ed0cdc9754178c31c44fed11a4_1440w.jpg)

用 <affinity level 3>.<affinity level 2>.<affinity level 1>.<affinity level 0> 的形式组成一个 PE 的路由。每一个 core 的 affnity 值可以通过 MPDIR_EL1 寄存器获取， 每一个 affinity 占用8bit。配置对应 core 的 MPIDR 值，可以将中断路由到该 core 上。

各个 affinity 的定义是根据 SOC 自己的定义，比如：

```
<group of groups>. <group of processors>.<processor>.<core>
<group of processors>.<processor>.<core>.<thread>
```

中断亲和性的设置的通用函数为 irq_set_affinity，后面会做详细介绍。

### **中断状态机**

中断处理的状态机如下图：

![](https://pica.zhimg.com/v2-c7791a9d84dcdb2e5ffdd054c517ed48_1440w.jpg)

- Inactive：无中断状态，即没有 Pending 也没有 Active。
- Pending：硬件或软件触发了中断，该中断事件已经通过硬件信号通知到 GIC，等待 GIC 分配的那个 CPU 进行处理，在电平触发模式下，产生中断的同时保持 Pending 状态。
- Active：CPU 已经应答（acknowledge）了该中断请求，并且正在处理中。
- Active and pending：当一个中断源处于 Active 状态的时候，同一中断源又触发了中断，进入 pending 状态。

### **中断处理流程**

1. 外设发起中断，发送给 Distributor
2. Distributor 将该中断，分发给合适的 Redistributor
3. Redistributor 将中断信息，发送给 CPU interface
4. CPU interface 产生合适的中断异常给处理器
5. 处理器接收该异常，并且软件处理该中断

## **GIC 驱动**

这里主要分析 linux kernel 中 GIC v3 中断控制器的代码(drivers/irqchip/irq-gic-v3.c)。

### **设备树**

先来看下一个中断控制器的设备树信息：

```
gic: interrupt-controller@51a00000 {
        compatible = "arm,gic-v3";
        reg = <0x0 0x51a00000 0 0x10000>, /* GIC Dist */
              <0x0 0x51b00000 0 0xC0000>, /* GICR */
              <0x0 0x52000000 0 0x2000>,  /* GICC */
              <0x0 0x52010000 0 0x1000>,  /* GICH */
              <0x0 0x52020000 0 0x20000>; /* GICV */
        #interrupt-cells = <3>;
        interrupt-controller;
        interrupts = <GIC_PPI 9
                (GIC_CPU_MASK_SIMPLE(6) | IRQ_TYPE_LEVEL_HIGH)>;
        interrupt-parent = <&gic>;
};
```

- compatible：用于匹配GICv3驱动
- reg ：GIC的物理基地址，分别对应GICD,GICR,GICC…
- #interrupt-cells：这是一个中断控制器节点的属性。它声明了该中断控制器的中断指示符(interrupts)中 cell 的个数
- interrupt-controller: 表示该节点是一个中断控制器
- interrupts：分别代表中断类型，中断号，中断类型， PPI中断亲和， 保留字段

关于设备数的各个字段含义，详细可以参考 Documentation/devicetree/bindings 下的对应信息。

### **初始化**

1. irq chip driver 的声明：

```
IRQCHIP_DECLARE(gic_v3, "arm,gic-v3", gic_of_init);
```

定义 IRQCHIP_DECLARE 之后，相应的内容会保存到 __irqchip_of_table 里边:

```
#define IRQCHIP_DECLARE(name, compat, fn) OF_DECLARE_2(irqchip, name, compat, fn)

#define OF_DECLARE_2(table, name, compat, fn) \ 
        _OF_DECLARE(table, name, compat, fn, of_init_fn_2)

#define _OF_DECLARE(table, name, compat, fn, fn_type)            \ 
    static const struct of_device_id __of_table_##name        \ 
        __used __section(__##table##_of_table)            \ 
         = { .compatible = compat,                \ 
             .data = (fn == (fn_type)NULL) ? fn : fn  }
```

__irqchip_of_table 在链接脚本 vmlinux.lds 里，被放到了 __irqchip_begin 和 __irqchip_of_end 之间，该段用于存放中断控制器信息：

```
#ifdef CONFIG_IRQCHIP
    #define IRQCHIP_OF_MATCH_TABLE()                    \
        . = ALIGN(8);                           \
        VMLINUX_SYMBOL(__irqchip_begin) = .;                \
        *(__irqchip_of_table)                       \
        *(__irqchip_of_end)
#endif
```

在内核启动初始化中断的函数中，of_irq_init 函数会去查找设备节点信息，该函数的传入参数就是 __irqchip_of_table 段，由于 IRQCHIP_DECLARE 已经将信息填充好了，of_irq_init 函数会根据 “arm,gic-v3” 去查找对应的设备节点，并获取设备的信息。or_irq_init 函数中，最终会回调 IRQCHIP_DECLARE 声明的回调函数，也就是 gic_of_init，而这个函数就是 GIC 驱动的初始化入口。

2. gic_of_init 流程：

```
static int __init gic_of_init(struct device_node *node, struct device_node *parent)
{
  ......
 dist_base = of_iomap(node, 0);                                           ------(1)
 if (!dist_base) {
  pr_err("%pOF: unable to map gic dist registers\n", node);
  return -ENXIO;
 }

 err = gic_validate_dist_version(dist_base);                              ------(2)
 if (err) {
  pr_err("%pOF: no distributor detected, giving up\n", node);
  goto out_unmap_dist;
 }

 if (of_property_read_u32(node, "#redistributor-regions", &nr_redist_regions))  ------(3)
  nr_redist_regions = 1;

 rdist_regs = kzalloc(sizeof(*rdist_regs) * nr_redist_regions, GFP_KERNEL);
 if (!rdist_regs) {
  err = -ENOMEM;
  goto out_unmap_dist;
 }

 for (i = 0; i < nr_redist_regions; i++) {                                ------(4)
  struct resource res;
  int ret;

  ret = of_address_to_resource(node, 1 + i, &res);
  rdist_regs[i].redist_base = of_iomap(node, 1 + i);
  if (ret || !rdist_regs[i].redist_base) {
   pr_err("%pOF: couldn't map region %d\n", node, i);
   err = -ENODEV;
   goto out_unmap_rdist;
  }
  rdist_regs[i].phys_base = res.start;
 }
 
 if (of_property_read_u64(node, "redistributor-stride", &redist_stride))  ------(5)
  redist_stride = 0;

 err = gic_init_bases(dist_base, rdist_regs, nr_redist_regions,           ------(6)
        redist_stride, &node->fwnode);
 if (err)
  goto out_unmap_rdist;

 gic_populate_ppi_partitions(node);                                       ------(7)
 gic_of_setup_kvm_info(node);
 return 0;
  ......
 return err;
}
```

1. 映射 GICD 的寄存器地址空间。
2. 验证 GICD 的版本是 GICv3 还是 GICv4（主要通过读GICD_PIDR2寄存器bit[7:4]. 0x1代表GICv1， 0x2代表GICv2…以此类推）。
3. 通过 DTS 读取 redistributor-regions 的值。
4. 为一个 GICR 域分配基地址。
5. 通过 DTS 读取 redistributor-stride 的值。
6. 下面详细介绍。
7. 设置一组 PPI 的亲和性。

```
static int __init gic_init_bases(void __iomem *dist_base,
     struct redist_region *rdist_regs,
     u32 nr_redist_regions,
     u64 redist_stride,
     struct fwnode_handle *handle)
{
  ......
 typer = readl_relaxed(gic_data.dist_base + GICD_TYPER);                ------(1)
 gic_data.rdists.id_bits = GICD_TYPER_ID_BITS(typer);
 gic_irqs = GICD_TYPER_IRQS(typer);
 if (gic_irqs > 1020)
  gic_irqs = 1020;
 gic_data.irq_nr = gic_irqs;

 gic_data.domain = irq_domain_create_tree(handle, &gic_irq_domain_ops,  ------(2)
       &gic_data);
 gic_data.rdists.rdist = alloc_percpu(typeof(*gic_data.rdists.rdist));
 gic_data.rdists.has_vlpis = true;
 gic_data.rdists.has_direct_lpi = true;
  ......
 set_handle_irq(gic_handle_irq);                                        ------(3)

 gic_update_vlpi_properties();                                          ------(4)

 if (IS_ENABLED(CONFIG_ARM_GIC_V3_ITS) && gic_dist_supports_lpis())
  its_init(handle, &gic_data.rdists, gic_data.domain);                  ------(5)

 gic_smp_init();                                                        ------(6)
 gic_dist_init();                                                       ------(7)
 gic_cpu_init();                                                        ------(8)
 gic_cpu_pm_init();                                                     ------(9)

 return 0;
  ......
}
```

1. 确认支持 SPI 中断号最大的值为多少。
2. 向系统中注册一个 irq domain 的数据结构，irq_domain 主要作用是将硬件中断号映射到 irq number，后面会做详细的介绍。
3. 设定 arch 相关的 irq handler。gic_irq_handle 是内核 gic 中断处理的入口函数，后面会做详细的介绍。
4. gic 虚拟化相关的内容。
5. 初始化 ITS。
6. 设置 SMP 核间交互的回调函数，用于 IPI，回到函数为 gic_raise_softir。
7. 初始化 Distributor。
8. 初始化 CPU interface。
9. 初始化 GIC 电源管理。

![](https://picx.zhimg.com/v2-db5f74b66dd196232942ca40782f3fdd_1440w.jpg)

## **中断的映射**

当早期的系统只存在一个中断控制器，而且中断数目也不多的时候，一个很简单的做法就是一个中断号对应到中断控制器的一个号，可以说是简单的线性映射：

![](https://pic4.zhimg.com/v2-7b65e66d05541eb9662f7c145b8043a1_1440w.jpg)

但当一个系统中有多个中断控制器，而且中断号也逐渐增加的时候。linux 内核为了应对此问题，引入了 irq_domain 的概念。

![](https://pic3.zhimg.com/v2-a4b962f85bbd9f9d706981ee8d8d807a_1440w.jpg)

irq_domain 的引入相当于一个中断控制器就是一个 irq_domain。这样一来所有的中断控制器就会出现级联的布局。利用树状的结构可以充分的利用 irq 数目，而且每一个 irq_domain 区域可以自己去管理自己 interrupt 的特性。

每一个中断控制器对应多个中断号， 而硬件中断号在不同的中断控制器上是会重复编码的， 这时仅仅用硬中断号已经不能唯一标识一个外设中断，因此 linux kernel 提供了一个虚拟中断号的概念。

接下来我们看下硬件中断号是如何映射到虚拟中断号的。

### **中断相关的数据结构**

在看硬件中断号映射到虚拟中断号之前，先来看下几个比较重要的数据结构。

struct irq_desc 描述一个外设的中断，称之中断描述符。

```
struct irq_desc {
 struct irq_common_data irq_common_data;
 struct irq_data  irq_data;  
 unsigned int __percpu *kstat_irqs;
 irq_flow_handler_t handle_irq;  
  ......
 struct irqaction *action; 
 ......
} ____cacheline_internodealigned_in_smp;
```

- irq_data：中断控制器的硬件数据
- handle_irq：中断控制器驱动的处理函数，指向一个 struct irqaction 的链表，一个中断源可以多个设备共享，所以一个 irq_desc 可以挂载多个 action，由链表结构组织起来
- action：设备驱动的处理函数

![](https://pic3.zhimg.com/v2-fa8d6851160c8524982d689f53109962_1440w.jpg)

struct irq_data 包含中断控制器的硬件数据。

```
struct irq_data {
 u32   mask;
 unsigned int  irq;
 unsigned long  hwirq;
 struct irq_common_data *common;
 struct irq_chip  *chip;
 struct irq_domain *domain;
#ifdef CONFIG_IRQ_DOMAIN_HIERARCHY
 struct irq_data  *parent_data;
#endif
 void   *chip_data;
};
```

- irq：虚拟中断号
- hwirq：硬件中断号
- chip：对应的 irq_chip 数据结构
- domain：对应的 irq_domain 数据结构

struct irq_chip 用于对中断控制器的硬件操作。

```
struct irq_chip {
 struct device *parent_device;
 const char *name;
 unsigned int (*irq_startup)(struct irq_data *data);
 void  (*irq_shutdown)(struct irq_data *data);
 void  (*irq_enable)(struct irq_data *data);
 void  (*irq_disable)(struct irq_data *data);

 void  (*irq_ack)(struct irq_data *data);
 void  (*irq_mask)(struct irq_data *data);
 void  (*irq_mask_ack)(struct irq_data *data);
 void  (*irq_unmask)(struct irq_data *data);
 void  (*irq_eoi)(struct irq_data *data);

 int  (*irq_set_affinity)(struct irq_data *data, const struct cpumask *dest, bool force);
 int  (*irq_retrigger)(struct irq_data *data);
 int  (*irq_set_type)(struct irq_data *data, unsigned int flow_type);
 int  (*irq_set_wake)(struct irq_data *data, unsigned int on);

 void  (*irq_bus_lock)(struct irq_data *data);
 void  (*irq_bus_sync_unlock)(struct irq_data *data);
 ......
};
```

- parent_device：指向父设备
- name：/proc/interrupts 中显示的名字
- irq_startup：启动中断，如果设置成 NULL，则默认为 enable
- irq_shutdown：关闭中断，如果设置成 NULL，则默认为 disable
- irq_enable：中断使能，如果设置成 NULL，则默认为 chip->unmask
- irq_disable：中断禁止
- irq_ack：开始新的中断
- irq_mask：中断源屏蔽
- irq_mask_ack：应答并屏蔽中断
- irq_unmask：解除中断屏蔽
- irq_eoi：中断处理结束后调用
- irq_set_affinity：在 SMP 中设置 CPU 亲和力
- irq_retrigger：重新发送中断到 CPU
- irq_set_type：设置中断触发类型
- irq_set_wake：使能/禁止电源管理中的唤醒功能
- irq_bus_lock：慢速芯片总线上的锁
- irq_bus_sync_unlock：同步释放慢速总线芯片的锁

struct irq_domain 与中断控制器对应，完成硬件中断号 hwirq 到 virq 的映射。

```
struct irq_domain {
 struct list_head link;
 const char *name;
 const struct irq_domain_ops *ops;
 void *host_data;
 unsigned int flags;
 unsigned int mapcount;

 /* Optional data */
 struct fwnode_handle *fwnode;
 enum irq_domain_bus_token bus_token;
 struct irq_domain_chip_generic *gc;
#ifdef CONFIG_IRQ_DOMAIN_HIERARCHY
 struct irq_domain *parent;
#endif
#ifdef CONFIG_GENERIC_IRQ_DEBUGFS
 struct dentry  *debugfs_file;
#endif

 /* reverse map data. The linear map gets appended to the irq_domain */
 irq_hw_number_t hwirq_max;
 unsigned int revmap_direct_max_irq;
 unsigned int revmap_size;
 struct radix_tree_root revmap_tree;
 unsigned int linear_revmap[];
};
```

- link：用于将 irq_domain 连接到全局链表 irq_domain_list 中
- name：irq_domain 的名称
- ops：irq_domain 映射操作函数集
- mapcount：映射好的中断的数量
- fwnode：对应中断控制器的 device node
- parent：指向父级 irq_domain 的指针，用于支持级联 irq_domain
- hwirq_max：该 irq_domain 支持的中断最大数量
- linear_revmap[]：hwirq->virq 反向映射的线性表

struct irq_domain_ops 是 irq_domain 映射操作函数集。

```
struct irq_domain_ops {
 int (*match)(struct irq_domain *d, struct device_node *node,
       enum irq_domain_bus_token bus_token);
 int (*select)(struct irq_domain *d, struct irq_fwspec *fwspec,
        enum irq_domain_bus_token bus_token);
 int (*map)(struct irq_domain *d, unsigned int virq, irq_hw_number_t hw);
 void (*unmap)(struct irq_domain *d, unsigned int virq);
 int (*xlate)(struct irq_domain *d, struct device_node *node,
       const u32 *intspec, unsigned int intsize,
       unsigned long *out_hwirq, unsigned int *out_type);
 ......
};
```

- match：用于中断控制器设备与 irq_domain 的匹配
- map：用于硬件中断号与 Linux 中断号的映射
- xlate：通过 device_node，解析硬件中断号和触发方式

struct irqaction 主要是用来存设备驱动注册的中断处理函数。

```
struct irqaction {
 irq_handler_t  handler; 
 void   *dev_id;  
  ......
 unsigned int  irq;  
 unsigned int  flags;  
  ......
 const char  *name;   
 struct proc_dir_entry *dir;
} ____cacheline_internodealigned_in_smp;
```

- handler：设备驱动里的中断处理函数
- dev_id：设备 id
- irq：中断号
- flags：中断标志，注册时设置，比如上升沿中断，下降沿中断等
- name：中断名称,产生中断的硬件的名字
- dir：指向 /proc/irq/ 相关的信息

这里，我们用一张图来汇总下上面的数据结构：

![](https://picx.zhimg.com/v2-4d430b26c07d1d1d9cc2bff5260f0d55_1440w.jpg)

上面的结构体 struct irq_desc 是设备驱动加载的过程中完成的，让设备树中的中断能与具体的中断描述符 irq_desc 匹配，其中 struct irqaction 保存着设备的中断处理函数。右边框内的结构体主要是在中断控制器驱动加载的过程中完成的，其中 struct irq_chip 用于对中断控制器的硬件操作，struct irq_domain 用于硬件中断号到 Linux irq 的映射。

下面我们结合代码看下中断控制器驱动和设备驱动是如何创建这些结构体，并且硬中断和虚拟中断号是如何完成映射的。

### **中断控制器注册 irq_domain**

![](https://picx.zhimg.com/v2-ae19b9565a924030252112ebe8df36e3_1440w.png)

通过 __irq_domain_add 初始化 irq_domain 数据结构，然后把 irq_domain 添加到全局的链表 irq_domain_list 中。

### **外设的驱动创建硬中断和虚拟中断号的映射关系**

设备的驱动在初始化的时候可以调用 irq_of_parse_and_map 这个接口函数进行该 device node 中和中断相关的内容的解析，并建立映射关系

![](https://pic4.zhimg.com/v2-6126f845a39af80a844af62fe6d75c8d_1440w.jpg)

- of_irq_parse_one 函数用于解析DTS文件中设备定义的属性，如"reg", “interrupt”
- irq_find_matching_fwspec 遍历 irq_domain_list 链表，找到 device node 匹配的 irq_domain
- gic_irq_domain_translate 解析出中断信息，比如硬件中断号 hwirq，中断触发方式
- irq_domain_alloc_descs 分配一个虚拟的中断号 virq，分配和初始化中断描述符 irq_desc
- gic_irq_domain_alloc 为 hwirq 和 virq 创建映射关系。内部会通过 irq_domain_set_info 调用 irq_domain_set_hwirq_and_chip，然后通过 virq 获取 irq_data 结构体，并将 hwirq 设置到 irq_data->hwirq 中， 最终完成 hwirq 到 virq 的映射
- irq_domain_set_info 根据硬件中断号的范围设置 irq_desc->handle_irq 的指针，共享中断入口为 handle_fasteoi_irq，私有中断入口为 handle_percpu_devid_irq

最后，我们可以通过 /proc/interrupts 下的值来看下它们的关系：

![](https://pica.zhimg.com/v2-fb10695cf1efce5e1c2efd48efd99706_1440w.jpg)

现在，我们已经知道内核为硬件中断号与 Linux 中断号做了映射，相关数据结构的绑定及初始化，并且设置了中断处理函数执行的入口。接下来我们再看下设备的中断是怎么来注册的？

## **中断的注册**

设备驱动中，获取到了 irq 中断号后，通常就会采用 request_irq/request_threaded_irq 来注册中断，其中 request_irq 用于注册普通处理的中断。request_threaded_irq 用于注册线程化处理的中断，线程化中断的主要目的把中断上下文的任务迁移到线程中，减少系统关中断的时间，增强系统的实时性。

```
static inline int __must_check
request_irq(unsigned int irq, irq_handler_t handler, unsigned long flags,
        const char *name, void *dev)
{
    return request_threaded_irq(irq, handler, NULL, flags, name, dev);
}
```

其中 irq 是 linux 中断号，handler 是中断处理函数，flags 是中断标志位，name 是中断的名字。在讲具体的注册流程前，先看一下主要的中断标志位：

```
#define IRQF_SHARED  0x00000080              //多个设备共享一个中断号，需要外设硬件支持
#define IRQF_PROBE_SHARED 0x00000100              //中断处理程序允许sharing mismatch发生
#define __IRQF_TIMER  0x00000200               //时钟中断
#define IRQF_PERCPU  0x00000400               //属于特定CPU的中断
#define IRQF_NOBALANCING 0x00000800               //禁止在CPU之间进行中断均衡处理
#define IRQF_IRQPOLL  0x00001000              //中断被用作轮训
#define IRQF_ONESHOT  0x00002000              //一次性触发的中断，不能嵌套，1）在硬件中断处理完成后才能打开中断；2）在中断线程化中保持关闭状态，直到该中断源上的所有thread_fn函数都执行完
#define IRQF_NO_SUSPEND  0x00004000      //系统休眠唤醒操作中，不关闭该中断
#define IRQF_FORCE_RESUME 0x00008000              //系统唤醒过程中必须强制打开该中断
#define IRQF_NO_THREAD  0x00010000      //禁止中断线程化
#define IRQF_EARLY_RESUME 0x00020000      //系统唤醒过程中在syscore阶段resume，而不用等到设备resume阶段
#define IRQF_COND_SUSPEND 0x00040000      //与NO_SUSPEND的用户共享中断时，执行本设备的中断处理函数
```

![](https://pic2.zhimg.com/v2-4a783033ac772eb92b41a3f7233f020b_1440w.jpg)

创建完成后，通过 ps 命令可以查看系统中的中断线程，注意这些线程是实时线程 SCHED_FIFO：

```
# ps -A | grep "irq/"
root          1749     2       0      0 irq_thread          0 S [irq/433-imx_drm]
root          1750     2       0      0 irq_thread          0 S [irq/439-imx_drm]
root          1751     2       0      0 irq_thread          0 S [irq/445-imx_drm]
root          1752     2       0      0 irq_thread          0 S [irq/451-imx_drm]
root          2044     2       0      0 irq_thread          0 S [irq/279-isl2902]
root          2192     2       0      0 irq_thread          0 S [irq/114-mmc0]
root          2199     2       0      0 irq_thread          0 S [irq/115-mmc1]
root          2203     2       0      0 irq_thread          0 S [irq/322-5b02000]
root          2361     2       0      0 irq_thread          0 S [irq/294-4-0051]
```

## **中断的处理**

当完成中断的注册后，所有结构的组织关系都已经建立好，剩下的工作就是当信号来临时，进行中断的处理工作。这里我们站在前面知识点的基础上，把中断触发，中断处理等整个流程走一遍。

假设当前在 EL0 运行一个应用程序，触发了一个 EL0 的 irq 中断，则处理器会做如下的操作:

![](https://pic1.zhimg.com/v2-f01751e7c3a7d7c51797a669b620ecd0_1440w.jpg)

先会跳到 arm64 对应的异常向量表：

```
/*
 * Exception vectors.
 */
        .pushsection ".entry.text", "ax"

        .align  11
SYM_CODE_START(vectors)
        ......
        
        kernel_ventry   1, sync                         // el1 下的同步异常，例如指令执行异常、缺页中断等
        kernel_ventry   1, irq                          // el1 下的异步异常，硬件中断。1代表异常等级
        kernel_ventry   1, fiq_invalid                  // FIQ EL1h
        kernel_ventry   1, error                        // Error EL1h

        kernel_ventry   0, sync                         // el0 下的同步异常，例如指令执行异常、缺页中断（跳转地址或者取地址）、系统调用等
        kernel_ventry   0, irq                          // el0 下的异步异常，硬件中断。0代表异常等级
        kernel_ventry   0, fiq_invalid                  // FIQ 64-bit EL0
        kernel_ventry   0, error                        // Error 64-bit EL0

        ......
#endif
SYM_CODE_END(vectors)
```

arm64 的异常向量表 vectors 中设置了各种异常的入口。kernel_ventry 展开后，可以看到有效的异常入口有两个同步异常 el0_sync，el1_sync 和两个异步异常 el0_irq，el1_irq，其他异常入口暂时都 invalid。中断属于异步异常。

![](https://pic1.zhimg.com/v2-fdf428e1ca04c5b13525d4d54e441a12_1440w.jpg)

通过上图，我们可以看出中断的处理分为三个部分，保护现场，中断处理，恢复现场。其中 el0_irq 和 el1_irq 的具体实现略有不同，但处理流程大致是相同的。接下来我们以 el0_irq 为例对上面三个步骤进行梳理。

![](https://pica.zhimg.com/v2-f17bf7b95e2e52f662f2a7d1b52b0eae_1440w.jpg)

### **恢复现场**

```
SYM_CODE_START_LOCAL(ret_to_user)
        disable_daif                      //D A I F 分别为PSTAT中的四个异常屏蔽标志位，此处屏蔽这4中异常
        gic_prio_kentry_setup tmp=x3
#ifdef CONFIG_TRACE_IRQFLAGS
        bl      trace_hardirqs_off
#endif
        ldr     x19, [tsk, #TSK_TI_FLAGS]  //获取 thread_info 中的flags变量的值
        and     x2, x19, #_TIF_WORK_MASK
        cbnz    x2, work_pending
finish_ret_to_user:
        user_enter_irqoff
        /* Ignore asynchronous tag check faults in the uaccess routines */
        clear_mte_async_tcf
        enable_step_tsk x19, x2
#ifdef CONFIG_GCC_PLUGIN_STACKLEAK
        bl      stackleak_erase
#endif
        kernel_exit 0                      //恢复 pt_regs 中的寄存器上下文
```

主要分三步：
1. disable 中断
2. 检查在退出中断前有没有需要处理事情，如调度、信号处理等
3. 将之前压栈的 pt_regs 弹出，恢复现场

## **总结**

上面讲了中断控制器和设备驱动的初始化。包括从设备树获取中断源信息的解析，硬件中断号到 Linux 中断号的映射关系，irq_desc 等各个结构的分配及初始化、中断的注册等等，总而言之，就是完成静态关系创建，为中断处理做好准备。

当外设触发中断信号时，中断控制器接收到信号并发送到处理器，此时处理器进行异常模式切换，如果涉及到中断线程化，则还需要进行中断内核线程的唤醒操作，最终完成中断处理函数的执行。

最后，用一张图来汇总中断控制器和设备驱动的来龙去脉：

![](https://pic1.zhimg.com/v2-c6c626142a1f8497058ef895379d42a4_1440w.jpg)


---
## **中断下半部之 workqueue**

workqueue 是除了 softirq 和 tasklet 以外最常用的下半部机制之一。workqueue 的本质是把 work 交给一个内核线程，在进程上下文调度的时候执行。因为这个特点，所以 workqueue 允许重新调度和睡眠，这种异步执行的进程上下文，能解决因为 softirq 和 tasklet 执行时间长而导致的系统实时性下降等问题。

当驱动程序在进程上下文中有异步执行的工作任务时，可以用 work 来描述工作任务。把 work 添加到一个链表 worklist 中，然后由一个内核线程 worker 遍历链表，串行地执行挂入 worklist 中的所有 work。如果 worklist 中没有 work，那么内核线程 worker 就会变成 IDLE 状态；如果有 work，则执行 work 中的回调函数。

## **workqueue 相关的数据结构**

关于 workqueue 中几个概念都是 work 相关的数据结构非常容易混淆，大概可以这样来理解：

### **work_struct ：**

工作。初始化一个 work 并添加到工作队列后，将会将其传递到合适的内核线程来进行处理，它是用于调度的最小单位。

```
struct work_struct {
 atomic_long_t data;     
 struct list_head entry; 
 work_func_t func;       
#ifdef CONFIG_LOCKDEP
 struct lockdep_map lockdep_map;
#endif
};
```

- data：低比特存放状态位，高比特存放 worker_pool 的ID或者 pool_workqueue 的指针
- entry：用于添加到其他队列上
- func：工作任务的处理函数，在内核线程中回调

### **workqueue_struct ：**

工作的集合。workqueue 和 work 是一对多的关系。内核中工作队列分为两种：

1. bound：绑定处理器的工作队列，每个 worker 创建的内核线程绑定到特定的 CPU 上运行。
2. unbound：不绑定处理器的工作队列，创建的时候需要指定 WQ_UNBOUND 标志，内核线程可以在处理器间迁移。

```
struct workqueue_struct {
 struct list_head pwqs;  /* WR: all pwqs of this wq */   
 struct list_head list;  /* PR: list of all workqueues */  

 struct list_head maydays; /* MD: pwqs requesting rescue */    
 struct worker  *rescuer; /* I: rescue worker */  

 struct pool_workqueue *dfl_pwq; /* PW: only for unbound wqs */

 char   name[WQ_NAME_LEN]; /* I: workqueue name */

 /* hot fields used during command issue, aligned to cacheline */
 unsigned int  flags ____cacheline_aligned; /* WQ: WQ_* flags */
 struct pool_workqueue __percpu *cpu_pwqs; /* I: per-cpu pwqs */    
 struct pool_workqueue __rcu *numa_pwq_tbl[]; /* PWR: unbound pwqs indexed by node */    //Per-Node创建pool_workqueue
    ...
};
```

- pwqs：所有的 pool_workqueue 都添加到本链表中
- list：用于将工作队列添加到全局链表 workqueues 中
- maydays：rescue状态下的 pool_workqueue 添加到本链表中
- rescuer：rescuer 内核线程，用于处理内存紧张时创建工作线程失败的情况
- cpu_pwqs：Per-CPU 创建 pool_workqueue
- numa_pwq_tbl[]：Per-Node 创建 pool_workqueue

### **pool_workqueue：**

中间人 / 中介，负责建立起 workqueue 和 worker_pool 之间的关系。workqueue 和 pool_workqueue 是一对多的关系。

```
struct pool_workqueue {
 struct worker_pool *pool;  /* I: the associated pool */    
 struct workqueue_struct *wq;  /* I: the owning workqueue */   

 int   nr_active; /* L: nr of active works */    
 int   max_active; /* L: max active works */   
 struct list_head delayed_works; /* L: delayed works */     
 struct list_head pwqs_node; /* WR: node on wq->pwqs */    
 struct list_head mayday_node; /* MD: node on wq->maydays */   //用于添加到workqueue链表中
    ...
} __aligned(1 << WORK_STRUCT_FLAG_BITS);
```

- pool：指向 worker_pool
- wq：指向所属的 workqueue
- nr_active：活跃的 work 数量
- max_active：活跃的最大 work 数量
- delayed_works：延迟执行的 work 挂入本链表
- pwqs_node：用于添加到 workqueue 链表中
- mayday_node：用于添加到 workqueue 链表中

### **worker_pool：**

工人的集合。pool_workqueue 和 worker_pool 是一对一的关系，worker_pool 和 worker 是一对多的关系。

1. bound 类型的工作队列：worker_pool 是 Per-CPU 创建，每个 CPU 都有两个 worker_pool，对应不同的优先级，nice 值分别为 0 和 -20。
2. unbound 类型的工作队列：worker_pool 创建后会添加到 unbound_pool_hash 哈希表中。

```
struct worker_pool {
 spinlock_t  lock;  /* the pool lock */
 int   cpu;  /* I: the associated cpu */     
 int   node;  /* I: the associated node ID */ 
 int   id;  /* I: pool ID */
 unsigned int  flags;  /* X: flags */

 unsigned long  watchdog_ts; /* L: watchdog timestamp */

 struct list_head worklist; /* L: list of pending works */  
 int   nr_workers; /* L: total number of workers */   

 /* nr_idle includes the ones off idle_list for rebinding */
 int   nr_idle; /* L: currently idle ones */

 struct list_head idle_list; /* X: list of idle workers */  
 struct timer_list idle_timer; /* L: worker idle timeout */
 struct timer_list mayday_timer; /* L: SOS timer for workers */

 /* a workers is either on busy_hash or idle_list, or the manager */
 DECLARE_HASHTABLE(busy_hash, BUSY_WORKER_HASH_ORDER);   /* L: hash of busy workers */

 /* see manage_workers() for details on the two manager mutexes */
 struct worker  *manager; /* L: purely informational */
 struct mutex  attach_mutex; /* attach/detach exclusion */
 struct list_head workers; /* A: attached workers */   
 struct completion *detach_completion; /* all workers detached */

 struct ida  worker_ida; /* worker IDs for task name */

 struct workqueue_attrs *attrs;  /* I: worker attributes */
 struct hlist_node hash_node; /* PL: unbound_pool_hash node */    
    ...
} ____cacheline_aligned_in_smp;
```

- cpu：绑定到 CPU 的 workqueue，代表 CPU ID
- node：非绑定类型的 workqueue，代表内存 Node ID
- worklist：pending 状态的 work 添加到本链表
- nr_workers：worker 的数量
- idle_list：处于 IDLE 状态的 worker 添加到本链表
- busy_hash：工作状态的 worker 添加到本哈希表中
- workers：worker_pool 管理的 worker 添加到本链表中
- hash_node：用于添加到 unbound_pool_hash 中

### **worker ：**

工人。在代码中 worker 对应一个 work_thread() 内核线程。

```
struct worker {
 /* on idle list while idle, on busy hash table while busy */
 union {
  struct list_head entry; /* L: while idle */     
  struct hlist_node hentry; /* L: while busy */ 
 };

 struct work_struct *current_work; /* L: work being processed */  
 work_func_t  current_func; /* L: current_work's fn */                
 struct pool_workqueue *current_pwq; /* L: current_work's pwq */   

 struct list_head scheduled; /* L: scheduled works */   
  
 /* 64 bytes boundary on 64bit, 32 on 32bit */

 struct task_struct *task;  /* I: worker task */   
 struct worker_pool *pool;  /* I: the associated pool */   
      /* L: for rescuers */
 struct list_head node;  /* A: anchored at pool->workers */  //添加到worker_pool->workers链表中
      /* A: runs through worker->node */
    ...
};
```

- entry：用于添加到 worker_pool 的空闲链表中
- hentry：用于添加到 worker_pool 的忙碌列表中
- current_work：当前正在处理的 work
- current_func：当前正在执行的 work 回调函数
- current_pwq：指向当前 work 所属的 pool_workqueue
- scheduled：所有被调度执行的 work 都将添加到该链表中
- task：指向内核线程
- pool：该 worker 所属的 worker_pool
- node：添加到 worker_pool->workers 链表中

可以用下图来总结：

![](https://pic3.zhimg.com/v2-a393aed59b41cf5ff4332e3df22e2b50_1440w.jpg)

![](https://pic4.zhimg.com/v2-0bfd8aa87dfb1ed520c3dc3fbce8492d_1440w.jpg)

## **workqueue 的初始化**

内核在启动的时候会对 workqueue 做初始化，workqueue 的初始化包含两个阶段，分别是 workqueue_init_early 和 workqueue_init。

### **workqueue_init_early**

![](https://pica.zhimg.com/v2-efa01c9596618b089c28a72fe60133ae_1440w.jpg)

- 分配 worker_pool，并且对该结构中的字段进行初始化操作
- 分配 workqueue_struct，并且对该结构中的字段进行初始化操作
- alloc_and_link_pwqs：分配 pool_workqueue，将 workqueue_struct 和 worker_pool 关联起来

### **workqueue_init**

这里主要完成的工作是给之前创建好的 worker_pool，添加一个初始的 worker，然后利用函数 create_worker，创建名字为 kworker/XX:YY 或者 kworker/uXX:YY 的内核线程。其中 XX 表示 worker_pool 的编号，YY 表示 worker 的编号，u 表示unbound。

![](https://pic4.zhimg.com/v2-c75857822f87a81c9c7671c2359f87c3_1440w.jpg)

- 分配 worker，并且对该结构中的字段进行初始化操作
- 为 worker 创建内核线程 worker_thread
- 将 worker 添加到 worker_pool 中
- worker 进入 IDLE 状态

经过上面两个阶段的初始化，workqueue 子系统基本就已经将数据结构的关联建立好了，当有 work 来进行调度的时候，就可以进行处理了。

## **使用 workqueue**

内核推荐驱动开发者使用默认的 workqueue，而不是新建 workqueue。要使用系统默认的 workqueue，首先需要初始化 work，内核提供了相应的宏 INIT_WORK。

### **初始化 work**

```
#define INIT_WORK(_work, _func)      \
 __INIT_WORK((_work), (_func), 0)
  
#define __INIT_WORK(_work, _func, _onstack)    \
 do {        \
  __init_work((_work), _onstack);    \
  (_work)->data = (atomic_long_t) WORK_DATA_INIT(); \
  INIT_LIST_HEAD(&(_work)->entry);   \
  (_work)->func = (_func);    \
 } while (0)
```

初始化 work 后，就可以调用 shedule_work 函数把 work 挂入系统默认的 workqueue 中。

### **work 调度**

![](https://pic3.zhimg.com/v2-f174c03e85659c97ac0b5dd8a068ce64_1440w.jpg)

- 将 work 添加到系统的 system_wq 工作队列中。
- 判断 workqueue 的类型，如果是 bound 类型，根据 CPU 来获取 pool_workqueue。如果是 unbound 类型，通过 node 号来获取 pool_workqueue。
- 判断 pool_workqueue 活跃的 work 数量，少于最大限值则将 work 加入到 pool->worklist 中，否则加入到 pwq->delayed_works 链表中。
- 如果 __need_more_worker 判断没有 worker 在执行，则通过 wake_up_worker 唤醒 worker 内核线程。

### **worker_thread**

worker 内核线程的执行函数是 worker_thread。

![](https://pic2.zhimg.com/v2-220ca08e24d12e10d73a96f0f5cba4d5_1440w.jpg)

- 设置标志位 PF_WQ_WORKER，调度器在进行调度处理时会对 task 进行判断，针对 workerqueue worker 有特殊的处理。
- worker 被唤醒的时候，跳转到 woke_up 执行。
- woke_up 中，如果此时 worker 是需要销毁的，那就进行清理工作并返回。否则，离开 IDLE 状态，并进入 recheck 模块执行。
- recheck 中，判断是否需要更多的 worker 来处理，如果没有任务处理，跳转到 sleep 地方进行睡眠。如果有任务需要处理时，遍历工作链表，对链表中的每个节点调用 process_one_work 来执行 work 的回调函数，即 INIT_WORK 里的回调函数。

![](https://picx.zhimg.com/v2-ce581b40b8a01e41ddd1a93c6101ae55_1440w.jpg)

- sleep 中，没有任务处理时，worker 进入空闲状态，并将当前的内核线程设置成睡眠状态，让出 CPU。

## **总结**

![](https://pica.zhimg.com/v2-18a4c17cd01215601beab342059313a2_1440w.jpg)