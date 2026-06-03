---
title: libvirt/virsh
category: entities
tags: [linux, 虚拟化, libvirt, virsh, 工具]
aliases: [virsh, libvirt命令行]
relationships:
  - target: "[[concepts/linux-virtio-architecture]]"
    type: related_to
  - target: "[[summaries/linux-live-migration-flow]]"
    type: related_to
source_dir: Linux 虚拟化/libvirt
source_files: ["virsh 常用命令汇总表.md"]
summary: virsh是libvirt的命令行管理工具，覆盖VM生命周期、配置管理、存储/网络、热迁移、快照等全部运维操作。
provenance:
  extracted: 0.90
  inferred: 0.10
  ambiguous: 0.0
base_confidence: 0.775
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# libvirt/virsh

virsh是libvirt项目提供的命令行虚拟机管理工具，是与KVM/QEMU虚拟化环境交互的主要入口。

## 关键属性

- **定位**：libvirt命令行管理工具，与QEMU/KVM虚拟化栈配合
- **覆盖领域**：VM生命周期、信息查询、配置管理、存储/网络管理、热迁移、快照、性能调优
- **底层**：操作libvirt API，libvirt再调用QEMU驱动

## 与其他实体的关系

- 依赖QEMU进程作为VM执行引擎
- 依赖libvirt作为中间管理层
- 热迁移命令与[[summaries/linux-live-migration-flow]]的流程直接对应


## 延伸阅读

实操指南：[[skills/linux-vm-debugging]]

## 来源

- `raw/sources/Linux 虚拟化/libvirt/virsh 常用命令汇总表.md` — 全部virsh命令分类汇总