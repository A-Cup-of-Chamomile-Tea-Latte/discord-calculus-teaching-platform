# TASK-19 report — provider-neutral email verification skeleton

## Outcome

Complete。機構信箱／偏好聯絡信箱分流、六位一次性 code、salted hash-only storage、expiry、attempt lock、resend cooldown/send limit、成功時間、稽核與 mock email provider 已完成並通過 fixture end-to-end tests；沒有寄送真實郵件、連接 Gmail、建立 Apps Script cloud resource 或使用真實學生地址。

## Summary

- 建立 provider-neutral `EmailVerificationService` 與 repository/email/random/hash/clock/lock/audit/institution-domain ports。
- 六位 code 由三個強隨機 bytes 以 rejection sampling 均勻產生，避免 modulo bias；只保存 16-byte random salt 與用途分隔的 SHA-256 hash。
- 預設 10 分鐘 expiry、5 次嘗試、60 秒 resend cooldown、每 challenge 最多 3 次寄送；全部有安全範圍 runtime policy validation。
- Wrong code 逐次扣 attempts；歸零後鎖到原到期時間。重新 start 不可立即繞過 attempt lock；到期後才可建立新 challenge。
- Resend 產生全新 code/salt/hash、重設 attempts 與 expiry，舊 code 立即失效；send limit 與 cooldown 都會 audit。
- 成功後 challenge 標記 `VERIFIED`、寫 `verifiedAt` 並建立符合既有 `verified-email.schema.json` 的 record；再次輸入同 code 回 `ALREADY_VERIFIED`，不重複建立 record。
- `INSTITUTIONAL` 必須通過 injected domain policy；可選 `CONTACT` 需要自己的獨立 challenge。驗證 NTU Mail 控制權不等於課程 enrollment proof。
- Mock provider 只把 delivery 放在記憶體陣列供 test 讀取，沒有 network；audit events 不含 email 或 code。
- Root fixtures 新增 Amber 的 institutional record，保留另一筆 primary contact record，且所有地址仍為 `example.com`。
- 文件核對 Google 官方 current quota：consumer Apps Script MailApp 100 recipients/day、Workspace 1,500 recipients/day；數值會變，部署日須再查並用 `getRemainingDailyQuota()`。

## Files changed

- `apps/gas/src/email-verification/contracts.ts`：challenge/verified-email types、ports、commands 與 outcomes。
- `apps/gas/src/email-verification/service.ts`：code issuance、start/resend/verify、hash、expiry、attempt/send limits、lock 與 audit。
- `apps/gas/src/email-verification/in-memory.ts`：fixture repository、mock delivery provider、audit sink、lock 與 domain allowlist policy。
- `apps/gas/src/email-verification/service.test.ts`：8 個 email verification tests，納入 GAS 44-test suite。
- `apps/gas/docs/EMAIL_VERIFICATION.md`：identity boundary、安全模型、quota、production gaps 與 cloud checklist。
- `apps/gas/README.md`：Task 19 模組與「不寄信」入口說明。
- `fixtures/users/users.json`、`verified-emails.json`：Amber 兩筆獨立 institutional/contact records 與關聯。
- `fixtures/adapters/mock-adapters.json`：email delivery mock signature、kind 與 no-tracking flag。
- `fixtures/DATA_DICTIONARY.md`、`fixtures/users/README.md`：record count 與驗證語意。
- `tests/contract/test_fixture_scenarios.py`：38-record count、institutional/contact 分離與 email ID ownership links。
- `docs/reports/TASK-19-REPORT.md`：本報告。

## Commands executed

- 只讀查閱 Google 官方 Apps Script quota 與 MailApp reference。
- `npx prettier --write <Task 19 TypeScript/JSON/Markdown files>`。
- `python -m ruff format tests/contract/test_fixture_scenarios.py`。
- `npm run typecheck --workspace @calculus/gas`。
- `npm run test --workspace @calculus/gas`。
- `env PATH=/tmp/codex-calculus-task12-venv/bin:… npm run check`。
- `npm run build --workspace @calculus/gas`。
- `rg`、`wc`、`git diff --check` 作只讀 code/email/provider/bundle/whitespace inspection。

沒有 `MailApp.sendEmail`、Gmail API、network delivery、tracking HTML、sender hardcode、real NTU address、credential、cloud project、Sheet write、publish 或 deploy。

## Verification

- Tests：GAS Vitest 6 files / 44 tests、Portal Vitest 5 files / 25 tests、Pytest 36 tests全部 passed；Task 19 有 8 個 domain tests，Python fixture scenarios 增為 11 個。
- Linters/type checks：完整 root check 通過；secret scan 269 candidate files / 0 findings；Prettier、Ruff lint/format、GAS strict tsc、Astro check 41 files / 0 errors / 0 warnings / 0 hints、mypy 9 source files全部成功。
- Builds：GAS build 成功；Task 19 domain 尚未掛入 entrypoint，因此 dist 仍只包含既有 public scaffold/routes。
- Manual checks：mock challenge snapshot 不含 delivery code；audit 不含 email/code；root fixture addresses 仍只出現 `example.com`，contract record count 38，全數符合 schemas。

## Diagnostics

- 六位 code 只有約 20-bit entropy。Salted SHA-256 符合 hash-only requirement，但資料庫外洩後仍可被離線枚舉；production 應加入 server-held HMAC pepper、極短 retention 與嚴格 repository access。
- Pure service 先保存 challenge 再呼叫 provider。真實 provider 若失敗，會留下未送達的 pending challenge；production 需 transactional outbox、delivery state、idempotency 與 reconciliation。
- Challenge update 與 VerifiedEmail insert 目前不是跨 storage transaction；production repository 必須設計單一 commit boundary 或補償機制。
- Attempt/send limits 是 per challenge；缺少跨 challenge、per account、per destination、per origin/IP 與全域 quota abuse control。公開 route 前必須補在 authenticated same-origin edge/backend。
- 不同 start outcomes 可能造成 email/account enumeration；公開 API 應回 generic message，只將詳細 outcome 留給受授權 audit/operator。
- 預定 deployer `ntusupercool@gmail.com` 的實際 account 類型未驗證；consumer Gmail 的 current Apps Script recipient quota較低，不能假設 Workspace 配額。
- Google 官方說 quota 以 user 計、首次請求後 24 小時重設、超額會使 execution 丟例外，且數值可隨時更動。來源：[Apps Script quotas](https://developers.google.com/apps-script/guides/services/quotas)、[MailApp reference](<https://developers.google.com/apps-script/reference/mail/mail-app#getRemainingDailyQuota()>)（2026-07-19 核對）。

## Assumptions made

- Fixture institution policy 使用 `institution.example`，root completed-record fixture仍使用 `example.com`；兩者都不是正式 NTU domain policy。
- Institutional 與 contact 必須分開驗證；只有一筆可由 product/account service選為 primary，本 domain 不跨使用者自動調整其他 records。
- Default 10-minute/5-attempt/60-second/3-send policy 是可逆 prototype設定，不是校方核准政策。
- 成功驗證只證明對該信箱的當下控制權，不建立 CourseMembership，不授予 Discord role，也不宣稱選課。
- Mock provider 可在 test process 記憶體中看到 code；persistent repository、audit、fixtures、logs 與 build output不得保存 code。

## Risks and blockers

- 高度：沒有 authenticated route、production repository、MailApp adapter、outbox、HMAC pepper、跨 challenge abuse control 或 generic anti-enumeration response；不得公開服務。
- 高度：尚未確認 institutional domain 規則與 enrollment authority。即使是有效 NTU Mail，也不得自動視為修課成員。
- 高度：Mail delivery quota/exception可能使 Sheet 狀態與實際送達分裂。必須先完成 outbox/reconciliation 才可 cloud pilot。
- 中度：`ntusupercool@gmail.com` 可能只有 consumer 100 recipients/day Apps Script quota；resend 也消耗 recipient，容量需以尖峰情境估算。
- 中度：完成 records 含 email PII；retention、刪除、存取與 audit policy待 Task 29。
- 無阻擋 Task 20 本機 architecture工作。

## Questions for ChatGPT discussion

- 哪些 NTU Mail domains/aliases 可接受，是否需要處理校友、停用或轉寄地址？
- 誰是 course enrollment authority：NTU COOL roster import、人工核准，或其他 registrar資料？
- 正式 email provider 使用 consumer MailApp、Workspace account 或獨立 transactional provider？預估每日初次驗證與 resend尖峰是多少？
- HMAC pepper 應置於 Apps Script Properties、Google Cloud Secret Manager，或把 verification搬到受保護 server？
- Challenge/outbox/verified record 要用何種 transactional store與 retention policy？

## Recommended next action

執行 Task 20：先定義 multiple Discord bot applications 的責任、事件所有權、permissions/intents、failure isolation與共同 contracts，保持所有 bots為local fixture architecture，不連真實 server。

## Exact cloud steps still required

1. 由擁有者確認 `ntusupercool@gmail.com` 是 consumer 或 Workspace account，並在部署當日重新核對 Apps Script/Gmail quotas與校方寄信政策。
2. 核准 institutional domain allowlist、email verification文字、support/reply/bounce政策、retention與 enrollment-proof boundary。
3. 建立/選定受保護 challenge + outbox store；以原子 compare-and-set更新 attempts/status，並將完成 records寫入既有 Emails schema。
4. 在受保護 runtime設定 HMAC pepper與必要 IDs；不得放進 source、Sheet、`.clasp.json`或 logs。
5. 驗證目標 runtime的 Web Crypto，建立 MailApp provider；寄送前呼叫 `getRemainingDailyQuota()`、保留安全餘額、使用純文字模板且無 tracking。
6. 實作 outbox delivery states、idempotent retry、provider exception handling、bounce/reconciliation與 cleanup job。
7. 建立 authenticated same-origin routes，加入 CSRF/authorization、generic responses、per-user/email/origin limits、global quota circuit breaker與必要 abuse protection。
8. 將 audit sink接到受保護 allowlisted AuditLog，設定告警但禁止 email、code、pepper與任意 request body進入 logs。
9. 在經核准的 staging deployment只用擁有者控制的測試地址做初次/重寄/錯碼/expiry/quota smoke test，檢查 Sheet/outbox/audit一致性。
10. 經安全、隱私與教學行政核准後才逐步開放；本 Task 未執行以上任何 cloud step。

## Copy-paste handoff

Task 19 已完成 provider-neutral email verification skeleton，全程未寄真實郵件。支援 institutional 與 optional contact 各自驗證、均勻六位 code、16-byte salt + SHA-256 hash-only storage、10分鐘 expiry、5次 attempts、60秒 cooldown、每 challenge 3次 send、重寄使舊碼失效、成功 verifiedAt與去敏 audit；attempt用完後鎖到原 expiry，不能重新 start繞過。Mock flow end-to-end通過，Amber fixture有分開的 institutional/contact records；控制 NTU Mail明確不等於選課證明。全套檢查通過：GAS 44/44、Portal 25/25、Pytest 36/36、secret scan 269 files/0 findings，Astro 41 files無問題，GAS build成功。Google官方於2026-07-19列 consumer Apps Script MailApp 100 recipients/day、Workspace 1,500/day，quota會變且resend也消耗；部署日須重查並用getRemainingDailyQuota。尚缺 production repository/outbox/MailApp adapter/HMAC pepper/auth/anti-enumeration/rate limits/retention與實際NTU domain、enrollment authority決策；報告列出10項精確cloud steps。建議下一步 Task 20 multibot architecture。
