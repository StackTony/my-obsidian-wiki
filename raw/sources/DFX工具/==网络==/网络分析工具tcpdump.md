https://blog.51cto.com/u_13053917/2430477

## 简单介绍

tcpdump是一个能够对网络上的数据包进行收集的网络分析工具，根据用户自定义条件截取数据包，具备灵活的策略，是系统管理员分析网络、排查问题的利器。tcpdump提供了源代码，有公开的接口，因此具备很强的可扩展性，它支持针对网络层、协议、主机、网络或端口的过滤，并且支持and、or、not等逻辑语句。普通用户无法执行tcpdump命令，只有具备root权限才能执行。

## 参数介绍

默认情况下启动tcpdump，将监听在第一个网络接口上所有流过的数据包  
![[e9b5575d478decedce34539c719f8b7d.png|linux工作利器之二，网络分析工具tcpdump_linux]]

tcpdump支持很多参数，往往网络中流量很大，如果不加分辨收集所有的数据包，数据量太大，不容易发现需要的数据包，使用参数定义的过滤规则收集特定的数据包，缩小目标，便于更好的分析网络中存在的问题。

**-i** 指定网络接口  
**-w** 将结果输出到文件中，通常文件以.pcap作为后缀，可以结合wirkshark分析数据  
**-n** 不把网络地址换成名字（不进行域名解析，速度更快）  
**-nn** 不进行端口名称的转换，直接以ip和端口显示  
**-v** 输出一个稍微详细的信息（例如在ip包中可以包括ttl和服务类型的信息）  
**-vv** 输出详细的报文信息  
**-c** 在收到指定的包的数目后，tcpdump就会停止，默认tcpdump需要crtl+c结束  
**-C** 后接file_size，指定-w写入文件的大小，如果超过了指定大小，则关闭当前文件，然后在打开一个新的文件， file_size 的单位是兆字节  
**-a** 将网络地址和广播地址转变成名字  
**-A** 以ASCII格式打印出所有分组，并将链路层头最小化，方便去收集web页面内容  
**-d** 将匹配信息包的代码以人们能够理解的汇编格式给出  
**-dd** 将匹配信息包的代码以c语言程序段的格式给出  
**-ddd** 将匹配信息包的代码以十进制的形式给出  
**-D** 打印出系统中所有可以用tcpdump分析的网络接口  
**-q** 快速输出，只输出较少信息  
**-e** 在输出行打印出数据链路层的头部信息  
**-f** 将外部的Internet地址以数字的形式打印出来  
**-l** 使标准输出变为缓冲行形式  
**-t** 在输出的每一行不打印时间戳  
**-tt** 在每一行中输出非格式化的时间戳  
**-ttt** 输出本行和前面一行之间的时间差  
**-F** 从指定的文件中读取表达式,忽略其它的表达式  
**-r** 从指定的文件中读取包(这些包一般通过-w选项产生)  
**-w** 直接将包写入文件中，并不分析和打印出来  
**-T** 将监听到的包直接解释为指定的类型的报文，常见的类型有rpc （远程过程调用）和snmp（简单网络管理协议）

## tcpdump表达式

格式：  
**tcpdump [option] 协议 + 传输方向 + 类型 + 具体值**  
这是一个正则表达式，满足表达式的报文会被收集。  
协议：主要包括ip、arp、rarp、tcp、udp、icmp、http，指定监听包的协议内容，如果没有指定，默认是监听所有协议的数据包  
传输方向：主要包括src、dst、dst or src、dst and src，指定传输方向，源地址或目标地址，如果没有指定，默认是src or dst  
类型：主要包括host、net、port、ip proto、protochain，指定收集的主机或网段，如果默认没有指定，默认是host  
其他关键字：gateway, broadcast,less,greate；三种逻辑运算符，取非运算 ‘not ’ ‘! ‘， 与运算’and’,’&&’，或运算 ‘or’ ,‘││’

## 使用实例

包含主机192.0.0.19的数据包

![[f91cf8c31e175a051ce9ec1b8a189f83.png|linux工作利器之二，网络分析工具tcpdump_tcpdump_02]]

包含192.0.0.0/24网段的数据包

![[9ea42d3618f7aa026645d5dd0572ce31.png|linux工作利器之二，网络分析工具tcpdump_linux_03]]

源ip是192.0.0.19的数据包和目标地址是192.0.0.19的数据包

![[3c6835a2ba4911158e9bac6f0222b706.png|linux工作利器之二，网络分析工具tcpdump_网络_04]]

9092端口的数据包

![[67774e59133806757a16cb037ab61750.png|linux工作利器之二，网络分析工具tcpdump_linux_05]]

ssh服务的数据包

![[985dde9cd8aaffe7f38d5d8ddcf6d157.png|linux工作利器之二，网络分析工具tcpdump_linux_06]]

源端口是9092的数据包，目标端口是9092的数据包

![[9a3fdd66007b0ba4bd348d4a1cdc86a4.png|linux工作利器之二，网络分析工具tcpdump_linux_07]]

tcp协议、udp协议、icmp协议的数据包

![[2b6b6418bebadad58aaf4fdfce4e2d20.png|linux工作利器之二，网络分析工具tcpdump_网络_08]]

源ip是192.0.0.19且目标端口是9092的数据包，用and

![[b13a1cd9c2e19b890ea890f4d9b27cf3.png|linux工作利器之二，网络分析工具tcpdump_linux_09]]

源ip是192.0.0.19或目标端口是9092的数据包，用or

![[082bacd2648072055784bc22eb2967f1.png|linux工作利器之二，网络分析工具tcpdump_网络_10]]

源ip是192.0.0.19且端口是9092，或源ip是192.0.0.20且目的端口不是80的数据包

![[99387423fe03b435609e20a1805ae3b2.png|linux工作利器之二，网络分析工具tcpdump_linux_11]]

流经网卡eth0的1000个数据包保存在文件backup.cap中

![[bccde64e5908720f31a7b2d37a18cd4f.png|linux工作利器之二，网络分析工具tcpdump_linux_12]]

从文件backup.cap中读取tcp协议的10个数据包

![[c68f3d6160347600083d8b7b92843c61.png|linux工作利器之二，网络分析工具tcpdump_linux_13]]

数据包类型是多播且端口不是22且协议不是icmp的数据包

![[051bfc111fd88f87973e532974b85bb8.png|linux工作利器之二，网络分析工具tcpdump_tcpdump_14]]

协议是ospf的数据包

![[9cabebefb5c9ec3575d33192e3b15f36.png|linux工作利器之二，网络分析工具tcpdump_linux_15]]

包长度大于50，小于100的数据包

![[9e00287a922e5f08a494f510fdd1859f.png|linux工作利器之二，网络分析工具tcpdump_网络_16]]

ip信息类型的数据包，ip信息类型协议可以是icmp、icmp6、igmp、igrp、pim、ah、esp、vrrp、udp、tcp

ipv6信息类型的数据包

![[715b4ab46b7aa4e50473806d725c7d55.png|linux工作利器之二，网络分析工具tcpdump_tcpdump_17]]

ether信息类型的数据包，ether信息类型协议可以是ip、ip6、arp、rarp、atalk、aarp、decnet、sca、lat、mopdl、moprc、iso、stp、ipx或netbeui

![[44812532124576268fbc57939b5f6053.png|linux工作利器之二，网络分析工具tcpdump_网络_18]]

以太网广播、多波数据包

![[3fed171f4d9635e0c31df1a6019e028e.png|linux工作利器之二，网络分析工具tcpdump_网络_19]]

ipv4广播、多波数据包

![[14909f33b64c166f959c8a5022f437a1.png|linux工作利器之二，网络分析工具tcpdump_tcpdump_20]]