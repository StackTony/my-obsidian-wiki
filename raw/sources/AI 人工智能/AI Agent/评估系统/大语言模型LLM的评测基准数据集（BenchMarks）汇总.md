原文： https://blog.csdn.net/qq_36803941/article/details/140045494
#### 文章目录

- [0. 引言](#0__3)
- [1. 知识与语言理解](#1__5)
- - [1.1 MMLU](#11_MMLU_6)
    - [1.2 ARC](#12_ARC_15)
    - [1.3 GLUE](#13_GLUE_25)
    - [1.4 Natural Questions](#14_Natural_Questions_34)
    - [1.5 LAMBADA](#15_LAMBADA_43)
    - [1.5 HellaSwag](#15_HellaSwag_51)
    - [1.6 MultiNLI](#16_MultiNLI_59)
    - [1.7 SuperGLUE](#17_SuperGLUE_68)
    - [1.8 TriviaQA](#18_TriviaQA_76)
    - [1.9 WinoGrande](#19_WinoGrande_85)
    - [1.10 SciQ](#110_SciQ_94)
- [2. 推理能力](#2__102)
- - [2.1 GSM8K](#21_GSM8K_103)
    - [2.2 DROP](#22_DROP_111)
    - [2.3 CRASS](#23_CRASS_119)
    - [2.4 RACE](#24_RACE_127)
    - [2.5 BBH](#25_BBH_135)
    - [2.6 AGIEval](#26_AGIEval_144)
    - [2.7 BoolQ](#27_BoolQ_154)
- [3. 多轮开放式对话](#3__162)
- - [3.1 MT-bench](#31_MTbench_163)
    - [3.2 QuAC](#32_QuAC_171)
- [3. 综述抽取与生成能力](#3__179)
- - [3.1 ACI-BENCH](#31_ACIBENCH_180)
    - [3.2 MS-MARCO](#32_MSMARCO_188)
    - [3.3 QMSum](#33_QMSum_196)
    - [3.4 PIQA](#34_PIQA_204)
- [4. 内容审核和叙事控制](#4__212)
- - [4.1 ToxiGen](#41_ToxiGen_213)
    - [4.2 HHH](#42_HHH_222)
    - [4.3 TruthfulQA](#43_TruthfulQA_234)
    - [4.4 RAI](#44_RAI_241)
- [5. 编程能力](#5__247)
- - [5.1 CodeXGLUE](#51_CodeXGLUE_248)
    - [5.2 HumanEval](#52_HumanEval_256)
    - [5.3 MBPP](#53_MBPP_264)
- [6. 参考](#6__272)

---

## 0. 引言

本文列出 llm 常见的一些 BenchMarks（评测基准）数据集，总有一款适合你！有用的话欢迎关注～

## 1. 知识与语言理解

### 1.1 MMLU

Massive Multitask Language Understanding，评测 57个不同学科的通用知识。

- **目的：** 评估 LLM 在广泛主题领域的理解和推理能力。
- **相关：** 非常适合需要广泛的世界知识和解决问题能力的多方面人工智能系统。
- **原文：**[《Measuring Massive Multitask Language Understanding》](https://arxiv.org/abs/2009.03300)
- **资源：**
    - [MMLU GitHub](https://github.com/hendrycks/test)
    - [MMLU Dataset](https://people.eecs.berkeley.edu/~hendrycks/data.tar)

### 1.2 ARC

AI2 Reasoning Challenge，测试小学科学问题的LLM，要求具备深厚的一般知识和 推理能力 。

- **目的：** 评估回答需要逻辑推理的复杂科学问题的能力。
- **相关：** 适用于教育人工智能应用程序、自动化辅导系统和一般知识评估。
- **原文：**[《Think you have Solved Question Answering? Try ARC, the AI2 Reasoning Challenge》](https://arxiv.org/abs/1803.05457)
- **资源：**
    - [ARC Dataset: HuggingFace](https://huggingface.co/datasets/ai2_arc)
    - [ARC Dataset: Allen Institute](https://allenai.org/data/arc)

### 1.3 GLUE

General Language Understanding Evaluation，来自多个数据集的各种语言任务的集合，旨在衡量整体语言理解能力。

- **目的：** 对不同语境下的语言理解能力进行全面评估。
- **相关：** 对于需要高级语言处理的应用程序（如聊天机器人和内容分析）至关重要。
- **原文：**[《GLUE: A Multi-Task Benchmark and Analysis Platform for Natural Language Understanding》](https://arxiv.org/abs/1804.07461)
- **资源：**
    - [GLUE Homepage](https://gluebenchmark.com/)
    - [GLUE Dataset](https://huggingface.co/datasets/glue)

### 1.4 Natural Questions

收集人们在谷歌上搜索的现实世界问题，与相关的维基百科页面配对以提取答案。

- **目的：** 测试从网络资源中找到准确的长短答案的能力。
- **相关：** 对于搜索引擎、信息检索系统和人工智能驱动的问答工具至关重要。
- **原文：**[《Natural Questions: A Benchmark for Question Answering Research》](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00276/43518/Natural-Questions-A-Benchmark-for-Question)
- **资源：**
    - [Natural Questions Homepage](https://ai.google.com/research/NaturalQuestions)
    - [Natural Questions Dataset: Github](https://github.com/google-research-datasets/natural-questions)

### 1.5 LAMBADA

LAnguage Modelling Broadened to Account for Discourse Aspects，测试语言 模型 基于长上下文理解和预测文本的能力。

- **目的：** 评估模型对叙事的理解及其在文本生成中的预测能力。
- **相关：** 对于人工智能在叙事分析、内容创作和长篇文本理解方面的应用非常重要。
- **原文：**[《The LAMBADA Dataset: Word prediction requiring a broad discourse context》](https://arxiv.org/abs/1606.06031)
- **资源：**
    - [LAMBADA Dataset: HuggingFace](https://huggingface.co/datasets/lambada)

### 1.5 HellaSwag

通过要求 LLM 以需要理解复杂细节的方式完成段落来测试 自然语言推理 。

- **目的：** 评估模型生成符合上下文的文本延续的能力。
- **相关：** 在内容创建、对话系统和需要高级文本生成功能的应用程序中很有用。
- **原文：**[《HellaSwag: Can a Machine Really Finish Your Sentence?》](https://arxiv.org/abs/1905.07830)
- **资源：**
    - [HellaSwag Dataset: GitHub](https://github.com/rowanz/hellaswag/tree/master/data)

### 1.6 MultiNLI

Multi-Genre Natural Language Inference ，由 433K 个句子对组成的基准，涵盖各种英语数据的流派，测试自然语言推理。

- **目的：** 评估 LLM 根据陈述推理正确类别的能力。
- **相关：** 对于需要高级文本理解和推理的系统至关重要，如自动推理和文本分析工具。
- **原文：**[《A Broad-Coverage Challenge Corpus for Sentence Understanding through Inference》](https://arxiv.org/abs/1704.05426)
- **资源：**
    - [MultiNLI Homepage](https://cims.nyu.edu/~sbowman/multinli/)
    - [MultiNLI Dataset](https://huggingface.co/datasets/multi_nli)

### 1.7 SuperGLUE

GLUE 基准的高级版本，包含更具挑战性和多样性的语言任务。

- **目的：** 评估语言理解和推理的更深层次。
- **相关：** 对于需要高级语言处理能力的复杂人工智能系统非常重要。
- **原文：**[SuperGLUE: A Stickier Benchmark for General-Purpose Language Understanding Systems](https://arxiv.org/abs/1905.00537)
- **资源：**
    - [SuperGLUE Dataset: HuggingFace](https://huggingface.co/datasets/super_glue)

### 1.8 TriviaQA

阅读理解测试，包含来自 Wikipedia 的复杂文本中的问题，要求进行情境分析。

- **目的：** 评估在复杂文本中筛选上下文并找到准确答案的能力。
- **相关：** 适用于知识提取、研究和详细内容分析方面的人工智能系统。
- **原文：**[《TriviaQA: A Large Scale Distantly Supervised Challenge Dataset for Reading Comprehension》](https://arxiv.org/abs/1705.03551)
- **资源：**
    - [TriviaQA GitHub](https://github.com/mandarjoshi90/triviaqa)
    - [TriviaQa Dataset](https://huggingface.co/datasets/trivia_qa)

### 1.9 WinoGrande

基于 Winograd Schema Challenge 的大规模问题集，测试句子中的上下文理解情境。

- **目的：** 评估 LLM 掌握微妙上下文和文本细微变化的能力。
- **相关：** 对于处理叙事分析、内容个性化和高级文本解释的模型至关重要。
- **原文：**[《WinoGrande: An Adversarial Winograd Schema Challenge at Scale》](https://arxiv.org/abs/1907.10641)
- **资源：**
    - [WinoGrande GitHub](https://github.com/allenai/winogrande)
    - [WinoGrande Dataset: HuggingFace](https://huggingface.co/datasets/winogrande)

### 1.10 SciQ

主要包含物理、化学和生物学等自然科学的多项选择题。

- **目的：** 测试回答基于科学的问题的能力，通常需要额外的支持文本。
- **相关：** 适用于教育工具，尤其是在科学教育和知识测试平台中。
- **原文：**[《Crowdsourcing Multiple Choice Science Questions》](https://arxiv.org/abs/1707.06209)
- **资源：**
    - [SciQ Dataset: HuggingFace](https://huggingface.co/datasets/sciq)

## 2. 推理能力

### 2.1 GSM8K

包含 8.5K 个小学数学问题，需要基本到中级的数学运算。

- **目的：** 测试 LLM 解决多步数学问题的能力。
- **相关性：** 有助于评估人工智能解决基本数学问题的能力，在教育背景下很有价值。
- **原文：** [《Training Verifiers to Solve Math Word Problems》](https://arxiv.org/abs/2110.14168)
- **资源：**
    - [GSM8K Dataset](https://huggingface.co/datasets/gsm8k)

### 2.2 DROP

Discrete Reasoning Over Paragraphs，一个对抗性创建的阅读理解基准，要求模型浏览参考文献并执行添加或排序等操作。

- **目的：** 评估模型理解复杂文本和执行离散运算的能力。
- **相关：** 适用于需要逻辑推理的高级教育工具和文本分析系统。
- **原文：**[《DROP: A Reading Comprehension Benchmark Requiring Discrete Reasoning Over Paragraphs》](https://arxiv.org/abs/1903.00161)
- **资源：**
    - [DROP Dataset](https://huggingface.co/datasets/drop)

### 2.3 CRASS

Counterfactual Reasoning Assessment，评估 LLM 的反事实推理能力，重点关注“假设”场景。

- **目的：** 评估模型根据给定数据理解和推理备选场景的能力。
- **相关：** 对于人工智能在战略规划、决策和场景分析中的应用非常重要。
- **原文：**[《CRASS: A Novel Data Set and Benchmark to Test Counterfactual Reasoning of Large Language Models》](https://arxiv.org/abs/2112.11941)
- **资源：**
    - [CRASS Dataset](https://github.com/apergo-ai/CRASS-data-set/tree/main)

### 2.4 RACE

Large-scale ReAding Comprehension Dataset From Examinations，来自中国学生参加的英语考试的阅读理解问题集。

- **目的：** 测试 LLM 对复杂阅读材料的理解以及他们回答考试水平问题的能力。
- **相关：** 在语言学习应用程序和考试准备教育系统中很有用。
- **原文：**[《RACE: Large-scale ReAding Comprehension Dataset From Examinations》](https://arxiv.org/abs/1704.04683)
- **资源：**
    - [RAC Dataset](https://www.cs.cmu.edu/~glai1/data/race/)

### 2.5 BBH

Big-Bench Hard，BIG Bench的一个子集，专注于需要多步骤推理的最具挑战性的任务。

- **目的：** 用需要高级推理技能的复杂任务挑战 LLM。
- **相关：** 对于评估人工智能在复杂推理和解决问题方面的能力上限很重要。
- **原文：**[《Challenging BIG-Bench Tasks and Whether Chain-of-Thought Can Solve Them》](https://arxiv.org/abs/2210.09261)
- **资源：**
    - [BIG-Bench-Hard GitHub: Dataset and Prompts](https://github.com/suzgunmirac/BIG-Bench-Hard)
    - [BBH Dataset: HuggingFace](https://huggingface.co/datasets/lukaemon/bbh)

### 2.6 AGIEval

一系列 标准化 考试，包括 GRE、GMAT、SAT、LSAT 和公务员考试等标准化测试的集合。

- **目的：** 评估 LLM 在各种学术和专业场景中的推理能力和解决问题的技能。
- **相关：** 有助于在标准化测试和专业资格背景下评估人工智能能力。
- **原文：**[《AGIEval: A Human-Centric Benchmark for Evaluating Foundation Models》](https://arxiv.org/abs/2304.06364)
- **资源：**
    - [AGIEval Github: Dataset and Prompts](https://github.com/ruixiangcui/AGIEval/tree/main)
    - [AGIEval Datasets: HuggingFace](https://huggingface.co/datasets?search=AGIEval)

### 2.7 BoolQ

收集了来自谷歌搜索的15000多个真实的是/否问题，以及维基百科的文章。

- **目的：** 测试 LLM 从可能不明确的上下文信息中推断正确答案的能力。
- **相关：** 对于问答系统和基于知识的人工智能应用至关重要，准确的推理是关键。
- **原文：**[《BoolQ: Exploring the Surprising Difficulty of Natural Yes/No Questions》](https://arxiv.org/abs/1905.10044)
- **资源：**
    - [BoolQ Dataset: HuggingFace](https://huggingface.co/datasets/boolq)

## 3. 多轮开放式对话

### 3.1 MT-bench

专为评估聊天助手在维持多轮对话中的熟练程度而设计。

- **目的：** 测试模型在多个回合中进行连贯和上下文相关对话的能力。
- **相关：** 对于开发复杂的会话代理和聊天机器人至关重要。
- **原文：**[《Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena》](https://arxiv.org/abs/2306.05685)
- **资源：**
    - [MT-bench Human Annotation Dataset](https://huggingface.co/datasets/lmsys/mt_bench_human_judgments)

### 3.2 QuAC

Question Answering in Context，包含14000个对话和100000个问答对，模拟学生与教师的互动。

- **目的：** 在对话中用上下文相关的、有时无法回答的问题来挑战 LLM。
- **相关：** 适用于对话式人工智能、教育软件和上下文感知信息系统。
- **原文：**[《QuAC : Question Answering in Context》](https://arxiv.org/abs/1808.07036)
- **资源：**
    - [QuAC Homepage and Dataset](https://quac.ai/)

## 3. 综述抽取与生成能力

### 3.1 ACI-BENCH

Ambient Clinical Intelligence Benchmark，包含来自各个医疗领域的医生-病人对话和相关的临床笔记。

- **目的：** 挑战模型根据会话数据准确生成临床笔记。
- **相关：** 对医疗保健中的人工智能应用至关重要，尤其是在自动化文档和医疗分析中。
- **原文：**[《ACI-BENCH: a Novel Ambient Clinical Intelligence Dataset for Benchmarking Automatic Visit Note Generation》](https://arxiv.org/abs/2306.02022)
- **资源：**
    - [ACI-BENCH Dataset](https://github.com/wyim/aci-bench)

### 3.2 MS-MARCO

MAchine Reading COmprehension Dataset， 从真实网络查询中提取的自然语言问题和答案的大规模集合。

- **目的：** 测试模型准确理解和响应真实世界查询的能力。
- **相关：** 对于搜索引擎、问答系统和其他面向消费者的人工智能应用程序至关重要。
- **原文：**[《MS MARCO: A Human Generated MAchine Reading COmprehension Dataset》](https://arxiv.org/abs/1611.09268)
- **资源：**
    - [MS-MARCO Dataset](https://huggingface.co/datasets/ms_marco)

### 3.3 QMSum

Query-based Multi-domain Meeting Summarization，针对特定查询从会议内容中提取和总结重要信息的基准。

- **目的：** 评估模型从会议内容中提取和总结重要信息的能力。
- **相关：** 适用于商业智能工具、会议分析应用程序和自动摘要系统。
- **原文：**[《QMSum: A New Benchmark for Query-based Multi-domain Meeting Summarization》](https://arxiv.org/abs/2104.05938)
- **资源：**
    - [QMSum Dataset](https://github.com/Yale-LILY/QMSum)

### 3.4 PIQA

Physical Interaction: Question Answering，通过假设性场景和解决方案测试对物理世界的知识和理解。

- **目的：** 衡量模型处理物理交互场景的能力。
- **相关：** 对于机器人、物理模拟和实际问题解决系统中的人工智能应用非常重要。
- **原文：**[《PIQA: Reasoning about Physical Commonsense in Natural Language》](https://arxiv.org/abs/1911.11641)
- **资源：**
    - [PIQA Dataset: GitHub](https://github.com/ybisk/ybisk.github.io/tree/master/piqa)

## 4. 内容审核和叙事控制

### 4.1 ToxiGen

一个关于少数群体的恶毒和善意言论的数据集，重点关注隐含的仇恨言论。

- **目的：** 测试模型识别和避免产生有毒内容的能力。
- **相关：** 对内容审核系统、社区管理和人工智能伦理研究至关重要。
- **原文：**[《ToxiGen: A Large-Scale Machine-Generated Dataset for Adversarial and Implicit Hate Speech Detection》](https://arxiv.org/abs/2203.09509)
- **资源：**
    - [TOXIGEN Code and Prompts: GitHub](https://github.com/microsoft/TOXIGEN/tree/main)
    - [TOXIGEN Dataset: HuggingFace](https://huggingface.co/datasets/skg/toxigen-data)

### 4.2 HHH

Helpfulness, Honesty, Harmlessness，评估语言模型与有用性、诚实性和无害性等道德标准的一致性。

- **目的：** 评估模型在交互场景中的道德反应。
- **相关：** 对于确保人工智能系统促进积极互动和遵守道德标准至关重要。
- **原文：**[《A General Language Assistant as a Laboratory for Alignment》](https://arxiv.org/abs/2112.00861)
- **资源：**
    - [HH-RLHF Datasets: GitHub](https://github.com/anthropics/hh-rlhf)
    - 最近进程:
        - [《Training a Helpful and Harmless Assistant with Reinforcement Learning from Human Feedback》](https://arxiv.org/abs/2204.05862)
        - [《Red Teaming Language Models to Reduce Harms: Methods, Scaling Behaviors, and Lessons Learned》](https://arxiv.org/abs/2209.07858)

### 4.3 TruthfulQA

评估 LLM 在回答容易产生错误信念和偏见的问题时的真实性的基准。

- **目的：** 测试模型提供准确无偏信息的能力。
- **相关：** 对于提供准确和公正信息至关重要的人工智能系统来说很重要，例如在教育或咨询方面。
- **原文：**[TruthfulQA: Measuring How Models Mimic Human Falsehoods](https://arxiv.org/abs/2109.07958v2)
- **资源：**
    - [TruthfulQA Dataset: GitHub](https://github.com/sylinrl/TruthfulQA)

### 4.4 RAI

Responsible AI，用于评估聊天优化模型在会话环境中的安全性的框架

- **目的：** 评估人工智能驱动的对话中潜在的有害内容、IP泄露和安全漏洞。
- **相关：** 对于开发安全可靠的对话式人工智能应用程序至关重要，尤其是在敏感领域。
- **原文：**[《A Framework for Automated Measurement of Responsible AI Harms in Generative AI Applications》](https://arxiv.org/abs/2310.17750)

## 5. 编程能力

### 5.1 CodeXGLUE

评估LLM在代码理解和生成、代码补全和翻译等各种任务中的能力。

- **目的：** 评估代码智能，包括理解、修复和解释代码。
- **相关：** 对于软件开发、代码分析和技术文档中的应用程序至关重要。
- **原文：**[《CodeXGLUE: A Machine Learning Benchmark Dataset for Code Understanding and Generation》](https://arxiv.org/abs/2102.04664)
- **资源：**
    - [CodeXGLUE Dataset: GitHub](https://github.com/microsoft/CodeXGLUE)

### 5.2 HumanEval

包含编程挑战，评估 LLM 基于指令编写功能性代码的能力。

- **目的：** 测试根据给定需求生成正确有效的代码。
- **相关：** 对于自动化代码生成工具、编程助手和编码教育平台非常重要。
- **原文：**[《Evaluating Large Language Models Trained on Code》](https://arxiv.org/abs/2107.03374)
- **资源：**
    - [HumanEval Dataset: GitHub](https://github.com/openai/human-eval)

### 5.3 MBPP

Mostly Basic Python Programming，包括1000个适合初级程序员的 Python 编程问题。

- **目的：** 评估解决基本编程任务的熟练程度和对 Python的理解。
- **相关：** 适用于初级编码教育、自动代码生成和入门级编程测试。
- **原文：**[《Program Synthesis with Large Language Models》](https://arxiv.org/abs/2108.07732)
- **资源：**
    - [MBPP Dataset: HuggingFace](https://huggingface.co/datasets/mbpp)

## 6. 参考

https://github.com/leobeeson/llm_benchmarks

---

欢迎关注本人，我是喜欢搞事的程序猿； 一起进步，一起学习；

欢迎关注知乎/CSDN：[SmallerFL](https://www.zhihu.com/people/feng-lei-13-12/posts)

也欢迎关注我的wx公众号（精选高质量文章）：一个比特定乾坤  
![在这里插入图片描述](https://i-blog.csdnimg.cn/blog_migrate/25027d157bd5abac73953be8117a41a3.png)