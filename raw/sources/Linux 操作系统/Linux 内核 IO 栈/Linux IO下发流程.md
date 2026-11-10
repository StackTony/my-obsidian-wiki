### IO下发流程
#### 简易流程：
Linux本地IO下发过程
[https://blog.csdn.net/invaders/article/details/126449378?utm_medium=distribute.pc_relevant.none-task-blog-2~default~baidujs_baidulandingword~default-1-126449378-blog-121689114.235^v36^pc_relevant_anti_vip_base&spm=1001.2101.3001.4242.2&utm_relevant_index=4](https://blog.csdn.net/invaders/article/details/126449378?utm_medium=distribute.pc_relevant.none-task-blog-2~default~baidujs_baidulandingword~default-1-126449378-blog-121689114.235%5ev36%5epc_relevant_anti_vip_base&spm=1001.2101.3001.4242.2&utm_relevant_index=4)

**P层 --> block层 --> scsi层 --> 驱动 --> 硬件**
1）通用BLOCK层，把请求排队，进入调度层
2）SCSI层提交给驱动层等待返回
3）硬件返回处理成功or超时

![[resources/Diagram 2.svg]]

#### 详细流程：
linux文件写入流程-从vfs层通用block层到scsi磁盘驱动
<https://gmd20.github.io/blog/linux%E6%96%87%E4%BB%B6%E5%86%99%E5%85%A5%E6%B5%81%E7%A8%8B-%E4%BB%8Evfs%E5%B1%82%E9%80%9A%E7%94%A8block%E5%B1%82%E5%88%B0scsi%E7%A3%81%E7%9B%98%E9%A9%B1%E5%8A%A8/>
