# ADR-0008: 本機明確啟動匯出

- Status: Accepted（prototype scope only）
- Date: 2026-07-19
- Owners: 課程管理者、資料工具維護者
- Related tasks: 23, 26–28, 29

## Context

現況需要人工複製完整 Discord 對話供後續檢視。自動同步所有訊息到 Sheets 或 AI 會擴大資料蒐集、配額與同意風險。

## Decision

由授權管理者明確選擇 thread 並執行本機 `dump` 或範圍清楚的 `follow`。輸出版本化 JSON/Markdown，保留時間、作者角色、回覆、編輯、附件 metadata 與同意資訊；之後才可匿名化或批次匯入。

## Consequences

### Positive

資料範圍、時間與操作者可稽核，能取代臨時複製並在分析前執行同意／排除規則。

### Negative

需要管理本機檔案安全、重跑 idempotency 與 incremental cursor；結果不是即時 mirror。

### Operational

真實匯出目錄被 Git ignore；原始資料與匿名結果分開。正式 Discord read permission 與附件下載政策需 technical spike。

## Alternatives considered

逐訊息同步到 Sheets 或直接送往 LLM 較自動，但不符合最小蒐集與人工明確啟動原則。

## Reversal strategy

ExportManifest 與訊息 schema 保持 storage-neutral；未來可把同一 pipeline 放入受控 job runner，而 CLI 行為與稽核欄位維持不變。

## Open questions

follow 的停止條件、保留期限、附件內容是否下載，以及正式操作者授權尚未定案。
