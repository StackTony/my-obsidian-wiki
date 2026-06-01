---
credibility: low
---
[2025 iThome 鐵人賽](https://ithelp.ithome.com.tw/2025ironman)DAY 22

0

[生成式 AI](https://ithelp.ithome.com.tw/2025ironman/generative-ai)

### 用 Node.js 打造生成式 AI 應用：從 Prompt 到 Agent 開發實戰系列 第 22 篇

## Day 22 - ReAct 模式實戰：封裝 LLM 建立可推理與行動的 Agent

- 分享至
- [![xImage](https://ithelp.ithome.com.tw/images/x/x.png)](https://twitter.com/intent/tweet?text=https://ithelp.ithome.com.tw/articles/10385213)

在前一篇文章中，我們已經學會如何用 **LangGraph** 建立基本的 AI Agent 流程。今天，我們要更進一步，介紹一個經典的 Agent 設計模式： **ReAct（Reasoning + Acting）** 。  
ReAct 模式的核心概念是結合「推理」與「行動」，讓模型不僅能回答問題，還能在需要時選擇合適的工具來完成任務。這種設計使得 AI Agent 具備更高的靈活性與解題能力。

## 什麼是 ReAct 模式？

**ReAct（Reasoning + Acting）** 模式最早由 Google Research 在論文 [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) 中提出，目的是讓大型語言模型（LLM）同時具備 **推理（Reasoning）** 與 **行動（Acting）** 能力。

它的核心運作流程可以拆解為以下循環：

1. **思考 (Thought)** ：模型根據目前的上下文，描述觀察結果並提出推理。
2. **行動 (Action)** ：模型決定要使用哪個工具，並產生對應的輸入。
3. **觀察 (Observation)** ：接收工具的輸出結果，並將其作為下一步推理的依據。
4. 重複以上步驟，直到模型認為任務已完成，輸出 **最終答案 (Final Answer)** 。

這樣的設計使得 ReAct 將 **Chain-of-Thought（CoT）** 與 **工具調用（Tool Use）** 結合在一起，不再只是單向的「輸入 Prompt → 輸出答案」，而是形成一個動態的「推理—行動—觀察—再推理」循環。這讓 LLM 能更有條理地處理複雜任務，並在需要時引入外部能力，透過實際操作與驗證逐步推進，最終獲得更準確、可解釋的結果。

舉例來說，假設使用者詢問：「台北今天適合跑步嗎？」ReAct 模式的過程可能如下：

1. **思考** ：要判斷是否適合跑步，需要知道台北的天氣。
2. **行動** ：呼叫天氣工具，輸入「Taipei」。
3. **觀察** ：工具回覆「30 度，多雲，有午後雷陣雨」。
4. **思考** ：因為有雷陣雨，今天不適合戶外跑步。
5. **最終答案** ：今天不建議在台北跑步，因為可能會下雨。

這個流程展現了 ReAct 的精髓：模型並不是一次性輸出結論，而是透過推理與工具調用的交互循環，逐步累積資訊，最終形成可靠的答案。

### ReAct 解決了什麼問題？

在 ReAct 概念落地之前，傳統的 LLM 應用中，模型通常採取「單次輸入 Prompt → 輸出答案」的方式運作。這種模式雖然簡單，但也存在一些限制：

- **無法即時查詢外部資料** ：只能依賴訓練階段的知識，遇到需要最新資訊的問題（例如天氣、股價、新聞）便無能為力。
- **中間思考過程不透明** ：LLM 的推理大多隱藏在內部，使用者與開發者難以觀察，也不容易調整或除錯。
- **難以處理複雜任務** ：面對需要多步驟推理的問題時，模型容易產生錯誤或幻覺（hallucination），缺乏可靠性。

ReAct 模式的循環設計，則帶來了以下幾個關鍵優勢：

- **資訊即時性** ：能透過工具調用獲取外部知識與最新資料，而不僅限於模型內部記憶。
- **可解釋性** ：思考（Thought）、行動（Action）與觀察（Observation）會被明確輸出，開發者能清楚追蹤推理過程。
- **任務可拆解** ：複雜問題可被分解為多個小步驟，每次透過「推理—行動—觀察」迴圈逐步完成，降低出錯率。

換句話說，ReAct 是讓 Agent 從「純對話機器人」進化為「能思考、能行動的智慧助手」的關鍵設計。

| 面向 | 傳統 LLM | ReAct 模式 |
| --- | --- | --- |
| **工作方式** | 一次性輸入 Prompt，直接產生最終回覆 | 在推理（Thought）與行動（Action）間循環，逐步收斂答案 |
| **資訊來源** | 完全依賴模型的內部知識 | 可結合外部工具與檢索結果 |
| **推理透明度** | 模型內部隱性推理，開發者難以追蹤 | 每一步都有可觀察的「思考」與「行動」輸出 |
| **適用任務** | 簡單問答、生成文本 | 複雜任務、多步推理、需要外部資料或工具輔助 |
| **優勢** | 快速、直接 | 更準確、可解釋、能處理更廣泛的情境 |

## 在 LangGraph 中實現 ReAct

ReAct 的核心精神是「推理與行動交替進行」，而 LangGraph 恰好非常適合用來實作這種迴圈式流程。要在 LangGraph 中落地 ReAct 模式，我們可以把「推理」與「行動」拆分成不同的 **節點（Node）** ，並透過 **狀態（State）** 與 **邊（Edge）** 的設計，讓 Agent 在兩者之間反覆循環，直到產生最終答案。

在這個設計中，通常會包含三個核心元件：

1. **LLM 節點**
	- 由大型語言模型（LLM）驅動，負責輸出 **思考（Thought）** 與 **行動（Action）** 的指令。
		- 例如，當使用者問「今天台北適合跑步嗎？」時，LLM 可能會先推理：「我需要知道今天台北的天氣，因此應該呼叫天氣查詢工具。」
2. **Tool 節點**
	- 負責執行模型指定的「行動」，例如呼叫 API、進行數學計算、或查詢資料庫。
		- 工具執行後會回傳結果，這就是 **觀察（Observation）** 的實現。延續前例，Tool 可能回覆：「台北今天 30 度，多雲，午後有雷陣雨。」
3. **迴圈控制**
	- 工具的回覆並不會直接呈現給使用者，而是送回 **LLM 節點** 進行新一輪推理。模型需要判斷是否要再次呼叫工具，或是已經有足夠資訊輸出 **最終答案（Final Answer）** 。
		- 這個迴圈會持續進行，直到模型明確輸出最終答案，流程才會結束。

### ReAct 在 LangGraph 的運作流程

在 LangGraph 中，ReAct 的運作可以想成是一個「 **推理 → 行動 → 觀察 → 再推理** 」的循環：

1. 使用者提出問題，進入 **LLM 節點** 。
2. 模型進行推理，並決定是否需要調用工具。
3. 如果需要，轉交給 **Tool 節點** 執行，並將結果作為觀察傳回。
4. 模型再根據觀察結果進一步推理，可能再次呼叫工具，或直接產生最終答案。

這個過程可以用下圖表示：

![https://ithelp.ithome.com.tw/upload/images/20250922/20150150kLMNSp7gBN.png](https://ithelp.ithome.com.tw/upload/images/20250922/20150150kLMNSp7gBN.png)

透過這樣的節點設計，LangGraph 能夠完整支援 ReAct 模式，讓 Agent 不再只是一次性回覆，而是能像人類一樣透過「推理—行動—觀察—再推理」的循環，不斷修正與補充資訊，最終得出更合理、精確且可解釋的答案。

## 實作範例：簡易 ReAct Agent

接下來我們用一個最小可行的案例示範 ReAct 模式：「查詢天氣，並根據結果建議今天是否適合出門運動。」這個範例會結合 **OpenAI 模型** 與 **Tavily Search 工具** ，展示 LLM 如何一邊思考、一邊透過工具取得資訊，再回過頭做出合理的建議。

### 建立 LangGraph 專案

首先，我們使用官方工具 `create-langgraph` 來建立一個全新的專案：

```bash
create-langgraph react-agent
```

當工具詢問模板類型時，選擇 **New LangGraph Project** 即可。這個模板會自動幫你建立一個包含 `src/agent` 目錄的專案骨架。

接著進入專案資料夾並安裝相依套件：

```bash
cd react-agent
yarn install
```

### 安裝依賴套件

初始化專案後，接著安裝以下套件：

```bash
yarn add @langchain/openai @langchain/tavily
```

這裡我們會用到兩個主要套件：

- `@langchain/openai` ：LangChain 官方的 OpenAI 模型整合套件，用於提供推理能力（Reasoning）。
- `@langchain/tavily` ：LangChain 官方支援的工具封裝，用來呼叫 Tavily Search API，這裡把它當作查詢天氣的資訊來源。

### 設定環境變數

在專案根目錄建立 `.env` 檔案，填入必要的 API 金鑰：

```markdown
LANGSMITH_KEY=llsv2...
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-dev-...
```
- `LANGSMITH_KEY` ：啟用 LangSmith 觀察功能（可選，但建議填入，方便後續在 Studio UI 追蹤流程）。
- `OPENAI_API_KEY` ：OpenAI 模型的金鑰。
- `TAVILY_API_KEY` ：Tavily 搜尋工具的金鑰。

### 撰寫 ReAct Agent 流程

專案的 `src/agent` 目錄下已經有兩個檔案：

- `state.ts` ：定義狀態結構，預設已經包含訊息處理，我們直接沿用即可。
- `graph.ts` ：主要的流程定義檔，我們會在這裡實作 ReAct Agent。

開啟 `src/agent/graph.ts` ，加入以下程式碼：

```ts
// src/agent/graph.ts
import { StateGraph, START, END } from '@langchain/langgraph';
import { ToolNode } from '@langchain/langgraph/prebuilt';
import { AIMessage } from '@langchain/core/messages';
import { ChatOpenAI } from '@langchain/openai';
import { TavilySearch } from '@langchain/tavily';
import { StateAnnotation } from './state.js';

// 建立可用的工具 (Act)
const tools = [new TavilySearch({ maxResults: 3 })];
const toolNode = new ToolNode(tools);

// 建立 LLM 並綁定工具 (Reason)
const model = new ChatOpenAI({
  model: 'gpt-4o-mini',
  temperature: 0,
}).bindTools(tools);

// 判斷是否要繼續迴圈
function shouldContinue({ messages }: typeof StateAnnotation.State) {
  const lastMessage = messages[messages.length - 1] as AIMessage;
  if (lastMessage.tool_calls?.length) {
    return 'tools'; // 如果 LLM 決定要呼叫工具
  }
  return END; // 否則結束，輸出最終答案
}

// LLM 推理節點
async function callModel(state: typeof StateAnnotation.State) {
  const response = await model.invoke(state.messages);
  return { messages: [response] };
}

// 建立 ReAct Agent 流程
const builder = new StateGraph(StateAnnotation)
  .addNode('agent', callModel) // Reasoning
  .addEdge(START, 'agent')
  .addNode('tools', toolNode)  // Acting
  .addEdge('tools', 'agent')   // Observation 回傳給 LLM
  .addConditionalEdges('agent', shouldContinue);

export const graph = builder.compile();
graph.name = 'ReAct Agent';
```

這裡最重要的部分是 `addConditionalEdges` ，它會根據 LLM 是否提出工具調用（ `tool_calls` ）來決定流程走向：

- 有工具調用 → 流程進到 `tools` 節點，執行外部動作，並將結果傳回 LLM。
- 沒有工具調用 → 流程走向 `END` ，輸出最終答案。

### 測試 ReAct Agent

完成程式碼後，可以啟動 LangGraph Server，並透過 LangGraph Studio 觀察流程：

```bash
npx @langchain/langgraph-cli dev
```

啟動後，終端機會顯示本地伺服器 URL，例如：

```markdown
http://127.0.0.1:2024
```

將它帶入 Studio UI 的網址：

```markdown
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

在 Studio UI 的 **Chat** 分頁輸入問題，例如：

```markdown
台北今天適合跑步嗎？
```

![https://ithelp.ithome.com.tw/upload/images/20250922/20150150cA2vWTF8L1.png](https://ithelp.ithome.com.tw/upload/images/20250922/20150150cA2vWTF8L1.png)

你會看到流程圖清楚呈現：

1. 使用者的問題先進到 **agent 節點** ，由 LLM 判斷是否需要外部資訊。
2. LLM 呼叫我們綁定的 **TavilySearch 工具** ，查詢台北天氣。
3. 工具回傳觀察結果（Observation），再送回 LLM。
4. LLM 根據天氣狀況進行推理，給出最終建議。
```markdown
今天台北的天氣大致晴朗，氣溫在33℃左右，降雨機率很低（約5%）。這樣的天氣條件很適合跑步，但建議注意防曬和保持水分。如果你打算在戶外運動，記得穿著輕便的運動服裝，並在早晨或傍晚的時候進行，以避免高溫。
```

這樣，我們就完成了一個最小可行的 ReAct Agent 範例。它雖然只是查詢天氣，但已經完整展現了 ReAct 的核心精神： **先思考，再行動，根據結果再思考，直到完成任務** 。

## 使用 createReactAgent 快速建立 ReAct Agent

如果你希望快速上手，不必手動設計所有節點與邊，LangGraph 提供了高階封裝函式 `createReactAgent` ，能自動幫你建立一個符合 ReAct 模式的 Agent。

這個函式會將 **LLM 節點** 與 **Tool 節點** 的互動邏輯封裝起來，你只需要：

1. 指定要使用的 **LLM** 。
2. 提供可調用的 **工具（Tools）** 。
3. 視需求加上 **記憶（Memory）** 、 **自訂 Prompt** 或其他進階功能。

以下是一個最小化範例：

```ts
import { ChatOpenAI } from '@langchain/openai';
import { TavilySearch } from '@langchain/tavily';
import { HumanMessage } from '@langchain/core/messages';
import { createReactAgent } from '@langchain/langgraph/prebuilt';

const tools = [new TavilySearch({ maxResults: 3 })];

const model = new ChatOpenAI({
  model: 'gpt-4o-mini',
  temperature: 0,
});

const graph = createReactAgent({
  llm: model,
  tools,
});

const finalState = await graph.invoke({
  messages: [new HumanMessage('台北今天適合跑步嗎？')],
});

console.log(finalState.messages[finalState.messages.length - 1].content);
```

在這個範例中， `createReactAgent` 自動幫我們處理了 ReAct 模式的整個迴圈：

- **LLM 推理** ：先分析問題，決定是否需要外部資訊。
- **工具調用** ：如果需要，就呼叫 `TavilySearch` 工具，獲取查詢結果。
- **觀察回饋** ：工具的回傳內容會再送回 LLM，做進一步推理。
- **最終答案** ：當模型認為資訊足夠時，輸出最後結論並結束流程。

這種高階封裝大幅降低了 ReAct Agent 的實作門檻，非常適合快速原型開發或不需要高度客製化的場景。如果未來需要更精細的流程控制，仍然可以回到前一節的做法，利用 `StateGraph` 手動定義節點與邊，打造更靈活的 ReAct 流程。

## 小結

今天我們學會如何在 LangGraph 中實作經典的 **ReAct** 模式，讓 Agent 能透過「思考—行動—觀察—再思考」的循環，逐步完成複雜任務。

- ReAct 的核心是把推理（Reasoning）與行動（Acting）結合，透過「思考—行動—觀察—再思考」的循環機制逐步收斂出可靠答案。
- 它解決了傳統 LLM 無法即時查詢、推理過程不透明、難以處理複雜任務的限制。
- ReAct 帶來資訊即時性、推理可解釋性，以及將複雜問題拆解成多步驟的能力。
- 在 LangGraph 中可用節點（Reasoning/Acting）、狀態與條件邊實現 ReAct 循環。
- 透過實作範例，我們示範了如何結合 OpenAI 與 Tavily 工具，建立一個能查天氣並給運動建議的最小 ReAct Agent。
- LangGraph 也提供 `createReactAgent` 高階封裝，能快速建立 ReAct Agent，適合原型開發或簡單應用場景。

ReAct 模式的出現，讓 AI 不再只是單向的「回答者」，而能像人類一樣邊思考邊行動，成為更靈活、可靠的智慧助手。

---

> ![Node.js 生成式 AI 應用開發實戰：實作 OpenAI API × LangChain × LangGraph × RAG，打造從雲端到本地 LLM 的混合式安全架構](https://ithelp.ithome.com.tw/upload/images/20260429/20150150q95EPleom3.jpg)  
> 本系列文已正式出版為《Node.js 生成式 AI 應用開發實戰：實作 OpenAI API × LangChain × LangGraph × RAG，打造從雲端到本地 LLM 的混合式安全架構》。內容全面升級，提供更完整的實戰範例與 LLM 應用架構設計。歡迎參考選購，開啟你的生成式 AI 開發之路！  
> 天瓏網路書店連結： [https://www.tenlong.com.tw/products/9786264144964](https://www.tenlong.com.tw/products/9786264144964)

- [留言](#reply)
- [追蹤](https://ithelp.ithome.com.tw/users/login)
- [檢舉](https://ithelp.ithome.com.tw/users/login)[上一篇](https://ithelp.ithome.com.tw/articles/10384662)

[

Day 21 - LangGraph 快速上手：使用圖形流程打造 AI Agent

](https://ithelp.ithome.com.tw/articles/10384662)[下一篇](https://ithelp.ithome.com.tw/articles/10386109)

[

Day 23 - 多代理系統：打造具協作能力的 AI 架構

](https://ithelp.ithome.com.tw/articles/10386109)

系列文

[用 Node.js 打造生成式 AI 應用：從 Prompt 到 Agent 開發實戰](https://ithelp.ithome.com.tw/users/20150150/ironman/8383) 共 31 篇

目錄

1. 27
	[Day 27 - LangGraph 整合實戰：打造具網路搜尋與人機互動能力的 AI 驅動寫作代理](https://ithelp.ithome.com.tw/articles/10388988)
2. 28
	[Day 28 - 認識本地 LLM 部署：為什麼要在自己的機器上跑模型？](https://ithelp.ithome.com.tw/articles/10389568)
3. 29
	[Day 29 - Ollama 快速上手：建立你的本地 LLM 環境](https://ithelp.ithome.com.tw/articles/10390521)
4. 30
	[Day 30 - LiteLLM 多模型代理：建構雲端與本地共存的 LLM 環境](https://ithelp.ithome.com.tw/articles/10391130)
5. 31
	[Day 31 - 後記：系列回顧與總結](https://ithelp.ithome.com.tw/articles/10391621)
[完整目錄](https://ithelp.ithome.com.tw/users/20150150/ironman/8383)

#### 尚未有邦友留言

 [![](https://ithelp.ithome.com.tw/storage/image/ironman18thsidebar.png) iThome鐵人賽](https://ithelp.ithome.com.tw/2026ironman?sc=iThelpR) 參賽組數

902 組

團體組數

37 組

累計文章數

19836 篇

完賽人數

528 人

[15th鐵人賽](https://ithelp.ithome.com.tw/tags/questions/15th%E9%90%B5%E4%BA%BA%E8%B3%BD) [16th鐵人賽](https://ithelp.ithome.com.tw/tags/questions/16th%E9%90%B5%E4%BA%BA%E8%B3%BD) [13th鐵人賽](https://ithelp.ithome.com.tw/tags/questions/13th%E9%90%B5%E4%BA%BA%E8%B3%BD) [14th鐵人賽](https://ithelp.ithome.com.tw/tags/questions/14th%E9%90%B5%E4%BA%BA%E8%B3%BD) [17th鐵人賽](https://ithelp.ithome.com.tw/tags/questions/17th%E9%90%B5%E4%BA%BA%E8%B3%BD) [12th鐵人賽](https://ithelp.ithome.com.tw/tags/questions/12th%E9%90%B5%E4%BA%BA%E8%B3%BD) [11th鐵人賽](https://ithelp.ithome.com.tw/tags/questions/11th%E9%90%B5%E4%BA%BA%E8%B3%BD) [鐵人賽](https://ithelp.ithome.com.tw/tags/questions/%E9%90%B5%E4%BA%BA%E8%B3%BD) [2019鐵人賽](https://ithelp.ithome.com.tw/tags/questions/2019%E9%90%B5%E4%BA%BA%E8%B3%BD) [javascript](https://ithelp.ithome.com.tw/tags/questions/javascript) [2018鐵人賽](https://ithelp.ithome.com.tw/tags/questions/2018%E9%90%B5%E4%BA%BA%E8%B3%BD) [python](https://ithelp.ithome.com.tw/tags/questions/python) [2017鐵人賽](https://ithelp.ithome.com.tw/tags/questions/2017%E9%90%B5%E4%BA%BA%E8%B3%BD) [windows](https://ithelp.ithome.com.tw/tags/questions/windows) [php](https://ithelp.ithome.com.tw/tags/questions/php) [c#](https://ithelp.ithome.com.tw/tags/questions/c%23) [linux](https://ithelp.ithome.com.tw/tags/questions/linux) [windows server](https://ithelp.ithome.com.tw/tags/questions/windows%20server) [css](https://ithelp.ithome.com.tw/tags/questions/css) [react](https://ithelp.ithome.com.tw/tags/questions/react)

- [鼎新 Workflow ERP 批次採購計畫明細表問題](https://ithelp.ithome.com.tw/questions/10220097)
- [K8s 顧問 / 平台治理經驗廠商請益](https://ithelp.ithome.com.tw/questions/10220098)
- [用AI問答方式，也是可以直接網址分享過程給別人(原來要最原始的網址才可以)](https://ithelp.ithome.com.tw/questions/10220099)

- [用AI問答方式，也是可以直接網址分享過程給別人(原來要最原始的網址才可以)](https://ithelp.ithome.com.tw/questions/10220099)

- [\[Frame & Reference Method-02\] 別再叫 AI「總結」這次對話了: 用起承轉合做對話回顧，價值差十倍](https://ithelp.ithome.com.tw/articles/10399939)
- [【案場實錄】RS485 的不歸路：為什麼 1000V DC 旁的訊號線必死無疑？（兼論 4-20mA 的老兵價值）](https://ithelp.ithome.com.tw/articles/10399941)
- [樹莓派串流機之路 - 0 開發背景](https://ithelp.ithome.com.tw/articles/10399921)
- [o11y-bench 協助你評估 LLM 到底能不能當 SRE？](https://ithelp.ithome.com.tw/articles/10399944)
- [【資安筆記】企業遭遇勒索軟體怎麼辦？從緊急隔離到系統重建的 5 階段 AI 應變指南](https://ithelp.ithome.com.tw/articles/10399961)