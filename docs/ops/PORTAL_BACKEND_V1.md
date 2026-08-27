# Portal backend v1

狀態：`IMPLEMENTED_LOCAL / NOT_DEPLOYED`

這是 post-v13 Portal candidate 的最小 same-origin backend 邊界。它不處理 CNAME、repository owner、公開 URL、hosting、OAuth provider 或 rollout；未注入正式設定時，public build 仍維持 fail closed。

## Routes

| Method | Path | 用途 | 安全邊界 |
| --- | --- | --- | --- |
| `GET` | `/api/join`（或 lookup route） | 由已授權 session seed 短效 CSRF cookie | 嚴格 `Origin` allowlist；session cookie 由外部 auth provider 管理，CSRF cookie `SameSite=Strict` |
| `POST` | `/api/join/email/start` | 建立 session/email-bound 六位數 challenge 並排入獨立 GAS sender | NTU/聯絡 Email server validation、PBKDF2 code hash、10 分鐘 expiry、rate limit |
| `POST` | `/api/join/email/verify` | 驗證 challenge | 最多五次、session binding、metadata-only audit |
| `POST` | `/api/join` | 消耗已驗證 challenge，建立或去重加入申請 | session、`X-CSRF-Token`、body allowlist、每 session／IP rate limit |
| `POST` | `/api/cases/lookup` | 一次查一個一般或 `-P` 案號 | session、`X-CSRF-Token`、每 session／IP rate limit；不提供 list、polling 或內容 |

加入 endpoint 只回傳通用 `ACCEPTED`；duplicate 不回顯目前申請、Email、Discord ID 或權限。案件查詢只回傳 `case-status-lookup-response.schema.json` 的 allowlist 欄位，Discord URL 只接受 `https://`。

所有結果（含 invalid、not found、拒絕與 rate limit）都送往 metadata-only `AuditSink`；事件不包含案號、Email、Discord username、IP 原值、request body、案件內容或 raw SQLite row。`PortalBackend` 沒有 audit sink 時拒絕啟動。

## Storage boundary

backend 只透過既有 `Repository` 寫入與 Bot 相同的 canonical SQLite。加入申請使用 `join_applications`、`join_application_events`、v12 email challenge/outbox 與既有 Course Manager review queue；案件查詢使用 content-free `safe_case_projection`。Browser 不取得 token、SQLite path、row 或 writer access。

session 預期由 trusted same-origin issuer 發出短效簽章 cookie；目前 local implementation 只有 `SignedSessionAuthorizer` 驗證器與 `issue_for_test()`，不自行替瀏覽器建立正式 session。CSRF seed 是對 `/api/join` 或 `/api/cases/lookup` 的 `GET`，不是登入 endpoint。不能把 test token 或 local fixture receipt 當 staging／production evidence。

## Session issuer stage

進入獨立 staging 前必須先完成下列 contract；這些是 session issuer 本身的工作，不得用 static Portal 或 CSRF cookie 代替：

- 決定 issuer 的 trust source，並分開「建立加入申請」與「查詢既有案件」所需的 session scope。匿名 browser session 可支援 Email challenge，但不能自然取得案件 ownership。
- issuer 只把 opaque random subject 放入 session，不放 Email、學號、Discord ID 或案件號；session cookie 必須為 `HttpOnly; Secure; SameSite=Strict`，有 bounded expiry，CSRF cookie 才由 browser script 讀取。
- issuer 與 verifier 使用 staging-only secret，需定義 rotation／key version、失效與 clock-skew policy；不得沿用 production secret。
- 現有 lookup path 對任一 valid session 會呼叫 `safe_case_projection(..., allow_private=True)`。在 subject-to-case ownership 尚未實作前，staging 必須使用 synthetic data 並停用 Private lookup；案號本身不能作唯一授權憑證。
- tests 至少覆蓋：首次 issuance、expiry、tampered signature、cross-origin／wrong Host、cookie attributes、rate limit、rotation、scope mismatch，以及沒有 ownership 時拒絕 Private lookup。

## Independent staging gates still open

- 使用獨立 HTTPS origin、staging-only secret、synthetic／temporary SQLite、獨立 audit DB 與 bounded rate-limit；不可連 production authority。
- 實作並驗證上述 session issuer contract；same-origin reverse proxy 必須能在 staging 重現。
- 以 staging 帳號驗證 join／Email capturing flow；不寄真信、不套 Discord role、不呼叫 Bot。
- Private lookup 在 ownership binding 完成前保持停用；一般 lookup 也只使用 synthetic cases。
- staging smoke、cleanup／rollback 與明示 external staging authorization 仍是 human gate。

未完成上述 gate 前，不應設定 `PUBLIC_JOIN_APPLICATION_ENDPOINT`、`PUBLIC_CASE_STATUS_ENDPOINT` 或 `PUBLIC_PORTAL_SESSION_ENDPOINT` 到任何公開 build，也不應開放動態 submission／lookup。issuer 完成後，staging 預期使用 `/api/join`、`/api/cases/lookup`、`/api/session`；Email start/verify 由 join client 以同站相對路徑呼叫。正式 rollout 仍需另外驗收 production service、白帳號、Email provider、backup 與 rollback，不沿用 staging PASS。
