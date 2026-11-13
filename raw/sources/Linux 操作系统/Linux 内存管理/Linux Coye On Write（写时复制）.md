原文： [https://zhuanlan.zhihu.com/p/579491341](https://zhuanlan.zhihu.com/p/579491341)

缺页中断是内核在访问一个虚拟地址时，发现该虚拟地址所在的页没有一个物理页框与之相对应，就会触发缺页异常进入物理页面分配的异常函数。而写时复制是指，父进程在fork出子进程的时候，并不会为子进程马上分配物理页框，而是当复进程或者子进程需要对内存进行写操作时，才会分配物理页框，分配时，先将内容完全复制到新页框，然后再进行改写，称为写时复制。

## 1. 写时复制原理

在传统的unix操作系统中，当执行fork系统调用时，内核复制父进程的整个用户空间并把复制得到的那一份分配给子进程，这种行为就非常耗时，这种子进程复制父进程所有资源的方法，有一些很明显的弊端

- 大量使用内存
- 复制操作耗费大量时间
- 通常情况下子进程不需要读或者写父进程拥有的所有资源，复制的资源都没有得以有效的使用

因此现代操作系统采用写时复制技术(Copy On Write, COW)进行优化，避免fork时将父进程所有资源都复制到子进程中，该技术的核心思想是

> 只有在不得不复制的内容时才会去复制内容，其遵循原则为

- 只需要复制父进程的进程地址空间页表到子进程，那么父子进程就共享相同的物理内存
- 当父子进程中有一方需要修改某个物理页面的内容时，触发写保护的缺页中断，然后才复制共享页面的内容，从而使父子进程拥有各自的副本

> 写时复制是一种可以推迟甚至避免复制数据的技术，在现代操作系统中广泛使用，节省了巨大的拷贝开销

## 2. 写时应用实例

**fork()**函数是一个神奇的函数，调用一次，会返回两次，在这个过程中子进程和父进程是共享一个内存空间的。

```c
#include <stdio.h>
#include <string.h> 
#include <sys/types.h>
#include <unistd.h>

int main()
{
	char c = 'a';
	int a = 2;

	int pid = fork();
	if(pid == -1){
		return (-1);
	}

	if(pid > 0){
		c = 'v';
		printf("Hi,Father Pid:%d &c:%p c:%c\n",getpid(),&c,c);
		printf("Hi,Father Pid:%d &a:%p a:%d\n",getpid(),&a,a);
		return (0);
	} else {
		printf("Hi,Child  Pid:%d &c:%p c:%c\n",getpid(),&c,c);
		printf("Hi,Father Pid:%d &a:%p a:%d\n",getpid(),&a,a);
		return (0);
	}
}
```

程序输出

![](https://picx.zhimg.com/v2-6b4e94d81c25ab0d6d0e50b0a46032d5_1440w.jpg)

我们可以看到，父进程中我们对资源 **c** 进行了修改,并打印了资源的地址和值，然后我们在子进程中也打印资源的值。对于父子进程，其对应的虚拟地址空间都没有变化，只是其对应的物理地址空间发生了变化，其变化为

![](https://picx.zhimg.com/v2-28de2914fe524ab2e0398138236f4f61_1440w.jpg)

当变量c发生写改变的时候，其虚拟地址对应的物理页面重新申请了一个页面发生映射关系。下面我们来看看内核通过fork创建子进程的时候，是如何与父进程共享内存资源的，其入口为kernel/fork.c

![](https://pic3.zhimg.com/v2-2b14d69be2d3eca185a52375b8768582_1440w.jpg)

对于copy_page_range函数拷贝父进程页表，那需要拷贝那些页表呢？

- copy_pud_range，页表上级目录
- copy_pmd_range，页中间目录
- copy_pte_range，拷贝页表

对于拷贝页表条目这个函数，其中主要的是为父子进程设置为只读的页项,ptep_set_wrprotect(src_mm, addr, src_pte)将父进程的页表项修改为只读， pte = pte_wrprotect(pte)将子进程的即将写入的页表项值修改为只读（注意：修改之前pte为父进程原来的pte值，修改之后子进程pte还没有写入到对应的页表项条目中！）

```c
/*
	 * If it's a COW mapping, write protect it both
	 * in the parent and the child
	 */
	if (is_cow_mapping(vm_flags)) { //vma为私有可写  而且pte有可写属性
		ptep_set_wrprotect(src_mm, addr, src_pte);//设置父进程页表项为只读
		pte = pte_wrprotect(pte);//为子进程设置只读的页表项值
	}
```

上面的代码块是判断当前页所在的vma是否是私有可写的属性而且父进程页表项是可写：

```c
static inline bool is_cow_mapping(vm_flags_t flags)
{
	return (flags & (VM_SHARED | VM_MAYWRITE)) == VM_MAYWRITE;
}
```

以上fork就完成了对于需要写时复制的页，将父进程的页表设置为只读，并共享相同的物理页，为后面的COW缺页做好页表级别的准备工作。

## 3. 写时复制流程

对于fork仅仅是对COW共享的页面做了只读访问，父子进程可以通过各自的页表就能直接访问到对应的数据，看似一切正常。但是一旦双方有一方需要去写，就会触发处理器异常，处理器就会走到COW异常处理中。之前在handle_pte_fault中有相关的触发条件

```c
if (fe->flags & FAULT_FLAG_WRITE) {         //vma可写
		if (!pte_write(entry))                  //页表项属性只读
			return do_wp_page(fe, entry);       //处理cow
		entry = pte_mkdirty(entry);
	}
```

程序走到上面的判断说明：页表项存在，物理页存在内存，但是vma是可写，pte页表项是只读属性（这就是fork的时候所作的准备），这些条件也是COW缺页异常判断的条件。

当触发COW的时候，就会调用do_wp_page，其处理流程为

```c
static int do_wp_page(struct fault_env *fe, pte_t orig_pte)
	__releases(fe->ptl)
{
	struct vm_area_struct *vma = fe->vma;
	struct page *old_page;

	old_page = vm_normal_page(vma, fe->address, orig_pte);      
	if (!old_page) {
		/*
		 * VM_MIXEDMAP !pfn_valid() case, or VM_SOFTDIRTY clear on a
		 * VM_PFNMAP VMA.
		 *
		 * We should not cow pages in a shared writeable mapping.
		 * Just mark the pages writable and/or call ops->pfn_mkwrite.
		 */
		if ((vma->vm_flags & (VM_WRITE|VM_SHARED)) ==
				     (VM_WRITE|VM_SHARED))
			return wp_pfn_shared(fe, orig_pte);

		pte_unmap_unlock(fe->pte, fe->ptl);
		return wp_page_copy(fe, orig_pte, old_page);
	}
    ....
}
```

通过vm_normal_page函数查找缺页异常地址(addr)对应页面的page数据结构，如果返回的page时一个NULL指针，说明这是一个特殊映射的页面

```c
#若发生缺页异常的页面是一个特殊页面，即vm_normal_page返回位NULL，如果VMA的属性是可写并且是共享的，那么就调用wp_pfn_shared
#若发生的缺页异常的页面是一个不可写的共享页面，那么跳转到wp_page_copy
if (PageAnon(old_page) && !PageKsm(old_page)) {                          --------------(1)
		int total_mapcount;
		if (!trylock_page(old_page)) {
			get_page(old_page);
			pte_unmap_unlock(fe->pte, fe->ptl);
			lock_page(old_page);
			fe->pte = pte_offset_map_lock(vma->vm_mm, fe->pmd,
					fe->address, &fe->ptl);
			if (!pte_same(*fe->pte, orig_pte)) {
				unlock_page(old_page);
				pte_unmap_unlock(fe->pte, fe->ptl);
				put_page(old_page);
				return 0;
			}
			put_page(old_page);
		}
		if (reuse_swap_page(old_page, &total_mapcount)) {
			if (total_mapcount == 1) {
				/*
				 * The page is all ours. Move it to
				 * our anon_vma so the rmap code will
				 * not search our parent or siblings.
				 * Protected against the rmap code by
				 * the page lock.
				 */
				page_move_anon_rmap(old_page, vma);
			}
			unlock_page(old_page);
			return wp_page_reuse(fe, orig_pte, old_page, 0, 0);
		}
		unlock_page(old_page);
	} else if (unlikely((vma->vm_flags & (VM_WRITE|VM_SHARED)) ==
					(VM_WRITE|VM_SHARED))) {
		return wp_page_shared(fe, orig_pte, old_page);                      --------------(2)
	}

	get_page(old_page);

	pte_unmap_unlock(fe->pte, fe->ptl);
	return wp_page_copy(fe, orig_pte, old_page);                           --------------(3)
```

使用PageAnon宏来判断匿名页面，判断当前页面是否位KSM的匿名页面，如果是就执行1的内容，

- trylock_page判断当前的是否已经加锁，如果返回false，说明这个页面已经被别的进程加锁，就会释放锁，然后调用pte_offset_map_lock获取PTE，然后判断PTE是否发生变化，若发生变化，就退出异常处理
- 如果没有加锁，就调用reuse_swap_page函数判断页面是否只有一个进程映射的匿名页面，如果是，就跳转到wp_page_reuse，继续使用这个页面并且不需要写时复制
- 如果处理的是可写的共享页面，就使用wp_page_shared
- c处理写时复制的情况，就调用wp_page_copy

对于do_wp_page函数处理非常多的情况，其总的处理流程如下图所示

![](https://pic4.zhimg.com/v2-3dc827de04c8da879d58fd5461b53865_1440w.jpg)

## 4. 总结

写时复制机制的整个过程如下：

1. 首先发生在父进程fork子进程的时候，父子进程会共享所有的物理页面(此时通过将页映射到每个进程页表形成共享)
2. 将父子进程对应的页表项修改为只读，当有一方试图写共享物理页的时候，由于页表项属性是只读，所以会发生COW缺页异常
3. 缺页异常会为写操作的一方重新分配一个新的物理页，并将原来共享的物理页内容拷贝到新页，然后建立新页的页表映射关系
4. 最终写进程就可以继续执行，并不会影响另外一方，父子进程对共享的私有页面访问就分道扬镳

梳理之前的例子，得到COW的整个过程如下：

![](https://picx.zhimg.com/v2-c660134f1e49224ef84d5b739cdca097_1440w.jpg)
