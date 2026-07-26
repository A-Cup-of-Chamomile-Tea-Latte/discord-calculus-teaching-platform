# TASK-31 report — documentation, fixture demo, and proposal preface

## Outcome

Complete。已建立審查者、開發者、學生、助教與本機操作員的完整文件路徑，並以實際 fixture CLI E2E 驗證 demo 指令。文件明確標示所有 mock、fail-closed stub、尚未部署與待審查部分，未連接外部服務。

## Summary

- 根 README 現為可執行入口：平台責任表、十分鐘 demo、常用指令、資料邊界、專案導覽與角色導向文件索引。
- 新增架構概觀、資料模型、未部署關卡、fixture demo、dump/follow/review/import 操作流程。
- 新增學生與助教快速指南，以及可重用的 status/fallback 文案庫。
- Portal status 頁現標示 timezone、明確說明 fixture 不送出，並給出 NTU COOL、備援管道與 Private Support 不改貼公開區的 fallback。
- 提案草案加入英文專案名稱、繁中執行摘要與改寫前言，不宣稱機構核准、已整合或已驗證效益。
- 文件定位 Astro 為實際 framework/build system，templates 只是後續可選視覺起點，不取代資訊架構、契約與隱私邊界。

## Files changed

- `README.md`：重整專案入口、平台邊界、quick start 與文件導覽。
- `docs/architecture/OVERVIEW.md`：審查版架構、資料流、信任邊界與 Astro/template 說明。
- `docs/architecture/DEVELOPMENT.md`：更新安裝、quality surface、workspace 指令、Pages base-path dry run 與 QA checklist。
- `docs/architecture/README.md`：索引新架構概觀與開發指南。
- `docs/FIXTURE_DEMO.md`：可照讀的 Portal + export + anonymizer + importer 十分鐘 demo。
- `docs/DEPLOYMENT_NOT_DONE.md`：已做/未做、mock matrix、治理關卡、Pages 與 incident stop points。
- `docs/DATA_MODEL_OVERVIEW.md`：契約關係、主要 records、三個隱私維度與 raw-to-sanitized 變換。
- `docs/OPERATOR_WORKFLOW.md`：dump/follow/checkpoint/review/import 及失敗處理。
- `docs/guides/STUDENT_QUICK_GUIDE.md`：學生管道選擇、Discord profile/DM、匿名、案件與 fallback。
- `docs/guides/TA_QUICK_GUIDE.md`：一般 triage、Private Support、匿名回覆、匯出與事故處理。
- `docs/guides/SYSTEM_FALLBACK_STATUS_TEXT.md`：可重用的狀態/fallback 文案與狀態頁最少要素。
- `docs/PROPOSAL_PREFACE_DRAFT.md`：英文標題、繁中執行摘要與實際可審閱前言。
- `apps/portal/src/pages/status/index.astro`：更完整的 manual status、fixture 邊界與 fallback。
- `docs/reports/TASK-31-REPORT.md`：本報告。

## Commands executed

- 讀取 Tasks 02–30 已有 reports、Task 32 report、架構/Portal/contracts/fixtures/tools 文件與三個 CLI help。
- `npx prettier --write ...`：格式化 Task 31 Markdown 與 status Astro page。
- 以 `/tmp/codex-task31-demo.*` 實際執行 fixture export 兩次、anonymizer 與 Sheets importer dry-run。
- `source .venv/bin/activate && npm run check && npm run build && git diff --check`。

沒有外部 network application call、Discord/Google/email/OAuth、real data/credential、remote/commit/push/deploy。

## Verification

- Tests：Python 113/113 passed（含 fixture integration 1/1）；Portal 25/25；GAS 44/44。
- Linters/type checks：secret scan 373 candidates / 0 findings；Prettier/Ruff 通過；mypy 68 source files / 0 issues；Astro 41 files / 0 errors/warnings/hints；GAS TypeScript 通過。
- Builds：Portal 14 static pages；GAS `dist/Code.js` + `dist/appsscript.json`。
- Demo E2E：首次 export 4 messages/2 pages；重跑 0 added + `unchanged=true`；anonymizer 3 included + 1 placeholder、5 redaction events、0 review flags；importer dry-run 5 planned/5 succeeded/3 batches/0 retries。
- Manual checks：Task 31 指南內的檔案、CLI 參數、fixture case/thread ID 與輸出目錄一致；`git diff --check` 通過。
- Known warnings：只有既有 discord.py 2.7.1 / Python 3.14 的 2 個 deprecation warnings。

## Diagnostics

- 這個 repository 已有可重現的 fixture journey，但正式 provider 權限、身分、quota、rate limit、durable audit/consent 與 Pages access scope 仍是 production blockers。
- Portal status 是人工更新，不得被說成即時 monitoring/SLA。
- 文件中將 raw export、sanitized package 與 import 分成三個存取/審查邊界，避免因「已去識別化」字樣略過人工 review。
- 第一次 root check 因 shell 未啟用 `.venv` 而在找不到 `python` 時即停止；依文件啟用專案環境後完整通過，非 repository defect。

## Assumptions made

- 英文專案名稱沿用 `Discord Calculus Teaching Support Platform`，正式提案可再由授課團隊調整。
- 學生/助教指南都是文案草案，尚未代表課程政策。
- Demo 的 `CALC-000421` 及所有輸出只作 fixture verification；不從此推導正式 case prefix。
- 未來 templates 只做視覺起點，沿用 Astro、既有 IA、accessibility 與 privacy copy。

## Risks and blockers

- 高：文件不能取代正式 privacy/security/institutional review。Mitigation：Task 33 把未決項、production blockers 與 go/no-go 統一收旂。
- 高：GitHub Pages internet-public 與課程成員可見目標可能不相容。Mitigation：決定 course-session gate/hosting 後才部署，之前只使用 fixtures。
- 中：功能改變可以使文件過時。Mitigation：Task 33 檢查 mock/TODO/drift，未來把 demo 作為 release review checklist。

## Questions for ChatGPT discussion

- 正式試用前，誰是學生文案、狀態頁、隱私告知與 fallback 的 accountable owner？
- Portal 若必須 course-member-only，是否改用支援 authenticated session 的 hosting，而不使用 public GitHub Pages？
- 提案對試用成功的可量化指標，應由誰在不製造監控壓力的前提下定義？

## Recommended next action

執行 Task 33 final diagnostic and handoff：整合 Tasks 29–32，統一執行 final inventory/check/build/base-path/secret-real-data/mock-drift 檢查，並對 Pages access scope、第一個 read-only live spike 與 production go/no-go 提出明確順序。

## Copy-paste handoff

Task 31 已完成審查用文件套件：重整根 README，新增架構概觀、本機開發、fixture demo、尚未部署、資料模型、dump/follow/review/import 操作流程、學生/助教快速指南與 fallback/status 文案；Portal status 也加入 fixture 不送出、manual timestamp 與備援路徑。提案草案現有英文標題、繁中執行摘要與不誇大的前言。文件明確把 Astro 定位為 framework/build system，templates 只是可選視覺起點；並標示 Discord/GAS/Sheets/email/OAuth/live export 仍未連接。實際 fixture demo：export 4 messages/2 pages，重跑 unchanged=true，anonymizer 3 included+1 placeholder，import dry-run 5/5。完整驗證：Python 113/113、Portal 25/25、GAS 44/44；secret 373/0、mypy 68 files、Astro 41 files 0 diagnostics；Portal 14 pages/GAS bundle build 通過，只有既有 2 個 discord.py/Python 3.14 warnings。未做 deploy/push/cloud/live/real data。建議下一步 Task 33 final diagnostic，重點收旂 Pages public-vs-course-only、正式權限/同意/保留與 bounded read-only spike 的 go/no-go。
