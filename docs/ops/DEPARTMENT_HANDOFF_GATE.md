# 統一教學網系辦交付 gate

狀態：`DRAFT_ONLY / NOT_APPROVED FOR DEPARTMENT HANDOFF`

Branch push、local staging、GAS provider PASS 或產生 static artifact 都不構成系辦交付授權。只有 human owner 收到 PM 明確文字 `APPROVED FOR DEPARTMENT HANDOFF` 後，才能把 final package 交給系辦或要求掛上微積分統一教學網。

## 核准前必須全 PASS

1. Public artifact 只保留五個核准頁面，沒有 reviewer／internal assets、secrets、SQLite path 或 credential。
2. Connected Portal 在隔離 staging 完成 browser join、Email challenge／verify、一般與 Private content-free lookup；same-origin、CSRF、session scope、rate limit 與 generic errors 均通過。
3. Owner-only GAS provider 與 Portal→outbox→GAS service chain 通過；收件地址、驗證碼與截圖不進 package。
4. Production rollout 另有 backup、rollback、loopback backend、reverse proxy 與白帳號 ACL／Discord E2E 證據；不能用 local PASS 代替。
5. 系辦 package 的 API 邊界只允許同站 `/api/`；不得把 Bot token、OAuth credential、production DB、Private 內容或內部管理頁交給系辦。
6. Package hash、source commit、rollback／停止條件、系辦只需執行的步驟與責任邊界均已由 PM 與 human owner 人工核對。

## 草案內容

- 五頁 public static artifact 與 checksum。
- `/api/` reverse-proxy contract；不包含 secrets 或 backend credential。
- cache／CSP／HTTPS／health check 要求。
- smoke 與停止條件；FAIL 時不公開 endpoint、不自行改 backend。
- rollback：移除 static artifact 或停用 `/api/` route，不刪 production SQLite。

目前可整理草案與測試證據，但不得傳送給系辦、設定正式 URL、CNAME、hosting 或 rollout。
