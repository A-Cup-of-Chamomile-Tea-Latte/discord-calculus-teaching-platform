# TASK-32 report — fixture-only integration journey and production gates

## Outcome

Complete。一個 repeatable Python integration test 已以 contracts/ports/fixture adapters 串起 Portal fixture question、case/thread mapping、Course Assistant writer、Portal lookup、anonymous modal/service、Archive Reader explicit dump、Task 26 file export、Task 27 anonymization 與 Task 28 dry-run import。Private Support 不公開，所有 bot config 為 fixture mode，沒有 polling/network/credential。Production plan 另列 0–7 gates、evidence 與每關 rollback/stop point，沒有部署。

## Summary

- Portal submit/case service boundary以已驗證 Case/CaseMessage fixtures作輸入，Course Assistant 透過 `DiscordCourseWriter` test double 建立指定 thread mapping，不直接依賴 Discord runtime。
- Portal search 逐筆通過 CaseLookupResponse contract；Private Support fixture `caseNumber=null`，不出現在 FOUND projection，exporter selection 也 fail closed。
- Anonymous follow-up 實際建立 modal definition（max 1800），並經 Course Assistant authorization/service/writer 發佈；audit 只有 metadata，無 body。
- Archive Reader 在 explicit `dump()` 前 0 reads；page size 2 後剛好 2 reads/4 messages，0 writes。
- Exporter 產生 4-message raw package；anonymizer 產生 3 included + 1 placeholder；importer dry-run 5 planned/5 success。
- Production plan 要求 data policy→read-only Discord→writer→Private Support→identity/auth→storage/API→Portal access→E2E rehearsal 順序，每階段可獨立撤銷/回到 fixture。

## Files changed

- `tests/integration/test_fixture_journey.py`：完整 fixture journey。
- `tests/integration/README.md`：流程、邊界與 no-network 說明。
- `docs/architecture/PRODUCTION_INTEGRATION_PLAN.md`：production gates/evidence/rollback 與第一個 live spike。
- `docs/reports/TASK-32-REPORT.md`：本報告。

## Commands executed

`ruff format/check tests/integration/test_fixture_journey.py`、strict mypy、directed pytest、Prettier architecture/report docs。完整 root check/build 在 Tasks 29–31 整合後由 Task 33 統一執行。無 Discord/Google/GitHub/email/OAuth/network/credential/deploy/commit/push。

## Verification

- Integration test：1/1 passed，實際走過八個指定步驟與三個 safety assertions。
- Linters/type checks：Ruff 通過，strict mypy 1 source file / 0 issues。
- Component evidence：Course Assistant 2 fixture writes（create + anonymous reply）；Archive Reader 2 reads/0 writes；export 4 messages；anonymizer 3+1；import dry-run 5/5。
- Full repository counts 由 Task 33 最終報告記錄。

## Diagnostics

- Portal/GAS 是 TypeScript/static components，Python integration 不直接 import framework code；用共享 JSON contracts/fixtures當跨語言 boundary，而 component 各自的 Vitest 已驗證 adapter rendering/behavior。
- Archive Reader handoff 與 Task 26 file exporter都已驗證，但尚未有一個 production durable queue/transaction 直接連二者；fixture journey 以共享合約資料作交接。
- Real-service 第一步不應是 full deployment，而是獨立 test guild 的單 thread/read-only Archive Reader spike。

## Assumptions made

- Cross-language integration 以 versioned JSON fixtures/contracts 為 authoritative boundary，不在 Python test 模擬 Astro/GAS framework internals。
- Mock case number 由 fixture case service事先分配，Course Assistant 只負責 writer representation/mapping。
- Fixture Archive Reader handoff 與 local exporter各自對同一 CaseMessage contract thread 驗證，production durable handoff 留在 gate 5。

## Risks and blockers

- 高：未驗證任何 real provider permission/auth/rate limit/quota。Mitigation：只按 plan gates 做 bounded spikes，每關需 evidence/owner/rollback。
- 高：GitHub Pages course-only access U-011 未決。Mitigation：Task 33 做正式決策建議，之前不發布可識別 case data。
- 中：Archive→file export 無 durable atomic handoff。Mitigation：production gate 5 驗證 queue/store/outbox/recovery。

## Questions for ChatGPT discussion

- 是否核准 read-only Archive Reader test-guild spike 為第一個 real-service experiment？
- Durable archive→export handoff 採 SQLite/local journal、backend queue/outbox，或直接 service DB？
- Portal 的 course-session gate 與 GitHub Pages hosting 是否相容，或需改用可驗證存取的 host？

## Recommended next action

執行 Task 33 最終診斷：在 Tasks 29–31 合併後跑 full check/build/inventory/secret-real-data/TODO/dependency/mock/drift/docs/base-path/cloud-readiness checks，建立 implementation status、ordered next steps 與無 secrets handoff。

## Copy-paste handoff

Task 32 已完成一條 repeatable fixture-only integration test：Portal question/case fixture→Course Assistant writer thread mapping→Portal lookup→anonymous modal/service→Archive Reader explicit 2-page dump→Task26 4-message files→Task27 3 included+1 placeholder→Task28 5-row dry-run。Private Support caseNumber=null/不公開且 exporter fail closed；reader 在 dump 前 0 reads，全程 fixture configs network_enabled=false、無 token/polling/cloud。Integration 1/1、Ruff/mypy 通過。已寫 production gates/rollback：data policy、read-only Discord、writer、Private Support、auth、storage、Portal access、E2E rehearsal。建議第一個 real spike 限於獨立 test guild + 獨立 Archive Reader + 單 fictional thread + 單次 read-only dump，驗證 permissions/content/rate-limit/audit/revoke，不同時開 writer/Portal/Sheets/Private Support。
