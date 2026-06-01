---
title: virsh虚拟机管理操作手册
category: skills
tags: [linux, 虚拟化, virsh, 运维, 操作手册]
relationships:
  - target: "[[entities/libvirt-virsh]]"
    type: implements
  - target: "[[summaries/linux-live-migration-flow]]"
    type: uses
source_dir: Linux 虚拟化/libvirt
source_files: ["virsh 常用命令汇总表.md"]
summary: virsh管理KVM虚拟机的实操指南：生命周期、配置调整、热迁移、快照、CPU绑定等常用场景的命令组合。
provenance:
  extracted: 0.85
  inferred: 0.10
  ambiguous: 0.05
base_confidence: 0.775
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# virsh虚拟机管理操作手册

## 前置条件

- libvirt和QEMU/KVM已安装并运行
- 有权限访问libvirt daemon（通常需要root或libvirt组成员）
- VM XML配置文件已准备

## 步骤

### 1. VM生命周期管理

```bash
virsh list --all          # 查看所有VM（含关机）
virsh start vm01          # 启动VM
virsh shutdown vm01       # 温关机（ACPI信号）
virsh destroy vm01        # 强关机（拔电源）
virsh reboot vm01         # 重启
virsh suspend vm01        # 暂停（挂起）
virsh resume vm01         # 恢复
```

### 2. 配置管理

```bash
virsh define vm01.xml     # 从XML定义VM（不启动）
virsh undefine vm01       # 删除VM定义
virsh edit vm01           # 编辑VM XML配置
virsh dumpxml vm01 > vm01.xml  # 导出XML配置
```

### 3. 动态资源调整

```bash
virsh setmem vm01 8G      # 调整内存（需支持动态）
virsh setvcpus vm01 8     # 增加CPU（需支持热插）
```

### 4. CPU绑定优化

```bash
virsh vcpuinfo vm01       # 查看当前vCPU绑定状态
virsh vcpupin vm01 0 2    # 绑定vCPU0到物理CPU2
virsh emulatorpin vm01 0-3  # 绑定QEMU进程到CPU0-3
```

### 5. 热迁移

```bash
# 迁移前检查兼容性
virsh capabilities > source_caps.xml

# 整机迁移（含磁盘）
virsh migrate --live --p2p --unsafe --migrateuri tcp://DEST_IP \
  VM_NAME qemu+tcp://DEST_IP/system --verbose --copy-storage-all

# 仅内存迁移（共享存储场景）
virsh migrate --live --p2p --unsafe VM_NAME qemu+tcp://DEST_HOST/system

# 迁移参数调整
virsh migrate-setmaxdowntime vm01 500   # 最大停机时间500ms
virsh migrate-setspeed vm01 1000       # 限速1000Mbps
```

### 6. 快照管理

```bash
virsh snapshot-create-as vm01 snap1    # 创建命名快照
virsh snapshot-list vm01               # 列出快照
virsh snapshot-revert vm01 snap1       # 恢复快照
virsh snapshot-delete vm01 snap1       # 删除快照
```

### 7. 存储与网络管理

```bash
# 磁盘
virsh attach-disk vm01 /data/disk.img vdb   # 挂载磁盘
virsh detach-disk vm01 vdb                  # 卸载磁盘
virsh domblklist vm01                       # 列出磁盘设备

# 网络
virsh attach-interface vm01 bridge br0      # 挂载网卡
virsh detach-interface vm01 bridge MAC      # 卸载网卡
virsh net-list --all                        # 列出虚拟网络
```

## 常见问题

- **shutdown不生效**：Guest未安装ACPI驱动，使用`destroy`强关
- **迁移失败"unsafe"**：不跳过安全检查时CPU特性不兼容，检查两端`virsh capabilities`
- **CPU绑定后性能反而下降**：绑定过窄导致CPU争抢，适当放宽绑定范围

## 来源

- `raw/sources/Linux 虚拟化/libvirt/virsh 常用命令汇总表.md` — 全部命令分类与示例