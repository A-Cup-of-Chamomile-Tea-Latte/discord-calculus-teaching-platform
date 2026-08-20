# Implementation status

Last repository／runtime verification: 2026-08-20 (Asia/Taipei)

Canonical root: `/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`

Branch: `codex/phase-2c-24h-production-integration`

Verified code baseline: `78fb4a8`

## Canonical snapshot

| 領域 | 現況 |
| --- | --- |
| Production writer | Mac 仍是唯一 writer；`course_assistant` 與 `dump_bot` 各一個 process、均 running |
| Live cutover | 未開始；未收到精確 `GO-LIVE-CUTOVER` |
| Local authority | SQLite；Google Sheets 只是精簡投影與暫時分享／恢復面 |
| Tracked schema | migration v5；案件異動與 outbox 同一 transaction |
| Live Mac DB | legacy schema v0；未原地修改。唯讀開啟後，consistent backup／restore／copy migration v0 → v5 演練 PASS |
| Compact Sheet | schema `2.0.0`；5 個人用頁＋5 個隱藏機器頁 |
| Standalone GAS | immutable v12；owner-only Execution API；無 public Web App |
| Bound GAS | immutable v6；source 對齊；status-digest trigger 未啟用 |
| Remote host | 尚未取得 SSH username、Tailscale target 與人工核對的 host-key fingerprint |

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
- Current transport 可刷新並已通過 `scripts.run`，但 Google Auth Platform 仍是 External／Testing。
- 因包含 Sheets scope，testing refresh token 通常約 7 天失效。24h production 前必須人工選擇：
  切到 Production 並按 Google 要求處理驗證，或接受約每 7 天重新授權。
- OAuth publishing status 不會改變 standalone GAS 的 owner-only access。

## Verification

- Python：246 passed；2 則 upstream `discord.py`／Python 3.14 deprecation warnings。
- Portal／Config Studio／GAS：53／3／66 tests passed。
- GAS strict typecheck、standalone／bound build、pull-back fingerprint：PASS。
- Live SQLite read-only recovery rehearsal：backup、restore、integrity、migration ledger、row-count equivalence、
  restored-copy independence 全 PASS；原始檔未修改。
- Mac bot single-instance：PASS。
- `.local/` 維持 Git-ignored；沒有 credential、live data 或學生資料加入 repository。

## 剩餘只分兩類

### A. 需要使用者／朋友人工處理外部 gate

1. Google Auth Platform：Production，或接受 Testing 約每 7 天人工重授權。
2. Remote identity：SSH username、Tailscale hostname／private IP、人工核對 host-key fingerprint。
3. Remote staging receipts 全 PASS 後，由使用者輸入精確 `GO-LIVE-CUTOVER`。
4. Remote heartbeat 穩定後，視需要在 Chrome「Ding Ding」授權 bound status-digest trigger。

### B. 必須等待真實時間

- Live cutover 後才開始 24 小時 observation；不能用本機測試或縮短計時替代。

詳細報告：`project-exchange/18_PHASE_2C_24H_HOST_PRODUCTION_INTEGRATION_REPORT_2026-08-19.md`。
