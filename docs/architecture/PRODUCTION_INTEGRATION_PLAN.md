# Production integration plan and rollback gates

Task 32 只驗證 fixture/mock adapters。本文是後續 production spikes 的順序與回滾點，不是部署授權。目前無 production Discord、OAuth、email、Apps Script deployment、Spreadsheet 或 GitHub Pages release。

## Gate sequence

| Gate                    | Bounded spike                                                                          | Evidence required                                                                               | Rollback / stop point                                          |
| ----------------------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| 0. Data policy          | 核准 Task 29 classification、retention、consent snapshot、Private Support isolation    | Named privacy/security owners; approved threat model and deletion test                          | 無核准就保持 fixtures only                                     |
| 1. Discord read-only    | 在獨立 test guild 以 `dump_bot` 只讀取一個 allowlisted fictional thread            | Token scope、VIEW_CHANNEL/READ_MESSAGE_HISTORY、MESSAGE_CONTENT、audit、rate-limit、revoke test | 撤銷 test token/app access；live adapter恢復 fail closed       |
| 2. Discord writer       | 在 test guild 建立一個 fictional forum thread、一則 anonymous modal reply              | Separate app/token、least privilege、idempotency、mention suppression、cleanup trace            | 刪除 test resources、撤銷 token；保留 fixture writer           |
| 3. Private Support      | 依 `PRIVATE_SUPPORT_SPIKE.md` 驗證 backend-only 與候選 Discord representation          | Owner/assigned/unassigned/student/archive-reader visibility matrix，archive/close/restart tests | 任一 leakage 立即中止，回到 BACKEND_ONLY                       |
| 4. Identity/auth        | 測試 OAuth + course-membership authority + email/activation flow，全使用專用測試帳號   | Session/CSRF/state/redirect/rate-limit/revocation evidence；no token in logs                    | 撤銷 OAuth client/keys，禁用 non-fixture route                 |
| 5. Storage/API          | 對新測試 Spreadsheet/backend 做 schema dry-run、small batch、duplicate/partial failure | Auth、row-level idempotency、locking、audit、backup/restore/delete test                         | 停用 endpoint、撤銷 credential、刪除 fictional rows            |
| 6. Portal access        | 在非公開 preview 驗證 base path、course-session gate、single lookup/list routes        | Task 33 U-011 決策、unauthenticated-field review、access tests                                  | 不發布 Pages，回到 local static build                          |
| 7. End-to-end rehearsal | 完全 fictional test accounts/data 跑一次 explicit submit→export→sanitize→review→import | Cross-system trace IDs、human approval、incident/rollback drill、deletion verification          | 逐 provider revoke/disable，清理 test data，不保留 raw exports |

## First real-service spike

第一個 real-service spike 應是 Gate 1：獨立 test guild、獨立 `dump_bot` application、單一 fictional thread、單次 explicit dump。它只驗證讀取權限、message-content availability、pagination/rate limit、token revocation 與 audit，不開啟 writer、Portal、Sheets 或 Private Support。

## Cross-cutting release gates

- 每個 provider 使用獨立 credential/least-privilege identity，secrets 只在 runtime secret store。
- Raw export、sanitized package、manifest/audit 與 curated rows 有獨立 access/retention/deletion rules。
- 任何 analysis/import 前重新解析 consent，並保存不含原文的 decision snapshot/audit。
- Production adapter 不得在錯誤時 fallback fixture/public channel/unrestricted sheet；一律 fail closed。
- 所有寫入都需 idempotency、bounded retry、partial-failure reconciliation 與可演練 rollback。
- 通過 Task 30 non-deploying CI 只是前置，不等於隱私/權限/營運核准。
