IPC 是**进程间通信(Interprocess Communication)**的缩写，通常指允许用户态进程执行系列操作的一组机制：

- 通过信号量与其他进程进行同步
- 向其他进程发送消息或者从其他进程接收消息
- 和其他进程共享一段内存区

System V IPC 最初是在一个名为 "Columbus Unix" 的开发版 Unix 变种中引入的，之后在 AT&T 的 System III 中采用。现在在大部分 Unix 系统 (包括 Linux) 中都可以找到。

IPC 资源包含**信号量**、**消息队列**和**共享内存**三种。IPC 的数据结构是在进程请求 IPC 资源时动态创建的。每个 IPC 资源都是持久的：除非被进程显式地释放，否则永远驻留在内存中(直到系统关闭)。IPC 资源可以由任一进程使用，包括那些不共享祖先进程所创建的资源的进程。  
由于一个进程可能需要同类型的多个 IPC 资源，因此每个新资源都是使用一个 32 位的 IPC 关键字来标识的，这和系统的目录树中的文件路径名类似。每个 IPC 资源都有一个 32 位的 IPC 标识符，这与和打开文件相关的文件描述符有些类似。IPC 标识符由内核分配给 IPC 资源，在系统内部是唯一的，而 IPC 关键字可以由程序员自由地选择。  
当两个或者更多的进程要通过一个 IPC 资源进行通信时，这些进程都要引用该资源的 IPC 标识符。

**共享内存是进程间通信的一种最基本、最快速的机制。**共享内存是两个或多个进程共享同一块内存区域，并通过该内存区域实现数据交换的进程间通信机制。通常是由一个进程开辟一块共享内存区域，然后允许多个进程对此区域进行访问。由于不需要使用中间介质，而是数据由内存直接映射到进程空间，因此共享内存是最快速的进程间通信机制。  
使用共享内存有两种方法：映射 /dev/mem 设备和内存映像文件。本文主要通过 demo 演示通过映射 /dev/mem 设备实现共享内存的方法。

共享内存的最大不足之处在于，由于多个进程对同一块内存区具有访问的权限，各个进程之间的同步问题显得尤为突出。必须控制同一时刻只有一个进程对共享内存区域写入数据，否则将造成数据的混乱。同步控制的问题，笔者将在随后的文章中介绍如何通过信号量解决。

## 共享内存相关的数据结构

**ipc_perm 结构**

对于每一个进程间通信机制的对象，都有一个 ipc_perm 结构与之相对应，该结构的定义如下：

```c
struct ipc_perm
{
    uid_t uid;
    gid_t gid;
    uid_t cuid;
    gid_t cgid;
    mode_t mode;
    ulong seq;
    key_t key;
}
```

该结构用于记录对象的各种相关信息，各个字段的具体含义如下：  
**uid**：所有者的有效用户 ID。  
**gid**：所有者的有效组 ID。  
**cuid**：创建者的有效用户 ID。  
**cgid**：创建者的有效组 ID。  
**mode**：表示此对象的访问权限。  
**seq**：对象的应用序号。  
**key**：对象的键。

**shmid_ds 结构**

每个共享内存都有与之相对应的 shmid_ds 结构，其定义如下：

```c
struct shmid_ds
{
    struct ipc_perm shm_perm;
    int shm_segsz;
    pid_t shm_cpid;
    pid_t shm_lpid;
    ulong shm_nattch;
    time_t shm_atime;
    time_t shm_dtiem;
    time_t shm_ctime;
}
```

此机构记录了一个共享内存的各种属性，该结构的各个字段的含义如下：  
**shm_perm**：对应于该共享内存的 ipc_perm 结构。  
**shm_segsz**：以字节表示的共享内存区域的大小。  
**shm_lpid**：最近一次调用 shmop 函数的进程 ID。  
**shm_cpid**：创建该共享内存的进程 ID。  
**shm_nattch**：当前使用该共享内存区域的进程数。  
**shm_atime**：最近一次附加操作的时间。  
**shm_dtime**：最近一次分离操作的时间。  
**shm_ctime**：最近一次改变的时间。

## 操作共享内存的函数

**创建或打开共享内存**

要使用共享内存，首先要创建一个共享内存区域，创建共享内存区域的函数声明如下：

```c
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/shm.h>

int shmget(key_t key, size_t size, int flg);
```

函数 shmget 除了可用于创建一个新的共享内存外，也可用于打开一个已存在的共享内存。其中，参数 key 表示所创建或打开的共享内存的键。参数 size 表示共享内存区域的大小，只在创建一个新的共享内存时生效。参数 flag 表示调用函数的操作类型，也可用于设置共享内存的访问权限。  
当函数调用成功时，返回值为共享内存的引用标识符；调用失败时，返回值为 -1。

**附加共享内存**

当一个共享内存创建或打开后，某个进程如果要使用该共享内存，则必须将这个共享内存区域附加到它的地址空间中。附加操作的函数声明如下：

```c
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/shm.h>

void *shmat(int shmid, const void *shmaddr, int flag);
```

参数 shmid 表示要附加的共享内存区域的引用标识符。参数 shmaddr 和 flag 共通决定共享内存区域要附加到的地址值。比如设置 shmaddr 为 0 时，系统将自动查找进程地址空间，将共享内存区域附加到第一块有效内存区域上，此时 flag 参数无效。  
当函数调用成功时，返回值为指向共享内存区域的指针；调用失败时，返回值为 -1。

**分离共享内存**

当一个进程对共享内存区域的访问完成后，可以调用 shmdt 函数使共享内存区域与该进程的地址空间分离，shmdt 函数的声明如下：

```c
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/shm.h>

int shmdt(const void *shmaddr);
```

此函数仅用于将共享内存区域与进程的地址空间分离，并不删除共享内存本身。参数 shmaddr 为指向要分离的共享内存区域的指针(就是调用 shmat 函数的返回值)。该函数调用成功时返回 0；调用失败时返回 -1。

**共享内存的控制**

对共享内存区域的具体控制操作是通过函数 shmctl 来实现的，shmctl 函数的声明如下：

```c
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/shm.h>

int shmctl(int shmid, int cmd, struct shmid_ds *buf);
```

参数 shmid 为共享内存的引用标识符。参数 cmd 表示调用该函数希望执行的操作。参数 buf 是指向 shmid_ds 结构体的指针。参数 cmd 的取值和对应的操作如下：  
**SHM_LOCK**：将共享内存区域上锁。  
**IPC_RMID**：用于删除共享内存。  
**IPC_SET**：按参数 buf 指向的结构中的值设置该共享内存对应的 shmid_ds 结构。  
**IPC_STAT**：用于取得该共享内存区域的 shmid_ds 结构，保存到 buf 指向的缓冲区。  
**SHM_UNLOCK**：将上锁的共享内存区域释放。

## 进程间通过共享内存通信的 demo

下面我们创建两个程序 demoa 和 demob 来简单的演示进程间如何通过共享内存通信。其中 demoa 的代码如下：

```c
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <stdio.h>
#include <stdlib.h>

#define BUF_SIZE 1024
#define MYKEY 24

int main(void)
{
    int shmid;
    char *shmptr;
    // 创建或打开内存共享区域
    if((shmid=shmget(MYKEY,BUF_SIZE,IPC_CREAT))==-1){
        printf("shmget error!\n");
        exit(1);
    }
    if((shmptr=shmat(shmid,0,0))==(void*)-1){
        printf("shmat error!\n");
        exit(1);
    }
    while(1){
        // 把用户的输入存到共享内存区域中
        printf("input:");
        scanf("%s",shmptr);
    }
    exit(0);
}
```

demoa 程序创建或打开 key 为 24 的共享内存区域，并把用户输入的字符串存入这个共享内存区域。把上面的代码保存到文件 shm_a.c 文件中，并用下面的命令编译：

$ gcc -Wall shm_a.c -o demoa

下面是 demob 的代码：

```c
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#define BUF_SIZE 1024
#define MYKEY 24

int main(void)
{
    int shmid;
    char *shmptr;
    // 创建或打开内存共享区域
    if((shmid=shmget(MYKEY,BUF_SIZE,IPC_CREAT))==-1){
        printf("shmget error!\n");
        exit(1);
    }
    if((shmptr=shmat(shmid,0,0))==(void*)-1){
        fprintf(stderr,"shmat error!\n");
        exit(1);
    }
    while(1){
        // 每隔 3 秒从共享内存中取一次数据并打印到控制台
        printf("string:%s\n",shmptr);
        sleep(3);
    }
    exit(0);
}
```

demob 程序创建或打开 key 为 24 的共享内存区域，然后每隔 3 秒从共享内存中取一次数据并打印到控制台。这样通过共享内存程序 demob 就可以获取到 demoa 程序中的数据。 把上面的代码保存到文件 shm_b.c 文件中，并用下面的命令编译：

$ gcc -Wall shm_b.c -o demob

接下来分别运行 demoa 和 demob，然后尝试在 demoa 中输入一些字符串：

![[952033-20180327131347844-1324002360.png]]

demob 完全不关心 demoa 在干什么，只是机械的每隔 3 秒钟去共享内存中取一次数据，取到什么就输出什么。

## 管理 ipc 资源的基本命令

我们在 demoa 和 demob 中并没有通过 shmctl 函数在适当的时机删除创建的共享内存区域，所以当程序 demoa 和 demob 退出后，我们创建的 key 为 24 的共享内存区域仍然驻留在系统的内存中。  
Linux 系统默认自带了一些管理 ipc 资源的基本命令，比如 **ipcs**、**ipcmk** 和 **ipcrm**。我们可以使用 ipcs 命令查看系统中的 ipc 资源：

![[952033-20180327131507474-463459409.png]]

红框中的共享内存就是我们的 demo 程序创建的，第一列的 key 0x18 换算成十进制就是 24。  
现在我们已经不需要这个共享内存区域了，所以可以使用下面的命令把它删除掉：

当然，除了删除 ipc 资源，我们还可以通过 ipcmk 命令创建 ipc 资源。关于 ipcs、ipcmk 和 kpcrm 这三个命令的具体用法请参考相关的 man page，此文不再赘述。

## 总结

本文简单的介绍了 IPC 相关的基本概念和共享内存编程中的一些结构与函数。并通过一个简单的 demo 演示了共享内存工作的基本原理。由于 demo 中没有采取任何同步技术，demob 的输出就显得有些杂乱无章。在接下来介绍信号量的文章中，我们会在 demo 中通过信号量来同步共享内存的访问。

**参考：**  
《深入理解 Linux 内核》  
《Linux 环境下 C 编程指南》
