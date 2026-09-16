---
title: Linux文件系统与Mount机制
category: concepts
tags: [linux, 内核, 文件系统, mount, VFS]
aliases: [Linux Mount, 文件系统挂载, VFS挂载, mount结构体]
relationships:
  - target: "[[concepts/linux-io-stack]]"
    type: related_to
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
  - target: "[[concepts/linux-namespace-cgroups]]"
    type: related_to
source_dir: Linux 操作系统/Linux 文件系统
source_files: [Linux内核—文件系统mount过程.md]
summary: VFS挂载三大数据结构(mount/mountpoint/vfsmount)+mount系统调用五分支流程+do_new_mount两步挂载(内核挂载vfs_kern_mount+关联挂载点do_add_mount)。
provenance:
  extracted: 0.85
  inferred: 0.12
  ambiguous: 0.03
base_confidence: 0.675
lifecycle: draft
lifecycle_changed: 2026-09-15
tier: supporting
created: 2026-09-15
updated: 2026-09-15
---

# Linux文件系统与Mount机制

文件系统挂载是磁盘分区文件系统接入内核根文件系统的过程：将磁盘分区（如sda1）的文件系统根目录与根文件系统中的某个目录项（挂载点）建立关联。挂载点可以同时挂载多个文件系统——后挂载的可见，先挂载的被隐藏；卸载上层后下层自动可见。

## 核心观点

### 三大数据结构

**mountpoint**（fs/mount.h）——根文件系统中的挂载点：
- `m_dentry` — 指向挂载点dentry实例（根文件系统中目录项，**不是**挂载文件系统的根目录项）
- `m_list` — 链接挂到该点的mount实例链表头
- `m_count` — 该挂载点执行挂载操作的次数
- 所有mountpoint实例由全局散列表 `mountpoint_hashtable` 管理

**mount**——一次挂载操作：
- `mnt_parent` — 父mount实例（指向自身则为root mount，代表rootfs）
- `mnt_mountpoint` — 挂载点dentry实例指针
- `mnt` — 内嵌vfsmount结构体
- `mnt_instance` — 链入超级块双链表 `sb->s_mounts`
- `mnt_ns` — 指向所属挂载命名空间（与 [[concepts/linux-namespace-cgroups]] 的Mount Namespace关联）
- mount实例组成父子层次结构 + 全局散列表 `mount_hashtable`

**vfsmount**（include/linux/mount.h）——mount与文件系统的关联：
- `mnt_root` — 指向挂载文件系统根目录项dentry
- `mnt_sb` — 指向文件系统超级块super_block

关键关系：**mount是vfsmount的封装**。一个文件系统可创建多个mount实例挂到不同挂载点，每个mount实例对应一个vfsmount。

### mount系统调用流程

```
sys_mount() → do_mount()
  ├─ do_remount()        # MS_REMOUNT 重新挂载/改选项
  ├─ do_loopback()       # MS_BIND 绑定挂载
  ├─ do_change_type()    # MS_SHARED/PRIVATE/SLAVE/UNBINDABLE 传播类型
  ├─ do_move_mount()     # MS_MOVE 移动挂载
  └─ do_new_mount()      # 全新挂载
```

- `sys_mount` 先将type/dev_name/data三参数从用户空间拷贝到内核，再委托 `do_mount`
- `do_mount` 用 `user_path()` 把挂载点目录解析成 `struct path {mnt, dentry}`，做安全检查（security_sb_mount），将MS_*用户标志转成MNT_*内核标志
- 五分支按flags路由，最常见的是 `do_new_mount()`

### do_new_mount两步挂载

**第一步：内核挂载 `vfs_kern_mount()`**
1. `alloc_vfsmnt()` — 从slab缓存分配mount实例并初始化
2. `mount_fs()` — 调用文件系统类型的 `type->mount()` 回调，创建（或查找）超级块、根dentry、根inode
3. 建立关联：`mnt_root`→根dentry、`mnt_sb`→超级块、`mnt_parent`暂指向自身、插入 `sb->s_mounts` 链表

磁盘文件系统走通用路径：`ext4_mount()` → `mount_bdev()`：
- `blkdev_get_by_path()` 由设备路径获取block_device描述符
- `sget()` 查找或创建super_block（已存在则复用——同一设备重复挂载共享超级块）
- 新建时调用 `fill_super`（如 `ext4_fill_super`）：读磁盘超级块→填充VFS超级块→读块组描述符→读磁盘根inode建VFS根inode→`d_make_root()` 创建根dentry

**第二步：关联挂载点 `do_add_mount()`**
1. `lock_mount(path)` — 创建（或查找）mountpoint实例，设置挂载点dentry的 `DCACHE_MOUNTED` 标记位，加入全局散列表
2. 检查避免同一文件系统重复挂载到同一挂载点（-EBUSY）
3. `graft_tree()` — 建立mount↔mountpoint↔挂载点dentry关联，插入全局散列表头部和父子层次结构

两步执行完，挂载点dentry与挂载文件系统根dentry之间通过mount实例建立联系。

### 路径查找如何"穿过"挂载点

当内核打开文件搜索路径到达挂载点时（dentry带DCACHE_MOUNTED标记），调用 `lookup_mnt(path)` 在mount全局散列表中查找第一个关联该挂载点dentry的mount实例，搜索路径随后进入mount实例关联的文件系统根目录项。这就是"后挂载遮蔽先挂载"的实现机制。

## 关键细节

- mount()的flags宏在 include/uapi/linux/fs.h（MS_RDONLY、MS_NOATIME等），VFS层解析；data是各文件系统私有挂载选项
- 可用 `strace mount ...` 查看最终系统调用：`mount("/dev/loop0", "/mnt/foobar", "xfs", MS_MGC_VAL|MS_NODEV, "noquota") = 0`
- `struct file_system_type`（如 `ext4_fs_type`）定义 `.mount` 和 `.kill_sb` 回调 + `FS_REQUIRES_DEV` 标志；磁盘文件系统普遍复用 `mount_bdev()`
- ext4_fill_super 五大工作：读磁盘超级块→填充关联VFS超级块→读块组描述符→读磁盘根inode建VFS根inode→创建根dentry
- 挂载点遮蔽与卸载自动可见的行为，本质是 `lookup_mnt` 总是取散列表中"最后插入"（头部）的mount实例 ^[inferred]

## 未解问题

- 共享/从属挂载传播（shared/subordinate propagation）的 `do_change_type` 细节本文未展开，需要补充来源
- mount命名空间（mnt_namespace）与容器场景的挂载隔离交互 ^[inferred]

## 来源

- [[summaries/linux-fs-mount-process]] — 原文：Linux内核—文件系统mount过程（知乎 zhuanlan.zhihu.com/p/606596107）
