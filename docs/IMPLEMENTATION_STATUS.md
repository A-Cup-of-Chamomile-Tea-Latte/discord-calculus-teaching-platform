# Implementation status

Last repository／runtime verification: 2026-08-22 (Asia/Taipei)

Canonical root: `/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`

Branch: `codex/phase-2c-24h-production-integration`

Verified code baseline: `78fb4a8`

## Canonical snapshot

| 領域 | 現況 |
| --- | --- |
| Production writer | Remote Linux 是唯一 writer；Mac LaunchAgents 已停用且本機 runtime process 為 0 |
| Live cutover | PASS；三個 remote systemd services 均 active／enabled，Public Discord smoke PASS |
| Local authority | SQLite；Google Sheets 只是精簡投影與暫時分享／恢復面 |
| Tracked schema | migration v5；案件異動與 outbox 同一 transaction |
| Production DB | Remote SQLite schema v5；cutover 前 consistent rollback backup、傳輸 checksum、integrity 與 migration ledger 均 PASS |
| Compact Sheet | schema `2.0.0`；5 個人用頁＋5 個隱藏機器頁 |
| Standalone GAS | immutable v12；owner-only Execution API；無 public Web App |
| Bound GAS | immutable v6；source 對齊；status-digest trigger 未啟用 |
| Remote host | SSH host identity 與 host key 已人工核對；release、DB、secrets 與 systemd production install 完成 |
| 24h observation | DEGRADED；Public create／finalize／close PASS，但 immediate reopen 暴露 DB／Discord side-effect 不一致。修復版重新部署並 smoke PASS 後重算 |

## Data Bridge 收據

- Local → Cloud projection：preview → apply → outbox complete → duplicate no-work，PASS。
- Cloud → Local → Cloud command：queue → claim → apply → ack → duplicate no-work，PASS。
- Synthetic cleanup：嚴格 allowlist、nonce、blank／duplicate key／formula fail-closed、unknown preserve、partial retry，PASS。
- 雲端最後狀態：可移除 human-view synthetic rows 為 0、unknown rows 為 0；保留一筆 terminal
  command machine receipt 作短期稽核與版本 watermark。
- `_CommandInbox`、`_EmailOutbox`、`_Artifacts` 不由 cleanup 刪除；`_SyncState` watermark 保留，避免舊 envelope 重播。
- cleanup 的 read-compare-delete 不是跨人工 Sheet 編輯的原子 transaction；執行窗口不得同時人工修改 Sheet。

## Google OAuth

- Desktop OAuth 只申請 Sheets scope；credential 只在 Git-ignored、權限 `0600` 的本機位置。
- Google Auth Platform 已切到 External／Production；owner credential 已通過 refresh 與
  `scripts.run`，只申請 Sheets scope。
- OAuth publishing status 不會改變 standalone GAS 的 owner-only access。

## Verification

- Python：246 passed；2 則 upstream `discord.py`／Python 3.14 deprecation warnings。
- Portal／Config Studio／GAS：53／3／66 tests passed。
- GAS strict typecheck、standalone／bound build、pull-back fingerprint：PASS。
- Live SQLite read-only recovery rehearsal：backup、restore、integrity、migration ledger、row-count equivalence、
  restored-copy independence 全 PASS；原始檔未修改。
- Mac bot single-instance：PASS。
- `.local/` 維持 Git-ignored；沒有 credential、live data 或學生資料加入 repository。

## 目前停止點

- 第一輪真實 observation 已發現 close → immediate reopen 缺陷，不能作為 Phase 2C PASS。
- 目前停止重複操作測試 thread；不把 rate-limit 延遲誤稱為使用者限制。
- 由獨立側線完成狀態機、文案與 owner-only safe status command；主線審查後才決定修復版 deploy。
- 修復版 Public smoke PASS 後，重新開始完整 24 小時 observation；不能沿用 2026-08-22 18:33 起點。
- 觀察單一 writer、三個 remote services、Discord connectivity、queue、OAuth refresh、GAS
  heartbeat、backup 與 compact Sheet projection。
- 滿 24 小時且各項 PASS 後，更新 Phase 2C report，再決定是否進入小規模試用。

詳細報告：`project-exchange/18_PHASE_2C_24H_HOST_PRODUCTION_INTEGRATION_REPORT_2026-08-19.md`。
