来源： https://www.cnblogs.com/sparkdev/p/9400673.html

IPC namespace 用来隔离 System V IPC 对象和 POSIX message queues。其中 System V IPC 对象包含共享内存、信号量和消息队列，笔者在《[System V IPC 之共享内存](https://www.cnblogs.com/sparkdev/p/8656898.html)》、《[System V IPC 之信号量](https://www.cnblogs.com/sparkdev/p/8692567.html)》和《[System V IPC 之消息队列](https://www.cnblogs.com/sparkdev/p/8716710.html)》三篇博文中对它们分别进行过介绍。本文我们将通过 demo 演示如何通过 IPC namespace 对 IPC 资源进行隔离，本文的演示环境为 ubuntu 16.04。

## 操作 IPC 资源的工具

Linux 系统中默认自带了操作 IPC 资源的命令行工具，如 ipcmk、ipcs 和 ipcrm 等。我们可以使用这些工具创建、查看和删除 IPC 资源。

**ipcmk**  
ipcmk 命令用来创建 IPC资源：共享内存、信号量和消息队列。下面的命令用来创建包含 10 个信号量的信号量集：

![[952033-20180801131407596-36009387.png]]

**ipcs**  
ipcs 命令显示当前系统中 IPC 资源的信息。默认会显示所有的 IPC 资源，包括共享内存、信号量和消息队列。可以通过命令行中的选项来控制显示的资源类型，比如通过应用 -s 选项，下面的命令只显示系统中 IPC 信号量的信息：

![[952033-20180801131452541-990815740.png]]

**ipcrm**  
ipcrm 命令用来删除系统中的 IPC 资源，此时必须指定资源的类型和标识。比如删除我们刚才创建的 IPC 信号量集：

![[952033-20180801131535214-136255079.png]]

## 与 namespace 相关的工具

**unshare 命令**  
unshare 命令把当前进程加入到一个新建的 namespace 中，然后运行指定的程序(不指定目标程序则运行系统的默认 shell)。在前文《[Linux Namespace: UTS](https://www.cnblogs.com/sparkdev/p/9377072.html)》中我们介绍了一些与 namespace 相关的 API，比如 unshare 函数。unshare 函数的功能是把当前进程加入到一个新建的 namespace 中。比起我们自己写的小 demo，系统工具中已经内置了 unshare 命令行工具，本文将使用系统中的 unshare 命令进行相关的演示。对 unshare 命令的实现感兴趣的朋友可以参考其源代码，它也是通过调用 unshare 函数实现的。  
下面的例子就是通过 unshare 命令让新建的 bash 进程属于新的 IPC namespace：

![[952033-20180801131626552-162600935.png]]

**nsenter 命令**  
nsenter 命令把当前进程加入到指定进程的 namespace 中，然后运行指定的程序(不指定目标程序则运行系统的默认 shell)。其实这个命令的核心功能也是通过我们在前文《[Linux Namespace: UTS](https://www.cnblogs.com/sparkdev/p/9377072.html)》中介绍的 setns 函数实现的。这个命令和 unshare 命令一样，也属于 linux 的 sys-utiles 工具，对其实现感兴趣的朋友可以参考其源代码。  
我们接上面的例子，使用 nsenter 命令把一个 bash 进程加入到 4956 号进程的 IPC namespace 中：

![[952033-20180801131714715-2033943375.png]]

此时当前 bash 进程的 IPC namespace 已经和 4956 号进程的 IPC namespace 是同一个了。

## 演示 IPC namespace 隔离

接下来让我们通过 IPC 信号量的隔离来了解如何隔离 IPC namespace。

**首先**我们打开两个 bash shell，为了方便区分，分别把它们称为为 shell1 和 shell2。先在 shell2 中执行 sudo unshare -i，然后分别执行 readlink /proc/\$\$/ns/ipc 命令：

![[952033-20180801131817612-952566636.png]]

图中左侧为 shell1，右侧为 shell2。可以看出它们的 IPC namespace 是不同的。

**然后**我们在 shell2 中创建 IPC 信号量集，并分别在两个 shell 中进行查看：

![[952033-20180801131858851-404043548.png]]

结果显示，shell1 中不能观察到 shell2 中创建的 IPC 信号量集，这是因为 shell1 和 shell2 此时分别在不同的 IPC namespace 中。

**接下来**我们在 shell1 中启动一个新的 bash 进程，并通过 nsenter 命令把它加入到 shell2 的 IPC namespace 中，然后再次查看 IPC 信号量信息：

![[952033-20180801131947519-211472505.png]]

这次 shell1 中显示的信号量信息和 shell2 中是一样的。

**最后**让我们看看此时 shell1 和 shell2 中当前进程的 IPC namespace：

![[952033-20180801132026372-1529796633.png]]

此时这两个进程属于同一个 IPC namespace，这才是他们可以看到相同的 IPC 资源的根本原因。

## 总结

总体来看，在我们了解了 linux namespace 的一些基本概念后，IPC namespace 隔离的观察和理解还是比较简单的。下篇我们将介绍  Mount namespace 的相关内容。

**参考：**  
[Linux Namespace系列（03）：IPC namespace (CLONE_NEWIPC)](https://segmentfault.com/a/1190000006908729)  
[Namespaces man page](http://man7.org/linux/man-pages/man7/namespaces.7.html)  
[Ipcmk man page](http://man7.org/linux/man-pages/man1/ipcmk.1.html)  
[Ipcs man page](http://man7.org/linux/man-pages/man1/ipcs.1.html)  
[Ipcrm man page](http://man7.org/linux/man-pages/man1/ipcrm.1.html)  
[Unshare man page](http://man7.org/linux/man-pages/man1/unshare.1.html)  
[Nsenter man page](http://man7.org/linux/man-pages/man1/nsenter.1.html)