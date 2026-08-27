# GAS deployment runbook

本機 source 可產生獨立與附著兩種 target。2026-08-28 的 canonical cloud baseline 為：

- standalone immutable v14，owner-only Execution API；cloud pull-back 與核准 source 完全相同，
  Execution API health 與一封受控 `MailApp` 實寄均通過，重複 delivery 為 no-op；immutable v13
  保留作 rollback；
- bound immutable v6，source 已對齊，但 status-digest trigger 仍刻意停用；
- Script ID、deployment ID、Sheet ID 與 credentials 只保存在 gitignored local state。

## Target ownership

| Target     | Cloud container   | Responsibilities                                 |
| ---------- | ----------------- | ------------------------------------------------ |
| standalone | `獨立 GAS`        | owner-only Execution API Bridge、跨檔案操作      |
| bound      | `Server Database` | 試算表管理選單、active spreadsheet dry-run/apply |

兩者共用同一份 schema/domain source；不得各自手改出兩套 business rules。

## Intended ownership

- Intended Apps Script owner/deployer：專案專用帳號。
- 所有 cloud project、Sheet、deployment 與 Script Properties 都應由此專用帳號或日後正式指定的課程服務帳號管理，不使用學生個人帳號。
- 本機需要人工瀏覽器操作時，使用 Chrome 顯示名稱 `Ding Ding` 的設定檔；不要改用其他 Chrome profile 的 session。clasp 仍使用命名 OAuth profile `ntusupercool`。

## Preconditions

1. 確認 branch、code baseline、schema version 與目標 environment。
2. 確認 repository secret scan 為 0 findings，且 fixture data 不含真實個資。
3. 確認 Google Auth Platform publishing status。External／Testing 且含 Sheets scope 時，
   refresh token 通常約 7 天失效；24h production 前必須選擇 Production 或接受週期性人工重授權。
4. 由授權者確認 Sheet owner、資料 retention、Execution API access policy 與 incident owner。

## Controlled deployment sequence

1. 以 `ntusupercool@gmail.com` 登入 clasp；不要共用個人 `.clasprc.json`。
2. 只使用已確認的 Drive 專案資料夾、`獨立 GAS` 與 `Server Database`；不要改動其他 project。
3. 使用被 gitignore 的 `.clasp.standalone.json` 與 `.clasp.bound.json`，只在本機填入真實 script ID。
4. 在 Apps Script Project Settings 設定 Script Properties；不要把 values 寫入 source 或 shell history。
5. 本機執行 typecheck/test/build，分別檢查 `dist/standalone/` 與 `dist/bound/`。
6. 先唯讀 pull 至 ignored inventory、確認遠端是空白 scaffold，再執行 scoped `clasp push`。
7. push 後建立 immutable version；standalone 更新既有 owner-only API executable deployment，
   先做 synthetic-only `scripts.run` health、Cloud → Local → Cloud command、Local → Cloud projection、
   duplicate-safe replay 與 cleanup no-op。Bound 只建立 immutable version，不安裝 trigger。
8. Standalone 維持 `executionApi.access=MYSELF`，不建立公開 Web App。任何擴大 access 或新增 HTTP endpoint 都需另做 security／privacy approval。
9. cleanup 只能在無人工同時編輯 Sheet 的受控窗口執行；dry-run 與 apply 必須使用同一 nonce，
   blank／duplicate primary key、formula 或未知列都應 fail closed。
10. 確認 request validation、quota、logging redaction、rollback version、deployment inventory 與
    OAuth longevity gate 後，才可考慮 production target。

2026-08-28 的 provider smoke 使用獨立、mode `0600`、同時含 Sheets 與
`script.send_mail` 的 OAuth credential；不覆寫 remote v13 core 的既有 Sheets-only credential。
驗收紀錄只保存版本與 PASS／FAIL，不保存真實收件地址、驗證碼或信件截圖。

## Rollback

- Apps Script 以 immutable version 建 deployment；保留上一個已知良好 version。
- 發現資料曝露、錯誤 routing 或 quota 異常時，先停用／撤銷 deployment，再復原 Script Properties 與 Sheet access。
- 真實 `.clasp.json`、deployment ID、Sheet ID 與 credentials 不進 git；若誤提交，立即撤銷／rotate，不能只刪除 commit。

## Non-goals

- GAS 不連 Discord Gateway，不維持 websocket，不代替 Python bots。
- GAS 不保存 Discord bot token、OAuth client secret 或 raw activation code。
- 本 runbook 記錄已核准流程，但不自行授權新的 login、project creation、email、public endpoint、
  production cutover 或資料範圍擴張。
