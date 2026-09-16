---
title: Linux内核文件系统mount过程（原文摘要）
category: summaries
tags: [linux, 内核, mount, VFS, 文件系统]
source_dir: Linux 操作系统/Linux 文件系统
source_files: [Linux内核—文件系统mount过程.md]
summary: 逐函数讲解mount系统调用：mountpoint/mount/vfsmount三大结构体定义、do_mount五分支、vfs_kern_mount创建sb/dentry/inode、do_add_mount关联挂载点，附完整调用树。
provenance:
  extracted: 0.90
  inferred: 0.07
  ambiguous: 0.03
base_confidence: 0.675
lifecycle: draft
lifecycle_changed: 2026-09-15
tier: supporting
created: 2026-09-15
updated: 2026-09-15
---

# Linux内核文件系统mount过程（原文摘要）

知乎文章（zhuanlan.zhihu.com/p/606596107）逐函数分析内核如何建立挂载点目录项与文件系统根目录的关联，附源码和结构图。

## 概述

- VFS通过dentry实例组成的根文件系统管理所有文件；具体文件系统根目录必须关联到根文件系统某目录项（挂载点）才能接入——这就是挂载
- 挂载点可叠加多个文件系统：后挂载的可见，先挂载的被隐藏，卸载后自动恢复可见
- 整个流程围绕三大数据结构展开：mountpoint（挂载点）、mount（一次挂载操作）、vfsmount（mount与文件系统的关联）

## 核心观点

- **三大结构体**：mountpoint含m_dentry（挂载点dentry）+m_list（mount链表）+m_count（挂载次数）；mount含mnt_parent/mnt_mountpoint/mnt_ns等二十余成员，组织成父子层次+全局散列表；vfsmount含mnt_root（文件系统根dentry）+mnt_sb（超级块）
- **mount是vfsmount的封装**：一个文件系统可创建多个vfsmount挂到不同挂载点；mnt_parent指向自身的是root mount（rootfs）
- **sys_mount→do_mount五分支**：MS_REMOUNT→do_remount、MS_BIND→do_loopback、传播类型→do_change_type、MS_MOVE→do_move_mount、默认→do_new_mount
- **do_new_mount两步**：vfs_kern_mount（创建sb/dentry/inode + mount实例）+ do_add_mount（创建mountpoint、graft_tree建立关联、插入全局散列表）
- **磁盘文件系统通用路径**：ext4_mount→mount_bdev→blkdev_get_by_path + sget（查找或创建sb，复用已有sb）→fill_super（ext4_fill_super读磁盘超级块/块组描述符/根inode，d_make_root建根dentry）
- **路径查找穿越挂载点**：dentry带DCACHE_MOUNTED标记时，lookup_mnt在mount散列表找第一个匹配的mount实例，进入其文件系统根目录项

## 未解问题

- 共享/从属挂载传播（do_change_type）细节未展开
- mount namespace与容器隔离的交互未覆盖

## 来源

- 概念整合见 [[concepts/linux-fs-mount]]
- 关联：[[concepts/linux-io-stack]]（块设备层）、[[concepts/linux-namespace-cgroups]]（Mount Namespace）
