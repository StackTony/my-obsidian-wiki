· 阅读需 12 分钟

大多数运行 AI 编程智能体（AI coding agents）的团队都在优化错误的变量。他们过度痴迷于模型选择 —— Claude vs. GPT vs. Gemini —— 却将周围的脚手架视为次要的配套工作。但基准测试数据和生产环境的实战经验告诉我们一个不同的故事：一个在演示中令人惊叹的模型与一个能够可靠交付生产代码的模型之间的差距，几乎完全取决于其周围的控制环（harness），而不是模型本身。

这个公式看似简单： **智能体 = 模型 + 控制环 (Harness)** 。控制环是除此之外的一切 —— 工具 schema、权限模型、上下文生命周期管理、反馈循环、沙箱环境、文档基础设施、架构不变性。如果控制环搞错了，即使是最前沿的模型也会生成虚构的文件路径，在会话进行到 20 轮时破坏自身的约定，甚至在没写任何测试之前就宣称功能已完成。

控制环优先地位最清晰的证据来自 SWE-bench，这是编程智能体的标准基准测试。同一个模型根据包裹它的脚手架不同，得分差异巨大 —— 在完全相同的底层模型上，不同控制环实现的得分差距可达 20–30 个百分点。SWE-bench 不仅仅是在测试模型；它同时也在评估控制环。将模型选择视为主要可靠性变量的团队正在衡量错误的东西。

## 指南与传感器：核心分类法

思考控制环设计最有效的框架是区分两种根本不同的控制类型。

**指南 (Guides)** 是前馈的 —— 它们在智能体行动之前对其进行引导。 `AGENTS.md` 文件就是一个指南。仓库中的架构文档是一个指南。在智能体执行第一个动作之前初始化其工作上下文的启动脚本也是一个指南。指南编码了“什么是好的实践”，主动防止错误的输出，并注入模型权重中不包含的项目特定知识。

**传感器 (Sensors)** 是反馈 —— 它们观察智能体的行为并生成修正信号。TypeScript 的类型检查器是一个传感器。ESLint 是一个传感器。Playwright 端到端测试套件是一个传感器。标记语义问题的 AI 代码审查器也是一个传感器。传感器允许智能体在单个会话内进行自我修正，而不是在每一步都需要人工干预。

传感器进一步按类型划分。计算型传感器 —— 如类型检查器、格式化器、结构化 Linter —— 是确定性的，运行速度以毫秒计，并提供二元的通过/失败反馈。推断型传感器 —— 如评估代码是否真正符合意图的 AI 审查器 —— 是概率性的，速度较慢，并能捕捉到结构化工具完全遗漏的含义层面错误。一个成熟的控制环会同时使用这两者。

实际情况是，大多数团队拥有的是“偶然形成的控制环”，而不是“设计出的控制环”。他们有一些 TypeScript 脚本，可能还有一个 Linter。他们添加了 `CLAUDE.md` 或 `AGENTS.md` 文件。但他们没有问：智能体在开始之前需要知道什么？每项操作后存在哪些反馈循环？当这些循环检测到失败时会发生什么？这些问题的答案 —— 而不是模型 —— 决定了生产环境的可靠性。

## 你的代码库现在是一个通信协议

当智能体进行主要的代码生成时，一些根本性的东西发生了变化：代码仓库本身成为了人类工程师与他们授权的智能体之间主要的通信渠道。任何存在于某人脑海中、Confluence、Notion 文档或隐性知识中的架构决策，都会在控制环中留下漏洞。

一个 Codex 团队在五个月内由三名工程师生成了大约 1,500 个拉取请求（PR），构建了一个百万行级别的生产代码库 —— 平均每位工程师每天处理约 3.5 个 PR，且没有手动编写的源代码。其中最重要的设计决策是：首先为智能体的可读性（legibility）优化仓库。这不是传统意义上的人类可读性，而是零上下文的智能体有效运作所需的东西。

具体而言，这意味着：

- 所有架构决策必须存在于仓库中，且是机器可读的，而不是散落在外部文档系统中
- 通过在 CI 中运行的结构化测试强制执行严格的依赖分层 —— 不是记录在某个 wiki 中，而是通过机械手段强制执行
- 通过 Linter 验证交叉链接的文档，以便在代码更改时引用不会失效
- 每个会话都会加载 `AGENTS.md` 或 `CLAUDE.md` 文件，其中包含技术栈、构建/测试命令和架构约束

最后一点值得强调。研究比较人工编写与 LLM 生成的 `AGENTS.md` 文件的发现了一个惊人的不对称性：LLM 生成的文件实际上会损害智能体的性能，而人工编写的文件在智能体基准测试中能带来约 4 个百分点的提升。那个加载到每个智能体会话并塑造后续每个决策的文件，应该由人类精心维护，而不是自动生成。

## 不变量胜过微观管理

一个来自大规模运行 Agent 团队的直觉反差经验：试图通过 Prompt 中冗长的指令来控制 Agent 行为是无法扩展的。指令变得越来越长，Agent 开始忽略末尾的指令，规则与执行的比例也持续恶化。

更持久的方法是 **强制执行不变量** ，而不是描述偏好。当架构边界违规或格式不一致导致 CI（持续集成）失败，而不是仅仅出现在风格指南中时，Agent 就不需要记住规则——它会收到一个信号。这与类型系统比代码审查评论在强制执行契约方面更有效的原理相同。

一个有效的模式是：将架构编码为在 CI 中运行的结构适应度函数（structural fitness functions）。如果你有一个严格的分层规则——比如服务层代码不能从运行时层导入——那就写一个测试来强制执行它。Agent 不需要理解架构背后的推理；它只需要在 PR 合并之前通过测试。不变量是自我强制执行的。

这使人类工程师的主要工作从编写代码转变为编写验收标准。指定“完成”是什么样子的——用传感器可以评估的术语来表达——比生成实现更具杠杆作用。模糊的 Prompt 会产生幻觉出的文件路径和对错误模块的修改。一个指定了应更改哪些文件、验收标准是什么以及应通过哪些测试的结构化任务，足以约束解空间，从而使输出变得可预测。

## 自我评估问题

任何要求生成 Agent 对其自身输出进行判断的框架，都会得到只有自信而没有准确性的结果。这并非某种微妙的失败模式——而是一种系统性偏差。模型总是持续高估它们刚刚产出的代码质量，且随着 Session 变长，以及 Agent 在特定方法上投入更多，这种过度自信会产生复合效应。

架构上的对策是将生成器与评估器分离。Anthropic 用于长期运行 Agent 的框架明确地做到了这一点：规划器（planner）将 Prompt 扩展为详细的规范，生成器（generator）实现功能，而独立的评估器（evaluator）根据定义的标准进行测试——使用 Playwright 进行浏览器交互，并针对设计质量、原创性、工艺和功能进行评分。评估器和生成器还会在实现开始前协商 Sprint 合约，在编写任何代码之前就一段工作的“完成”标准达成一致。

生成器-评估器分离还有第二个好处：它使评估标准显式化且可检查。当评估器是一个拥有定义评分标准的独立 Agent 时，人类可以审查并调整衡量的内容。当它是同一个 Agent 进行自我评估时，评分标准是不可见的，且总是盲目乐观。

## 上下文窗口是无状态的轮班工人

长期运行 Agent 最常见的失败类别不是代码错误——而是上下文管理失败。在经过足够的轮次后，Agent 会忘记早期的约束。它们会重新实现二十步之前写过的函数。它们会失去当前功能目标的思路。它们开始自信地做一些与 Session 开始时的决策相矛盾的事情。

上下文腐化是架构性的，而非偶然的。随着 Token 数量的增加，准确性会下降——注意力机制对早期上下文的有效召回会降低，系统 Prompt 中给出的指令开始与不断增加的观察结果和工具输出产生竞争。从某种意义上说，Agent 框架的每个组件都是对这一约束的回应。

有效的框架在多个层面解决上下文管理问题：

- **初始化脚本** ：在每个 Session 开始时恢复项目状态，无论之前的 Session 发生了什么。
- **持久化进度文件** ：通常采用 JSON 而非 Markdown 格式（因为模型不太可能不当地编辑结构化数据），用于跨上下文边界携带任务状态。
- **影子 Git 快照** ：在每次文件更改时生成，当一长串操作需要部分回滚时，可以实现每一步的回退。
- **事件驱动的提醒** ：在决策点注入，而不是预先加载到冗长的系统 Prompt 中——这既能对抗指令淡忘，又不会进一步撑大上下文。
- **带有结构化移交的上下文重置** ：对于运行时间极长的任务，将 Agent 积累的观察结果进行总结，并开始一个新的上下文。

一个运行拥有 200 多个功能条目 Agent 的团队将功能列表存储为 JSON 而非 Markdown，正是因为模型对结构化数据格式进行不当编辑的可能性低于对散文体。这就是实践中框架工程的细粒度。

## 沙箱是基础设施，而非安全演戏

在大规模应用中，执行沙箱是不可或缺的。研究表明，在根据既定标准进行测试时，40–62% 的 AI 生成代码包含安全漏洞。但使用沙箱的主要原因并非为了捕捉恶意输出——而是为了提升速度。能够在隔离环境中运行代码并观察效果的 Agent，比仅依赖静态分析的 Agent 迭代得更快、更准确。

正在兴起的基础设施模式是：在亚秒级内配置临时环境，其范围仅限于修改的工作负载而非整个集群，并在任务完成或失败时自动销毁。人类审阅者会获得一个沙箱链接以立即与运行中的代码交互——无需本地设置，在审阅和生产环境之间没有环境差异。

对于 Agent 的准确性而言，E2E（端到端）测试的访问权限比单元测试更重要。配备了 Playwright 或 Puppeteer 的 Agent 可以像“人类用户一样”验证行为——这是一个比单元测试强得多的信号，因为单元测试很容易写成虽然通过了但功能却是坏的。这与 Agent 的能力无关，而与反馈循环的质量有关。更好的传感器能产生更准确的 Agent。

## Harness 工程究竟改变了什么

做得出色的团队已经实现了几个实际的转变：

他们不再将 AGENTS.md 视为文档，而是将其视为工程基础设施——进行版本化、评审，并针对实际的 Agent 性能进行测试。他们维护它的方式与维护其他 CI 配置的方式完全相同。

他们将质量检查“左移”，将其分布在 pre-commit（快速 linter）、PR 集成（类型检查、架构适应性函数）以及持续监控（漂移检测）中。对于高速生成的 Agent 代码，传统的 CI 流水线速度太慢了。

他们接受了这样一个事实：Harness 的每个组件都隐含了一个关于“当前模型无法独立可靠地完成什么”的假设——并且随着模型的改进，他们会重新审视这些假设。六个月前必不可少的脚手架，现在可能只会增加开销而没有价值。

最重要的是，他们不再询问“哪个模型最好”，而是开始询问“Harness 需要什么才能可靠地产生我们所需的输出？”模型只是一个组件，Harness 才是产品。

那些将 Agent 部署视为模型选择问题的团队，将不断被生产环境中的故障所震惊——这些故障往往发生在会话开始三小时后，此时模型已经偏离了会话开始时指定的约束。而那些构建 Harness 的团队正在持续交付。

**References:**
- [https://martinfowler.com/articles/harness-engineering.html](https://martinfowler.com/articles/harness-engineering.html)
- [https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [https://arxiv.org/html/2603.05344v1](https://arxiv.org/html/2603.05344v1)
- [https://developers.redhat.com/articles/2026/04/07/harness-engineering-structured-workflows-ai-assisted-development](https://developers.redhat.com/articles/2026/04/07/harness-engineering-structured-workflows-ai-assisted-development)
- [https://www.infoq.com/news/2026/02/openai-harness-engineering-codex/](https://www.infoq.com/news/2026/02/openai-harness-engineering-codex/)
- [https://www.infoq.com/news/2026/04/anthropic-three-agent-harness-ai/](https://www.infoq.com/news/2026/04/anthropic-three-agent-harness-ai/)
- [https://newsletter.eng-leadership.com/p/how-openais-codex-team-works-and](https://newsletter.eng-leadership.com/p/how-openais-codex-team-works-and)
- [https://new.signadot.com/blog/your-infrastructure-isnt-ready-for-agentic-development-at-scale](https://new.signadot.com/blog/your-infrastructure-isnt-ready-for-agentic-development-at-scale)
- [https://arxiv.org/html/2511.09268v1](https://arxiv.org/html/2511.09268v1)
- [https://www.latent.space/p/anita-tdd](https://www.latent.space/p/anita-tdd)
- [https://www.swebench.com/](https://www.swebench.com/)
- [https://github.com/microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit)
**Let's stay in touch and Follow me for more thoughts and updates**