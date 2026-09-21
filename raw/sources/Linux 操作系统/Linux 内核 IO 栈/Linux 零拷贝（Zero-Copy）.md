原文： https://zhuanlan.zhihu.com/p/430848775

## **- 概念篇 -**

## **1、零拷贝是什么？**

"零拷贝"中的"拷贝"是指操作系统在I/O操作中,将数据从一个内存区域复制到另外一个内存区域，而"零"并不是指0次复制, 更多的是指在用户态和内核态之间的复制是0次。

## **2、零拷贝给我们带来的好处**

• 减少甚至完全避免不必要的 CPU 拷贝，从而让 CPU 解脱出来去执行其他的任务；

• 减少[内存带宽](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E5%86%85%E5%AD%98%E5%B8%A6%E5%AE%BD&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLlhoXlrZjluKblrr0iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.l8ZdLROvireb6tMGynZMgUy3TWrh7EYH3OiEnilJxSs&zhida_source=entity)的占用；

• 通常零拷贝技术还能够减少用户空间和[操作系统内核](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E6%93%8D%E4%BD%9C%E7%B3%BB%E7%BB%9F%E5%86%85%E6%A0%B8&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLmk43kvZzns7vnu5_lhoXmoLgiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.VYvGd5tsfj82C4Opt3wV5TtBw0j2noAeeRjT2ZISmTs&zhida_source=entity)空间之间的上下文切换。

## **3、操作系统中谁负责IO拷贝？**

DMA 负责内核间的 IO 传输，CPU 负责内核和应用间的 IO 传输。

两种拷贝类型：

（1）[CPU COPY](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=CPU+COPY&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJDUFUgQ09QWSIsInpoaWRhX3NvdXJjZSI6ImVudGl0eSIsImNvbnRlbnRfaWQiOjE4Mzg3MzA2MiwiY29udGVudF90eXBlIjoiQXJ0aWNsZSIsIm1hdGNoX29yZGVyIjoxLCJ6ZF90b2tlbiI6bnVsbH0.JVOCzBPgsQu7GacZipN3FJ6XroUHcnAEycaq4QhcWQk&zhida_source=entity)

通过计算机的组成原理我们知道, 内存的读写操作是需要 CPU 的协调数据总线,[地址总线](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E5%9C%B0%E5%9D%80%E6%80%BB%E7%BA%BF&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLlnLDlnYDmgLvnur8iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.3WpTsdQkJ08qHlz323Hlos5Fku_PXzc82ttwoYR07gQ&zhida_source=entity)和控制总线来完成的因此在"拷贝"发生的时候,往往需要 CPU 暂停现有的处理逻辑,来协助内存的读写，这种我们称为 CPU COPY。CPU COPY 不但占用了 CPU 资源,还占用了总线的带宽。

（2）[DMA COPY](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=DMA+COPY&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJETUEgQ09QWSIsInpoaWRhX3NvdXJjZSI6ImVudGl0eSIsImNvbnRlbnRfaWQiOjE4Mzg3MzA2MiwiY29udGVudF90eXBlIjoiQXJ0aWNsZSIsIm1hdGNoX29yZGVyIjoxLCJ6ZF90b2tlbiI6bnVsbH0.HJgtENcE2IchnCbmotxEaTk5b-eGGOxw1cPDYWTFkgg&zhida_source=entity)

DMA(DIRECT MEMORY ACCESS) 是现代计算机的重要功能，它有一个重要特点：当需要与外设进行数据交换时, CPU 只需要初始化这个动作便可以继续执行其他指令,剩下的数据传输的动作完全由DMA来完成可以看到 DMA COPY 是可以避免大量的 CPU 中断的。

## **4、拷贝过程中会发生什么？**

从内核态到用户态时会发生上下文切换，上下文切换时指由用户态切换到内核态, 以及由内核态切换到用户态。

现在我们对零拷贝有一定的概念基础了，接下来，让我们深入去了解一下 [Linux 操作系统](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=Linux+%E6%93%8D%E4%BD%9C%E7%B3%BB%E7%BB%9F&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJMaW51eCDmk43kvZzns7vnu58iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.V_r2zZdy3O03m0u9yE4LtFDERc03JnJ0OJB9NdB16H8&zhida_source=entity)与 IO 复制之间的来龙去脉。

## **- 原理篇 -**

## **1、内存管理**

Linux 内存管理结构的历史：在 Linux 内核2.4版本之前，内存管理结构中 page cache 和 [buffer cache](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=buffer+cache&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJidWZmZXIgY2FjaGUiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.BT05_jfThG1gAM1Xh-Roi28gw_rG6YA71-O3MtR9bmc&zhida_source=entity) 是分开的，分别是两个独立的。

从 Linux 内核2.4 版本开始操作系统在内存管理机制进行了优化，才支持了零拷贝机制。

### **2、Linux内存管理结构**

Linux 内核的文件 Cache 管理机制来进行实现的，在 Linux 的实现中，文件 Cache 分为两个层面，一是 Page Cache，另一个 Buffer Cache，每一个 Page Cache 包含若干 Buffer Cache。

内存管理系统和 [VFS](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=VFS&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJWRlMiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.dE5qHHlTCgteISzij-B3TMfxUGHtpNOyzE-BkbR3T_M&zhida_source=entity) 只与 Page Cache 交互，内存管理系统负责维护每项 Page Cache 的分配和回收，同时在使用 [memory map](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=memory+map&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJtZW1vcnkgbWFwIiwiemhpZGFfc291cmNlIjoiZW50aXR5IiwiY29udGVudF9pZCI6MTgzODczMDYyLCJjb250ZW50X3R5cGUiOiJBcnRpY2xlIiwibWF0Y2hfb3JkZXIiOjEsInpkX3Rva2VuIjpudWxsfQ.-8P7Dt4KdWBRlPTouFvYCsHxXR7Pb1bGRSzUipTp-fY&zhida_source=entity) 方式访问时负责建立映射。

VFS 负责 Page Cache 与用户空间的数据交换。而具体文件系统则一般只与 Buffer Cache 交互，它们负责在外围存储设备和 Buffer Cache 之间交换数据。

**标注：VFS（virtual File System） 的作用就是采用标准的 Unix 系统调用读写位于不同物理介质上的不同文件系统**，即为各类文件系统提供了一个统一的操作界面和[应用编程接口](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E5%BA%94%E7%94%A8%E7%BC%96%E7%A8%8B%E6%8E%A5%E5%8F%A3&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLlupTnlKjnvJbnqIvmjqXlj6MiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.Na1f1dYv6rm0ErC1NTCKnh7SQLnaaj_oDJFCJAp_qfc&zhida_source=entity)。VFS 是一个可以让open()、read()、write()等系统调用不用关心底层的存储介质和文件系统类型就可以工作的[粘合层](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E7%B2%98%E5%90%88%E5%B1%82&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLnspjlkIjlsYIiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.zz6Pous_EFAk_iM7fvEO1IK-ZeISX7BdJyw43Pj_3Qo&zhida_source=entity)。

![](https://pic1.zhimg.com/v2-5a58db1de950db53a6c66c37bcf6e25c_1440w.jpg)

### **3、应用上下文与内核上下文[共享内存](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E5%85%B1%E4%BA%AB%E5%86%85%E5%AD%98&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLlhbHkuqvlhoXlrZgiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.2jaMJV8ggP-QPVdwh355BRj3JvGbSz2OKZVSHqz3u7k&zhida_source=entity)交互过程**

将 Cache 项映射到用户空间，使得应用程序可以像使用内存指针一样访问文件，Memory map 访问 Cache 的方式在内核中是采用请求页面机制实现的：

• 当我们应用程序调用 mmap（下图中1），陷入到内核中后调用 dommappgoff （图中2）该函数从应用程序的地址空间中分配一段区域作为[映射](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=3&q=%E6%98%A0%E5%B0%84&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLmmKDlsIQiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MywiemRfdG9rZW4iOm51bGx9.F77WOi4Qtad56TOCTfA5pWTCdZRsPdTcve1EaDPidW4&zhida_source=entity)的内存地址，并使用一个 [VMA](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=VMA&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJWTUEiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.rRL0jgGmct4jN7um8Uo-qLQqJe2n375G1zE1YI39UZ8&zhida_source=entity)（vmareastruct）结构代表该区域，之后就返回到应用程序（图中3）；

• 然后当应用程序访问 mmap 所返回的地址指针时（图中4），由于[虚实映射](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E8%99%9A%E5%AE%9E%E6%98%A0%E5%B0%84&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLomZrlrp7mmKDlsIQiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.BrgGaOGbUM_Nq5uosNVB5cHmJHRQUsT_PAbW_rjTtUo&zhida_source=entity)尚未建立，会触发**[缺页中断](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E7%BC%BA%E9%A1%B5%E4%B8%AD%E6%96%AD&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLnvLrpobXkuK3mlq0iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.rcbInDCyrF-60Y4vWZ-UT0YAZ4NxAlD9C6ec2AW8agE&zhida_source=entity)**（图中5）；

• 之后系统会调用缺页中断处理函数（图中6），在缺页中断处理函数中，内核通过相应区域的 VMA 结构判断出该区域属于[文件映射](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E6%96%87%E4%BB%B6%E6%98%A0%E5%B0%84&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLmlofku7bmmKDlsIQiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.P79BOXE8jMIF9prub08Alg3mdD9b1Vz8xBzSdr_nol4&zhida_source=entity)，于是调用具体文件系统的接口读入相应的 Page Cache 项（图中7、8、9），并填写相应的虚实映射表；

• 经过这些步骤之后，应用程序就可以正常访问相应的[内存区域](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=3&q=%E5%86%85%E5%AD%98%E5%8C%BA%E5%9F%9F&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLlhoXlrZjljLrln58iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MywiemRfdG9rZW4iOm51bGx9.C8pkIeQ-CzXP_w4R6o5gBrKtU8SOGkvol_Vzt8s6K5w&zhida_source=entity)了。

![](https://pic4.zhimg.com/v2-6e70a0c9e37a3dd908b694578fc1a8f5_1440w.jpg)

【文章福利】需要C/C++ Linux[服务器架构师](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E6%9C%8D%E5%8A%A1%E5%99%A8%E6%9E%B6%E6%9E%84%E5%B8%88&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLmnI3liqHlmajmnrbmnoTluIgiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.vk4FB8ZXIy3HrdVjZ08rBf1cfd0cq_-KPqY3bg4ta2A&zhida_source=entity)学习资料加群[812855908](https://link.zhihu.com/?target=https%3A//jq.qq.com/%3F_wv%3D1027%26k%3DckYqybaE)（资料包括C/C++，Linux，[golang技术](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=golang%E6%8A%80%E6%9C%AF&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJnb2xhbmfmioDmnK8iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.n8EHb2svV6Dthr_Ohyu8JlQshkzvKuEABGmCcZB9VfY&zhida_source=entity)，内核，Nginx，ZeroMQ，MySQL，Redis，fastdfs，MongoDB，ZK，[流媒体](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E6%B5%81%E5%AA%92%E4%BD%93&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLmtYHlqpLkvZMiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.EO_cO-t1RCppCg3BiauY5k_4olbBOoBiZNEJaFKn2-g&zhida_source=entity)，CDN，[P2P](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=P2P&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJQMlAiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.rd42vFUu69YywbR0Qi9L6EDl5sCnPi_PRyLdSlVKvik&zhida_source=entity)，K8S，[Docker](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=Docker&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJEb2NrZXIiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.X8UvbnmnxjM8DbLrnecoLc96saHLd4v4jW0frjfbOy0&zhida_source=entity)，TCP/IP，协程，[DPDK](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=DPDK&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJEUERLIiwiemhpZGFfc291cmNlIjoiZW50aXR5IiwiY29udGVudF9pZCI6MTgzODczMDYyLCJjb250ZW50X3R5cGUiOiJBcnRpY2xlIiwibWF0Y2hfb3JkZXIiOjEsInpkX3Rva2VuIjpudWxsfQ.r7iqDaDIe41RyKnfx7H_DmzPXHt8Uk8F6EKmcwk5rdA&zhida_source=entity)，ffmpeg等）

![](https://pic2.zhimg.com/v2-016587b1e95f5c6148709dbac1fa8d7b_1440w.jpg)

## **- IO 零拷贝 -**

### **1、存在多次拷贝的原因**

操作系统为了保护系统不被应用程序有意或无意地破坏，为操作系统设置了用户态和内核态两种状态，用户态想要获取系统资源(例如访问硬盘)，必须通过系统调用进入到内核态, 由内核态获取到系统资源，再切换回用户态返回应用程序。

出于 "readahead cache" 和[异步写入](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E5%BC%82%E6%AD%A5%E5%86%99%E5%85%A5&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLlvILmraXlhpnlhaUiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.5NT8hokCtVx8BEwsDb-xf6kMFIE5FrZXpqnonFzfRlE&zhida_source=entity)等等性能优化的需要, 操作系统在内核态中也增加了一个"内核缓冲区"([kernel](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=kernel&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJrZXJuZWwiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.v5y1N8hqllE-0o8FBOTtv9cMhVQHKGMMQDsEJVdKwcE&zhida_source=entity) buffer)。读取数据时并不是直接把数据读取到应用程序的 buffer， 而先读取到 kernel buffer， 再由 kernel buffer 复制到应用程序的 buffer。因此,数据在被应用程序使用之前，可能需要被多次拷贝。

### **2、非零拷贝IO流程**

总结所有系统中, 不管是 WEB [应用服务器](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E5%BA%94%E7%94%A8%E6%9C%8D%E5%8A%A1%E5%99%A8&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLlupTnlKjmnI3liqHlmagiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.6a2ASMYJfa_hJKkI3eABupgZzaxfefXRc7seifRftQo&zhida_source=entity), FTP 服务器,[数据库服务器](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E6%95%B0%E6%8D%AE%E5%BA%93%E6%9C%8D%E5%8A%A1%E5%99%A8&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLmlbDmja7lupPmnI3liqHlmagiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.V7YnuAulkhxvgkCAle_BoDK2eMW6HzEUyO1z-99mojU&zhida_source=entity), 静态[文件服务器](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E6%96%87%E4%BB%B6%E6%9C%8D%E5%8A%A1%E5%99%A8&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLmlofku7bmnI3liqHlmagiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.hDde9Q5zrAow1vPZumlreS-KOzXzjYdA1IUWSI8VZmo&zhida_source=entity)等等, 所有涉及到数据传输的场景，无非就一种:

——从硬盘上读取文件数据, 发送到网络上去。

这个场景我们简化为一个模型:

File.read(fileDesc, buf, len);

Socket.send(socket, buf, len);

为了方便描述,上面这两行代码, 我们给它起个名字: **read-send模型。**

操作系统在实现这个 read-send 模型时,需要有以下步骤:

1. 应用程序开始读文件的操作；
2. 应用程序发起系统调用, 从用户态切换到内核态(第一次上下文切换)；
3. 内核态中把数据从硬盘文件读取到内核中间缓冲区(kernel buf)；
4. 数据从内核中间缓冲区(kernel buf)复制到(用户态)应用程序缓冲区(app buf),从内核态切换回到用户态(第二次上下文切换)；
5. 应用程序开始发送数据到网络上；
6. 应用程序发起系统调用,从用户态切换到内核态(第三次上下文切换)；
7. 内核中把数据从应用程序(app buf)的缓冲区复制到socket的缓冲区(socket)；
8. 内核中再把数据从socket的缓冲区(socket buf)发送的[网卡](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E7%BD%91%E5%8D%A1&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLnvZHljaEiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.egiAjZZse23m2JoxqQ33NQ9IHNQrw9y1VjUpu7GKYyE&zhida_source=entity)的缓冲区(NIC buf)上；
9. 从内核态切换回到用户态(第四次上下文切换)。

如下图表示：

![](https://pic3.zhimg.com/v2-4339abe8f90eaf8ccc294907283a43a2_1440w.jpg)

由上图可以很清晰地看到, 一次 read-send 涉及到了四次拷贝:

1. 硬盘拷贝到内核缓冲区(DMA COPY)；
2. [内核缓冲区](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=3&q=%E5%86%85%E6%A0%B8%E7%BC%93%E5%86%B2%E5%8C%BA&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLlhoXmoLjnvJPlhrLljLoiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MywiemRfdG9rZW4iOm51bGx9.l8IfwQ2yiGv53LX93OHNllTi_Skg5XyiChnGR_OaLsQ&zhida_source=entity)拷贝到[应用程序缓冲区](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=2&q=%E5%BA%94%E7%94%A8%E7%A8%8B%E5%BA%8F%E7%BC%93%E5%86%B2%E5%8C%BA&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLlupTnlKjnqIvluo_nvJPlhrLljLoiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MiwiemRfdG9rZW4iOm51bGx9.xrR-eBSXVovILKihFkOkZ8nsl5zAgyJ1d3REMaH-YO8&zhida_source=entity)(CPU COPY)；
3. 应用程序缓冲区拷贝到socket缓冲区(CPU COPY)；
4. socket buf拷贝到网卡的buf(DMA COPY)。

其中涉及到2次 CPU 中断, 还有4次的上下文切换。很明显,第2次和第3次的的 copy 只是把数据复制到 app buffer 又原封不动的复制回来, 为此带来了两次的 CPU COPY 和两次上下文切换, 是完全没有必要的。

Linux 的零拷贝技术就是为了优化掉这两次**不必要的拷贝。**

### **3、[sendFile](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=sendFile&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJzZW5kRmlsZSIsInpoaWRhX3NvdXJjZSI6ImVudGl0eSIsImNvbnRlbnRfaWQiOjE4Mzg3MzA2MiwiY29udGVudF90eXBlIjoiQXJ0aWNsZSIsIm1hdGNoX29yZGVyIjoxLCJ6ZF90b2tlbiI6bnVsbH0.mLC8d8AJ9702geCMnBmOkpbXDnGZtk6DroeT2YTQNHo&zhida_source=entity) 系统调用的IO流程**

**Linux 内核2.1**开始引入一个叫 sendFile 系统调用,这个系统调用可以在内核态内把数据从内核缓冲区直接复制到[套接字](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E5%A5%97%E6%8E%A5%E5%AD%97&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLlpZfmjqXlrZciLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.Ekoh2AiUyg53x97tL82xO5IbV4cRaYwGlCWUPMLFT0Q&zhida_source=entity)(SOCKET)缓冲区内, 从而可以减少上下文的切换和不必要数据的复制。

这个系统调用其实就是一个高级 I/O 函数, 函数签名如下:

#include<sys/sendfile.h>

ssize_t senfile(int out_fd,int in_fd,off_t* [offset](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=offset&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJvZmZzZXQiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.NVDjkCGDiaXoKepKgjwHODs6eoksSRQgrAK9dPwiu9c&zhida_source=entity),size_t count);

1. out_fd 是写出的[文件描述符](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E6%96%87%E4%BB%B6%E6%8F%8F%E8%BF%B0%E7%AC%A6&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLmlofku7bmj4_ov7DnrKYiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.NixfOLc0aiPUO1YEjDjjCPPwSMs5-g05P9O-iR-JRCc&zhida_source=entity),而且必须是一个 [socket](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=8&q=socket&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJzb2NrZXQiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6OCwiemRfdG9rZW4iOm51bGx9.-uUg5j6D9bgScDwyXv1GlW_zuu3hjSbvuePCdjAQNRE&zhida_source=entity)；
2. in_fd 是读取内容的文件描述符,必须是一个真实的文件, 不能是管道或 socket；
3. offset 是开始读的位置；
4. count 是将要读取的[字节数](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E5%AD%97%E8%8A%82%E6%95%B0&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLlrZfoioLmlbAiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.2J_Wzf8Zqv6QMC1Pz954vFGkCcsbUvT4UrnIKf-zxSY&zhida_source=entity)。

有了sendFile这个系统调用后, 我们 read-send 模型就可以简化为:

1. 应用程序开始读文件的操作；
2. 应用程序发起系统调用, 从用户态切换到内核态(第一次上下文切换)；
3. 内核态中把数据从硬盘文件读取到内核中间缓冲区；
4. 通过 sendFile,在内核态中把数据从内核缓冲区复制到socket的缓冲区；
5. 内核中再把数据从 socket 的缓冲区发送的网卡的 buf 上；
6. 从[内核态](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=18&q=%E5%86%85%E6%A0%B8%E6%80%81&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLlhoXmoLjmgIEiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MTgsInpkX3Rva2VuIjpudWxsfQ.52sCpbBKnPGpibnSrUcacCmabig8VH5P6xMpALhiv80&zhida_source=entity)切换到用户态(第二次上下文切换)。

如下图所示：

![](https://pic2.zhimg.com/v2-c5b255c1c42e195f32c4afc3cb82a26b_1440w.jpg)

**涉及到数据拷贝变成:**

1. 硬盘拷贝到内核缓冲区(DMA COPY)；
2. 内核缓冲区拷贝到socket缓冲区(CPU COPY)；
3. socket 缓冲区拷贝到网卡的buf(DMA COPY)。

可以看到,一次 read-send 模型中, 利用 sendFile 系统调用后, 可以将4次数据拷贝减少到3次, 4次上下文切换减少到2次, 2次 CPU 中断减少到1次。

相对传统 I/O, 这种零拷贝技术通过减少两次上下文切换, 1次 CPU COPY, 可以将[I/O](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=4&q=I%2FO&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJJL08iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6NCwiemRfdG9rZW4iOm51bGx9.fIUAPtejwE0BU6nRfibJJDPh3RnQqjNFBW9mioUgbW0&zhida_source=entity) 性能提高50%以上([网络数据](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=%E7%BD%91%E7%BB%9C%E6%95%B0%E6%8D%AE&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLnvZHnu5zmlbDmja4iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.FWv-o_hjOs1y68D060khimnhhztnfZArUNYhmJY6KGM&zhida_source=entity), 未亲测)。

开篇的概念中说到, 所谓的零拷贝的"零", 是指用户态和内核态之间的拷贝次数为0, 从这个定义上来说, 现在的这个[零拷贝技术](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=4&q=%E9%9B%B6%E6%8B%B7%E8%B4%9D%E6%8A%80%E6%9C%AF&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiLpm7bmi7fotJ3mioDmnK8iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6NCwiemRfdG9rZW4iOm51bGx9.-4S_CubklAlCBGB9YURvbgtxmPgkz9EqOpKXlejQcGk&zhida_source=entity)已经是真正的"零"了。

然而, 对性能追求极致的伟大的科学家和工程师们并不满足于此，精益求精的他们对中间第2次的 CPU COPY 依旧耿耿于怀, 想尽千方百计要去掉这一次没有必要的数据拷贝和 CPU 中断。

### **4、零拷贝的IO流程**

支持 [scatter-gather](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=1&q=scatter-gather&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJzY2F0dGVyLWdhdGhlciIsInpoaWRhX3NvdXJjZSI6ImVudGl0eSIsImNvbnRlbnRfaWQiOjE4Mzg3MzA2MiwiY29udGVudF90eXBlIjoiQXJ0aWNsZSIsIm1hdGNoX29yZGVyIjoxLCJ6ZF90b2tlbiI6bnVsbH0.4tLb5B4v0yxkF12YtfWjcmnsi1fmrBrJoLbcBpXrfyQ&zhida_source=entity) 特性的 sendFile 的 IO 流程：

**Linux在内核2.4**以后的版本中, Linux 内核对 socket 缓冲区描述符做了优化。通过这次优化, sendFile 系统调用可以在只复制 kernel buffer 的少量元信息的基础上, 把数据直接从 kernel buffer 复制到网卡的 buffer 中去，从而避免了从"内核缓冲区"拷贝到"[socket缓冲区](https://zhida.zhihu.com/search?content_id=183873062&content_type=Article&match_order=3&q=socket%E7%BC%93%E5%86%B2%E5%8C%BA&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTE3MzUsInEiOiJzb2NrZXTnvJPlhrLljLoiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoxODM4NzMwNjIsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MywiemRfdG9rZW4iOm51bGx9.tZsyO54CnbC1gInnUVswtct8MqEh7i2J8PTOSN8N9AY&zhida_source=entity)"的这一次拷贝。

这个优化后的 sendFile, 我们称之为**支持 scatter-gather 特性的 sendFile。**

在支持 scatter-gather 特性的 sendFile 的支撑下, 我们的 read-send 模型可以优化为:

1. 应用程序开始读文件的操作；
2. 应用程序发起系统调用, 从用户态进入到内核态(第一次上下文切换)；
3. 内核态中把数据从硬盘文件读取到内核中间缓冲区；
4. 内核态中把数据在内核缓冲区的位置(offset)和数据大小(size)两个信息追加(append)到socket的缓冲区中去；
5. 网卡的buf上根据socekt缓冲区的offset和size从内核缓冲区中直接拷贝数据；
6. 从内核态返回到用户态(第二次上下文切换)；

**这个过程如下图所示:**

![](https://pica.zhimg.com/v2-b72230f321d142066a2bad52c8e0f3c4_1440w.jpg)

最后数据拷贝变成只有两次 **DMA COPY:**

1. 硬盘拷贝到内核缓冲区(DMA COPY)；
2. 内核缓冲区拷贝到网卡的 buf(DMA COPY)。