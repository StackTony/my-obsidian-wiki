#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Manifest 更新：CRLF哈希刷新 + 删除清理 + 稀薄文件登记 + 高可信新条目"""
import json, hashlib, os, io, sys

TODAY = "2026-09-15"
manifest_path = 'wiki/.manifest.json'
m = json.load(io.open(manifest_path, encoding='utf-8'))

def sha(rel):
    return 'sha256:' + hashlib.sha256(open('raw/sources/' + rel, 'rb').read()).hexdigest()

def size(rel):
    return os.path.getsize('raw/sources/' + rel)

def mtime(rel):
    import datetime
    return datetime.datetime.fromtimestamp(os.path.getmtime('raw/sources/' + rel)).strftime('%Y-%m-%dT%H:%M')

# ============ 1. 删除清理 ============
removed = [
    'AI 人工智能/AI Agent/Agent智能体/入门级Agent 智能体.md',  # 无页面产出，直接移除
]
# _wiki_synthesis/agent-architecture-landscape: 页面仍存在(concepts/agent-architecture-landscape.md)，
# 它是 wiki_synthesis 类型记账条目，文件本身从未存在（0字节占位）——保留记账，不动
for r in removed:
    if r in m['sources']:
        del m['sources'][r]
        print(f"REMOVED: {r}")

# ============ 2. CRLF 哈希刷新（50个行尾-only文件） ============
crlf_files = [
"AI 人工智能/AI Agent/Multi-Agent协同/GitHub 上 10 个令人惊艳的 Agent 开发平台.md",
"AI 人工智能/AI Agent/Skills/开源skills库.md",
"AI 人工智能/AI Agent/各种协议/A2A/A2A协议.md",
"AI 人工智能/AI Agent/各种协议/深度解析三大AI协议：MCP、ACP与A2A.md",
"DFX工具/==网络==/内核网络Bonding调试日志.md",
"Linux 操作系统/Linux 内存管理/Linux meminfo参数详细解释.md",
"Linux 操作系统/Linux 内存管理/Linux 页缓存（Page Cache）.md",
"Linux 操作系统/Linux 网络/Linux TCP - IP协议.md",
"Linux 操作系统/Linux 网络/Linux 常见的网络协议.md",
"Linux 操作系统/Linux 网络/Linux 网络三张表：ARP表, MAC表, 路由表.md",
"Linux 操作系统/Linux 网络/Linux 网络协议栈.md",
"Linux 操作系统/Linux 资源隔离/Linux Namespace与Cgroups介绍.md",
"Linux 操作系统/Linux 资源隔离/System V IPC/Linux Namespace  -  IPC.md",
"Linux 操作系统/Linux 资源隔离/System V IPC/System V IPC 之信号量.md",
"Linux 操作系统/Linux 资源隔离/System V IPC/System V IPC 之共享内存.md",
"Linux 操作系统/Linux 资源隔离/System V IPC/System V IPC 之消息队列.md",
"Linux 操作系统/Linux 进程调度/Linux 进程调度器.md",
"Linux 操作系统/Linux 进程调度/Linux 进程调度策略.md",
"Linux 虚拟化/IO虚拟化/1）设备初始化流程.md",
"Linux 虚拟化/libvirt/virsh 常用命令汇总表.md",
"Linux 虚拟化/热迁移/热迁移流程.md",
"云原生/Kubernetes（K8s）/1-K8s 核心术语速查表.md",
"云原生/Kubernetes（K8s）/K8s云原生-官方文档-K8s架构.md",
"云原生/Kubernetes（K8s）/K8s云原生-阿里云-K8S技术原理.md",
"云原生/Kubernetes（K8s）/K8s安全加固完全指南.md",
"云原生/Kubernetes（K8s）/Kubernetes网络/K8s网络整体架构-腾讯云.md",
"云原生/Kubernetes（K8s）/Kubernetes（K8s）全面解析：核心概念、架构与实践.md",
"云原生/容器运行时/从零造容器系列/【从零造容器】1 Linux Namespaces：用 50 行 C 隔离一个进程.md",
"云原生/容器运行时/从零造容器系列/【从零造容器】10 容器 vs microVM：Firecracker 凭什么 125ms 启动.md",
"云原生/容器运行时/从零造容器系列/【从零造容器】11 容器网络性能真相：veth vs macvlan vs eBPF 数据面.md",
"云原生/容器运行时/从零造容器系列/【从零造容器】12 runc 源码考古：OCI 参考实现到底长什么样.md",
"云原生/容器运行时/从零造容器系列/【从零造容器】2 Network Namespace：给你的进程接上虚拟网线.md",
"云原生/容器运行时/从零造容器系列/【从零造容器】3 Mount Namespace 与 pivot_root：构建容器文件系统.md",
"云原生/容器运行时/从零造容器系列/【从零造容器】4 Cgroups v2：让容器不能吃掉整台机器.md",
"云原生/容器运行时/从零造容器系列/【从零造容器】5 OverlayFS：一层一层像洋葱.md",
"云原生/容器运行时/从零造容器系列/【从零造容器】6 用 Go 组装迷你容器运行时：把积木拼起来.md",
"云原生/容器运行时/从零造容器系列/【从零造容器】7 OCI 规范兼容：让迷你运行时说标准语言.md",
"云原生/容器运行时/从零造容器系列/【从零造容器】8 Seccomp-BPF 与 Capabilities：容器安全的两道防线.md",
"云原生/容器运行时/从零造容器系列/【从零造容器】9 User Namespace 与 Rootless 容器：不需要 root 也能跑.md",
"云原生/容器运行时/从零造容器系列/从零造容器系列文章.md",
"云原生/容器运行时/容器运行时 containerd.md",
"数据结构与算法/图/图 合集.md",
"数据结构与算法/树/红黑树讲解.md",
"消息队列/Kafka 设计架构原理详细解析（超详细图解）.md",
"消息队列/三大MQ选型对比-博客园.md",
"消息队列/零拷贝与内存映射-数据搬运极致优化.md",
"软件工程/设计原则.md",
"软件工程/设计框架.md",
"软件工程/设计模式.md",
"Linux 操作系统/Linux 内核 IO 栈/Linux IO调度算法.md",
]
for rel in crlf_files:
    e = m['sources'].get(rel)
    if e:
        e['content_hash'] = sha(rel)
        e['size_bytes'] = size(rel)
        e['modified_at'] = mtime(rel)
crlf_count = len(crlf_files)
print(f"CRLF refreshed: {crlf_count}")

# ============ 3. 真实修改的文件 ============
# Linux IO全景介绍：新增IO阻塞调试段(hctx busy)
rel = "Linux 操作系统/Linux 内核 IO 栈/Linux IO全景介绍.md"
e = m['sources'][rel]
e.update({
    'ingested_at': TODAY, 'size_bytes': size(rel), 'modified_at': mtime(rel),
    'content_hash': sha(rel),
    'pages_updated': sorted(set(e.get('pages_updated', []) + [
        'concepts/linux-io-stack.md', 'skills/linux-io-debugging.md'])),
})
print(f"MODIFIED re-ingested: {rel}")

# 多 Agent 协作 github项目示例：新增 tutti 链接（稀薄文件，仍登记 sparse 但页面已引用）
rel = "AI 人工智能/AI Agent/Multi-Agent协同/多 Agent 协作 github项目示例.md"
m['sources'][rel] = {
    'ingested_at': TODAY, 'size_bytes': size(rel), 'modified_at': mtime(rel),
    'content_hash': sha(rel), 'source_type': 'sparse', 'project': None,
    'pages_created': [], 'pages_updated': ['concepts/multi-agent-orchestration.md'],
    'note': '仅含2个GitHub项目链接(clowder-ai/tutti)，作为参考项目示例记入multi-agent-orchestration'
}
print(f"UPDATED sparse: {rel}")

# ============ 4. 新增：高可信来源 ============
new_entries = {
    # Linux 文件系统 mount（新子领域）
    "Linux 操作系统/Linux 文件系统/Linux内核—文件系统mount过程.md": {
        'source_type': 'document', 'project': None,
        'pages_created': ['concepts/linux-fs-mount.md', 'summaries/linux-fs-mount-process.md'],
        'pages_updated': ['concepts/linux-os-virtualization-landscape.md'],
    },
    # DSH 插件生态
    "AI 人工智能/AI Agent/Deepseek Harness/DSH几个插件推荐.md": {
        'source_type': 'document', 'project': None,
        'pages_created': ['entities/dsh-plugin-ecosystem.md'],
        'pages_updated': ['concepts/agent-architecture-landscape.md'],
    },
}
for rel, extra in new_entries.items():
    m['sources'][rel] = {
        'ingested_at': TODAY, 'size_bytes': size(rel), 'modified_at': mtime(rel),
        'content_hash': sha(rel), **extra,
    }
    print(f"ADDED: {rel}")

# ============ 5. 新增：Obsidian使用 目录 ============
obsidian_entries = {
    "Obsidian使用/Karpathy LLM Wiki/Karpathy wiki方法论.md": {
        'source_type': 'document',
        'pages_created': ['concepts/llm-wiki-methodology.md'],
        'pages_updated': [],
    },
    "Obsidian使用/Karpathy LLM Wiki/Obsidian-Wiki：LLM Wiki 的工程化实践.md": {
        'source_type': 'sparse',  # 仅118字节：安装教程+github链接
        'pages_created': [], 'pages_updated': ['concepts/llm-wiki-methodology.md'],
        'note': '仅含安装教程链接和github仓库地址，方法论细节已在llm-wiki-methodology引用',
    },
    "Obsidian使用/Karpathy LLM Wiki/参考的CLAUDE.md文件.md": {
        'source_type': 'document',
        'pages_created': [],
        'pages_updated': ['concepts/llm-wiki-methodology.md'],
    },
    "Obsidian使用/Karpathy LLM Wiki/期望目标：构建个人的Karpathy LLM Wiki + Obsidian + Claude知识系统.md": {
        'source_type': 'document',
        'pages_created': [],
        'pages_updated': ['concepts/llm-wiki-methodology.md'],
    },
    "Obsidian使用/Skill和MCP/obsidian相关skill和mcp.md": {
        'source_type': 'document',
        'pages_created': ['concepts/obsidian-ai-toolchain.md'],
        'pages_updated': [],
    },
    "Obsidian使用/备份示例文件/Day learn 示例.md": {
        'source_type': 'document',
        'pages_created': [],
        'pages_updated': ['concepts/obsidian-ai-toolchain.md'],
    },
    "Obsidian使用/插件/Claude Code 安装.md": {
        'source_type': 'sparse',  # 251字节：npm二进制路径说明
        'pages_created': [], 'pages_updated': ['concepts/obsidian-ai-toolchain.md'],
        'note': '安装路径速记，并入obsidian-ai-toolchain',
    },
    "Obsidian使用/插件/Claudian 插件.md": {
        'source_type': 'sparse',  # 544字节：github链接+功能列表+API配置
        'pages_created': [], 'pages_updated': ['concepts/obsidian-ai-toolchain.md'],
        'note': '插件安装与功能列表，并入obsidian-ai-toolchain',
    },
    "Obsidian使用/插件/OpenCode 插件.md": {
        'source_type': 'sparse',  # 59字节：github链接
        'pages_created': [], 'pages_updated': ['concepts/obsidian-ai-toolchain.md'],
        'note': '仅含github链接，并入obsidian-ai-toolchain',
    },
    "Obsidian使用/插件/插件记录.md": {
        'source_type': 'document',
        'pages_created': [],
        'pages_updated': ['concepts/obsidian-ai-toolchain.md', 'concepts/agent-architecture-landscape.md'],
    },
    "Linux 操作系统/Linux 文件系统/未命名.md": {
        'source_type': 'sparse',
        'pages_created': [], 'pages_updated': [],
        'note': '仅含知乎链接(zhuanlan.zhihu.com/p/606596107)，该链接正是Linux内核mount过程一文的原文——疑似收藏占位',
    },
    "AI 人工智能/AI Agent/Skills/开源skills库.md": {
        # 已在manifest但哈希刷新过——检查是否已存在
    },
}
for rel, extra in obsidian_entries.items():
    if not extra:
        continue
    if rel in m['sources']:
        e = m['sources'][rel]
        e.update({
            'ingested_at': TODAY, 'size_bytes': size(rel), 'modified_at': mtime(rel),
            'content_hash': sha(rel),
            'pages_updated': sorted(set(e.get('pages_updated', []) + extra.get('pages_updated', []))),
        })
        print(f"REFRESHED: {rel}")
    else:
        m['sources'][rel] = {
            'ingested_at': TODAY, 'size_bytes': size(rel), 'modified_at': mtime(rel),
            'content_hash': sha(rel), **extra,
        }
        print(f"ADDED: {rel}")

json.dump(m, io.open(manifest_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"\nTotal sources: {len(m['sources'])}")
print("DONE")
