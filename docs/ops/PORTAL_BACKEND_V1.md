# Portal backend v1

狀態：`IMPLEMENTED_LOCAL / NOT_DEPLOYED`

這是 post-v13 Portal candidate 的最小 same-origin backend 邊界。它不處理 CNAME、repository owner、公開 URL、hosting、OAuth provider 或 rollout；未注入正式設定時，public build 仍維持 fail closed。

## Routes

| Method | Path | 用途 | 安全邊界 |
| --- | --- | --- | --- |
| `POST` | `/api/session` | 建立匿名短效 `JOIN` 或 `LOOKUP` session | 嚴格 Host／Origin、per-IP／global rate limit；兩種 scope 使用不同 cookie，不能互相呼叫 |
| `GET` | `/api/join`（或 lookup route） | 以既有 scope session 重新 seed CSRF cookie | session cookie 為 `HttpOnly; Secure; SameSite=Strict`；CSRF cookie 才由 browser script 讀取 |
| `POST` | `/api/join/email/start` | 建立 session/email-bound 六位數 challenge 並排入獨立 GAS sender | NTU/聯絡 Email server validation、PBKDF2 code hash、10 分鐘 expiry、rate limit |
| `POST` | `/api/join/email/verify` | 驗證 challenge | 最多五次、session binding、metadata-only audit |
| `POST` | `/api/join` | 消耗已驗證 challenge，建立或去重加入申請 | session、`X-CSRF-Token`、body allowlist、每 session／IP rate limit |
| `POST` | `/api/cases/lookup` | 一次查一個一般或 `-P` 案號 | session、`X-CSRF-Token`、每 session／IP rate limit；不提供 list、polling 或內容 |

加入 endpoint 只回傳通用 `ACCEPTED`；duplicate 不回顯目前申請、Email、Discord ID 或權限。案件查詢只回傳 `case-status-lookup-response.schema.json` 的 allowlist 欄位，Discord URL 只接受 `https://`。

所有結果（含 invalid、not found、拒絕與 rate limit）都送往 metadata-only `AuditSink`；事件不包含案號、Email、Discord username、IP 原值、request body、案件內容或 raw SQLite row。`PortalBackend` 沒有 audit sink 時拒絕啟動。

## Storage boundary

backend 只透過既有 `Repository` 寫入與 Bot 相同的 canonical SQLite。加入申請使用 `join_applications`、`join_application_events`、v12 email challenge/outbox 與既有 Course Manager review queue；案件查詢使用 content-free `safe_case_projection`。Browser 不取得 token、SQLite path、row 或 writer access。

session issuer 已在 local candidate 實作：`POST /api/session` 只發匿名、短效、scope-bound cookie，不是登入或身分證明。`JOIN` 只供 Email challenge／加入申請，`LOOKUP` 只供一次一案的狀態查詢；兩者使用不同 session 與 CSRF cookie。不能把 local fixture receipt 當 external staging／production evidence。

## Session issuer stage

2026-08-28 owner 決定：完整 Case ID 是 content-free status lookup 的 bearer capability。所有一般與 Private Case ID 都由 Discord DM 傳給案件建立者，但可以自行轉傳；取得完整案號的人可查看最小狀態。此決定不把 session 或案號宣稱為身分證明。

- issuer 只把 opaque random subject、scope、`iat`／`exp` 與 `kid` 放入 session，不放 Email、學號、Discord ID 或案件號。
- session cookie 為 `HttpOnly; Secure; SameSite=Strict`，最長 30 分鐘；HMAC key ring 支援 key version／rotation，clock skew 限 60 秒。staging 使用獨立 secret。
- lookup 回應只含案號、類型、五態、更新時間、是否回覆與 HTTPS Discord URL；不含內容、附件、作者、Email、Discord ID 或內部 ID。
- Case ID 只以 POST body 傳送；connected lookup 不同步到 URL。API 回應 `no-store`／`no-referrer`，且採 per-session、per-IP 與 global rate limit。
- 頁面「測試中」表示功能可能查不到或狀態延遲，不表示 Case ID 禁止轉傳。
- 若未來加入對話／附件檢視、補充內容、關閉、重開或其他案件操作，bearer Case ID 不再足夠，必須另行決定身分驗證與授權。
- tests 覆蓋 issuance、expiry、tampered signature、cross-origin／wrong Host、cookie attributes、rate limit、rotation、scope mismatch，以及一般／Private synthetic minimal projection。

## Independent staging gates still open

- 使用獨立 HTTPS origin、staging-only secret、synthetic／temporary SQLite、獨立 audit DB 與 bounded rate-limit；不可連 production authority。
- local issuer 與 synthetic composition 已實作；same-origin HTTPS reverse proxy 仍須在 external staging 重現。
- 以 staging 帳號驗證 join／Email capturing flow；不寄真信、不套 Discord role、不呼叫 Bot。
- 一般與 Private lookup 都只使用 synthetic cases；不連 production authority。
- staging smoke、cleanup／rollback 與明示 external staging authorization 仍是 human gate。

未完成上述 gate 前，不應設定 `PUBLIC_JOIN_APPLICATION_ENDPOINT`、`PUBLIC_CASE_STATUS_ENDPOINT` 或 `PUBLIC_PORTAL_SESSION_ENDPOINT` 到任何公開 build，也不應開放動態 submission／lookup。issuer 完成後，staging 預期使用 `/api/join`、`/api/cases/lookup`、`/api/session`；Email start/verify 由 join client 以同站相對路徑呼叫。正式 rollout 仍需另外驗收 production service、白帳號、Email provider、backup 與 rollback，不沿用 staging PASS。
