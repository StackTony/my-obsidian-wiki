---
title: Linux IO性能分析方法
category: concepts
tags: [linux, io, 性能分析, iostat, fio]
aliases: [IO性能分析, iostat, blktrace, block_dump]
relationships:
  - target: "[[concepts/linux-io-stack]]"
    type: uses
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
source_dir: DFX工具
source_files: [==IO==/IO常用工具.md]
summary: Linux IO性能分析工具链：iostat监控磁盘利用率和时延、fio压测IO性能、dd测裸盘读写速率、blktrace追踪IO路径、block_dump+SCSI_LOG日志开关。
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

# Linux IO性能分析方法

IO性能分析聚焦磁盘设备利用率、IO请求时延和队列深度。通过 iostat 定量监控、fio 定性压测、blktrace 定位瓶颈层，形成从宏观到微观的完整分析链路。

## 核心观点

- **iostat 是IO监控的第一入口**：`%util` 接近100表示设备饱和，`await >> svctm` 表示IO队列过长而非设备慢
- **fio 是IO压测的标准工具**：支持随机读写/顺序读写/混合负载，通过 `-rw/randread|randwrite|read|write` 和 `-bs` 控制测试模型
- **blktrace 追踪IO请求在内核各层的流转时间**：能区分是IO Scheduler慢还是硬件响应慢
- **IO分析黄金法则**：`svctm < 5ms` 设备正常；`svctm > 5ms + util≈100%` 设备瓶颈；`await >> svctm` 队列过长需优化业务

## 关键细节

### iostat 关键指标解读

| 指标 | 含义 | 健康阈值 |
|------|------|----------|
| r/s, w/s | 每秒读写请求数 | 与设备规格对比 |
| avgqu-sz | 平均请求队列长度 | 越小越好 |
| await | 平均请求等待时间(ms) | 应接近svctm |
| svctm | 平均请求服务时间(ms) | <5ms为正常 |
| %util | 设备利用率 | 接近100%为饱和 |

**四种分析方法**：

| 场景 | 判断标准 | 处理方向 |
|------|----------|----------|
| 设备瓶颈 | util≈100% + svctm>5ms | 存储硬件问题 |
| 队列过长 | r/s或w/s大 + svctm<5ms + await>>svctm | 优化虚拟机业务降低IO压力 |
| 正常 | r/s或w/s大 + svctm<5ms + await≈svctm | 无需处理 |
| 性能对比 | 同模型下svctm越小越好 | svctm降低0.1ms可能大幅改善数据库性能 |

### IO DFX日志开关

| 层 | 开关 | 命令 |
|----|------|------|
| block层 | block_dump | `echo 1/0 > /proc/sys/vm/block_dump` |
| SCSI中层 | SCSI_LOG_MLQUEUE | `scsi_logging_level -s --mlqueue=5/0` |

### blktrace 注意事项

若出现 "Invalid argument" 报错，需先执行 `echo $$ >> /sys/fs/cgroup/cpuset/cgroup.procs`。

## 未解问题

- blktrace 具体使用方法和输出格式未在源文件中详述
- iotop 工具仅列出名称，缺少详细使用说明
- block_dump 日志输出格式和解析方法未详细说明

## 来源

- [[concepts/linux-io-stack]] — IO栈架构