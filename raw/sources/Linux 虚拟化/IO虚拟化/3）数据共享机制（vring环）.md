
上一节分析了消息通知机制，消息通知之后数据如何传送呢？在整体流程图中我们其实已经画出---**vring**

### **1. Vring数据结构**
```c
struct vring {
    unsigned int num;

    struct vring_desc *desc;

    struct vring_avail *avail;

    struct vring_used *used;
};
```

VRING共享区域总共有三个表：

　　**vring_desc**表，存放虚拟机产生的IO请求的地址，实际共享的数据；
　　**vring_avail**表，指明vring_desc中哪些项是可用的，==前端告诉后端我有新请求可以来取给硬件了，前端写入后端读取==；
　　**vring_used**表，指明vring_desc中哪些项已经被递交到硬件，==后端告诉前端你的IO处理完了可以读取结果了，后端写入前端读取==。

这样，我们往virng_desc表中存放IO请求，用vring_avail告诉QEMU进程vring_desc表中哪些项是可用的，QEMU将IO请求递交给硬件执行后，用vring_used表来告诉前端vring_desc表中哪些项已经被递交，可以释放这些项了。

#### **1）vring_desc：**
```c
/* Virtio ring descriptors: 16 bytes.  These can chain together via "next". */
struct vring_desc {
    /* Address (guest-physical). */
    __virtio64 addr;
    /* Length. */
    __virtio32 len;
    /* The flags as indicated above. */
    __virtio16 flags;
    /* We chain unused descriptors via this, too */
    __virtio16 next;
};
```

存储虚拟机产生的IO请求在内存中的地址(GPA地址)，在这个表中每一行都包含四个域，如下所示：

　　**addr**，存储IO请求在虚拟机内的内存地址，是一个GPA值；
　　**len**，表示这个IO请求在内存中的长度；
　　**flags**，指示这一行的数据是可读、可写（VRING_DESC_F_WRITE），是否是一个请求的最后一项（VRING_DESC_F_NEXT）；
　　**next**，每个IO请求都有可能包含了vring_desc表中的多行，next域就指明了这个请求的下一项在哪一行。

其实，通过next我们就将一个IO请求在vring_desc中存储的多行连接成了一个链表，当flag=~ VRING_DESC_F_NEXT，就表示这个链表到了末尾。

如下图所示，表示desc表中有两个IO请求，分别通过next域组成了链表。

　　![[774036-20220127153409556-836900867 1.png]]

#### **2）vring_avail**

存储的是每个IO请求在vring_desc中连接成的链表的表头位置。数据结构如下所示：
```c
struct vring_avail {
    __virtio16 flags;
    __virtio16 idx;
    __virtio16 ring[];
};
```

在vring_desc表中：

　　**ring[]**, 通过next域连接起来的链表的表头在vring_desc表中的位置
　　**idx**，指向的是ring数组中下一个可用的空闲位置；
　　**flags**是一个标志域。

如下图所示， vring_avail表指明了vring_desc表中有两个IO请求组成的链表是最近更新可用的，它们分别从0号位置和3号位置开始。

　　![[774036-20220127153654680-1377886127 1.png]]

#### **3）vring_used**
```c
struct vring_used_elem {
    /* Index of start of used descriptor chain. */
    __virtio32 id;
    /* Total length of the descriptor chain which was used (written to) */
    __virtio32 len;
};

struct vring_used {
    __virtio16 flags;
    __virtio16 idx;
    struct vring_used_elem ring[];
};
```

vring_uesd中ring[]数组有两个成员：

　　**id**，表示处理完成的IO request在vring_desc表中的组成的链表的头结点位置；
　　**len**，表示链表的长度。
　　**idx**，指向了ring数组中下一个可用的位置；
　　**flags**，是标记位。

如下图所示，vring_used表表示vring_desc表中的从0号位置开始的IO请求已经被递交给硬件，前端可以释放vring_desc表中的相应项。

　　![[774036-20220127153923501-200230662 1.png]]

### **2. 对Vring进行操作**

Vring的操作分为两部分：在前端虚拟机内，通过virtqueue_add_buf将IO请求的内存地址，放入vring_desc表中，同时更新vring_avail表；在后端QEMU进程内，根据vring_avail表的内容，通过virtqueue_get_buf从vring_desc表中取得数据，同时更新vring_used表。

#### **1) virtqueue_add_buf**

　　　①将IO请求的地址存入当前空闲的vring_desc表中的addr（如果没有空闲表项，则通知后端完成读写请求，释放空间）；
　　　②设置flags域，若本次IO请求还未完，则为VRING_DESC_F_NEXT，并转③；若本次IO请求的地址都已保存至vring_desc中，则为~VRING_DESC_F_NEXT，转④；
　　　③根据next，找到下一个空闲的vrring_desc表项，跳转①；
　　　④本次IO请求已全部存在vring_desc表中，并通过next域连接成了一个链表，将链表头结点在vring_desc表中位置写入vring_avail->ring\[idx\]，并使idx++。

　　虚拟机内通过上述步骤将IO请求地址存至vring_desc表中，并通过kick函数通知前端来读取数据。

　　![[774036-20220127154230671-394523311 1.png]]

 如上图所示，在add_buf之前vring_desc表中已经保存了一个IO请求链表，可以从vring_avail中知道，vring_desc表中的IO请求链表头结点位置为0，然后根据next遍历整个IO请求链表。

我们调用add_buf将本次IO请求放入vring_desc表中：在vring_desc表中的第三行添加一个数据项，flags域设置为NEXT,表示本次IO请求的内容还没有结束；从next域找到下一个空闲的vring_desc表项，即第4行，添加一行数据，flags域设置为~NEXT，表示本次IO请求的内容已经结束next域置为空。

更新vring_avail表，从idx找到viring_avali表中的第一个空闲位置（第2行），把添加到vring_desc表中的IO请求链表的头结点位置(也就是图中vring_desc表的第3行)，添加到vring_avail表中；更新vring_avail的idx加1。

#### **2) virtqueue_get_buf**

　　　①从vring_avail中取出数据，直到取到idx位置为止；
　　　②根据vring_avail中取到的值，从vring_desc中取出链表的头结点，并根据next域依次找到其余结点；
　　　③当IO请求被取出后，将链表头结点的位置值放入vring_used->ring\[idx\].id。

　　![[774036-20220127154355106-1249084027 1.png]]

如上图所示，在QEMU进行操作之前，vring_avial表中显示vring_desc表中有两个新的IO请求。

从vring_avail表中取出第一个IO请求的位置(vring_desc第0行)，从vring_desc表的第0行开始获取IO请求，若flags为NEXT则根据next继续往下寻找；若flags为~NEXT，则表示这个IO请求已经结束。QEMU将这个IO请求封装，发送硬件执行。

更新vring_used表，将从vring_desc取出的IO请求的链表的头结点位置存到vring_used->idx所指向的位置，并将idx加1。

这样当IO处理返回到虚拟机时，virtio驱动程序可以更具vring_uesd表中的信息释放vring_desc表的相应表项。