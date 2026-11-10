#### Linux的存储IO栈：
<https://zhuanlan.zhihu.com/p/39721251>
![[Pasted image 20260424165505.png]]

![[Pasted image 20260430114122.png]]


确认下发到磁盘的io是透传还是写回模式
```
cat /sys/class/scsi_disk/0\:2\:0\:0/cache_type
```
当选用write through方式时，系统的写磁盘操作并不利用阵列卡的Cache，而是直接与磁盘进行数据的交互。 而write Back方式则利用阵列Cache作为系统与磁盘间的二传手，系统先将数据交给Cache，然后再由Cache将数据传给磁盘。

```
cat /sys/kernel/debug/block/sdX/hctx0/tags
```
这个命令可以看到busy值是否为0
busy非0代表等待IO返回，即可能存在IO阻塞。