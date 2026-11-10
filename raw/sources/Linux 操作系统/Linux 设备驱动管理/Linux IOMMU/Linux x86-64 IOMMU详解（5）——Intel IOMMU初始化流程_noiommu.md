## 整体 流程图

长图预警！！！  
下图完整展示了Intel IOMMU的 初始化 流程，是对本文所有内容的总结。只要看懂这张图，读者就能够完全理解Intel IOMMU的初始化流程。  
接下来，笔者将按流程图的顺序，结合代码，介绍Intel IOMMU初始化流程的一些关键步骤。图中部分细节，本文可能并未提到，读者可结合代码自行理解。

![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/931fa16c646524b6728ffaaee4b99eae.png#pic_center)

## Intel IOMMU初始化前的准备工作

### 函数调用 树

```
start_kernel ->
	mm_init ->
		mem_init ->
			pci_iommu_alloc ->
				pci_swiotlb_init ->
					swiotlb_init
				detect_intel_iommu
```

其中的核心函数是pci_iommu_alloc()。

### pci_iommu_alloc()

下面展示该函数的代码。其中，for循环内被注释的部分是原始代码，而为了调试方便，笔者对代码略作改动，在不改变其逻辑的前提下，输出一些关键信息。注：printk()函数中的格式控制字符串"%ps"，能够输出函数指针所指向的函数名的字符串。

```
void __init pci_iommu_alloc(void)
{
        struct iommu_table_entry *p;

        sort_iommu_table(__iommu_table, __iommu_table_end);
        check_iommu_entries(__iommu_table, __iommu_table_end);

        for (p = __iommu_table; p < __iommu_table_end; p++) {
                /*
                if (p && p->detect && p->detect() > 0) {
                        p->flags |= IOMMU_DETECTED;

                        if (p->early_init)
                                p->early_init();
                        if (p->flags & IOMMU_FINISH_IF_DETECTED)
                                break;
                }
                */
                if (p && p->detect) {
                        int p_detect_ret = p->detect();
                        printk("[sh-debug] In pci_iommu_alloc(), p is %ps(); p->detect is %ps(); %ps() returns %d.",
                                        p, p->detect, p->detect, p_detect_ret);

                        if (p_detect_ret > 0) {
                                p->flags |= IOMMU_DETECTED;

                                printk("[sh-debug] In pci_iommu_alloc(), p->early_init is %ps().", p->early_init);
                                if (p->early_init)
                                        p->early_init();
                                if (p->flags & IOMMU_FINISH_IF_DETECTED)
                                        break;
                        }
                }
        }
}
```

首先看for循环之前的代码。在执行pci_iommu_alloc()之前，内核已经通过汇编指令，将IOMMU相关的启动函数，加载到IOMMU Table中。  
那么，IOMMU Table中到底有哪些启动函数呢？  
根据上一篇文章所述，为了启用Intel IOMMU，我们进行了如下配置：  
在. config 文件中：

```
CONFIG_INTEL_IOMMU=y
```

在启动参数文件中：

```
iommu=force intel_iommu=on
```

基于如上配置，编译并重启内核后，使用dmesg过滤输出信息：

```
dmesg | grep "pci_iommu_alloc"
```

结果如下：  
![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/302e932829b9bbb139de016e5e192e7a.png)

在pci_iommu_alloc()代码的for循环中，p每次指向一个IOMMU table entry，而每个entry包含detect和early_init两个函数指针（其实还有第三个函数指针，late_init，在本文末尾介绍pci_iommu_init()函数时会涉及到）。pci_iommu_alloc()会先调用p->detect，只有当该函数返回值大于0时，才会调用p->early_init。  
那么，哪些detect函数的返回值是正数，从而会调用对应的early_init函数呢？在上图中，只有两个。

1. p->detect = pci_swiotlb_detect_4gb。该detect函数返回1，之后调用对应的early_init函数，pci_swiotlb_init()，用于初始化SWIOTLB。
2. p->detect = detect_intel_iommu。该detect函数返回1，但并没有对应的early_init函数（看截图最后一行，p->early_init is 0x0）。

看到这里，读者想必会有两个疑问：

1. 我们不是已经在启动参数中指定使用Intel IOMMU了吗？按照之前文章的说法，Intel IOMMU与SWIOTLB不能共存。那么这里为什么还会初始化SWIOTLB？
2. 既然detect_intel_iommu()没有对应的early_init函数，那么Intel IOMMU的初始化函数，是如何被调用的呢？

对于这两个疑问，接下来我们逐一解答。

#### 为什么会初始化SWIOTLB

对于第一个问题，我们需要看SWIOTLB的detect函数——pci_swiotlb_detect_4gb()代码。

```
/*
 * If 4GB or more detected (and iommu=off not set) or if SME is active
 * then set swiotlb to 1 and return 1.
 */
int __init pci_swiotlb_detect_4gb(void)
{
        /* don't initialize swiotlb if iommu=off (no_iommu=1) */
        if (!no_iommu && max_possible_pfn > MAX_DMA32_PFN)
                swiotlb = 1;

        /*
         * If SME is active then swiotlb will be set to 1 so that bounce
         * buffers are allocated and used for devices that do not support
         * the addressing range required for the encryption mask.
         */
        if (sme_active())
                swiotlb = 1;

        return swiotlb;
}

```

需要说明的是，在上述代码中，**swiotlb是一个全局变量，它决定了SWIOTLB是否被初始化**。相关代码很简单：

```
void __init pci_swiotlb_init(void)
{
        if (swiotlb)
                swiotlb_init(0);
}

```

可见，只有swiotlb = 1时，SWIOTLB初始化函数swiotlb_init()才会被调用——这个函数在[本系列第二篇](https://blog.csdn.net/qq_34719392/article/details/114873284)中进行过详细介绍。在调用pci_swiotlb_init()之前，有若干函数可能会将swiotlb的值置为1，上面提到的pci_swiotlb_detect_4gb()便是其中之一。  
我们只需关注pci_swiotlb_detect_4gb()的第一个 if 语句：

```
if (!no_iommu && max_possible_pfn > MAX_DMA32_PFN)
        swiotlb = 1;
```

对于第一个子条件，顾名思义，!no_iommu显然为true（我们已经启用了Intel IOMMU，显然不是No IOMMU）。重点解释一下第二个子条件。MAX_DMA32_PFN是32位设备能够寻址到的最大页数。所以，如果“物理 内存 中的页数 > MAX_DMA32_PFN”，则将swiotlb置为1。  
对于条件“物理内存中的页数 > MAX_DMA32_PFN”，我们把不等式两边同时乘以PAGE_SIZE（页的大小），这个条件实际上等价于：“物理内存 > 32位设备能够寻址的最大内存”。  
而我们知道，32位设备能够寻址的最大内存为232 = 4GB。因此，这个判断条件最终转换为：  
“物理内存 > 4GB”  
现在就非常明确了：**如果物理内存大于4GB，那么pci_swiotlb_detect_4gb()就会将swiotlb置为1，从而导致后续swiotlb_init()被调用，以初始化SWIOTLB。**

笔者用free命令查看自己机器的可用物理内存，确实大于4GB。

```
free -h
```

![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/d5d325e0e1b458f108903a52e2a0d5ef.png)

作为对比测试，我们在启动参数中，新增一项"mem=1G"，将可用物理内存限制为1GB。

```
iommu=force intel_iommu=on mem=1G
```

重启内核，首先用：

```
free -h
```

确认可用物理内存确实为1GB。

![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/7d8c6bba4cc840a3b9f980a15df31e9e.png)

而后用：

```
dmesg | grep "pci_iommu_alloc"
```

查看内核日志，如下图所示。  
![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/44cc0750a05c685319d77220a05b672b.png)

这次我们可以看到，在可用内存不大于4GB时，detect函数pci_swiotlb_detect_4gb()返回值是0，从而不会调用early_init函数pci_swiotlb_init()，因而不会初始化SWIOTLB。

#### Intel IOMMU的初始化函数是如何被调用的

现在解答第二个疑问。  
虽然detect函数detect_intel_iommu()对应的early_init函数是空函数，不过，detect_intel_iommu()函数会将x86_init.iommu.iommu_init设置为intel_iommu_init，后者正是Intel IOMMU的初始化函数。

```
int __init detect_intel_iommu(void)
{
        int ret;
        /* ...... */
#ifdef CONFIG_X86
        if (!ret) {
                /* 设置iommu_init函数为intel_iommu_init */
                x86_init.iommu.iommu_init = intel_iommu_init;
                x86_platform.iommu_shutdown = intel_iommu_shutdown;
        }

#endif

        /* ...... */
        return ret ? ret : 1;
}

```

那么，intel_iommu_init()何时会被调用呢？相关的调用流程如下：

```
kernel_init ->
	kernel_init_freeable ->
		do_one_initcall ->
			pci_iommu_init ->
				x86_init.iommu.iommu_init	/* i.e. intel_iommu_init */
```

以下展示pci_iommu_init()的代码。此处调用x86_init.iommu.iommu_init()，实际上就是调用intel_iommu_init()。

```
static int __init pci_iommu_init(void)
{
        struct iommu_table_entry *p;

        x86_init.iommu.iommu_init();

        for (p = __iommu_table; p < __iommu_table_end; p++) {
                if (p && (p->flags & IOMMU_DETECTED) && p->late_init)
                        p->late_init();
        }

        return 0;
}
```

#### 不能共存？

讲到这里，细心的读者会发现，笔者还是没有回答“Intel IOMMU与SWIOTLB不能共存”这一疑问——根据上述分析，如果物理内存大于4GB，那么SWIOTLB就会被初始化；而根据我们配置的启动参数，Intel IOMMU也会被初始化。既然二者都被初始化，那它们不就共存了吗？  
这时，我们就要引用一句古话：“一山难容二虎”。聪明的读者应该能立即理解此言的含义。不理解也没关系，请看后续章节的分析。

## intel_iommu_init()的主要工作

intel_iommu_init()是Intel IOMMU的初始化函数，其主要的函数调用树如下：

```
intel_iommu_init ->
	init_dmars ->
		init g_iommus
		intel_iommu_enable_qi ->
			dmar_enable_qi
		iommu_init_domains
		iommu_alloc_root_entry
	SET swiotlb = 0
```

这个函数完成了Intel IOMMU所必需数据结构的初始化工作，本文对此不展开介绍。重点关注最后一行：“SET swiotlb = 0”。这不是一个函数名，而只是一个行为：将 全局变量 swiotlb置为0。以下展示相关代码，非常简单：

```
int __init intel_iommu_init(void)
{
	/* ...... */
#if defined(CONFIG_X86) && defined(CONFIG_SWIOTLB)
        /*
         * If the system has no untrusted device or the user has decided
         * to disable the bounce page mechanisms, we don't need swiotlb.
         * Mark this and the pre-allocated bounce pages will be released
         * later.
         */
        if (!has_untrusted_dev() || intel_no_bounce)
                swiotlb = 0;
#endif
	/* ...... */
}
```

我们看到，如果.config文件中CONFIG_X86和CONFIG_SWIOTLB都为y（在我们的实验机器上确实如此），那么这个if判断就会执行。结合代码与注释，可以得知：如果系统没有检测到不可信设备（untrusted device），或者全局变量intel_no_bounce为1，那么swiotlb就会被置为0。  
那么，这两个条件是否成立呢？  
一般情况下，系统并不会加载不可信设备。在我们的实验机器上也是如此。因此，第一个条件是成立的。由于这个if语句是条件或，所以直接返回true，"swiotlb = 0"会被执行。  
至于intel_no_bounce，我们也顺带介绍一下。它是一个全局变量，默认值为0，代表Intel IOMMU会用到bounce buffer（就是先前文章提到的SWIOTLB bounce机制）。除非在启动参数中进行如下配置，才会将其置为1，代表禁用bounce buffer机制：

```
intel_iommu=nobounce
```

我们并没有进行如此配置，所以它等于默认值0。因此，如果对第二个条件进行判断，那么会返回false——当然，根据if语句的短路原则，在第一个条件返回true的情况下，第二个条件根本不会进行判断。

## 释放已分配的SWIOTLB Buffer和SWIOTLB管理数据结构

是时候水到渠成地解释“一山难容二虎”的含义了。  
上一节我们讲到，一般情况下，Intel IOMMU初始化过程中，也就是函数intel_iommu_init()函数体内，会将全局变量swiotlb置为0。前面我们已经介绍过swiotlb的作用——如果它为0，那么内核后续就不会调用swiotlb_init()，从而不会初始化SWIOTLB。可是，假如内存大于4GB，那么现在SWIOTLB都已经初始化完成，此时再将swiotlb置为0，岂不是为时已晚？

答案就在如下函数调用流程中。

```
pci_iommu_init ->
	intel_iommu_init	/* SET swiotlb = 0 */
	pci_swiotlb_late_init ->	/* If swiotlb == 0, invoke swiotlb_exit() */
		swiotlb_exit	
```

再次看pci_iommu_init()函数代码：

```
static int __init pci_iommu_init(void)
{
        struct iommu_table_entry *p;

        x86_init.iommu.iommu_init();

        for (p = __iommu_table; p < __iommu_table_end; p++) {
                if (p && (p->flags & IOMMU_DETECTED) && p->late_init)
                        p->late_init();
        }

        return 0;
}
```

该函数在for循环中，会遍历IOMMU table entry，调用对应的p->late_init函数。SWIOTLB对应的late_init函数为pci_swiotlb_late_init()，其代码如下：

```
void __init pci_swiotlb_late_init(void)
{
	/* An IOMMU turned us off. */
	if (!swiotlb)
		swiotlb_exit();
	else {
		printk(KERN_INFO "PCI-DMA: "
		       "Using software bounce buffering for IO (SWIOTLB)\n");
		swiotlb_print_info();
	}
}
```

很明显，当swiotlb为0时，函数swiotlb_exit()将会被调用。以下展示swiotlb_exit()的代码，它释放了已分配的SWIOTLB Buffer和所有SWIOTLB管理数据结构。

```
void __init swiotlb_exit(void)
{
	if (!io_tlb_orig_addr)
		return;

	if (late_alloc) {
		free_pages((unsigned long)io_tlb_orig_addr,
			   get_order(io_tlb_nslabs * sizeof(phys_addr_t)));
		free_pages((unsigned long)io_tlb_list, get_order(io_tlb_nslabs *
								 sizeof(int)));
		free_pages((unsigned long)phys_to_virt(io_tlb_start),
			   get_order(io_tlb_nslabs << IO_TLB_SHIFT));
	} else {
		memblock_free_late(__pa(io_tlb_orig_addr),
				   PAGE_ALIGN(io_tlb_nslabs * sizeof(phys_addr_t)));
		memblock_free_late(__pa(io_tlb_list),
				   PAGE_ALIGN(io_tlb_nslabs * sizeof(int)));
		memblock_free_late(io_tlb_start,
				   PAGE_ALIGN(io_tlb_nslabs << IO_TLB_SHIFT));
	}
	swiotlb_cleanup();
}
```

如此，SWIOTLB便不复存在，只剩下Intel IOMMU。

## 总结

我们用一张简单的流程图，描述Intel IOMMU初始化流程的主要步骤。实际上，这5个步骤，也正好对应本文开头流程图中用红色花括号和文字标注的内容。

![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/559c1329c060b7fbdaa2d48c0ad5dcb3.png#pic_center)