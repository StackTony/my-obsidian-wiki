## Harness Engineering 是什么？从上下文工程到驾驭工程

[社区首页](https://cloud.tencent.com/developer) > [专栏](https://cloud.tencent.com/developer/column) >Harness Engineering 是什么？从上下文工程到驾驭工程

## Harness Engineering 是什么？从上下文工程到驾驭工程

13.1K

举报

![](https://developer.qcloudimg.com/http-save/yehe-1628742/930d17da35c6cf0b6f755411c929bce1.jpg)

**Harness Engineering 驾驭工程** ：通过构建受控环境，让AI在约束下高效可靠地工作。

想象AI是一匹拥有神力的独角兽，它力量强大但难以预测。

驾驭工程不是去拔掉它的角，而是为它打造一套“黄金缰绳”和“水晶马车”。

**缰绳** （架构约束）引导它走正确的路， **马车** （上下文工程）提供舒适的承载空间， **车上的镜子** （反馈循环）随时照出它的状态，而 **车夫** （熵管理）则负责清理它奔跑时留下的杂乱痕迹。

这样，独角兽既保留了神力，又变得温顺可控。

## Harness Engineering 是什么？AI 时代的新杠杆

2026 年开年，开发者社区最热的关键词不是某个新模型，而是一个关于「环境」的词。

LangChain 的编码 Agent 在 Terminal Bench 2.0 基准测试上，通过仅优化 Agent 运行的外部环境（文档结构、验证回路、追踪系统）排名从全球第 30 位跃升至第 5 位， **得分从 52.8% 飙升至 66.5%** 。底层模型一个参数都没改。

这不是魔法，这是一个正在被正式命名的工程实践： **Harness Engineering** 。

### 谁第一次喊出了这个名字

2026 年 2 月 5 日，HashiCorp 联合创始人在他的博客文章中首次使用了「harness engineering」这个术语。这位传奇工程师，在经历了一段时间的 AI 辅助开发实践后，意识到一个关键问题： **当 Agent 犯错时，正确的回应不是换一个模型，而是重新设计它运行的环境。**

> *harness engineering is the idea that anytime you find an agent makes a mistake, you take the time to engineer a solution such that the agent will not make that mistake again in the future.*

这句话的潜台词是： **Agent 的每一次失败，都是环境设计不完善的信号** 。

六天后，OpenAI 发布了一份详细的实验报告，标题直接用了这个词。再之后，知名工程师 Martin Fowler 在 Twitter 上为 Thoughtworks 工程师对这份报告的深度分析站台。

一个月之内，Harness Engineering 从一篇博客文章变成了开发者社区的高频词。

### Harness 到底在做什么

根据 OpenAI 官方报告的描述，Harness 由三个核心类别组成：

**第一层：Context Engineering（上下文工程）** 。不仅仅是给 Agent 一份文档，而是持续增强的知识库，加上动态上下文——比如可观测性数据、浏览器导航状态。OpenAI 团队发现，传统的「一个巨大的 AGENTS.md 文件」方法注定失败：上下文是稀缺资源，过多的指导反而变得无效，那本「1000 页的说明书」会变成「陈旧规则的坟场」。

**第二层：Architectural Constraints（架构约束）** 。通过自定义格式和结构测试来强制执行规则，而不是让 Agent 随意发挥。OpenAI 要求 Codex 「在边界处解析数据形状」，但不规定具体实现方式。有开发者对此点评道：增加信任和可靠性需要约束解决方案空间：特定的架构模式、强制执行的边界、标准化的结构。这意味着放弃一些『生成任何东西』的灵活性。

**第三层：Garbage Collection（垃圾回收）** 。定期运行的 Agent，负责扫描不再反映真实代码行为的过时文档，发起修复 Pull Request。这对应了软件开发中的「技术债务」概念：与其让债务累积，不如持续小额偿还。

### 为什么 Prompt Engineering 不够用了

你可能还记得「vibe coding」的概念：YC 发布的指南强调「你主导决策，AI 负责执行」。这在当时刷新了很多人对 AI 编程的认知。

但问题在于：无论 Prompt 多精妙，如果 Agent 运行的「脚手架」不稳，一切都是空中楼阁。

Harness Engineering 代表的思维转变是：从「优化输入内容」到「优化系统环境」。

Prompt Engineering 关注的是「说什么」，Context Engineering 关注的是「给什么上下文」，而 Harness Engineering 关注的是「在什么条件下运行」。

这就像建筑工地上的脚手架：无论设计师的图纸多精美，如果没有稳固的脚手架，工人也爬不到高处。 **Harness 就是 AI Agent 的脚手架。**

OpenAI 团队花了 5 个月时间来构建和完善他们的 Harness。

这不是某种「快速见效」的技巧，而是一个需要持续投入的系统工程。

### 真正的杠杆在哪里

当所有人都在讨论「GPT-5.3 vs Opus」哪个模型更强时，Can Boluk 的实验给出了另一个答案。这位安全研究员仅仅改变了 Agent 的代码编辑格式：从传统的 patch 改为他设计的 **Hashline格式** 。Grok Code Fast 1 的基准得分就从 6.7% 跃升至 68.3%。

**Hashline 格式** ：文件内容会以类似 42:a3f| let x = compute(); 的形式呈现。这里的 42:a3f 就是哈希锚点，它由行号和内容哈希组成。

**一个格式的改变，等于十个模型升级。**

这揭示了一个核心事实：在 AI Agent 编码领域，决定结果好坏的最大变量，往往不是模型有多聪明，而是模型被放在了一个什么样的环境里。

OpenAI 在报告的结尾写道：

> *我们当前最棘手的挑战集中在设计环境、反馈回路和控制系统方面，帮助 Agent 实现我们的目标：大规模构建和维护复杂、可靠的软件。*

这句话值得反复品味。当模型的「能力竞赛」仍在继续，真正在一线决定 Agent 工程产出质量的杠杆，已经转移到了「环境」一侧。

---

### 致最先触达未来的那一小部分人

**Harness** Engineering 不是一个新概念：它是对一组已有实践的系统化命名。

但它的意义在于认知转变：当 AI 能写的代码越来越多，人类工程师的价值正在从「写代码」转向「设计系统」。

---

### 参考

\[1\] LangChain Terminal Bench 2.0 Results - blockchain.news.

\[2\] Mitchell Hashimoto - My AI Adoption Journey.

\[3\] Martin Fowler - Harness Engineering.

\[4\] OpenAI - Harness Engineering: leveraging Codex in an agent-first world.

\[5\] shadow的笔记.md - YC关于"Vibe Coding"的核心指南

\[6\] Can Boluk - I Improved 15 LLMs at Coding in One Afternoon. Only the Harness Changed.

本文参与 [腾讯云自媒体同步曝光计划](https://cloud.tencent.com/developer/support-plan) ，分享自微信公众号。

原始发表：2026-03-15，如有侵权请联系 [cloudcommunity@tencent.com](mailto:cloudcommunity@tencent.com) 删除

本文分享自 无界社区mixlab 微信公众号，前往查看

如有侵权，请联系 [cloudcommunity@tencent.com](mailto:cloudcommunity@tencent.com) 删除。

本文参与 [腾讯云自媒体同步曝光计划](https://cloud.tencent.com/developer/support-plan) ，欢迎热爱写作的你一起参与！

目录