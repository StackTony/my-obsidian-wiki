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
    y: 16
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
    y: 32
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
- [ ] 检视发现了几个问题处理下：⏎1、frontend/src/views/DiagnosisView.vue：clearAttached 里没调 scheduleSaveFiles:模板「清空」按钮直接绑的这个函数,点完清空再刷新或切回会话,勾选又回来了。pickRoot 里现在是手动补的 saveSessionFiles,建议把 scheduleSaveFiles() 挪进 clearAttached 内部,pickRoot 那句手动调用就可以删了。⏎⏎2、frontend/src/views/DiagnosisView.vue：onTreeSelect，这里有个回环:切会话恢复勾选时,attached 恢复 → attachedIds → 树同步 selectedIds → 树 emit select → 又回到 onTreeSelect → scheduleSaveFiles,内容没变也会 PATCH 一次同样的 selected_files。建议持久化前比对一下前后 id 列表,一致就跳过。⏎⏎3、frontend/src/components/diagnosis/ComposerTaskDock.vue：editing 存的是数组下标,队列一动就串行:正在编辑第 2 条时,如果队头被自动发走、或用户删了前面某条,下标整体前移,保存时会写到你没在编辑的那条消息上。下面的 watch 只兜住了 editing >= len 一种情况。建议给 QueuedItem 加个自增 id,编辑态跟着 id 走而不是下标。⏎⏎4、frontend/src/views/DiagnosisView.vue：saveSessionRoot、上面的 saveSessionFiles、以及 onKbChange(约 L484)是三段一模一样的「patchSession → findIndex → merge sessions → catch apiError」,抽一个 patchAndMergeSession(sid, payload) 三处共用吧。另外 pickRoot(L259)把 root 和 files 拆成两次 PATCH,后端一个请求就能一起收,顺便合并。⏎⏎5、frontend/src/components/diagnosis/AssistantTurn.vue：这套 clipboard + execCommand 降级建议抽成公共 util:DiagnosisFileReader.copyPath(L23 附近)还是裸的 navigator.clipboard.writeText,HTTP 环境下静默失败。抽个 copyText() 两处共用,顺手把旧的那处也修好。⏎⏎6、frontend/src/views/DiagnosisView.vue：runTurn 从 SSE 事件分发到收尾排队调度 90 来行,而且这个文件已经 2300+ 行、本次又涨了 200 行。建议至少把 onEvent 里的分支分发抽成独立 handler;进一步可以把排队逻辑和会话持久化分别拆成 composable,不然这个 view 会越来越难维护。⏎⏎7、frontend/src/views/DiagnosisView.vue：queue 和 QueuedItem 定义在这儿,但 L516 的 loadMessageList、L563 的 addSession 已经在用了,读代码得往下翻 200 行找定义。运行时虽然不会踩 TDZ,但状态声明建议统一放到顶部状态区,和 attached、fileNodes 它们放一起。⏎⏎8、frontend/src/components/diagnosis/toolLabel.ts：共享 ts 工具的存放位置现在出现两种约定:已有的 diagnosisFiles.ts 在 components/ 根,这个新文件在 components/diagnosis/。两个消费方都在 diagnosis/ 下,放这儿说得通,但建议和 diagnosisFiles.ts 统一一下,别两套并存,后面再加工具就乱了。⏎⏎9、backend/app/api/diagnosis.py：selected_files 只限了条数(200),单条 id/name/path 没限长度,str() 任意长度都能进 JSONB。local_root 有 512 上限,这里每个字段也加个最大长度保持一致。⏎⏎10：backend/app/api/diagnosis.py：docstring 只补了 local_root,漏了 selected_files。另外 L709 selected_files 块后面多了一个空行,和上下文的 if 块间距不一致,顺手对齐。⏎⏎以上是针对之前的提交提出的修改建议，判断下是否合理，合适的话进行修改并重新提交推送远端；

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
