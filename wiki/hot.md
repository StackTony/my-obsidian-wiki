---
title: Hot Cache
updated: 2026-11-09
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-11-09] WIKI_UPDATE — vault 自身首次作为项目同步：新建 [[projects/my-obsidian-wiki]] 项目枢纽页（架构决策索引+运营模式+待办债务）；manifest 新增 projects 节（last_commit_synced=1565714）；total_pages 169
- [2026-11-09] INGEST — Linux中断系统目录完整重蒸馏（2新增来源：中断分类表/中断所有知识点 + 4修改来源，其中3个被用户重命名）→ 2新页面（linux-interrupt-classification、linux-interrupt-lifecycle）+ hub与softirq-detail重蒸馏。manifest 938→940，total_pages 166→168
- [2026-11-09] MAINTAIN — raw侧：吐血整理文dedup（复制粘贴事故，删96行重复）后用户重命名为"Linux中断所有知识点.md"；中断分类表新增英文全称列（用户手工增强）
- [2026-11-06] INGEST — 物理硬件域首批10来源（PCIe错误、SSD TRIM、网卡IRQ绑定、BMC/IPMI、光模块、SPD/ECC等）→ 15新页面 + 4更新

## Active Threads

- **下一批待消化**：git 暂存区已备好"Linux 内存管理"来源（CPU Cache 一致性新增、内存屏障、TLB 改名），是下次 /wiki-ingest 的输入
- **vault 元枢纽建立**：[[projects/my-obsidian-wiki]] 记录了 vault 作为项目的架构决策索引与运营模式（重叠合并/稀薄折叠/backup 流/skill 外置），manifest 开始跟踪 projects 节
- **中断知识线闭环** ^[inferred]：中断分类表（四维框架）+ 中断所有知识点（GIC硬件→irq_domain→注册→ARM64处理全链路）+ softirq三件套（原理/实现/内核线程）已全部蒸馏完毕，hub `concepts/linux-interrupt-system` 成为中断域唯一枢纽；与 `concepts/linux-interrupt-virtualization`（VGIC）、`summaries/nic-smp-irq-affinity`（硬件侧亲和）、`summaries/linux-tlb-management`（IPI用例TLB Shootdown）完成交叉链接
- **"软中断"歧义是最大混淆点**：指令级软中断（INT n/SVC=同步Trap）、广义软件中断（=异常Exception）、Linux Softirq（下半部机制）三重含义——分类页与hub均已建立澄清
- **此前活跃**：物理硬件层（PCIe错误体系、掉盘=链路静默失败、带外管理BMC）；IO栈L5硬件层（TRIM）；DFX工具矩阵硬件层行

## Key Takeaways

- **中断分类四维度正交** ^[inferred]：同步/异步（触发时机，最本质主轴）× 软/硬（通俗叫法）× 上/下半部（处理阶段）× 功能/用途（I/O、定时器等叫法）；功能标签与机制类别不在同一层级——"网卡中断"的机制实现是MSI-X，跨层混比产生"谁包含谁"类无意义问题
- **MSI/MSI-X与LPI是两层不是两种**：MSI/MSI-X是设备侧发出形式（PCIe总线协议层），LPI是GICv3+侧接收类型（ITS翻译后经Redistributor投递）；x86上同样的MSI写直接落入Local APIC，无LPI中间层
- **SGI归类澄清**：软件发起但经GIC异步投递→归异步硬件中断，非指令级软中断；ARM的IPI功能由SGI实现（实现×功能对应）
- **GIC三组件分工**：Distributor管SPI（全局）、Redistributor管每核SGI/PPI/LPI、CPU interface管应答与投递；多控制器hwirq重复→irq_domain映射为virq
- **workqueue五元组**：work→workqueue→pool_workqueue(中介)→worker_pool(bound型每CPU两个，nice 0/-20)→worker(kworker线程)；进程上下文可睡眠是与softirq/tasklet的本质差异
- **softirq执行借用被中断任务上下文**（代码mask/unmask PF_MEMALLOC佐证）；预算超限三条件判断（时间/need_resched/重启次数）→ksoftirqd兜底

## Flagged Contradictions

- **softirq计数9 vs 10** ^[ambiguous]：源文档正文一处写"内置的9种softirq"但其贴出的5.10 enum为10项（NR_SOFTIRQS=10）——hub已修正为10种并标注，以enum为准
- **中断所有知识点为知乎blog级可信度**(0.55)：GIC结构体字段级细节、GICD_PIDR2版本编码等未对照内核源码复核，lifecycle=draft；中断分类表为用户协同整理并人工审核（按documentation 0.85计，base_confidence 0.6）
- **历史遗留**：5个2026-09-16建的Self learn页面已补入index（2026-11-06处理）；manifest顶层vault_path仍为过期旧路径——待用户决策
