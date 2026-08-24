# Schemas

本目錄使用 JSON Schema Draft 2020-12，`schemaVersion` 目前固定為 `1.0`。每個跨元件 record 有獨立 schema，共用 enum、ID、case number 與時區 timestamp 定義位於 `common.schema.json`。

## Records

- `user.schema.json`
- `verified-email.schema.json`
- `discord-account.schema.json`
- `course-membership.schema.json`
- `case.schema.json`
- `case-id-mapping.schema.json`
- `case-message.schema.json`
- `consent.schema.json`
- `activation-code.schema.json`
- `export-manifest.schema.json`
- `audit-event.schema.json`
- `case-lookup-response.schema.json`
- `case-status-lookup-response.schema.json`（當前一般／Private 共用的 content-free 單案狀態投影）
- `thread-export.schema.json`
- `attachment-index.schema.json`
- `sanitized-thread.schema.json`

Contracts 不含 framework runtime object、OAuth token、bot token、activation-code 明文或任意 audit metadata。外部 ID 使用字串保存；顯示標籤不作關聯主鍵。

Task 26 的 `thread-export` 是後續匿名化前的 raw local export：保留內部 user ID 與 Discord message ID 供 consent/reply 對照，但顯示標籤本身不含真名。`attachment-index` 只保留 metadata，不允許 CDN URL。

舊 `case-lookup-response.schema.json` 只供 legacy GAS／fixture 相容；新 backend 依 ADR-0013 使用 `case-status-lookup-response.schema.json`，不回傳題目或內容摘要。
