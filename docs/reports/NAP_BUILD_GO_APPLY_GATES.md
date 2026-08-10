# NAP BUILD：GO-APPLY 前置門檻

> 歷史狀態：本文件記錄 2026-07-28 的 pre-apply gate。Discord 測試伺服器已於
> 2026-07-30 依後續核准完成佈建；目前狀態以
> `DISCORD_INFRASTRUCTURE_PROVISIONING_REPORT_2026-07-30.md` 與
> `docs/IMPLEMENTATION_STATUS.md` 為準，不得重新把本頁當成現行 GO／NO-GO 判斷。

目前狀態是 **NO-GO**。本文件不是套用授權。

## 必須全部完成

1. online GPT／產品決策明確核准 proposed config 版本與 legacy lifecycle migration。
2. 指定 privacy、security、data、system owners，核准 retention／deletion／backup／consent withdrawal。
3. 建立完全隔離、只含虛構成員與內容的 Discord 測試伺服器，記錄 server ID 但不得提交 Git。
4. 分別建立 `course_assistant` 與 `dump_bot` Bot Application；禁止共用 token。
5. 人工核對 OAuth scopes、intents、Bot role hierarchy、Forum permissions、Private Support overwrite 與 `dump_bot` 讀取白名單。
6. token 只放入核准的 secret store；完成洩漏撤銷演練，任何 token 不得進聊天、Git、ZIP 或 log。
7. 在普通學生、Guest、special guest、Staff、Administrator 與兩 Bot 帳號逐一驗證 effective visibility。
8. 先執行 dry-run，兩位審查者核對 plan／diff／rollback；備妥逐項停止與回復方式。
9. 建立 `/health`、audit、rate-limit、partial-failure reconciliation 與 kill switch。
10. Portal、Google／Sheets、Email、OAuth 與 AI API 仍須分別取得新授權；Discord GO-APPLY 不自動涵蓋它們。

## 明確停止條件

- plan 出現 `ADMINISTRATOR`、超出白名單的 Bot scope、未辨識或 unmanaged resource 刪除。
- Private Support 對 Student／Guest 可見，或內容進入公開 lookup／分析。
- proposed config、generated docs 與實際 plan hash／版本不一致。
- rollback 未演練、owner 不在場、token 儲存位置未核准、使用真實學生資料。

在收到新的明確指令前，所有開發與操作都停在本機 fixture preview。
