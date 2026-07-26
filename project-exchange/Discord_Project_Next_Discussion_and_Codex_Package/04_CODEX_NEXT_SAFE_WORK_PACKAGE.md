# Codex 下一階段安全工作包
## 只做基礎工程，不部署、不連真實服務

本文件描述可以先交給 Codex 的工作。這些工作不需要先確定正式 Discord roles／channels，也不得擅自改變尚未定案的產品政策。

## 1. Packaging 修復

- 修復最終 handoff ZIP 漏掉 `fixtures/exports/export-manifests.json`。
- 調整 archive exclusion 規則，避免誤排除 fixture 目錄。
- 增加 packaging regression test。
- 在 freshly extracted ZIP 中驗證完整 tests／build。
- 產生新的 reproducible handoff ZIP。

## 2. Case ID

實作：

```text
C12-7K4M2Q-0907-2007
C12-7K4M2Q-0907-2007-P
C99-R8N6WX-0907-2007
```

需求：

- 隨機 token。
- 不由姓名、學號、Email、Discord ID 衍生。
- 解析、驗證、格式化、遮罩。
- collision retry。
- 內部 UUID mapping。
- 測試一般、Private、C99、跨時間與碰撞情境。

## 3. Reduced Case Projection

新增或擴充：

- `last_update_at`
- `last_teaching_response_at`
- `last_student_activity_at`
- `last_read_at`
- `last_synced_at`
- `latest_teaching_response_excerpt`
- `attachment_count`
- `has_attachments`
- `timeline_events`
- `discord_deep_link`
- `closure_source`
- `closed_at`
- `reopened_at`

Portal fixture 頁應顯示 reduced screen。

## 4. 文字與附件 marker

對 fixture conversation 支援附件 marker，不下載附件本體。

## 5. 結案狀態機

支援 manual close、temporary auto-close、automatic close、reopen、closure source、closure timestamp、new activity after close。

```text
closure_source = MANUAL | AUTO
```

3 日與 7 日規則需可設定，不硬編碼在 UI。`VERIFIED_VIEW` 先作 interface／fixture，不自行決定正式驗證方法。

## 6. AI Yes／No

Portal：

```text
是否允許 AI 輔助教學分析？
○ Yes
○ No
```

需求：

- 不使用預先勾選 checkbox。
- Original poster 決定 case-level eligibility。
- Database state 為 source of truth。
- Discord tag／title icon 只作 projection。
- OP No 時整案不得進入 AI pipeline。
- OP Yes 時保留其他作者的訊息層級過濾接口。

## 7. Working／Archive Data Model

建立 fixture-first schema：

Working：ActiveCases、CaseProjection、Users、Consent、SyncState、ChangedCaseQueue。

Archive：ArchiveIndex、ExportManifest、SanitizedPackage、WeeklyMaintenanceRun。

要求：Active data 與 long-term archive 分離；網頁查詢不重新演算完整歷史；支援增量 projection、每週 archive rollover；暫不寫入真實 Google Sheets。

## 8. `dump_bot`

將 `archive_reader` 名稱與文件整理為 `dump_bot`，保留相容 alias 或 migration note。

支援 fixture-only：structure inventory、selected thread fetch、`/dump`、`/follow`、reconciliation、export manifest、no continuous polling。

新增 structure-only inventory schema：server metadata、category tree、channel tree、roles、permission overwrites、forum tags、active／archived thread counts、bots。

不讀取真實 server。

## 9. Synthetic Students

建立 fixture student／TA／teacher actor、webhook-like actor、fake interaction、fake thread lifecycle、fake read／close／reopen events。

明確標註 synthetic actors 不等同一般 Discord 使用者帳號；OAuth、DM、UI、真實 permission 仍需真人測試。

## 10. GAS／GSheet Spike

僅做 fixture／mock：changed-case batch write、active-case query cache、trigger schedule simulation、weekly maintenance plan、working sheet rollover、archive index、idempotency、quota estimation hooks。

不得實際建立 production Spreadsheet、部署 GAS、寄 Email、呼叫 Colab或使用真實學生資料。

## 11. Provisioning Dry-run Scaffold

建立 declarative server plan：roles、categories、channels、forums、permissions、bot permissions。

只允許 parse config、validate、compute diff、print plan、rollback plan、fixture server state。不得連接真實 Discord 或實際建立資源。

## 12. Portal Desktop Review Mode

更新 fixture Portal：新案號格式、reduced screen、timeline、Last Update、Last Response、attachment marker、Close Case、temporary close、AI radio、Private suffix。

先以桌面版 review 為主，保持基本 responsive，不做正式品牌美術。

## 13. 報告要求

Codex 完成後應回報：修改內容、修改檔案、測試結果、新增 schema／contract、尚未完成、可逆假設、風險與 diagnostics、下一步建議，以及可貼回 ChatGPT 的繁體中文摘要。

## 14. 明確禁止

- 不建立正式 Discord roles／channels。
- 不連入 112／113／114 server。
- 不讀取真實訊息。
- 不使用 bot token。
- 不部署 GitHub Pages。
- 不部署 GAS。
- 不寄 Email。
- 不購買服務。
- 不使用真實學生資料。
- 不自行決定 Private Support 權限。
- 不自行決定正式身份架構。
