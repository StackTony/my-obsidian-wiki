## 前情回顾

在上一篇文章中，我们详细介绍了Intel IOMMU的初始化流程，并耗费大量笔墨讲述了此过程中Intel IOMMU与SWIOTLB二虎相争的故事。最终，SWIOTLB被禁用，而Intel IOMMU得以保留。现在，所有的DMA操作，都要经由Intel IOMMU了。本文将介绍Intel IOMMU在DMA Coherent Mapping过程中的作用。

## 整体流程图

下面这张流程图是对本文内容的概括。

![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/8b5c945831832d16711d037763d2eec0.png#pic_center)

## intel_dma_ops结构体

在DMA代码中，有一个重要的结构体声明，那就是struct dma_map_ops。这个结构体包含了一系列函数指针，规定了各种DMA操作的函数。所有的硬件IOMMU都必须用相应的函数实例化struct dma_map_ops的函数指针。在Intel IOMMU中，这样实例化后的结构体，就是intel_dma_ops。以下是intel_dma_ops的定义。

```
static const struct dma_map_ops intel_dma_ops = {
	.alloc = intel_alloc_coherent,
	.free = intel_free_coherent,
	.map_sg = intel_map_sg,
	.unmap_sg = intel_unmap_sg,
	.map_page = intel_map_page,
	.unmap_page = intel_unmap_page,
	.map_resource = intel_map_resource,
	.unmap_resource = intel_unmap_resource,
	.dma_supported = dma_direct_supported,
	.mmap = dma_common_mmap,
	.get_sgtable = dma_common_get_sgtable,
	.get_required_mask = intel_get_required_mask,
};
```

需要指出的是，intel_dma_ops并未实例化struct dma_map_ops的所有函数指针——例如，它并未实例化任何sync函数，包括sync_single_for_device、sync_single_for_cpu等等。  
本文将重点介绍第一个函数，即alloc函数——intel_alloc_coherent。它是Intel IOMMU用于实现DMA Coherent Mapping的函数。让我们看看，Intel IOMMU的存在，会导致DMA Coherent Mapping出现哪些变化。

## 函数调用树

下面的函数调用树，清晰地描述了Intel IOMMU参与下的DMA Coherent Mapping（下文称为**Intel IOMMU DMA Coherent Mapping**）流程中涉及的主要函数。

```
intel_alloc_coherent ->
	/* if iommu_need_mapping(dev) returns false */
	dma_direct_alloc ->
		dma_direct_alloc_pages ->
			__dma_direct_alloc_pages ->
				dma_alloc_from_contiguous ->
					cma_alloc
				alloc_pages_node ->
	/* if iommu_need_mapping(dev) returns true */
	dma_alloc_contiguous
	alloc_pages
		__intel_map_single ->
			deferred_attach_domain ->
				find_domain
			domain_get_iommu
			intel_alloc_iova ->
				alloc_iova_fast ->
					iova_rcache_get
					alloc_iova ->
						alloc_iova_mem ->
							kmem_cache_zalloc ->
								kmem_cache_alloc ->
						__alloc_and_insert_iova_range
			domain_pfn_mapping ->
				domain_mapping ->
					__domain_mapping ->
						pfn_to_dma_pte
						domain_flush_cache
```

上述函数调用树中，相同缩进的函数，可能为顺序结构，也可能在同一分支结构的不同分支上，读者可以自行结合代码理解。不过，笔者用注释标明了其中最重要的一个分支结构：函数intel_alloc_coherent()会根据函数iommu_need_mapping()的返回值——即设备是否需要Intel IOMMU映射，来决定DMA Coherent Mapping的实现方式。  
如果设备不需要映射，那么走第一个分支，调用dma_direct_alloc()，这完全是**传统DMA Coherent Mapping**流程。所谓“传统”是指，即使没有启用Intel IOMMU，DMA Coherent Mapping也会沿用这一流程。  
如果设备需要映射，那么走第二个分支。实现映射的入口函数是__intel_map_single()。  
接下来我们介绍intel_alloc_coherent()函数，读者可以结合代码理解上述分支。

## intel_alloc_coherent()函数

我们先从顶层函数intel_alloc_coherent()函数开始，其代码如下。笔者加了两行简单的注释，以标记两种DMA Coherent Mapping的实现流程。

```
static void *intel_alloc_coherent(struct device *dev, size_t size,
				  dma_addr_t *dma_handle, gfp_t flags,
				  unsigned long attrs)
{
	struct page *page = NULL;
	int order;

	if (!iommu_need_mapping(dev))
		/* 传统DMA Coherent Mapping流程 */
		return dma_direct_alloc(dev, size, dma_handle, flags, attrs);

	/* 从这里开始，是Intel IOMMU DMA Coherent Mapping流程 */
	size = PAGE_ALIGN(size);
	order = get_order(size);

	if (gfpflags_allow_blocking(flags)) {
		unsigned int count = size >> PAGE_SHIFT;

		page = dma_alloc_from_contiguous(dev, count, order,
						 flags & __GFP_NOWARN);
	}

	if (!page)
		page = alloc_pages(flags, order);
	if (!page)
		return NULL;
	memset(page_address(page), 0, size);

	*dma_handle = __intel_map_single(dev, page_to_phys(page), size,
					 DMA_BIDIRECTIONAL,
					 dev->coherent_dma_mask);
	if (*dma_handle != DMA_MAPPING_ERROR)
		return page_address(page);
	if (!dma_release_from_contiguous(dev, page, size >> PAGE_SHIFT))
		__free_pages(page, order);

	return NULL;
}
```

## iommu_need_mapping()函数

现在我们分析这个关键的判断函数iommu_need_mapping()，它判断设备是否需要进行Intel IOMMU映射，代码如下。

```
static bool iommu_need_mapping(struct device *dev)
{
	int ret;

	if (iommu_dummy(dev))
		return false;

	ret = identity_mapping(dev);
	if (ret) {
		u64 dma_mask = *dev->dma_mask;

		if (dev->coherent_dma_mask && dev->coherent_dma_mask < dma_mask)
			dma_mask = dev->coherent_dma_mask;

		if (dma_mask >= dma_direct_get_required_mask(dev))
			return false;

		/* ...... */
	}

	return true;
}
```

判断依据主要有二：

1. 设备本身的archdata.iommu属性。iommu_need_mapping()会调用identity_mapping()，而后者的返回值，取决于设备的archdata.iommu属性。
2. 设备的dma_mask属性，代表设备的DMA寻址能力。其中最关键的判断代码是下面两行，在笔者的机器上，其含义相当于：**如果设备能够直接寻址的内存范围不小于1GB，则不需要映射，反之则需要**。从这个意义上来说，倒是与SWIOTLB map的触发条件非常相似。

```
if (dma_mask >= dma_direct_get_required_mask(dev))
	return false;
```

## __intel_map_single()函数

现在我们假定设备需要映射，进入Intel IOMMU DMA Coherent Mapping流程。  
首先，内核会像传统流程那样，申请一段连续物理内存，用作DMA Buffer，这就是函数dma_alloc_from_contiguous()和alloc_pages()的作用。  
而后，调用__intel_map_single()函数，完成映射。那么，映射的具体含义是什么呢？  
在具体介绍此函数之前，我们有必要介绍一些Intel IOMMU涉及的概念。

### IOVA

回顾本系列第一篇文章中的这张图，它解释了IOMMU得名的由来。

![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/23f0f982a6693370c99cbdf58e3041d4.jpeg)

对虚拟内存机制略有耳闻的读者都知道，MMU（Memory Management Unit）是一个地址转译硬件，能够将VA（Virtual Address）映射为PA（ Physical Address)。VA是由谁来访问的呢？是用户进程。  
IOMMU（I/O Memory Management Unit）的功能与MMU非常相似，也是将一个“虚拟地址”映射为PA，只不过这个“虚拟地址”是设备进行DMA操作时访问的，因而称为IOVA（I/O Virtual Address）。因此，**IOMMU的作用是将IOVA映射为PA**。  
需要注意的是，上图中使用的术语是DMA Address，这是一个更为宽泛的概念——在不同的场合，DMA Address有不同的表现形式。而在启用Intel IOMMU时，DMA Address的表现形式就是IOVA。

### IOMMU页表

我们知道，MMU将VA映射为PA，是通过页表（Page Table）来实现的。对于 Linux x86-64操作系统，页表默认为4级。  
Intel IOMMU将IOVA转换为PA的过程，也是通过专用的页表来实现的，本文称为IOMMU页表。IOMMU页表与MMU页表彼此独立，但原理基本相同，并且默认情况下也是4级页表。  
下图展现了IOMMU页表将IOVA映射为PA的流程（基于4K标准页）。可以看出，它与MMU页表的地址转译流程，原理完全一致。  
![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/7c5e410aa49a288ed09298ef93c87ad3.png)

### __intel_map_single()函数代码

现在，我们可以开始介绍__intel_map_single()函数了，其代码如下。笔者删除了非关键代码，并且对于其中的重要函数，用注释简要说明其功能。

```
static dma_addr_t __intel_map_single(struct device *dev, phys_addr_t paddr,
				     size_t size, int dir, u64 dma_mask)
{
	struct dmar_domain *domain;
	phys_addr_t start_paddr;
	unsigned long iova_pfn;
	int prot = 0;
	int ret;
	struct intel_iommu *iommu;
	unsigned long paddr_pfn = paddr >> PAGE_SHIFT;

	/* ...... */
	size = aligned_nrpages(paddr, size);
	
	/* 申请一个IOVA */
	iova_pfn = intel_alloc_iova(dev, domain, dma_to_mm_pfn(size), dma_mask);
	if (!iova_pfn)
		goto error;

	/* ...... */
	
	/*
	 * paddr - (paddr + size) might be partial page, we should map the whole
	 * page.  Note: if two part of one page are separately mapped, we
	 * might have two guest_addr mapping to the same host paddr, but this
	 * is not a big problem
	 */
	/* 建立IOVA与物理页的映射关系 */
	ret = domain_pfn_mapping(domain, mm_to_dma_pfn(iova_pfn),
				 mm_to_dma_pfn(paddr_pfn), size, prot);
	if (ret)
		goto error;

	/*
	 * start_paddr = iova_pfn << PAGE_SHIFT
	 * start_paddr看起来是DMA Buffer物理地址，实际上只是IOVA
	 * 真正的DMA Buffer物理地址是作为本函数参数的paddr
	 */
	start_paddr = (phys_addr_t)iova_pfn << PAGE_SHIFT;
	start_paddr += paddr & ~PAGE_MASK;

	trace_map_single(dev, start_paddr, paddr, size << VTD_PAGE_SHIFT);
	
	/* 将start_paddr作为DMA地址返回给设备 */
	return start_paddr;

error:
	/* ...... */
}
```

## intel_alloc_iova()函数

顾名思义，这个函数申请一个IOVA。我们截取前文函数调用树中从intel_alloc_iova()开始的部分，放在下面：

```
intel_alloc_iova ->
	alloc_iova_fast ->
		iova_rcache_get
		alloc_iova ->
			alloc_iova_mem ->
				kmem_cache_zalloc ->
					kmem_cache_alloc ->
```

这个函数会调用alloc_iova()，并且最后落到kmem_cache_alloc()函数，分配一个struct iova结构体。kmem_cache_alloc()是从slab分配器申请结构体的入口函数。事实上，内核启动时，就通过iova_cache_get()函数，声明了struct iova结构体专用的slab分配器。

## domain_pfn_mapping()函数

这是__intel_map_single()调用的另一个重要函数，它完成从IOVA到PA的映射。该函数最后会调用__domain_mapping()。这个函数的代码比较长，以下仅展示其最重要的部分：

```
static int __domain_mapping(struct dmar_domain *domain, unsigned long iov_pfn,
			    struct scatterlist *sg, unsigned long phys_pfn,
			    unsigned long nr_pages, int prot)
{
	struct dma_pte *first_pte = NULL, *pte = NULL;
	phys_addr_t uninitialized_var(pteval);
	unsigned long sg_res = 0;
	unsigned int largepage_lvl = 0;
	unsigned long lvl_pages = 0;

	/* ...... */
	if (!sg) {
		sg_res = nr_pages;
		pteval = ((phys_addr_t)phys_pfn << VTD_PAGE_SHIFT) | prot;
	}

	while (nr_pages > 0) {
		uint64_t tmp;

		/* ...... */
		if (!pte) {
			largepage_lvl = hardware_largepage_caps(domain, iov_pfn, phys_pfn, sg_res);

			first_pte = pte = pfn_to_dma_pte(domain, iov_pfn, &largepage_lvl);
			if (!pte)
				return -ENOMEM;

		/* ...... */
		/* We don't need lock here, nobody else
		 * touches the iova range
		 */
		tmp = cmpxchg64_local(&pte->val, 0ULL, pteval);

		/* ...... */
		nr_pages -= lvl_pages;
		iov_pfn += lvl_pages;
		phys_pfn += lvl_pages;
		pteval += lvl_pages * VTD_PAGE_SIZE;
		sg_res -= lvl_pages;

		/* If the next PTE would be the first in a new page, then we
		   need to flush the cache on the entries we've just written.
		   And then we'll need to recalculate 'pte', so clear it and
		   let it get set again in the if (!pte) block above.

		   If we're done (!nr_pages) we need to flush the cache too.

		   Also if we've been setting superpages, we may need to
		   recalculate 'pte' and switch back to smaller pages for the
		   end of the mapping, if the trailing size is not enough to
		   use another superpage (i.e. sg_res < lvl_pages). */
		pte++;
		if (!nr_pages || first_pte_in_page(pte) ||
		    (largepage_lvl > 1 && sg_res < lvl_pages)) {
			domain_flush_cache(domain, first_pte,
					   (void *)pte - (void *)first_pte);
			pte = NULL;
		}
		/* ...... */
	}
	return 0;
}
```

上述代码中的while循环，即：

```
while (nr_pages > 0) { ... }
```

代表从页表的最高级逐级向下，直至到达PTE一级的过程。

在每一级中，函数都会分别计算pteval和pte，二者分别由PA和IOVA对应区段转换而来。然后，下面这行代码将pte->val设置为pteval，从而建立起从IOVA（pte）到PA（pteval）的映射关系。

```
tmp = cmpxchg64_local(&pte->val, 0ULL, pteval);
```

## Intel IOMMU参与下的DMA操作流程

读者理解以上的DMA alloc过程后，接下来就很容易理解实际DMA的操作流程了。  
DMA alloc的结果是，intel_alloc_coherent()将一个IOVA作为DMA地址，返回给设备。而后，设备就会向该IOVA发起DMA读写操作。此时，Intel IOMMU就会根据IOMMU页表中已建立好的映射关系，将IOVA映射为DMA Buffer的物理地址PA，从而完成DMA数据传输。