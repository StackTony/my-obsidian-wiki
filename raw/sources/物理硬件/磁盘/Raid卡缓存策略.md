原文： [https://blog.csdn.net/u014686399/article/details/71122880](https://blog.csdn.net/u014686399/article/details/71122880)


关于raid卡的写策略有两种write-through和write-back，如下图（Dell R730）

**![](https://img-blog.csdn.net/20170503140657215?watermark/2/text/aHR0cDovL2Jsb2cuY3Nkbi5uZXQvdTAxNDY4NjM5OQ==/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70/gravity/Center)**

**write-through**

数据在写入存储的同时，要写入缓存，这种方式安全但是会牺牲写性能，因为只有等数据完全落入硬盘后，才算是一次io完成，这个过程会造成cpu的iowait。

**write-back**

数据直接写入缓存，写缓存的速度是远远大于写磁盘的，所以这种方式可以提高服务器的写性能。也许你会想当断电了怎么办？不用担心，raid卡是有电池的，完全可以支持缓存中的数据再写入磁盘。除非点背，raid卡电池也没电了。（具体什么时候缓存中的数据会写入硬盘，这个我不是很清楚）

我们生产环境用的就是**write-back** ，就是并且还设置了**force write-back  (即使电池没电了，也要写缓存)，** 这样有了点冒险，但是大幅度的提高了写性能，我觉得利大于弊吧。具体的设置如下图：

（1）重启机器,按crtl+R，进入配置页面

 ![](https://img-blog.csdn.net/20170503141239546?watermark/2/text/aHR0cDovL2Jsb2cuY3Nkbi5uZXQvdTAxNDY4NjM5OQ==/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70/gravity/Center)

（2）在上图位置处，按F2,进入下图：

 ![](https://img-blog.csdn.net/20170503141304844?watermark/2/text/aHR0cDovL2Jsb2cuY3Nkbi5uZXQvdTAxNDY4NjM5OQ==/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70/gravity/Center)

（3）在上图位置，按回车，就看到设置页面了

![](https://img-blog.csdn.net/20170503141348173?watermark/2/text/aHR0cDovL2Jsb2cuY3Nkbi5uZXQvdTAxNDY4NjM5OQ==/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70/gravity/Center)

顺便说说图中的 read policy 和Disk cache Policy 

read policy 说的是raid卡的 缓存 策略，他有三个选项（No-Read-Ahead（非预读）、Read-ahead（预读）或Adaptive（自适应）），也就是是否提前加载数据到缓存，加速顺序读请求，其中自适应策略是说如果最近两次的磁盘访问都落在了连续的扇区内那就采用Read-ahead,否则就采用No-Read-ahead

Disk cache Policy 指的是磁盘上的缓存，区别于raid卡的缓存，该项SAS和SATA一般都是关的,因为掉电了有可能会丢数据，ssd可以打开。