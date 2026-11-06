---
title: Hot Cache
updated: 2026-11-06
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-11-06] INGEST — 物理硬件域首批10来源（PCIe错误×2、SSD TRIM、网卡IRQ绑定、BMC、IPMI SOL、光模块、内存SPD/XMP、ECC、芯片功耗）→ 15新页面 + 4更新。manifest 928→938条目，last_ingest → 2026-11-06
- [2026-10-21] INGEST — Linux 内存/调度/零拷贝/devmem 增量8来源 → 6新页面 + 5更新
- [2026-08-03] INGEST — AI Agent 协议+平台增量：11新来源 → 7新页面+3更新

## Active Threads

- **新领域：物理硬件层**——此前wiki全部知识止步于软件栈（内核/虚拟化/AI infra），本批补上软件栈之下的物理世界：PCIe错误体系、SSD介质语义、中断亲和性、带外管理、光器件、内存硬件
- **掉盘=PCIe链路静默失败**：`concepts/pcie-error-aer-nvme-drive-loss` 的核心洞察——链路错误在Root Complex的AER里、不在盘的SMART里，"SMART全绿但掉盘"是分层日志的边界效应而非工具失灵 ^[inferred]
- **SMP IRQ Affinity 并入中断系统**：`concepts/linux-interrupt-system` 新增硬中断CPU亲和性一节（smp_affinity位掩码、RPS/RFS补单队列网卡、irqbalance经验法则），补上了软中断知识的物理层配对杠杆
- **IO栈打通到介质层**：`concepts/linux-io-stack` 新增L5硬件层小节——TRIM缝合"文件系统知道已删除、介质不知道"的信息断层；`skills/linux-io-debugging` 增加TRIM确认启用步骤
- **DFX工具矩阵加硬件层行**：`synthesis/linux-dfx-tool-landscape` 从六域扩展到含硬件层（lspci/setpci/nvme-cli/ipmitool），新综合页 `synthesis/hardware-layer-debugging-landscape` 提炼五条显形规律

## Key Takeaways

- **硬件问题显形的五条规律** ^[inferred]：静默失败链（每层只记自己层的错误）、信息断层下推（TRIM/IRQ affinity/SPD同属"上层知识显式传给下层"模式）、亲和性杠杆（局部性从调度器贯穿到中断控制器）、带外观察平面（BMC是perf在线/vmcore事后之外的第三平面）、功耗换时延（IPU降uncore、ASPM致掉盘、discard改定时——电源管理永远在重分配功耗-时延-稳定性三角）
- **诊断语法与软件栈同构**：用硬件寄存器说话（setpci↔devmem）、用时间戳对齐（AER vs dmesg↔perf时间窗）、用排除法定界（最小系统法↔二分法）
- **两篇PCIe文章高度重叠**（381行+37行）→ 合并蒸馏为一个summary（source_files双列），37行版贡献"高速公路"隐喻与错误演进路径
- **稀薄笔记折叠而非建页**：芯片功耗(280B)→synthesis功耗规律、ECC(792B)→内存硬件concept，manifest登记产出页面

## Flagged Contradictions

- **AER寄存器语义存疑** ^[ambiguous]：来源将setpci读的AER状态寄存器当"计数器"用，但按PCIe规范它是按错误类型的位标志——三页均已标注，dmesg为更可靠证据，待规范原文裁定
- **博客级可信度** ^[ambiguous]：本批8来源均为blog(0.55)，CE>50/h、PRS公式、"90%掉盘是链路问题"等数字均为作者单方声明，全部标 ^[ambiguous] 待人工复核
- **既有lint债务**（部分已处理）：5个2026-09-16建的Self learn页面（agent-paradigm-selection、agent-reliability-engineering、loop-engineering、helm-package-management、k8s-network-troubleshooting）漏入index——本次ingest已补齐索引条目并重算stats(concepts 82/skills 16/total_pages 166)；manifest顶层vault_path仍为过期旧路径——待用户决策
