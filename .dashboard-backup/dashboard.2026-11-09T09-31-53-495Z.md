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
immersiveEditable: false
immersiveBackground: "https://images.unsplash.com/photo-1788651946293-893d6b217f34?q=80&w=1374&auto=format&fit=crop&ixlib=rb-4.1.0"
immersive:
  - id: "widget:quickActions"
    w: 3
    cap: 18
    fixed: true
    x: 0
    y: 15
  - id: "widget:weather"
    w: 3
    cap: 19
    fixed: true
    x: 0
    y: 35
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
    y: 12
  - id: "card:demo-memo-1"
    w: 6
    cap: 21
    fixed: true
    x: 3
    y: 0
  - id: "card:demo-todo-1"
    w: 3
    cap: 29
    fixed: true
    x: 6
    y: 21
  - id: "section:Library"
    w: 9
    cap: 34
    fixed: true
    x: 3
    y: 50
  - id: "widget:lunar"
    w: 3
    cap: 14
    fixed: true
    x: 0
    y: 0
  - id: "card:card-mw3bdxt2"
    w: 3
    cap: 29
    fixed: true
    x: 3
    y: 21
  - id: "widget:calendar"
    w: 3
    cap: 28
    fixed: true
    x: 0
    y: 56
  - id: "widget:pomodoro"
    w: 3
    cap: 18
    fixed: true
    x: 9
    y: 31
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

### 快速上手
id: demo-todo-1
type: task
- [ ] 拖住卡片右下角把它变大
- [ ] 打开左上角 + 添加一个小组件

### 2026-11-05 备忘录
id: card-mw3bdxt2
type: task
- [ ] d

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
