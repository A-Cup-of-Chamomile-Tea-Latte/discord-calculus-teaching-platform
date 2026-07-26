# `dump_bot`：112／113／114 舊伺服器結構盤點
## 前置手動作業與 Codex 執行指令

本任務分成兩部分：

1. **你先完成的手動作業**：把 `dump_bot` 安全地加入三個舊伺服器，並提供最低限度的唯讀權限。
2. **Codex 執行的程式工作**：建立真正的唯讀盤點功能，抓取伺服器結構並產生三年比較報告。

本輪只做「結構盤點」，不讀取訊息正文、不下載附件、不列出成員、不做語氣分析，也不修改任何 Discord 設定。

---

# 第一部分：你要先完成的手動作業

## 1. 先確認你是否有權加入機器人

一般 Discord 邀請連結只能讓**一般使用者帳號**加入伺服器，不能讓機器人自動取得存取權。

要把 `dump_bot` 加入 112、113、114 伺服器，你必須符合其中一項：

- 你是伺服器擁有者；
- 你有「管理伺服器」權限；
- 伺服器擁有者或管理員願意代為安裝 `dump_bot`。

若你只是一般成員，必須請原管理員協助。不要嘗試使用個人帳號權杖或其他非官方方式繞過權限。

### 待填

```text
112 伺服器：我是否可管理？  Yes / No / Unknown
113 伺服器：我是否可管理？  Yes / No / Unknown
114 伺服器：我是否可管理？  Yes / No / Unknown
```

---

## 2. 建立或確認 `dump_bot`

若 Developer Portal 中已建立 `dump_bot`，直接沿用，不要重複建立。

建議測試用名稱：

```text
calculus-dump-bot-dev
```

本任務使用一隻 `dump_bot` 即可，不必每年建立一隻。

---

## 3. 不開啟不需要的特殊資料權限

本輪只盤點結構，不需要：

- 成員清單特殊權限；
- 在線狀態特殊權限；
- 訊息內容特殊權限。

因此 Developer Portal 中以下項目先保持關閉：

```text
SERVER MEMBERS INTENT
PRESENCE INTENT
MESSAGE CONTENT INTENT
```

本輪也不讀取：

- 訊息正文；
- 附件；
- 投票內容；
- 成員姓名；
- 成員加入時間；
- 私人討論串內容。

---

## 4. 產生 `dump_bot` 安裝連結

安裝方式使用伺服器安裝。必要範圍是：

```text
bot
```

若 Developer Portal 的預設安裝設定同時保留 `applications.commands`，可以保留，但本任務不得註冊或使用任何 slash command。

### 最低權限

對要盤點的公開課程區域，給予：

```text
View Channels
Read Message History
```

不要給：

```text
Administrator
Manage Server
Manage Channels
Manage Roles
Manage Threads
Kick Members
Ban Members
View Audit Log
Manage Webhooks
```

### 為何需要 `Read Message History`

本輪不讀訊息正文，但要統計公開封存討論串。Discord 對「列出公開封存討論串」要求 `Read Message History`。

### 私人區域

若不希望本輪盤點：

- 助教內部區；
- 教師內部區；
- 私人支援區；
- 個人案件區；

請不要讓 `dump_bot` 看見它們。

本輪不應為了盤點私人討論串而給 `Manage Threads`。

---

## 5. 將 `dump_bot` 加入三個伺服器

分別使用機器人安裝連結加入：

- 112 預備微積分伺服器
- 113 預備微積分伺服器
- 114 預備微積分伺服器

加入後確認：

1. 成員列表中看得到 `dump_bot`。
2. `dump_bot` 身份組沒有管理權限。
3. 它可以看到需要盤點的課程分類與頻道。
4. 它看不到不希望盤點的私人區域。
5. 不要把 bot 身份組拖到管理員或助教身份組上方。

---

## 6. 開啟 Developer Mode 並複製三個伺服器 ID

Discord：

```text
User Settings
→ Advanced
→ Developer Mode
```

然後對伺服器名稱按右鍵，選擇：

```text
Copy Server ID
```

記錄：

```text
DISCORD_GUILD_112_ID=
DISCORD_GUILD_113_ID=
DISCORD_GUILD_114_ID=
```

伺服器 ID 不是密碼，但不必放進公開報告。

---

## 7. 將權杖與伺服器 ID 放入本機 `.env`

只在本機設定，不放進 Markdown、Git、Google Sheets 或聊天。

範例：

```text
DUMP_BOT_TOKEN=只放本機
DISCORD_GUILD_112_ID=純數字
DISCORD_GUILD_113_ID=純數字
DISCORD_GUILD_114_ID=純數字
```

確認：

- `.env` 已在 `.gitignore`；
- `git status` 不會顯示 `.env`；
- 終端輸出不會印出權杖；
- 不把 `.env` 打進交接 ZIP。

若權杖曾出現在聊天、截圖或 Git，立即到 Developer Portal 重設。

---

## 8. 建立私人輸出資料夾

在專案根目錄建立：

```text
.private/discord-inventory/
```

並確認 `.gitignore` 排除：

```text
.private/
```

原始伺服器 ID、頻道 ID、身份組 ID 與完整權限資料只能放在這裡，不直接提交 Git。

---

## 9. 手動作業完成條件

交給 Codex 前，應具備：

```text
[ ] `dump_bot` Application 已存在
[ ] `dump_bot` 已加入 112
[ ] `dump_bot` 已加入 113
[ ] `dump_bot` 已加入 114
[ ] 只給 View Channels + Read Message History
[ ] 沒有 Administrator
[ ] 沒有 Manage Channels / Roles / Threads
[ ] 三個 Server ID 已放進本機 `.env`
[ ] Bot token 已放進本機 `.env`
[ ] `.env` 與 `.private/` 均不會進 Git
[ ] 已確認哪些私人區域不在盤點範圍
```

若其中任何一個舊伺服器無法加入 bot，Codex 仍可先處理能存取的伺服器，但報告必須明確標示缺少哪一年。

---

# 第二部分：交給 Codex 的執行指令

以下內容可直接交給 Codex。

---

# Task 35 — `dump_bot` 舊伺服器唯讀結構盤點

## 目標

在既有 Discord 微積分模組教學優化專案中，為 `dump_bot` 建立真正的 Discord 唯讀結構盤點功能，並盤點 112、113、114 三個舊伺服器。

本任務有兩個目的：

1. 取得三年伺服器的結構資料，供後續伺服器設計討論使用。
2. 驗證 `dump_bot` 在真實 Discord 伺服器中的最低權限、唯讀連線、分頁、錯誤處理與輸出能力。

本任務只讀取結構，不讀取訊息正文或成員資料。

---

## 一、執行前先閱讀

請先閱讀：

- `PROJECT_DEFAULTS.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `docs/NEXT_STEPS.md`
- `docs/decisions/UNRESOLVED.md`
- `bots/dump_bot/`
- `bots/archive_reader/`
- `contracts/`
- Task 34 報告與現有結構盤點 fixture
- 本文件

不得重做既有架構，不得自行擴大資料範圍。

---

## 二、嚴格的唯讀邊界

### 允許的 Discord HTTP 方法

只允許：

```text
GET
```

### 禁止

禁止任何：

```text
POST
PUT
PATCH
DELETE
```

禁止：

- 建立或修改頻道；
- 建立或修改身份組；
- 建立討論串；
- 發送訊息；
- 註冊 slash command；
- 修改暱稱；
- 加入成員；
- 變更權限；
- 解封存討論串；
- 讀取邀請與稽核紀錄；
- 讀取訊息正文；
- 下載附件；
- 列出全部成員；
- 讀取私人訊息；
- 讀取私人討論串；
- 使用使用者帳號權杖。

### 實作要求

建立明確的 `ReadOnlyDiscordInventoryClient` 或同等邊界：

- 只允許預先列入清單的 GET 路徑；
- 遇到任何非 GET 請求立即拒絕；
- 不在 log 中輸出 bot token；
- 只允許設定檔列出的三個伺服器 ID；
- 遇到未知伺服器 ID 立即停止；
- 不註冊 Discord 應用程式指令；
- 不依賴常駐 Gateway 連線；
- 以一次性本機命令完成盤點。

優先使用 Discord HTTP API 的唯讀端點，而不是為此啟動長時間運作的 bot。

---

## 三、允許讀取的資料

### 1. 伺服器摘要

可讀取：

- 伺服器名稱；
- 伺服器 ID（只留在私人原始輸出）；
- 伺服器功能；
- 驗證等級；
- 預設通知設定；
- 媒體內容篩選等級；
- 是否啟用社群功能；
- 近似成員數或 API 可安全取得的成員總數；
- 伺服器偏好語言；
- 系統頻道、規則頻道是否存在。

不得輸出擁有者帳號資訊。

### 2. 分類與頻道

每個分類／頻道可讀取：

- 私人原始 ID；
- 脫敏後的穩定代碼；
- 名稱；
- 類型；
- 排列位置；
- 上層分類；
- 主題；
- 是否限制級；
- 慢速模式；
- 預設自動封存時間；
- Forum 排序方式；
- Forum 顯示方式；
- Forum 可用標籤；
- 頻道級權限覆寫；
- 是否對 `dump_bot` 可見。

### 3. 身份組

可讀取：

- 私人原始 ID；
- 名稱；
- 排列位置；
- 權限位元；
- 顏色；
- 是否可被提及；
- 是否由整合或 bot 管理；
- 若 API 可安全取得，身份組成員數。

不得列出任何具有該身份組的成員姓名或帳號。

### 4. 討論串

可讀取：

- 伺服器目前可見的 active thread 數量；
- 各公開文字／公告／Forum 頻道的公開封存討論串數量；
- 討論串名稱；
- 上層頻道；
- 建立或封存時間；
- 自動封存時間；
- 是否鎖定；
- 訊息數量等 Discord 直接提供的結構計數。

不得讀取：

- 訊息正文；
- 作者；
- 附件；
- 投票；
- 討論串成員名單；
- 私人討論串。

### 5. Bot／整合痕跡

只能使用：

- managed role；
- role tag；
- 其他不需要成員清單或管理伺服器權限的安全資料。

不得為了列出 integrations 而要求 `Manage Server`。

---

## 四、不需要的特殊資料權限

本任務不得要求或啟用：

```text
GUILD_MEMBERS / SERVER MEMBERS INTENT
GUILD_PRESENCES / PRESENCE INTENT
MESSAGE_CONTENT INTENT
```

若現有程式意外要求其中任何一項，應先修正為不需要，再繼續。

---

## 五、輸出目錄

### 私人原始輸出

不得提交 Git：

```text
.private/discord-inventory/
├── 112/
│   ├── server.json
│   ├── channels.json
│   ├── roles.json
│   ├── threads.json
│   └── inventory-manifest.json
├── 113/
│   └── ...
└── 114/
    └── ...
```

私人輸出可保留 Discord ID，但不得保留 token。

檔案權限應盡量限制為目前使用者可讀。

### 可分享的脫敏輸出

可放入：

```text
docs/reports/discord-inventory/
├── 112-structure-summary.md
├── 113-structure-summary.md
├── 114-structure-summary.md
├── three-year-structure-comparison.md
├── inventory-limitations.md
└── sanitized-structure-data.json
```

脫敏輸出要求：

- 移除伺服器 ID；
- 移除頻道 ID；
- 移除身份組 ID；
- 移除使用者覆寫中的 member ID；
- 不含成員資料；
- 不含訊息；
- 不含附件；
- 不含邀請；
- 不含 token；
- 不含私人討論串。

名稱可以保留，因為本任務的目的就是分析伺服器結構；若名稱包含真實姓名，應改成穩定代號並記錄在私人映射中。

---

## 六、三年比較報告

`three-year-structure-comparison.md` 至少比較：

### 1. 整體規模

- 分類數量；
- 文字頻道數；
- Forum 數；
- 語音頻道數；
- 公告頻道數；
- 身份組數；
- 公開 active threads；
- 公開 archived threads。

### 2. 資訊架構

- 頻道樹深度；
- 是否容易找到提問入口；
- 是否有明確規則區；
- 是否有資源分享區；
- 是否有助教或教師內部區；
- 是否有系統或機器人操作區；
- 是否大量使用分班頻道。

### 3. Forum 設定

- 是否使用 Forum；
- 標籤數量與用途；
- 預設排序；
- 預設顯示；
- 自動封存時間；
- 慢速模式；
- 是否有狀態標籤。

### 4. 權限結構

- 身份組層級；
- 哪些區域依角色隔離；
- 權限覆寫複雜度；
- 是否存在大量個人層級覆寫；
- 是否有難以維護的重複設定。

不要判斷個別使用者，不要分析誰活躍或誰沒有回答。

### 5. 設計建議

分成：

- 值得沿用；
- 應避免；
- 需要人工查看；
- API 無法判定；
- 下一階段若要分析活動，需要新增哪些最低資料。

---

## 七、錯誤與限制處理

遇到以下情況不得偷偷忽略：

- 某個伺服器沒有存取權；
- 某個分類不可見；
- 缺少 `Read Message History`；
- 封存討論串分頁失敗；
- API 限流；
- member-specific 權限覆寫；
- 頻道名稱含疑似個資；
- 結構資料不完整；
- Discord API 回傳未知類型。

報告必須列出：

```text
COMPLETE
PARTIAL
NOT ACCESSIBLE
SKIPPED_BY_POLICY
```

不得將「不可見」解讀為「不存在」。

---

## 八、測試

新增測試：

1. 只允許 GET。
2. 未列入清單的 GET 路徑被拒絕。
3. 非白名單伺服器 ID 被拒絕。
4. Token 不會出現在 log 或輸出。
5. 不需要特殊成員權限。
6. 不需要訊息內容權限。
7. 不讀 message endpoint。
8. 公開封存討論串正確分頁。
9. 限流後 bounded retry。
10. 私人討論串被跳過。
11. member-level overwrite 正確脫敏。
12. 原始輸出不進 Git。
13. 可分享報告不含 Discord IDs。
14. 三年其中一年失敗時，仍能產生標明缺失的部分比較報告。
15. 重複執行時輸出穩定，並產生 manifest hash。

---

## 九、執行階段

### 階段 A：離線測試

- 使用 fixtures；
- 全部測試通過；
- 產生示範報告；
- 不讀真實 Discord。

### 階段 B：單一伺服器預檢

先只測試 112：

- 驗證 token；
- 驗證伺服器白名單；
- 驗證唯讀端點；
- 顯示將讀取的資料類型；
- 不輸出訊息或成員；
- 產生 112 結構報告。

若發現權限過大、資料超出範圍或任何寫入行為，立即停止。

### 階段 C：三年盤點

112 預檢通過後，才依序執行：

```text
112
113
114
```

然後產生三年比較報告。

---

## 十、禁止自動執行的後續工作

本任務完成後停止，不得自行開始：

- 讀取訊息正文；
- 活躍度分析；
- 回覆時間分析；
- 語氣分析；
- 去識別化對話樣本；
- 成員角色映射；
- 將舊資料寫入 Google Sheets；
- LLM 分析；
- 新伺服器 provisioning；
- 修改舊伺服器。

---

## 十一、最終回報

建立：

```text
docs/reports/TASK-35-DISCORD-STRUCTURE-INVENTORY-REPORT.md
```

內容包括：

1. 實作內容。
2. 使用的唯讀端點。
3. 實際需要的 Discord 權限。
4. 是否使用任何特殊資料權限。
5. 112／113／114 各自結果。
6. 不可見或未完成部分。
7. 測試與檢查結果。
8. 私人原始輸出位置。
9. 可分享報告位置。
10. 三年結構差異摘要。
11. 發現的 `dump_bot` 問題。
12. 下一階段建議。
13. 可直接貼回 ChatGPT 的繁體中文摘要。

不得把 token、完整 `.env` 或私人原始 Discord ID 貼入報告。

完成後停止，等待人工審核。
