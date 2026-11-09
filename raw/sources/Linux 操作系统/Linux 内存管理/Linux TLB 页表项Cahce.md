原文： https://developer.aliyun.com/article/1479067

## 1. TLB介绍

TLB是Translation Lookaside Buffer的简称，可翻译为“地址转换后援缓冲器”，也可简称为“快表”。

简单地说，**TLB就是页表的Cache，属于MMU的一部分**，其中存储了当前最可能被访问到的页表项，其内容是部分页表项的一个副本。

处理器在取指或者执行访问memory指令的时候都需要进行地址翻译，即把虚拟地址翻译成物理地址。

而地址翻译是一个漫长的过程，需要遍历几个level的Translation table，从而产生严重的开销。

为了提高性能，我们会在MMU中增加一个TLB的单元，把地址翻译关系保存在这个高速缓存中，从而省略了对内存中页表的访问。

![](https://ucc.alicdn.com/pic/developer-ecology/xnrzg3oftrk66_73d9841fe3404f7eb64293455e1848d8.png?x-oss-process=image%2Fresize%2Cw_1400%2Cm_lfit%2Fformat%2Cwebp)

**TLB存放了之前已经进行过地址转换的查询结果。** 这样，当同样的虚拟地址需要进行地址转换的时候，我们可以直接在 TLB 里面查询结果，而不需要多次访问内存来完成一次转换。

TLB其实本质上也是一种cache，既然是一种cache，其目的就是为了提供更高的performance。而与我们知道的指令cache和数据cache又又什么不同呢？

- 1.指令cache：解决cpu获取main memory中的指令数据的速度比较慢的问题而设立  
    
- 2.数据cache：解决cpu获取main memory中的数据的速度比较慢的问题而设立  
    

Cache为了更快的访问main memory中的数据和指令，而TLB是为了更快的进行地址翻译而将部分的页表内容缓存到了Translation lookasid buffer中，避免了从main memory访问页表的过程。

## 2. TLB的转换过程

TLB中的项由两部分组成：

- 标识区:存放的是虚地址的一部
- 数据区:存放物理页号、存储保护信息以及其他一些辅助信息

对于数据区的辅助信息包括以下内容：

- 有效位(Valid)：对于操作系统，所有的数据都不会加载进内存，当数据不在内存的时候，就需要到硬盘查找并加载到内存。当为1时，表示在内存上，为0时，该页不在内存，就需要到硬盘查找。
- 引用位(reference):由于TLB中的项数是一定的，所以当有新的TLB项需要进来但是又满了的话，如果根据LRU算法，就将最近最少使用的项替换成新的项。故需要引用位。同时要注意的是，页表中也有引用位。
- 脏位(dirty):当内存上的某个块需要被新的块替换时，它需要根据脏位判断这个块之前有没有被修改过，如果被修改过，先把这个块更新到硬盘再替换，否则就直接替换。

![](https://ucc.alicdn.com/pic/developer-ecology/xnrzg3oftrk66_42214c70bf104761b36cd5f372325ba8.png?x-oss-process=image%2Fresize%2Cw_1400%2Cm_lfit%2Fformat%2Cwebp)

下面我们来看一下，当存在TLB的访问流程：

- 当CPU收到应用程序发来的虚拟地址后，首先去TLB中根据标志Tag寻找页表数据，假如TLB中正好存放所需的页表并且有效位是1，说明TLB命中了，那么直接就可以从TLB中获取该虚拟页号对应的物理页号。
- 假如有效位是0，说明该页不在内存中，这时候就发生缺页异常，CPU需要先去外存中将该页调入内存并将页表和TLB更新
- 假如在TLB中没有找到，就通过上一章节的方法，通过分页机制来实现虚拟地址到物理地址的查找。
- 如果TLB已经满了，那么还要设计替换算法来决定让哪一个TLB entry失效，从而加载新的页表项。

引用位、脏位何时更新?

1. 如果是TLB命中，那么引用位就会被置1，当TLB或页表满时，就会根据该引用位选择适合的替换位置
2. 如果TLB命中且这个访存操作是个写操作，那么脏位就会被置1，表明该页被修改过，当该页要从内存中移除时会先执行将该页写会外存的操作，保证数据被正确修改。

## 3. 如何确定TLB match

我们选择Cortex-A72 processor来描述ARMv8的TLB的组成结构以及维护TLB的指令

![](https://ucc.alicdn.com/pic/developer-ecology/xnrzg3oftrk66_1ce6f506316f467fb186ff169d71af21.png?x-oss-process=image%2Fresize%2Cw_1400%2Cm_lfit%2Fformat%2Cwebp)

A72实现了2个level的TLB，

- 绿色是L1 TLB，包括L1 instruction TLB（48-entry fully-associative）和L1 data TLB（32-entry fully-associative）。
- 黄色block是L2 unified TLB，它要大一些，可以容纳1024个entry，是4-way set-associative的。当L1 TLB发生TLB miss的时候，L2 TLB是它们坚强的后盾

通过上图，我们还可以看出：对于多核CPU，每个processor core都有自己的TLB。

![](https://ucc.alicdn.com/pic/developer-ecology/xnrzg3oftrk66_9157b4462c6244e1aad425ff1dcb90c4.png?x-oss-process=image%2Fresize%2Cw_1400%2Cm_lfit%2Fformat%2Cwebp)

假如不做任何的处理，那么在进程A切换到进程B的时候，TLB和Cache中同时存在了A和B进程的数据。

对于kernel space其实无所谓，因为所有的进程都是共享的

对于A和B进程，它们各种有自己的独立的用户地址空间，也就是说，同样的一个虚拟地址X，在A的地址空间中可以被翻译成Pa，而在B地址空间中会被翻译成Pb，如果在地址翻译过程中，TLB中同时存在A和B进程的数据，那么旧的A地址空间的缓存项会影响B进程地址空间的翻译

因此，在进程切换的时候，需要有tlb的操作，以便清除旧进程的影响，具体怎样做呢？

当系统发生进程切换，从进程A切换到进程B，从而导致地址空间也从A切换到B，这时候，我们可以认为在A进程执行过程中，所有TLB和Cache的数据都是for A进程的，一旦切换到B，整个地址空间都不一样了，因此需要全部flush掉

这种方案当然没有问题，当进程B被切入执行的时候，其面对的CPU是一个干干净净，从头开始的硬件环境，TLB和Cache中不会有任何的残留的A进程的数据来影响当前B进程的执行。

当然，稍微有一点遗憾的就是在B进程开始执行的时候，TLB和Cache都是冰冷的（空空如也），因此，B进程刚开始执行的时候，TLB miss和Cache miss都非常严重，从而导致了性能的下降。

我们管**这种空TLB叫做cold TLB**，它需要随着进程的运行warm up起来才能慢慢发挥起来效果，而在这个时候有可能又会有新的进程被调度了，而造成**TLB的颠簸效应。**

我们采用进程地址空间这样的术语，其实它可以被进一步细分为内核地址空间和用户地址空间。

对于所有的进程（包括内核线程），内核地址空间是一样的，因此对于这部分地址翻译，无论进程如何切换，内核地址空间转换到物理地址的关系是永远不变的，其实在进程A切换到B的时候，不需要flush掉，因为B进程也可以继续使用这部分的TLB内容（上图中，橘色的block）。

对于用户地址空间，各个进程都有自己独立的地址空间，在进程A切换到B的时候，TLB中的和A进程相关的entry（上图中，青色的block）对于B是完全没有任何意义的，需要flush掉。

在这样的思路指导下，我们其实需要区分global和local（其实就是process-specific的意思）这两种类型的地址翻译，因此，在页表描述符中往往有一个bit来标识该地址翻译是global还是local的，同样的，

**在TLB中，这个标识global还是local的flag也会被缓存起来**。有了这样的设计之后，我们可以根据不同的场景而flush all或者只是flush local tlb entry。

## 4. 多核的TLB操作

完成单核场景下的分析之后，我们一起来看看多核的情况。进程切换相关的TLB逻辑block示意图如下

![](https://ucc.alicdn.com/pic/developer-ecology/xnrzg3oftrk66_035185e6c50a40f1bc4e942e3f9a7d07.png?x-oss-process=image%2Fresize%2Cw_1400%2Cm_lfit%2Fformat%2Cwebp)

在多核系统中，进程切换的时候，TLB的操作要复杂一些，主要原因有两点：

- 其一是各个cpu core有各自的TLB，因此TLB的操作可以分成两类，一类是flush all，即将所有cpu core上的tlb flush掉，
- 还有一类操作是flush local tlb，**即仅仅flush本cpu core的tlb。**

另外一个原因是进程可以调度到任何一个cpu core上执行（当然具体和cpu affinity的设定相关），**从而导致task处处留情（在各个cpu上留有残余的tlb entry）。**

我们了解到地址翻译有global（各个进程共享）和local（进程特定的）的概念，因而tlb entry也有global和local的区分。

如果不区分这两个概念，那么进程切换的时候，直接flush该cpu上的所有残余。

这样，当进程A切出的时候，留给下一个进程B一个清爽的tlb，而当进程A在其他cpu上再次调度的时候，它面临的也是一个全空的TLB（其他cpu的tlb不会影响）。

当然，如果区分global 和local，那么tlb操作也基本类似，只不过进程切换的时候，不是flush该cpu上的所有tlb entry，**而是flush所有的tlb local entry就OK了**。

## 5. PCID

按照这种思路走下去，那就要思考，有没有别的办法能够不刷新TLB呢？

有办法的，那就是PCID。

PCID（进程上下文标识符）是在Westmere架构引入的新特性。简单来说，在此之前，TLB是单纯的VA到PA的转换表，进程1和进程2的VA对应的PA不同，不能放在一起。

加上PCID后，转换变成VA + 进程上下文ID到PA的转换表，放在一起完全没有问题了。

这样进程1和进程2的页表可以和谐的在TLB中共处，进程在它们之前切换完全不需要预热了！

所以新的加载CR3的过程变成了：如果CR4的PCID=1，加载CR3就不需要Flush TLB。

## 6. TLB shootdown

一切看起来很美好，PCID这个在多年前就有了的技术，现在已经在每个Intel CPU中生根了，那么是不是已经被广泛使用了呢？

而实际的情况是Linux在2017年底才在4.15版中真正全面使用了PCID（尽管在4.14中开始部分引入PCID，见参考资料1），这是为什么呢？

PCID这么好的技术也有副作用。

在它之前的日子里，Linux在多核CPU上调度进程时候，因为每次进程调度都会刷掉进程用户空间的TLB，并没有什么问题。

如果支持PCID的话，TLB操作变得很简单，或者说我们没有必要去执行TLB的操作，因为在TLB的搜索的时候已经区分各个进程，这样TLB不会影响其他任务的执行。

在单核系统中，这样的操作确实能够获得很好的性能，例如场景为A—>B—>A，如果TLB足够大，TLB再两个进程中反复切换，极大的提升了性能。

但是在多核系统重，如果CPU支持PCID，并且在进程切换的时候不flush tlb，那么系统中各个CPU中的TLB entry则保留各个进程的TLB entry，当在某个CPU上，一个进程被销毁了，或者该进程修改了自己的页表的时候，就必须将该进程的TLB从系统中请出去。

这时候，不仅仅需要flush本CPU上对应的TLB entry，还需要flush其他CPU上和该进程相关的残余。

**而这个动作就需要通过IPI实现，从而引起了系统开销，此外PCID的分配和管理也会带来额外的开销。**

再加上PCID里面的上下文ID长度有限，只能够放得下4096个进程ID，这就需要一定的管理以便申请和放弃。

如此种种，导致Linux系统在应用PCID上并不积极，直到不得不这样做。

## 7. 结论

TLB的引入解决了分页机制的性能问题，但是如何提高TLB的性能问题，但是如何提高TLB的命中确成为一个新的技术难题，对于X86提供了PCID的方式，而ARM采用的ASID技术，但是对于现在日益复杂的应用场景，这些都未能彻底的解决这些问题。

## 参考资料

- [https://zhuanlan.zhihu.com/p/492184589?utm_id=0](https://zhuanlan.zhihu.com/p/492184589?utm_id=0)