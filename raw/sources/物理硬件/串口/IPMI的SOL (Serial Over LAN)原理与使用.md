原文： https://blog.csdn.net/qq_24993025/article/details/135452367

## 前言

        SOL (Serial over LAN)是一个非常强大的工具IPMI其中的一个功能，提供了在局域网上对某台机器串口进行远程访问。SOL的主要目标是重定向本地异步串行控制器接口的数据到远端。我们可以用SOL建立一个虚拟的远程串行终端，用远程软件就能够通过串口远程操作机器的 操作系统 或者管理服务。

        SOL是IPMI v2.0版本的功能，想使用这个功能的前提是要确定你的服务器的BMC是支持IPMIv2.0的。SOL是通过重定向，将串口的信息发送到LAN上来实现的。使用SOL控制台重定向，我们就可以从任何地方远程查看远程服务器或PC上基于文本的控制台，并执行任何不需要GUI的任务。

        本文档介绍了在服务器上配置和使用SOL 远程控制 Linux和ESXi直接控制台的方法。

## SOL的原理 

        下图展示了SOL的结构和框架，线条表示串口数据流。BMC (Baseboard Management Controller)通过局域网重定向串口通信，使远程服务器或PC可以通过IPMI LAN会话与BIOS或OS进行交互。

![](https://i-blog.csdnimg.cn/blog_migrate/a4b0965ec39af4f25382260cf75568aa.png)

图1 SOL原理框图

        SOL可用于操作系统和操作系统前的异步串行通信，通过BMC连接。SOL为用户提供了一种在远程控制台与串行文本接口进行交互的方法，例如操作系统命令行、串行重定向BIOS接口和IPMI LAN会话上的串行文本应用程序。单个远程控制台应用可以使用SOL在统一的用户界面下同时提供局域网访问IPMI平台管理和串口文本重定向。SOL的访问权限管理在与IPMI管理相同的用户配置界面下。这简化了配置软件、远程管理应用程序和跨平台配置实用工具的创建。

        通过BMC将OS或者BIOS的串口输出转换成IPMI的约定协议，通过SMBus发送到LAN控制器，在一个局域网中的其他机器就可以使用IPMI接受到目标服务器上串口的数据，进行交互，即远程通过串口操控OS或者BIOS。 

## 如何设置并使用SOL

### 1. 使用SOL的前提条件

        在使用SOL的确保如下条件，否则SOL不能正常工作。

##### 目标服务器:

- **检查IPMI over LAN**：确保服务器的BMC设置中启用了IPMI over LAN。
- **UEFI下配置串口设置**：确保串口设置正确。
- **在OS中配置控制台重定向**：将操作系统的console重定向到串口。

##### **远程服务器的电脑：**

- **ipmitool支持ipmi2.0版本**：推荐使用ipmitool v1.8.18版本。

### 2. 检查IPMI over LAN状态

        在配置SOL之前，请确保已启用IPMI over LAN。不同品牌的服务器不太一样，以我的服务器为例。打开BMC的web管理界面，通过BMC Configuration→Network→IPMI over LAN进行配置，如图2所示。

![](https://i-blog.csdnimg.cn/blog_migrate/664d19b8938e06566af5167e9144266e.png)

图2 BMC网络端口设置

        除了启用LAN上的IPMI，有的BMC对用户的可访问权限也有相关设置，所以除了开启IPMI over LAN端口，还需要确认您的BMC用户有IPMI over LAN的访问权限。

        以我的服务器为例，进入BMC Configuration→User/LDAP，选择要编辑的用户。如果它有用户可访问接口选项，请确保选中IPMI over Lan选项，如图3所示。 

![](https://i-blog.csdnimg.cn/blog_migrate/314f62191c2803018e3359cb18b930f6.png)

图3 BMC用户访问权限设置

### 3. 在UEFI中配置串口

        为了正常通信，需要开启串口控制台重定向，并确保串口参数正确。串口控制台重定向可在UEFI中配置。

        不同型号版本的机器UEFI设置不尽相同，但大同小异。以我的服务器为例，进入BIOS，选择“系统设置”→“设备和I/O端口”→“控制台重定向设置”，可以设置服务器串口的设置，如图4所示。

        不同服务器品牌的设置不一样，我这台机器的SOL与Console Redirection相关联COM 1。所以我选择COM1开启重定向，具体的服务器这一块如何设计，需要参考相应服务器的说明书。

![](https://i-blog.csdnimg.cn/blog_migrate/e33bbd44e136bd3a2bc7bb47a7e1bcb5.png)

图4 UEFI设置

        这里除了要开启串口重定向，还要确保串口的通信参数设置要与之后ipmitool的设置一致否则会通信错误，我这里就使用了最通用且ipmitool默认的串口通信参数。

### 4. 配置OS的控制台重定向

        现在BMC及UEFI的设置已完成，我们还需要重定向OS中的直接控制台。让OS将console控制台输出到串口，BMC就会将输出在串口的控制台信息通过SOL发送出去。因为我的服务器上，SOL与COM1绑定，之前我在UEFI里设置的也是COM1，因此我需要将OS的console重定向到COM1。

以下介绍 Linux 和ESXi两种OS的console重定向到COM1的方法。

#### Linux：

1.  编辑/etc/default/grub文件，如图5所示。
2. 在’**GRUB_CMDLINE_LINUX**”参数的末尾添加“**console=tty0 console=ttyS0,115200**‘。
3. 添加’**GRUB_TERMINAL="serial"**‘到新行。
4. 添加’**GRUB_SERIAL_COMMAND="serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1"**‘到新行。
5. 输入以下命令生成grub配置文件。

UEFI mode:

```
~# grub2-mkconfig -o /boot/efi/EFI/redhat/grub.cfg
```

Legacy mode:

```
# grub2-mkconfig -o /boot/grub2/grub.cfg
```

![](https://i-blog.csdnimg.cn/blog_migrate/e67199a8044085741be656757f0a79ab.png)

图5 grub配置文件

#### ESXi： 

1. 重启，当加载ESXi窗口出现时，您可以在右下角看到提示符“**SHIFT+O: Edit boot options**”，如图6所示。按“Shift + O”编辑启动项。
    
    ![](https://i-blog.csdnimg.cn/blog_migrate/9901f10773452d968e0deddcf037ecdd.png)
    
    图7 启动ESXi
    
2. 关闭com1上的logPort和gdbPort，通过输入以下启动选项将tty2Port设置为com1，并在原始启动选项之后添加以下选项，如图7所示。
    
    ```
    gdbPort=none logPort=none tty2Port=com1
    ```
    
    ![](https://i-blog.csdnimg.cn/blog_migrate/92c65ae8d72c8baf030500d2ba183c43.png)
    
    图8 添加启动项
    
3. 添加这些启动选项后，按Enter键启动ESXi。 
    

> **提示:**通过手动设置启动选项重定向到串口是一次性的。要为后续启动重定向直接控制台，请使用其他方法。

或者可以使用命令的方式进行设置：

1. 使用CLI命令设置控制台重定向。
    
    ```
    ~~~
    ```
    
2. 执行命令检查配置是否正确。该命令的输出如图9所示。 
    
    ```
    ~~~
    ```
    
    ![](https://i-blog.csdnimg.cn/blog_migrate/8834fe88bed4f76f2b7fa77f2a145e50.png)
    
    图10 ESXi命令运行结果
    

### 5. 使用ipmitool远程监控控制台

        在完成如上设置后服务器OS的控制台就被重定向到了SOL通过LAN发出了，接下来我们需要做的就是在远端（我的电脑上）使用工具ipmitool建立连接远程控制这台服务器。

        SOL是在IPMI v2.0下实现的，要求ipmitool支持IPMI v2.0。ipmitool v1.6.0及更高版本已经发布，我这里使用的是ipmitool v1.8.18。

1. 确保ipmitool在您的PC上工作，并且您的PC与目标服务器的BMC在同一个局域网上。
2. 从使用以下IPMI命令连接SOL。
    
    ```
    ipmitool -C 17 -I lanplus -H <IP address of BMC > -U ADMIN -P ADMIN sol activate
    ```
    
    例如：
    
    ```
    ipmitool -C 17 -I lanplus -H 10.10.10.10 -U ADMIN -P ADMIN sol activate
    ```
    

IPMI SOL命令说明如下表所示：

|功能|命令行|描述|
|---|---|---|
|获取SOL信息|ipmitool sol info<br><br>ipmitool sol info 1|获取SOL配置数据|
|建立SOL连接|ipmitool -C 17 -I lanplus -U <username> -P <password> -H <ip_address> sol activate<br><br>其中:<br><br>- -U is BMC 用户名<br>- -H is BMC IP地址<br>- -P is BMC 密码|建立SOL远程访问控制台连接|
|关闭SOL连接|ipmitool -C 17 -I lanplus -U <username> -P <password> -H <ip_address> sol deactivate|关闭SOL远程访问控制台连接|

         连接建立后，重启服务器就可以在电脑上看见服务器的启动信息了，如下图。

![](https://i-blog.csdnimg.cn/blog_migrate/94fcce7b2ef4c8e5f90b27ad7bb1a5a8.png)

**PS：如果在运行ipmitool后出现如下警告：Error: Unable to establish IPMI v2 / RMCP+ session，有三种可能导致这种问题：**

1. 服务器BMC密码错误。
2. 服务器ipmi over LAN端口没有开启。
3. 服务器BMC用户没有使用的权限。

![](https://i-blog.csdnimg.cn/blog_migrate/f1ff1a2569b4b23c0ab265a9ec6268a1.png)