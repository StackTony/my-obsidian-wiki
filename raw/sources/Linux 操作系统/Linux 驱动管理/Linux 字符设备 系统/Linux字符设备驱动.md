原文： https://doc.embedfire.com/linux/rk356x/driver/zh/latest/linux_driver/base_character_device.html#

上几章节我们了解到什么是内核模块，模块的加载/卸载详细过程以及内核模块的使用等内容。 本章，我们将学习字符设备使用、字符设备驱动相关的概念，理解字符设备驱动程序的基本框架，并从源码上分析字符设备驱动实现和管理等。 主要分为下面五部分：

1. Linux设备分类；
    
2. 字符设备的抽象，字符设备设计思路；
    
3. 字符设备相关的概念以及数据结构，了解设备号等基本概念以及file_operations、file、inode相关数据结构；
    
4. 字符字符设备驱动程序框架，例如内核是如何管理设备号的；系统关联、调用file_operation接口，open函数所涉及的知识等等。
    
5. 设备驱动程序实验。
    

## 4.1. Linux设备分类[¶](#id1 "永久链接至标题")

linux是文件型系统，所有硬件都会在对应的目录(/dev)下面用相应的文件表示。 在windows系统中，设备大家很好理解，像硬盘，磁盘指的是实实在在硬件。 而在文件系统的linux下面，都有对应文件与这些设备关联的，访问这些文件就可以访问实际硬件。 像访问文件那样去操作硬件设备，一切都会简单很多，不需要再调用以前com,prt等接口了。 直接读文件，写文件就可以向设备发送、接收数据。 按照读写存储数据方式，我们可以把设备分为以下几种：字符设备、块设备和网络设备。

**字符设备**：指应用程序按字节/字符来读写数据的设备。 这些设备节点通常为传真、虚拟终端和串口调制解调器、键盘之类设备提供流通信服务， 它通常不支持随机存取数据。字符设备在实现时，大多不使用缓存器。系统直接从设备读取/写入每一个字符。 例如，键盘这种设备提供的就是一个数据流，当你敲入“cnblogs”这个字符串时， 键盘驱动程序会按照和输入完全相同的顺序返回这个由七个字符组成的数据流。它们是顺序的，先返回c，最后是s。

**块设备**：通常支持随机存取和寻址，并使用缓存器。 操作系统为输入输出分配了缓存以存储一块数据。当程序向设备发送了读取或者写入数据的请求时， 系统把数据中的每一个字符存储在适当的缓存中。当缓存被填满时，会采取适当的操作把数据传走，而后系统清空缓存。 它与字符设备不同之处就是，是否支持随机存储。字符型是流形式，逐一存储。 典型的块设备有硬盘、SD卡、闪存等，应用程序可以寻址磁盘上的任何位置，并由此读取数据。 此外，数据的读写只能以块的倍数进行。

**网络设备**：是Linux中一种特殊的设备类型，它既不存在于/dev目录下，也不通过常规的open/read/write文件I/O接口进行访问， 而是通过Socket API与内核网络协议栈进行交互。典型代表包括以太网卡、无线网卡以及本地回环接口。

Linux内核中处处体现面向对象的设计思想，为了统一形形色色的设备，Linux系统将设备分别抽象为struct cdev、 struct block_device、struct net_devce三个对象，具体的设备都可以包含着三种对象从而继承和三种对象属性和操作， 并通过各自的对象添加到相应的驱动模型中，从而进行统一的管理和操作。

字符设备驱动程序适合于大多数简单的硬件设备，而且比起块设备或网络驱动更加容易理解， 因此我们选择从字符设备开始，从最初的模仿，到慢慢熟悉，最终成长为驱动界的高手。

## 4.2. 字符设备抽象[¶](#id2 "永久链接至标题")

Linux内核中将字符设备抽象成一个具体的数据结构(struct cdev)，我们可以理解为字符设备对象， cdev记录了字符设备的相关信息(设备号、内核对象)，字符设备的打开、读写、关闭等操作接口(file_operations)， 在我们想要添加一个字符设备时，就是将这个对象注册到内核中，通过创建一个文件(设备节点)绑定对象的cdev， 当我们对这个文件进行读写操作时，就可以通过虚拟文件系统，在内核中找到这个对象及其操作接口，从而控制设备。

C语言中没有面向对象语言的继承的语法，但是我们可以通过结构体的包含来实现继承，这种抽象提取了设备的共性， 为上层提供了统一接口，使得管理和操作设备变得很容易。

![device_number](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/characprog004.png)

在硬件层，我们可以通过查看硬件的原理图、芯片的数据手册，确定底层需要配置的寄存器，这类似于裸机开发， 将对底层寄存器的配置，读写操作放在文件操作接口里面，也就是实现file_operations结构体； 在驱动层，我们将文件操作接口注册到内核，内核通过内部散列表来登记记录主次设备号； 在文件系统层，新建一个文件绑定该文件操作接口，应用程序通过操作指定文件的文件操作接口来设置底层寄存器。

实际上，在Linux上写驱动程序，都是做一些“填空题”。因为Linux给我们提供了一个基本的框架， 我们只需要按照这个框架来写驱动，内核就能很好的接收并且按我们所要求的那样工作。有句成语工欲善其事，必先利其器， 在理解这个框架之前我们得花点时间来学习字符设备驱动相关概念及数据结构。

## 4.3. 相关概念及数据结构[¶](#id3 "永久链接至标题")

在linux中，我们使用设备编号来表示设备，主设备号区分设备类别，次设备号标识具体的设备。 cdev结构体被内核用来记录设备号，而在使用设备时，我们通常会打开设备节点，通过设备节点的inode结构体、 file结构体最终找到file_operations结构体，并从file_operations结构体中得到操作设备的具体方法。

### 4.3.1. 设备号[¶](#id4 "永久链接至标题")

对于字符的访问是通过文件系统的名称进行的，这些名称被称为特殊文件、设备文件，或者简单称为文件系统树的节点， Linux根目录下有/dev这个文件夹，专门用来存放设备中的驱动程序，我们可以使用ls -l 以列表的形式列出系统中的所有设备。 其中，每一行表示一个设备，每一行的第一个字符表示设备的类型。

如下图：’c’用来标识字符设备，’b’用来标识块设备。如 autofs 是一个字符设备c， 它的主设备号是10，次设备号是235； loop0 是一个块设备，它的主设备号是7，次设备号为0，同时可以看到loop0-loop3共用一个主设备号，次设备号由0开始递增。

![device_number](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/device_number.png)

一般来说，主设备号指向设备的驱动程序，次设备号指向某个具体的设备。如上图，I2C-0，I2C-1属于不同设备但是共用一套驱动程序

#### 4.3.1.1. 内核中设备编号的含义[¶](#id5 "永久链接至标题")

在内核中，dev_t用来表示设备编号，dev_t是一个32位的数，其中，高12位表示主设备号，低20位表示次设备号。 也就是理论上主设备号取值范围：0-2^12，次设备号0-2^20。 实际上在内核源码中__register_chrdev_region(…)函数中，major被限定在0-CHRDEV_MAJOR_MAX，CHRDEV_MAJOR_MAX是一个宏，值是512。 在kdev_t中，设备编号通过移位操作最终得到主/次设备号码，同样主/次设备号也可以通过位运算变成dev_t类型的设备编号， 具体实现参看下面代码MAJOR(dev)、MINOR(dev)和MKDEV(ma,mi)。

dev_t定义 (内核源码/include/types.h)[¶](#id36 "永久链接至代码")

```c
typedef u32 __kernel_dev_t;

typedef __kernel_dev_t               dev_t;
```

设备号相关宏 (内核源码/include/linux/kdev_t.h)[¶](#id37 "永久链接至代码")

```c
#define MINORBITS    20
#define MINORMASK    ((1U << MINORBITS) - 1)

#define MAJOR(dev)   ((unsigned int) ((dev) >> MINORBITS))
#define MINOR(dev)   ((unsigned int) ((dev) & MINORMASK))
#define MKDEV(ma,mi) (((ma) << MINORBITS) | (mi))
```

- 第4-5行：内核还提供了另外两个宏定义MAJOR和MINOR，可以根据设备的设备号来获取设备的主设备号和次设备号。
    
- 第6行：宏定义MKDEV，用于将主设备号和次设备号合成一个设备号，主设备可以通过查阅内核源码的Documentation/devices.txt文件，而次设备号通常是从编号0开始。
    

#### 4.3.1.2. cdev结构体[¶](#cdev "永久链接至标题")

内核通过一个散列表(哈希表)来记录设备编号。 哈希表由数组和链表组成，吸收数组查找快，链表增删效率高，容易拓展等优点。

以主设备号为cdev_map编号，使用哈希函数f(major)=major%255来计算组数下标(使用哈希函数是为了链表节点尽量平均分布在各个数组元素中，提高查询效率)； 主设备号冲突，则以次设备号为比较值来排序链表节点。 如下图所示，内核用struct cdev结构体来描述一个字符设备，并通过struct kobj_map类型的 散列表cdev_map来管理当前系统中的所有字符设备。

![字符设备散列表](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/charac004.jpg)

cdev结构体(内核源码/include/linux/cdev.h)[¶](#id38 "永久链接至代码")

```c
struct cdev {
   struct kobject kobj;
   struct module *owner;
   const struct file_operations *ops;
   struct list_head list;
   dev_t dev;
   unsigned int count;
} __randomize_layout;
```

- **struct kobject kobj：** 内嵌的内核对象，通过它将设备统一加入到“Linux设备驱动模型”中管理(如对象的引用计数、电源管理、热插拔、生命周期、与用户通信等)。
    
- **struct module *owner：** 字符设备驱动程序所在的内核模块对象的指针。
    
- **const struct file_operations *ops：** 文件操作，是字符设备驱动中非常重要的数据结构，在应用程序通过文件系统(VFS)呼叫到设备设备驱动程序中实现的文件操作类函数过程中，ops起着桥梁纽带作用，VFS与文件系统及设备文件之间的接口是file_operations结构体成员函数，这个结构体包含了对文件进行打开、关闭、读写、控制等一系列成员函数。
    
- **struct list_head list：** 用于将系统中的字符设备形成链表(这是个内核链表的一个链接因子，可以再内核很多结构体中看到这种结构的身影)。
    
- **dev_t dev：** 字符设备的设备号，有主设备和次设备号构成。
    
- **unsigned int count：** 属于同一主设备好的次设备号的个数，用于表示设备驱动程序控制的实际同类设备的数量。
    

### 4.3.2. 设备节点[¶](#id6 "永久链接至标题")

设备节点(设备文件)：Linux中设备节点是通过“mknod”命令来创建的。一个设备节点其实就是一个文件， Linux中称为设备文件。有一点必要说明的是，在Linux中，所有的设备访问都是通过文件的方式， 一般的数据文件程序普通文件，设备节点称为设备文件。

设备节点被创建在/dev下，是连接内核与用户层的枢纽，就是设备是接到对应哪种接口的哪个ID 上。 相当于硬盘的inode一样的东西，记录了硬件设备的位置和信息在Linux中，所有设备都以文件的形式存放在/dev目录下， 都是通过文件的方式进行访问，设备节点是Linux内核对设备的抽象，一个设备节点就是一个文件。 应用程序通过一组标准化的调用执行访问设备，这些调用独立于任何特定的驱动程序。而驱动程序负责将这些标准调用映射到实际硬件的特有操作。

### 4.3.3. 数据结构[¶](#id7 "永久链接至标题")

在驱动开发过程中，不可避免要涉及到三个重要的的内核数据结构分别包括文件操作方式(file_operations)， 文件描述结构体(struct file)以及inode结构体，在我们开始阅读编写驱动程序的代码之前，有必要先了解这三个结构体。

#### 4.3.3.1. file_operations结构体[¶](#file-operations "永久链接至标题")

file_operation就是把系统调用和驱动程序关联起来的关键数据结构。这个结构的每一个成员都对应着一个系统调用。 读取file_operation中相应的函数指针，接着把控制权转交给函数指针指向的函数，从而完成了Linux设备驱动程序的工作。

![字符设备散列表](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/characprog002.png)

在系统内部，I/O设备的存取操作通过特定的入口点来进行，而这组特定的入口点恰恰是由设备驱动程序提供的。 通常这组设备驱动程序接口是由结构file_operations结构体向系统说明的，它定义在ebf_buster_linux/include/linux/fs.h中。 传统上， 一个file_operation结构或者其一个指针称为 fops( 或者它的一些变体). 结构中的每个成员必须指向驱动中的函数， 这些函数实现一个特别的操作， 或者对于不支持的操作留置为NULL。当指定为NULL指针时内核的确切的行为是每个函数不同的。

以下代码中只列出本章使用到的部分函数。

file_operations结构体(内核源码/include/linux/fs.h)[¶](#id39 "永久链接至代码")

```c
struct file_operations {
   struct module *owner;
   loff_t (*llseek) (struct file *, loff_t, int);
   ssize_t (*read) (struct file *, char __user *, size_t, loff_t *);
   ssize_t (*write) (struct file *, const char __user *, size_t, loff_t *);
   long (*unlocked_ioctl) (struct file *, unsigned int, unsigned long);
   int (*open) (struct inode *, struct file *)
   int (*release) (struct inode *, struct file *);
};
```

- **llseek：** 用于修改文件的当前读写位置，并返回偏移后的位置。参数file传入了对应的文件指针，我们可以看到以上代码中所有的函数都有该形参，通常用于读取文件的信息，如文件类型、读写权限；参数loff_t指定偏移量的大小；参数int是用于指定新位置指定成从文件的某个位置进行偏移，SEEK_SET表示从文件起始处开始偏移；SEEK_CUR表示从当前位置开始偏移；SEEK_END表示从文件结尾开始偏移。
    
- **read：** 用于读取设备中的数据，并返回成功读取的字节数。该函数指针被设置为NULL时，会导致系统调用read函数报错，提示“非法参数”。该函数有三个参数：file类型指针变量，char__user*类型的数据缓冲区，__user用于修饰变量，表明该变量所在的地址空间是用户空间的。内核模块不能直接使用该数据，需要使用copy_to_user函数来进行操作。size_t类型变量指定读取的数据大小。
    
- **write：** 用于向设备写入数据，并返回成功写入的字节数，write函数的参数用法与read函数类似，不过在访问__user修饰的数据缓冲区，需要使用copy_from_user函数。
    
- **unlocked_ioctl：** 提供设备执行相关控制命令的实现方法，它对应于应用程序的fcntl函数以及ioctl函数。在 kernel 3.0 中已经完全删除了 struct file_operations 中的 ioctl 函数指针。
    
- **open：** 设备驱动第一个被执行的函数，一般用于硬件的初始化。如果该成员被设置为NULL，则表示这个设备的打开操作永远成功。
    
- **release：** 当file结构体被释放时，将会调用该函数。与open函数相反，该函数可以用于释放
    

上面，我们提到read和write函数时，需要使用copy_to_user函数以及copy_from_user函数来进行数据访问，写入/读取成 功函数返回0，失败则会返回未被拷贝的字节数。

copy_to_user和copy_from_user函数(内核源码/include/asm-generic/uaccess.h)[¶](#id40 "永久链接至代码")

```c
static inline long copy_from_user(void *to, const void __user * from, unsigned long n)
static inline long copy_to_user(void __user *to, const void *from, unsigned long n)
```

函数参数和返回值如下：

**参数**

- **to**：指定目标地址，也就是数据存放的地址，
    
- **from**：指定源地址，也就是数据的来源。
    
- **n**：指定写入/读取数据的字节数。
    

**返回值**

- 写入/读取数据的字节数
    

#### 4.3.3.2. file结构体[¶](#file "永久链接至标题")

内核中用file结构体来表示每个打开的文件，每打开一个文件，内核会创建一个结构体，并将对该文件上的操作函数传递给 该结构体的成员变量f_op，当文件所有实例被关闭后，内核会释放这个结构体。如下代码中，只列出了我们本章需要了解的成员变量。

file结构体(内核源码/include/fs.h)[¶](#id41 "永久链接至代码")

```c
struct file {
{......}
const struct file_operations *f_op;
/* needed for tty driver, and maybe others */
void *private_data;
{......}
};
```

- **f_op**：存放与文件操作相关的一系列函数指针，如open、read、wirte等函数。
    
- **private_data**：该指针变量只会用于设备驱动程序中，内核并不会对该成员进行操作。因此，在驱动程序中，通常用于指向描述设备的结构体。
    

#### 4.3.3.3. inode结构体[¶](#inode "永久链接至标题")

VFS inode 包含文件访问权限、属主、组、大小、生成时间、访问时间、最后修改时间等信息。 它是Linux 管理文件系统的最基本单位，也是文件系统连接任何子目录、文件的桥梁。 内核使用inode结构体在内核内部表示一个文件。因此，它与表示一个已经打开的文件描述符的结构体(即file文件结构)是不同的， 我们可以使用多个file文件结构表示同一个文件的多个文件描述符，但此时， 所有的这些file文件结构全部都必须只能指向一个inode结构体。 inode结构体包含了一大堆文件相关的信息，但是就针对驱动代码来说，我们只要关心其中的两个域即可：

inode结构体(内核源码/include/linux/fs.h)[¶](#id42 "永久链接至代码")

```c
 1  struct inode {
 2
 3     dev_t    i_rdev;
 4     {......}
 5     union {
 6        struct pipe_inode_info *i_pipe;   /* linux内核管道 */
 7        struct block_device *i_bdev;      /* 如果这是块设备，则设置并使用 */
 8        struct cdev *i_cdev;              /* 如果这是字符设备，则设置并使用 */
 9        char        *i_link;
10        unsigned    i_dir_seq;
11     };
12     {......}
13  };
```

- **dev_t i_rdev：** 表示设备文件的结点，这个域实际上包含了设备号。
    
- **struct cdev *i_cdev：** struct cdev是内核的一个内部结构，它是用来表示字符设备的，当inode结点指向一个字符设备文件时，此域为一个指向inode结构的指针。
    

## 4.4. 字符设备驱动程序框架[¶](#id8 "永久链接至标题")

讲了很多次字符设备驱动程序框架，那到底什么是字符文件程序框架呢？我们可以从下面的思维导图来解读内核源码。

![字符设备散列表](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/characprog001.png)

我们创建一个字符设备的时候，首先要的到一个设备号，分配设备号的途径有静态分配和动态分配； 拿到设备的唯一ID，我们需要实现file_operation并保存到cdev中，实现cdev的初始化； 然后我们需要将我们所做的工作告诉内核，使用cdev_add()注册cdev； 最后我们还需要创建设备节点，以便我们后面调用file_operation接口。

注销设备时我们需释放内核中的cdev，归还申请的设备号，删除创建的设备节点。

在实现设备操作这一段，我们可以看看open函数到底做了什么。

### 4.4.1. 驱动初始化和注销[¶](#id9 "永久链接至标题")

#### 4.4.1.1. 设备号的申请和归还[¶](#id10 "永久链接至标题")

Linux内核提供了两种方式来定义字符设备，如下所示。

定义字符设备[¶](#id43 "永久链接至代码")

```c
//第一种方式
static struct cdev chrdev;
//第二种方式
struct cdev *cdev_alloc(void);
```

第一种方式，就是我们常见的变量定义；第二种方式，是内核提供的动态分配方式，调用该函数之 后，会返回一个struct cdev类型的指针，用于描述字符设备。

从内核中移除某个字符设备，则需要调用cdev_del函数，如下所示。

cdev_del函数[¶](#id44 "永久链接至代码")

```c
void cdev_del(struct cdev *p)
```

函数参数和返回值如下：

**参数：**

- **p：** 该函数需要将我们的字符设备结构体的地址作为实参传递进去，就可以从内核中移除该字符设备了。
    

**返回值：** 无

**register_chrdev_region函数**

register_chrdev_region函数用于静态地为一个字符设备申请一个或多个设备编号。函数原型如下所示。

register_chrdev_region函数[¶](#id45 "永久链接至代码")

```c
int register_chrdev_region(dev_t from, unsigned count, const char *name)
```

函数参数和返回值如下：

**参数：**

- **from**：dev_t类型的变量，用于指定字符设备的起始设备号，如果要注册的设备号已经被其他的设备注册了，那么就会导致注册失败。
    
- **count**：指定要申请的设备号个数，count的值不可以太大，否则会与下一个主设备号重叠。
    
- **name**：用于指定该设备的名称，我们可以在/proc/devices中看到该设备。
    

**返回值：** 返回0表示申请成功，失败则返回错误码

**alloc_chrdev_region函数**

使用register_chrdev_region函数时，都需要去查阅内核源码的Documentation/devices.txt文件， 这就十分不方便。因此，内核又为我们提供了一种能够动态分配设备编号的方式：alloc_chrdev_region。

调用alloc_chrdev_region函数，内核会自动分配给我们一个尚未使用的主设备号。 我们可以通过命令“cat /proc/devices”查询内核分配的主设备号。

alloc_chrdev_region函数原型[¶](#id46 "永久链接至代码")

```c
int alloc_chrdev_region(dev_t *dev, unsigned baseminor, unsigned count, const char *name)
```

函数参数和返回值如下：

**参数：**

- **dev**：指向dev_t类型数据的指针变量，用于存放分配到的设备编号的起始值；
    
- **baseminor**：次设备号的起始值，通常情况下，设置为0；
    
- **count、name**：同register_chrdev_region类型，用于指定需要分配的设备编号的个数以及设备的名称。
    

**返回值：** 返回0表示申请成功，失败则返回错误码

**unregister_chrdev_region函数**

当我们删除字符设备时候，我们需要把分配的设备编号交还给内核，对于使用register_chrdev_region函数 以及alloc_chrdev_region函数分配得到的设备编号，可以使用unregister_chrdev_region函数实现该功能。

unregister_chrdev_region函数(内核源码/fs/char_dev.c)[¶](#id47 "永久链接至代码")

```c
void unregister_chrdev_region(dev_t from, unsigned count)
```

函数参数和返回值如下：

**参数：**

- **from**：指定需要注销的字符设备的设备编号起始值，我们一般将定义的dev_t变量作为实参。
    
- **count**：指定需要注销的字符设备编号的个数，该值应与申请函数的count值相等，通常采用宏定义进行管理。
    

**返回值：** 无

**register_chrdev函数**

除了上述的两种，内核还提供了register_chrdev函数用于分配设备号。该函数是一个内联函数，它不仅支持静态申请设备号，也支持动态申请设备号，并将主设备号返回，函数原型如下所示。

register_chrdev函数原型(内核源码/include/linux/fs.h文件)[¶](#id48 "永久链接至代码")

```c
static inline int register_chrdev(unsigned int major, const char *name,
const struct file_operations *fops)
{
   return __register_chrdev(major, 0, 256, name, fops);
}
```

函数参数和返回值如下：

**参数：**

- **major**：用于指定要申请的字符设备的主设备号，等价于register_chrdev_region函数，当设置为0时，内核会自动分配一个未使用的主设备号。
    
- **name**：用于指定字符设备的名称
    
- **fops**：用于操作该设备的函数接口指针。
    

**返回值：** 主设备号

我们从以上代码中可以看到，使用register_chrdev函数向内核申请设备号，同一类字 符设备(即主设备号相同)，会在内核中申请了256个，通常情况下，我们不需要用到这么多个设备，这就造成了极大的资源浪费。

**unregister_chrdev函数**

使用register函数申请的设备号，则应该使用unregister_chrdev函数进行注销。

unregister_chrdev函数(内核源码/include/linux/fs.h)[¶](#id49 "永久链接至代码")

```c
static inline void unregister_chrdev(unsigned int major, const char *name)
{
__unregister_chrdev(major, 0, 256, name);
}
```

函数参数和返回值如下：

**参数：**

- **major**：指定需要释放的字符设备的主设备号，一般使用register_chrdev函数的返回值作为实参。
    
- **name**：执行需要释放的字符设备的名称。
    

**返回值：** 无

#### 4.4.1.2. 初始化cdev[¶](#id11 "永久链接至标题")

前面我们已经提到过了，编写一个字符设备最重要的事情，就是要实现file_operations这个结构体中的函数。 实现之后，如何将该结构体与我们的字符设备结构体相关联呢？内核提供了cdev_init函数，来实现这个过程。

cdev_init函数(内核源码/fs/char_dev.c)[¶](#id50 "永久链接至代码")

```c
void cdev_init(struct cdev *cdev, const struct file_operations *fops)
```

函数参数和返回值如下：

**参数：**

- **cdev**：struct cdev类型的指针变量，指向需要关联的字符设备结构体；
    
- **fops**：file_operations类型的结构体指针变量，一般将实现操作该设备的结构体file_operations结构体作为实参。
    

**返回值：** 无

![file_operations的实现](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/characprog003.png)

### 4.4.2. 设备注册和注销[¶](#id12 "永久链接至标题")

cdev_add函数用于向内核的cdev_map散列表添加一个新的字符设备，如下所示。

cdev_add函数(内核源码/fs/char_dev.c)[¶](#id51 "永久链接至代码")

```c
int cdev_add(struct cdev *p, dev_t dev, unsigned count)
```

函数参数和返回值如下：

**参数：**

- **p**：struct cdev类型的指针，用于指定需要添加的字符设备；
    
- **dev**：dev_t类型变量，用于指定设备的起始编号；
    
- **count**：指定注册多少个设备。
    

**返回值：** 错误码

从系统中删除cdev，cdev设备将无法再打开，但任何已经打开的cdev将保持不变， 即使在cdev_del返回后，它们的FOP仍然可以调用。

cdev_del函数(内核源码/fs/char_dev.c)[¶](#id52 "永久链接至代码")

```c
void cdev_del(struct cdev *p)
```

函数参数和返回值如下：

**参数：**

- **p**：struct cdev类型的指针，用于指定需要删除的字符设备；
    

**返回值：** 无

### 4.4.3. 设备节点的创建和销毁[¶](#id13 "永久链接至标题")

创建一个设备并将其注册到文件系统

device_create函数(内核源码/drivers/base/core.c)[¶](#id53 "永久链接至代码")

```c
struct device *device_create(struct class *class, struct device *parent,
            dev_t devt, void *drvdata, const char *fmt, ...)
```

函数参数和返回值如下：

**参数：**

- **class**：指向这个设备应该注册到的struct类的指针；
    
- **parent**：指向此新设备的父结构设备(如果有)的指针；
    
- **devt**：要添加的char设备的开发；
    
- **drvdata**：要添加到设备进行回调的数据；
    
- **fmt**：输入设备名称。
    

**返回值：** 成功时返回 struct device 结构体指针， 错误时返回ERR_PTR().

删除使用device_create函数创建的设备

device_destroy函数(内核源码/drivers/base/core.c)[¶](#id54 "永久链接至代码")

```c
void device_destroy(struct class *class, dev_t devt)
```

函数参数和返回值如下：

**参数：**

- **class**：指向注册此设备的struct类的指针；
    
- **devt**：以前注册的设备的开发；
    

**返回值：** 无

除了使用代码创建设备节点，还可以使用mknod命令创建设备节点。

用法：mknod 设备名 设备类型 主设备号 次设备号

当类型为”p”时可不指定主设备号和次设备号，否则它们是必须指定的。 如果主设备号和次设备号以”0x”或”0X”开头，它们会被视作十六进制数来解析；如果以”0”开头，则被视作八进制数； 其余情况下被视作十进制数。可用的类型包括：

- b 创建(有缓冲的)区块特殊文件
    
- c, u 创建(没有缓冲的)字符特殊文件
    
- p 创建先进先出(FIFO)特殊文件
    

如：mkmod /dev/test c 2 0

创建一个字符设备/dev/test，其主设备号为2，次设备号为0。

![open函数的执行过程](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/characprog005.png)

当我们使用上述命令，创建了一个字符设备文件时，实际上就是创建了一个设备节点inode结构体， 并且将该设备的设备编号记录在成员i_rdev，将成员f_op指针指向了def_chr_fops结构体。 这就是mknod负责的工作内容，具体代码见如下。

mknod调用关系 (内核源码/mm/shmem.c)[¶](#id55 "永久链接至代码")

```c
 1  static struct inode *shmem_get_inode(struct super_block *sb, const struct inode *dir,
 2  umode_t mode, dev_t dev, unsigned long flags)
 3  {
 4     inode = new_inode(sb);
 5     if (inode) {
 6        ......
 7        switch (mode & S_IFMT) {
 8           default:
 9           inode->i_op = &shmem_special_inode_operations;
10           init_special_inode(inode, mode, dev);
11           break;
12           ......
13        }
14     } else
15     shmem_free_inode(sb);
16     return inode;
17  }
```

- 第10行：mknod命令最终执行init_special_inode函数
    

init_special_inode函数(内核源码/fs/inode.c)[¶](#id56 "永久链接至代码")

```c
 1  void init_special_inode(struct inode *inode, umode_t mode, dev_t rdev)
 2  {
 3     inode->i_mode = mode;
 4     if (S_ISCHR(mode)) {
 5        inode->i_fop = &def_chr_fops;
 6        inode->i_rdev = rdev;
 7     } else if (S_ISBLK(mode)) {
 8        inode->i_fop = &def_blk_fops;
 9        inode->i_rdev = rdev;
10     } else if (S_ISFIFO(mode))
11        inode->i_fop = &pipefifo_fops;
12     else if (S_ISSOCK(mode))
13        ;      /* leave it no_open_fops */
14     else
15        printk(KERN_DEBUG "init_special_inode: bogus i_mode (%o) for"
16              " inode %s:%lu\n", mode, inode->i_sb->s_id,
17              inode->i_ino);
18  }
```

- 第4-17行：判断文件的inode类型，如果是字符设备类型，则把def_chr_fops作为该文件的操作接口，并把设备号记录在inode->i_rdev。
    

inode上的file_operation并不是自己构造的file_operation，而是字符设备通用的def_chr_fops， 那么自己构建的file_operation等在应用程序调用open函数之后，才会绑定在文件上。接下来我们再看open函数到底做了什么。

## 4.5. open函数到底做了什么[¶](#open "永久链接至标题")

使用设备之前我们通常都需要调用open函数，这个函数一般用于设备专有数据的初始化，申请相关资源及进行设备的初始化等工作， 对于简单的设备而言，open函数可以不做具体的工作，你在应用层通过系统调用open打开设备时， 如果打开正常，就会得到该设备的文件描述符，之后，我们就可以通过该描述符对设备进行read和write等操作； open函数到底做了些什么工作？下图中列出了open函数执行的大致过程。

![open函数的执行过程](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/character_ready014.png)

户空间使用open()系统调用函数打开一个字符设备时(int fd = open(“dev/xxx”, O_RDWR))大致有以下过程：

- 在虚拟文件系统VFS中的查找对应与字符设备对应 struct inode节点
    
- 遍历散列表cdev_map，根据inod节点中的 cdev_t设备号找到cdev对象
    
- 创建struct file对象(系统采用一个数组来管理一个进程中的多个被打开的设备，每个文件秒速符作为数组下标标识了一个设备对象)
    
- 初始化struct file对象，将 struct file对象中的 file_operations成员指向 struct cdev对象中的 file_operations成员(file->fops = cdev->fops)
    
- 回调file->fops->open函数
    

我们使用的open函数在内核中对应的是sys_open函数，sys_open函数又会调用do_sys_open函数。在do_sys_open函数中， 首先调用函数get_unused_fd_flags来获取一个未被使用的文件描述符fd，该文件描述符就是我们最终通过open函数得到的值。 紧接着，又调用了do_filp_open函数，该函数通过调用函数get_empty_filp得到一个新的file结构体，之后的代码做了许多复杂的工作， 如解析文件路径，查找该文件的文件节点inode等，直接来到了函数do_dentry_open函数，如下所示。

do_dentry_open函数(位于内核源码/fs/open.c)[¶](#id57 "永久链接至代码")

```c
 1  static int do_dentry_open(struct file *f,struct inode *inode,int (*open)(struct inode *, struct file *),const struct cred *cred)
 2  {
 3     //……
 4     f->f_op = fops_get(inode->i_fop);
 5     //……
 6     if (!open)
 7     open = f->f_op->open;
 8     if (open) {
 9        error = open(inode, f);
10        if (error)
11        goto cleanup_all;
12     }
13     //……
14  }
```

- 第4行：使用fops_get函数来获取该文件节点inode的成员变量i_fop，在上图中我们使用mknod创建字符设备文件时，将def_chr_fops结构体赋值给了该设备文件inode的i_fop成员。
    
- 第7行：到了这里，我们新建的file结构体的成员f_op就指向了def_chr_fops。
    

def_chr_fops结构体(内核源码/fs/char_dev.c)[¶](#id58 "永久链接至代码")

```c
const struct file_operations def_chr_fops = {
   .open = chrdev_open,
   .llseek = noop_llseek,
};
```

最终，会执行def_chr_fops中的open函数，也就是chrdev_open函数，可以理解为一个字符设备的通用初始化函数，根据字符设备的设备号， 找到相应的字符设备，从而得到操作该设备的方法，代码实现如下。

![操作该设备的的方法](https://doc.embedfire.com/linux/rk356x/driver/zh/latest/_images/charac003.jpg)

chrdev_open函数(内核源码/fs/char_dev.c)[¶](#id59 "永久链接至代码")

```c
 1  static int chrdev_open(struct inode *inode, struct file *filp)
 2  {
 3     const struct file_operations *fops;
 4     struct cdev *p;
 5     struct cdev *new = NULL;
 6     int ret = 0;
 7     spin_lock(&cdev_lock);
 8     p = inode->i_cdev;
 9     if (!p) {
10        struct kobject *kobj;
11        int idx;
12        spin_unlock(&cdev_lock);
13        kobj = kobj_lookup(cdev_map, inode->i_rdev, &idx);
14        if (!kobj)
15           return -ENXIO;
16        new = container_of(kobj, struct cdev, kobj);
17        spin_lock(&cdev_lock);
18        /* Check i_cdev again in case somebody beat us to it whilewe dropped the lock.*/
19        p = inode->i_cdev;
20        if (!p) {
21           inode->i_cdev = p = new;
22           list_add(&inode->i_devices, &p->list);
23           new = NULL;
24        } else if (!cdev_get(p))
25           ret = -ENXIO;
26     } else if (!cdev_get(p))
27        ret = -ENXIO;
28     spin_unlock(&cdev_lock);
29     cdev_put(new);
30     if (ret)
31        return ret;
32
33     ret = -ENXIO;
34     fops = fops_get(p->ops);
35     if (!fops)
36     goto out_cdev_put;
37
38     replace_fops(filp, fops);
39     if (filp->f_op->open) {
40        ret = filp->f_op->open(inode, filp);
41        if (ret)
42        goto out_cdev_put;
43     }
44
45     return 0;
46
47     out_cdev_put:
48     cdev_put(p);
49     return ret;
50  }
```

在Linux内核中，使用结构体cdev来描述一个字符设备。

- 第8行：inode->i_rdev中保存了字符设备的设备编号，
    
- 第13行：通过函数kobj_lookup函数便可以找到该设备文件cdev结构体的kobj成员，
    
- 第16行：再通过函数container_of便可以得到该字符设备对应的结构体cdev。函数container_of的作用就是通过一个结构变量中一个成员的地址找到这个结构体变量的首地址。同时，将cdev结构体记录到文件节点inode中的i_cdev，便于下次打开该文件。
    
- 第38-43行：函数chrdev_open最终将该文件结构体file的成员f_op替换成了cdev对应的ops成员，并执行ops结构体中的open函数。
    

最后，调用上图的fd_install函数，完成文件描述符和文件结构体file的关联，之后我们使用对该文件描述符fd调用read、write函数， 最终都会调用file结构体对应的函数，实际上也就是调用cdev结构体中ops结构体内的相关函数。

总结一下整个过程，当我们使用open函数，打开设备文件时，会根据该设备的文件的设备号找到相应的设备结构体， 从而得到了操作该设备的方法。也就是说如果我们要添加一个新设备的话，我们需要提供一个设备号， 一个设备结构体以及操作该设备的方法(file_operations结构体)。

## 4.6. 字符设备驱动程序实验[¶](#id14 "永久链接至标题")

### 4.6.1. 硬件介绍[¶](#id15 "永久链接至标题")

本节实验使用Lubancat_RK系列板卡进行操作。

### 4.6.2. 实验代码讲解[¶](#id16 "永久链接至标题")

本章的示例代码目录为： **linux_driver/03_chardev**

结合前面所有的知识点，首先，字符设备驱动程序是以内核模块的形式存在的， 我们要向系统注册一个新的字符设备，需要这几样东西：字符设备结构体cdev，设备编号dev_t， 以及最最最重要的操作方式结构体file_operations。

下面，我们开始编写我们自己的字符设备驱动程序。

#### 4.6.2.1. 内核模块框架[¶](#id17 "永久链接至标题")

既然我们的设备程序是以内核模块的方式存在的，那么就需要先写出一个基本的内核框架，见如下所示。

内核模块加载函数(位于linux_driver/03_chardev/chardev.c)[¶](#id60 "永久链接至代码")

```c
 1  /* 定义字符设备的名称 */
 2  #define DEV_NAME    "chardev"
 3  /* 定义要分配的字符设备数量 */
 4  #define DEV_CNT     1
 5
 6  /* 定义设备号，用于标识字符设备 */
 7  static dev_t devno;
 8  /* 定义字符设备结构体，用于管理字符设备 */
 9  static struct cdev chr_dev;
10  /* 定义设备类结构体指针，用于在sysfs中创建设备类 */
11  struct class *class;
12  /* 定义设备结构体指针，用于在/dev目录下创建设备文件 */
13  struct device *device;
14
15  /* 定义主设备号 */
16  int major;
17  /* 定义次设备号 */
18  int minor;
19
20  static int __init chrdev_init(void)
21  {
22     int ret = 0;
23
24     /* 打印字符设备驱动初始化信息 */
25     printk("chrdev init\n");
26
27     /* 动态分配字符设备号 */
28     ret = alloc_chrdev_region(&devno, 0, DEV_CNT, DEV_NAME);
29     if (ret < 0) {
30        /* 若分配失败，打印错误信息并跳转到错误处理标签 */
31        printk("fail to alloc devno\n");
32        goto alloc_err;
33     }
34     /* 获取主设备号 */
35     major = MAJOR(devno);
36     /* 获取次设备号 */
37     minor = MINOR(devno);
38     /* 打印分配到的主设备号和次设备号 */
39     printk("major=%d,minor=%d\n", major, minor);
40
41     /* 设置字符设备的所有者为当前模块 */
42     chr_dev.owner = THIS_MODULE;
43     /* 初始化字符设备结构体，关联文件操作结构体 */
44     cdev_init(&chr_dev, &chr_dev_fops);
45
46     /* 将字符设备添加到内核中 */
47     ret = cdev_add(&chr_dev, devno, DEV_CNT);
48     if (ret < 0)
49     {
50        /* 若添加失败，打印错误信息并跳转到错误处理标签 */
51        printk("fail to add cdev\n");
52        goto add_err;
53     }
54
55     /* 在sysfs中创建设备类 */
56     class = class_create(THIS_MODULE, DEV_NAME);
57     if (IS_ERR(class)) {
58        /* 若创建设备类失败，打印错误信息并跳转到错误处理标签 */
59        printk("fail to add class\n");
60        goto class_err;
61     }
62
63     /* 创建1个设备文件 */
64     device = device_create(class, NULL, MKDEV(major, 0), NULL, DEV_NAME);
65     if (IS_ERR(device)) {
66        /* 若创建设备文件失败，打印错误信息并跳转到错误处理标签 */
67        printk("fail to create device\n");
68        goto device_err;
69     }
70     /* 打印设备文件创建成功信息 */
71     printk("device created\n");
72
73     return 0;
74
75  device_err:
76     /* 若创建设备文件失败，销毁已创建的设备文件和设备类 */
77     device_destroy(class, MKDEV(major, 0));
78     class_destroy(class);
79
80  class_err:
81     /* 若创建设备类失败，从内核中移除字符设备 */
82     cdev_del(&chr_dev);
83
84  add_err:
85     /* 若添加字符设备失败，注销已分配的设备号 */
86     unregister_chrdev_region(devno, DEV_CNT);
87
88  alloc_err:
89     return ret;
90  }
91
92  module_init(chrdev_init);
```

- 第7-18行：定义字符设备驱动核心全局变量，包含设备号、字符设备结构体、设备类、设备文件指针、主次设备号；
    
- 第28-39行：初始化函数第一步，动态分配字符设备号；失败则跳转错误处理，成功则提取并打印主次设备号；
    
- 第42-53行：初始化字符设备结构体并关联文件操作集，将字符设备添加到内核；失败则跳转对应错误处理；
    
- 第56-61行：在sysfs中创建设备类；创建失败则跳转对应错误处理；
    
- 第64-71行：创建设备文件（/dev目录下）；创建失败则跳转设备错误处理，成功则打印创建信息。
    

模块的卸载函数就相对简单一下，只需要完成注销设备号，以及移除字符设备，如下所示。

内核模块卸载函数(位于linux_driver/03_chardev/chardev.c)[¶](#id61 "永久链接至代码")

```c
 1  static void __exit chrdev_exit(void)
 2  {
 3     /* 打印字符设备驱动退出信息 */
 4     printk("chrdev exit!\n");
 5
 6     /* 从内核中移除字符设备 */
 7     cdev_del(&chr_dev);
 8     /* 注销已分配的设备号 */
 9     unregister_chrdev_region(devno, DEV_CNT);
10
11     /* 销毁设备文件 */
12     device_destroy(class, MKDEV(major, 0));
13
14     /* 销毁设备类 */
15     class_destroy(class);
16  }
17
18  module_exit(chrdev_exit);
```

#### 4.6.2.2. 文件操作方式的实现[¶](#id18 "永久链接至标题")

下面开始实现字符设备最重要的部分：文件操作方式结构体file_operations，见如下所示。

file_operations结构体(位于linux_driver/03_chardev/chardev.c)[¶](#id62 "永久链接至代码")

```c
static struct file_operations  chr_dev_fops =
{
   .owner = THIS_MODULE,
   .open = chr_dev_open,
   .release = chr_dev_release,
   .write = chr_dev_write,
   .read = chr_dev_read,
};
```

由于这个字符设备是一个虚拟的设备，与硬件并没有什么关联，因此，open函数与release直接返回0即可，我们重点关注write以及read函数的实现。

chr_dev_open函数与chr_dev_release函数(位于linux_driver/03_chardev/chardev.c)[¶](#id63 "永久链接至代码")

```c
 1  /* 定义读写缓冲区的大小为128字节 */
 2  #define BUFF_SIZE   128
 3  /* 定义一个设备的缓冲区，用于数据读写 */
 4  static char vbuf[BUFF_SIZE];
 5
 6  static int chr_dev_open(struct inode *inode, struct file *filp)
 7  {
 8     /* 打印字符设备打开信息 */
 9     printk("chardev open\n");
10
11     /* 关联vbuf缓冲区 */
12     filp->private_data = vbuf;
13
14     return 0;
15  }
16
17  static int chr_dev_release(struct inode *inode, struct file *filp)
18  {
19     /* 打印字符设备释放信息 */
20     printk("chardev release\n");
21     return 0;
22  }
```

我们在open函数与release函数中打印相关的调试信息，如上方代码所示。

chr_dev_write函数(位于linux_driver/03_chardev/chardev.c)[¶](#id64 "永久链接至代码")

```c
 1  static ssize_t chr_dev_write(struct file *filp, const char __user * buf, size_t count, loff_t *ppos)
 2  {
 3     int ret = 0;
 4     /* 获取文件结构体中保存的缓冲区地址 */
 5     char *vbuf = filp->private_data;
 6
 7     /* 将用户空间的数据拷贝到内核空间的缓冲区 */
 8     ret = copy_from_user(vbuf, buf, count);
 9     if (ret == 0) {
10        /* 若拷贝成功，打印写入的数据 */
11        printk("write data: %s\n", vbuf);
12     } else {
13        /* 若拷贝失败，打印写入失败信息 */
14        printk("Write failure!\n");
15     }
16     return 0;
17  }
```

当我们的应用程序调用write函数，最终就调用我们的chr_dev_write函数。

- 第5行：从文件结构体filp的私有数据域（private_data）中获取预先关联的内核空间缓冲区地址；
    
- 第8行：调用内核函数copy_from_user，将用户空间缓冲区buf的数据拷贝到内核空间缓冲区vbuf，拷贝长度为count，返回值为未成功拷贝的字节数。
    

chr_dev_read函数(位于linux_driver/03_chardev/chardev.c)[¶](#id65 "永久链接至代码")

```c
 1  /* 定义要传输给用户空间的数据 */
 2  static char data[] = {"chardev driver"};
 3
 4  static ssize_t chr_dev_read(struct file *filp, char __user * buf, size_t count, loff_t *ppos)
 5  {
 6     int ret = 0;
 7     /* 获取文件结构体中保存的缓冲区地址 */
 8     char *vbuf = filp->private_data;
 9
10     /* 将默认数据拷贝到缓冲区 */
11     memcpy(vbuf, data, sizeof(data));
12     /* 将缓冲区的数据拷贝到用户空间 */
13     ret = copy_to_user(buf, vbuf, count);
14     if (ret != 0) {
15        /* 若拷贝失败，打印读取失败信息 */
16        printk("Read failure!\n");
17     }
18
19     return 0;
20  }
```

同样的，当我们应用程序调用read函数，则会执行chr_dev_read函数。

- 第8行：从文件结构体filp的私有数据域（private_data）中获取预先关联的内核空间缓冲区地址；
    
- 第11行：调用memcpy将默认数据data拷贝到内核空间缓冲区vbuf，拷贝长度为data的字节大小；
    
- 第13行：调用内核函数copy_to_user，将内核缓冲区vbuf的数据拷贝到用户空间缓冲区buf，拷贝长度为count，返回值为未成功拷贝的字节数。
    

#### 4.6.2.3. 应用测试程序[¶](#id19 "永久链接至标题")

下面，我们开始编写应用程序，来读写我们的字符设备，如下所示。

chardev_app.c(位于linux_driver/03_chardev/chardev_app.c)[¶](#id66 "永久链接至代码")

```c
 1  #include <stdio.h>
 2  #include <unistd.h>
 3  #include <fcntl.h>
 4  #include <string.h>
 5
 6  int main(int argc, char *argv[])
 7  {
 8     int fd, ret;
 9     char *file_path;
10     char usr_data[] = "Hello World\n";
11     char wbuf[128];
12     char rbuf[128];
13
14     if(argc != 2){
15        printf("Error Usage!\n");
16        return -1;
17     }
18
19     file_path = argv[1];
20
21     printf("--------------写入数据--------------\n");
22
23     //打开文件
24     fd = open(file_path, O_RDWR);
25     if(fd < 0){
26        printf("Can't open file: %s\n", file_path);
27        return -1;
28     }
29
30     //写入数据
31     memcpy(wbuf, usr_data, sizeof(usr_data));
32     ret = write(fd, wbuf, strlen(wbuf));
33     if(ret < 0){
34        printf("write file %s failed!\n", file_path);
35        return -1;
36     }
37
38     //写入完毕，关闭文件
39     close(fd);
40
41     sleep(1);
42
43     printf("--------------读取数据--------------\n");
44
45     //打开文件
46     fd = open(file_path, O_RDWR);
47     if(fd < 0){
48        printf("Can't open file: %s\n", file_path);
49        return -1;
50     }
51     //读取文件内容
52     ret = read(fd, rbuf, 128);
53     if(ret < 0){
54        printf("read file %s failed!\n", file_path);
55        return -1;
56     }else{
57        printf("read data:%s\n",rbuf);
58     }
59
60     //读取完毕，关闭文件
61     close(fd);
62
63     return 0;
64  }
```

- 第24行：以可读可写的方式打开我们创建的字符设备驱动；
    
- 第31-39行：写入数据然后关闭；
    
- 第46-61行：再次打开设备将数据读取出来。
    

### 4.6.3. 实验准备[¶](#id20 "永久链接至标题")

获取内核模块源码，将配套代码linux_driver/放到内核代码同级目录，然后进入linux_driver/03_chardev/目录中。

#### 4.6.3.1. Makefile说明[¶](#makefile "永久链接至标题")

makefile(位于linux_driver/03_chardev/Makefile)[¶](#id67 "永久链接至代码")

```makefile
 1  #指定内核路径,可以是相对路径或绝对路径
 2  KERNEL_DIR=../../kernel/
 3  #KERNEL_DIR=/home/guest/LubanCat_Linux_rk356x_SDK/kernel/
 4
 5  #指定目标架构为arm64
 6  ARCH=arm64
 7
 8  #指定交叉编译工具链的前缀
 9  CROSS_COMPILE=aarch64-linux-gnu-
10
11  #导出为环境变量
12  export  ARCH  CROSS_COMPILE
13
14  #指定要编译的内核模块目标文件
15  obj-m := chardev.o
16
17  test_app =  chardev_app
18
19  #all :默认目标，执行时会编译驱动模块
20  #$(MAKE) ：调用make工具
21  #-C $(KERNEL_DIR) ：指定的内核源码目录
22  #M=$(CURDIR) ：模块的源码位于当前目录
23  #modules ：编译模块
24  all:
25     $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) modules
26     $(CROSS_COMPILE)gcc -o $(test_app) $(test_app).c
27
28  .PHONE:clean
29
30  #清理编译生成的文件
31  clean:
32     $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) clean
33     rm $(test_app)
```

Makefile与此前相比，增加了编译测试程序部分。

#### 4.6.3.2. 编译命令说明[¶](#id21 "永久链接至标题")

在实验目录下输入如下命令来编译驱动模块：

```bash
 1  #进入chardev例程源码目录
 2  cd linux_driver/03_chardev
 3
 4  #编译驱动模块
 5  make
 6
 7  #信息输出如下
 8  make -C ../../kernel/ M=/home/guest/linux_driver/03_chardev modules
 9  make[1]: Entering directory '/home/guest/kernel'
10  CC [M]  /home/guest/linux_driver/03_chardev/chardev.o
11  Building modules, stage 2.
12  MODPOST 1 modules
13  CC      /home/guest/linux_driver/03_chardev/chardev.mod.o
14  LD [M]  /home/guest/linux_driver/03_chardev/chardev.ko
15  make[1]: Leaving directory '/home/guest/kernel'
16  aarch64-linux-gnu-gcc -o chardev_app chardev_app.c
```

编译成功后，实验目录下会生成名为”chardev.ko”驱动模块文件和”chardev_app”测试程序。

### 4.6.4. 程序运行结果[¶](#id22 "永久链接至标题")

将chardev.ko和chardev_app文件拷贝到开发板，执行以下进行命令：

```bash
 1  #加载驱动模块
 2  sudo insmod chardev.ko
 3
 4  #信息输出如下
 5  [  706.156347] chrdev init
 6  [  706.156468] major=236,minor=0
 7  [  706.157107] device created
 8
 9  #查看注册的设备
10  cat /proc/devices | grep chardev
11
12  #信息输出如下
13  236 chardev
14
15  #查看注册生成的字符设备
16  ls -l /dev/chardev
17
18  #信息输出如下
19  crw------- 1 root root 236, 0 Mar 20 14:44 /dev/chardev
```

我们从/proc/devices文件中，可以看到我们注册的字符设备chardev的主设备号为236。 从/dev/chardev详细信息可以看到，主设备号为236，次设备号为0。

以root权限运行chardev_app测试程序。

```bash
 1  #读写字符设备
 2  sudo ./chardev_app /dev/chardev
 3
 4  #信息输出如下
 5  --------------写入数据--------------
 6  [  871.201589] chardev open
 7  [  871.201693] write data: Hello World
 8  [  871.201693]
 9  [  871.201714] chardev release
10  --------------读取数据--------------
11  [  872.202010] chardev open
12  read data:chardev driver
13  [  872.202211] chardev release
```

可以从写入数据部分的内核打印信息看到驱动获取到了用户写入的数据Hello World， 从读取数据部分应用程序输出看到，成功从驱动获取到数据chardev driver。

## 4.7. 一个驱动支持多个设备[¶](#id23 "永久链接至标题")

本章的示例代码目录为： **linux_driver/04_moredev**

前文我们基于chardev.c实现了单实例字符设备驱动，完成了单个设备的注册、打开、读写、卸载全流程，理解了字符设备驱动的基础框架。 但在实际嵌入式开发中，同一类硬件往往存在多个实例（如多路串口、多个LED），如果为每个设备单独编写驱动，会造成代码冗余、设备号资源浪费。

Linux内核提供了一套驱动管控多个同类型设备的机制，核心思路是：主设备号标识驱动，次设备号区分设备实例， 共用一套file_operations操作接口，通过私有数据实现设备资源隔离。

本节基于单设备驱动基础，通过两个案例详细讲解两种多设备实现方案。

### 4.7.1. 实现方式一：独立缓冲区+次设备号判断[¶](#id24 "永久链接至标题")

该方案是入门级多设备实现，在单设备基础上小幅修改，通过独立全局缓冲区存储多设备数据， 在open函数中通过次设备号判断绑定对应缓冲区，代码改动小、易于理解，适合快速实现少量多设备场景。

#### 4.7.1.1. 实验代码讲解[¶](#id25 "永久链接至标题")

1. 将设备数量改为2，定义两个独立的读写缓冲区，分别对应次设备号0和1，将设备结构体指针改为指针数组：
    

宏定义修改部分(位于linux_driver/04_moredev/moredev1.c)[¶](#id68 "永久链接至代码")

```c
 1  /* 定义字符设备的名称 */
 2  #define DEV_NAME    "moredev"
 3  /* 定义要分配的字符设备数量 */
 4  #define DEV_CNT     2
 5
 6  /* 定义读写缓冲区的大小为128字节 */
 7  #define BUFF_SIZE   128
 8  /* 定义第一个设备的缓冲区，用于数据读写 */
 9  static char vbuf1[BUFF_SIZE];
10  /* 定义第二个设备的缓冲区，用于数据读写 */
11  static char vbuf2[BUFF_SIZE];
12  /* 定义要传输给用户空间的数据 */
13  static char data[] = {"chardev driver"};
14
15  /* 定义设备号，用于标识字符设备 */
16  static dev_t devno;
17  /* 定义字符设备结构体，用于管理字符设备 */
18  static struct cdev chr_dev;
19  /* 定义设备类结构体指针，用于在sysfs中创建设备类 */
20  struct class *class;
21  /* 定义设备结构体指针数组，用于在/dev目录下创建设备文件 */
22  struct device *devices[DEV_CNT];
```

2. 通过MINOR(inode->i_rdev)获取当前打开设备的次设备号，用switch-case判断，将对应缓冲区地址赋值给filp->private_data，实现设备与资源的绑定：
    

chr_dev_open函数修改(位于linux_driver/04_moredev/moredev1.c)[¶](#id69 "永久链接至代码")

```c
 1  static int chr_dev_open(struct inode *inode, struct file *filp)
 2  {
 3     /* 打印字符设备打开信息 */
 4     printk("chardev open\n");
 5
 6     /* 根据次设备号选择对应的缓冲区 */
 7     switch (MINOR(inode->i_rdev))
 8     {
 9        case 0:
10        {
11              /* 次设备号为 0 时，使用 vbuf1 */
12              filp->private_data = vbuf1;
13              break;
14        }
15        case 1:
16        {
17              /* 次设备号为 1 时，使用 vbuf2 */
18              filp->private_data = vbuf2;
19              break;
20        }
21     }
22     return 0;
23  }
```

- 第7行：使用宏定义MINOR来获取该设备文件的次设备号。
    
- 第9-20行：对于次设备号为0的设备，负责管理vbuf1的数据，对于次设备号为1的设备，则用于管理vbuf2的数据。
    

3. read/write函数与chardev.c完全一致，无需修改，直接通过filp->private_data获取当前设备的缓冲区，实现数据隔离。
    

read/write函数(位于linux_driver/04_moredev/moredev1.c)[¶](#id70 "永久链接至代码")

```c
 1  static ssize_t chr_dev_write(struct file *filp, const char __user * buf, size_t count, loff_t *ppos)
 2  {
 3     int ret = 0;
 4     /* 获取文件结构体中保存的缓冲区地址 */
 5     char *vbuf = filp->private_data;
 6
 7     /* 将用户空间的数据拷贝到内核空间的缓冲区 */
 8     ret = copy_from_user(vbuf, buf, count);
 9     if (ret == 0) {
10        /* 若拷贝成功，打印写入的数据 */
11        printk("write data: %s\n", vbuf);
12     } else {
13        /* 若拷贝失败，打印写入失败信息 */
14        printk("Write failure!\n");
15     }
16     return 0;
17  }
18
19  static ssize_t chr_dev_read(struct file *filp, char __user * buf, size_t count, loff_t *ppos)
20  {
21     int ret = 0;
22     /* 获取文件结构体中保存的缓冲区地址 */
23     char *vbuf = filp->private_data;
24
25     /* 将默认数据拷贝到缓冲区 */
26     memcpy(vbuf, data, sizeof(data));
27     /* 将缓冲区的数据拷贝到用户空间 */
28     ret = copy_to_user(buf, vbuf, count);
29     if (ret != 0) {
30        /* 若拷贝失败，打印读取失败信息 */
31        printk("Read failure!\n");
32     }
33
34     return 0;
35  }
```

4. 初始化函数仅修改设备节点创建逻辑，循环创建2个设备节点（/dev/moredev0、/dev/moredev1）。
    

chrdev_init函数(位于linux_driver/04_moredev/moredev1.c)[¶](#id71 "永久链接至代码")

```c
 1  static int __init chrdev_init(void)
 2  {
 3     int ret = 0;
 4     int i;
 5
 6     /* 打印字符设备驱动初始化信息 */
 7     printk("chrdev init\n");
 8
 9     /* 动态分配字符设备号 */
10     ret = alloc_chrdev_region(&devno, 0, DEV_CNT, DEV_NAME);
11     if (ret < 0) {
12        /* 若分配失败，打印错误信息并跳转到错误处理标签 */
13        printk("fail to alloc devno\n");
14        goto alloc_err;
15     }
16     /* 获取主设备号 */
17     major = MAJOR(devno);
18     /* 获取次设备号 */
19     minor = MINOR(devno);
20     /* 打印分配到的主设备号和次设备号 */
21     printk("major=%d,minor=%d\n", major, minor);
22
23     /* 设置字符设备的所有者为当前模块 */
24     chr_dev.owner = THIS_MODULE;
25     /* 初始化字符设备结构体，关联文件操作结构体 */
26     cdev_init(&chr_dev, &chr_dev_fops);
27
28     /* 将字符设备添加到内核中 */
29     ret = cdev_add(&chr_dev, devno, DEV_CNT);
30     if (ret < 0)
31     {
32        /* 若添加失败，打印错误信息并跳转到错误处理标签 */
33        printk("fail to add cdev\n");
34        goto add_err;
35     }
36
37     /* 在sysfs中创建设备类 */
38     class = class_create(THIS_MODULE, DEV_NAME);
39     if (IS_ERR(class)) {
40        /* 若创建设备类失败，打印错误信息并跳转到错误处理标签 */
41        printk("fail to add class\n");
42        goto class_err;
43     }
44
45     /* 循环创建设备文件 */
46     for (i = 0; i < DEV_CNT; i++) {
47        /* 根据主设备号和次设备号创建设备文件 */
48        devices[i] = device_create(class, NULL, MKDEV(major, i), NULL, "%s%d", DEV_NAME, i);
49        if (IS_ERR(devices[i])) {
50              /* 若创建设备文件失败，打印错误信息并跳转到错误处理标签 */
51              printk("fail to create device%d\n", i);
52              goto device_err;
53        }
54        /* 打印设备文件创建成功信息 */
55        printk("device%d created\n", i);
56     }
57
58     return 0;
59
60  device_err:
61     /* 若创建设备文件失败，销毁已创建的设备文件和设备类 */
62     while (i--) {
63        device_destroy(class, MKDEV(major, i));
64     }
65     class_destroy(class);
66
67  class_err:
68     /* 若创建设备类失败，从内核中移除字符设备 */
69     cdev_del(&chr_dev);
70
71  add_err:
72     /* 若添加字符设备失败，注销已分配的设备号 */
73     unregister_chrdev_region(devno, DEV_CNT);
74
75  alloc_err:
76     return ret;
77  }
```

5. 卸载函数与chardev.c基本一致，销毁设备文件改为循环销毁全部设备文件：
    

chrdev_exit函数(位于linux_driver/04_moredev/moredev1.c)[¶](#id72 "永久链接至代码")

```c
 1  static void __exit chrdev_exit(void)
 2  {
 3     int i;
 4
 5     /* 打印字符设备驱动退出信息 */
 6     printk("chrdev exit!\n");
 7
 8     /* 从内核中移除字符设备 */
 9     cdev_del(&chr_dev);
10     /* 注销已分配的设备号 */
11     unregister_chrdev_region(devno, DEV_CNT);
12
13     /* 循环销毁设备文件 */
14     for (i = 0; i < DEV_CNT; i++) {
15        device_destroy(class, MKDEV(major, i));
16     }
17
18     /* 销毁设备类 */
19     class_destroy(class);
20  }
```

#### 4.7.1.2. 实验准备[¶](#id26 "永久链接至标题")

获取内核模块源码，将配套代码linux_driver/放到内核代码同级目录，然后进入linux_driver/04_moredev/目录中。

##### 4.7.1.2.1. Makefile说明[¶](#id27 "永久链接至标题")

makefile(位于linux_driver/04_moredev/Makefile)[¶](#id73 "永久链接至代码")

```makefile
 1  #指定内核路径,可以是相对路径或绝对路径
 2  KERNEL_DIR=../../kernel/
 3  #KERNEL_DIR=/home/guest/LubanCat_Linux_rk356x_SDK/kernel/
 4
 5  #指定目标架构为arm64
 6  ARCH=arm64
 7
 8  #指定交叉编译工具链的前缀
 9  CROSS_COMPILE=aarch64-linux-gnu-
10
11  #导出为环境变量
12  export  ARCH  CROSS_COMPILE
13
14  #指定要编译的内核模块目标文件
15  obj-m := moredev1.o
16
17  test_app =  chardev_app
18
19  #all :默认目标，执行时会编译驱动模块
20  #$(MAKE) ：调用make工具
21  #-C $(KERNEL_DIR) ：指定的内核源码目录
22  #M=$(CURDIR) ：模块的源码位于当前目录
23  #modules ：编译模块
24  all:
25     $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) modules
26     $(CROSS_COMPILE)gcc -o $(test_app) $(test_app).c
27
28  .PHONE:clean
29
30  #清理编译生成的文件
31  clean:
32     $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) clean
33     rm $(test_app)
```

Makefile与此前相比，只修改了要编译的内核模块目标文件。

##### 4.7.1.2.2. 编译命令说明[¶](#id28 "永久链接至标题")

在实验目录下输入如下命令来编译驱动模块：

```bash
 1  #进入moredev例程源码目录
 2  cd linux_driver/04_moredev
 3
 4  #编译驱动模块
 5  make
 6
 7  #信息输出如下
 8  make -C ../../kernel/ M=/home/guest/linux_driver/04_moredev modules
 9  make[1]: Entering directory '/home/guest/kernel'
10  CC [M]  /home/guest/linux_driver/04_moredev/moredev1.o
11  Building modules, stage 2.
12  MODPOST 1 modules
13  CC      /home/guest/linux_driver/04_moredev/moredev1.mod.o
14  LD [M]  /home/guest/linux_driver/04_moredev/moredev1.ko
15  make[1]: Leaving directory '/home/guest/kernel'
16  aarch64-linux-gnu-gcc -o chardev_app chardev_app.c
```

编译成功后，实验目录下会生成名为“moredev1.ko”驱动模块文件和“chardev_app”测试程序。

#### 4.7.1.3. 程序运行结果[¶](#id29 "永久链接至标题")

将moredev1.ko和chardev_app文件拷贝到开发板，执行以下进行命令：

```bash
 1  #加载驱动模块
 2  sudo insmod moredev1.ko
 3
 4  #信息输出如下
 5  [ 4138.711128] chrdev init
 6  [ 4138.711216] major=236,minor=0
 7  [ 4138.711980] device0 created
 8  [ 4138.712176] device1 created
 9
10  #查看注册的设备
11  cat /proc/devices | grep moredev
12
13  #信息输出如下
14  236 moredev
15
16  #查看注册生成的字符设备文件
17  ls -l /dev/moredev*
18
19  #信息输出如下
20  crw------- 1 root root 236, 0 Mar 20 15:42 /dev/moredev0
21  crw------- 1 root root 236, 1 Mar 20 15:42 /dev/moredev1
```

我们从/proc/devices文件中，可以看到我们注册的字符设备moredev的主设备号为236。 从/dev/moredev*详细信息可以看到，/dev/moredev0主设备号为236，次设备号为0，/dev/moredev1主设备号为236，次设备号为1。

以root权限运行chardev_app测试程序：

```bash
 1  #读写字符设备
 2  sudo ./chardev_app /dev/moredev0
 3
 4  #信息输出如下
 5  --------------写入数据--------------
 6  [ 4286.859838] chardev open
 7  [ 4286.859952] write data: Hello World
 8  [ 4286.859952]
 9  [ 4286.859973] chardev release
10  --------------读取数据--------------
11  read data:chardev driver
12  [ 4287.860309] chardev open
13  [ 4287.860478] chardev release
14
15  #同理读写/dev/moredev1效果是一样的
16  sudo ./chardev_app /dev/moredev1
```

可以从写入数据部分的内核打印信息看到驱动获取到了用户写入的数据Hello World， 从读取数据部分应用程序输出看到，成功从驱动获取到数据chardev driver。

### 4.7.2. 实现方式二：结构体封装+container_of[¶](#container-of "永久链接至标题")

该方案是Linux内核标准多设备驱动写法，采用面向对象封装思想，将cdev结构体和设备私有资源（缓冲区、硬件配置等）封装为自定义结构体，每个设备对应独立结构体实例； 通过container_of宏反向获取设备实例，摒弃硬编码判断，扩展性强、代码规范，适合批量多设备场景。

#### 4.7.2.1. 实验代码讲解[¶](#id30 "永久链接至标题")

1. 自定义结构体封装内核cdev对象和设备私有资源，实现设备资源的一体化管理：
    

宏定义修改(位于linux_driver/04_moredev/moredev2.c)[¶](#id74 "永久链接至代码")

```c
 1  /* 定义字符设备的名称 */
 2  #define DEV_NAME    "moredev"
 3  /* 定义要分配的字符设备数量 */
 4  #define DEV_CNT     2
 5
 6  /* 定义读写缓冲区的大小为128字节 */
 7  #define BUFF_SIZE   128
 8
 9  /* 定义要传输给用户空间的数据 */
10  static char data[] = {"chardev driver"};
11
12  /* 定义设备号，用于标识字符设备 */
13  static dev_t devno;
14
15  /*
16  * 自定义字符设备结构体
17  * 包含一个 cdev 结构体用于字符设备的管理
18  * 以及一个大小为 BUFF_SIZE 的缓冲区 vbuf 用于数据读写
19  */
20  struct chr_dev {
21     struct cdev dev;
22     char vbuf[BUFF_SIZE];
23  };
24  /* 定义字符设备结构体数组，用于管理多个字符设备 */
25  static struct chr_dev chr_devs[DEV_CNT];
26
27  /* 定义设备类结构体指针，用于在sysfs中创建设备类 */
28  struct class *class;
29  /* 定义设备结构体指针数组，用于在/dev目录下创建设备文件 */
30  struct device *devices[DEV_CNT];
31
32  /* 定义主设备号 */
33  int major;
34  /* 定义次设备号 */
35  int minor;
```

2. 内核打开设备调用open函数时，会将对应cdev地址存入inode->i_cdev，通过container_of宏， 可从内嵌cdev地址反向计算出自定义结构体的首地址，实现设备实例的自动化绑定，消除switch-case硬编码：

open函数(位于linux_driver/04_moredev/moredev2.c)[¶](#id75 "永久链接至代码")

```c
static int chr_dev_open(struct inode *inode, struct file *filp)
{
   /* 打印字符设备打开信息 */
   printk("chardev open\n");
   /* 通过 container_of 宏获取对应的 chr_dev 结构体地址 */
   filp->private_data = container_of(inode->i_cdev, struct chr_dev, dev);
   return 0;
}
```

3. 读写函数从私有数据中取出自定义结构体，直接访问专属缓冲区：
    

read/write函数(位于linux_driver/04_moredev/moredev2.c)[¶](#id76 "永久链接至代码")

```c
 1  static ssize_t chr_dev_write(struct file *filp, const char __user * buf, size_t count, loff_t *ppos)
 2  {
 3     int ret = 0;
 4     /* 获取文件结构体中保存的 chr_dev 结构体指针 */
 5     struct chr_dev *dev = filp->private_data;
 6     /* 获取对应的缓冲区地址 */
 7     char *vbuf = dev->vbuf;
 8     /* 将用户空间的数据拷贝到内核空间的缓冲区 */
 9     ret = copy_from_user(vbuf, buf, count);
10     if (ret == 0) {
11        /* 若拷贝成功，打印写入的数据 */
12        printk("write data: %s\n", vbuf);
13     } else {
14        /* 若拷贝失败，打印写入失败信息 */
15        printk("Write failure!\n");
16     }
17     return 0;
18  }
19
20  static ssize_t chr_dev_read(struct file *filp, char __user * buf, size_t count, loff_t *ppos)
21  {
22     int ret = 0;
23     /* 获取文件结构体中保存的 chr_dev 结构体指针 */
24     struct chr_dev *dev = filp->private_data;
25     /* 获取对应的缓冲区地址 */
26     char *vbuf = dev->vbuf;
27     /* 将默认数据拷贝到缓冲区 */
28     memcpy(vbuf, data, sizeof(data));
29     /* 将缓冲区的数据拷贝到用户空间 */
30     ret = copy_to_user(buf, vbuf, count);
31     if (ret != 0) {
32        /* 若拷贝失败，打印读取失败信息 */
33        printk("Read failure!\n");
34     }
35
36     return 0;
37  }
```

4. 遍历设备实例数组，逐个初始化cdev、注册设备、创建设备节点，每个设备对应独立cdev：
    

chrdev_init函数(位于linux_driver/04_moredev/moredev2.c)[¶](#id77 "永久链接至代码")

```c
 1  static int __init chrdev_init(void)
 2  {
 3     int ret = 0;
 4     int i;
 5
 6     /* 打印字符设备驱动初始化信息 */
 7     printk("chrdev init\n");
 8
 9     /* 动态分配字符设备号 */
10     ret = alloc_chrdev_region(&devno, 0, DEV_CNT, DEV_NAME);
11     if (ret < 0) {
12        /* 若分配失败，打印错误信息并跳转到错误处理标签 */
13        printk("fail to alloc devno\n");
14        goto alloc_err;
15     }
16     /* 获取主设备号 */
17     major = MAJOR(devno);
18     /* 获取次设备号 */
19     minor = MINOR(devno);
20     /* 打印分配到的主设备号和次设备号 */
21     printk("major=%d,minor=%d\n", major, minor);
22     /* 循环初始化并添加每个字符设备 */
23     for (i = 0; i < DEV_CNT; i++) {
24        /* 初始化字符设备结构体，关联文件操作结构体 */
25        cdev_init(&chr_devs[i].dev, &chr_dev_fops);
26        /* 设置字符设备的所有者为当前模块 */
27        chr_devs[i].dev.owner = THIS_MODULE;
28        /* 将字符设备添加到内核中 */
29        ret = cdev_add(&chr_devs[i].dev, MKDEV(major, i), 1);
30        if (ret < 0) {
31              /* 若添加失败，打印错误信息并跳转到错误处理标签 */
32              printk("fail to add cdev for device%d\n", i);
33              goto add_err;
34        }
35     }
36     /* 在sysfs中创建设备类 */
37     class = class_create(THIS_MODULE, DEV_NAME);
38     if (IS_ERR(class)) {
39        /* 若创建设备类失败，打印错误信息并跳转到错误处理标签 */
40        printk("fail to add class\n");
41        goto class_err;
42     }
43
44     /* 循环创建设备文件 */
45     for (i = 0; i < DEV_CNT; i++) {
46        /* 根据主设备号和次设备号创建设备文件 */
47        devices[i] = device_create(class, NULL, MKDEV(major, i), NULL, "%s%d", DEV_NAME, i);
48        if (IS_ERR(devices[i])) {
49              /* 若创建设备文件失败，打印错误信息并跳转到错误处理标签 */
50              printk("fail to create device%d\n", i);
51              goto device_err;
52        }
53        /* 打印设备文件创建成功信息 */
54        printk("device%d created\n", i);
55     }
56
57     return 0;
58
59  device_err:
60     /* 若创建设备文件失败，销毁已创建的设备文件和设备类 */
61     while (i--) {
62        device_destroy(class, MKDEV(major, i));
63     }
64     class_destroy(class);
65
66  class_err:
67     /* 若创建设备类失败，从内核中移除所有字符设备 */
68     for (i = 0; i < DEV_CNT; i++) {
69        cdev_del(&chr_devs[i].dev);
70     }
71
72  add_err:
73     /* 若添加字符设备失败，注销已分配的设备号 */
74     unregister_chrdev_region(devno, DEV_CNT);
75
76  alloc_err:
77     return ret;
78  }
```

5. 卸载函数批量释放资源，按初始化反向顺序，逐个注销cdev、销毁设备节点、释放设备号：
    

chrdev_exit函数(位于linux_driver/04_moredev/moredev2.c)[¶](#id78 "永久链接至代码")

```c
 1  static void __exit chrdev_exit(void)
 2  {
 3     int i;
 4
 5     /* 打印字符设备驱动退出信息 */
 6     printk("chrdev exit!\n");
 7
 8     /* 从内核中移除所有字符设备 */
 9     for (i = 0; i < DEV_CNT; i++) {
10        cdev_del(&chr_devs[i].dev);
11     }
12     /* 注销已分配的设备号 */
13     unregister_chrdev_region(devno, DEV_CNT);
14
15     /* 循环销毁设备文件 */
16     for (i = 0; i < DEV_CNT; i++) {
17        device_destroy(class, MKDEV(major, i));
18     }
19
20     /* 销毁设备类 */
21     class_destroy(class);
22  }
```

#### 4.7.2.2. 实验准备[¶](#id31 "永久链接至标题")

获取内核模块源码，将配套代码linux_driver/放到内核代码同级目录，然后进入linux_driver/04_moredev/目录中。

##### 4.7.2.2.1. Makefile说明[¶](#id32 "永久链接至标题")

makefile(位于linux_driver/04_moredev/Makefile)[¶](#id79 "永久链接至代码")

```makefile
 1  #指定内核路径,可以是相对路径或绝对路径
 2  KERNEL_DIR=../../kernel/
 3  #KERNEL_DIR=/home/guest/LubanCat_Linux_rk356x_SDK/kernel/
 4
 5  #指定目标架构为arm64
 6  ARCH=arm64
 7
 8  #指定交叉编译工具链的前缀
 9  CROSS_COMPILE=aarch64-linux-gnu-
10
11  #导出为环境变量
12  export  ARCH  CROSS_COMPILE
13
14  #指定要编译的内核模块目标文件
15  obj-m := moredev2.o
16
17  test_app =  chardev_app
18
19  #all :默认目标，执行时会编译驱动模块
20  #$(MAKE) ：调用make工具
21  #-C $(KERNEL_DIR) ：指定的内核源码目录
22  #M=$(CURDIR) ：模块的源码位于当前目录
23  #modules ：编译模块
24  all:
25     $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) modules
26     $(CROSS_COMPILE)gcc -o $(test_app) $(test_app).c
27
28  .PHONE:clean
29
30  #清理编译生成的文件
31  clean:
32     $(MAKE) -C $(KERNEL_DIR) M=$(CURDIR) clean
33     rm $(test_app)
```

Makefile与此前相比，只修改了要编译的内核模块目标文件。

##### 4.7.2.2.2. 编译命令说明[¶](#id33 "永久链接至标题")

在实验目录下输入如下命令来编译驱动模块：

```bash
 1  #进入moredev例程源码目录
 2  cd linux_driver/04_moredev
 3
 4  #编译驱动模块
 5  make
 6
 7  #信息输出如下
 8  make -C ../../kernel/ M=/home/guest/linux_driver/04_moredev modules
 9  make[1]: Entering directory '/home/guest/kernel'
10  CC [M]  /home/guest/linux_driver/04_moredev/moredev2.o
11  Building modules, stage 2.
12  MODPOST 1 modules
13  CC      /home/guest/linux_driver/04_moredev/moredev2.mod.o
14  LD [M]  /home/guest/linux_driver/04_moredev/moredev2.ko
15  make[1]: Leaving directory '/home/guest/kernel'
16  aarch64-linux-gnu-gcc -o chardev_app chardev_app.c
```

编译成功后，实验目录下会生成名为“moredev2.ko”驱动模块文件和“chardev_app”测试程序。

#### 4.7.2.3. 程序运行结果[¶](#id34 "永久链接至标题")

将moredev2.ko和chardev_app文件拷贝到开发板，执行以下进行命令：

```bash
 1  #加载驱动模块
 2  sudo insmod moredev2.ko
 3
 4  #信息输出如下
 5  [ 6040.232903] chrdev init
 6  [ 6040.233017] major=236,minor=0
 7  [ 6040.234477] device0 created
 8  [ 6040.239626] device1 created
 9
10  #查看注册的设备
11  cat /proc/devices | grep moredev
12
13  #信息输出如下
14  236 moredev
15
16  #查看注册生成的字符设备文件
17  ls -l /dev/moredev*
18
19  #信息输出如下
20  crw------- 1 root root 236, 0 Mar 20 15:42 /dev/moredev0
21  crw------- 1 root root 236, 1 Mar 20 15:42 /dev/moredev1
```

我们从/proc/devices文件中，可以看到我们注册的字符设备moredev的主设备号为236。 从/dev/moredev*详细信息可以看到，/dev/moredev0主设备号为236，次设备号为0，/dev/moredev1主设备号为236，次设备号为1。

以root权限运行chardev_app测试程序：

```bash
 1  #读写字符设备
 2  sudo ./chardev_app /dev/moredev0
 3
 4  #信息输出如下
 5  --------------写入数据--------------
 6  [ 4286.859838] chardev open
 7  [ 4286.859952] write data: Hello World
 8  [ 4286.859952]
 9  [ 4286.859973] chardev release
10  --------------读取数据--------------
11  read data:chardev driver
12  [ 4287.860309] chardev open
13  [ 4287.860478] chardev release
14
15  #同理读写/dev/moredev1效果是一样的
16  sudo ./chardev_app /dev/moredev1
```

可以从写入数据部分的内核打印信息看到驱动获取到了用户写入的数据Hello World， 从读取数据部分应用程序输出看到，成功从驱动获取到数据chardev driver。

### 4.7.3. 总结[¶](#id35 "永久链接至标题")

一个驱动支持多个设备的具体实现方式的重点在于如何运用file的私有数据成员。

- 第一种方法是通过将各自的数据缓冲区放到该成员中，在读写函数的时候，直接就可以对相应的数据缓冲区进行操作；
    
- 第二种方法则是通过将我们的数据缓冲区和字符设备结构体封装到一起，由于文件结构体inode的成员i_cdev保存了对应字符设备结构体，使用container_of宏便可以获得封装后的结构体的地址，进而得到相应的数据缓冲区。
    

两种方案的核心共性：主设备号共用、次设备号区分实例、private_data实现资源隔离、file_operations接口复用，掌握这一核心思想，即可轻松实现任意数量同类型字符设备的驱动开发。