
**统计原理：**
top里的steal时间占比应该是间隔1分钟执行两次/bin/cat /proc/stat \| /usr/bin/egrep "^cpu " \| /usr/bin/head -1 取值除以总时间搞的

kvmtop里的应该是从proc里面读取dfx_debugfs_entries的数值做的计算，/sys/kernel/debug/kvm/vcpu_stat，具体需要看代码


**steal时间占比**：等待宿主机CPU资源耗费的时间（虚拟机）。代表系统运行在虚拟机中的时候，被其他虚拟机占用的CPU时间占比。
Linux的top和iostat命令，提供了Steal Time （st） 指标，用来衡量被Hypervisor偷去给其它虚拟机使用的CPU时间所占的比例，这个值越高，说明这台物理服务器的资源竞争越激烈。
**采集原理**：
通过/bin/cat /proc/stat | /usr/bin/egrep "^cpu" | /usr/bin/head -1命令取出各个字段的值。difference=total2-total1。total1为上个周期采集的CPU使用量，total2为本周期采集的CPU使用量。Steal时间占比计算为(steal2 -steal1) / difference * 100%
**命令**：iostat -c 输出steal 指标
间隔1分钟执行两次/bin/cat /proc/stat | /usr/bin/egrep "^cpu " | /usr/bin/head -1
两次steal差值  / 总CPU（所有时间相加）差值= 1分钟的平均CPU的steal时间占比
**采集周期**：1分钟
推荐自定义阈值规则超过10%告警


**CPU被抢占时间占比**：被抢占时间与CPU运行时间的比是通过kvmtop采集到的%ST值，该值为百分比，它的值表明虚拟机花了百分之多少CPU运行时间等待得到真正的CPU资源。
**采集原理**：x86的话，是从cat /var/run/sysinfo/kvmtop/kvmtop_info获取对应虚拟机的ST值，除以虚拟机CPU核数，得到虚拟机所有核的平均抢占时间，如果是CPU被抢占时间占比超过阈值告警：当虚拟机所有核的平均抢占时间连续三个周期大于等于20时，系统产生此告警，小于20，5~10分钟后告警清除；
arm的话，是使用sudo /usr/bin/kvmtop -b -n 2 -z命令获取对应虚拟机的ST值，除以虚拟机CPU核数，得到虚拟机所有核的平均抢占时间，如果是CPU被抢占时间占比超过阈值**告警**：当虚拟机所有核的平均抢占时间连续三个周期大于等于20%时，系统产生此告警，小于20，5~10分钟后告警清除；
**采集周期**：1分钟
“CPU被抢占时间占比” 默认是监控的，由虚拟机所在主机采集

**区别**：
top里的%ST关注整个物理机的cpu抢占情况；
kvmtop里的%ST关注的是虚拟机的cpu抢占情况，steal时间占比使用的是top，CPU被抢占时间占比使用的kvmtop




**实际举例：**
问题：现网虚拟机1:3超分时，当某个虚拟机的CPU完全跑满消耗掉了物理机的cpu，其他两个虚拟机是不是也会卡死了呀？

——当配置了shares字段，即使一个虚拟机满载甚至D状态了，其他虚拟机仍能获得最小保障的CPU时间片，但性能会显著下降
