# Discord Course Bots — Canonical tracked runtime

這是兩隻已通過測試伺服器實測的 Bot runtime 之 canonical tracked package。它由
`.local/discord-course-bots-runtime/` 受控遷入；目前 live LaunchAgent 尚未切換，避免在
source checkpoint 階段中斷既有服務。

## 已實作

### `course_assistant`

- 僅接受 `TEST_GUILD_ID` 指定的單一伺服器。
- `/lab health`：檢查 Guild、Intents、角色層級、頻道權限與資料庫設定。
- `/lab bootstrap`：建立最小測試角色、控制頻道、Forum 與 Private Support 分類。
- 偵測白名單 Forum 的新文章。
- 公開起始設定訊息；只有原作者可設定或刪除草稿。
- 私人關鍵字輸入 + AI Yes/No 選擇。
- 正式成案、初始快照、案號、DM；DM 失敗時只記錄 Email fallback 待處理，不假裝已寄信。
- 固定 `[M1] [關鍵字]` 前綴與離線後校正。
- `/case close` 與「繼續詢問」。
- `/private open` 建立測試 Private Support 頻道。
- 草稿提醒與刪除排程；測試時可把秒數縮短。

### `dump_bot`

- 邀請權限只有 View Channel + Read Message History。
- `probe`：一次性登入、列出可見頻道與權限後離線。
- `online`：保持在線，無任何寫入事件或 Discord 指令。
- `export-public`：只匯出已登錄的公開 Forum 案件。
- `export-private`：只匯出已登錄的 Private Support 案件。

## 刻意未接通

- Portal／GAS 命令傳遞。
- Email 寄送。
- NTU Mail、Student／Guest 真實驗證。
- 正式 Google Sheets／資料庫。
- Private Support 結案後的跨 Bot 自動授權、驗證與刪除。
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

在 Discord 輸入：

```text
/lab health
/lab bootstrap
/lab health
```

`/lab bootstrap` 只允許伺服器擁有者或 `BOT_OWNER_IDS` 執行。

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

## 測試版權限

`course_assistant` 邀請權限不含 Administrator、Manage Guild、Kick、Ban、Manage Webhooks 或 Mention Everyone。`/lab bootstrap` 建立的可操作角色與頻道都位於測試結構內。

`dump_bot` 只有：

- View Channels
- Read Message History

## 重要測試限制

- 空伺服器仍是真實 Discord API；任何測試文字都會留在 Discord，除非手動刪除。
- Bot 會拒絕在非 `TEST_GUILD_ID` 的伺服器啟動。
- `dump_bot` 匯出內容可能含訊息正文與附件 URL，請只使用虛構測試資料。
- 第一次測試不要給 `course_assistant` Administrator。權限錯誤本身正是目前要觀察的資料。
