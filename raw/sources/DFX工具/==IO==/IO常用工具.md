### 1. iostat工具使用
iostat主要用来显示磁盘使用率，io时延等信息
`iostat -dmx 1 5 /dev/sda /dev/sdb`（1代表每隔1s刷新一次，5代表总共显示5次，/dev/sdx代表要显示的盘符）
 
需要关注的iostat输出项主要有：
−r/s：采集周期内平均每秒读IO请求个数。
−w/s：采集周期内平均每秒写IO请求个数。
−avgqu-sz：采集周期内平均请求队列的长度。
−await：采集周期内平均每次请求的等待时间，单位ms。r_await与w_await非别对应每次读、写请求的平均等待时间，单位也是ms。
−svctm：采集周期内平均每次请求的服务时间，单位ms。
−%util：设备利用率，百分比。
 
分析IO统计信息。主要分析方法如下：
1）如果util很高，例如等于或者接近100，表明磁盘设备能力趋于饱和。此时如果svctm较大，例如大于5ms时，表明磁盘设备读写性能存在瓶颈，需要联系存储及硬件同事分析处理。
2）如果r/s或者w/s较大，例如每秒达到几百个请求，但svctm较小，例如小于5ms时，表明磁盘设备正常。此时如果avgqu-sz较大且await远大于svctm，例如await值是svctm的几倍甚至几十倍，则表明虽然磁盘设备正常，但是用户业务IO请求较多，IO请求队列过长导致系统无法及时处理。此时需要优化虚拟机内部业务降低IO压力。
3）如果r/s或者w/s较大，但svctm较小，await等于或者接近svctm，则正常。
4）相同业务测试模型下，例如业务IO请求块大小相同的情况下，svctm越小存储性能越好。在IO密集型业务场景下，例如数据库IO测试，svctm值仅降低0.1ms就可能大幅改善性能测试结果。
 
### 2. fio工具使用
fio工具主要用来测试随机读写加压使用
100%随机读：
`./fio -filename=/opt/testio -direct=1 -iodepth 1 -thread -rw=randread -ioengine=psync -bs=8k -size=10G -numjobs=50 -runtime=60 -group_reporting -name=rand_100read_8k`
100%随机写：
`./fio -filename=/opt/testio -direct=1 -iodepth 1 -thread -rw=randwrite -ioengine=psync -bs=8k -size=10G -numjobs=50 -runtime=60 -group_reporting -name=rand_100write_8k`
100%顺序读：
`./fio -filename=/opt/testio -direct=1 -iodepth 1 -thread -rw=read -ioengine=psync -bs=8k -size=10G -numjobs=50 -runtime=60 -group_reporting -name=seq_100read_8k`
100%顺序写：
`./fio -filename=/opt/testio -direct=1 -iodepth 1 -thread -rw=write -ioengine=psync -bs=8k -size=10G -numjobs=50 -runtime=60 -group_reporting -name=seq_100write_8k`
 
### 3. dd工具使用
dd命令主要用来测试读写速率或进行数据拷贝使用
读裸盘：`dd if=/dev/sda of=/dev/null bs=5M count=10 iflag=direct`
写裸盘：`dd if=/dev/zero of=/dev/sda bs=10M count=5 oflag=direct`（不建议，容易写坏数据）
写盘上的文件：`dd if=/dev/zero of=/tmp/tmp.log bs=10M count=5 oflag=direct` （推荐使用）
 
### 4. iotop工具使用
 
### 5. blktrace工具使用
它能记录I/O所经历的各个步骤，从中可以分析是IO Scheduler慢还是硬件响应慢，同时几个参数可以看到处理的io的块大小。
其他参考博客：
（若出现Invalid argument的报错，需要先执行`echo $$ >> /sys/fs/cgroup/cpuset/cgroup.procs`） https://www.hikunpeng.com/document/detail/zh/perftuning/tuningtip/kunpengtuning_12_0036.html
 
### 6. 存储IO DFX使用
整个IO的流程可以分为block层和scsi层：
1）block层我们使用block_dump来作为日志的记录开关，用echo 1/0 > /proc/sys/vm/block_dump 的情况下会打开/关闭block层的日志打印开关
2）scsi层我们使用了SCSI_LOG_MLQUEUE宏来作为日志记录的开关，用scsi_logging_level -s --mlqueue=5/0可以打开scsi中层相关的日志打印开关