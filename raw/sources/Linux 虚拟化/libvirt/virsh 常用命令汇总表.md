
## virsh 常用命令汇总

### 一、虚拟机生命周期管理

| 命令 | 含义 | 示例 |
|------|------|------|
| `virsh list` | 列出运行中的虚拟机 | `virsh list --all` 显示全部（含关机） |
| `virsh start <domain>` | 启动虚拟机 | `virsh start vm01` |
| `virsh shutdown <domain>` | 温关机（发送 ACPI 信号） | `virsh shutdown vm01` |
| `virsh destroy <domain>` | 强关机（类似拔电源） | `virsh destroy vm01` |
| `virsh reboot <domain>` | 重启虚拟机 | `virsh reboot vm01` |
| `virsh suspend <domain>` | 暂停（挂起状态） | `virsh suspend vm01` |
| `virsh resume <domain>` | 恢复暂停的虚拟机 | `virsh resume vm01` |
| `virsh reset <domain>` | 硬重置（类似硬件复位） | `virsh reset vm01` |

---

### 二、虚拟机信息查询

| 命令 | 含义 | 示例 |
|------|------|------|
| `virsh dominfo <domain>` | 显示虚拟机详细信息（状态、CPU、内存） | `virsh dominfo vm01` |
| `virsh domstate <domain>` | 查看虚拟机状态 | `virsh domstate vm01` |
| `virsh domid <domain>` | 获取虚拟机 ID | `virsh domid vm01` |
| `virsh domname <id>` | 根据 ID 获取名称 | `virsh domname 5` |
| `virsh dumpxml <domain>` | 输出虚拟机 XML 配置 | `virsh dumpxml vm01 > vm01.xml` |
| `virsh vcpuinfo <domain>` | 显示 vCPU 信息和绑定状态 | `virsh vcpuinfo vm01` |
| `virsh domblklist <domain>` | 列出虚拟机磁盘设备 | `virsh domblklist vm01` |
| `virsh domiflist <domain>` | 列出虚拟机网络接口 | `virsh domiflist vm01` |
| `virsh dommemstat <domain>` | 显示内存统计 | `virsh dommemstat vm01` |

---

### 三、配置管理

| 命令 | 含义 | 示例 |
|------|------|------|
| `virsh define <xml>` | 从 XML 定义虚拟机（不启动） | `virsh define vm01.xml` |
| `virsh undefine <domain>` | 删除虚拟机定义 | `virsh undefine vm01` |
| `virsh edit <domain>` | 编辑虚拟机 XML 配置 | `virsh edit vm01` |
| `virsh setmem <domain> <size>` | 调整内存（需关机或支持动态） | `virsh setmem vm01 4G` |
| `virsh setvcpus <domain> <count>` | 设置 vCPU 数量 | `virsh setvcpus vm01 4` |
| `virsh vcpupin <domain> <vcpu> <cpuset>` | 绑定 vCPU 到物理 CPU | `virsh vcpupin vm01 0 2-4` |
| `virsh emulatorpin <domain> <cpuset>` | 绑定 QEMU 进程到 CPU | `virsh emulatorpin vm01 0-3` |

---

### 四、磁盘与存储管理

| 命令 | 含义 | 示例 |
|------|------|------|
| `virsh attach-disk <domain> <source> <target>` | 挂载磁盘 | `virsh attach-disk vm01 /data/disk.img vdb` |
| `virsh detach-disk <domain> <target>` | 卸载磁盘 | `virsh detach-disk vm01 vdb` |
| `virsh blockresize <domain> <path> <size>` | 调整块设备大小 | `virsh blockresize vm01 vda 20G` |
| `virsh pool-list` | 列出存储池 | `virsh pool-list` |
| `virsh pool-info <pool>` | 显示存储池信息 | `virsh pool-info default` |
| `virsh vol-list <pool>` | 列出存储卷 | `virsh vol-list default` |

---

### 五、网络管理

| 命令 | 含义 | 示例 |
|------|------|------|
| `virsh net-list` | 列出虚拟网络 | `virsh net-list --all` |
| `virsh net-info <network>` | 显示网络信息 | `virsh net-info default` |
| `virsh net-dumpxml <network>` | 输出网络 XML 配置 | `virsh net-dumpxml default` |
| `virsh net-start <network>` | 启动虚拟网络 | `virsh net-start default` |
| `virsh net-destroy <network>` | 停止虚拟网络 | `virsh net-destroy default` |
| `virsh attach-interface <domain> <type> <source>` | 挂载网卡 | `virsh attach-interface vm01 bridge br0` |
| `virsh detach-interface <domain> <type> <mac>` | 卸载网卡 | `virsh detach-interface vm01 bridge 52:54:00:xx:xx` |

---

### 六、热迁移（Live Migration）

| 命令 | 含义 | 示例 |
|------|------|------|
| `virsh migrate --live` | 热迁移虚拟机 | 见下方详细示例 |
| `virsh migrate-setmaxdowntime <domain> <ms>` | 设置最大停机时间 | `virsh migrate-setmaxdowntime vm01 500` |
| `virsh migrate-setspeed <domain> <Mbps>` | 设置迁移带宽限速 | `virsh migrate-setspeed vm01 1000` |
| `virsh migrate-getmaxdowntime <domain>` | 获取最大停机时间 | `virsh migrate-getmaxdowntime vm01` |
| `virsh migrate-getspeed <domain>` | 获取迁移带宽 | `virsh migrate-getspeed vm01` |

**热迁移完整命令示例**：
```bash
# 整机迁移（含磁盘）
virsh migrate --live --p2p --unsafe --migrateuri tcp://9.31.3.238 \
  instance-00005c53 qemu+tcp://9.31.3.238/system \
  --verbose --copy-storage-all

# 仅内存迁移（共享存储场景）
virsh migrate --live --p2p --unsafe vm01 qemu+tcp://dest-host/system

# 参数说明：
# --live        : 热迁移（不停机）
# --p2p         : 点对点迁移
# --unsafe      : 跳过安全检查
# --copy-storage-all : 整机迁移（复制磁盘）
# --verbose     : 显示详细信息
```

---

### 七、快照管理

| 命令 | 含义 | 示例 |
|------|------|------|
| `virsh snapshot-list <domain>` | 列出快照 | `virsh snapshot-list vm01` |
| `virsh snapshot-create <domain>` | 创建快照 | `virsh snapshot-create vm01` |
| `virsh snapshot-create-as <domain> <name>` | 创建命名快照 | `virsh snapshot-create-as vm01 snap1` |
| `virsh snapshot-revert <domain> <snapshot>` | 恢复快照 | `virsh snapshot-revert vm01 snap1` |
| `virsh snapshot-delete <domain> <snapshot>` | 删除快照 | `virsh snapshot-delete vm01 snap1` |
| `virsh snapshot-info <domain> <snapshot>` | 显示快照信息 | `virsh snapshot-info vm01 snap1` |

---

### 八、性能与监控

| 命令 | 含义 | 示例 |
|------|------|------|
| `virsh domstats <domain>` | 显示虚拟机统计信息 | `virsh domstats vm01` |
| `virsh cpu-stats <domain>` | CPU 使用统计 | `virsh cpu-stats vm01` |
| `virsh memtune <domain> <param> <value>` | 内存调优 | `virsh memtune vm01 hard_limit 4G` |
| `virsh blkiotune <domain> <param> <value>` | 块 IO 调优 | `virsh blkiotune vm01 weight 500` |
| `virsh schedinfo <domain>` | 查看/设置调度参数 | `virsh schedinfo vm01` |

---

### 九、其他实用命令

| 命令 | 含义 | 示例 |
|------|------|------|
| `virsh capabilities` | 显示宿主机能力（CPU 特性等） | 用于迁移兼容性检查 |
| `virsh version` | 显示 libvirt 版本 | `virsh version` |
| `virsh hostname` | 显示宿主机名 | `virsh hostname` |
| `virsh sysinfo` | 显示系统信息 | `virsh sysinfo` |
| `virsh nodeinfo` | 显示节点 CPU/内存信息 | `virsh nodeinfo` |
| `virsh console <domain>` | 连接虚拟机串口控制台 | `virsh console vm01` |
| `virsh ttyconsole <domain>` | 显示串口设备路径 | `virsh ttyconsole vm01` |

---

## 常见组合使用场景

### 场景1：创建并启动虚拟机
```bash
virsh define vm-config.xml   # 定义虚拟机
virsh start vm01             # 启动
virsh console vm01           # 连接控制台
```

### 场景2：CPU 绑定优化
```bash
virsh vcpuinfo vm01          # 查看当前绑定
virsh vcpupin vm01 0 2       # 绑定 vCPU0 到物理 CPU2
virsh emulatorpin vm01 0-3   # 绑定 QEMU 进程
```

### 场景3：动态调整资源
```bash
virsh setmem vm01 8G         # 调整内存
virsh setvcpus vm01 8        # 增加 CPU（需支持热插）
```

### 场景4：热迁移监控
```bash
# 迁移前检查兼容性
virsh capabilities > source_caps.xml
# 目的端
virsh capabilities > dest_caps.xml

# 执行迁移
virsh migrate --live vm01 qemu+tcp://dest/system --verbose

# 监控迁移进度
virsh domjobinfo vm01
```
