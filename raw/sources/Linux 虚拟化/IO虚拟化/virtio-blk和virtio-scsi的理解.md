---
tags:
  - virtio
---

<https://blog.csdn.net/yongwan5637/article/details/91489961>

在virtio-blk磁盘中，采用io_event_fd进行前端到后端通知，采用中断注入方式实现后端到前端的通知，并通过IO环(vring)进行数据的共享。

virtio-blk设备从功能上来看，核心功能就是实现虚拟机内外的事件通知和数据传递：虚拟机内部的前端驱动准备好待处理的IO请求和数据存放空间并通知后端；虚拟机外部的后端程序获取待处理的请求并交给真正的IO子系统处理，完成后将处理结果通知前端。

使用virtio_blk驱动的磁盘显示为“/dev/vda”，使用virtio_scsi驱动的磁盘显示为“/dev/sda”，这不同于IDE硬盘的“/dev/hda”或者SATA硬盘的“/dev/sda”这样的显示标识。

virtio-scsi功能是一种新的半虚拟化SCSI控制器设备。virtio-scsi的优势在于它能够处理数百个设备，而virtio-blk只能处理大约30个设备并耗尽PCI插槽。

driver为scsi-block，对应的device是virtio-scsi。
在虚拟化环境中，通常使用virtio-scsi作为SCSI设备的后端，因为它提供了更好的性能和可扩展性。而driver则是scsi-block，它是Linux内核中的一种SCSI块设备驱动程序，用于管理SCSI设备上的块存储。
