# GAS deployment runbook

本機 scaffold 現在可產生獨立與附著兩種 target。2026-08-10 已由 owner 建立空白的
`獨立 GAS` 與附著於 `Server Database` 的 GAS；Script ID、deployment ID 與 credentials
只保存在 gitignored local state。

## Target ownership

| Target     | Cloud container   | Responsibilities                                 |
| ---------- | ----------------- | ------------------------------------------------ |
| standalone | `獨立 GAS`        | Web App/API、跨檔案操作、外部整合入口            |
| bound      | `Server Database` | 試算表管理選單、active spreadsheet dry-run/apply |

兩者共用同一份 schema/domain source；不得各自手改出兩套 business rules。

## Intended ownership

- Intended Apps Script owner/deployer：`ntusupercool@gmail.com`
- 所有 cloud project、Sheet、deployment 與 Script Properties 都應由此專用帳號或日後正式指定的課程服務帳號管理，不使用學生個人帳號。
- 本機需要人工瀏覽器操作時，使用 Chrome 顯示名稱 `Ding Ding` 的設定檔；不要改用其他 Chrome profile 的 session。clasp 仍使用命名 OAuth profile `ntusupercool`。

## Preconditions

1. 完成 Tasks 16–19 的 schema/API/nonce/email skeleton 與 local tests。
2. 完成 Task 29 security/privacy review、Task 30 CI 與 Task 33 go/no-go。
3. 由授權者確認 Google account、Sheet owner、資料 retention、web-app access policy 與 incident owner。
4. 確認 repository secret scan 為 0 findings，且 fixture data 不含真實個資。

## Controlled deployment sequence

1. 以 `ntusupercool@gmail.com` 登入 clasp；不要共用個人 `.clasprc.json`。
2. 只使用已確認的 Drive 專案資料夾、`獨立 GAS` 與 `Server Database`；不要改動其他 project。
3. 使用被 gitignore 的 `.clasp.standalone.json` 與 `.clasp.bound.json`，只在本機填入真實 script ID。
4. 在 Apps Script Project Settings 設定 Script Properties；不要把 values 寫入 source 或 shell history。
5. 本機執行 typecheck/test/build，分別檢查 `dist/standalone/` 與 `dist/bound/`。
6. 先唯讀 pull 至 ignored inventory、確認遠端是空白 scaffold，再執行 scoped `clasp push`。
7. push 後建立 immutable version；standalone 先做 fixture-only smoke test，bound 先從選單做 dry-run。
8. 另行審查 web-app `execute as` / `who has access`；scaffold manifest 安全預設 `MYSELF`，任何擴大都需 security/privacy approval。
9. 確認 request validation、quota、logging redaction、rollback version 與 deployment URL inventory 後，才可考慮 production deployment。

## Rollback

- Apps Script 以 immutable version 建 deployment；保留上一個已知良好 version。
- 發現資料曝露、錯誤 routing 或 quota 異常時，先停用／撤銷 deployment，再復原 Script Properties 與 Sheet access。
- 真實 `.clasp.json`、deployment ID、Sheet ID 與 credentials 不進 git；若誤提交，立即撤銷／rotate，不能只刪除 commit。

## Non-goals

- GAS 不連 Discord Gateway，不維持 websocket，不代替 Python bots。
- GAS 不保存 Discord bot token、OAuth client secret 或 raw activation code。
- 本 runbook 不授權 login、project creation、push、deploy、email 或 Sheet mutation。
