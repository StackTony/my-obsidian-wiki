---
title: 内核网络Bonding调试日志
category: summaries
tags: [linux, 内核, 网络, bonding, dynamic-debug]
source_dir: DFX工具/==网络==
source_files: [内核网络Bonding调试日志.md]
summary: 开启内核网络Bonding(链路聚合)模块调试日志的方法：调整printk级别+dynamic debug开启bond_3ad/bond_main源码打印，配合dmesg实时观测802.3ad聚合问题。
provenance:
  extracted: 0.90
  inferred: 0.05
  ambiguous: 0.05
base_confidence: 0.59
lifecycle: draft
lifecycle_changed: 2026-06-15
tier: supporting
created: 2026-06-15
updated: 2026-06-15
---

# 内核网络Bonding调试日志

原文蒸馏：开启内核 Bonding（链路聚合）模块调试日志的完整方法，用于排查 Bond/802.3ad 聚合问题。

## 核心内容

### 1. 调整内核日志级别

```bash
echo 8 > /proc/sys/kernel/printk
```

- `printk` 四个参数格式：`控制台级别 默认消息级别 最低控制台级别 默认控制台级别`
- 写入 `8` 放开所有级别内核日志输出，让 dynamic debug 的 `pr_debug()/dev_dbg()` 打印能显示到 dmesg/控制台
- **临时生效**，重启后失效
- 查看当前级别：`cat /proc/sys/kernel/printk`

### 2. Dynamic Debug 开启 Bond 源码打印

内核 dynamic debug 机制，`+p` 启用该文件内所有 `pr_debug()/dev_dbg()` 调试打印：

```bash
# 开启 bond_3ad.c（802.3ad 聚合协议逻辑）
echo 'file drivers/net/bonding/bond_3ad.c +p' >> /sys/kernel/debug/dynamic_debug/control

# 开启 bond_main.c（Bond 主逻辑、状态、收发）
echo 'file drivers/net/bonding/bond_main.c +p' >> /sys/kernel/debug/dynamic_debug/control
```

### 3. 配套操作

**查看已开启的动态调试点**：
```bash
cat /sys/kernel/debug/dynamic_debug/control | grep bond
```

**实时查看 Bond 调试日志**：
```bash
dmesg -wT
dmesg -wT | grep -i bond
```

**关闭调试（恢复默认）**：
```bash
echo 'file drivers/net/bonding/bond_3ad.c -p' > /sys/kernel/debug/dynamic_debug/control
echo 'file drivers/net/bonding/bond_main.c -p' > /sys/kernel/debug/dynamic_debug/control
echo 7 > /proc/sys/kernel/printk  # 恢复默认级别
```

**永久生效（不建议生产常开）**：
- `/etc/sysctl.conf` 中 `kernel.printk = 8`，执行 `sysctl -p`
- dynamic debug 开机自启需写 `rc.local` 或 systemd 服务

### 4. 注意事项

- **权限**：必须 root 执行
- **debugfs**：确保已挂载 `/sys/kernel/debug`，未挂载执行 `mount -t debugfs none /sys/kernel/debug`
- **性能**：生产环境长时间开启产生大量日志、轻微损耗性能，排障完成务必关闭
- **内核版本**：dynamic debug 主流 Linux 内核（3.x+）均支持

## 来源

- 原始文件：`raw/sources/DFX工具/==网络==/内核网络Bonding调试日志.md`
