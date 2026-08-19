# GAS 狀態摘要

Bound GAS 是獨立 watchdog：每 5 分鐘檢查一次，但只處理 Asia/Taipei 的 `07:00`、`13:30`、`19:00` slot。即使 24h host 離線，它仍可依 Sheet 最後 receipt 判斷 stale。

## 分級

- NORMAL：最後 heartbeat 不超過 15 分鐘，無 terminal failure。
- ATTENTION：超過 15 分鐘或持續 retryable failure。
- CRITICAL：超過 30 分鐘、permanent failure、OAuth revoked 或 service DOWN。

信件只有整體狀態、需處理事項、Bot／同步／案件概況與資料時間，不含 PID、資源數字、stack trace、學生資料或 Discord ID。

## 啟用

1. 在 bound Apps Script 的 Script Properties 設 `STATUS_EMAIL_RECIPIENTS`；第一版只放 project owner。
2. 回到 Server Database，重整頁面。
3. 選「微積分模組管理 → 安裝狀態摘要排程…」。
4. 確認只存在一個 `boundStatusDigestDispatcher` 的每 5 分鐘 trigger。

每個 slot 先寫 `ATTEMPTING` 再寄信；不論成功或發生 ambiguous failure，同一 slot 都不自動重寄，避免 spam。
