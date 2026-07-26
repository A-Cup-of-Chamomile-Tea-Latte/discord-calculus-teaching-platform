# TASK-28 report — local Sheets batch importer abstraction

## Outcome

Complete。已建立只處理 GENERAL+INCLUDED ExportManifest 與 SanitizedThread 的 local Python batch importer，提供 dry-run、durable CSV、in-memory mock Apps Script endpoint 與 fail-closed future Google Sheets API adapters。實作 export/message/summary 逐列 idempotency keys、destination grouping、batching、bounded row-level retry、partial-failure report、schema/version validation 與 configurable sheet mapping。沒有 HTTP/Google/Apps Script/cloud/credentials/clasp data transfer。

## Summary

- CLI 輸入 Task 26 `metadata.json` + Task 27 `sanitized-thread.json`，可選擇 manager-reviewed summaries JSON。
- Default rows：1 筆 `Exports`、N 筆 `AnalysisMessages`、optional `AnalysisSummaries`；sheet names 可設定。
- Message rows只有 pseudonym/local refs/sanitized body/chronology/content status/source/attachment count，不含 raw Discord/internal IDs、attachment bytes/ID/filename/URL。
- Idempotency keys：`export:<exportId>`、`message:<exportId>:<messageRef>`、`summary:<exportId>:<summaryId>`。
- Dry-run 完整回報欲寫入的 rows；CSV 透過 `importKey` 持久去重；mock endpoint 可測 retry/permanent failure；future Sheets adapter 一律 NOT_CONFIGURED。
- Retry 只針對 destination 明確標記 retryable 的單列，最多 0–5 次；永久失敗以 reason/attempts/sheet/key 回報，不丟掉已成功 rows。

## Files changed

- `tools/sheets_importer/{__init__,__main__,cli,models,adapters,importer}.py`：CLI、rows/report models、四 adapters、mapping/validation/batch/retry orchestration。
- `tools/sheets_importer/README.md`：adapter/data/security/clasp boundaries。
- `tests/tools/test_sheets_importer.py`：6 個 acceptance tests。
- `docs/reports/TASK-28-REPORT.md`：本報告。

## Commands executed

Ruff format/check、strict mypy、directed pytest；實際 CLI dry-run；實際 CSV first import + second re-import。輸出位於 `/tmp/codex-task28-*`。未使用 clasp、HTTP、Google API、credential、production data、deploy、commit/push。

## Verification

- Tests：Task 28 最終 7/7 passed，覆蓋 exact dry-run、same-adapter 與 cross-instance CSV idempotency、retry+partial failure、summary/mapping、excluded/future API fail closed，以及 raw/sanitized package binding mismatch rejection。
- Linters/type checks：Task 28 Ruff 與 strict mypy 7 files 通過。
- CLI：dry-run 5 planned/5 success/3 batches（batch size 2）；CSV 首次 5 success，重新 process 後第二次 0 success/5 skipped。
- 完整 root check/build 會在並行 Tasks 29–31 整合後統一執行。

## Diagnostics

- GAS Task 16 現有 11-sheet schema 有 `Exports`/raw `Posts`，但尚無 `AnalysisMessages`/`AnalysisSummaries`。本任務使用 configurable destination abstraction，不擅自修改 production workbook schema；Task 32 需決定是新增 curated sheets，還是改用受控 backend。
- CSV adapter是本機 demonstration，沒有 concurrent locking/transaction；production idempotency 必須由 endpoint/store 原子確保。
- Export row 仍含 internal case/manager IDs 與 cursor，屬行政 manifest；message rows才是 sanitized projection。兩者應有不同權限/retention。

## Assumptions made

- Importer 只接受 Task 27 sanitized messages，不把 Task 26 raw CaseMessage 寫到 Sheets。
- Placeholder row 可匯入以保留 chronology，body 只有固定 placeholder。
- Summary 必須是人工審查後的簡單 fixture shape，本 task 不生成 summary。

## Risks and blockers

- 高：production destination auth/audit/idempotency/locking 未實作。Mitigation：future adapter 保持 fail closed，Task 32 定 endpoint contract。
- 中：curated sheet schema 尚未核准。Mitigation：Task 32/33 決定後再以 non-destructive migration 新增，不重用 raw Posts。
- 中：CSV concurrent writers 可產生 duplicate/race。Mitigation：只用 single-operator local demonstration，production 用 transactional store。

## Questions for ChatGPT discussion

- 是否新增 `AnalysisMessages`/`AnalysisSummaries` sheets，還是把 sanitized packages 留在受控 backend/object storage？
- Export manifest 與 curated content 是否應分離 spreadsheet/access role？
- Production batch endpoint 應回傳逐列 status，還是提供 atomic whole-batch mode？

## Recommended next action

進入 Task 29 security/privacy/abuse review，先定義 raw/sanitized/manifest/Sheets 的 data classification、access、retention、audit 與 abuse cases，再由 Task 30–33 完成 CI、docs、fixture integration 與最終診斷。

## Copy-paste handoff

Task 28 已完成 local batch importer，只接受 GENERAL+INCLUDED ExportManifest 與 Task27 SanitizedThread，並強制核對 source export ID/thread digest，防止 mix-and-match package。提供 dry-run、durable 0700/0600 CSV、in-memory mock Apps Script endpoint、fail-closed future Sheets API；實作 export/message/summary idempotency keys、configurable sheets、batch、bounded row retry、partial failure report。Message rows無 raw Discord/internal IDs或 attachment bytes/filename/URL，只有 sanitized content/chronology/pseudonym/status/count。Task28 最終 7/7、Ruff/mypy 通過；CLI dry-run 5/5，CSV first 5 success、second process 5 skipped。無 clasp/HTTP/Google/credential。Production API/auth/audit/atomic idempotency 仍未實作；GAS schema 尚無 AnalysisMessages/AnalysisSummaries，建議新 curated sheets 或 backend storage，不重用 raw Posts。
