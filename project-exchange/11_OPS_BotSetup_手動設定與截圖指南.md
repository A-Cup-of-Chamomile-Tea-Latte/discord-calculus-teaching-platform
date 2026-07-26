# Discord Test Server 與 Bot 建立
## 手把手操作指南

這份文件供專案負責人本人操作。每一步可以把安全截圖貼到臨時 ChatGPT 對話詢問，但不得貼 bot token、client secret、Email 密碼、OAuth secret 或完整 `.env`。

## 0. 操作前準備

你需要：

- 已登入 Discord 的瀏覽器。
- 已建立的測試 server。
- 可以管理該 server 的帳號。
- 專案本機資料夾。
- 一個只在本機保存 secrets 的位置。

建議先建立兩隻 bot：

1. `course_assistant`
2. `dump_bot`

先不要建立 moderation bot。

## 1. 開啟 Developer Mode

1. 左下角齒輪進入 User Settings。
2. 找到 Advanced。
3. 開啟 Developer Mode。

開啟後可以 Copy User ID、Server ID、Channel ID、Message ID。

可以截圖 Advanced 頁面，只要沒有其他個資。

## 2. 複製自己的 Discord User ID

1. 回到任意 server。
2. 找到自己的名稱或頭像。
3. 右鍵。
4. 選 Copy User ID。

`dingding124816` 是 username，不是純數字 User ID。User ID 會是一長串純數字。

User ID 不是密碼，但不必放進公開文件。

## 3. 複製測試 Server ID

1. 在 server 左上名稱按右鍵。
2. 選 Copy Server ID。
3. 記錄在本機安全筆記。

可以截圖 Server menu 或 Server overview，不需要顯示邀請碼。

## 4. 建立 `course_assistant` Application

1. 開啟 Discord Developer Portal。
2. 按 New Application。
3. 名稱輸入：`calculus-course-assistant-dev`。
4. 接受開發者條款。
5. 建立。

可以截圖 Application General Information。Application ID 可以顯示。

不得截圖或貼出 Client Secret、Bot Token、OAuth secret。

## 5. 建立 Bot User

1. Application 左側進入 Bot。
2. 若有 Add Bot，按下。
3. 設定名稱與測試頭像。
4. 只有真正需要時才建立或 reset token。
5. Token 立刻只存本機 `.env`。

Bot token 等同密碼：不得貼到 ChatGPT、Markdown、Git、Email、Google Sheets 或截圖。若曾出現在不安全位置，立即 reset。

## 6. 建立 `dump_bot` Application

重複上面的 Application 與 Bot User 流程，名稱建議：

```text
calculus-dump-bot-dev
```

它應以唯讀權限為主。

## 7. 設定 Installation

每一隻 Application 都需要 Guild Install。

Scopes 先選：

```text
bot
applications.commands
```

### `course_assistant` 暫定權限

先不要給 Administrator。

候選：

- View Channels
- Send Messages
- Send Messages in Threads
- Create Public Threads
- Create Private Threads
- Manage Threads
- Read Message History
- Use Application Commands
- Manage Nicknames
- Manage Roles

正式 permission matrix 決定前，不要額外開高權限。

### `dump_bot` 暫定權限

優先只給：

- View Channels
- Read Message History
- Use Application Commands

若 `/dump` 要回傳檔案，才加 Send Messages 與 Attach Files。

不要給 Manage Roles、Manage Channels、Kick Members、Ban Members 或 Administrator。

## 8. 產生 Install Link

1. 在 Installation 或 OAuth2 URL Generator。
2. 選 Guild Install。
3. 選 scopes。
4. 選最低權限。
5. 複製 install link。
6. 在瀏覽器開啟。
7. 選擇測試 server。
8. Authorize。

可以截圖權限列表、OAuth2 scopes 與安裝成功後的成員列表。不要貼 bot token 或 client secret。

## 9. 確認 Bot 已加入

在測試 server：

1. 成員列表應看到 bot。
2. Server Settings → Integrations 應看到 application。
3. Server Settings → Roles 應看到 bot role。

先不要拖動 role hierarchy，除非我們已確定規則。

## 10. 記錄必要 IDs

可能需要：

- Discord User ID
- Test Server ID
- Test Category ID
- Test Forum ID
- Test Text Channel ID
- Bot Application ID

可存成：

```text
TEST_GUILD_ID=
TEST_FORUM_CHANNEL_ID=
TEST_TEXT_CHANNEL_ID=
OWNER_DISCORD_USER_ID=
```

真正 token 另存：

```text
COURSE_ASSISTANT_BOT_TOKEN=
DUMP_BOT_TOKEN=
```

## 11. 建立本機 `.env`

在專案 root 建立 `.env`：

```text
DISCORD_ENV=development
TEST_GUILD_ID=123456789012345678
COURSE_ASSISTANT_BOT_TOKEN=REPLACE_LOCALLY
DUMP_BOT_TOKEN=REPLACE_LOCALLY
```

確認：

- `.env` 已列入 `.gitignore`。
- 不加入 ZIP。
- 不貼給 ChatGPT。
- 截圖時遮住整個 token value。

## 12. 第一次啟動只做 Health Check

第一次不要建立 roles／channels。

目標只有：

- Bot 登入成功。
- Slash command 註冊成功。
- `/health` 有回覆。
- Log 不出現 token。
- Bot 沒有多餘權限。

錯誤時可貼：錯誤訊息、command、Python／Node 版本、哪一隻 bot、哪個步驟與安全截圖。不要貼 token。

## 13. Provisioning 前必須停止

Bot 登入成功後先停下。不要直接讓 Codex 或 bot 建立 Roles、Categories、Channels、Forums 或 permission overwrites。先討論正式結構。

## 14. 建議截圖清單

1. Application General Information。
2. Bot 頁面，但避開 token 區。
3. Installation scopes。
4. Bot permissions。
5. Server Settings → Roles。
6. Server Settings → Integrations。
7. 測試 server 現有 channel tree。
8. Bot 加入後的成員列表。
9. `/health` 回覆。
10. Terminal 的安全錯誤訊息。

## 15. 臨時對話提示詞

```markdown
我正在設定 Discord 微積分教學專案的測試 server。

目前步驟：
[填寫步驟]

這是安全截圖／錯誤訊息：
[貼圖或貼文字]

請只告訴我下一個最小步驟，不要一次跳到正式部署。
不要要求我貼 bot token、client secret、Email 密碼或完整 .env。
先確認目前權限是否過大，以及我應該截哪個畫面給你檢查。
```

## 16. 遇到這些情況立刻停下

- Portal 要你公開 token。
- Codex 要你把 token 寫進 repository。
- Bot 要求 Administrator。
- Server role hierarchy 看不懂。
- Install link 指向不是你的測試 server。
- Bot 突然大量建立 channels。
- Bot 讀取不應可見的 private channel。
- Terminal log 印出 token。
- Git 顯示 `.env` 被追蹤。

先停止程序，再到臨時對話詢問。
