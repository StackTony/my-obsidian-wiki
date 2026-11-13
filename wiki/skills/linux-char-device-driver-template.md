---
title: 编写一个字符设备驱动（最小骨架）
category: skills
tags: [linux, 驱动, 字符设备, 内核模块, 实操]
aliases: [字符设备驱动模板, cdev 模板, chardev 骨架]
relationships:
  - target: "[[summaries/linux-char-device-driver]]"
    type: derived_from
source_dir: Linux 操作系统/Linux 驱动管理/Linux 字符设备 系统
source_files: [Linux字符设备驱动.md]
summary: 从零写字符设备驱动的六步骨架：申请 dev_t、cdev_init、cdev_add、class_create/device_create（或 mknod）、实现 file_operations、逆序注销；附最小代码框架与常见坑。
provenance:
  extracted: 0.82
  inferred: 0.16
  ambiguous: 0.02
base_confidence: 0.59
lifecycle: draft
lifecycle_changed: 2026-11-12
tier: supporting
created: 2026-11-12
updated: 2026-11-12
---

# 编写一个字符设备驱动（最小骨架）

本页把 [[summaries/linux-char-device-driver]] 的框架压成可照抄的操作步骤。目标不是写一个完整产品驱动，而是先跑通"模块加载 → 设备节点出现 → read/write 到达驱动"的最小闭环。

## 概述

Linux 字符设备驱动 = **一个内核模块 + 一个 `cdev` + 一张 `file_operations` 函数表 + 一个设备节点**。内核已经提供了注册、查找、VFS 转发等全部通用逻辑，驱动只需要"填空"：申请设备号、绑定 fops、注册 cdev、创建设备节点、实现硬件操作。

## 前置条件

- 能编译内核模块：内核源码/头文件、与目标板匹配的交叉编译器、`Makefile`。
- 目标板（实验环境为 Lubancat_RK 系列）可加载 `.ko`，并有串口/SSH 可看 `dmesg`。
- 知道设备要暴露的接口：`open/release/read/write/ioctl` 中需要哪几个。

## 步骤

### 1. 定义设备号与设备对象

```c
#define DEV_NAME "chardev"
#define DEV_CNT  1

static dev_t devno;              // 起始设备号
static struct cdev chr_dev;      // 字符设备对象
static struct class *class;      // sysfs 设备类
static struct device *device;    // /dev 下的设备
static int major, minor;
```

### 2. 申请设备号

```c
/* 动态分配（推荐） */
ret = alloc_chrdev_region(&devno, 0, DEV_CNT, DEV_NAME);
major = MAJOR(devno);
minor = MINOR(devno);

/* 或静态指定 */
// ret = register_chrdev_region(MKDEV(240, 0), DEV_CNT, DEV_NAME);
```

失败返回负错误码，必须在 `init` 中回滚。`cat /proc/devices` 可确认动态分配到的主设备号。

### 3. 实现 file_operations

```c
static int chardev_open(struct inode *inode, struct file *file)
{
    file->private_data = /* 你的设备结构体 */;
    return 0;
}

static ssize_t chardev_read(struct file *file, char __user *buf,
                            size_t count, loff_t *ppos)
{
    /* 从内核缓冲区拷到用户空间 */
    if (copy_to_user(buf, kbuf + *ppos, count))
        return -EFAULT;
    *ppos += count;
    return count;
}

static ssize_t chardev_write(struct file *file, const char __user *buf,
                             size_t count, loff_t *ppos)
{
    if (copy_from_user(kbuf + *ppos, buf, count))
        return -EFAULT;
    *ppos += count;
    return count;
}

static int chardev_release(struct inode *inode, struct file *file)
{
    return 0;
}

static const struct file_operations chardev_fops = {
    .owner   = THIS_MODULE,
    .open    = chardev_open,
    .read    = chardev_read,
    .write   = chardev_write,
    .release = chardev_release,
};
```

要点：`read/write` 的返回值是实际读写的字节数；`copy_*_user` 返回**未拷贝字节数**，非 0 要转成 `-EFAULT`；用户指针不能直接解引用。

### 4. 初始化并注册 cdev

```c
cdev_init(&chr_dev, &chardev_fops);
chr_dev.owner = THIS_MODULE;
ret = cdev_add(&chr_dev, devno, DEV_CNT);
if (ret)
    goto err_cdev;
```

### 5. 创建设备节点

优先用 `class_create()` + `device_create()` 让内核/udev 自动建 `/dev` 节点：

```c
class  = class_create(THIS_MODULE, DEV_NAME);
device = device_create(class, NULL, devno, NULL, DEV_NAME);
```

也可以手工 `mknod /dev/chardev c <major> <minor>`，但需要自己管理权限与节点生命周期。

### 6. 注销（与注册逆序）

```c
static void __exit chardev_exit(void)
{
    device_destroy(class, devno);
    class_destroy(class);
    cdev_del(&chr_dev);
    unregister_chrdev_region(devno, DEV_CNT);
}
```

## 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `insmod` 成功但 `/dev` 无节点 | 只用 `cdev_add`，没 `device_create`/`mknod` | 补建设备节点 |
| `open` 返回 `ENXIO` | `cdev_add` 未成功，或设备号不匹配 | 检查 `devno` 与 `cdev_add` 返回值 |
| `read/write` 返回 `-EFAULT` | `copy_*_user` 参数方向或长度错 | 核对 `to/from` 与 `count` |
| 主设备号冲突 | 静态申请了已被占用的号 | 改用 `alloc_chrdev_region` |
| 卸载后 rmmod 失败 | 还有进程打开设备 | 先关闭 fd，再 `rmmod` |
| 次设备号不够用 | 误用 `register_chrdev()`，它一次占 256 个 | 改用 region API |

## 进阶用法

- **一个驱动支持多个设备**：主设备号共用，`MINOR(inode->i_rdev)` 区分实例；资源隔离用 `file->private_data`，或把缓冲区与 `cdev` 封装后用 `container_of()` 反推。
- **简化接口**：简单字符设备可用 `miscdevice`，自动分配次设备号，少写一半注册代码。
- **并发保护**：多进程同时读写时，共享缓冲区需要 `mutex` 或 `spinlock`；中断上下文只能用自旋锁。
- **自动创建设备类**：`class_create` 的返回值要用 `IS_ERR()` 检查，`device_create` 失败要回滚 class。

## 来源

- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux 字符设备 系统/Linux字符设备驱动.md` — 第 4 章驱动框架、API 与实验代码
- 交叉：[[summaries/linux-char-device-driver]]（原理与 open 路径）、[[concepts/linux-driver-model]]（LDM 与设备模型）
