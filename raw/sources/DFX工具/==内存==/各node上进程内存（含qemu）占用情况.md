
numastat -m

查看某个进程的实际虚拟内存布局
cat /proc/pid/maps 或者 pmap pid

查看 numa 各node上的进程内存占用
ps aux \| grep -v grep \|awk '{print \$2}' \|xargs numastat -p

查看虚拟机占用的numa情况可以使用命令
ps aux \| grep qemu-kvm \|grep -v grep \|awk '{print \$2}' \|xargs numastat -p
————————
**注意**：qemu进程自己（堆、栈、二进制）不受配置文件里的strict限制，strict控制的是用户空间的分配
可以通过cat /proc/\<pid\>/numa_maps \| grep -w Nxx确定内存具体的使用情况
————————

查看每个node大页使用情况
cat /proc/\*/numa_maps \| grep -i huge
