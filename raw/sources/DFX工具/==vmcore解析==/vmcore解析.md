硬件关闭**==SPCR开关==**的话会导致无法记录硬件日志，注意！！！

<span style='background:white'>crash分析指导和工具使用：</span>
<span style='background:white'>工具装好后的命令为：./crash vmcore vmlinux</span>
<span style='background:white'>安装好kernel-debuginfo包后，bt -slf可以加参数显示函数偏移，函数所在的文件和每一帧的具体内容，从而对照源码和汇编代码，查看函数入参和局部变量</span>

<span style='color:#151515'></span>
时间戳转换命令
<span style='background:white'>date -d@'xxxxx'</span>
date -d@'xxxxx' "+%Y-%m-%d %H:%M:%S"
<span style='color:#151515'></span>
<span style='color:#151515'></span>
<span style='background:white'>ps，files，mount，net等命令会输出一个地址，通过对应地址的结构体，使用struct命令，就可以看到相应结构的内容。</span>
foreach bt -c \<cpu_id\>可以看的是当前所有进程的记录
bt -a \| grep -i COMMAND \| grep -v "PID: 0" 可以看问题堆栈
dis -s + \<address\>可以分析源码里这个函数哪里来的dis -r + \<address\>可以反汇编出代码流程
rd -S +\<address\> + \<len\>查看对应地址的内存，并且尝试将地址转换为对应的符号
struct + task_struct + \<address\> 可以看进程结构体信息
kmem -p + \<address\> 可以看内存信息


汇编参考:
<https://blog.csdn.net/hzj_001/article/details/99703510>


进程相关的结构体最重要的就是task_struct和mm_struct
[[进程结构task_struct和mm_struct]]