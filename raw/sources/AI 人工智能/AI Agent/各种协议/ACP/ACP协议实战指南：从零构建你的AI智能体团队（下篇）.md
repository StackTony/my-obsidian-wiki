原文链接： https://zhuanlan.zhihu.com/p/1935327158538077444

在上篇文章里，我们一起探讨了ACP协议的来龙去脉，也对比了它和其他协议的差异。如果你还没看过，不妨先去读一下《AI智能体的"[世界语](https://zhida.zhihu.com/search?content_id=261182456&content_type=Article&match_order=1&q=%E4%B8%96%E7%95%8C%E8%AF%AD&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODUzOTU0NzcsInEiOiLkuJbnlYzor60iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjExODI0NTYsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.v8fUzvzCqfxxoFExMszFgy4cXNT6tWOsbricK9uYi9U&zhida_source=entity)"来了！ACP协议深度解析（上篇）》。

[ACP协议让AI团队协作成为现实（上篇）](https://zhuanlan.zhihu.com/p/1935325407202222463)

理论讲得再多，不如动手试试。今天我们就来实际搭建几个有趣的智能体，看看ACP到底能做什么。

### 你的第一个ACP智能体

我们先来看看ACP整个生态是怎么运作的：

![](https://picx.zhimg.com/v2-bc46202342fbd3c5994238275c6f1bbf_1440w.jpg)

### 环境准备

工欲善其事，必先利其器。我们先把开发环境搞定。ACP官方推荐用`uv`这个包管理器，确实比pip好用不少。

如果你还没装`uv`，去官网按照安装指南 [https://docs.astral.sh/uv/getting-started/installation/](https://link.zhihu.com/?target=https%3A//docs.astral.sh/uv/getting-started/installation/) 安装完成后。然后我们就可以开始了：

```
# 创建项目目录
uv init --python '>=3.11' my_acp_project
cd my_acp_project
```

接下来装一些必要的包：

```
# 基础的ACP SDK
uv add acp-sdk

# 如果要做诗歌生成的话
uv add transformers torch crewai crewai-tools
uv add scipy pydub httpx asyncio

# 智能体生成器需要这些
uv add langchain langchain-mcp-adapters langgraph mcpdoc
uv add pydantic-settings
```

最后配置一下API密钥。创建个`.env`文件：

然后根据你用的LLM服务商，填入对应的API key：

```
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here  
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### 案例一：诗歌创作智能体

我一直觉得，让AI写诗是个挺有意思的事情。不过单靠一个智能体可能有点单调，要是能组个团队就好了——有人负责写诗，有人配音，再来个作曲的。

用ACP正好可以实现这个想法。我们来搭建一个诗歌创作智能体：

- 诗人：负责根据主题创作诗歌，中英文都能写
- 配音师：把诗歌转成语音
- 音乐家：配个背景音乐
- 协调器：统筹整个流程

这几个角色分工明确，通过ACP协议互相配合。架构大概是这样的：

![](https://pic4.zhimg.com/v2-8cfd86908993d8ce54d16b3a058d1505_1440w.jpg)

这里我使用了开源的小模型, 自己的笔记本电脑上就能运行起来：

**语音合成（TTS）**

- 这是BosonAI推出的最新语音生成模型，支持情感表达和多语言(中文、英文、德语、韩语)
- 在EmergentTTS评测中表现优异，胜过GPT-4o的TTS效果

**音乐生成**：

- Meta开源的文本到音乐生成模型，300M参数版本
- 可以根据文字描述生成背景音乐

先来看看服务器端的代码（`poetry_server.py`）：

```
import os
import asyncio
from collections.abc import Iterator
from datetime import datetime
from acp_sdk import Message, MessagePart
from acp_sdk.server import Context, Server
from crewai import Agent, Crew, Task, Process
from crewai.llm import LLM
from crewai.tools import tool

# 设置LLM，这里用Gemini，你也可以换成其他的
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("需要设置GEMINI_API_KEY环境变量")

llm = LLM(model='gemini/gemini-2.0-flash-exp',
         api_key=GEMINI_API_KEY,
         temperature=0.7)  # 温度设高一点，让诗歌更有创意

server = Server()

# 全局会话ID管理
_current_session_id = None

def generate_unique_session_id():
    """生成唯一的会话ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    import uuid
    short_uuid = uuid.uuid4().hex[:6]
    return f"{timestamp}_{short_uuid}"

@tool("Text to Speech")
def text_to_speech_tool(text: str) -> str:
    """将文本转换为语音文件"""
    global _current_session_id
    os.makedirs("poem", exist_ok=True)
    output_path = f"poem/speech_{_current_session_id}.wav"

    # 这里简化处理，实际可以集成真实的TTS服务
    print(f" ️ 正在生成语音: {text[:50]}...")

    # 创建占位文件（实际应用中会调用TTS API）
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"TTS音频文件占位符\n文本内容: {text}")

    print(f"✅ 语音文件已生成: {output_path}")
    return output_path

@tool("Music Generation")
def music_generation_tool(prompt: str) -> str:
    """根据提示生成背景音乐"""
    global _current_session_id
    os.makedirs("poem", exist_ok=True)
    output_path = f"poem/music_{_current_session_id}.wav"

    print(f"  正在生成音乐: {prompt}")

    # 创建占位文件（实际应用中会调用音乐生成模型）
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"音乐文件占位符\n音乐风格: {prompt}")

    print(f"✅ 音乐文件已生成: {output_path}")
    return output_path

@server.agent()
def poetry_agent(input: list[Message], context: Context) -> Iterator:
    """多智能体诗歌创作系统"""
    global _current_session_id

    theme = str(input[-1].parts[0].content) if input else ""
    if not theme:
        yield MessagePart(content="请提供一个诗歌主题。")
        return

    # 生成会话ID
    _current_session_id = generate_unique_session_id()

    try:
        # 定义专业智能体团队
        poet = Agent(
            llm=llm,
            role="诗人",
            goal="根据主题 {theme} 创作一首优美的短诗（4-8行）。如果主题是中文，请用中文创作；如果是英文，请用英文创作。",
            backstory="你是一位精通中英文的专业诗人，擅长创作富有感染力的短诗。",
            verbose=True,
        )

        voice_artist = Agent(
            llm=llm,
            role="配音师",
            goal="将诗歌转换为清晰动人的语音文件。",
            backstory="你是一位专业的配音演员，能够将文字转化为富有情感的声音。",
            verbose=True,
            tools=[text_to_speech_tool],
        )

        musician = Agent(
            llm=llm,
            role="音乐家",
            goal="为诗歌创作合适的背景音乐。",
            backstory="你是一位才华横溢的作曲家，专长于创作与诗歌情境匹配的音乐。",
            verbose=True,
            tools=[music_generation_tool],
        )

        # 定义创作任务
        write_poem_task = Task(
            description="根据主题 '{theme}' 创作一首短诗（4-8行）。保持语言与主题一致。",
            expected_output="一首4-8行的优美诗歌",
            agent=poet,
        )

        speak_poem_task = Task(
            description="将诗歌转换为语音文件。",
            expected_output="语音文件路径",
            agent=voice_artist,
            context=[write_poem_task]
        )

        create_music_task = Task(
            description="为诗歌创作适合的背景音乐。",
            expected_output="音乐文件路径",
            agent=musician,
            context=[write_poem_task]
        )

        # 创建并运行智能体团队
        crew = Crew(
            agents=[poet, voice_artist, musician],
            tasks=[write_poem_task, speak_poem_task, create_music_task],
            process=Process.sequential,
            verbose=True,
        )

        result = crew.kickoff(inputs={'theme': theme})

        # 处理结果
        poem_content = None
        speech_file = None
        music_file = None

        # 提取任务输出
        if hasattr(result, 'tasks_output'):
            for task_output in result.tasks_output:
                output_text = str(task_output.raw) if hasattr(task_output, 'raw') else str(task_output)

                # 提取诗歌内容
                if poem_content is None and 'poem/' not in output_text and '.wav' not in output_text:
                    if len(output_text.strip()) > 20:
                        poem_content = output_text.strip()

                # 提取文件路径
                if 'poem/speech_' in output_text:
                    speech_file = f"poem/speech_{_current_session_id}.wav"
                elif 'poem/music_' in output_text:
                    music_file = f"poem/music_{_current_session_id}.wav"

        # 保存诗歌文本
        if poem_content:
            poem_file_path = f"poem/poem_text_{_current_session_id}.txt"
            with open(poem_file_path, 'w', encoding='utf-8') as f:
                f.write(f"主题: {theme}\n")
                f.write(f"创作时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*50}\n")
                f.write(poem_content)

            yield MessagePart(content=f"  诗歌创作完成！会话ID: {_current_session_id}\n\n"
                                    f"  诗歌: {poem_file_path}\n"
                                    f" ️ 配音: {speech_file or '生成中...'}\n"
                                    f"  音乐: {music_file or '生成中...'}\n\n"
                                    f"诗歌内容预览:\n{'-'*30}\n{poem_content[:200]}...")
        else:
            yield MessagePart(content=f"❌ 诗歌创作失败，会话ID: {_current_session_id}")

    except Exception as e:
        yield MessagePart(content=f"❌ 创作过程出错: {str(e)}")

if __name__ == "__main__":
    print("  启动诗歌创作智能体团队...")
    print("  服务地址: http://localhost:8000")
    server.run(host="localhost", port=8000)
```

再写个客户端来测试（`poetry_client.py`）：

```
import asyncio
from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart

async def create_poetry():
    """调用诗歌创作智能体"""
    print("连接到诗歌创作服务...")

    async with Client(base_url="http://localhost:8000") as client:
        # 试试不同的主题
        themes = ["八月太热了"]

        for theme in themes:
            print(f"\n创作主题: {theme}")
            print("-" * 50)

            run = await client.run_sync(
                agent="poetry_agent",
                input=[Message(parts=[
                    MessagePart(content=theme, content_type="text/plain")
                ])]
            )

            for message in run.output:
                for part in message.parts:
                    print(part.content)

            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(create_poetry())
```

现在可以运行了：

1. 先设置API密钥：

```
export GEMINI_API_KEY=your_key
# 或者直接写在.env文件里
```

1. 启动服务器：

1. 另开一个终端，运行客户端：

看看实际效果如何。我试着让它写个关于"八月太热了"的诗，结果还挺不错的：

```
八月炎炎似火烧，
大地蒸腾热浪嚣。
蝉鸣声声催人倦，
树影婆娑也无聊。

汗珠滴落湿衣衫，
微风难觅影踪杳。
池塘水面波光静，
鱼儿潜底避骄阳。

午后昏沉人欲睡，
街头巷尾少喧嚣。
唯有空调声低吟，
带来一丝清凉调。

盼得夜幕缓缓降，
星光点点慰寂寥。
愿得清风拂热浪，
明日凉爽胜今朝。
```

还会自动生成配音和背景音乐文件（虽然这里只是占位符，但接入真实的TTS和音乐API后就能产出真正的音频了）。

### 跨框架智能体协作, 让智能体生成智能体

刚才的诗歌团队已经挺酷了，但我还想给你看个更厉害的——让智能体来生成其他的AI智能体。

### 案例二：[动态智能体](https://zhida.zhihu.com/search?content_id=261182456&content_type=Article&match_order=1&q=%E5%8A%A8%E6%80%81%E6%99%BA%E8%83%BD%E4%BD%93&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODUzOTU0NzcsInEiOiLliqjmgIHmmbrog73kvZMiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjExODI0NTYsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.ITxThnSXOgJ9XEee4T_BD6gbJAxMPNhksu_2NpakXaI&zhida_source=entity)生成器

很多实际场景的事情,即使是人来处理都需要随机应变. 需要只用语言描述你想要什么功能，然后[智能体系统](https://zhida.zhihu.com/search?content_id=261182456&content_type=Article&match_order=1&q=%E6%99%BA%E8%83%BD%E4%BD%93%E7%B3%BB%E7%BB%9F&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODUzOTU0NzcsInEiOiLmmbrog73kvZPns7vnu58iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjExODI0NTYsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.J9d09KHYtHjwqKBkCesOCZd6znynHGoIAs9hqoqRSEc&zhida_source=entity)帮你写出完整的智能体架构,包括代码。

这个案例我就不从零写了，因为ACP官方已经有个很不错的例子。你可以直接去看源码：

这个Agent生成器的能力包括： - 理解你的自然语言描述 - 查阅相关技术文档（ACP、LangGraph、BeeAI等） - 自动生成完整的智能体代码 - 连测试代码都给你写好

整个工作流程是这样的：

![](https://pic3.zhimg.com/v2-1e58ce03727abf09c0b11581565977f6_1440w.jpg)

核心技术原理很有意思，动态智能体生成器本质上是一个"[元智能体](https://zhida.zhihu.com/search?content_id=261182456&content_type=Article&match_order=1&q=%E5%85%83%E6%99%BA%E8%83%BD%E4%BD%93&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODUzOTU0NzcsInEiOiLlhYPmmbrog73kvZMiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjExODI0NTYsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.k_lt0edxqMHK0hTb9V5_3qWyLZyGe0FRb6_2jg7CWJo&zhida_source=entity)"，：

1. **多源文档集成（[MCP协议](https://zhida.zhihu.com/search?content_id=261182456&content_type=Article&match_order=1&q=MCP%E5%8D%8F%E8%AE%AE&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODUzOTU0NzcsInEiOiJNQ1DljY_orq4iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjExODI0NTYsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.NpTrOsg7s92pVu1h9R2Rshq-mXcWJy6_AqAMimrouRk&zhida_source=entity)）**：通过MCP协议实时读取各种技术文档

```
# 它能访问这些文档来学习最新的API
documentation_sources = [
    "ACP协议文档",
    "LangGraph框架文档", 
    "BeeAI平台文档"
]
```

1. **智能代码生成**：用LangGraph + LLM来理解需求并生成代码

```
@server.agent()
async def acp_agent_generator(input: list[Message], context: Context):
    """这就是核心的生成逻辑"""
    user_request = input[-1].parts[0].content

    # 先理解用户要什么
    requirements = analyze_requirements(user_request)

    # 查文档找最佳实践
    docs = await query_documentation(requirements)

    # 生成代码
    generated_code = await generate_agent_code(requirements, docs)

    yield generated_code
```

1. **自适应模板系统**：根据不同需求选择合适的代码模板

**技术架构要点：** - **SessionManager**：管理MCP文档连接和工具 - **ReAct Agent**：使用推理-行动模式生成代码 - **Temperature=0.1**：确保代码生成的准确性和一致性

想试试的话，直接用官方的例子就行：

```
# 克隆代码
git clone https://github.com/i-am-bee/acp.git
cd acp/examples/python/acp-agent-generator

# 装依赖
uv sync

# 配置API（在.env文件里）
LLM_MODEL_NAME=openai/gpt-4o
OPENAI_API_KEY=your_key_here

# 启动
uv run agent.py

# 另开个终端测试
uv run client.py
```

效果挺神奇的，比如你说"希望创建AI辅助智能体，能够影像分析、病历分析和药物推荐"，它就会：

- 自动查阅ACP文档
- 生成完整的服务器端代码 包括**AI辅助智能体架构**, 如下：

```
患者信息 → 病历分析AI → 影像诊断AI → 药物推荐AI → 综合报告AI
         ↘                ↗              ↘
          症状分析AI ←→ 风险评估AI ←→ 治疗方案AI
```

- 写好客户端测试
- 给出详细的运行说明

### 学习资源

如果你想深入了解ACP，这些资源挺有用的：

1. 官方文档：[https://agentcommunicationprotocol.dev/](https://link.zhihu.com/?target=https%3A//agentcommunicationprotocol.dev/)
2. GitHub仓库：[https://github.com/i-am-bee/acp](https://link.zhihu.com/?target=https%3A//github.com/i-am-bee/acp)
3. BeeAI平台：[https://beeai.dev/agents](https://link.zhihu.com/?target=https%3A//beeai.dev/agents)

---

ACP最大的价值，我觉得是让AI之间的协作变得简单了。不需要为每个框架写特定的胶水代码，大家都用同一套"语言"交流。这就好比以前各国说各自的语言，现在有了通用语，交流起来容易多了。

---
