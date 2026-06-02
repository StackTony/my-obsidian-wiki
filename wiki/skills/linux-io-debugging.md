---
title: Linux IO性能排查与压测实操手册
category: skills
tags: [linux, io, iostat, fio, blktrace, dd, 性能分析]
aliases: [IO调试实操, iostat实操, fio压测]
relationships:
  - target: "[[concepts/linux-io-performance-analysis]]"
    type: implements
  - target: "[[concepts/linux-io-stack]]"
    type: uses
source_dir: DFX工具
source_files: [==IO==/IO常用工具.md]
summary: IO性能排查与压测实操手册：iostat监控磁盘利用率/时延、fio随机/顺序读写压测、dd裸盘读写速率测试、blktrace追踪IO路径、block_dump+SCSI日志开关。
provenance:
  extracted: 0.85
  inferred: 0.10
  ambiguous: 0.05
base_confidence: 0.55
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# Linux IO性能排查与压测实操手册

IO性能分析从监控(iostat)→压测(fio)→追踪(blktrace)→日志(block_dump)的四步流程。

## 前置条件

- root 权限
- 安装 iostat(sysstat)、fio、blktrace 工具
- 理解 [[concepts/linux-io-stack]] 基础概念

## 步骤

### 1. iostat 监控磁盘状态

```bash
iostat -dmx 1 5 /dev/sda /dev/sdb
# -d: 仅设备统计；-m: MB单位；-x: 扩展统计；1: 每秒刷新；5: 共5次
```

**关键指标解读**：

| 场景 | 判断标准 | 处理方向 |
|------|----------|----------|
| 设备瓶颈 | util≈100% + svctm>5ms | 存储硬件问题，联系硬件同事 |
| 队列过长 | r/s或w/s大 + svctm<5ms + await>>svctm | 优化虚拟机业务降低IO压力 |
| 正常 | r/s或w/s大 + svctm<5ms + await≈svctm | 无需处理 |
| 性能对比 | 同模型svctm越小越好 | svctm降0.1ms可能大幅改善数据库IO |

### 2. fio IO压测

**100%随机读**：
```bash
fio -filename=/opt/testio -direct=1 -iodepth 1 -thread -rw=randread -ioengine=psync -bs=8k -size=10G -numjobs=50 -runtime=60 -group_reporting -name=rand_100read_8k
```

**100%随机写**：
```bash
fio -filename=/opt/testio -direct=1 -iodepth 1 -thread -rw=randwrite -ioengine=psync -bs=8k -size=10G -numjobs=50 -runtime=60 -group_reporting -name=rand_100write_8k
```

**100%顺序读/写**：替换 `-rw=read` 或 `-rw=write`

### 3. dd 读写速率测试

```bash
# 读裸盘
dd if=/dev/sda of=/dev/null bs=5M count=10 iflag=direct

# 写盘上文件（推荐）
dd if=/dev/zero of=/tmp/tmp.log bs=10M count=5 oflag=direct

# 写裸盘（不建议，容易写坏数据）
dd if=/dev/zero of=/dev/sda bs=10M count=5 oflag=direct
```

### 4. blktrace IO路径追踪

blktrace 记录IO请求在各层的流转时间，区分IO Scheduler慢还是硬件响应慢。

**注意**：出现 "Invalid argument" 时需先执行 `echo $$ >> /sys/fs/cgroup/cpuset/cgroup.procs`。

### 5. IO DFX日志开关

| 层 | 开关 | 命令 |
|----|------|------|
| block层 | block_dump | `echo 1 > /proc/sys/vm/block_dump`（开启）/ `echo 0`（关闭） |
| SCSI中层 | SCSI_LOG_MLQUEUE | `scsi_logging_level -s --mlqueue=5`（开启）/ `--mlqueue=0`（关闭） |

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| await远大于svctm | IO队列过长 | 优化业务降低IO压力 |
| util接近100% | 设备饱和 | 升级存储硬件或检查配置 |
| blktrace报Invalid argument | cpuset cgroup限制 | `echo $$ >> cpuset/cgroup.procs` |

## 来源

- [[concepts/linux-io-performance-analysis]] — IO性能分析方法
- [[concepts/linux-io-stack]] — IO栈架构