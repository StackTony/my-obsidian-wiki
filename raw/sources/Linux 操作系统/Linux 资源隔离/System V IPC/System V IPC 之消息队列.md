消息队列和共享内存、信号量一样，同属 System V IPC 通信机制。消息队列是一系列连续排列的消息，保存在内核中，通过消息队列的引用标识符来访问。使用消息队列的好处是对每个消息指定了特定消息类型，接收消息的进程可以请求接收下一条消息，也可以请求接收下一条特定类型的消息。

## 相关数据结构

与其他两个 System V IPC 通信机制一样，消息队列也有一个与之对应的结构，该结构的定义如下：

```c
struct msqid_ds
{
    struct ipc_perm msq_perm;
    struct msg *msg_first;
    struct msg *msg_last;
    ulong msg_ctypes;
    ulong msg_qnum;
    ulong msg_qbytes;
    pid_t msg_lspid;
    pid_t msg_lrpid;
    time_t msg_stime;
    time_t msg_rtime;
    time_t msg_ctime;
}
```

该结构中各个字段的说明如下。  
**msg_perm**：对应于该消息队列的 ipc_perm 结构指针。  
**msg_first**：msg 结构指针，msg 结构用于表示一个消息，此指针指向消息队列中的第一个消息。  
**msg_last**：msg 结构指针，指向消息队列中的最后一个消息。  
**msg_ctypes**：记录消息队列中当前的总字节数。  
**msg_qnum**：记录消息队列中当前的总消息数。  
**msg_qbytes**：记录消息队列中最大可容纳的字节数。  
**msg_lspid**：最近一个执行 msgsnd 函数的进程的 PID。  
**msg_lrpid**：最近一个执行 msgrcv 函数的进程的 PID。  
**msg_stime**：最近一次执行 msgsnd 函数的时间。  
**msg_rtime**：最近一次执行 msgrcv 函数的时间。  
**msg_ctime**：最近一次改变该消息队列的时间。  
消息队列所传递的消息由两部分组成，即消息的类型及所传递的数据。一般用一个结构体来表示。通常消息类型用一个正的长整数表示，而数据则根据需要设定。比如设定一个传递 1024 个字节长度的字符串数据的消息如下：

```c
struct msgbuf
{
    long msgtype;
    char msgtext[1024];
}
```

传递消息时将所传递的数据内容写入 msgtext 中，然后把这个结构体发送到消息队列中即可。

## 消息队列相关的函数

**消息队列的创建与打开**  
要使用消息队列，首先要创建一个消息队列，创建消息队列的函数声明如下：

```c
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/msg.h>

int msgget(key_t key, int msgflg);
```

函数 msgget 用于创建或打开一个消息队列。其中，参数 key 表示所创建或打开的消息队列的键。参数 msgflg 表示调用函数的操作类型，也可用于设置消息队列的访问权限，两者通过逻辑或表示。调用函数 msgget 所执行的具体操作由参数 key 和 flag 决定。相应约定与 shmget 函数类似。  
函数调用成功时，返回值为消息队列的引用标识符。调用失败时，返回值为 -1。  
当调用 msgget 函数创建一个消息队列时，它相应的 msqid_ds 结构被初始化。Ipc_perm 中各个字段被设置为相应的值，其中 msg_qnum、msg_lspid、msg_lrpid、msg_stime 和 msg_rt 都被设置为 0，msg_qtypes 被设置为系统限制值，msg_ctime 被设置为当前时间。

**向消息队列中发送消息**  
接下来我们介绍如何向一个消息队列中发送消息，发送消息的函数声明如下：

```c
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/msg.h>

int msgsnd(int msqid, const void *msgp, size_t msgsz, int msgflg);
```

此函数的作用是向一个消息队列中发送消息。该消息将被添加到消息队列的末尾。参数 msqid 是消息队列的引用标识符。参数 msgp 是一个 void 指针，指向要发送的消息。参数 msgsz 是以字节数标识的消息数据的长度。参数 msgflg 用于指定消息队列充满时的处理方法。当消息队列充满时，如果设置了 IPC_NOWAIT 位，就立即出错返回，否则发送消息的进程被阻塞，直至消息队列中有空间或该消息队列被删除时，函数返回。  
msgsnd 函数调用成功时，返回值为 0，调用失败时，返回值为 -1。

**从消息队列中接收消息**  
进程要从消息队列中接收消息时，需要调用 msgrcv 函数，其声明如下：

```c
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/msg.h>

ssize_t msgrcv(int msqid, void *msgp, size_t msgsz, long msgtyp, int msgflg);
```

此函数用于从指定的消息队列中接收消息。参数 msqid 是消息队列的引用标识符。参数 msgp 是一个 void 指针，接收到的消息将被存放在 msgp 所指向的缓冲区。参数 msgsz 是以字节数表示的要接收的消息的长度。当消息的实际长度大于这个值时，将根据 msgflg 的设置做出相应的处理。参数 msgtyp 用于表示要接收的消息的类型，其取值和含义如下：  
**msgtyp=0**    接收消息队列中的第一条消息  
**msgtyp>0**    接收消息队列中类型值等于 msgtyp 的第一条消息  
**msgtyp<0**    接收消息队列中类型值小于等于 msgtyp 的绝对值的所有消息类型值最小的消息中的第一条消息  
参数 msgflg 用于设定与接收消息相关的信息。  
**IPC_NOWAIT**：指定 msgtyp 无效时的处理方法。当 msgtyp 无效时，如果 IPC_NOWAIT 被设置，则立即出错返回，否则接收消息的进程将被阻塞，直至 msgtyp 有效或该消息队列被删除。  
**MSG_NOERROR**：用于设置消息长度大于 msgsz 时的处理方法。当消息长度大于 msgsz 时，如果 MSG_NOERROR 位被设置，则接收该消息，超出部分被截断，函数正确返回，否则不接收该消息而将其保留在消息队列中，出错返回。  
函数 msgrcv 调用成功时，返回值为以字节数表示的接收到的消息数据的长度，调用失败时，返回值为 -1。

**消息队列的控制**  
对消息队列的具体控制操作是通过函数 msgctl 来实现的，其声明如下：

```c
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/msg.h>

int msgctl(int msqid, int cmd, struct msqid_ds *buf);
```

其中，参数 msqid 为消息队列的引用标识符。参数 cmd 表示调用该函数希望执行的操作，其取值和相关说明如下。  
**IPC_RMID**：删除消息队列。此命令是立即执行的，如果还有进程对此消息队列进行操作，则出错返回。只有有效用户 ID 和消息队列的所有者 ID 或创建者 ID 相同的用户进程，以及超级用户进程可以执行这一操作。  
**IPC_SET**：按参数 buf 指向的结构中的值设置该消息队列对应的 msqid_ds 结构。只有有效用户 ID 和消息队列的所有者 ID 或创建者 ID 相同的用户进程，以及超级用户进程可以执行这一操作。  
**IPC_STAT**：获得该消息队列的 msqid_ds 结构，保存于 buf 指向的缓冲区。

## 应用消息队列的 demo

下面是一个通过消息队列进行进程间通信的 demo：

```c
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/msg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    int msgid;
    int status;
    char str1[ ]={"test message:hello!"};
    char str2[ ]={"test message:godbye!"};
    struct msgbuf
    {
        long msgtype;
        char msgtext[1024];
    }sndmsg, rcvmsg;

    if((msgid=msgget(IPC_PRIVATE,0666))==-1)
    {
        printf("msgget error!\n");
        exit(254);
    }
    sndmsg.msgtype = 111;
    sprintf(sndmsg.msgtext,"%s", str1);
    if(msgsnd(msgid,(struct msgbuf *)&sndmsg,sizeof(str1)+1,0)==-1)
    {
        printf("msgsnd error!\n");
        exit(254);
    }
    sndmsg.msgtype = 222;
    sprintf(sndmsg.msgtext, "%s", str2);
    if(msgsnd(msgid,(struct msgbuf *)&sndmsg,sizeof(str2)+1,0)==-1)
    {
        printf("msgsnd error!\n");
        exit(254);
    }
    if((status=msgrcv(msgid,(struct msgbuf *)&rcvmsg,80,222,IPC_NOWAIT))==-1)
    {
        printf("msg rcv error!\n");
        exit(254);
    }

    printf("The received message: %s.\n", rcvmsg.msgtext);
    // 下面的代码会删除消息队列，这里把它注释掉是为了使用 ipcs 命令进行观察
    // msgctl(msgid, IPC_RMID,0);
    exit(0);
}
```

简单起见，该程序自己完成了消息的发送和接收。由于我们指定了接收消息的类型，所以只有第二条消息会被接收。  
把程序代码保存到文件 msgqueue.c 中，并编译：

$ gcc -Wall msgqueue.c -o msgqueue_demo

然后运行程序：

![](https://images2018.cnblogs.com/blog/952033/201804/952033-20180404131205928-1041121929.png)

接收者只收到了类型为 222 的消息。  
由于我们注释了程序中删除消息队列的代码，所以我们还可以通过 ipcs 命令来查看程序中创建的消息队列：

![](https://images2018.cnblogs.com/blog/952033/201804/952033-20180404131236340-736839390.png)

## 总结

本文以一个极简的 demo 介绍并演示了 IPC 消息队列的基本概念和用法，对于了解 IPC 消息队列我想这些已经足够了。

**参考：**  
《Linux 环境下 C 编程指南》
