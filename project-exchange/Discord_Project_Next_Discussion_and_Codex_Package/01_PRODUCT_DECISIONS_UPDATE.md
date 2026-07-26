# Discord 微積分模組教學優化專案
## 產品決策更新

本文件整理目前已確認的產品方向，供後續 Codex、ChatGPT 與人工討論共同使用。若與舊 handoff 衝突，以本文件較新的決策為準；未列入者仍視為未決。

## 1. 平台責任邊界

### NTU COOL

NTU COOL 仍是正式課務依據，負責教材、作業、成績、截止日期、正式公告與課程政策。

### Discord

Discord 是補充性的討論與協作空間，負責學生提問、TA／教師回覆、Forum posts 與 threads、資源整合、Private Support，以及不錄音、不自動轉錄的語音 office hour。

### 入口網站

入口網站是 Discord 的低門檻替代入口與中介層，負責加入與設定、OAuth 綁定、Email 驗證、身分與班級設定、規則與資料分析選項、代為發問、依案號查詢、查看文字回覆與進度、Private Support 入口、使用指南、系統狀態與 NTU Mail 退路。

學生仍可直接進 Discord 使用；網站代為發問不是強制流程。

## 2. 案號格式

一般案件：

```text
C12-7K4M2Q-0907-2007
```

Private Support：

```text
C12-7K4M2Q-0907-2007-P
```

欄位語意：

- `C12`：班級代碼。
- `C99`：不屬於標準班級或特殊身份。
- `7K4M2Q`：系統隨機生成的案件 token。
- `0907-2007`：建立日期與時間，格式為月日－時分。
- 尾端 `P`：Private Support。
- 內部仍可另有 UUID、Discord thread ID 或 database primary key。

隨機 token 不使用學生姓名、學號、Email 或 Discord ID 衍生。

查詢成功後可顯示遮罩：

```text
C12-7K****-0907-2007
```

即使遮罩後撞號，也加入簡單辨識機制，例如保留更多 token 字元、顯示短校驗碼，或在同頁有多筆結果時增加辨識尾碼。Production 原則採 one-case-at-a-time lookup，不提供未驗證的 list-all-cases。

## 3. 網頁案件查詢畫面

第一版以桌面瀏覽器為主，採 reduced screen，不重新製作完整 Discord client。

建議顯示：

```text
Case
Status
Last Update
Last Response
Last Read（若可可靠判定）
Latest Teaching Response
Timeline
Text Conversation
Attachment Markers
Discord Deep Link
Close Case
Add Follow-up
```

### Last Update

任何案件變化，包括學生補充、TA／教師回覆、狀態改變、結案與重新開啟。

### Last Response

最後一次教學團隊的文字回覆時間。

### Timeline

```text
09/07 20:07  Submitted
09/07 20:18  TA responded
09/07 20:30  Student follow-up
09/08 09:10  Answered
```

## 4. 文字與附件

Bot 可增量同步案件文字與事件摘要。第一版不下載、不代理、不重新託管 Discord 附件。

Discord：

```text
Student:
老師好，我想請教這題。[附件]

TA:
收到了，這題解法如下。[附件]
如果還有問題可以再詢問。
```

網頁：

```text
Student:
老師好，我想請教這題。
[此訊息包含附件，請至 Discord 查看]

TA:
收到了，這題解法如下。
[此訊息包含附件，請至 Discord 查看]
如果還有問題可以再詢問。
```

## 5. 同步與效能原則

不做全 server 定時輪詢，也不每幾分鐘重新抓所有 threads。

```text
Discord Gateway event
→ bot 判定案件發生變更
→ 加入 changed-case queue
→ 每 1–5 分鐘批次寫入有變更的案件 projection
→ 網頁只讀 projection
```

另設：

- Active case 漏事件校正：15–60 分鐘一次。
- 完整 dump／教學分析／封存：每週一次。
- 網頁查詢優先讀 working data，不臨時重新演算整段歷史。
- 必要時提供「重新整理」按鈕，針對單一案件 on-demand fetch。

## 6. 結案機制

案件至少支援：

```text
OPEN
ANSWERED
TEMPORARILY_CLOSED
CLOSED
REOPENED
```

手動結案：

```text
closure_source = MANUAL
```

自動結案建議：

- 已確認讀取最新回覆，3 天未更新：暫結案。
- 暫結案後累計 7 天未更新：自動結案。
- 關閉後出現新回覆或補充：重新開啟。

```text
closure_source = AUTO
```

是否能判定「已讀」仍是未決。Discord auto-archive 只負責將 inactive thread 收起，不等同產品層結案。

## 7. AI 輔助教學分析

發文時使用強制二選一，不使用預先勾選 checkbox：

```text
是否允許 AI 輔助教學分析？
○ Yes
○ No
```

建議說明：

> 允許系統在去識別化與人工複核後，使用 AI 分析本案件內容，以改善教學與整理常見問題。選擇 No 不影響提問與回覆；教學團隊仍可基於課程運作需要閱讀及保存案件紀錄。

Original poster 主導案件層級：

- OP 選 No：整案不得進入 AI 分析 pipeline。
- OP 選 Yes：案件具備基本資格。
- 其他參與者訊息仍依作者設定或教學團隊規則處理。
- Database 欄位是 source of truth。

Discord 可用 Forum tag 或標題前綴 `AI✓`／`AI×`，但不能只靠標題。

## 8. Bot 分工

### `course_assistant`

- 加入與設定
- nickname／roles
- 建立 Forum post
- 代為發文
- Modal 回覆
- Private Support
- 案件狀態更新

### `dump_bot`

原 `archive_reader` 可整合為 `dump_bot`：

- read-only structure inventory
- 指定 thread fetch
- `/dump`
- `/follow`
- active-case reconciliation
- weekly export
- 112／113／114 舊 server 結構盤點

## 9. Working data 與 archive data

Google Sheets working data 優先保存 Users、Classes、ActiveCases、CaseProjection、Consent、Status、Last Update、Last Response、latest response excerpt、附件標記、Discord thread ID、archive pointer 與 audit summary。

結案後完整內容可整理為 JSON、Markdown、sanitized export、attachment manifest 與 analysis report。

使用 Google Sheets／Google Drive／本機儲存的最終分工仍待驗證。目標是：線上查詢快速、Active data 小而明確、Long-term archive 不拖慢 working sheet、每週維護可重建索引。

## 10. 固定事項

- 不錄音。
- 不自動語音轉錄。
- 不做全 server continuous polling。
- 不自動將所有內容送入 LLM。
- Private Support 與一般案件分流。
- 第一版網站以桌面版 review 為主。
- GitHub Pages 只作靜態入口；真實案件不預先 build 成公開靜態頁。
- Bot token、OAuth secrets、Email secrets 不得提交 Git 或貼進聊天。
