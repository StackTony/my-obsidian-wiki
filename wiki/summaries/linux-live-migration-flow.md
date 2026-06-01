---
title: Linux虚拟机热迁移流程
category: summaries
tags: [linux, 虚拟化, 热迁移, QEMU, libvirt]
source_dir: Linux 虚拟化/热迁移
source_files: [热迁移流程.md, 热迁移命令.md]
summary: 虚拟机热迁移三阶段：内存迭代拷贝→停机拷贝→网络恢复。关键参数：downtime_limit、迁移带宽限速。大页需4K打散，脏页检测有性能开销。
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.775
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# Linux虚拟机热迁移流程

虚拟机热迁移是在不停机的情况下将VM从源主机迁移到目的主机，核心挑战是在有限停机时间内完成内存状态同步。

## 核心观点

### 迁移三阶段

**阶段一：数据迁移（内存迭代拷贝）**
- 以~1s为周期进行脏页同步
- 脏页速率高于迁移带宽20次 → 迁移失败
- 持续以最大限速带宽拷贝内存数据至目的端
- 条件"M < threshold_size"时进入快速迭代（M=剩余脏页量，threshold=bandwidth×downtime_limit）

**阶段二：快速迭代拷贝**
- 以~50ms为周期脏页同步
- CPU降频：脏页速率高于传输带宽时每计数满2/4次降频一档
- 强制收敛：`M < threshold_size`计数达到force_converge后激活，停机条件变为`M < bandwidth×force_downtime`
- 动态调整min_downtime：计数满20次递增100ms
- 条件`M < bandwidth×min_downtime(40+ms)`时进入停机拷贝

**阶段三：停机拷贝**
- 源端虚拟机停机
- 以最大可用带宽拷贝剩余脏页
- 目的端加载设备状态并启动

### 网络恢复时序

```
内存迁移 → 迁移virtio-net设备状态 + 内存(含vring数据)
停机拷贝 → 停止VM → 拷贝剩余脏页/状态
网络恢复 → 下发流表 → 激活网桥端口 → 启动VM → RARP/GARP广播 → CAM表更新
清理 → 删除旧流表 → 清理源端资源
```

### libvirt迁移流程

```
qemuMigrationSrcPerformPeer2Peer3:
  qemuMigrationSrcBeginPhase — 解析VM XML
  domainMigratePrepare3 — 远程创建目的端domain
  qemuMigrationSrcPerformNative — 开始数据迁移
  domainMigrateFinish3 — 等待目的端完成/失败
  qemuMigrationSrcConfirmPhase — 清理源端或目的端
```

### 关键要点

1. 大页虚拟机迁移前按4K页粒度打散（耗时）
2. 热迁移耗时包括：FS调度下发、内存迭代拷贝、数通流表拉起、目的端重建页表
3. getdirty接口查询脏页时需陷出标脏，对虚拟机有性能影响
4. `set_migration_pin`对主机所有VM生效，`domain.migrationPin`仅对单VM生效
5. 迁移兼容性检查：比较目的主机virsh capabilities和VM virsh dumpxml的cpu feature
6. 迁移结束后目的端进行RARP广播（异步动作）

### virsh热迁移命令

```bash
# 整机迁移（含磁盘）
virsh migrate --live --p2p --unsafe --migrateuri tcp://DEST_IP \
  VM_NAME qemu+tcp://DEST_IP/system --verbose --copy-storage-all

# 仅内存迁移（共享存储）
virsh migrate --live --p2p --unsafe VM_NAME qemu+tcp://DEST_HOST/system
```

| 参数 | 含义 |
|------|------|
| `--live` | 热迁移（不停机） |
| `--p2p` | 点对点迁移 |
| `--unsafe` | 跳过安全检查 |
| `--copy-storage-all` | 整机迁移（复制磁盘） |

## 来源

- `raw/sources/Linux 虚拟化/热迁移/热迁移流程.md` — 三阶段流程、网络恢复时序、libvirt代码流程、关键要点
- `raw/sources/Linux 虚拟化/热迁移/热迁移命令.md` — virsh migrate命令示例

> 相关概念：[[entities/libvirt-virsh]]（virsh工具）、[[skills/virsh-vm-management]]（virsh操作手册）、[[concepts/linux-virtio-architecture]]（virtio网络迁移中vring数据传输）