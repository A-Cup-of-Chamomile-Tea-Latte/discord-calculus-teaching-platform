# SQLite 與資料載體：去黑盒學習路線

這份路線的目標不是把你訓練成資料庫工程師，而是讓你能獨立回答三件事：資料在哪裡、哪個版本說了算、程式失敗時資料會不會亂掉。

本機 Portal 現已提供 `/sqlite-lab/` 互動版本：包含資料地圖、合成 SQL、transaction、reliable queue、載體分類、cloud authenticity gate、整合小測與只存在瀏覽器的進度紀錄。本文件保留作為可搜尋的小抄。

## SQLite 是什麼

SQLite 是一個嵌入在程式裡的小型關聯式資料庫。它通常把資料表、索引與交易狀態放在一個 `.sqlite3` 檔案中，不需要另外架一台 database server。

可以把它想成「有嚴格規則、可交易、可查詢的本機資料檔」：

- **table**：同一類資料的表格，例如 `cases`；
- **row**：一筆案件或工作；
- **column**：每筆資料必須遵守的欄位；
- **primary／unique key**：防止同一案件或案號重複；
- **transaction**：一組變更全部成功或全部撤回；
- **migration**：有版本、有 checksum 的結構升級步驟；
- **index**：讓常用查詢更快，但不是另一份真實資料。

它不是 AI，也不會自行決策。專案裡的 Python 程式送出明確 SQL；schema、migration 與測試都能逐行查看。它適合目前單機、兩隻 bot 共用的低至中量 operational state。若未來多台主機同時大量寫入、需要遠端高可用或細緻資料庫帳號權限，再評估 Postgres；現在先上雲端 database 會增加維運面而沒有明確收益。

## 這個專案怎麼分工

| 載體 | 負責 | 不負責 |
| --- | --- | --- |
| Local SQLite | Bot 案件狀態、Private Support queue、交易一致性；主要 authority | 遠端共用介面、大型附件 |
| Google Sheets | TA 看得懂的目前摘要、成員／bot 狀態、低頻操作與 sync receipt | 原始訊息、完整 log、secret、source code |
| Git 文字檔 | schema、migration、policy、程式與可 review 歷史 | live 資料與 secret |
| 受管 archive 檔案 | raw／sanitized export 與附件，配合 manifest/checksum | 即時狀態查詢 |
| Local rotating logs | 除錯與近期 runtime evidence | 永久歷史、TA dashboard |

一句話：SQLite 負責「現在真實狀態與安全寫入」，Sheet 負責「人需要看見的投影」，檔案負責「體積大或需要封存的內容」。

## 七堂小課，不再用長篇 token 轟炸

每堂 15–30 分鐘；一次只做一堂，使用 synthetic／disposable database。完成小驗收再進下一堂。

### 0. 畫出資料地圖（15 分鐘）

把一個 case 從 Discord → SQLite → Sheet projection → archive 畫成四格。驗收：你能指出每一格的 owner，並說明為何 raw message 不進 Sheet。

### 1. 唯讀看見 SQLite（20 分鐘）

建立 disposable DB，執行：

```bash
runtime/discord-course-bots/.venv/bin/discord-db-inspect /path/to/disposable.sqlite3
```

工具只顯示版本、表名、欄位、列數與檔案 SHA-256，不顯示 row values。驗收：你能指出 `cases` 的 primary key、列數與目前 migration version。

### 2. 親手做四個安全 SELECT（20 分鐘）

在副本上學 `.tables`、`.schema cases`、`SELECT COUNT(*)`、依 status 分組計數。不要一開始查 `SELECT *`。驗收：能自己回答「有幾個案件、各狀態多少」，且不把內容貼到聊天。

### 3. 看懂 transaction 與 migration（25 分鐘）

用兩個 synthetic rows 模擬 transaction 中途失敗，觀察 rollback；再讀 migration ledger 的 version／name／checksum。驗收：能解釋為何 checksum 不符時 bot 應拒絕啟動。

### 4. 追一個 queue job（25 分鐘）

只看 `PENDING → CLAIMED → VERIFIED` 的 metadata，模擬 lease 到期與舊 token 失效。驗收：能說明 idempotency、claim 與 lease 各防哪一種重複／競爭。

### 5. 比較 SQLite、Sheet 與檔案（20 分鐘）

拿 Members、bot heartbeat、raw attachment 三種資料做 carrier 分類。驗收：能判斷哪些要投影到雲端、哪些只需機器看、哪些應留檔案。

### 6. 驗證 local → cloud projection（25 分鐘）

用 synthetic snapshot 檢查 schema version、source version、checksum、timestamp 與 operator confirmation。驗收：能說明為何 Sheet 比較新不代表它自動是真相。

### 7. Backup／restore 演練（30 分鐘）

只對 disposable DB 操作：安全停止 writer、建立一致性備份、在另一個路徑 restore、執行 inspector 比對版本與列數。驗收：有一張自己看得懂的 restore checklist。

## 學習護欄

- 教學一律先用 synthetic／disposable DB；live DB 只做事先核准的唯讀檢查。
- 不把 DB、row dump、學生資料、Discord ID、Email、Private Support 或附件貼給 LLM。
- AI 每次最多引入三個新名詞，先讓你預測結果，再執行，再用 evidence 解釋。
- 每堂課結束產出一張小抄或一個可重跑指令，不用保存長篇對話。
- 不懂時回到「authority、carrier、transaction」三個核心，不繼續堆工具名。

## 可行性清單

- [x] 本機 SQLite 已有 versioned migration ledger 與 checksum 驗證。
- [x] Reliable Private Support queue 已用 disposable DB 測試 claim／lease／retry。
- [x] 新增不顯示 row values 的唯讀 inspector。
- [x] Sheet compact schema 將人類視圖與機器視圖分開。
- [x] Members 與 Operations 有去識別／安全摘要欄位。
- [ ] 用 synthetic DB 陪你完成第 1–2 課。
- [ ] 建立 local → Sheets projection adapter 與 authenticity receipt。
- [ ] 做一次 disposable backup／restore drill。
- [ ] 正式 cutover 前對 live DB 副本 rehearsal；不直接拿大檔 live DB 練習。

## 你真正需要記住的三句話

1. SQLite 是本機資料庫檔與嚴格規則，不是 AI 黑盒。
2. 真實狀態在 local SQLite；Sheet 是方便人看的受控投影。
3. 任何 cloud → local 都要驗證與人工確認，不能因為雲端看起來新就覆蓋本機。
