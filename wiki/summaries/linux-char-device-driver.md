---
title: Linux 字符设备驱动
category: summaries
tags: [linux, 内核, 驱动, 字符设备, cdev]
aliases: [字符设备驱动, cdev, file_operations, 设备号, dev_t]
relationships:
  - target: "[[concepts/linux-driver-model]]"
    type: implements
  - target: "[[summaries/linux-block-subsystem]]"
    type: related_to
  - target: "[[skills/linux-char-device-driver-template]]"
    type: related_to
source_dir: Linux 操作系统/Linux 驱动管理/Linux 字符设备 系统
source_files: [Linux字符设备驱动.md]
summary: 字符设备驱动全链路：dev_t 12+20 位设备号、cdev/cdev_map 散列表、file_operations-file-inode 三角、设备号申请→cdev_init→cdev_add→device_create 五步框架，以及 open 经 def_chr_fops→chrdev_open→replace_fops 绑定驱动的路径。
provenance:
  extracted: 0.86
  inferred: 0.11
  ambiguous: 0.03
base_confidence: 0.59
lifecycle: draft
lifecycle_changed: 2026-11-12
tier: supporting
created: 2026-11-12
updated: 2026-11-12
---

# Linux 字符设备驱动

野火 RK356x 驱动教程第 4 章的蒸馏。字符设备是三大设备类型中最适合入门的一类：**按字节流顺序访问、通常不经缓存、通过 `/dev` 下的设备文件暴露给用户态**。本页沿"设备号 → cdev → file_operations → 注册框架 → open 路径"这条主线展开，实验代码骨架见 [[skills/linux-char-device-driver-template]]。

## 概述

Linux 把所有硬件抽象成文件，字符设备就是"能用 read/write 按字节流访问"的那一类。内核用 `struct cdev` 表示字符设备对象，用 `dev_t` 标识设备号，用 `struct file_operations` 提供操作入口；用户态打开 `/dev/xxx` 时，VFS 依据 inode 里的设备号在全局散列表中找回 `cdev`，再把 `file->f_op` 替换成驱动实现的函数表。

## 核心观点

- **三类设备按访问模型划分**：字符设备字节流、顺序访问、通常无缓存；块设备按块随机访问、有缓存与调度；网络设备走 socket，不经 `/dev` 与 VFS。三者在内核中分别抽象为 `cdev`、`block_device`、`net_device`。
- **设备号是 32 位整数**：高 12 位主设备号、低 20 位次设备号；`MAJOR()`/`MINOR()`/`MKDEV()` 做位运算。主设备号标识"用哪套驱动"，次设备号标识"同类设备中的哪一个"。实际 `register_chrdev_region()` 把主设备号限制在 0–511。
- **`cdev` 通过 `cdev_map` 散列表管理**：内核以主设备号为哈希键（`major % 255`）组织 `kobj_map` 散列表，冲突时按次设备号排序；`cdev` 内嵌 `kobject`，因此字符设备同时被纳入 LDM 的引用计数、电源管理与热插拔体系。^[inferred]
- **`file_operations` 是系统调用与驱动的桥梁**：`read/write/open/release/unlocked_ioctl/llseek` 等函数指针一一对应系统调用；未实现的指针留 `NULL`，内核行为因函数而异。
- **注册框架可压成五步**：申请设备号 → `cdev_init()` 绑定 fops → `cdev_add()` 注册进 `cdev_map` → `device_create()`（或 `mknod`）创建设备节点 → 退出时逆序释放。
- **`open` 的核心是"换函数表"**：inode 初始只挂通用的 `def_chr_fops`，`chrdev_open()` 用设备号查出 `cdev`，把 `file->f_op` 替换成 `cdev->ops`，再回调驱动自己的 `open()`。

## 关键细节

### 核心数据结构

| 结构 | 作用 | 关键字段 |
|---|---|---|
| `dev_t` | 设备号 | 32 位：主 12 位 + 次 20 位 |
| `struct cdev` | 字符设备对象 | `kobj`、`owner`、`ops`、`list`、`dev`、`count` |
| `struct file_operations` | 操作函数表 | `open`、`release`、`read`、`write`、`unlocked_ioctl`、`llseek` |
| `struct file` | 一次打开实例 | `f_op`（指向 fops）、`private_data`（驱动私有数据） |
| `struct inode` | 文件静态元数据 | `i_rdev`（设备号）、`i_cdev`（字符设备指针） |

- `file` 与 `inode` 是"多对一"：同一文件可被多次打开，产生多个 `file`，但共用一个 `inode`。
- `private_data` 是驱动隔离多实例资源的常用落点。

### 设备号申请的三套 API

| API | 特点 | 适用 |
|---|---|---|
| `register_chrdev_region(from, count, name)` | 静态指定起始设备号 | 已知主设备号 |
| `alloc_chrdev_region(&dev, baseminor, count, name)` | 内核动态分配未占用主设备号 | 现代驱动首选 |
| `register_chrdev(major, name, fops)` | 旧接口，一次占用 **256 个次设备号** | 简单驱动/历史代码 |

对应释放：`unregister_chrdev_region()` / `unregister_chrdev()`。`register_chrdev()` 的 256 个次设备号是资源浪费，新代码不建议使用。

### open 的完整路径

1. 用户态 `open("/dev/xxx", O_RDWR)` → `sys_open` → `do_sys_open` → `do_filp_open`。
2. VFS 解析路径，找到设备文件的 `inode`；`inode->i_rdev` 保存设备号，`inode->i_fop` 暂时指向通用的 `def_chr_fops`。
3. `do_dentry_open()` 执行 `f->f_op = fops_get(inode->i_fop)`，于是 `file->f_op` 先指向 `def_chr_fops`。
4. `def_chr_fops.open = chrdev_open`：用 `kobj_lookup(cdev_map, inode->i_rdev)` 找到 `cdev` 的 `kobject`，再用 `container_of()` 还原 `cdev`，并把 `inode->i_cdev` 缓存起来。
5. `replace_fops(filp, cdev->ops)` 把 `file->f_op` 换成驱动自己的函数表，随后回调 `filp->f_op->open(inode, filp)`。
6. `fd_install()` 把 `file` 与文件描述符关联；后续 `read/write` 直接走驱动 fops。

`mknod` 创建节点时，`init_special_inode()` 对字符设备设置 `i_fop = &def_chr_fops`、`i_rdev = rdev`——所以"自定义 fops 并不是在 mknod 时挂上的，而是在第一次 open 时才绑定"。

### 用户态与内核态数据拷贝

`read/write` 不能直接解引用用户指针，必须用：

- `copy_to_user(to, from, n)`：内核 → 用户；
- `copy_from_user(to, from, n)`：用户 → 内核。

返回值为**未拷贝成功的字节数**，成功时为 0；驱动应把失败转换为 `-EFAULT`。

### 一个驱动支持多设备

两种做法，核心都是 `file->private_data`：

1. **独立缓冲区 + 次设备号判断**：每个次设备号对应一个全局缓冲区，读写时按 `MINOR(inode->i_rdev)` 选择。
2. **结构体封装 + `container_of`**：把缓冲区与 `cdev` 封装进自定义结构体，由 `inode->i_cdev` 反推出外层结构体地址，资源隔离更彻底。

共同点：**主设备号共用、次设备号区分实例、fops 复用、private_data 隔离资源**。

### 实验与注销顺序

- 实验以 Lubancat_RK 系列板卡 + 内核模块形式完成，示例目录 `linux_driver/03_chardev`。^[ambiguous]
- 注销顺序与注册相反：`device_destroy()` → `class_destroy()` → `cdev_del()` → `unregister_chrdev_region()`。
- `cdev_del()` 只阻止新打开，已经打开的 `cdev` 及其 fops 仍可继续调用，驱动必须自行保证生命周期安全。

## 未解问题

- `cdev_map` 的 `kobj_map` 实现细节（区间查找、多主设备号冲突处理）本文只到哈希函数层。
- `device_create()` 与 `class_create()` 在 sysfs/uevent 中的完整链路未展开，只作为"自动创建 `/dev` 节点"的入口。
- 并发打开同一设备时 `chrdev_open()` 的双重检查锁路径（`cdev_lock`）只给了代码，未做竞态分析。
- 字符设备与 `miscdevice`、`devtmpfs`、udev 的关系需要单独补源。

## 来源

- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux 字符设备 系统/Linux字符设备驱动.md` — 野火 RK356x 驱动教程第 4 章：设备分类、字符设备抽象、设备号/cdev/fops/file/inode、驱动注册框架、open 路径、实验与多设备实现
- 交叉：[[concepts/linux-driver-model]]（LDM 与三类设备总纲）、[[summaries/linux-block-subsystem]]（块设备对照）、[[skills/linux-char-device-driver-template]]（代码骨架）
