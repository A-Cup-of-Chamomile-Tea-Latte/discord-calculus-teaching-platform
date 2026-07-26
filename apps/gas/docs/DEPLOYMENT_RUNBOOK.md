# GAS deployment runbook (future, manual only)

Task 15 只建立 local scaffold。沒有執行下列任何外部動作。

## Intended ownership

- Intended Apps Script owner/deployer：`ntusupercool@gmail.com`
- 所有 cloud project、Sheet、deployment 與 Script Properties 都應由此專用帳號或日後正式指定的課程服務帳號管理，不使用學生個人帳號。

## Preconditions

1. 完成 Tasks 16–19 的 schema/API/nonce/email skeleton 與 local tests。
2. 完成 Task 29 security/privacy review、Task 30 CI 與 Task 33 go/no-go。
3. 由授權者確認 Google account、Sheet owner、資料 retention、web-app access policy 與 incident owner。
4. 確認 repository secret scan 為 0 findings，且 fixture data 不含真實個資。

## Future manual actions requiring explicit approval

1. 以 `ntusupercool@gmail.com` 登入 clasp；不要共用個人 `.clasprc.json`。
2. 建立獨立 Apps Script project 與受控 Sheet，記錄 owner/用途/rollback；不要改動其他現有 project。
3. 將 `.clasp.json.example` 複製成被 gitignore 的 `.clasp.json`，只在本機填入真實 script ID。
4. 在 Apps Script Project Settings 設定 Script Properties；不要把 values 寫入 source 或 shell history。
5. 本機執行 typecheck/test/build，檢查 `dist/Code.js` 與 `dist/appsscript.json`。
6. 經 code review 後才執行 `clasp push`；先建立 development deployment，再做 fixture-only smoke test。
7. 另行審查 web-app `execute as` / `who has access`；scaffold manifest 安全預設 `MYSELF`，任何擴大都需 security/privacy approval。
8. 確認 request validation、quota、logging redaction、rollback version 與 deployment URL inventory 後，才可考慮 production deployment。

## Rollback

- Apps Script 以 immutable version 建 deployment；保留上一個已知良好 version。
- 發現資料曝露、錯誤 routing 或 quota 異常時，先停用／撤銷 deployment，再復原 Script Properties 與 Sheet access。
- 真實 `.clasp.json`、deployment ID、Sheet ID 與 credentials 不進 git；若誤提交，立即撤銷／rotate，不能只刪除 commit。

## Non-goals

- GAS 不連 Discord Gateway，不維持 websocket，不代替 Python bots。
- GAS 不保存 Discord bot token、OAuth client secret 或 raw activation code。
- 本 runbook 不授權 login、project creation、push、deploy、email 或 Sheet mutation。
