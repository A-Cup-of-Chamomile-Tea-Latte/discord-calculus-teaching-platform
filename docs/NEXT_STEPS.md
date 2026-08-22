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

計時起點：2026-08-22 18:33（Asia/Taipei）。最早完成：2026-08-23 18:33。

期間驗證單一 writer、三個 remote services、Discord connectivity、queue depth、OAuth refresh、GAS
heartbeat、backup 與 compact Sheet projection。滿 24 小時後原地更新 Phase 2C report，再決定是否
進入小規模試用。第一天不新增 production feature；bound digest 延後至 heartbeat 穩定後再處理。

## 固定停止線

- SQLite 是 authority；任何 cloud fetch 都必須驗 version、checksum、source 與 operator confirmation。
- 不把 raw messages、姓名、學號、Discord ID、Email、附件、Private Support、credential 放進
  chat、Git、公開 ZIP 或 LLM。
- 不建立 public SSH、public GAS endpoint、第二個 production writer，或未經核准的 email／分析流程。
