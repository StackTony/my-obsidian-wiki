### 开启trunk/bonding调试日志命令
```bash
echo 8 > /proc/sys/kernel/printk 

echo 'file drivers/net/bonding/bond_3ad.c +p' >> /sys/kernel/debug/dynamic_debug/control 
echo 'file drivers/net/bonding/bond_main.c +p' >> /sys/kernel/debug/dynamic_debug/control
```

### 命令作用说明
这三组命令用于**开启内核网络Bonding(链路聚合)模块调试日志**，配合调整内核打印级别，方便排查Bond、802.3ad聚合问题。

---
### 逐条解析
#### 1. `echo 8 > /proc/sys/kernel/printk`
修改内核日志打印级别，**临时生效**（重启失效）。
- `printk` 格式：`控制台级别 默认消息级别 最低控制台级别 默认控制台级别`
- 写入 `8`：放开**所有级别内核日志**输出，让动态调试日志能正常打印到 dmesg/控制台。
- 查看当前级别：`cat /proc/sys/kernel/printk`

#### 2. 动态调试开启 Bond 源码打印
内核 **dynamic debug（动态调试）** 机制，`+p` 表示**启用该文件内所有 `pr_debug()`/dev_dbg() 调试打印**：
```bash
# 开启 bond_3ad.c（802.3ad 聚合协议逻辑）调试
echo 'file drivers/net/bonding/bond_3ad.c +p' >> /sys/kernel/debug/dynamic_debug/control

# 开启 bond_main.c（Bond 主逻辑、状态、收发）调试
echo 'file drivers/net/bonding/bond_main.c +p' >> /sys/kernel/debug/dynamic_debug/control
```

---
### 配套常用操作
#### 1. 查看已开启的动态调试点
```bash
cat /sys/kernel/debug/dynamic_debug/control | grep bond
```

#### 2. 实时查看 Bond 调试日志
```bash
dmesg -wT
# 或过滤关键字
dmesg -wT | grep -i bond
```

#### 3. 关闭调试（恢复默认）
```bash
# 关闭对应文件调试打印
echo 'file drivers/net/bonding/bond_3ad.c -p' > /sys/kernel/debug/dynamic_debug/control
echo 'file drivers/net/bonding/bond_main.c -p' > /sys/kernel/debug/dynamic_debug/control

# 恢复默认 printk 级别（常见默认值 7）
echo 7 > /proc/sys/kernel/printk
```

#### 4. 永久生效（可选，不建议生产常开）
编辑 `/etc/sysctl.conf` 持久化 printk：
```ini
kernel.printk = 8
```
生效：`sysctl -p`
动态调试开机自启需写 `rc.local` 或 systemd 服务。

---
### 注意事项
1. **权限**：必须 `root` 执行，普通用户会权限不足。
2. **debugfs**：确保 `debugfs` 已挂载，大部分系统默认挂载在 `/sys/kernel/debug`；未挂载执行：
   ```bash
   mount -t debugfs none /sys/kernel/debug
   ```
3. **性能**：生产环境长时间开启会产生大量日志、轻微损耗性能，排障完成务必关闭。
4. **内核版本**：dynamic debug 主流 Linux 内核（3.x+）均支持。