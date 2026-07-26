# Batch C GAS summary

## Outcome

Complete。Tasks 15–19均已完成，沒有 skipped/blocked task；Apps Script/Sheets/email全程只使用local fixtures與mock providers，未建立或部署cloud project、未寫真實Sheet、未寄email。

## Completed tasks

- Task 15：clasp-compatible local scaffold、manifest、build與mock entrypoint。
- Task 16：versioned Sheets schema/bootstrap、header drift檢查、lock/retry interfaces。
- Task 17：public general-case lookup API、validation、anti-enumeration projection與Portal adapter parity。
- Task 18：single-use activation nonce、hash-only storage、expiry/redeem/revoke、lock與audit。
- Task 19：institutional/contact email分流、salted hash-only six-digit code、expiry/attempt/resend limits、mock delivery與audit。

## Skipped or blocked

- 無 skipped/blocked task。
- Cloud owner/account type、deployment ID、Properties secrets、production Sheets repository、MailApp delivery、web-app auth與quota monitoring保持未配置；未取得外部授權前不得執行。

## Verification

- Batch C完成時：GAS Vitest 6 files / 44 tests、Portal 5 files / 25 tests、Pytest 36 tests；secret scan 269 files / 0 findings；Astro 41 files零診斷，GAS build成功。
- Task 25後最新回歸：GAS仍44/44、Portal仍25/25，完整Pytest增至86/86；GAS tsc與bundle build仍成功。

## Key diagnostics

- Sheets/Apps Script不適合高頻逐訊息mirror；原始Discord內容應先由Task 26本機pipeline匯出，再batch import。
- Activation/email verification需要production durable repository、transaction/outbox、HMAC pepper、rate limits、anti-enumeration與retention。
- NTU Mail控制權不等於course enrollment；正式membership authority尚未決定。
- Apps Script/Mail quotas會變，部署日必須用官方文件與getRemainingDailyQuota重新核對；預定owner/deployer是ntusupercool@gmail.com，但account type未驗證。

## Product and architecture questions

- 正式Sheets layout與protected ranges由誰核准、如何migration/backup？
- Public GAS endpoint使用何種authentication與anti-abuse edge？
- Enrollment authority是NTU COOL roster import、人工核准或其他來源？
- Email provider使用consumer MailApp、Workspace或獨立transactional provider？

## Recommended next batch

Batch D已完成；依目前pause點，新環境下一步為Batch E Tasks 26–28。

## Copy-paste handoff

Batch C Tasks 15–19已全部完成：local clasp/GAS scaffold、Sheets schema/bootstrap、public case API、activation nonce及provider-neutral email verification。完成時GAS 44/44、Portal 25/25、Pytest 36/36、secret scan 269/0；Task 25後最新回歸仍為GAS 44/44、Portal 25/25、完整Pytest 86/86，GAS tsc/build成功。全程未建立Apps Script cloud、未寫真實Sheet、未寄email。主要缺口是production auth/storage/outbox/HMAC pepper/rate limits/retention與正式Mail/enrollment authority。新環境從Batch E Task 26繼續。
