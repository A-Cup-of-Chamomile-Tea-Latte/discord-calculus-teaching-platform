# Discord Server 結構討論表

本文件不是 provisioning 指令。用途是先討論清楚正式 roles、categories、channels、forums 與權限，再讓 Codex 產生 dry-run provisioning plan。

## 1. 使用者身份

| 身份 | Discord role | Database 欄位 | 公開顯示 | 備註 |
|---|---:|---:|---:|---|
| Professor | 待決 | 待決 | 待決 | |
| TA | 待決 | 待決 | 待決 | |
| Verified Student | 待決 | 待決 | 待決 | |
| Class Role | 待決 | 待決 | 待決 | |
| Approved Guest | 待決 | 待決 | 待決 | |
| System Admin | 待決 | 待決 | 待決 | |
| Bot | Discord 原生 | 設定檔 | 公開 | |

## 2. 學生資料欄位

候選：Discord user ID、username、server nickname、`nnmmm`、班級、身份、Email、真名／代號顯示模式、AI 分析預設、加入時間、啟動碼紀錄、特許身份與狀態。

待討論：哪些放 Discord role、哪些只放 database、哪些可被其他學生看到、哪些只對 TA／教師可見、哪些可修改。

## 3. Category 候選

```text
START HERE
COURSE QUESTIONS
CLASS QUESTIONS
COMMUNITY
PRIVATE SUPPORT
VOICE
TEACHING STAFF
SYSTEM
ARCHIVE
```

每個 category 需決定誰可見、誰可發文、誰可建立 thread、誰可管理、是否讓 dump_bot 讀取。

## 4. Forum 候選

### Course Questions

- 所有課程成員可讀。
- 一題一 post。
- 使用 tags 表示類型、狀態與 AI 分析。
- 可設定 Open／Answered／Closed。

### Class Questions

- 按班級切割。
- 每班一個 Forum，或一個 Forum 加班級 tag，待決。
- 教授／TA 是否跨班可見，待決。

### Private Support

- private thread
- restricted channel
- backend-only representation

目前未定案。

## 5. Chat 候選

```text
#general-chat
#resource-sharing
#announcements-mirror
#bot-commands
#system-status
```

避免一般 chat 取代正式 Forum 提問。

## 6. Voice 候選

```text
Office Hours
Study Room 1
Study Room 2
```

固定原則：不錄音、不自動轉錄。Voice text chat 是否納入 dump，待決。

## 7. Forum tags

狀態候選：Open、Answered、Waiting for Student、Temporarily Closed、Closed、Escalated。

類型候選：Concept、Homework Guidance、Course Administration、Technical Issue、Resource、Other。

AI：AI✓、AI×。

班級：C01、C02、…、C99。

Discord Forum tag 數量有限，需要避免設計過多。

## 8. Bot 權限討論

### `course_assistant`

候選：View Channels、Send Messages、Send Messages in Threads、Create Public Threads、Create Private Threads、Manage Threads、Read Message History、Use Application Commands、Manage Nicknames、Manage Roles。

待決：Manage Channels 是否必要、Manage Webhooks 是否必要、Private Support 權限、是否需要 Guild Members intent。

### `dump_bot`

候選：View Channels、Read Message History、Use Application Commands、Send Messages、Attach Files。

固定：不給 Manage Roles、Manage Channels 或 Administrator；結構盤點與匯出採 read-only。

## 9. 初版最小化目標

```text
START HERE
#start-here
#rules-and-guide

QUESTIONS
#course-questions

COMMUNITY
#general-chat
#resource-sharing

SUPPORT
#private-support-entry

SYSTEM
#bot-commands
#system-status
```

班級專屬 Forum、Voice 與 Staff 區可後加。

## 10. 尚待討論

1. 班級要用 role 還是 tag。
2. 所有 TA 是否看得到所有班。
3. Private Support 誰預設可見。
4. Approved Guest 可看到哪些區。
5. 是否允許學生直接 DM TA。
6. 真名與 `nnmmm` 顯示規則。
7. Anonymous 回覆如何操作。
8. `dump_bot` 是否可讀教學團隊內部區。
9. Discord auto-archive 與案件結案如何配合。
10. Forum tag 上限與最小分類。
