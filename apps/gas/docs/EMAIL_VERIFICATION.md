# 電子郵件驗證與 delivery boundary

Task 19 的 provider-neutral domain service 與純記憶體 mock 仍保留。v13 deployment candidate 另加入尚未部署的 production delivery boundary：SQLite durable outbox 是唯一 delivery authority，owner-only 獨立 GAS 只負責呼叫 `MailApp`；Sheet-bound GAS 不寄驗證信，也沒有 public Web App route。Email 僅用於加入申請驗證；Public／Private 案件通知維持 Discord DM-only。

## 身分語意

- `INSTITUTIONAL`：驗證使用者能接收指定機構網域信箱。正式 domain allowlist 尚未核准；測試只使用保留的 `.example` 網域。
- `CONTACT`：可選偏好聯絡信箱，必須以自己的 challenge 另行驗證。驗證機構信箱不會自動把聯絡信箱標成已驗證。
- 控制 NTU Mail 地址只證明當下能接收該信箱，**不等於證明已選修本課程、班別、在學狀態或 Discord 身分**。課程 membership 仍需由 NTU COOL roster、人工核准或另行核准的啟動碼流程決定。

## Code 與生命週期

- 每次寄送產生均勻的六位數 code。`RandomBytesSource` 必須由 cryptographically secure provider 實作；三 bytes 經 rejection sampling 避免 modulo bias。
- 儲存資料只有 16-byte random salt 與 `SHA-256(email-verification:v1:salt:code)`，沒有明文 code。由於六位碼只有約 20 bits，salted hash 仍不能抵抗取得資料庫後的離線枚舉；短效期、attempt limit、存取控制與未來 server-held HMAC pepper 都是必要防線。
- 保守預設：10 分鐘到期、5 次嘗試、60 秒重寄冷卻、每 challenge 最多 3 次寄送；policy 允許在安全範圍內注入。
- 重寄會產生新 code、salt/hash、到期時間並重設 attempts，舊 code 立即失效。
- 用完 attempts 後 challenge 鎖定至原到期時間；重新開始不會立即繞過 lock。到期後才可建立新 challenge。
- 成功後 challenge 變成 `VERIFIED`，建立符合 `verified-email.schema.json` 的 record 並寫入 `verifiedAt`；同 code 不可再用。
- 稽核只記 event type、challenge ID、outcome、時間，不含 email 或 code。

## Provider 與儲存邊界

`MemoryVerificationEmailProvider` 仍只供 fixture test。production path 由 SQLite migration v11 的 `email_delivery_outbox` 保存待寄 delivery，Linux bridge 以 claim token／lease 取件，再呼叫獨立 GAS 的 `bridgeSendVerificationEmail`。GAS 以 Script Properties 記錄 delivery receipt：已接受的 delivery 重送為 no-op；若 `MailApp.sendEmail` 回傳結果不明，標成 `EMAIL_DELIVERY_AMBIGUOUS` 並停止自動重送，交由人工處理。

待寄期間 SQLite 必須暫存收件地址與六位碼；完成、到期或永久失敗時立即清空兩欄，只保留 destination SHA-256、safe error code 與 metadata。這不是靜態加密替代品：production DB／backup 必須維持 owner-only 權限，outbox 不得投影到 Sheet、log、Portal 或一般管理畫面。

Production 尚缺：

1. 經核准的 institution domain policy。
2. 使用 `crypto.getRandomValues` 的 runtime composition，以及 deployment-held HMAC pepper 或受保護 verification service。
3. 可原子更新 challenge attempts/status 的 repository；正式 verified records 可寫入既有 `Emails` sheet，但 ephemeral challenges 不應混入已驗證 records。
4. 將 challenge 建立與 v11 outbox enqueue 接成同一 SQLite transaction；目前 delivery infrastructure 已完成，但 Portal join 尚未啟用 email verification。
5. Authenticated route、per-user/per-email/per-IP abuse limits、CAPTCHA/edge protection、operator controls 與 retention cleanup。
6. Plain-text-only verification template、reply/support policy、bounce handling、監控與告警。不得加入追蹤像素或把 code 寫入 log。

## Gmail / Apps Script quota implications

預定 deployer `ntusupercool@gmail.com` 看起來是 consumer Gmail 身分，但部署前仍需由擁有者確認實際 account 類型。依 [Google Apps Script Quotas](https://developers.google.com/apps-script/guides/services/quotas)（本文件於 2026-07-19 核對），`MailApp` 每日收件者配額是 consumer account 100 recipients/day、Google Workspace 1,500 recipients/day；配額以 user 計、從第一次請求起 24 小時後重設，而且 Google 明示數值可隨時更動。每次初次 code 與 resend 都會消耗 recipient quota，不能把 100 當作可服務 100 名學生。

正式 adapter 每次寄送前讀 [`MailApp.getRemainingDailyQuota()`](<https://developers.google.com/apps-script/reference/mail/mail-app#getRemainingDailyQuota()>)，預設保留 10 recipients 的操作安全餘額；可用 `EMAIL_QUOTA_RESERVE` Script Property 提高但不得設為 0。quota 不足時 fail closed，由 SQLite outbox 延後重試。部署當日仍必須重新核對官方 quota，不把文件數字硬編碼成產品保證。

## 本機驗證

`src/email-verification/service.test.ts` 覆蓋 domain flow；`mail-app-provider.test.ts` 覆蓋純文字寄送、quota reserve、accepted no-op、ambiguous fail-closed、輸入與 expiry。Python tests 覆蓋 SQLite enqueue／claim／retry／到期／terminal scrub 及 Linux→GAS receipt。所有地址皆為 `.example` fixture；測試不寄真實郵件。
