# Discord Bot 支線整合回主線報告

日期：2026-07-29
來源套件：`discord-course-bots-handoff-2026-07-29.zip`
用途：供「Discord 微積分模組教學優化專案」主線審核、更新 Project Knowledge，並安排受控程式遷移。

> 本報告以「已定案產品規格」「目前程式實作」「Discord 實機測試結果」三者分開判定。
> `已選定方向` 不等於 `已實作`；`測試伺服器可運作` 也不等於 `production ready`。

---

## 0. 整合結論

本支線已達成原本最重要的技術目的：兩隻 Bot 已在空測試伺服器完成首次真實整合，Public Forum 與 Private Support 均已產生有意義的實機結果。

### 可以正式寫回主線的結論

✅ 正式 Bot 維持兩隻：

- `course_assistant`：Discord 互動、案件狀態與必要寫入。
- `dump_bot`：指定範圍唯讀抓取、匯出與完整性驗證。

✅ Public Forum 已完成可操作的測試切片：

- 新文章建立草稿。
- 原作者設定關鍵字與 AI Yes／No。
- 成案、標題前綴、初始快照、案號與 Discord 私訊。
- Staff 手動結案。
- 同一 thread、同一案號的 reopen。
- reopen 邏輯錯誤已修正；輪次可依序為 `2`、`3`、`4`，無上限。

✅ Private Support 已完成並實測完整成功閉環：

```text
/private open
→ 建立單案私人頻道
→ /private close
→ 單頻道授予 dump_bot 唯讀權限
→ Staff 確認匯出並刪除
→ 建立持久 dump job
→ dump_bot 匯出 JSON／Markdown／manifest
→ 重新驗證 SHA-256
→ course_assistant 刪除頻道
→ SQLite 收斂為 DELETED
```

✅ 案號規格已固定並實作：

```text
Public:  C00-XXXXXX-MMDD-HHMM
Private: C00-XXXXXX-MMDD-HHMM-P
```

- `XXXXXX` 為六碼大寫英數字。
- 使用 `secrets.choice`。
- 時間使用 `Asia/Taipei`。
- Public 不得有 `-P`；Private 才加 `-P`。
- 發生唯一性碰撞時最多重試五次。

⚠️ 目前仍不適合直接宣告正式可上線。最主要未完成項目為：

1. 24＋24 與 48＋48 排程的正式可靠性設計。
2. Discord API `429`、逾時與 SQLite／Discord 跨系統一致性。
3. Public 每週批次 dump 與持久 queue。
4. Private failure path、重試、撤權與管理者通知的完整測試。
5. 目前 bootstrap 文件與程式現況不同步。
6. 身份同步、Portal、Email fallback 與正式部署仍未接通。

---

## 1. 本次審查範圍

### 1.1 已檢視內容

- `GPT_ONLINE_HANDOFF_2026-07-29.md`
- `INTEGRATION_REPORT_2026-07-29.md`
- `README.md`
- `docs/*.md`
- `src/discord_course_bots/**`
- `tests/**`
- `Makefile`、dependency files、`.env.example`、`.gitignore`
- 本支線的 Discord 實測紀錄與使用者確認

### 1.2 驗證限制

- 交接 ZIP 不含 `.env`、token、SQLite 與 `exports/`，這是正確的安全處置。
- 本審查環境已完成 Python syntax compile 檢查。
- 交接報告記載完整測試為 `25 passed`；原始碼含 21 個 test function，另有參數化案例。
- 本審查環境無法從套件來源安裝 `discord.py==2.7.1`，因此未獨立重跑 pytest；`25 passed` 應視為支線環境的已回報結果，而非本審查環境的第二次重現。
- 真實 Private 成功閉環由交接報告與使用者實測確認；ZIP 本身不含 Discord 外部狀態或匯出資料，不能只靠 ZIP 重現該證據。

---

## 2. 產品決策：應寫回主線

## 2.1 Bot 身分與邊界

| 內部名稱 | Discord 名稱 | 功能邊界 |
|---|---|---|
| `course_assistant` | `DC-Calculus-Manager` | 學生互動、案件狀態、Private 頻道與必要 Discord 寫入 |
| `dump_bot` | `DC-Calculus-Archive` | 指定頻道唯讀匯出、manifest 與 checksum 驗證 |

固定原則：

- `dump_bot` 不管理或刪除頻道。
- Private 頻道的最終刪除由 `course_assistant` 執行。
- `dump_bot` 平時不可見 Private Support；只在單案結案後取得該頻道臨時唯讀權限。
- 不建立第三隻 `archive_reader`；該名稱只能視為舊相容名稱。

## 2.2 Public 案件生命週期

```text
DRAFT
→ TRACKED
→ CLOSED
→ TRACKED（reopen）
→ CLOSED
→ ……
```

reopen 規則：

- 沿用同一 Forum thread。
- 沿用同一案號。
- `reopen_count += 1`。
- 第一次 reopen 顯示 `2`，之後為 `3`、`4`……。
- reopen 只能從 `CLOSED` 成功轉為 `TRACKED`。
- 已為 `TRACKED` 時點擊舊按鈕，不得再次增加輪次或修改標題。
- 成功 reopen 後，該次舊結案卡的按鈕失效；下一次結案產生新的按鈕。

## 2.3 Private Support 生命週期

```text
OPEN
→ CLOSED
→ PENDING dump job
→ VERIFIED
→ DELETED
```

使用者介面：

```text
Staff /private close
→ 顯示 Private Support 結案確認卡
→ Staff 按「確認匯出並刪除」
```

`/private dump` 保留為 Staff 備援入口，不作為主要 UX。

## 2.4 Public dump 的已選定方向

此項為已選定設計，尚未實作：

```text
管理員 /dump public
→ 建立持久 queue 工作
→ dump_bot 下次在線時處理
→ 匯出與 checksum 驗證成功
→ 才更新 dump_version
```

篩選條件：

```sql
status = 'CLOSED'
AND dump_version < reopen_count + 1
```

Private 與 Public 不共用同一批次語意：

- Private：單案、結案後立即匯出，成功後刪除頻道。
- Public：週期批次、Forum thread 不刪除。

---

## 3. 目前實作狀態矩陣

| 項目 | 現況 | 主線判定 |
|---|---|---|
| 兩隻 Bot 安裝與真實登入 | 已完成 | ✅ 測試環境成立 |
| 單 Guild guard | 已實作 | ✅ 保留 |
| `/lab health` | 已實作並實測 | ✅ |
| `/lab bootstrap` | 已實作並實測 | ✅ 僅測試工具 |
| Public draft 建立 | 已實作並實測 | ✅ 測試切片 |
| 原作者專屬設定 | 已實作並實測 | ✅ |
| AI Yes／No 按鈕 | 已實作 | ✅ Public 設定 UI |
| Public 成案與初始快照 | 已實作並實測 | ✅ |
| Public 案號 | 已修正並有測試 | ✅ |
| Private 案號 | 已實作並實測 | ✅ |
| Discord DM 案號 | 已實作 | ✅ |
| Email fallback | 只記錄待處理，不寄信 | ⚠️ 未接後端 |
| `/case close` | 已實作並實測 | ✅ 手動結案 |
| reopen 邏輯 | 已修正並實測 | ✅ 邏輯通過 |
| close/reopen API 一致性 | 仍可能受 429 影響 | ⚠️ 未完成 |
| 24＋24 草稿排程 | 有測試型 30 秒 sweep | ⚠️ 非正式可靠性設計 |
| 48＋48 正式案件排程 | 未實作 | ❌ |
| Private open | 已實作並實測 | ✅ |
| Private close 確認卡 | 已實作並實測 | ✅ |
| Private 持久 dump job | 已實作 | ✅ 初版 |
| Private 匯出與 checksum | 已實作並實測 | ✅ |
| Private 驗證後刪除 | 已實作並實測 | ✅ 成功路徑 |
| Private 失敗補償 | 不完整 | ⚠️ |
| 指定 Public 單案 dump | 已實作並實測 | ✅ 管理工具 |
| 指定 Private 單案 dump | 已實作並實測 | ✅ 不觸發刪除 |
| `/dump public` | 未實作 | ❌ |
| Public 每週 queue | 未實作 | ❌ |
| `dump_version` 自動更新 | 未實作 | ❌ |
| 身份／班級／暱稱同步 | scaffold 或未實作 | ❌ |
| Portal／GAS／Bot bridge | 未實作 | ❌ |
| 正式附件保存策略 | 未決 | ⬜ |
| 正式 hosting／supervision | 未決 | ⬜ |

---

## 4. 重要技術分析

## 4.1 reopen 的「邏輯修正」與「API 卡住」應分開

目前 reopen 的資料邏輯已修正：

- conditional update 只允許 `CLOSED → TRACKED`。
- 重複 reopen 不增加 `reopen_count`。
- `base_title` 避免第二輪生成 `... 2 3`。
- 舊按鈕會即時回覆，不再無限顯示「正在思考」。

但 Discord API 與 SQLite 的提交順序仍有一致性風險：

```text
SQLite 先更新 TRACKED
→ Discord channel PATCH 解除封存／改名
→ PATCH 可能 429 或失敗
```

若 Discord PATCH 失敗，資料庫可能已是 `TRACKED`，但 Discord thread 仍封存或仍是舊標題。這不是 reopen 規則錯誤，而是跨系統操作沒有 transaction 的典型問題。

相同類型也存在於 close：

```text
SQLite 先設 CLOSED
→ 再送結案卡
→ 再封存 thread
```

中途失敗時，資料庫與 Discord 可能暫時分岔。

### 主線應採的描述

> Public reopen 邏輯已完成；Discord API `429`、逾時及跨 SQLite／Discord 一致性尚未完成，應與 24／48 小時 lifecycle reliability 一併設計。

不要再把它寫成「reopen 尚未完成」，也不要寫成「reopen 已完全 production-ready」。

## 4.2 24／48 小時計時：離散偵測器是合理候選，但尚未定案

使用者提出可考慮 discrete detector。這個方向與現有程式一致：

- 草稿目前使用每 30 秒掃描一次的 `draft_sweep`。
- Private dump 與 deletion 使用每 10 秒掃描一次的 worker。
- 這些都是簡化的週期離散偵測，而不是每案一個常駐記憶體 timer。

因此正式 24＋24／48＋48 可以優先評估「持久 deadline ＋週期 detector」，而不是替每案建立長時間 `asyncio.sleep()`。

### 建議研究模型（尚未定案）

Working data 保存：

```text
reminder_due_at
close_due_at / delete_due_at
lifecycle_generation
reminder_status
close_status
last_staff_response_at
last_activity_at
retry_after_at
attempt_count
last_error
```

Detector 每隔固定時間執行：

```text
查詢已到期、尚未成功處理的案件
→ 以 conditional UPDATE／claim 防止重複處理
→ 呼叫 Discord／Email API
→ 成功後寫入完成狀態
→ 429／timeout 寫入 retry_after_at
→ 下輪再處理
```

必要條件：

1. **持久 deadline**：Bot 離線或重啟後仍可判斷逾期工作。
2. **冪等性**：同一提醒、結案、刪除不得重複執行。
3. **claim／lease**：即使誤啟動兩個實例，也不能同時處理同一工作。
4. **API 回覆後提交**：不可在 Discord 動作尚未成功前就宣告完成。
5. **失敗補償**：能區分尚未執行、Discord 已完成但 DB 未寫回、DB 已更新但 Discord 未完成。
6. **429 尊重**：保存 `retry_after`，不可固定每 10 秒硬撞同一端點。
7. **啟動校正共用同一 detector**：不另寫一套容易漂移的啟動 timer 邏輯。

### 仍需日後決定

- detector 間隔。
- 何謂「活動」以及學生／Staff 哪些動作重設計時。
- Email reminder 與 Discord reminder 的交付成功定義。
- queue 使用共用 job table，或直接使用 case 欄位與狀態。
- 最大重試次數、退避與人工介入門檻。

此報告只將離散偵測列為優先候選，不將其寫成已定案架構。

## 4.3 Private 成功路徑已通，但 failure path 尚未達原規格

目前成功路徑合理：

- `private_dump_jobs` 持久化。
- dump_bot 只讀取 `CLOSED` 案件。
- manifest 重新計算 checksum。
- 只有 `VERIFIED` 才會交給 course_assistant 刪除。
- 刪除成功後才標記 `DELETED`。

但仍有以下缺口：

### A. job 沒有 `RUNNING` claim

目前 worker 直接讀取全部 `PENDING`。若兩個相同 token／共用 DB 的實例同時運行，可能重複匯出同一工作。

現階段以「禁止第二實例」作營運限制，但正式版本仍應加入 atomic claim／lease。

### B. 失敗工作沒有狀態與退避

`private_dump_jobs.error` 欄位存在，但 worker 失敗時目前只寫 log：

- job 保持 `PENDING`。
- 每 10 秒再次嘗試。
- 沒有 `attempt_count`、`retry_after_at`、`FAILED` 或人工重試狀態。

若 Discord 長時間 429 或附件／檔案系統持續失敗，可能形成高頻重試。

### C. 刪除失敗沒有實作既定撤權補償

原產品規格要求：

```text
匯出成功但刪除失敗
→ 撤回 dump_bot 臨時權限
→ 保留頻道
→ 通知管理者
→ 等待人工重試
```

目前刪除失敗只記錄 exception，保留 `VERIFIED` 並每 10 秒重試；沒有撤權、通知與人工重試收據。

因此主線應寫：

> Private 成功閉環已實測通過；刪除失敗、ACL rollback、重試與管理通知仍未完成。

## 4.4 現行草稿 sweep 有兩個重要一致性問題

### A. 提醒失敗仍標記已提醒

目前即使 DM 失敗，而且 Email fallback 尚未接通，程式仍會執行 `mark_draft_reminded()`。結果可能是：

```text
學生完全沒收到提醒
但資料庫認為提醒已完成
```

正式 24 小時提醒必須以實際成功的交付管道為準，不能以「已嘗試」代替「已送達或已可靠排入 Email queue」。

### B. 先標記刪除，再呼叫 Discord delete

目前到期草稿流程是：

```text
先將 draft 標記 deleted
→ 再刪除 Discord thread
```

若 Discord delete 失敗，該 draft 已不會再被 `pending_drafts()` 選到，可能留下 Discord thread，但後台認為已刪除。

這正是 24／48 detector 必須一併處理的外部一致性問題。

## 4.5 Public 標題「可編輯主體」與目前 `base_title` 實作有衝突

主線產品決策是：

- 學生可修改標題主體。
- Bot 只補回 `[M1] [關鍵字]` 固定前綴。

目前實作的 `reconcile_title()` 會直接將完整標題恢復為不可變 `base_title` 加輪次後綴。學生修改任何主體後，Bot 會把整個主體改回去。

因此目前實際行為比較接近：

> 成案後完整基礎標題固定，學生不能持續修改主體。

這是主線規格與實作的真衝突，不能只靠文件更新掩蓋。

需由主線明確決定：

- **方案 A：維持原產品決策**，新增獨立 `title_body`，學生修改主體時更新該欄位；Bot 只補前綴與輪次。
- **方案 B：改產品決策**，成案後主體固定，只允許透過未來專用命令修改。

本報告不替使用者選擇。

## 4.6 未成立草稿仍永久保存原始標題

產品決策寫明未成立草稿不保存標題、正文與附件，只保留建立／提醒／刪除資訊。

目前 `drafts` table 有 `original_title TEXT NOT NULL`，且草稿刪除後 row 仍保留該值。因此目前只做到「沒有保存正文與附件」，尚未符合「不保存標題」。

正式化時至少應：

- 成案後清除或刪除 draft row；或
- 草稿刪除時清空 `original_title`；或
- 重新設計 draft 與成案過渡資料。

## 4.7 Private 附件白名單尚未由程式強制

產品規格允許 PNG、JPG／JPEG、WebP、GIF、PDF，其他格式拒絕。

目前 Private 頻道只授予 `attach_files=True`，沒有監聽與拒絕不允許的附件格式。因此這仍是未實作規格，不能因 Private lifecycle 通過而標記完成。

## 4.8 Staff 判定目前過寬

目前 `is_staff()` 將任何具有 `Manage Threads` guild permission 的成員視為 Staff。測試伺服器可接受，但正式環境可能讓非教學角色意外取得結案／匯出能力。

正式環境應以：

- 明確 TA／Professor／System Administrator role allowlist；以及
- 伺服器 owner／指定管理者 allowlist

為主，不能只依一項泛用 Discord permission。

---

## 5. 文件一致性問題

交接 ZIP 內的兩份新報告已反映 Private lifecycle，但舊 README 與 `docs/` 仍停在 bootstrap 初期。

主要矛盾：

- `README.md` 仍寫「Private Support 結案後跨 Bot 自動授權、驗證與刪除未接通」。
- `docs/BOT_DATA_FLOW.md` 仍把 dump_bot 描述成只由本機一次性登入、完成後離線。
- `docs/BOT_OPEN_QUESTIONS.md` 仍寫 Private Support 只有建立頻道。
- `docs/BOT_CONFIG.md` 沒有 `DUMP_BOT_CLIENT_ID` 對 course_assistant Private close 的用途，也沒有 `private_dump_jobs`。
- Private 開案訊息程式內仍顯示「測試版尚未接通結案匯出後自動刪除」，與現況不符。

在合併回主線前，必須先決定：

1. bootstrap 的 `docs/` 是要更新為現行測試實作；或
2. 直接淘汰，由主線 Project Knowledge 文件接管。

不應把互相矛盾的兩套文件一起當 source of truth。

---

## 6. 測試覆蓋分析

已存在的測試涵蓋：

- 案號格式與碰撞重試。
- keyword 規則。
- 權限位元。
- title 與 reopen 輪次。
- repository reopen conditional update。
- `base_title` migration。
- reopen 按鈕成功與重複點擊。
- AI Yes／No 按鈕。
- exporter 與 manifest tamper detection。
- dump CLI 參數。

目前沒有明確測試覆蓋：

- `/private close` 的 ACL 寫入。
- `private_dump_jobs` 的完整狀態轉移。
- dump worker 的 atomic claim。
- manifest failure 時不可刪除。
- channel deletion failure。
- 刪除失敗時撤回 dump_bot ACL。
- 兩個 worker 同時處理同一 job。
- Discord 429／timeout。
- close/reopen 的跨系統補償。
- draft reminder 實際交付成功與失敗。
- draft delete API 失敗後重試。
- 48＋48 lifecycle。
- Public `dump_version`。

因此 `25 passed` 可證明核心純邏輯與部分 UI callback 沒有回歸，不能證明 Private failure path 或 production concurrency 已安全。

品質現況：

- `25 passed`（支線環境回報）。
- 28 個 pytest-asyncio／Python 3.14 event-loop deprecation warnings。
- Ruff 29 項尚未清理。

---

## 7. 主線 Project Knowledge 更新地圖

依主線既有維護規則，建議更新下列文件，不新增一套平行 source of truth。

## 7.1 `01_CURRENT_DECISIONS.md`

新增或補強：

1. 案號格式與 `Asia/Taipei`。
2. Public／Private `-P` 規則。
3. reopen 無上限、舊按鈕不得重複生效。
4. Private close 的 Staff 確認卡。
5. Private 持久 job 與 verified receipt 後才刪除。
6. Public 每週 dump 採管理員觸發持久 queue；標明尚未實作。

保留未決：

- title body 是否仍允許原生修改。
- 24／48 detector 的具體架構。

## 7.2 `02_SYSTEM_ARCHITECTURE.md`

將 `dump_bot` 架構更新為：

```text
dump_bot
├── 管理者指定 Public／Private 單案匯出
├── Private 持久單案 queue worker
├── JSON／Markdown／manifest
└── checksum 驗證
```

同時註明：

- 不背景掃描全部伺服器訊息。
- worker 只掃描本地持久 job table。
- Private verified receipt 由 `course_assistant` 消費並刪除頻道。
- Public 批次 queue 尚未實作。

## 7.3 `03_SERVER_CONFIG.md`

新增 Private 結案時的實際 ACL：

```text
dump_bot 對單一 Private channel：
View Channel = Allow
Read Message History = Allow
Send Messages = Deny
```

頻道刪除後覆寫隨頻道消失。若刪除失敗，正式規格仍要求撤權與人工處理。

## 7.4 `04_BOT_CONFIG.md`

新增：

- Discord 顯示名稱。
- `DUMP_BOT_CLIENT_ID` 是 course_assistant 找到 dump_bot member 並設定單頻道 ACL 的必要設定。
- `/private open`、`/private close`、`/private dump`。
- Staff-only「確認匯出並刪除」。
- `private_dump_jobs` 狀態。
- Public 單案 CLI 已存在；`/dump public` 尚未存在。
- 目前 worker 為 10 秒 polling 的測試實作，不視為正式排程決策。

## 7.5 `05_IMPLEMENTATION_STATUS.md`

這份文件需要大幅更新，建議至少改成：

| 項目 | 新狀態 |
|---|---|
| Discord provisioning 真實套用 | ✅ 空測試伺服器已完成；非正式 server provisioning |
| `course_assistant` 真實功能 | ✅／⚠️ Public 與 Private 測試切片可運作；未 production-ready |
| `dump_bot` 正式案件匯出 | ✅ 指定單案與 Private queue 初版 |
| 公開案件草稿設定 | ✅ 測試伺服器已通過 |
| 48＋48 自動結案 | ❌ 尚未實作 |
| 重新詢問 | ✅ 邏輯與實測通過；429 一致性待處理 |
| dump 版本 | ❌ Public 自動版本未實作 |
| Private Support 真實流程 | ✅ 成功閉環實測；failure path 待補 |
| 正式部署 | ❌ |

## 7.6 `06_UNRESOLVED.md`

調整：

- U-05「真實測試伺服器」：移至部分已解決；Application、最低權限、角色層級與 health 已測。kill switch／rollback 可保留。
- U-09「Private Support 刪除失敗」：仍未解決，不可因成功路徑通過而刪除。

新增：

### U-14 Scheduled lifecycle reliability

- 24＋24／48＋48 detector。
- Discord 429／timeout。
- SQLite／Discord 一致性。
- 冪等、claim、重試、啟動補做。

### U-15 Public batch dump queue

- `/dump public`。
- `dump_version < reopen_count + 1`。
- queue、狀態查詢、人工重試。

### U-16 Public title body semantics

- 原生修改主體 vs immutable `base_title`。

### U-17 Draft privacy and lifecycle state

- 刪除後不得保留原始標題。
- reminder delivery 的成功定義。

## 7.7 `90_DECISION_CHANGELOG.md`

建議新增：

### DEC-012：案件編號

- 六碼大寫英數安全亂數。
- `Asia/Taipei`。
- Public 無 `-P`；Private 有 `-P`。

### DEC-013：Private Support 匯出刪除交接

- Staff close 後確認卡。
- 持久單案 job。
- checksum verified receipt。
- 只有 course_assistant 刪除頻道。

### DEC-014：Public dump 方向

- 管理員 `/dump public` 建立持久 queue。
- dump_bot 下次上線處理。
- 成功後才更新 dump_version。
- 註明尚未實作。

---

## 8. 程式碼遷移建議

正式主線不可直接把 ZIP 解壓後整包覆蓋。

## 8.1 應遷移

- `src/discord_course_bots/`
- `tests/`
- `Makefile`
- `requirements*.txt`
- `pyproject.toml`
- `.env.example`
- `.gitignore` 中必要規則
- 經更新後的 README／docs，或只遷移主線 Project Knowledge 更新

## 8.2 不應遷移

- `.env`
- Bot token
- `.venv/`
- `data/course_bots.sqlite3`
- `exports/`
- cache／bytecode
- 測試伺服器產生的真實訊息內容

## 8.3 不可直接假設相容

正式主線可能已有：

- 不同 package layout。
- Portal／Schema／workflow contract。
- 既有 SQLite 或其他 working data。
- 正式角色／頻道 ID 命名。

因此應使用 feature branch／受控拷貝，逐檔比較，而非整個資料夾覆寫。

## 8.4 建議合併順序

```text
1. 先更新主線 Project Knowledge
2. 建立 Bot integration feature branch
3. 遷移純 domain／repository／exporter 與測試
4. 比對 settings、角色、頻道與 Portal contract
5. 遷移 Discord adapters／cogs／views
6. 在獨立測試 DB 執行 migration
7. 跑完整 pytest
8. 跑 Ruff，但 lint cleanup 與功能合併分開 commit
9. 啟動單一 course_assistant 與單一 dump_bot
10. 重新做 Public smoke test 與 Private 完整閉環
```

建議 commit 邊界：

1. `docs: integrate bot side-branch decisions`
2. `feat: import discord bot domain and repository`
3. `feat: import public and private discord adapters`
4. `test: add lifecycle and failure-path coverage`
5. `chore: lint and migration cleanup`

---

## 9. 合併前必須處理／接受的風險

### 🔴 必須在正式試行前處理

- 24＋24／48＋48 的持久排程與補做。
- close/reopen 的 API／DB 一致性。
- 429／timeout retry 與冪等。
- draft delete 先標記後 API 的錯序。
- reminder 未送達卻標記完成。
- Staff 判定收斂為明確 role allowlist。
- 私人附件格式限制。
- Private delete failure 的撤權與通知。

### 🟠 可先合併到開發主線，但必須明確標記

- Public batch dump 未實作。
- Public title body 規格衝突。
- Private job 沒有 RUNNING claim／backoff。
- 文件仍有 bootstrap 舊描述。
- Ruff 與 Python 3.14 warnings。
- 匯出仍包含 raw Discord author ID、display name 與附件 URL，尚未完成去識別化／保留政策。

### 🟡 可後續處理

- 正式 hosting。
- log retention。
- Portal／GAS／Email。
- 身份、班級、`nnmmm` 與暱稱同步。
- 附件檔案 bytes 的永久保存政策。

---

## 10. 主線驗收標準

合併完成後，至少應重新確認：

### 文件

- [ ] `01_CURRENT_DECISIONS.md` 已含案號與 Private job 規格。
- [ ] `04_BOT_CONFIG.md` 已反映實際命令與 worker。
- [ ] `05_IMPLEMENTATION_STATUS.md` 不再把 Public／Private 全部標成未實作。
- [ ] `06_UNRESOLVED.md` 新增 scheduled lifecycle reliability。
- [ ] 舊 bootstrap docs 不再與現行實作矛盾。

### 安全

- [ ] `.env` 與 token 未被遷移或提交。
- [ ] `dump_bot` 無管理／刪除頻道權限。
- [ ] Private 平時不讓 `dump_bot` 看見。
- [ ] 只有 verified receipt 才觸發刪除。
- [ ] 同 token 不存在第二實例。

### 程式

- [ ] migration 在副本 DB 成功。
- [ ] 完整測試通過。
- [ ] Public 成案／結案／reopen smoke test 通過。
- [ ] Private open／close／dump／verify／delete 再通過一次。
- [ ] 失敗路徑尚未完成者已在狀態文件明確列出。

---

## 11. 下一階段建議

目前不建議立刻擴張 Portal 或身份同步。下一個技術主題應集中為：

> **Scheduled lifecycle reliability：將 24＋24、48＋48、Discord API 429／timeout、重啟補做、冪等性與跨 SQLite／Discord 一致性放在同一設計中研究。**

離散偵測器是合理候選，但需先完成狀態、claim、成功定義、retry 與補償模型，再決定實作。

Public `/dump public` queue 可在此之後接續，因為它可直接重用相同的持久 job、claim、retry 與狀態查詢模式。

---

## 12. 最終判定

本支線不是只有「架好兩隻 Bot」；它已驗證核心架構確實能在 Discord 運作，尤其 Private Support 已形成第一個真實成功閉環。

主線應接收：

- 已定案的 Bot 邊界。
- Public／Private 案號規則。
- Public reopen 邏輯。
- Private 持久 dump／verify／delete 交接。
- 單案匯出與 manifest。
- 測試程式與 migration。

主線不應錯誤接收為已完成：

- 48＋48 自動結案。
- Public 每週 batch dump。
- production 級 API retry／補償。
- Private failure path。
- Portal／Email／身份同步。
- 正式部署。

建議以本報告作為 side branch → main branch 的單一整合入口，再依第 7 節更新既有 Project Knowledge；不要把 ZIP 內舊 README、舊 docs 與新報告同時當成等權 source of truth。
