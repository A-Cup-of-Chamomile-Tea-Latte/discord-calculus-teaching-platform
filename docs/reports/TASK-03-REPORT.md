# TASK-03 report — 可逆 monorepo 骨架

## Outcome

完成。建立所有指定目錄、責任文件、保守 ignore 規則，並初始化沒有 remote 的本機 Git repository（`main` 分支）。沒有加入產品程式碼、真實資料或憑證。

## Summary

建立 Portal、GAS、四個 bot 區域、本機資料工具、共用 contracts、fixtures、tests、architecture docs 與非部署 workflow 的單一儲存庫骨架。根 README 說明平台邊界與 monorepo 理由；每個主要區域及子元件均說明責任與非責任。

## Files changed

- `README.md`：專案目的、平台邊界、安全狀態、目錄及 monorepo 理由。
- `.gitignore`：涵蓋 Python、Node/Astro、Apps Script、本機資料、憑證、環境檔與 macOS；明確保留 `.env.example` 與 fixtures。
- `.editorconfig`：UTF-8、LF、縮排與 Markdown 規則。
- `apps/**/README.md`：Portal 與 GAS 責任邊界。
- `bots/**/README.md`：common、course assistant、archive reader、moderation 邊界。
- `tools/**/README.md`：匯出、匿名化與 Sheets importer 邊界。
- `contracts/**/README.md`：schemas 與 examples 邊界。
- `fixtures/**/README.md`：users、cases、messages、exports 的虛構資料規則。
- `tests/**/README.md`：contract 與 integration 測試邊界。
- `docs/architecture/README.md`、`.github/workflows/README.md`：架構文件及非部署 CI 邊界。
- `.git/`：以 `git init -b main` 建立的本機 metadata；沒有 remote、commit 或 secrets。
- `docs/reports/TASK-03-REPORT.md`：本報告。

## Commands executed

- `mkdir -p ...`：建立 Task 03 指定的 22 個目錄。
- `git init -b main`：在 Task 02 判定安全後初始化本機儲存庫。
- `git check-ignore`：驗證 secrets 被忽略且 `fixtures/exports` 不被忽略。
- `git status --short --branch`、`git remote -v`：驗證分支與 remote 狀態。

## Verification

- Tests: 無產品程式碼測試；scaffold shell 驗證 1/1 通過。
- Linters/type checks: 不適用，Task 04 才建立工具鏈。
- Builds: 不適用。
- Manual checks: 8/8 類別通過——22 個必需目錄存在、根 README 存在、`.gitignore` 存在、`.editorconfig` 存在、`.env` 被忽略、`credentials.json` 被忽略、fixture export 不被忽略、分支為 `main` 且 remote 為 0。

## Diagnostics

- Git 狀態是 `No commits yet on main`；所有專案檔目前均為未追蹤，符合剛初始化狀態。
- 目錄中共有 25 份區域責任／保留文件（不含原指令包文件與本報告）。
- 沒有建立 remote、commit、部署設定或應用程式功能。

## Assumptions made

- `main` 作為本機初始分支是可逆且符合未來 CI 的保守預設。
- 空目錄以 README 保留，並利用內容同時記錄責任邊界，不另加 `.gitkeep`。
- 本機真實匯出使用根層 `exports/` 或 `local-data/`，而 `fixtures/exports/` 永遠保持可追蹤。

## Risks and blockers

- 低度：尚無 lockfile 與自動品質檢查；Task 04 將補齊。
- 低度：目前所有檔案尚未 commit。依規格，只有在 worktree clean 時才偏好逐任務 commit；初始 repository 無基準 commit，因此本任務沒有自行 commit。
- 無阻擋 Task 04 的問題。

## Questions for ChatGPT discussion

無新增會阻擋工具鏈的產品問題。既有未決事項持續記錄於 `docs/decisions/UNRESOLVED.md`。

## Recommended next action

執行 Task 04：建立 Python 與 npm workspace 的專案本機工具鏈、統一命令介面、secret scanning smoke test 與不部署的 CI。

## Copy-paste handoff

> TASK-03 已完成：建立指定的 22 個 monorepo 目錄與 25 份責任／保留文件，根 README 說明 NTU COOL、Discord、Portal、GAS/Sheets 與本機工具邊界及採 monorepo 的理由；新增保守 `.gitignore` 與 `.editorconfig`。已初始化本機 Git `main` 分支，remote 為 0，沒有 commit、部署、產品程式碼、token 或真實資料。scaffold 驗證 1/1 通過，8/8 類別手動檢查通過，fixtures 不會被 ignore。無 blocker，下一步是 TASK-04 專案本機工具鏈與品質基線。
