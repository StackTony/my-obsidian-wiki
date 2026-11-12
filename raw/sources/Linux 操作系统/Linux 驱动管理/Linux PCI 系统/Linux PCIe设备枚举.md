原文： https://blog.csdn.net/qq_48057735/article/details/151584045

### 一、枚举流程概述：

1. 首先，内核上电，会先根据acpi表提供的pcie根节点，创建主桥设备（下图Host Bridge ）；
2. 紧跟着创建第一根pcie总线bus0；
3. 之后开始扫描该总线下的pcie设备（下图Dev_1、Dev_2、Pci-to-Pci Bridge_1、Pci-to-Pci Bridge_2），将扫描到的pcie设备加入链表；
4. 然后轮询刚才创建的pcie设备链表，判断是否为桥设备，如下图，首先发现Pci-to-Pci Bridge_1
5. 发现pcie设备为桥设备后，便会重复上述2、3、4步骤，直至扫描完所有的pcie设备。![](https://i-blog.csdnimg.cn/direct/40ef2c50ccd044d89ad86cb7b9ad03ad.png)

### 二、根节点匹配过程

#### 2.1 注册根节点处理 结构体

函数调用栈如下
```
acpi_init->acpi_scan_init->acpi_pci_root_init->acpi_scan_add_handler_with_hotplug(&pci_root_handler, "pci_root")->-acpi_scan_add_handler>list_add_tail(&handler->list_node, &acpi_scan_handlers_list);
```
pci_root_handler结构体内容、root_device_ids结构体内容
```c
static struct acpi_scan_handler pci_root_handler = {

.ids = root_device_ids,

.attach = acpi_pci_root_add,

.detach = acpi_pci_root_remove,

.hotplug = {

.enabled = true,

.scan_dependent = acpi_pci_root_scan_dependent,

},

};

=======

static const struct acpi_device_id root_device_ids[] = {

{"PNP0A03", 0},

{"", 0},

};
```
总结来说，就是把pci_root_handler结构体，加入到acpi_scan_handlers_list链表中。

#### 2.2 创建并 初始化 acpi根节点设备

函数调用栈如下
```
acpi_init->acpi_scan_init->acpi_bus_scan(ACPI_ROOT_OBJECT)->acpi_bus_check_add->acpi_add_single_object->创建acpi设备

->acpi_device_dep_initialize->初始化pnp->ids等信息
```
#### 2.3 根节点设备 匹配 根节点处理结构体

函数调用栈如下
```
acpi_init->acpi_scan_init->acpi_bus_scan(ACPI_ROOT_OBJECT)->acpi_bus_attach->-acpi_scan_attach_handler>acpi_scan_match_handler(hwid->id, &devid)
```
其中acpi_scan_attach_handler会遍历device->pnp.ids

acpi_scan_match_handler函数内容
```c
static struct acpi_scan_handler *acpi_scan_match_handler(const char *idstr,

const struct acpi_device_id **matchid)

{

struct acpi_scan_handler *handler;

list_for_each_entry(handler, &acpi_scan_handlers_list, list_node) // 遍历acpi_scan_handlers_list的内容，存放在handler

if (acpi_scan_handler_matching(handler, idstr, matchid)) //匹配handler中的root_device_ids，和device->pnp.ids匹配

return handler;

return NULL;

}
```
#### 2.4 根匹配匹配后，调用acpi_pci_root_add开始pcie设备扫描

函数调用栈如下
```
acpi_init->acpi_scan_init->acpi_bus_scan(ACPI_ROOT_OBJECT)->acpi_bus_attach->acpi_scan_attach_handler->（handler->attach）（即2.1注册的acpi_pci_root_add）

在acpi_pci_root_add中，会先调用pci_acpi_scan_root->acpi_pci_root_create->pci_create_root_bus创建根节点

->pci_scan_child_bus扫描总线
```
### 三、pcie设备扫描过程

**pci_scan_child_bus**函数会调用pci_scan_child_bus_extend->pci_scan_slot扫描pcie设备

pci_scan_slot函数，会多次执行，遍历完32个设备为止；

![](https://i-blog.csdnimg.cn/img_convert/27bf3a2c3038756a0a071e9928a4bc7a.png)

在pci_scan_slot函数中，又会调用pci_scan_single_device遍历设备的8个func；

![](https://i-blog.csdnimg.cn/img_convert/abf3b7c217d5186fd32357111ba8abd4.png)

pci_scan_single_device则会开始扫描pcie设备（pci_scan_device）+初始化pcie设备（pci_device_add）

#### 3.1 扫描pcie设备（pci_scan_device）

pci_scan_device会判断设备是否存在、申请设备、配置设备

##### 3.1.1 pci_bus_read_dev_vendor_id

读pcie配置空间的厂商号，读到有效值，则表示设备存在

##### 3.1.2 pci_alloc_dev

申请pcie设备结构体

##### 3.1.3 pci_setup_device

配置设备类型（EP设备/桥设备）、获取配置空间bar大小

其中**pci_read_bases**函数，就是**网上常说的bar写1，获取bar大小的函数实现**。

#### 3.2 初始化及配置pcie设备（pci_device_add）

##### 3.2.1 初始化设备能力

初始化acs等能力

##### 3.2.2 增加设备到pcie设备链表

list_add_tail(&dev->bus_list, &bus->devices)

##### 3.2.3 注册设备到系统，用于匹配pcie设备驱动

device_add(&dev->dev)

### 四、桥设备识别及建立新总线

**pci_scan_child_bus**函数会调用pci_scan_child_bus_extend->pci_scan_bridge_extend识别pcie桥设备

pci_scan_bridge_extend函数，会多次执行，遍历完bus->devices为止（**3.2.2加到链表的**）

这是bus号建立的概述：[PCIE深度扫描](https://i.zte.com.cn/#/shared/1f7724153bb645649174c8a810cc422e/wiki/page/5910838d51f64da6811c08fa2806752e/view "PCIE深度扫描")

![](https://i-blog.csdnimg.cn/img_convert/62652719750d8268e37f3a55a9c81f4f.png)

遍历时，会判断设备是否为桥（**3.1.3配置的**）

![](https://i-blog.csdnimg.cn/img_convert/c8ff76cd59eb68e9eddcb0443f96fe94.png)

#### 4.1 获取当前桥设备的上游总线号、下游总线号![](https://i-blog.csdnimg.cn/direct/0d36794c712e4820b630ac8317c122cf.png)

读配置空间，获取总线信息

![](https://i-blog.csdnimg.cn/img_convert/abe4dcb77c0b027555acef597160d395.png)

#### 4.2 建立桥设备下游总线

将4.1获取的下游总线号，作为pci_add_new_bus建立的子总线的总线号

![](https://i-blog.csdnimg.cn/img_convert/545b1c5f678e5030d435e89cde77fa0a.png)

这是给子总线的总线号赋值

![](https://i-blog.csdnimg.cn/img_convert/6be98373fdda90ed8a016bfc38bf90af.png)

#### 4.3 递归扫描新建立的总线
递归调用pci_scan_child_bus/pci_scan_child_bus_extend扫描新建立的总线

#### 4.4 如果os要自己分配总线号，走else分支

会先清配置空间的bus信息，再重新分配，并将分配的值写到寄存器

![](https://i-blog.csdnimg.cn/img_convert/cec93bd60ad3d3eb5a597fb019023cc8.png)


参考链接：
[https://zhuanlan.zhihu.com/p/717396193](https://zhuanlan.zhihu.com/p/717396193 "https://zhuanlan.zhihu.com/p/717396193")

[https://zhuanlan.zhihu.com/p/644554217?share_code=1ne1FkaRfjJYI&utm_psn=1945521169332671566](https://zhuanlan.zhihu.com/p/644554217?share_code=1ne1FkaRfjJYI&utm_psn=1945521169332671566 "https://zhuanlan.zhihu.com/p/644554217?share_code=1ne1FkaRfjJYI&utm_psn=1945521169332671566")

[https://zhuanlan.zhihu.com/p/9367977478](https://zhuanlan.zhihu.com/p/9367977478 "https://zhuanlan.zhihu.com/p/9367977478")