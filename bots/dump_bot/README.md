# dump_bot

`dump_bot` 是結構盤點與明確匯出的 canonical 名稱；現有 `bots.archive_reader`
保留為 Python 相容層，既有 import、`/dump`、`/follow` 與 checkpoint 不變。未來移除舊名
前須先公告版本與更新部署設定，本輪不進行破壞式 rename。

目前僅支援注入式 fixture：

- structure inventory：server metadata、category/channel tree、roles、permission
  overwrites、forum tags、active/archived thread counts、bots；禁止 message body 與 member list。
- selected thread fetch：沿用 allowlisted `ArchiveReaderService`，必須由管理者明確指定案件。
- `/dump`：一次性、具邊界的完整分頁讀取。
- `/follow`：從成功 checkpoint 增量讀取一次；不是訂閱或背景輪詢。
- reconciliation：檢查 message ID 唯一性與尾端 cursor。
- export manifest：以 canonical JSON 計算 SHA-256，只描述本機交付檔。

沒有 Gateway、scheduler、continuous polling、live REST adapter、token 或真實 server 讀取。
`bots/archive_reader/README.md` 是舊名的 migration note 入口。

## 目前設定名稱

產品與文件使用 `dump_bot`；為避免破壞既有 runtime，程式設定仍暫時使用
`ARCHIVE_READER_DISCORD_TOKEN`、`ARCHIVE_READER_GUILD_ID`、
`ARCHIVE_READER_CHANNEL_IDS` 與 `ARCHIVE_READER_MESSAGE_CONTENT_ENABLED`。
它們是同一個 reader runtime 的相容 namespace，不代表可另建一個 archive-reader
token。有效設定與 fixture/live fail-closed 規則見
[`docs/CONFIGURATION.md`](../../docs/CONFIGURATION.md)。
