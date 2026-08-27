# Discord 公開／隱密支援入口

狀態：`V13_DEPLOYED / LIVE_WHITE_ACCOUNT_E2E_PENDING`

更新日期：2026-08-28

## 統一流程

公開與隱密案件共用題目、圖片、問題型、關鍵字、逐案 AI 同意、案號、close／reopen 與通知語意；唯一差異是 Discord 可見度。

- 公開：學生在受管理 Forum 直接發文。
- 隱密：學生用 Discord 指令要求 Course Manager 建立受限空間。
- Portal：只說明流程與查狀態，不收題目、不上傳附件、不另存 Discord 圖片。

production v13 已註冊 `/private open`，以受限文字頻道承載 Private Support，並使用 `private dump` 後刪除頻道的生命週期。程式與部署檢查已通過；正式對學生宣稱完成前，仍須做一次白帳號可見性、DM、close／reopen 與非參與學生不可見的 live E2E。

## 冪等與防濫用

- 同一 Discord interaction 重送時回傳原結果，不建立第二個空間或案件。
- 不用問題文字 hash 判定不同問題是否相同。
- 私密入口初始容量：每位使用者 2 分鐘 1 次、每小時 5 次、24 小時 20 次。
- 超過即時處理容量時，保留在 queue 並告知「已收到，等待建立」，不丟資料。
- 開學前兩週若需要容量估計，可由 owner 手動啟用 Gamma–Poisson 更新；不是常駐背景分析，也不讀問題內容或建立學生評分。
