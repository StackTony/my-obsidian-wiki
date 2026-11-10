## BIOS配置

在BIOS中，需要启用Intel VT和VT-d。VT是Virtualization Technology的缩写，而VT-d是Virtualization Technology for Directed I/O的缩写。后者正是Intel IOMMU的别名。

## .config文件配置

```
CONFIG_INTEL_IOMMU=y
```

CONFIG_INTEL_IOMMU=y，是启用Intel IOMMU的**必要非充分条件**。这一配置目的在于告诉内核在启动时，要将Intel IOMMU的检测函数detect_intel_iommu()加载到IOMMU table中。但是，加载并不意味着使用——只有按下一节的方式配置启动参数后，Intel IOMMU才会被初始化。

## 启动参数配置

设置以下两个启动参数，以显式指定Intel IOMMU作为IOMMU的实现方式：

```
iommu=force intel_iommu=on
```

进行完以上配置后，内核将会启用Intel IOMMU，作为IOMMU的实现方式，同时禁用SWIOTLB——严格来说，“禁用SWIOTLB”只是一个笼统的说法，具体实现过程比较复杂，[下一篇文章](https://blog.csdn.net/qq_34719392/article/details/117563480)将予以详细介绍。

## 确认Intel IOMMU已启用

确认内核已启用Intel IOMMU的方法很简单。在控制台执行如下命令：

```
dmesg | grep "DMAR"
```

如果看到 类 似下图中以"DMAR"开头的一系列日志信息，就表明Intel IOMMU已启用。  
![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/cd22afaf65e5e2e28d64d971e2db3b5b.png)

下一篇文章将结合代码，介绍Intel IOMMU的初始化流程。