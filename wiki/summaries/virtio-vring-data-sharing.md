---
title: Virtio数据共享机制：vring环
category: summaries
tags: [linux, 虚拟化, virtio, vring, 数据共享]
source_dir: Linux 虚拟化/IO虚拟化
source_files: ["3）数据共享机制（vring环）.md"]
summary: vring是virtio前后端数据共享的核心结构，由desc/avail/used三个表组成。前端add_buf写入请求，后端get_buf取出处理，通过共享内存实现零拷贝数据传递。
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

# Virtio数据共享机制：vring环

vring是virtio数据平面的核心——前后端通过共享内存中的三个表完成IO请求的传递与回收。因为虚拟机内存本身就是QEMU进程地址空间的一部分，前端只需将内存区域地址传递给QEMU即可实现共享。

## 核心观点

### vring三大表

| 表 | 生产者 | 消费者 | 作用 |
|---|---|---|---|
| `vring_desc` | 前端(Guest) | 后端(QEMU) | 存放IO请求的GPA地址和长度 |
| `vring_avail` | 前端(Guest) | 后端(QEMU) | 前端告诉后端"有新请求可取" |
| `vring_used` | 后端(QEMU) | 前端(Guest) | 后端告诉前端"IO处理完了可回收" |

**两个生产者-消费者模型**：前端是请求的生产者和响应的消费者，后端是请求的消费者和响应的生产者。

### vring_desc结构

```c
struct vring_desc {
    __virtio64 addr;    // IO请求在Guest内存中的GPA地址
    __virtio32 len;     // IO请求长度
    __virtio16 flags;   // VRING_DESC_F_WRITE(可写) / VRING_DESC_F_NEXT(链表还有下一项)
    __virtio16 next;    // 链表下一项在desc表中的位置
};
```

一个IO请求可能占据desc表中多行，通过`next`域链接成链表。当`flags & ~VRING_DESC_F_NEXT`时表示链表末尾。

### vring_avail结构

```c
struct vring_avail {
    __virtio16 flags;   // 标志位
    __virtio16 idx;     // ring数组中下一个可用位置
    __virtio16 ring[];  // 每个IO请求链表头在desc表中的位置
};
```

### vring_used结构

```c
struct vring_used_elem {
    __virtio32 id;      // 处理完成的IO请求链表头在desc表中的位置
    __virtio32 len;     // 链表长度
};
struct vring_used {
    __virtio16 flags;
    __virtio16 idx;     // ring数组中下一个可用位置
    struct vring_used_elem ring[];
};
```

### 前端操作：virtqueue_add_buf

1. 将IO请求地址存入当前空闲的vring_desc表项的addr域
2. 设置flags域：未完则VRING_DESC_F_NEXT，完成则~VRING_DESC_F_NEXT
3. 通过next域将IO请求的多个desc表项链接成链表
4. 将链表头位置写入vring_avail→ring[idx]，idx++
5. 通过kick函数通知后端来取数据

### 后端操作：virtqueue_get_buf

1. 从vring_avail中取出数据，直到idx位置
2. 根据avail值从vring_desc取出链表头，沿next遍历整个IO请求
3. 封装IO请求发送给硬件执行
4. 将链表头位置存入vring_used→ring[idx].id，idx++
5. 前端根据used表信息释放desc表相应表项

## 来源

- `raw/sources/Linux 虚拟化/IO虚拟化/3）数据共享机制（vring环）.md` — vring三大表数据结构、add_buf/get_buf操作流程、生产者-消费者模型

> 相关概念：[[concepts/linux-virtio-architecture]]（virtio整体框架）、[[summaries/virtio-io-notification-mechanism]]（消息通知机制）