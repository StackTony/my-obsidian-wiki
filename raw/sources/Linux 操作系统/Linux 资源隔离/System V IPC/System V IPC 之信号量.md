本文继《[System V IPC 之共享内存](http://www.cnblogs.com/sparkdev/p/8656898.html)》之后接着介绍 System V IPC 的信号量编程。在开始正式的内容前让我们先概要的了解一下 Linux 中信号量的分类。

## 信号量的分类

在学习 IPC 信号量之前，让我们先来了解一下 Linux 提供两类信号量：

- 内核信号量，由内核控制路径使用。
- 用户态进程使用的信号量，这种信号量又分为 POSIX 信号量和 System V 信号量。

**POSIX 信号量与 System V 信号量的区别如下：**

- 对 POSIX 来说，信号量是个非负整数，常用于线程间同步。而 System V 信号量则是一个或多个信号量的集合，它对应的是一个信号量结构体，这个结构体是为 System V IPC 服务的，信号量只不过是它的一部分，常用于进程间同步。
- POSIX 信号量的引用头文件是 "<semaphore.h>"，而 System V 信号量的引用头文件是 "<sys/sem.h>"。
- 从使用的角度，System V 信号量的使用比较复杂，而 POSIX 信号量使用起来相对简单。

**本文介绍 System V 信号量编程的基本内容。**

## System V IPC 信号量

信号量是一种用于对多个进程访问共享资源进行控制的机制。共享资源通常可以分为两大类：

- 互斥共享资源，即任一时刻只允许一个进程访问该资源
- 同步共享资源，即同一时刻允许多个进程访问该资源

信号量是为了**解决互斥共享资源的同步问题**而引入的机制。信号量的实质是整数计数器，其中**记录了可供访问的共享资源的单元个数**。本文接下来提到的信号量都特指 System V IPC 信号量。

当有进程要求使用某一资源时，系统首先要检测该资源的信号量，如果该资源的信号量的值大于 0，则进程可以使用这一资源，同时信号量的值减 1。进程对资源访问结束时，信号量的值加 1。如果该资源信号量的值等于 0，则进程休眠，直至信号量的值大于 0 时进程被唤醒，访问该资源。  
信号量中一种常见的形式是双态信号量。双态信号量对应于只有一个可供访问单元的互斥共享资源，它的初始值被设置为 1，任一时刻至多只允许一个进程对资源进行访问。  
信号量用于实现对任意资源的锁定机制。它可以用来同步对任何共享资源的访问。

## 相关数据结构

System V 子系统提供的信号量机制是比较复杂的。我们不能单独定义一个信号量，而只能定义一个信号量集，其中包括一组信号量，同一信号量集中的信号量可以使用同一 ID 引用。每个信号量集都有一个与其相对应的结构，其中包含了信号量集的各种信息，该结构的声明如下：

```c
struct semid_ds
{
        struct ipc_perm sem_perm;
        struct sem *sem_base;
        ushort sem_nsems;
        time_t sem_otime;
        time_t sem_ctime;
};
```

下面简单介绍一下 semid_ds 结构中字段的含义。  
**sem_perm**：对应于该信号量集的 ipc_perm 结构(该结构的详情请参考《System V IPC 之内存共享》)指针。  
**sem_base**：sem 结构指针，指向信号量集中第一个信号量的 sem 结构。  
**sem_nsems**：信号量集中信号量的个数。  
**sem_otime**：最近一次调用 semop 函数的时间。  
**sem_ctime**：最近一次改变该信号量集的时间。

sem 结构记录了一个信号量的信息，其声明如下：

```c
struct sem
{
        ushort semval;    /* 信号量的值 */
        pid_t sempid;    /* 最后一次返回该信号量的进程ID 号 */
        ushort semncnt;    /* 等待可利用资源出现的进程数 */
        ushort semzcnt;    /* 等待全部资源可被独占的进程数 */
};
```

## 与信号量相关的函数

**信号量集的创建与打开**  
要使用信号量，首先要创建一个信号量集，创建信号量集的函数声明如下：

```c
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/sem.h>

int semget(key_t key, int nsems, int semflg);
```

函数 semget 用于创建一个新的信号量集或打开一个已存在的信号量集。其中参数 key 表示所创建或打开的信号量集的键。参数 nsems 表示创建的信号量集中信号量的个数，此参数只在创建一个新的信号量集时有效。参数 semflg 表示调用函数的操作类型，也可用于设置信号量集的访问权限。所以调用函数 semget 的作用由参数 key 和 semflg 决定。  
当函数调用成功时，返回值为信号量的引用标识符，调用失败时，返回值为 -1。当调用 semget 函数创建一个信号量时，它相应的 semid_ds 数据结构被初始化。ipc_perm 中的各个字段被设置为相应的值，sem_nsems 被设置为 nsems 所表示的值，sem_otime 被设置为 0，sem_ctime 被设置为当前时间。

**对信号量集的操作**  
对信号量集操作的函数声明如下：

```c
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/sem.h>

int semop(int semid, struct sembuf *sops, size_t nsops);
```

参数 semid 为信号量集的引用标识符。sops 为指向 sembuf 类型的数组的指针，sembuf 结构用于指定调用 semop 函数所做的操作。sembuf 结构的定义如下：

```c
struct sembuf
{
        short sem_num;    // 要操作的信号量在信号量集里的编号
        short sem_op;
        short sem_flag;
};
```

其中，sem_num 指定要操作的信号量。sem_flag 为操作标记，与此函数相关的有 IPC_NOWAIT 和 SEM_UNDO。sem_op 用于表示所要执行的操作，相应的取值和含义如下：  
**sem_op > 0**：表示进程对资源使用完毕，交回该资源。此时信号量集的 semid_ds 结构的 sem_base.semval 将加上 sem_op 的值。若此时设置了 SEM_UNDO 位，则信号量的调整值将减去 sem_op 的绝对值。  
**sem_op = 0**：表示进程要等待，直至 sem_base.semval 变为 0。  
**sem_op < 0**：表示进程希望使用资源。此时将比较 sem_base.semval 和 sem_op 的绝对值大小。如果 sem_base.semval 大于等于 sem_op 的绝对值，说明资源足够分配给此进程，则 sem_base.semval 将减去 sem_op 的绝对值。若此时设置了 SEM_UNDO 位，则信号量的调整值将加上 sem_op 的绝对值。如果 sem_base.semval 小于 sem_op 的绝对值，表示资源不足。若设置了 IPC_NOWAIT 位，则函数出错返回，否则 semid_ds 结构中的 sem_base.semncnt 加 1，进程等待直至 sem_base.semval 大于等于 sem_op 的绝对值或该信号量被删除。  
sops 指向的数组中的每个元素表示一个操作，由于此函数是一个原子操作，一旦执行就将执行数组中所有的操作。

**信号量的控制**  
对信号量的具体控制操作是通过函数 semctl 来实现的，其声明如下：

```c
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/sem.h>

int semctl(int semid, int semnum, int cmd, union semun arg);
```

参数 semid 为信号量集的引用标识符。参数 semnum 用于指明某个特定的信号量。参数 cmd 表示调用该函数希望执行的操作。参数 arg 是一个用户自定义的联合体：

```c
union semun
{
        int val;
        struct semid_ds *buf;
        ushort *array; // cmd == SETALL，或 cmd = GETALL
};
```

此联合中各个字段的使用情况与参数 cmd 的设置有关。具体的说明如下：  
**GETALL**：获得 semid 所表示的信号量集中信号量的个数，并将该值存放在无符号短整型数组 array 中。  
**GETNCNT**：获得 semid 所表示的信号量集中的等待给定信号量锁的进程数目，即 semid_ds 结构中 sem.semncnt 的值。  
**GETPID**：获得 semid 所表示的信号量集中最后一个使用 semop 函数的进程 ID，即 semid_ds 结构中的 sem.sempid 的值。  
**GETVAL**：获得 semid 所表示的信号量集中 semunm 所指定信号量的值。  
**GETZCNT**：获得 semid 所表示的信号量集中的等待信号量成为 0 的进程数目，即 semid_ds 结构中的 sem.semncnt 的值。  
**IPC_RMID**：删除该信号量。  
**IPC_SET**：按参数 arg.buf 指向的结构中的值设置该信号量对应的 semid_ds 结构。只有有效用户 ID 和信号量的所有者 ID 或创建者 ID 相同的用户进程，以及超级用户进程可以执行这一操作。  
**IPC_STAT**：获得该信号量的 semid_ds 结构，保存在 arg.buf 指向的缓冲区。  
**SETALL**：以 arg.array 中的值设置 semid 所表示的信号量集中信号量的个数。  
**SETVAL**：设置 semid 所表示的信号量集中 semnum 所指定信号量的值。

## 应用信号量的 demo

下面我们通过一个 demo 来看看如何在程序中使用信号量。这是一个通过共享内存进行进行进程间通信的例子：

```c
#include <sys/types.h>
#include <sys/sem.h>
#include <sys/shm.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include <signal.h>
#define SHMDATASIZE 1000
#define SN_EMPTY 0
#define SN_FULL 1
int deleteSemid = 0;

void server(void);
void client(int shmid, int semid);
void delete(void);
void sigdelete(int signum);
void locksem(int signum, int semnum);
void unlocksem(int semid, int semnum);
void clientwrite(int shmid, int semid, char *buffer);
union semun
{
    int val;
    struct semid_ds *buf;
    ushort *array;
};
int safesemget(key_t key, int nssems, int semflg);
int safesemctl(int semid, int semunm, int cmd, union semun arg);
int safesemop(int semid, struct sembuf *sops, unsigned nsops);
int safeshmget(key_t key, int size, int shmflg);
void *safeshmat(int shmid, const void *shmaddr, int shmflg);
int safeshmctl(int shmid, int cmd, struct shmid_ds *buf);

int main(int argc, char *argv[ ])
{
    if(argc < 3){
        server();
    }
    else{
        client(atoi(argv[1]), atoi(argv[2]));
    }
    return 0;
}

void server(void)
{
    union semun sunion;
    int semid, shmid;
    char *buffer;
    semid = safesemget(IPC_PRIVATE, 2, SHM_R|SHM_W);
    deleteSemid = semid;
    // 在服务器端程序退出时删除掉信号量集。
    atexit(&delete);
    signal(SIGINT, &sigdelete);
    // 把第一个信号量设置为 1，第二个信号量设置为 0,
    // 这样来控制：必须在客户端程序把数据写入共享内存后服务器端程序才能去读共享内存
    sunion.val = 1;
    safesemctl(semid, SN_EMPTY, SETVAL, sunion);
    sunion.val = 0;
    safesemctl(semid, SN_FULL, SETVAL, sunion);
    shmid = safeshmget(IPC_PRIVATE, SHMDATASIZE, IPC_CREAT|SHM_R|SHM_W);
    buffer = safeshmat(shmid, 0, 0);
    safeshmctl(shmid, IPC_RMID, NULL);
    // 打印共享内存 ID 和 信号量集 ID，客户端程序需要用它们作为参数
    printf("Server is running with SHM id ** %d**\n", shmid);
    printf("Server is running with SEM id ** %d**\n", semid);
    while(1)
    {
        printf("Waiting until full...");
        fflush(stdout);
        locksem(semid, SN_FULL);
        printf("done.\n");
        printf("Message received: %s.\n", buffer);
        unlocksem(semid, SN_EMPTY);
    }
}

void client(int shmid, int semid)
{
    char *buffer;
    buffer = safeshmat(shmid, 0, 0);
    printf("Client operational: shm id is %d, sem id is %d\n", shmid, semid);
    while(1)
    {
        char input[3];
        printf("\n\nMenu\n1.Send a message\n");
        printf("2.Exit\n");
        fgets(input, sizeof(input), stdin);
        switch(input[0])
        {
            case '1':
                clientwrite(shmid, semid, buffer);
                break;
            case '2':
                exit(0);
                break;
        }
    }
}
…

void locksem(int semid, int semnum)
{
    struct sembuf sb;
    sb.sem_num = semnum;
    sb.sem_op = -1;
    sb.sem_flg = SEM_UNDO;
    safesemop(semid, &sb, 1);
}

void unlocksem(int semid, int semnum)
{
    struct sembuf sb;
    sb.sem_num = semnum;
    sb.sem_op = 1;
    sb.sem_flg = SEM_UNDO;
    safesemop(semid, &sb, 1);
}
…

```

由于完整的 demo 代码比较长，这里仅贴出来了程序的主干，完整的程序请访问[这里](https://github.com/sparkdevo/linuxipc/blob/master/semaphore/sem.c)。  
把程序代码保存到文件 sem.c 文件中，并编译：

$ gcc -Wall sem.c -o sem_demo

先不传递参数运行服务器端程序：

然后再启动一个终端运行客户端程序，并把服务器端输出的 SHM id 和 SEM id 作为参数传入到客户端程序中：

$ sudo ./sem_demo 2064397 131072

![](https://images2018.cnblogs.com/blog/952033/201804/952033-20180402131247407-1986620549.png)

服务器端(左侧窗口)程序会等待客户端(右侧窗口)程序的输入，并按照顺序把客户端中的输入在服务器端输出。服务器端程序和客户端程序通过信号量来控制对共享内存的访问，从而实现进程间数据的同步(具体的实现请参考代码)。  
接着我们通过下面的命令查看系统中的 IPC 信号量：

![](https://images2018.cnblogs.com/blog/952033/201804/952033-20180402131308762-111707038.png)

这就是服务器与客户端程序用来实现同步机制的信号量集！在我们的 demo 中，当服务器端程序退出时会删除掉这个信号量集，以免给系统添加垃圾。

## 总结

我们在《[System V IPC 之共享内存](http://www.cnblogs.com/sparkdev/p/8656898.html)》一文中写了一个很简陋的应用共享内存的 demo，由于没有应用任何的同步访问技术，其输出是比较混乱的。本文的 demo 则是在其基础上添加了信号量来控制进程对共享内存的访问。从程序的输出我们可以看到，使用信号量解决互斥共享资源的同步问题后，服务器端程序的输出变得和客户端的输入一致了。

**参考：**  
《深入理解 Linux 内核》  
《Linux 环境下 C 编程指南》
