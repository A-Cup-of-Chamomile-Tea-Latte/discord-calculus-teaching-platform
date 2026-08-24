# Phase 2C 真實 24 小時 observation

## Current observation window

- 開始：2026-08-23 17:12（Asia/Taipei）
- 最早完成：2026-08-24 17:12（Asia/Taipei）
- 狀態：`AWAITING FINAL REMOTE CHECKPOINT`；本 repository 整合輪沒有重新連線探測，不能寫成 PASS
- Production authority：remote SQLite
- Production writer：remote Linux only
- Production schema：v6；repository candidate v10 尚未部署

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
- 此 finding 屬於 2026-08-22 的已作廢窗口；修復與新 smoke 已完成，但仍需等目前窗口的最終遠端 checkpoint。

## Final checkpoint gate

- [x] v5 live consistent copy 升級到 v6、integrity 與 migration ledger PASS。
- [x] 三個 remote services 使用同一個 v6 release，fresh health PASS，Mac writer 為 0。
- [x] Public close／immediate reopen smoke 收斂；沿用案號，沒有重複 lifecycle side effect。
- [x] owner-only `/ops status` 唯讀、ephemeral，非 owner fail closed。
- [ ] 2026-08-24 17:12 後重新取得安全摘要，確認三服務、schema、queue、manual attention、projection、OAuth 與 backup。
- [ ] 只有上述最終 checkpoint PASS，才可更新為 observation PASS。

本文件不記錄 Discord／Google ID、credential、案件正文、姓名、學號、Email 或其他私人資料。

## 必查項目

- [ ] 單一 writer invariant 持續成立；Mac writer 不得復活。
- [ ] 三個 remote services 持續 active，沒有 restart loop。
- [ ] Discord gateway 與 Public workflow 持續可用。
- [ ] Projection queue 無持續 backlog 或 critical failure。
- [ ] OAuth refresh 與 GAS health 正常。
- [ ] Compact Sheet production projection 有前進且沒有重複副作用。
- [ ] Production SQLite integrity、schema 與 migration ledger 正常。
- [ ] Daily backup 成功，並採有界 retention；不長期堆積於朋友主機。

## 停止線

若出現 duplicate writer、Bot 登入失敗、重複 Discord 副作用、DB corruption、critical queue failure、
production secret 缺漏或 OAuth 無法恢復，立即停止 remote services，保留 rollback DB；不得同時重啟
Mac writer。

## 24 小時後

只有實際滿 24 小時且上述項目均 PASS，才可更新 Phase 2C report 並討論小規模試用。Bound GAS
status digest、Portal、CNAME 與其他新功能不屬於本觀察窗口。
