# Working／Archive fixture data model

本模型把網站查詢所需的短期 working set 與長期 archive 分開。它是 schema 與 in-memory
spike，不會建立或寫入 Google Spreadsheet。

## Working set

| Model | 用途 | 更新方式 |
|---|---|---|
| `ActiveCases` | 尚在服務流程內的最小狀態、projection version、source cursor | 依 `caseId + changeVersion` 增量 upsert |
| `CaseProjection` | Portal reduced screen 的 materialized projection | Changed queue 成功後替換單一案件，不從完整歷史重算 |
| `Users` | 既有內部使用者與顯示政策 | 既有 `user.schema.json` |
| `Consent`／`Consents` | 帳號與逐訊息分析決定 | 既有 `consent.schema.json`；變更會 enqueue case |
| `SyncState` | 每個 fixture source 的 cursor、狀態與最後同步時間 | 成功交付後才 advance cursor |
| `ChangedCaseQueue` | 需要重建 projection 的案件佇列 | `idempotencyKey` 去重，支援 reconciliation reason |

網頁只查 `CaseProjection`／`ActiveCases`，不得在 HTTP request 中讀完整 Discord thread 或
archive。queue consumer 以小批次處理，projection 更新完成後才標記 applied。

## Long-term archive

| Model | 用途 |
|---|---|
| `ArchiveIndex` | `caseId + period` 到 manifest／sanitized package 的索引，不含 message body |
| `ExportManifest` | immutable export file、SHA-256、cursor 與 count；沿用既有 contract |
| `SanitizedPackage` | 匿名化後 package 的 source binding、hash、人工 review state；Private 永遠 false |
| `WeeklyMaintenanceRun` | 每週 dry-run 計畫、估算 writes 與完成狀態，不保存 case content |

archive payload 不放回 working workbook。Fixture rollover 只處理計畫快照中的 closed cases：
先建立 manifest/index，再移除 working projection；同一 `runId` 重播不重複。正式版仍需要
transaction/outbox、retention、restore drill 與人工核准。

## 每週增量流程

1. drain `ChangedCaseQueue`，批次更新 `ActiveCases` 與 `CaseProjection`。
2. 依 `SyncState` 做 bounded reconciliation；不啟動 continuous polling。
3. 產生 `WeeklyMaintenanceRun(dryRun=true)` 與 quota estimate，交由 operator review。
4. 對 closed case 產生 export manifest 與 archive index。
5. 確認 archive 可讀後才 rollover working rows；用 `runId` 保證重播安全。

目前可逆假設：週別採 ISO `YYYY-Www`、cache TTL 60 秒、batch size 由 caller 注入、closed
case 才能 rollover。這些值都不是 Portal UI 或正式 policy 的硬編碼。
