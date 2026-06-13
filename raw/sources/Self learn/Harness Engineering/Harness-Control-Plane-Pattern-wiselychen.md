## 先講源頭：OpenAI 的 Harness Engineering 到底是什麼？

二月初，OpenAI 工程團隊發了一篇博客： [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/) ，作者是 Ryan Lopopolo。

這篇文章講了一個極端實驗： **一個 3 人工程團隊，5 個月，產出 100 萬行代碼，0 行人寫的代碼。** 所有代碼——應用邏輯、測試、CI 配置、文檔、可觀測性、內部工具——全部由 Codex 生成。他們估計這省了 10 倍時間。

幾個關鍵數字：

- **1,500 個 PR** 在 5 個月內被開啟和合併
- **平均每個工程師每天 3.5 個 PR** ，而且隨著團隊從 3 人擴展到 7 人，吞吐量還在增加
- 單次 Codex 運行可以 **持續工作 6 小時以上** （通常在人類睡覺的時候）
- 團隊原本每週五花 20% 的時間清理「AI slop」，後來也自動化了

核心哲學是八個字： **Humans steer. Agents execute.**（人類掌舵，Agent 執行。）

而 Peter Steinberger（OpenClaw 作者）可能是這套哲學在野外最極端的見證者。有人統計了他單人單日的提交次數 Top 5：

| 日期 | Peter 單人提交次數 |
| --- | --- |
| 2 月 22 日（週日） | **627 次** |
| 2 月 16 日（週一） | 490 次 |
| 2 月 15 日（週日） | 461 次 |
| 2 月 14 日（週六） | 447 次 |
| 2 月 21 日（週六） | 315 次 |

一天只有 1,440 分鐘。627 次提交，不吃不喝不睡不上廁所，平均每 2.3 分鐘提交一次。

這當然不是人在手寫代碼。這是 **Codex + Harness 跑起來之後的真實產出** 。Peter 之前開 50 個 Codex 並行審 3,000 個 PR 已經夠誇張了，現在他的日常提交量直接證明了一件事： **當你的 repo 有足夠完善的 harness，Agent 的產出上限不是模型能力，而是你的控制平面能不能接住。**

但這篇博客最有價值的不是數字，而是他們摸索出來的一整套「怎麼讓 Agent 在 repo 裡可靠地工作」的方法論。他們把這套方法叫做 **Harness Engineering** ——不是寫代碼的工程，而是 **建構框架、約束和反饋迴路的工程** 。

具體包括幾個核心洞察：

**1\. Repository 就是系統記錄（System of Record）**

他們試過在一個大 AGENTS.md 裡塞所有指令，失敗了。原因很直白：context 是稀缺資源，什麼都「重要」等於什麼都不重要，而且大文件會瞬間過時。

最終做法是把 AGENTS.md 當 **目錄** （約 100 行），指向 `docs/` 裡的結構化知識庫。所有 Slack 討論、架構決策、設計原則，都必須沉澱到 repo 裡—— **Agent 看不到的東西，等於不存在。**

**2\. 用架構約束框住 Agent，而不是微管理實現**

他們建了嚴格的分層架構： `Types → Config → Repo → Service → Runtime → UI` ，每一層只能往前依賴，不能反向。違反了就被自動攔住。

關鍵是：這些約束用自訂 linter 和結構測試強制執行，而且 **linter 的錯誤信息裡直接嵌入了修復指令** 。Agent 犯錯的瞬間，怎麼改就已經注入 context 了。

**3\. 熵管理（Entropy Management）是持續工程**

Agent 會忠實複製 repo 裡已有的模式——包括壞的。一個反模式會在幾天內被複製到多個 module。他們的解法是定期跑背景 Codex 任務掃描偏差、更新質量評分、開重構 PR。 **像垃圾回收一樣持續清理，而不是攢到痛苦時一次性處理。**

**4\. 讓 Agent 能「看到」應用的運行狀態**

他們把應用做成每個 git worktree 可以獨立啟動，接上 Chrome DevTools Protocol，讓 Codex 可以直接截圖、操作 DOM、查 log、看 metrics。 **Agent 不只是寫代碼，還能自己跑應用、自己驗證、自己修 bug。**

---

這篇博客在社群引起了很大迴響。其中 Ryan Carson（ [@ryancarson](https://x.com/ryancarson) ）受到啟發，把 Harness Engineering 的理念落地成了一套 **具體的、可複製的 control-plane pattern** ——從 PR 開啟到 merge 的完整控制迴路。

他的目標更直白：

> “I’ve been grinding with Codex (on Extra High) through setting up our repo for Harness Engineering. The goal is to have Codex write and review 100% of the code.”

---

## 從 Harness Engineering 到 Control-Plane Pattern

OpenAI 的原文告訴你「為什麼要建框架」和「建什麼框架」，Ryan Carson 告訴你 **怎麼建** ——具體到每一個 GitHub workflow、每一行 TypeScript、每一個 edge case。

讓我一層一層拆。

---

## 第一步：一份機器可讀的 Contract

Ryan 做的第一件事，不是寫 test，不是配 CI，而是寫一份 JSON contract。

```json
{
  "version": "1",
  "riskTierRules": {
    "high": [
      "app/api/legal-chat/**",
      "lib/tools/**",
      "db/schema.ts"
    ],
    "low": ["**"]
  },
  "mergePolicy": {
    "high": {
      "requiredChecks": [
        "risk-policy-gate",
        "harness-smoke",
        "Browser Evidence",
        "CI Pipeline"
      ]
    },
    "low": {
      "requiredChecks": ["risk-policy-gate", "CI Pipeline"]
    }
  }
}
```

這份 contract 做三件事：

1. **定義風險等級** ：哪些路徑是高風險（API、資料庫 schema、工具函式），哪些是低風險
2. **定義 merge 條件** ：高風險路徑要過四道檢查，低風險只要兩道
3. **消除歧義** ：所有規則都在同一個地方，不是散落在 workflow 文件、腳本、文檔三個不同的地方

為什麼這件事重要？因為當你有 50 個 Codex 同時在跑的時候（對，就是 Peter Steinberger 那種規模），你不可能靠人去記「這個目錄改了要跑哪些 check」。規則必須是機器可讀的，而且只有一份。

**一份 contract 消除了腳本、workflow、文檔之間的 silent drift。**

---

## 第二步：Preflight Gate — 先攔，再跑

這是我覺得 Ryan 最聰明的設計之一。

傳統做法：PR 一開，CI 全部開始跑——test、build、security scan、code review 全部平行啟動。跑完再看哪些過了哪些沒過。

Ryan 的做法： **先跑 preflight gate，過了才開始跑貴的 CI。**

```typescript
const requiredChecks = computeRequiredChecks(changedFiles, riskTier);
await assertDocsDriftRules(changedFiles);
await assertRequiredChecksSuccessful(requiredChecks);

if (needsCodeReviewAgent(changedFiles, riskTier)) {
  await waitForCodeReviewCompletion({ headSha, timeoutMinutes: 20 });
  await assertNoActionableFindingsForHead(headSha);
}
```

邏輯很簡單：

1. 先看改了什麼檔案，判斷風險等級
2. 確認文檔沒有 drift
3. 如果需要 code review agent，等它跑完
4. 全部通過，才讓 test/build/security 開始跑

**省的不只是 CI 分鐘數。** 當你一天開 50 個 PR，每個 PR 跑一次完整 CI 要 15 分鐘，一天就是 750 分鐘的 CI 時間。如果 30% 的 PR 在 preflight 就被攔住，你一天省 225 分鐘。一個月省 100 多個小時。

但更重要的是： **preflight gate 強制了確定性的排序。** 先跑 policy 檢查，再跑 review，最後才跑 CI。這個順序不能亂。

---

## 第三步：SHA Discipline — Ryan 說這是最大的實戰教訓

這一段 Ryan 自己說了：

> “This was the biggest practical lesson from real PR loops.”

問題是這樣的：Code review agent 在 commit A 上跑完了，說「clean」。然後 Agent 又 push 了一個 fix commit，現在 HEAD 是 commit B。你拿 commit A 的 review 結果去決定能不能 merge commit B——這是錯的。

你用舊的「clean」證據去放行新的代碼，等於什麼都沒審。

Ryan 的規則：

- Review 狀態只在匹配當前 PR HEAD commit 時才有效
- 忽略所有綁定在舊 SHA 上的 summary comments
- 每次 push/synchronize 之後必須重跑 review
- 如果最新的 review run 不是 success 或超時，直接 fail

**這看起來是小事，但在 Agent 高頻 push 的場景下，這是你的 merge 結果是否可信的生死線。**

我自己在用 Claude Code 的時候也遇過類似的問題。Agent 修完第一輪 review 的問題後 push 了新代碼，但修復本身又引入了新問題。如果不重新跑 review，那個新問題就直接進 main 了。

---

## 第四步：Rerun Comment 的 SHA Dedupe

這是一個很實際的工程問題。

當多個 workflow 都可以觸發 review rerun 的時候，PR 底下會出現一堆重複的 bot comment。更慘的是 race condition——兩個 workflow 同時發 rerun 請求，review agent 跑了兩次，結果互相覆蓋。

Ryan 的解法很工程： **只用一個 canonical workflow 發 rerun 請求，用 marker + SHA 做 dedupe。**

```typescript
const marker = '<!-- review-agent-auto-rerun -->';
const trigger = \`sha:${headSha}\`;
const alreadyRequested = comments.some((c) =>
  c.body.includes(marker) && c.body.includes(trigger),
);

if (!alreadyRequested) {
  postComment(\`${marker}\n@review-agent please re-review\n${trigger}\`);
}
```

HTML comment 當 marker（使用者看不到），SHA 當 dedupe key。同一個 HEAD 不會發兩次 rerun。

這種東西你不會在任何架構文件裡看到。但你一跑起來就會撞到。

---

## 第五步：Automated Remediation Loop — 讓 Agent 自己修

到目前為止我們解決了「怎麼攔」和「怎麼審」。但還有一個問題：審出問題之後誰去修？

傳統答案：人。

Ryan 的答案： **讓 coding agent 讀 review context，自己 patch，自己跑 local validation，自己 push fix commit 到同一個 PR branch。**

然後 PR 的 synchronize event 觸發正常的 rerun 流程。完美閉環。

但 Ryan 加了三個 guardrail：

1. **Pin model + effort** ：固定模型版本和 effort level，保證可重現
2. **Skip stale comments** ：不理會不匹配當前 HEAD 的舊評論
3. **Never bypass policy gates** ：remediation agent 也要過所有 gate，沒有特權

**第三點是關鍵。** 如果你讓 remediation agent 繞過 policy gate，你就在控制迴路裡開了一個洞。Agent 可以用「我是在修 bug」的理由推進任何代碼。

---

## 第六步：Bot Thread 的自動 Resolve

Review bot 會開一堆 conversation thread。如果 bot 的問題已經在新的 commit 裡修好了，這些 thread 應該被自動 resolve，不然 GitHub 的 required conversation resolution 會擋住 merge。

但 Ryan 加了一個重要的條件：

- **只自動 resolve 全部是 bot comment 的 thread**
- **永遠不自動 resolve 有人類參與的 thread**

為什麼？因為人的 comment 代表了人的判斷和意圖。自動幫人 resolve 等於代替人做決策。

resolve 完之後再跑一次 policy gate，確保 conversation resolution 狀態是最新的。

---

## 第七步：Browser Evidence — 截圖不夠，要 first-class proof

UI 改動的 review 是最容易偷懶的。很多團隊的做法是「在 PR 裡貼個截圖」。

Ryan 的要求更高： **browser evidence 必須是 CI 裡的 first-class artifact，有 manifest 和 assertion。**

```bash
npm run harness:ui:capture-browser-evidence
npm run harness:ui:verify-browser-evidence
```

驗證的內容包括：

- 必要的 flow 都跑過了
- 使用了正確的 entrypoint
- 登入流程用了正確的帳號身分
- Artifact 是新鮮的、有效的

**截圖是快照，evidence 是可驗證的證據。** 這個差別在你做合規審計的時候特別明顯。

---

## 第八步：Harness Gap Loop — 把事故記憶化

最後一個，也是我覺得最容易被忽略的：

```
production regression → harness gap issue → case added → SLA tracked
```

每一個線上事故，不只是修掉就算了，而是：

1. 開一個 harness gap issue
2. 把復現條件轉成 test case
3. 加進 harness
4. 追蹤 SLA（多久修好、多久加 case）

**這確保了修復不會變成 one-off patch。** 同樣的問題不會第二次出現，而且長期的測試覆蓋率是在成長的。

---

## 完整的 Control-Plane Pattern

把上面八步串起來，就是這個完整的控制平面：

| 步驟 | 功能 | 確定性 |
| --- | --- | --- |
| 1\. Risk Contract | 定義規則，消除歧義 | 完全確定 |
| 2\. Preflight Gate | 先攔再跑，省 CI 成本 | 完全確定 |
| 3\. SHA Discipline | 只信當前 HEAD 的證據 | 完全確定 |
| 4\. Rerun Dedupe | 一個 canonical writer，不重複 | 完全確定 |
| 5\. Remediation Loop | Agent 自己修，不繞過 gate | 半確定（model 是非確定性的） |
| 6\. Bot Thread Resolve | 自動清理 bot thread，不碰人的 | 完全確定 |
| 7\. Browser Evidence | UI 證據是 CI artifact | 完全確定 |
| 8\. Harness Gap Loop | 事故轉 test case | 完全確定 |

注意到了嗎？ **8 步裡面有 7 步是完全確定性的。** 只有 remediation loop 裡面有 LLM 參與，其他全部是機器可以 pass/fail 的邏輯。

這跟我之前寫的四層防禦觀點完全一致： **用確定性的工具，框住不確定性的 AI。**

---

## 跟上次的四層防禦是什麼關係？

上次的四層防禦（Test → Lint → CI Gate → LLM Judge）是 **垂直的** ——每一層往下更深入地檢查一個 PR。

Ryan 的 control-plane pattern 是 **水平的** ——從 PR 開啟到 merge 的完整生命週期。

兩者不衝突，反而是互補的。四層防禦是 control-plane 裡面的一個組件，具體來說就是 Step 2 Preflight Gate 和 Step 5 Remediation Loop 裡面跑的東西。

把兩個放在一起看：

```
PR 開啟
  │
  ├── Step 1: Risk Contract → 判斷風險等級
  ├── Step 2: Preflight Gate
  │     ├── Layer 1: Test
  │     ├── Layer 2: Lint + Type Check
  │     ├── Layer 3: CI Gate (coverage, security)
  │     └── Layer 4: LLM Judge (code review agent)
  ├── Step 3: SHA Discipline → 確認證據匹配當前 HEAD
  ├── Step 4: Rerun Dedupe → 避免重複 rerun
  ├── Step 5: Remediation Loop → Agent 自修 → 回到 Step 2
  ├── Step 6: Bot Thread Resolve → 清理已修復的 thread
  ├── Step 7: Browser Evidence → UI 證據驗證
  ├── Step 8: Harness Gap Loop → 事故轉 test case
  │
  └── Merge
```

**這就是一個完整的、可以讓 Agent 寫 + 審 + 修代碼的 repo 架構。**

---

## 通用模式 vs. 具體實作

Ryan 特別強調這是一個 **通用模式** ，不是某個特定工具鏈。

| 通用概念 | Ryan 的具體實作 |
| --- | --- |
| Code Review Agent | Greptile |
| Remediation Agent | Codex Action |
| Canonical Rerun Workflow | `greptile-rerun.yml` |
| Stale Thread Cleanup | `greptile-auto-resolve-threads.yml` |
| Preflight Policy | `risk-policy-gate.yml` |

你可以把 Greptile 換成 CodeRabbit、CodeQL、自建的 LLM review。你可以把 Codex 換成 Claude Code、Cursor、Devin。 **Control-plane 的語義不變，只是換接入點。**

這也是為什麼我覺得這篇值得單獨寫——它不是在推銷某個工具，而是在定義一個架構模式。

---

## 跟我自己的實戰經驗對照

我在〈Make CI/CD Great Again〉裡分享過用三個 Agent 做多角色 code review 的經驗。現在用 Ryan 的框架回頭看，我當時缺了什麼？

1. **沒有 Risk Contract。** 我的 review 對所有檔案一視同仁。但實際上 `db/schema.ts` 和 `README.md` 的風險等級差 10 倍。
2. **沒有 SHA Discipline。** 我的 Agent 修完問題 push 新 commit 後，我沒有強制重跑 review。靠的是人眼去判斷「修好了」。
3. **沒有 Remediation Loop。** Review 發現問題後是我自己去修，或者重新 prompt Agent。沒有自動化的修 → 重審迴路。
4. **沒有 Harness Gap Loop。** 上線出問題就修掉，沒有系統性地轉成 test case。

用百分比來量化的話，Ryan 的八步我當時做到了大概 40%——有 Test、有 Lint、有 CI Gate、有 LLM Judge，但控制平面的另外四步（contract、SHA、dedupe、remediation loop）完全缺失。

**這就是「能跑」和「能 scale」的差距。**

---

## 工具推薦：搭建 Control-Plane 你需要什麼？

整套 Harness Engineering 涉及的技術工具可以分為四大類。重點是： **這是一個通用模式，每一類都可以換成你熟悉的替代品。**

### 1\. AI 模型與 Agent

這是產出代碼和修復代碼的「引擎」：

- **OpenAI Codex** ：Ryan 和 OpenAI 團隊的主力工具，支援長時間自主運行（單次可跑 6 小時以上）
- **Claude Code** ：我自己在用的工具，適合需要深度理解 codebase context 的場景
- 其他選項：Cursor、Devin、Windsurf 等，只要能接 PR workflow 都可以

### 2\. 自動化程式碼審查

Control-Plane 裡的「LLM Judge」角色：

- **Greptile** ：Ryan 具體實作中使用的 code review agent，能理解 codebase 語義
- **CodeRabbit** ：另一個主流選項，我在〈Make CI/CD Great Again〉裡用過
- **CodeQL** ：GitHub 原生的靜態分析工具，偏向安全漏洞檢測
- **自建 LLM Review** ：用 GPT-4 / Claude 包一層 review prompt，彈性最大但維護成本也最高

### 3\. CI/CD 與基礎架構控制平面

這是接住 AI 產出的「防護網」本體，主要依賴 GitHub 生態系與自動化腳本：

- **GitHub Actions** ：整個控制平面的執行環境。文中提到的具體 Workflow 包含：
	- `risk-policy-gate.yml` （Preflight 預檢閘門）
		- `greptile-rerun.yml` （處理重複觸發的 Dedupe 機制）
		- `greptile-auto-resolve-threads.yml` （自動清理 Bot 留言）
- **JSON Contract** ：用來撰寫機器可讀的 Risk Contract，定義哪些目錄（如 `db/schema.ts` ）需要更嚴格的防線
- **TypeScript** ：用於撰寫自訂的預檢邏輯（Preflight Gate）與去重邏輯（Marker + SHA Dedupe）
- **Git 原生機制** ：深度依賴 PR 的 `synchronize` 事件、HEAD Commit 的 SHA 追蹤，以及隱藏的 HTML Comment（ `<!-- marker -->` ）來做狀態管理

### 4\. 應用程式運行與 UI 驗證工具

為了解決「Agent 看不到運行狀態」的問題，讓 AI 能自己驗證：

- **Chrome DevTools Protocol (CDP)** ：OpenAI 團隊將應用程式接上 CDP，讓 Codex 可以直接操作 DOM、查 Log、看 Metrics 並截圖
- **npm scripts** ：用於產生 Browser Evidence，例如 `npm run harness:ui:capture-browser-evidence` 和 `npm run harness:ui:verify-browser-evidence`
- **Git Worktree** ：讓每個 Agent 跑在獨立的 worktree 裡，互不干擾地啟動應用、跑測試

### 最低可行工具組合

如果你是 2-3 人的小團隊，不需要全部到位。我的建議是先從這三樣開始：

| 優先級 | 工具 | 成本 | 對應步驟 |
| --- | --- | --- | --- |
| P0 | JSON Risk Contract + GitHub Actions | 免費 | Step 1, 2 |
| P0 | Git SHA 追蹤腳本 | 免費 | Step 3, 4 |
| P1 | CodeRabbit 或 Greptile | $19-49/月 | Step 2 Layer 4 |
| P2 | Codex 或 Claude Code | 按用量計費 | Step 5 |

**前兩項是純紀律問題，零成本，立即可做。** 後兩項視團隊規模和預算決定。

---

## 坦白說

Ryan 的這套架構很完整，但我有幾個實際操作上的疑問還沒想通：

**比較確定的：**

1. **Risk Contract 是必須的。** 不管你的 repo 多小，把風險等級寫下來、把 merge 條件寫下來，這件事的 ROI 極高。一份 JSON 就能省掉無數次「這個 PR 要不要 review」的爭論。
2. **SHA Discipline 是非妥協的。** 我之前因為偷懶沒做這件事，結果一個 Agent 的 fix commit 引入的 bug 直接進了 main。教訓很痛。
3. **Preflight Gate 省的錢是真的。** 我粗算了一下，如果我們的 repo 有 preflight gate，上個月可以省大約 30% 的 CI 費用。

**不太確定的：**

1. **Remediation Loop 的收斂性。** Agent 修完 → review 又發現問題 → Agent 再修 → review 又發現問題……這個 loop 什麼時候停？Ryan 沒提到 max retry 或 circuit breaker。在我的經驗裡，LLM 修復本身會引入新問題（我之前那篇寫過「修完跑第二輪又冒出兩個高危」），無限 loop 是真實風險。
2. **小團隊的成本效益。** Ryan 在 OpenAI，資源充足。但 2-3 人的 startup 要搭這整套，光 Greptile + Codex + CI 的月費就不少。八步是不是都要做？還是可以挑重點？我的建議是先做 1（contract）、2（preflight）、3（SHA discipline），這三步幾乎零成本，純粹是紀律。
3. **Browser Evidence 的泛用性。** 如果你的產品不是 Web UI，而是 API 或 CLI，browser evidence 要換成什麼？API response assertion？CLI output snapshot？這部分 Ryan 沒展開。

---

## 不是結論

上次我說「Make CI/CD Great Again」不是口號。Ryan Carson 用他的 repo 證明了下一句：

**CI/CD 不只是要 Great Again，它要變成一個完整的控制平面。**

從 risk contract 到 harness gap loop，從 preflight gate 到 remediation loop——這套架構讓 Agent 不只是「能寫代碼」，而是「能被 repo 安全地接住」。

你的 repo 有多完善的控制平面，決定了你能讓 Agent 跑多快。

沒有 SHA discipline 的 repo 讓 Agent 跑，等於讓一台沒有 ABS 的車跑 200 公里——不是不能跑，是遲早要出事。

---

**延伸閱讀：**

- [當代碼量暴增 10 倍後，到底誰來做 Review？Make CI/CD Great Again](https://ai-coding.wiselychen.com/coders-who-stopped-coding-harness-context-spec-engineering/)
- [三個月 63 萬行之後：在 AI Coding 時代，工程師真正的價值是什麼？](https://ai-coding.wiselychen.com/claude-code-630k-lines-three-months-reflection/)
- [AI Coding 半年回顧：開發並沒有變快，我們只是把瓶頸從寫 Code，轉移到了 QA 跟需求收集](https://ai-coding.wiselychen.com/ai-coding-half-year-review-demand-transformation-tool-evolution/)
- [AI Coding 工具的資安風險：當 Prompt Injection 遇上 RCE](https://ai-coding.wiselychen.com/ai-coding-tool-security-risk-prompt-injection-rce/)