**查询内存分配详情：**
使用<span style='font-weight:bold;color:#E03E2D'>dmesg</span>命令进行查看
\[root@localhost ~\]# dmesg \| grep Memory  
\[ 0.000000\] Memory: 3848740k/5242880k available (7792k kernel code, 1049480k absent, 344660k reserved, 5950k data, 1984k init)  
\[ 0.182945\] x86/mm: Memory block size: 128MB
实际总内存为5242880KB，其中可用内存为3848740KB，absent 1049480KB，reserved 344660KB。


kdump使用kexec引导到第二个内核（捕获内核），第二个内核位于第一​​个内核无法访问的系统内存的reserved部分中，第二个内核捕获崩溃的内核内存的内容（崩溃转储）并保存，且reserved内存属于第二内核，并且永远不会被释放或交换。

系统可用内存的计算方式为：
available = 物理内存 – absent – reserved
