---
title: OverlayFS 与容器镜像分层
category: concepts
tags: [云原生, OverlayFS, 容器, 存储, Copy-on-Write]
aliases: [OverlayFS, overlay2, 容器镜像]
relationships:
  - target: "[[concepts/container-runtime-deep-dive]]"
    type: related_to
  - target: "[[concepts/linux-io-stack]]"
    type: uses
  - target: "[[concepts/linux-memory-management]]"
    type: uses
source_dir: 云原生/容器运行时/从零造容器系列
source_files: [【从零造容器】5 OverlayFS：一层一层像洋葱.md]
summary: OverlayFS联合挂载四目录(lowerdir+upperdir+workdir+merged)；Copy-on-Write首次写100MB文件慢263倍(47.32ms vs 0.18ms)；overlay2是Docker默认驱动；数据库文件必须放在volume上
provenance:
  extracted: 0.85
  inferred: 0.12
  ambiguous: 0.03
base_confidence: 0.80
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-13
---

# OverlayFS 与容器镜像分层

OverlayFS 是容器镜像分层的核心机制——把多个目录叠成合并视图，像洋葱一层一层。它是 Docker 18.09 开始的默认存储驱动（overlay2），替代了已弃用的 aufs 和性能不佳的 devicemapper。

## 核心观点

- **OverlayFS 四个关键目录**：lowerdir（只读，可多层）、upperdir（读写）、workdir（内核用）、merged（合并视图）。
- **Copy-on-Write 是性能杀手**：修改1字节需要先复制整个文件到upperdir。100MB文件首次写47.32ms vs 第二次0.18ms——慢263倍（实测数据）。
- **数据库文件必须放在volume上**：不要放在overlay可写层。数据库频繁随机写触发大量copy-up。 ^[inferred]
- **overlay2 成为默认的三大理由**：内核主线支持、inode效率、配置简单。
- **读性能几乎等于直接读底层文件系统**：OverlayFS转发到底层inode，无额外开销。

## OverlayFS 结构

```
merged (合并视图，用户看到的)
  ├── lowerdir (只读，可多层: lower1, lower2, ...)
  ├── upperdir (读写层，容器修改)
  ├── workdir  (内核内部使用)
```

### Copy-on-Write (copy-up) 机制

修改lowerdir文件时：
1. 整个文件先从lowerdir复制到upperdir
2. 修改在upperdir的副本上进行
3. merged视图呈现修改后的版本

**性能代价**：首次写100MB文件 47.32ms（copy-up）vs 第二次0.18ms（只写upperdir已有副本）。263倍差距。

### Whiteout 删除机制

删除文件时在upperdir创建whiteout字符设备(0,0)标记"不存在"。删除目录时创建opaque directory（`trusted.overlay.opaque=y`）标记整个目录删除。

## Docker overlay2 存储驱动

### 镜像层结构

Docker镜像在 `/var/lib/docker/overlay2/` 下存储：
- 每层一个目录（lower层只读）
- 最上层是容器的upperdir（可写层）
- `-init` 层包含 `/etc/hostname`、`/etc/resolv.conf`，放在lower和upper之间

**Docker默认限制镜像最多128层**：层数越多 `open()` 查找越慢。

### 存储驱动对比

| 驱动 | 机制 | COW方式 | 状态 |
|------|------|---------|------|
| **overlay2** | 内核OverlayFS | 文件级copy-up | 默认，推荐 |
| **devicemapper** | LVM块设备 | 块级COW | 已弃用 |
| **btrfs** | 子卷快照 | 子卷级 | 可用但不主流 |
| **zfs** | 克隆 | 数据集级 | 可用但不主流 |
| **aufs** | 内核外模块 | 文件级 | 已弃用 |

## 关键细节

### XFS inode 源溢出

Linux < 4.17 的XFS有inode编号溢出问题（overlay2需要大量inode）。生产推荐 ext4 + overlay2。 ^[inferred]

### 只读根文件系统

容器安全最佳实践：`MS_REMOUNT | MS_RDONLY | MS_BIND` 将根挂载为只读。选择性挂载tmpfs给 `/tmp`、`/run` 等需要写入的路径。

tmpfs用 `size=65536k` 限制大小防止吃光内存。 `/tmp` 权限 `01777` 中 `1` 是sticky bit。

### Volume vs overlay 可写层

| 场景 | 推荐 | 原因 |
|------|------|------|
| 数据库文件 | Volume (bind mount) | 避免copy-up性能损失 |
| 日志文件 | Volume 或 tmpfs | 避免copy-up |
| 配置文件 | ConfigMap/Secret mount | 只读挂载 |
| 临时文件 | tmpfs | 自动清理 |

## 未解问题

- overlay2在大规模镜像仓库中的inode消耗问题？
- copy-up对不同文件大小（1KB vs 1GB）的性能影响量化？
- overlay2与btrfs/zfs在容器场景下的全面性能对比？

## 来源

- 从零造容器系列 #05 — OverlayFS机制+overlay2驱动+实测性能数据