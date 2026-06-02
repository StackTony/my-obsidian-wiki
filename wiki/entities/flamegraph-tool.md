---
title: 火焰图工具
category: entities
tags: [linux, 火焰图, FlameGraph, 性能分析, CPU可视化]
aliases: [FlameGraph, 火焰图, flamegraph]
relationships:
  - target: "[[entities/perf-tool]]"
    type: uses
  - target: "[[concepts/linux-cpu-performance-analysis]]"
    type: related_to
source_dir: DFX工具
source_files: [==设置trace点==/3 火焰图.md, "==CPU==/火焰图抓取CPU占用情况.md"]
summary: 火焰图(FlameGraph)是CPU调用栈的可视化SVG工具：y轴调用栈深度、x轴采样占比宽度，平顶(plateau)即为性能瓶颈。基于perf record数据生成。
provenance:
  extracted: 0.85
  inferred: 0.10
  ambiguous: 0.05
base_confidence: 0.65
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# 火焰图工具

火焰图 (FlameGraph) 是 Brendan Gregg 创建的 CPU 调用栈可视化工具，将 perf 采样数据转换为 SVG 图形，直观展示函数调用层次和CPU时间分布。

## 简介

GitHub 项目：https://github.com/brendangregg/FlameGraph

## 关键属性

| 属性 | 值 |
|------|-----|
| 作者 | Brendan Gregg |
| 输入 | perf record 采样数据 |
| 输出 | SVG 火焰图 |
| 转换流程 | perf script → stackcollapse-perf.pl → flamegraph.pl |
| Y轴 | 调用栈深度（每层一个函数） |
| X轴 | 采样数占比（按字母排序合并） |
| 颜色 | 随机，无特殊含义 |
| 瓶颈识别 | 平顶(plateaus)=性能问题 |

## 与其他实体的关系

- **perf** — 火焰图依赖 perf record 采集调用栈数据，是 perf 的可视化前端
- **ftrace/kprobe** — ftrace 的 function_graph 也能生成调用栈，但火焰图通常与 perf 配合 ^[inferred]

## 使用流程

### 方法一（标准流程）

```bash
# 1. 采集数据
perf record -e cpu-clock -g -p `pidof xxx`
# Ctrl+C 结束，生成 perf.data

# 2. 解析数据
perf script -i perf.data > perf.unfold

# 3. 折叠符号（进入FlameGraph目录）
./stackcollapse-perf.pl perf.unfold > perf.folded

# 4. 生成SVG
./flamegraph.pl perf.folded > perf.svg
```

### 方法二（指定CPU核）

```bash
perf record -C 33-38 -g -a -- sleep 20
perf script > out.perf
/opt/FlameGraph/stackcollapse-perf.pl out.perf > out.folded
/opt/FlameGraph/flamegraph.pl out.folded > cpu.svg
```

## 解读规则

- **横向宽度** = 函数被采样到的次数占比 → 宽度越大执行时间越长
- **纵向深度** = 调用栈层级 → 越高越深的子函数调用
- **平顶山(plateau)** = 宽大且顶部平坦的函数 → **性能瓶颈嫌疑**
- X轴不代表时间，而是所有调用栈合并后按字母排序的统计视图

## 来源

- [[entities/perf-tool]] — perf性能分析工具