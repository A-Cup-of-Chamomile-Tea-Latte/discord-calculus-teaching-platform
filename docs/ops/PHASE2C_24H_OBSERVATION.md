# Phase 2C 真實 24 小時 observation

## Observation window

- 開始：2026-08-22 18:33（Asia/Taipei）
- 最早完成：2026-08-23 18:33（Asia/Taipei）
- Production authority：remote SQLite
- Production writer：remote Linux only

## Start receipt

- Mac LaunchAgents absent；本機 runtime process 為 0。
- Remote `course-assistant`、`dump-bot`、`data-bridge` 均 active／enabled。
- 三個服務各有不同 MainPID，啟動後 restart count 為 0。
- Cutover repair、fresh service health、data-bridge backlog drain 均 PASS。
- Allowlisted Discord Public smoke PASS：Bot 接到新 Forum thread、完成互動設定並更新標題。
- Smoke 後三個服務仍 running，沒有 warning。

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
