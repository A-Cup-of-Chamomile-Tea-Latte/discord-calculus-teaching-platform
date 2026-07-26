# Batch D BOTS summary

## Outcome

Complete。Tasks 20–25 全部依序完成，沒有 skipped 或 blocked task；所有 runtime 都保持 fixture/dry-run，未連 Discord、未使用 token、未建立 production resource。

## Completed tasks

- Task 20：固定 multi-bot responsibility、permission/intent、event/command ownership、failure isolation 與 reversal architecture。
- Task 21：建立 strict typed Python common core、per-bot config/token isolation、redacted logging、health/lifecycle、contracts、narrow ports、idempotency及 network-free fakes。
- Task 22：建立 discord.py Course Assistant fixture skeleton、health、case write、membership alias/roles、case status、interaction hooks及 Private Support fail-closed delegation。
- Task 23：建立 explicit selected-thread Archive Reader、case→thread resolution、bounded pagination、local dump/follow handoff、checkpoint及 attachment metadata-only mapping。
- Task 24：建立 owner-authorized anonymous modal reply，清楚分流 course alias/fully anonymous，ephemeral acknowledgement、mention suppression及 private actor audit。
- Task 25：建立 backend-only Private Support service、Portal/Bot creation、participants、escalation、closure/retention hooks、public/analysis/export deny policy及 Discord permission spike plan。

## Skipped or blocked

- 無 skipped/blocked task。
- Live Discord adapters、identity provider、durable storage/outbox、persistent view registration、Private Support正式mechanism均刻意保持 mocked/unconfigured；這是安全邊界，不是 Batch D 未完成。

## Final verification

- Portal Vitest：5 files / 25 tests passed。
- GAS Vitest：6 files / 44 tests passed。
- Python：86 tests passed，2 個既有 discord.py/Python 3.14 upstream deprecation warnings。
- Secret scan：打包前最後 321 candidate files / 0 findings。
- Strict mypy：46 source files passed。
- Ruff format/lint、Prettier、GAS tsc：passed。
- Astro check：41 files / 0 errors / 0 warnings / 0 hints。
- Builds：Portal 14 static pages；GAS dist/Code.js + dist/appsscript.json。

## Key diagnostics

- Reader需要 View Channel + Read Message History；讀 content/attachments仍涉及 Message Content privileged capability，但沒有 writer methods或background polling。
- Anonymous/Public writes與Private Support必須使用 trusted Discord→internal identity mapping；Discord snowflake不是owner identity。
- Provider write、audit、repository、idempotency等多步操作仍有partial-failure風險，production需要durable outbox/reconciliation。
- Private Support維持 BACKEND_ONLY；private thread/restricted channel在隔離test guild通過完整visibility/permission/failure測試前不啟用。
- 現有AuditEvent contract缺 anonymous message-operation event，已登記 U-010。
- Python 3.14 + discord.py 2.7.1有2個 upstream deprecation warnings，Python 3.16前需追蹤升級。

## Product and architecture questions

- Portal/GAS到Course Assistant的authenticated transport、host與credential rotation由誰負責？
- Anonymous reply主要入口採persistent per-case button或 /calc reply case-number route？
- Private Support應永久backend-only，或承擔Discord private representation風險？
- Durable idempotency/outbox/checkpoint採SQLite/filesystem manifest或backend database？
- Audit/retention/consent正式contract與治理owner是誰？

## Recommended next batch

依使用者指示暫停。新環境先驗證archive hash、安裝依賴、跑 npm run check，再執行 Batch E Tasks 26–28；Private Support content必須維持排除。

## Copy-paste handoff

Batch D Tasks 20–25已全部完成且無skip/block：multi-bot架構、Python common core、Course Assistant、Archive Reader、anonymous modal reply、Private Support backend-only boundary都已落成fixture與報告。完整結果Portal 25/25、GAS 44/44、Pytest 86/86、mypy 46 files、Astro 41 files零診斷，Portal 14頁與GAS bundle build成功；只有2個discord.py在Python 3.14的上游deprecation warnings。未連Discord、無token、無production writes。主要mock/gap是live identity/Discord adapters、durable outbox/checkpoint/audit、persistent views與Private Support正式mechanism。Private Support固定無public case number、TEACHING_STAFF+EXCLUDED，public lookup/analysis/content export deny；通過隔離test-guild spike前維持BACKEND_ONLY。依使用者指示已準備在Task 25後打包暫停，新環境從Batch E Task 26繼續。
