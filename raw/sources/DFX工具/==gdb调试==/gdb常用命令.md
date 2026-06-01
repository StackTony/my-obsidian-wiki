# GDB 常用命令速查指南

> 整理自 hellogcc 《100 个 GDB 调试技巧》
> 源项目: https://github.com/hellogcc/100-gdb-tips

---

## 一、启动与退出

| 命令 | 缩写 | 说明 |
|------|------|------|
| `gdb program` | - | 启动调试指定程序 |
| `gdb -q program` | - | 启动时不显示提示信息 |
| `quit` | `q` | 退出 GDB |
| `run [args]` | `r` | 运行程序，可带参数 |
| `start` | - | 运行到 main 函数入口 |

**设置程序参数：**
```bash
(gdb) set args arg1 arg2 arg3    # 设置运行参数
(gdb) show args                   # 查看当前参数
```

---

## 二、断点管理 🔥

### 基本断点命令

| 命令 | 说明 |
|------|------|
| `break main` | 在 main 函数设置断点 |
| `break file.c:10` | 在指定文件的第 10 行设置断点 |
| `break file.c:func` | 在指定文件的函数设置断点 |
| `break *0x400500` | 在指定地址设置断点 |
| `tbreak ...` | 设置临时断点（触发一次后自动删除） |
| `info breakpoints` | 查看所有断点 |
| `delete 1` | 删除 1 号断点 |
| `disable 1` | 禁用 1 号断点 |
| `enable 1` | 启用 1 号断点 |
| `clear` | 删除所有断点 |

### 条件断点 🔥

**语法：** `break ... if condition`

```bash
# 在第 10 行设置条件断点，当 i==101 时触发 break 10 if i==101

# 修改已有断点的条件 1 if i==200

# 删除断点条件 1
```

**应用场景：** 循环中只关注特定迭代、特定变量值时触发。

### 忽略断点

```bash
# 忽略 1 号断点的前 10 次触发 ignore 1 10
```

### 保存和恢复断点

```bash
# 保存断点到文件 save breakpoints bp.txt

# 加载断点 source bp.txt
```

---

## 三、观察点 (Watchpoint) 🔥

观察点用于监控变量或内存的变化，当值改变时程序自动停止。

| 命令 | 说明 |
|------|------|
| `watch var` | 当 var 被写入时停止 |
| `rwatch var` | 当 var 被读取时停止 |
| `awatch var` | 当 var 被读取或写入时停止 |
| `info watchpoints` | 查看所有观察点 |

**示例：**
```bash
# 监控变量 a 的变化 a
Hardware watchpoint 2: a

# 监控指定地址的内存变化 *(int*)0x6009c8
```

**注意：** 软件观察点会导致程序运行变慢，硬件观察点性能更好。

---

## 四、执行控制

### 单步执行

| 命令 | 缩写 | 说明 |
|------|------|------|
| `next` | `n` | 执行下一行，不进入函数 |
| `step` | `s` | 执行下一行，进入函数 |
| `continue` | `c` | 继续执行到下一个断点 |
| `finish` | - | 执行到当前函数返回 |
| `return [value]` | - | 立即返回，可指定返回值 |
| `until` | `u` | 执行到指定行或循环结束 |

### 进入无调试信息的函数

```bash
# 设置进入无调试信息函数的模式 set step-mode on   # 进入
(gdb) set step-mode off  # 不进入
```

---

## 五、打印与显示 🔥

### 基本打印

| 命令 | 说明 |
|------|------|
| `print var` | 打印变量值 |
| `print *ptr` | 打印指针指向的值 |
| `print arr[0]@10` | 打印数组前 10 个元素 |
| `print/x var` | 以十六进制打印 |
| `print/t var` | 以二进制打印 |
| `print/c var` | 以字符打印 |
| `ptype var` | 打印变量类型 |
| `info locals` | 打印所有局部变量 |
| `info args` | 打印函数参数 |

### 打印内存 (examine) 🔥

**语法：** `x/nfu addr`

- `n`：单元个数
- `f`：输出格式
- `u`：单元大小

| 格式 (f) | 说明 | 单位 (u) | 说明 |
|----------|------|----------|------|
| `x` | 十六进制 | `b` | 1 byte |
| `d` | 十进制 | `h` | 2 bytes (halfword) |
| `u` | 无符号十进制 | `w` | 4 bytes (word) |
| `o` | 八进制 | `g` | 8 bytes (giant word) |
| `t` | 二进制 | | |
| `c` | 字符 | | |
| `s` | 字符串 | | |

**示例：**
```bash
# 打印 16 个字节的十六进制值 x/16xb arr

# 打印 16 个字节的二进制值 x/16tb arr

# 打印 16 个 word 的十六进制值 x/16xw arr

# 打印字符串 x/s str
```

### 格式化打印

```bash
# 每行打印一个结构体成员 set print pretty on

# 打印数组时显示索引 set print array-indexes on

# 打印 C++ 虚表信息 info vtbl object
```

### 显示命令 (Display)

```bash
# 每次停止时自动显示变量 display var

# 查看所有 display info display

# 删除 display undisplay 1
```

---

## 六、堆栈与帧

| 命令 | 说明 |
|------|------|
| `backtrace` | `bt` | 显示调用堆栈 |
| `bt full` | 显示完整堆栈和局部变量 |
| `frame 2` | 切换到第 2 层栈帧 |
| `up` | 向上切换栈帧 |
| `down` | 向下切换栈帧 |
| `info frame` | 显示当前帧详细信息 |
| `info registers` | 显示寄存器值 |

---

## 七、多线程调试 🔥

### 查看线程信息

```bash
# 列出所有线程 info threads

# 打印所有线程的堆栈 thread apply all bt

# 切换到 3 号线程 thread 3

# 查看当前线程线程号 $_thread
```

### 线程控制

```bash
# 只允许当前线程运行 set scheduler-locking on

# 恢复所有线程运行 set scheduler-locking off

# 设置线程断点 break func thread 2
```

---

## 八、多进程调试 🔥

### 进程跟随模式

```bash
# 设置跟随子进程 set follow-fork-mode child

# 设置跟随父进程 set follow-fork-mode parent

# 同时调试父进程和子进程 set detach-on-fork off
```

### 查看进程信息

```bash
# 查看所有进程 info inferiors

# 切换进程 inferior 2
```

---

## 九、Core Dump 文件

### 生成 Core Dump

```bash
# 在 GDB 中生成 core dump generate-core-file

# 或使用 gcore 命令 gcore <pid>
```

### 加载 Core Dump

```bash
# 加载可执行程序和 core 文件 gdb ./program core.12345

# 或在 GDB 中加载 core-file core.12345
```

---

## 十、汇编调试

| 命令 | 说明 |
|------|------|
| `disassemble` | 反汇编当前函数 |
| `disassemble func` | 反汇编指定函数 |
| `set disassembly-flavor intel` | 设置 Intel 汇编格式 |
| `set disassembly-flavor att` | 设置 AT&T 汇编格式 |
| `info registers` | 显示所有寄存器 |
| `print $pc` | 打印 PC 寄存器值 |
| `layout asm` | 显示汇编窗口 |

---

## 十一、信号处理

```bash
# 查看信号处理信息 info signals

# 信号发生时不暂停程序 handle SIGUSR1 nostop

# 信号发生时不打印信息 handle SIGUSR1 noprint

# 不把信号传给程序 handle SIGUSR1 nopass

# 给程序发送信号 signal SIGUSR1
```

---

## 十二、TUI 图形界面 🔥

| 命令 | 说明 |
|------|------|
| `tui enable` | 进入 TUI 模式 |
| `tui disable` | 退出 TUI 模式 |
| `layout src` | 显示源代码窗口 |
| `layout asm` | 显示汇编窗口 |
| `layout split` | 同时显示源码和汇编 |
| `layout regs` | 显示寄存器窗口 |
| `focus src` | 焦点切换到源码窗口 |
| `focus cmd` | 焦点切换到命令窗口 |
| `winheight src +5` | 调整窗口高度 |

**快捷键：**
- `Ctrl+X A`：切换 TUI 模式
- `Ctrl+X 2`：切换双窗口布局

---

## 十三、实用技巧

### 修改程序执行

```bash
# 修改变量值 set var = 100

# 修改字符串 set {char[6]}str = "hello"

# 修改 PC 寄存器（跳转执行） set $pc = 0x400500

# 跳转到指定位置执行 jump +10
```

### 自动化调试

```bash
# 定义命令宏 define print_all
> info locals
> info args
> end

# 断点触发时执行命令 commands 1
> print var
> continue
> end
```

### 日志记录

```bash
# 开启日志 set logging on

# 设置日志文件 set logging file gdb.log
```

### 源码路径

```bash
# 添加源码搜索路径 directory /path/to/src

# 替换源码路径 set substitute-path /old /new
```

---

## 十四、命令缩写速查表

| 完整命令 | 缩写 | 说明 |
|----------|------|------|
| `break` | `b` | 设置断点 |
| `run` | `r` | 运行程序 |
| `next` | `n` | 单步执行（不进入函数） |
| `step` | `s` | 单步执行（进入函数） |
| `continue` | `c` | 继续执行 |
| `print` | `p` | 打印变量 |
| `backtrace` | `bt` | 显示堆栈 |
| `info` | `i` | 查看信息 |
| `list` | `l` | 显示源码 |
| `delete` | `d` | 删除断点 |
| `disable` | `dis` | 禁用断点 |
| `enable` | `en` | 启用断点 |
| `finish` | `fin` | 执行到函数返回 |
| `until` | `u` | 执行到指定位置 |
| `watch` | `wa` | 设置观察点 |
| `thread` | `t` | 线程操作 |

---

## 十五、常见调试场景

### 场景1：调试循环中的特定迭代

```bash
# 设置条件断点，只在 i==100 时停止 break loop.c:20 if i==100
```

### 场景2：追踪变量何时被修改

```bash
# 设置观察点 watch global_var
```

### 场景3：调试多线程死锁

```bash
# 查看所有线程状态 thread apply all bt

# 只让当前线程运行 set scheduler-locking on
```

### 场景4：分析 core 文件

```bash
gdb ./program core.12345

# 在 GDB 中 backtrace full
```

### 场景5：调试子进程

```bash
# 启动 GDB set follow-fork-mode child
(gdb) start
```

---

## 参考资源

- **GDB 官方手册**: https://sourceware.org/gdb/onlinedocs/gdb/
- **100 个 GDB 调试技巧**: https://github.com/hellogcc/100-gdb-tips
- **GDB Dashboard**: https://github.com/cyrus-and/gdb-dashboard (增强型 GDB 界面)

---

## 标签

#GDB #调试 #Linux #开发工具 #性能分析