---
title: TRIM擦除指令
category: summaries
tags: [硬件, SSD, TRIM, NAND, 写放大]
aliases: [TRIM指令, SSD TRIM, discard指令]
source_dir: 物理硬件/磁盘
source_files: [TRIM擦除指令.md]
summary: TRIM是ATA8-ACS规范的SATA指令，让OS通知SSD哪些页已无效：SSD页读块擦不对称导致写放大与GC负担，TRIM把删除信息下推给介质；含三方支持检测与三种启用方法。
provenance:
  extracted: 0.75
  inferred: 0.13
  ambiguous: 0.12
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-06
tier: supporting
created: 2026-11-06
updated: 2026-11-06
---

# TRIM擦除指令

TRIM是微软联合各大SSD厂商开发的技术，属于ATA8-ACS规范的技术指令——告诉NAND闪存固态存储设备要擦除哪些数据的SATA接口指令（微软侧称disable delete notify）。机理沉淀于 [[concepts/ssd-trim-write-amplification]]，检测/启用命令整理进 [[skills/linux-io-debugging]]。

## 核心观点

- SSD的Read和Write以page为单位，Erase以block为单位；Write只能写到空page，不能像HDD那样覆盖写。修改数据= read-modify-write：读原page→cache中改→写入新空page→重映射逻辑地址→原page标记stale。
- **写入放大**：无TRIM时SSD不知哪些page已无效，对非空page写入必须先Erase整个block(read-erase-modify-write)——整block读进cache、擦除、写回。既拖累GC效率，又损耗寿命。
- **文件系统与介质的信息断层**：删除文件只是把地址标记为"空"，硬盘本身并不知道数据已无效——除非系统通知。文件恢复工具正是利用"数据残留直到被覆盖"的原理工作。
- Windows侧机制：识别SSD且确认支持TRIM后，用Volume Bitmap(磁盘快照)记住已删除区域——建快照比逐块读写标记快得多；写入时直接向快照中已删除区块写新数据，无需先擦原数据。
- 启用TRIM需要三方支持：SSD + 操作系统 + 文件系统，缺一不可。
- RedHat部署指南：随使用的block接近磁盘容量，SSD性能开始降低，所有设备都会遇到、程度因供应商而异；Linux支持发送discard请求通知存储器哪些block不再使用。
- SSD组RAID0后将失去TRIM功能。
- Linux检测三法：`/sys/block/sdX/queue/discard_granularity`非0；`lsblk --discard`的DISC-GRAN/DISC-MAX非0；`hdparm -I /dev/sdb | grep -i trim`。
- Linux启用三法：fstab挂载选项`discard`(实时下发但降低磁盘性能)；手动`fstrim -a -v`；CentOS 7+自带`fstrim.timer`(每周定时，推荐)。
- Windows检测/设置：`fsutil behavior query disabledeletenotify`(0=已开启TRIM)、`fsutil behavior set disabledeletenotify 0`(开启)。

## 未解问题

- 原文关于Windows删除流程的表述自相矛盾：既称"确认支持Trim后删除时不向硬盘通知删除指令、只用Volume Bitmap"，又以disabledeletenotify=0为"开启TRIM"(即删除时通知)。推测前者描述的是文件系统层记账、后者是块层discard下发，但原文未区分层次。 ^[ambiguous]
- "SSD组RAID0后失去TRIM"的适用范围（消费级软阵列/阵列卡/所有实现）未展开，现代阵列卡对TRIM透传的支持情况需补充来源。 ^[inferred]

## 来源

- raw/sources/物理硬件/磁盘/TRIM擦除指令.md（引Crucial官方文章与知乎专栏）
