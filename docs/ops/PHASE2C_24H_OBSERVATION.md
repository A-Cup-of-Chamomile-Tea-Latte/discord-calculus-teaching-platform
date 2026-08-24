# Phase 2C 真實 24 小時 observation

## Current observation window

- 開始：2026-08-23 17:12（Asia/Taipei）
- 完成：2026-08-24 17:16（Asia/Taipei）
- 狀態：`PASS`
- Production authority：remote SQLite
- Production writer：remote Linux only
- Production schema：v6；repository candidate v10 尚未部署

## Final receipt

- 2026-08-24 17:12 後的 owner-only `/ops status` 顯示課程助理、封存服務與雲端同步均
  `HEALTHY`，schema v6，案件操作、雲端同步、私人匯出與 manual attention queue 均為 0。
- 2026-08-24 17:16 的 remote 唯讀核對顯示 `/opt/calculus-discord/current` 仍指向已驗證的
  v6 release；三個 systemd services 均 `active`／`enabled`。
- root-owned 受限部署入口仍存在且保持原權限；本次只核對，沒有執行 deployer。
- Mac LaunchAgent 與本機 runtime process 均為 0；remote 持續是唯一 production writer。
- GPT Pro 已接受上述安全摘要、single-writer 證據與既定成功／停止條件，故現行 v6 baseline 的
  24 小時 observation 判定 PASS。

## Superseded defect window

2026-08-22 18:33 的第一個窗口因 close → immediate reopen 的 SQLite／Discord side-effect 不一致而標記
`DEGRADED / NOT ELIGIBLE FOR PASS`。該窗口只保留為 defect evidence，不再作為目前狀態。修復版完成
v5 → v6、Public smoke 與安全狀態核對後，才從 2026-08-23 17:12 重新起算。

## Current start receipt

- Mac LaunchAgents absent；本機 runtime process 為 0。
- Remote `course-assistant`、`dump-bot`、`data-bridge` 均 active／enabled。
- 三個服務各有不同 MainPID，啟動後 restart count 為 0。
- Cutover repair、fresh service health、data-bridge backlog drain 均 PASS。
- Schema v6 lifecycle 修復版 Public create／finalize／close／immediate reopen smoke PASS。
- owner-only `/ops status` 顯示三服務 `HEALTHY`、queue 歸零、manual attention 為 0。
- Smoke 後三個服務仍 running，沒有 warning。

## Historical finding：close → immediate reopen

- Public create、互動設定、標題更新與 `/case close` 均成功。
- 原發文者立即按「繼續詢問」後，SQLite transition 先變為重新開啟；Discord thread 的解封／改名仍在
  等待。再次點擊時系統回覆案件已開啟，但畫面仍保留 CLOSED 標題。
- 這證明現有流程缺少 durable pending side effect／reconciliation；不能把問題歸因為使用者操作限制。
- 學生向隱私說明也暴露 `reopen_count`、dump 等內部術語，須一併修正。
- 目前不再重複操作該測試 thread。服務保持單一 remote writer；尚無 duplicate writer、DB corruption
  或 service restart 證據，因此未觸發整體 rollback。
- 此 finding 屬於 2026-08-22 的已作廢窗口；修復、新 smoke 與後續 24 小時 observation 均已完成。

## Final checkpoint gate

- [x] v5 live consistent copy 升級到 v6、integrity 與 migration ledger PASS。
- [x] 三個 remote services 使用同一個 v6 release，fresh health PASS，Mac writer 為 0。
- [x] Public close／immediate reopen smoke 收斂；沿用案號，沒有重複 lifecycle side effect。
- [x] owner-only `/ops status` 唯讀、ephemeral，非 owner fail closed。
- [x] 2026-08-24 17:12 後取得 owner-only 安全摘要：三服務健康、schema v6、三類 queue 與 manual attention 均為 0。
- [x] Remote runtime、single-writer 與受限部署入口完成唯讀核對；observation 判定 PASS。

本文件不記錄 Discord／Google ID、credential、案件正文、姓名、學號、Email 或其他私人資料。

## 完成項目與後續證據

- [x] 單一 writer invariant 持續成立；Mac writer 沒有復活。
- [x] 三個 remote services 持續 active／enabled；owner-only 狀態摘要均為 `HEALTHY`。
- [x] Projection queue、私人匯出 queue 與 manual attention 均歸零，沒有 critical failure。
- [x] Production schema 保持 v6，沒有在 observation 中換版。
- [ ] OAuth refresh、GAS／Compact Sheet 與 daily backup 沒有在 17:12 最終 checkpoint 另外執行寫入式
  smoke；既有收據未出現異常，但這些項目必須在 candidate v10 的 release gate 以安全方式再確認。
- [ ] Production v6 consistent backup 副本的 v6 → v10 rehearsal、backup readability、integrity、ledger、
  row counts 與 rollback readiness 屬於下一個 release gate，不由本次 v6 PASS 代替。

## 停止線

若出現 duplicate writer、Bot 登入失敗、重複 Discord 副作用、DB corruption、critical queue failure、
production secret 缺漏或 OAuth 無法恢復，立即停止 remote services，保留 rollback DB；不得同時重啟
Mac writer。

## PASS 後

Phase 2C v6 baseline 已完成。Bound GAS status digest、Portal、CNAME 與其他新功能不屬於本觀察
窗口；candidate v10 也沒有因本次 PASS 自動取得部署授權。

這個 24 小時窗只是現行 Production v6 baseline 的最後收據，不是以後每次換版的固定冷卻期。Candidate v10 若獲授權部署，以 production consistent backup rehearsal、部署後 smoke、白帳號 E2E 與 rollback readiness 作主 gate；需額外觀察時，以最長約 8 小時的過夜窗口為原則。v6 窗口不為 v10 功能背書，但也不因此強制 v10 重等 24 小時。
