
在虚拟化平台中，QEMU进程由libvirtd服务拉起，由于QEMU初始化非常快，在启动过程中无法通过gdb直接挂载并跟踪调试QEMU初始化过程中。

通过如下方法可以调试QEMU进程初始化流程：
1) 使用gdb attach libvirtd服务，命令如下：gdb attach $(cat /var/run/libvirtd.pid)
2) 在gdb中使用如下方法在virCommandSetPreExecHook函数中打断点。
(gdb) break virCommandSetPreExecHook
(gdb) cont
3) 使用virsh 命令启动需要调试的QEMU进程对应的虚拟机。
 `virsh start $GUESTNAME`
 4) 启动过程中触发断点，执行如下gdb命令：
(gdb) break main
(gdb) handle SIGKILL nopass noprint nostop
Signal        Stop	Print	Pass to program	Description
SIGKILL       No	No	No		Killed
(gdb) handle SIGTERM nopass noprint nostop
Signal        Stop	Print	Pass to program	Description
SIGTERM       No	No	No		Terminated
(gdb) set follow-fork-mode child
(gdb) cont
process 3020 is executing new program: /usr/bin/qemu-kvm
[Thread debugging using libthread_db enabled]
[Switching to Thread 0x7f2a4064c700 (LWP 3020)]
Breakpoint 2, main (argc=38, argv=0x7fff71f85af8, envp=0x7fff71f85c30)
at /usr/src/debug/qemu-kvm-0.14.0/vl.c:1968
1968	{
(gdb) 
cont之后进入QEMU的main函数，可以开始调试QEMU进程的初始化流程。