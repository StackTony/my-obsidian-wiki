原文： [https://blog.csdn.net/2301_76257382/article/details/143673888](https://blog.csdn.net/2301_76257382/article/details/143673888)


![在这里插入图片描述](https://i-blog.csdnimg.cn/direct/bddce273d8b24436b0d7710e63b4f364.png#pic_center)

- 通常，BMC和 BIOS之间的通信可以通过 IPMl (Inteligent Platform Management Interface)或 SMBus(System Management Bus)来实现。
    
- BMC(Baseboard Management Controler)是一种专门用于监控和管理计算机硬件的微控制器，负责远程管理、电源控制、传感器监控等功能。而 BOS(Basic inputOutput System)是计算机系统中的固件，负责系统启动时的硬件初始化和操作系统加载等工作。在某些系统中，BMC和 BIOS 需要进行通信以实现部分功能。
    
- IPMI（Intelligent Platform Management Interface）：IPMI是一种开放标准的硬件管理协议，它定义了服务器BMC与系统管理软件之间的通信接口。通过IPMI，可以使用网络远程管理服务器，包括监控硬件状态、重启服务器、诊断问题等。BMC通过Ethernet接口连接到服务器的网络，而管理软件可以通过IPMI命令和消息与BMC通信。
    
- Serial-over-LAN（SOL）：SOL是一种通过串口将服务器BMC与远程控制台连接的通信方式。通过串口连接，可以远程访问服务器的BIOS设置界面和操作系统的命令行界面。BMC充当一个串口服务器，将串口输入和输出流转发给管理软件，实现远程控制和访问。
    
- KVM-over-IP：KVM-over-IP（键盘、视频、鼠标远程控制）是一种将服务器的图形输出转发到管理软件，实现远程图形控制的技术。BMC可以将服务器的图形输出转换为网络数据包，并通过网络传输给管理软件。
    
- SNMP（Simple Network Management Protocol）：SNMP是一种常用的网络管理协议，用于监控和管理网络设备。一些服务器BMC也支持SNMP协议，通过SNMP管理软件可以监控和控制BMC，包括获取硬件信息、修改配置参数等。
    
- Redfish：Redfish是一种开放标准的硬件管理协议，基于RESTful API和JSON数据格式。一些新款的服务器BMC支持Redfish协议，通过Redfish API可以远程管理服务器，包括获取硬件状态、修改BIOS设置、执行远程操作等。