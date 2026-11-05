---
dashboard: true
layout: immersive
banner:
  quote: "The mind is everything. What you think you become."
  author: "Buddha"
  image: "https://images.unsplash.com/photo-1788651946293-893d6b217f34?q=80&w=1374&auto=format&fit=crop&ixlib=rb-4.1.0"
  quoteFont: "Didot,\"Bodoni MT\",Georgia,serif"
  images:
    - "https://images.unsplash.com/photo-1788651946293-893d6b217f34?q=80&w=1374&auto=format&fit=crop&ixlib=rb-4.1.0"
immersiveBackground: "https://images.unsplash.com/photo-1788651946293-893d6b217f34?q=80&w=1374&auto=format&fit=crop&ixlib=rb-4.1.0"
immersive:
  - id: "widget:quickActions"
    w: 3
    cap: 18
    fixed: true
    x: 0
    y: 14
  - id: "widget:weather"
    w: 3
    cap: 19
    fixed: true
    x: 0
    y: 32
  - id: "widget:countdown-cd-2026-end"
    w: 3
    cap: 10
    fixed: true
    x: 9
    y: 0
  - id: "widget:music"
    w: 3
    cap: 17
    fixed: true
    x: 9
    y: 10
  - id: "card:demo-memo-1"
    w: 6
    cap: 21
    fixed: true
    x: 3
    y: 0
  - id: "card:demo-todo-1"
    w: 3
    cap: 42
    fixed: true
    x: 6
    y: 21
  - id: "section:Library"
    w: 9
    cap: 34
    fixed: true
    x: 3
    y: 63
  - id: "widget:album-1793868541713"
    w: 3
    cap: 21
    fixed: true
    x: 9
    y: 27
  - id: "widget:lunar"
    w: 3
    cap: 14
    fixed: true
    x: 0
    y: 0
  - id: "widget:reading"
    w: 3
    cap: 15
    x: 9
    y: 48
  - id: "card:card-mw3bdxt2"
    w: 3
    cap: 42
    fixed: true
    x: 3
    y: 21
  - id: "widget:calendar"
    w: 3
    cap: 28
    fixed: true
    x: 0
    y: 51
  - id: "widget:pomodoro"
    w: 3
    cap: 18
    fixed: true
    x: 0
    y: 79
columns:
  - name: 便利贴
    color: "#f59e0b"
    type: sticky
  - name: Library
    color: "#8b5cf6"
    type: projects
    showCover: false
    library:
      viewMode: grid
      sortBy: "modified"
      sortDesc: true
---

## 便利贴

### 2026-11-05 备忘
id: demo-memo-1
type: generic
欢迎使用 Apex Dashboard！点击此处编辑你的第一条备忘。

### 快速上手
id: demo-todo-1
type: task
- [ ] 拖动这张卡片换个位置
- [ ] 拖住卡片右下角把它变大
- [ ] 打开左上角 + 添加一个小组件

### 2026-11-05 备忘录
id: card-mw3bdxt2
type: task
- [ ] 今天完成

## Library

### Reading
id: demo-lib-reading
type: project
width: 218

### To Read
id: demo-lib-toread
type: project
width: 232

### Done
id: demo-lib-done
type: project
