# TASK-08 report — 虛構 fixtures 與 mock adapters

## Outcome

完成。37 筆契約化 records、五種 mock adapter scenarios、資料字典、seed/reset 文件及真實資料 guard 全數通過。

## Summary

建立四個虛構 users（其中三名學生）、全部使用 `example.com` 的 email、兩個班別、五種一般案件狀態、匿名與 alias 案件、分析排除的 Private Support、含回覆／編輯／附件／混合同意的 thread、四種 activation code 狀態及兩個 export manifests。Portal、GAS、bots、tools 共同使用 `case_000421` / `CALC-000421`。

## Files changed

- `fixtures/MANIFEST.json`：10 個 record sets 與四 lane 共用情境索引。
- `fixtures/users/*.json`：4 users、4 emails、4 Discord accounts、3 memberships、4 consents、4 activation codes。
- `fixtures/cases/cases.json`：5 個 GENERAL（每個狀態各一）與 1 個 PRIVATE_SUPPORT。
- `fixtures/messages/case-000421-thread.json`：4 則有 reply graph、edit、attachment metadata 與混合同意的訊息。
- `fixtures/exports/export-manifests.json`：一般案件 dump 與 Private Support analysis-excluded manifest。
- `fixtures/adapters/case-lookup-responses.json`：FOUND / NOT_FOUND 兩種公開查詢回應。
- `fixtures/adapters/mock-adapters.json`：case lookup、Discord thread fetch、Sheets storage、email delivery、activation-code validation 五種語言中立 mock interfaces/scenarios。
- `fixtures/README.md`：immutable seed/reset 流程與真實資料目錄界線。
- `fixtures/DATA_DICTIONARY.md`：資料集數量、共用情境、ID/label、隱私與 adapter 字典。
- `tests/contract/test_fixture_scenarios.py`：schema、隱私、跨 record、完整狀態與 adapter 測試。
- `docs/reports/TASK-08-REPORT.md`：本報告。

## Commands executed

- `python -m pytest tests/contract/test_fixture_scenarios.py -q`：Task 08 專屬測試。
- `python -m ruff format tests/contract/test_fixture_scenarios.py`：修正一個格式差異。
- `npm run check`：Batch A 全部 secret scan、format、lint、typecheck 與 tests。

## Verification

- Fixture tests: 10/10 passed。
- Contract validation: 37/37 fixture records 均通過對應 Task 07 schema。
- Full tests: 35/35 passed，0 failed（0.12s）。
- Linters/type checks: Ruff lint 全通過；Ruff format 9 files formatted；Prettier 通過；兩個 TS workspaces 通過；mypy 9 source files、0 issues。
- Secret/data guards: 169 candidate files、0 secret findings；fixtures 中無 `ntu.edu.tw`、臺灣／常見十位電話格式、private-key/GitHub/Google key pattern；所有 email domain 都是 `example.com`。
- Builds: 本任務無產品 build。

## Diagnostics

- Schema 只驗證單筆結構；Task 08 測試另補 user/case/message parent 外鍵、course alias 組合與共用 case 參照。
- 完全匿名是對一般成員的顯示模式；fixture 仍保存受授權管理用途的 `authorUserId`，符合 shared context。
- Activation validation mock 只記錄 fixture ID、時間與 expected boolean，不保存或回顯 presented nonce。
- Private Support 沒有公開 case number，也沒有出現在 case lookup adapters；其 manifest 只作 analysis-excluded audit fixture。

## Assumptions made

- `case_000421` 是後續所有 lane 的 canonical happy path；consumer 可複製資料到 memory，但不得各自改寫來源 fixture。
- 虛構姓名採英文植物／教學代稱並加 `Example`，Discord snowflake 使用人工連號；沒有映射真實人物或帳號。
- Email mock 的 `ACCEPTED_BY_MOCK` 只表示 adapter 測試結果，不表示寄信成功或已選定 provider。

## Risks and blockers

- 中度：Mock adapters 不驗證外部 API、quota、權限、CORS 或 network failure；各後續 lane 仍需明確 technical spike。
- 低度：Privacy guard 是 pattern-based，不能證明任意文字絕對不對應真實人；fixtures 仍需 code review，且禁止從正式資料複製。
- 低度：目前只為 canonical case 建完整 thread；各 lane 如需 edge case 應新增最小 fixture，而不是改動 canonical happy path。
- 無阻擋 Batch B–E 的問題。

## Questions for ChatGPT discussion

沒有阻擋下一批的問題。正式 case prefix、Private Support mechanism 與 consent withdrawal 仍保留在未決清單。

## Recommended next action

Batch A 已完成。依任務矩陣，下一步優先執行 Batch B（Tasks 09–14 Portal）；GAS、bots、export lanes 可在後續獨立 session/worktree 依同一 contracts/fixtures 實作。

## Copy-paste handoff

> TASK-08 已完成：建立 37 筆完全虛構且通過 Task 07 schemas 的 records，含 4 users/`example.com` emails、班別 01/02、五種 GENERAL 狀態、alias、完全匿名、PRIVATE_SUPPORT+EXCLUDED、4 則具 replies/edit/attachment/mixed consent 的 thread、activation code 四狀態與 export manifests。五種 mock adapters（case lookup、Discord fetch、Sheets、email、activation validation）均不連外；Portal/GAS/bots/tools 共用 `case_000421`。Fixture tests 10/10、全套 35/35、mypy 9 files 0 issues、secret scan 169 files 0 findings；另 guard `ntu.edu.tw`、電話與明顯 secret pattern。Batch A 無 blocker，下一步建議 Batch B Portal。
