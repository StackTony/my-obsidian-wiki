PCIE的BDF框架：
在 PCI/PCIe 架构里，系统里可能有很多设备，必须要有一种**全局唯一的寻址方式**来访问每个设备的配置空间（Config Space）。 这就是 **BDF (Bus–Device–Function)** 体系。

### BDF 三元组定义

- **Bus (总线号，8 bit)**
    
    - 范围：0 ~ 255
        
    - Bus 0 通常是 Root Complex 出来的第一个总线。
        
    - 每个桥（PCI-PCI Bridge 或 PCIe Switch）下游会分配一个新的 Bus 号空间。
        
- **Device (设备号，5 bit)**
    
    - 范围：0 ~ 31
        
    - 每个总线最多挂 32 个“设备插槽”。
        
    - 在 PCIe 中，一个端口就是一个设备。
        
- **Function (功能号，3 bit)**
    
    - 范围：0 ~ 7
        
    - 每个设备最多 8 个功能（Function）。
        
    - Function 0 是主要功能，其它 1~7 可能是附加功能（多功能设备，例如显卡 + 音频，网卡 + iSCSI Offload）。
        

所以 **BDF = [Bus:Device.Function]**，唯一标识一个功能。

![](https://i-blog.csdnimg.cn/direct/657ccd87701b43019b1d1a7a6953162b.png)

### 配置空间寻址

每个 Function 有 4KB 的配置空间（PCIe 标准），前 256B 是 PCI 兼容头部。

- 在硬件上，访问配置空间使用 **Configuration TLP**（CfgRd/CfgWr）。
    
- 在软件上（比如 Linux），BDF 被映射成设备节点：
    
    - `/sys/bus/pci/devices/0000:02:00.0/`
        
    - `/proc/bus/pci/`
        

### 实际应用场景

- **操作系统枚举**： BIOS/UEFI 或操作系统枚举 PCIe 设备时，通过 Bus 递归扫描，分配 Device/Function，建立设备树。
    
- **Linux 工具查看**：
    
    - `lspci`：列出 BDF，如 `03:00.0 Ethernet controller: Intel …`
        
    - `setpci`：按 BDF 精确访问配置寄存器。
        
- **驱动匹配**：
    
    - 驱动里通过 `struct pci_device_id` 匹配 Vendor ID、Device ID，同时也依赖 BDF 定位。