# Discord Course Bots — Canonical tracked runtime

這是 Discord Bot 的 canonical tracked runtime 與目前 production candidate。Remote Linux 的已驗證
production baseline 仍是 schema v6；v13 deployment candidate 已整合到 schema v13，但尚未部署。任何 forward
都必須先用 production consistent backup 演練 migration，並取得另外的部署授權。

## 已實作

### `course_assistant`

- 僅接受 `TEST_GUILD_ID` 指定的單一伺服器。
- 偵測白名單 Forum 的新文章。
- 公開起始設定訊息；只有原作者可設定或按「刪除這篇草稿」。
- 私人關鍵字輸入 + AI Yes/No 選擇。
- 正式成案、初始快照、案號、DM；DM 失敗時進人工接管，不改寄 Email、不假裝已通知。
- 固定 `[M{n} | C{classCode}][關鍵字]` 前綴與離線後校正；班別從 Discord class role 唯一判斷，Module 從設定取得。
- `/case close` 與「繼續詢問」。
- `/private open` 建立受限 Private Support 頻道；案號使用 `C99…-P`。
- Private 案件進入 IDLE 48 小時後，再 48 小時無學生回覆會先自動排入
  `private_dump_jobs`。只有 manifest 驗證成功才刪除 Discord 頻道並清除 operational DB
  內的正文、連結與 requester；export 失敗時保留頻道並進人工接管。
- `/join-review` 與 `/join-admin`：兩級審核權限、五態加入流程、角色／暱稱 durable side effect 與 Discord DM。
- 草稿提醒與刪除排程；測試時可把秒數縮短。

### `dump_bot`

- 邀請權限只有 View Channel + Read Message History。
- `probe`：一次性登入、列出可見頻道與權限後離線。
- `online`：處理 Private Support 到期時的 verified export；v13 deployment 必須保持此服務在線。
- `export-public`：只匯出已登錄的公開 Forum 案件。
- `export-private`：只匯出已登錄的 Private Support 案件。
- Private dump queue 使用原子 claim、唯一 token、15 分鐘 lease、5 分鐘心跳、指數退避與最多五次嘗試；只有持有目前 claim token 的 worker 可以完成或標記失敗。
- System admin 可用 `/ops attention-list`、`attention-inspect`、`attention-retry`、
  `attention-resolve`，以及 `/ops replacement-case` 接管失敗項目；這些命令只操作 allowlisted
  queue 欄位並留下 owner audit，不接受任意 SQL。
- SQLite 使用具 checksum 的 migration ledger；未知新版或已竄改 migration 會拒絕啟動。
- `discord-db-inspect` 以 SQLite 唯讀模式列出 schema version、表名、欄位與列數；不執行 migration，也不讀出或列印 application row values。

## 尚未接通／仍需 gate

- Portal same-origin 加入申請與單案查詢 adapter。
- Email 寄送。
- NTU Mail 的正式身分 authority；目前只做後端格式與網域重驗，不把 Email 當選課證明。
- 正式 Google Sheets／資料庫。
- production Discord role／category／class-module 映射與白帳號端到端 ACL regression。
- AI 正文分析。

這些介面仍保留，但測試版不會偽造成功。

## 最快啟動

### 1. 建立兩個 Discord Applications

在 Discord Developer Portal 分別建立：

- `course_assistant`
- `dump_bot`

兩個 Application 都建立 Bot user。Token 只放本機 `.env`，不要貼到聊天、截圖或 Git。

在 **Bot → Privileged Gateway Intents**：

- `course_assistant`：開啟 **Server Members Intent** 與 **Message Content Intent**。
- `dump_bot`：開啟 **Message Content Intent**。
- 不需要 Presence Intent。

### 2. 本機安裝

```bash
cd runtime/discord-course-bots
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
```

填入四個 Application／Bot 欄位與 `TEST_GUILD_ID`。

取得 ID：Discord 使用者設定 → Advanced → Developer Mode，右鍵伺服器／使用者 → Copy ID。

### 3. 產生並開啟邀請連結

```bash
.venv/bin/discord-bot-invites
```

依序開啟輸出的兩個 URL，加入空測試伺服器。

### 4. 啟動 `course_assistant`

```bash
.venv/bin/course-assistant
```

完成 `.env` 與 SQLite runtime config 後，在 Discord 使用：

```text
/ops status
/case claim
/case close
/private open
/private close
/join-review queue
/join-review bind
/join-review approve
/join-admin grant
```

`/ops` 與 `/join-admin` 只允許 `BOT_OWNER_IDS` 或已授權的 `SYSTEM_ADMIN`；
`/join-review` 允許教學審核者與系統管理員。第一位系統管理員以 `BOT_OWNER_IDS` 作 bootstrap，
不使用 Portal 的本機帳密。

### Runtime config

下列 key 儲存在 SQLite `runtime_config`，不放 token 或學生資料：

- `managed_forum_ids`、`private_support_category_id`、`private_support_entry_channel_id`
- `course_role_id`、`visitor_role_id`
- `ta_role_id`、`professor_role_id`、`system_admin_role_id`
- `class_role_01` 至 `class_role_16`
- `class_module_01` 至 `class_module_16`

System admin 可用 `/join-admin set-role`、`/join-admin set-category`、
`/join-admin set-module`、`/join-admin add-forum` 與 `/join-admin remove-forum` 更新
allowlisted 設定。正式使用前仍須用測試帳號核對 Discord role hierarchy、唯一班別、Private ACL 與
115-1 canonical mapping；設定缺漏時流程會 fail closed。

### 5. 實測 Forum

到 `math-questions` 建立文章，依序測試：

1. 原作者設定。
2. 另一帳號點設定按鈕。
3. 關鍵字與 AI 選項。
4. Bot 改標題。
5. 私訊案號。
6. 手動刪掉標題前綴，看 Bot 是否補回。
7. Staff 使用 `/case close`。
8. 原作者按「繼續詢問」。

### 6. 啟動／探測 `dump_bot`

```bash
.venv/bin/dump-bot probe
# 或保持在線：.venv/bin/dump-bot online
```

匯出已登錄的公開 Forum thread：

```bash
.venv/bin/dump-bot export-public \
  --thread-id 123456789012345678
```

匯出已登錄的 Private Support 頻道：

```bash
.venv/bin/dump-bot export-private \
  --channel-id 123456789012345678
```

## 權限邊界

`course_assistant` 邀請權限不含 Administrator、Manage Guild、Kick、Ban、Manage Webhooks 或 Mention Everyone。可操作的角色與頻道必須由 owner 預先建立並明確映射；Bot 不自行擴權。

`dump_bot` 只有：

- View Channels
- Read Message History

## 重要測試限制

- 空伺服器仍是真實 Discord API；任何測試文字都會留在 Discord，除非手動刪除。
- Bot 會拒絕在非 `TEST_GUILD_ID` 的伺服器啟動。
- `dump_bot` 匯出內容可能含訊息正文與附件 URL，請只使用虛構測試資料。
- Queue 的 `error` 欄位只保存固定安全代碼，不保存 exception 原文、學生姓名或訊息內容。
- 第一次測試不要給 `course_assistant` Administrator。權限錯誤本身正是目前要觀察的資料。

## 自己檢查 SQLite 結構（唯讀）

先對測試資料庫使用，不要直接修改 live 檔案：

```bash
.venv/bin/discord-db-inspect ./data/course_bots.sqlite3
# 或輸出只含結構、列數與檔案雜湊的 JSON
.venv/bin/discord-db-inspect ./data/course_bots.sqlite3 --json
```

這個指令不會顯示訊息、姓名、Discord ID 或其他 row values。檔案雜湊可用來確認檢查前後資料庫檔本身沒有被改寫。
