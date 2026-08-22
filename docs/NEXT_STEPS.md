# Ordered next steps

## 已壓縮完成

本機 implementation、compact Sheet、雙向 Google Bridge smoke、安全 synthetic cleanup、SQLite
live-copy backup／restore／migration rehearsal 均已完成。不要重跑 44-action Sheet migration、另建 OAuth
client、另寫一份 Phase 2C 報告，或把 corpus／LLM 分析拉進本階段。

Live cutover 與最小 Public Discord smoke 已完成。Remote Linux 是唯一 production writer；Mac
LaunchAgents 已停用。status digest 尚未啟用。

## 1. 已完成的人工 gate

Google OAuth Production、SSH host identity、remote staging、runtime secrets receipt、精確
`GO-LIVE-CUTOVER`、remote systemd activation 與 Public Discord smoke 均已完成。朋友目前不需要再
執行 sudo。

## 2. 必須等待 24 小時

第一輪曾於 2026-08-22 18:33（Asia/Taipei）開始，但 close → immediate reopen 暴露 SQLite
transition 已提交而 Discord thread side effect 尚未完成的可見不一致，因此本輪標記為 `DEGRADED`，
不得在原定時間宣告 PASS。

先在隔離側線完成 close／reopen 可恢復狀態機、學生文案與 owner-only safe status command。經主線審查、
另行部署授權、修復版 deploy 與 Public smoke PASS 後，才記錄新的 24 小時計時起點。

新的 observation 期間驗證單一 writer、三個 remote services、Discord connectivity、queue depth、OAuth
refresh、GAS heartbeat、backup 與 compact Sheet projection。滿 24 小時後原地更新 Phase 2C report，再
決定是否進入小規模試用。Bound digest 延後至 heartbeat 穩定後再處理。

## 固定停止線

- SQLite 是 authority；任何 cloud fetch 都必須驗 version、checksum、source 與 operator confirmation。
- 不把 raw messages、姓名、學號、Discord ID、Email、附件、Private Support、credential 放進
  chat、Git、公開 ZIP 或 LLM。
- 不建立 public SSH、public GAS endpoint、第二個 production writer，或未經核准的 email／分析流程。
