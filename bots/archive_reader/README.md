# Archive reader（`dump_bot` 相容名稱）

新的 canonical 名稱是 [`bots/dump_bot`](../dump_bot/README.md)。本 package 暫時保留，
既有 import、fixture tests、`/dump`／`/follow` 與設定名稱均不破壞；正式 rename 與設定
migration 必須另行審核。

讀取指定案件／thread並交給明確啟動的本機匯出流程。它不持續監控所有訊息、不寫入教學互動，也不分析學生表現。

## 介面與生命週期

- `ArchiveReaderService.resolve_thread_id()`：授權後將一個公開案件編號解析成 allowlisted thread ID。
- `dump()`：每次明確請求時，從 thread 開頭分頁讀取一次。
- `follow()`：每次明確請求時，從上次成功交付的 Discord message ID 之後讀取一次。它是 checkpoint，不是訂閱、timer 或 background polling。
- `ArchiveReaderAdminApp` 暴露 `/dump` 與 `/follow` 同名的本機管理介面，但不註冊 Discord command tree，因此不需要發送 interaction response 的權限。
- 每批結果交給 injected `ExportHandoffSink`；fixture sink 只保存記憶體物件。本機檔案輸出由明確啟動的 `tools/discord_export` CLI 負責。

## 最小權限與資料邊界

- Discord channel permissions 只有 allowlisted `VIEW_CHANNEL` 與 `READ_MESSAGE_HISTORY`。
- 為明確讀取 content 與 attachment metadata，獨立 application 需核准 privileged `MESSAGE_CONTENT` capability。
- 不需要 `SEND_MESSAGES`、`MANAGE_MESSAGES`、`MANAGE_THREADS`、`MANAGE_ROLES`、`MANAGE_NICKNAMES` 或 `ADMINISTRATOR`。
- 不訂閱全域 message event，不建立 Gateway、timer 或 background task；未來 live adapter 優先採 targeted REST fetch。
- 只讀 attachment ID、filename、media type 與 size；download URL 不進入 CaseMessage 交付，也不下載檔案。
- Discord author ID 必須先有內部 user/display/analysis policy mapping；未知作者 fail closed。
- `PRIVATE_SUPPORT`、無 mapping、跨 guild 或超出 channel allowlist 的案件均作為不存在。
- runtime 只讀 `ARCHIVE_READER_DISCORD_TOKEN`；fixture/dry-run 模式禁止配置 token。

## 目前限制

Live Discord REST adapter、durable case index/checkpoint/idempotency/sink 與 manager identity provider 都尚未連接。attachment-only message 與 checkpoint/handoff 的 durable transaction 邊界仍是 production gate；本版對未定義情況 fail closed。
