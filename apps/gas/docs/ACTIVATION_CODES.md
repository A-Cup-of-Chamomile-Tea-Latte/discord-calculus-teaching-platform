# 啟動碼設計與安全邊界

本模組把一次性人工作業憑證稱為「啟動碼」，不是密碼。啟動碼只用於取得一個明確、可稽核的課程權限設定檔；它不取代 Google、Discord 或任何正式身分提供者的登入機制。

## 格式與熵

- 顯示格式為 `CALC-XXXX-XXXX-XXXX-XXXX`，輸入時可忽略大小寫、空白與連字號。
- 16 個隨機字元取自 32 字元的不易混淆 alphabet，因此提供 80 bits 的搜尋空間。
- 正式發行只接受 `crypto.getRandomValues` 這類 cryptographically secure random source。若 runtime 沒有強隨機來源，發行會以 `CRYPTOGRAPHIC_RANDOM_SOURCE_UNAVAILABLE` 失敗；不以 UUID、時間戳或 `Math.random()` 降級。
- `SequenceRandomSource` 只供 deterministic local tests 使用，禁止接入正式發行路徑。

在啟用雲端發行前，部署者仍須在目標 Apps Script V8 runtime 驗證 Web Crypto 可用。這個 repository 沒有建立或部署雲端專案，也沒有產生可供真人使用的啟動碼。

## 儲存與一次顯示

發行服務只在建立結果中回傳一次明文，repository、Sheets fixture、稽核事件及 log 都只接觸以下衍生資料：

- `verifierHash`：正規化啟動碼的 SHA-256 fingerprint。
- `bindingValueHash`：選用 email 或 Discord user ID 綁定時，經種類分隔與正規化後的 SHA-256 fingerprint。
- `redemptionRequestHash`：idempotency key 經用途分隔後的 SHA-256 fingerprint。

SHA-256 fingerprint 不等於密碼雜湊器；這裡的安全性主要來自 80-bit 隨機啟動碼、短效期、單次使用與存取限制。不得把低熵資料或一般密碼直接套用這個設計。

## 權限與生命週期

每筆新發行資料都帶有明確的 `role`、`courseId`、可選 `classCode` 與非空 permission allowlist。既有 schema v1 資料可以缺少 Task 18 新增的可選欄位，但 production authorization 不得替缺漏的 legacy record 猜測或自動擴權；應拒絕並由管理者重新發行。

狀態流如下：

1. 建立為 `UNUSED`，寫入建立與到期時間並記錄 `ACTIVATION_CODE_CREATED`。
2. 首次成功兌換在 lock 內更新為 `USED`，寫入兌換者、時間及 request hash，再記錄結果。
3. 同一 idempotency key 重送回傳 `REPLAY`，不再次授權；不同 key 對已使用資料回傳 `USED`。
4. 過期資料會標記 `EXPIRED`；管理者可在未使用前標記 `REVOKED`。
5. 不存在、格式錯誤、綁定不符、過期、撤銷與重送都會留下不含明文或綁定值的稽核結果。

## 併發與 Google Sheets 限制

`GasScriptLock` 使用 Apps Script `LockService.getScriptLock()`。它是整個 script 的全域互斥鎖，不是 per-code row lock；這會犧牲吞吐量，但可避免同一 deployment 內兩個兌換同時把相同啟動碼當作未使用。若取得鎖逾時，操作會失敗而不兌換。

Google Sheets 不提供跨工作表交易。將來若兌換流程同時更新 `ActivationCodes` 與 `CourseMemberships`，在其中一次寫入成功、另一次失敗時仍可能不一致。正式整合必須採用可重試的單一 commit boundary、狀態機或補償作業，並以 request hash 對帳；目前程式只提供 domain service、記憶體 repository 與 schema，**不宣稱是 production-grade transactional store**。

## 本機驗證

`src/activation/service.test.ts` 使用 deterministic bytes 驗證固定輸出、一次性、replay、過期、撤銷、email/Discord 綁定、稽核去敏與儲存不含明文。所有測試都在 fixture mode 執行，不需 Google credential 或網路。
