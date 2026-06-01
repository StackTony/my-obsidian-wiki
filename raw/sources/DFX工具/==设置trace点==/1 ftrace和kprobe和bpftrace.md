
https://zhuanlan.zhihu.com/p/652907405

![[v2-4268bd3153517778fe43a889dbaadf21_1440w.png]]

```
ftrace（函数追踪）
    │
    ├── 优点：完整函数调用链、function_graph
    │
    ├── 缺点：只能追踪静态函数，开销大
    │
    ▼
kprobe（动态追踪）
    │
    ├── 优点：可追踪任意内核函数、灵活
    │
    ├── 应用：sched_switch、virtio_notify 等
```


## 相关链接

- [[trace：ftrace使用方法]]
- [[trace：kprobe使用方式]]