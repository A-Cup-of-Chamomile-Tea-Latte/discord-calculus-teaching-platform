# 統一教學網系辦交付 gate

狀態：`DRAFT_ONLY / NOT_APPROVED FOR DEPARTMENT HANDOFF`

Branch push、local staging、GAS provider PASS 或產生 static artifact 都不構成系辦交付授權。只有 human owner 收到 PM 明確文字 `APPROVED FOR DEPARTMENT HANDOFF` 後，才能把 final package 交給系辦或要求掛上微積分統一教學網。

## 已知事實與不可代替的確認

截至 2026-08-28，公開可驗證的正式入口是
`https://www.math.ntu.edu.tw/~calc/Default.html`，由 HTTPS Apache endpoint 提供；頁面內容同時指向校方 CCMS。這只能證明目前網址與公開呈現，不能證明專案可直接上傳檔案、取得 Apache 設定權、執行 server runtime，或新增 reverse proxy。

`/~calc/DC-platform-beta/` 目前只是本機 build contract，不是系網已核准的正式 path。以下項目必須由系網管理方逐項回答，不能由 PM、朋友主機或程式碼猜測：

| 介面 | 必須取得的明確答案 |
| --- | --- |
| 部署型態 | 只接受 CCMS 內容／連結、可上傳 static artifact、可建立子路徑，或可設定 reverse proxy／server runtime？ |
| 正式位置 | 最終 HTTPS origin、path、入口頁名稱、是否保留 `Default.html`，以及舊連結／查詢參數相容要求。 |
| 更新權限 | 誰能發布、使用何種介面（CCMS、SFTP、Git、工單或由網管代上傳）、是否有維護時段與審核人。 |
| TLS／same-origin | TLS 在哪一層終止；是否能讓 static pages 與 session／join／lookup 三組 `/api/` routes 位於完全相同的 scheme、host、port 與 base path。 |
| API 網路路徑 | 系網是否能把限定 `/api/session`、`/api/join*`、`/api/cases/lookup` 轉送到朋友主機的固定 HTTPS endpoint；來源 IP、DNS、timeout、body-size 與 header 規則。 |
| Proxy 信任 | 是否覆寫而非串接外來 `X-Forwarded-For`、保留 canonical `Host`，以及 backend 能信任的唯一 proxy IP。 |
| Session／cookie | 子路徑下 `Secure; HttpOnly; SameSite=Strict` cookie 是否能正常回傳；cookie path、clock、key rotation 與登出／失效方式。 |
| CORS／CSRF | current contract 是 strict same-origin，不使用瀏覽器跨站直連 API；Origin、Host 與 `X-CSRF-Token` 必須原樣到達 backend。 |
| Secrets／資料庫 | session key、GAS credential、Bot token 與 SQLite 只留在朋友主機受限路徑；不得放入 static artifact、CCMS、系網 web root 或 browser。SQLite 不提供下載、NFS 或公開管理介面。 |
| Staging | 是否提供獨立 HTTPS hostname/path、測試期限、允許的測試人員與清除日期；沒有的話先使用朋友主機的獨立 synthetic staging。 |
| 可觀測性 | 系網可提供的 access/error log、request ID、health probe、告警窗口與 log 保存期；不得記錄 Case ID、Email、驗證碼或 cookie。 |
| 更新／回退 | static artifact 如何 atomic 切換、API route 如何 enable/disable、前一版保留多久、失敗時由誰回退。 |

若系網只能放連結，Portal static 與 API 必須一起留在另一個受控 HTTPS origin，系網只連到該 origin。不能把系網 static page 配上 browser 跨站直連朋友主機 API，因為這違反 current same-origin session／CSRF contract。若系網能放 static 但不能 proxy，仍採「外部同源 Portal + 系網連結」，不新增臨時 CORS 例外。

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

## 最小可重複更新協議

### 1. 我們封裝與驗證

1. PM 指定單一 source commit、target origin 與 base path；HOLD／obsolete package 不得重用。
2. 從 clean worktree 產生 public 五頁 artifact；執行 typecheck、Portal tests、public-route verifier、secret scan、symlink／inventory scan。
3. package 必須含 immutable `manifest.json`、逐檔 `SHA256SUMS`、外層 archive SHA-256、source commit、origin、base path、schema/kind 與 `productionConnected` 標記。
4. 另附一頁部署單：exact artifact、必要設定、預期 health、smoke、停止條件、上一版 release ID 與 rollback 指令。所有 secret 由 host owner 在主機建立，不進 package。

### 2. 對方部署

1. 部署者先核對外層與逐檔 checksum、manifest 的 origin/base path，以及簽核中的 exact release；任一不符立即停止。
2. 先裝到新的 versioned directory，不覆寫 current；先跑設定語法檢查與 loopback health。
3. external staging 先使用 synthetic SQLite、獨立 session secret、capture-only Email 與獨立 audit store。production path 必須對 staging service 不可見。
4. 只有 staging smoke PASS 後才 atomic 切換 static symlink／proxy route；不得順便重啟 Bot、migrate production SQLite、寄真信或變更 Discord。

### 3. 驗收證據回傳

部署者只回傳 metadata，不回傳 cookie、Email、Case ID、驗證碼、credential 或 DB：

- deployment timestamp、hostname/role、release ID、source commit、archive SHA-256；
- checksum、config syntax、service active、loopback health、external HTTPS health 的 PASS/FAIL；
- browser 五頁、base-path assets、JOIN/LOOKUP scope isolation、一般／Private synthetic lookup、real-email refusal 的 PASS/FAIL；
- production DB modified=`NO`、Discord mutation=`NO`、real email sent=`NO`；
- 若失敗：第一個 safe error code、是否已 disable route／rollback、目前 active release ID。

PM 只接受 exact evidence；截圖可補充 UI，但不能代替 release/hash 與 smoke 結果。

### 4. 後續更新與回退

- 每次改版都是新 commit、新 release ID、新 archive/hash；不得覆寫或「補檔」舊 release。
- 先在相同 staging contract 驗證，再由有權部署者 promote exact artifact。static、proxy contract 與 backend 若不同步，整次 rollout 停止。
- 至少保留上一個已驗收 release。smoke、session/cookie、API 或 public-route 任一失敗，先 disable 新 route／恢復前一 release；不刪 SQLite、不自行 downgrade schema。
- 回退後重新跑 public health 與最小 lookup smoke，回傳 active release ID；資料相容性不確定時維持 HOLD，由 PM 決定，不要求系網臨場修程式。

## 真正掛到數學系微積分統一教學網還缺什麼

依阻塞順序，並非 Portal build PASS 就算完成：

1. **先完成外部 synthetic staging**：取得非 production HTTPS origin、host-owner proxy adapter、獨立 secret／DB／audit／Email capture，重現 same-origin browser journey 與 rollback。
2. **取得系網的真實介面答覆**：以上表格的部署型態、URL/path、TLS、proxy、權限、log、更新與 rollback 必須有具名 owner 回覆。
3. **選定唯一 topology**：優先為系網同源 static + bounded `/api/` proxy；若不支援，採系網只連到外部同源 Portal。current runtime 不支援「系網 static + browser 跨站 API」。
4. **準備 department-bound artifact**：使用系網核准的 exact origin/base path 重建，不可拿 example staging package 或舊 HOLD packet 改名交付。
5. **完成 staging 與真人 E2E gate**：先網站主流程，再補 negative ACL、DM、close/reopen、48 小時 Private dump；負向 ACL 最晚在正式 rollout 前通過。
6. **取得兩個明示核准**：PM `APPROVED FOR DEPARTMENT HANDOFF` 後才交件；human owner 再核准 production rollout。系網管理方只執行已同意的 hosting/proxy 操作，不承擔 Bot、SQLite 或應用除錯。

目前可整理草案與測試證據，但不得傳送給系辦、設定正式 URL、CNAME、hosting 或 rollout。
