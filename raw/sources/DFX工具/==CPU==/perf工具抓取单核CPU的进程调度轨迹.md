---
tags:
  - perf
---

**perf sched抓取CPU调度**
perf sched record -g -p 12345 sleep10

perf sched script \> cpu_sched.log
