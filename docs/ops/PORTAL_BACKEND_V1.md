# Portal backend v1

狀態：`IMPLEMENTED_LOCAL / NOT_DEPLOYED`

這是 candidate v10 的最小 same-origin backend 邊界。它不處理 CNAME、repository owner、公開 URL、hosting、OAuth provider 或 rollout；未注入正式設定時，public build 仍維持 fail closed。

## Routes

| Method | Path | 用途 | 安全邊界 |
| --- | --- | --- | --- |
| `GET` | `/api/join`（或 lookup route） | 由已授權 session seed 短效 CSRF cookie | 嚴格 `Origin` allowlist；session cookie 由外部 auth provider 管理，CSRF cookie `SameSite=Strict` |
| `POST` | `/api/join` | 建立或去重加入申請 | session、`X-CSRF-Token`、JSON body allowlist、每 session／IP rate limit |
| `POST` | `/api/cases/lookup` | 一次查一個一般或 `-P` 案號 | session、`X-CSRF-Token`、每 session／IP rate limit；不提供 list、polling 或內容 |

加入 endpoint 只回傳通用 `ACCEPTED`；duplicate 不回顯目前申請、Email、Discord ID 或權限。案件查詢只回傳 `case-status-lookup-response.schema.json` 的 allowlist 欄位，Discord URL 只接受 `https://`。

已通過 session middleware 的 route attempt、storage outcome 與 backend failure 都送往 metadata-only `AuditSink`；middleware rejection 只回 generic response，不記錄原始輸入。事件不包含案號、Email、Discord username、IP 原值、request body、案件內容或 raw SQLite row。`PortalBackend` 沒有 audit sink 時拒絕啟動。

## Storage boundary

backend 只透過既有 `Repository` 寫入 SQLite。加入申請使用 v8 的 `join_applications`、`join_application_events` 與既有 Course Manager review queue；案件查詢使用既有 content-free `safe_case_projection`。Browser 不取得 token、SQLite path、row 或 writer access。

session 是由外部 authenticated same-origin provider 發出的短效簽章 cookie；目前 local implementation 提供 `SignedSessionAuthorizer` 驗證器與 test issuer，不自行替瀏覽器建立登入身分。CSRF seed 是對 `/api/join` 或 `/api/cases/lookup` 的 `GET`，不是登入 endpoint。deployment 前必須由 owner 確認 session provider、單 instance／sticky session，或提供受保護的 shared session store；不能把 local fixture receipt 當 production evidence。

## Release gates still open

- 注入正式 session secret、same-origin allowlist、durable audit sink、TLS cookie 與 bounded provider rate-limit 設定。
- 以白帳號驗證加入、duplicate、waiting、approve、reject、archive／restore 與 Discord DM。
- 以白帳號驗證一般／Private status lookup 的最小揭露與 Discord ACL；不以案號作唯一授權憑證。
- 先取得 production v6 consistent backup，另在副本演練 v6 → v10、rollback 與 row-count receipt。
- deployment smoke、rollback readiness 與明示 deploy authorization 仍是 human gate。

未完成上述 gate 前，不應設定 `PUBLIC_JOIN_APPLICATION_ENDPOINT`、`PUBLIC_CASE_STATUS_ENDPOINT` 或 `PUBLIC_PORTAL_SESSION_ENDPOINT` 到 public build，也不應開放動態 submission／lookup。若通過，三者預期為 `/api/join`、`/api/cases/lookup`、`/api/join`（最後一個只作 CSRF seed）。
