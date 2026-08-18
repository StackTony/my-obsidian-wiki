
## 1. dsh-web-ui ⭐1312
Web 界面增强全家桶，一次补齐官方最大的短板

官方 Web UI 最被吐槽的就是「素」。这个插件集一次补齐：任务看板、Git 图谱、右侧面板、手机端远程访问、实时 Token 统计、多套皮肤。几乎装完就解决了「界面简陋」这个最大痛点，颜值和使用效率同时拉满。

任务看板（五列：待规划 / 待办 / 进行中 / 已完成 / 已失败）
Git 可视化图谱
右侧工具面板
移动端远程访问
桌宠系统
Token 实时统计
主题皮肤中心
仓库：
https://github.com/zhu1090093659/dsh-web-ui

安装：dsh plugin --profile web add dsh-web-ui

## 2. modlens ⭐1274
给纯文本模型装上一双眼睛

DeepSeek 本身是纯文本模型，最大的短板就是看不了图。ModLens 的 README 第一句就是「Give a text-only model sight」——你直接把图片粘贴进聊天框，它通过一个原生工具把图转成结构化文本证据，再喂给模型作答。

图片理解
OCR 文字识别
页面结构分析
输出结构化 JSON
适合：UI 设计稿还原、报错截图分析、文档 / 流程图解析。

仓库：
https://github.com/liustack/modlens

安装：dsh plugin --profile web add @liustack/modlens

## 3. DSH-better-sidebar ⭐702
把 DSH 从聊天框变成完整 AI IDE 工作台

原本只是个文件树的侧边栏，被它升级成了一整套工作台：文件渲染与编辑、内置终端、Git 操作、子代理管理都在里面，还支持注册第三方新 Tab、自由调布局。重度用文件和终端的人会非常顺手——不用在编辑器和终端之间反复切窗口。

文件浏览器
文件编辑
xterm.js 终端
Git 管理
子 Agent
自定义 Tab
仓库：
https://github.com/omdsh-dev/DSH-better-sidebar

安装：dsh plugin --profile web add
github:omdsh-dev/DSH-better-sidebar

## 4. dsh-TUI ⭐643
️ 终端党的快乐：Claude Code 风格全屏终端

把整个交互换成 Claude Code 风格的全屏终端，像素鲸鱼顶栏、流式思考展开、上下文进度条加 TPS 表。喜欢纯键盘、追求沉浸感的人会一眼爱上。

全屏终端体验
Markdown 流式渲染
会话恢复
模型切换
仓库：
https://github.com/ccch1mneyyy/dsh-TUI

安装：npm install -g @
deepseek-harness-tui/dsh-tui，随后直接运行 dsh-tui（独立终端 profile）

## 5. dsh-deep-whale ⭐378
DeepSeek 专属萌系皮肤（深海女仆工坊）

不图生产力，图个心情。给界面换上一整套深海与鲸鱼风格的主题，长期盯着屏幕干活，一点点可爱能增加持久力。

鲸鱼娘主题
UI 美化
动态效果
仓库：
https://github.com/Small-tailqwq/dsh-deep-whale

安装：dsh plugin --profile web add
github:Small-tailqwq/dsh-deep-whale

6. dsh-vision-toolkit ⭐267
️ 视觉任务增强包，在 modlens 之上更进一步

如果说 modlens 是「通用看图」，那这个工具箱更偏向开发 / 测试场景：带意图的图片问答、长截图 OCR、UI 界面还原，甚至能做像素级对比，形成「参考图 → 写页面 → 截图 → 对比 → 再改」的前端闭环。

图片问答
长截图 OCR
UI 页面还原
图片分析
仓库：
https://github.com/Anionex/dsh-vision-toolkit

安装：dsh plugin --profile web add
github:Anionex/dsh-vision-toolkit

## 7. dsh-browser ⭐64
让 DSH 直接操控真实 Chrome

不是靠视觉模型去猜按钮位置，而是把网页转成结构化文本，给链接、按钮、输入框编号，再由模型通过编号操作。保留登录态和 Cookie，做网页自动化、数据采集、需要登录态的操作时特别好用。

使用真实 Chrome
保留 Cookie 与登录状态
自动化网页操作
仓库：
https://github.com/Lum1104/dsh-browser

安装：dsh plugin --profile web add
github:Lum1104/dsh-browser（含 Chrome 扩展，需手动加载）

## 8. dsh_workflow ⭐49
多 Agent 工作流神器：把一次性调度升级为可治理的 Workflow 层

官方的一次性调度干完就完，这个插件把多 Agent 协作变成可保存、可审计、可复用的工程资产：一键存成 workflow，运行记录、成本、权限全留痕，中断后还能按快照续跑。

Agent 编排
执行记录
成本统计
中断恢复
权限控制
仓库：
https://github.com/omdsh-dev/dsh_workflow

安装：dsh plugin --profile web add
github:omdsh-dev/dsh_workflow

## 9. dsh-chat-import ⭐14
聊天记录迁移神器，换工具不丢上下文

把 Claude Code、Codex、ChatGPT、Cursor、Gemini 等 14+ 平台的聊天历史全保真导入 DSH，导入后可以直接续聊，还能反向同步回去。正在从别的工具迁过来的人，先装这个。

Claude Code
ChatGPT
Cursor
Gemini
Codex（等 14+ 来源）
仓库：
https://github.com/Nwflower/dsh-chat-import

安装：dsh plugin --profile web add
github:Nwflower/dsh-chat-import

## 10. dsh-find-plugin ⭐7
插件搜索助手：让 Agent 帮你找下一件该装的东西

插件越来越多，「找插件」本身也成了问题。这个插件让 Agent 按你的模糊需求（比如「我想要任务结束时微信通知我」）去 GitHub 搜带 dsh-plugin 标签的项目，返回按 Star 排序的候选，每个都带一句话说明和可执行安装命令。

插件搜索
分类查询
安装命令生成
仓库：
https://github.com/awesome-dsh-plugin/dsh-find-plugin

安装：dsh plugin --profile web add dsh-find-plugin

⭐ 推荐安装顺序
第一梯队（必装，立竿见影）
dsh-web-ui
DSH-better-sidebar
dsh-TUI（终端党）
第二梯队（生产力提升）
modlens
dsh-browser
dsh_workflow
第三梯队（探索玩法）
dsh-deep-whale
dsh-find-plugin