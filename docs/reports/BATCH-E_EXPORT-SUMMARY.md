# Batch E export summary — Tasks 26–28

## Outcome

Batch E complete，Tasks 26、27、28 無 skip/block。已建立單次 fixture/local thread export → consent/anonymization → dry-run/CSV/mock batch import 完整 lane，無 live Discord、LLM/API、Google API、clasp data transfer、credentials、real data、deploy 或 continuous process。

## Completed tasks

- Task 26：case/thread selection、pagination、full/incremental、checkpoint、idempotent atomic four-file raw export、contracts、pseudonymous labels、readable reply Markdown。
- Task 27：Private/EXCLUDED fail closed、current consent resolution、structural placeholders、case-local pseudonyms、PII category replacement、sanitized contract、redaction/consent/review artifacts。
- Task 28：validated curated rows、export/message/summary idempotency、batch/retry/partial failure、dry-run/CSV/mock/future adapters、configurable mapping。

## Verification snapshot

- Task 26 completion：Python 96/96、Portal 25/25、GAS 44/44；secret 338/0；mypy 53 files。
- Task 27 completion：Python 102/102、Portal 25/25、GAS 44/44；secret 346/0；mypy 58 files。
- Task 28 directed：6/6；Ruff/mypy 7 files；CLI dry-run 5/5、CSV re-import 5 skipped。
- Final root check/build 在 Tasks 29–31 並行整合後統一重跑。

## Key diagnostics

- Task 26 raw export 仍含 IDs 與 EXCLUDED content，不可直接分析。
- Task 27 只是 conservative de-identification，必須人工複核，附件 binary 未分析。
- Task 28 production destination/auth/audit/atomicity 未實作；curated Sheets schema 尚待決定。
- Attachment-only CaseMessage v1 仍 fail closed；multi-file crash recovery/live REST 留 Task 32。

## Product/architecture questions

- Raw/sanitized/manifest/curated rows 的各自 access/retention/review owner？
- Consent 要保存 export-time 與 analysis-time 雙 snapshot 嗎？
- Curated messages/summaries 應存新 Sheets、backend DB 或 object storage？
- Attachment-only 與 edited-message reconciliation 政策？

## Recommended next batch

Tasks 29–33：security/privacy/abuse threat model、non-deploying CI、documentation/demo/proposal、fixture-only integration exercise、final diagnostic/handoff。

## Copy-paste summary

Batch E Tasks26–28已全部完成。匯出工具可以 case/thread 選擇、分頁、checkpoint、full edit refresh、incremental/no-duplicate、atomic four files；匿名化以 raw+current consent 雙重 INCLUDED 為條件，Private/EXCLUDED/missing consent fail closed 或 placeholder，移除 IDs/姓名/email/URL/mention/student-ID-like text，保留 pseudonym/reply chronology，產生 redaction/consent/review artifacts；importer 只匯入 manifest+sanitized rows，支援 dry-run/CSV/mock/future API、idempotency/batch/retry/partial failure，無 raw attachment/clasp/network。完成時 Task27 完整測試 Python102/102、Portal25/25、GAS44/44、secret346/0；Task28 6/6，CSV第二次全5 skipped。仍需決定 retention/access/consent snapshot/curated storage，並在 Task32 實作 live boundaries 之前保持 fail closed。下一階段 Tasks29–33。
