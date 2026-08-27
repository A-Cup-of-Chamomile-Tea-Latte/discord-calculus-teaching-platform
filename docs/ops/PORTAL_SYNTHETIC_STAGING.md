# Portal synthetic staging

狀態：`LOCAL BROWSER PASS / NOT DEPLOYED`

用途：在不連 production SQLite、Discord、Google 或真 Email 的情況下，從瀏覽器演練匿名 session、加入流程與一般／Private 案件狀態查詢。這份 staging 不是 production evidence。

## 安全邊界

- 只接受明示的 `PORTAL_STAGING_SYNTHETIC_ONLY=1`。
- 只使用指定 staging root 內的 temporary SQLite、獨立 audit DB 與 capture-only Email 檔案。
- staging root 若已有檔案但沒有 synthetic marker，啟動會拒絕，不覆寫既有資料。
- Email capture 只接受 `synthetic.student@ntu.edu.tw` 與 `synthetic.guest@example.com`，不呼叫 GAS／MailApp。
- backend 預設只綁 `127.0.0.1`；瀏覽器 staging 由另一層 HTTPS same-origin reverse proxy 承載。
- 一般與 Private 都是 synthetic case，只回最小狀態，不回 fixture body。

## 啟動

在 repository root：

```sh
export PORTAL_STAGING_SYNTHETIC_ONLY=1
export PORTAL_STAGING_SESSION_SECRET="$(openssl rand -hex 32)"

node tools/run-python.mjs -m discord_course_bots.portal_staging \
  --root /tmp/calculus-portal-synthetic-staging \
  --origin https://portal-staging.example \
  --bind-host 127.0.0.1 \
  --bind-port 8081
```

啟動輸出會列出兩個 synthetic Case ID、三個本機資料檔路徑與 `productionConnected: false`，不輸出 secret。停止 server 不會刪除 staging root；再次以同一 root 啟動會沿用同一組假案件。

## Browser artifact

static build 只設定同站相對路徑：

```sh
PUBLIC_JOIN_APPLICATION_ENDPOINT=/api/join \
PUBLIC_CASE_STATUS_ENDPOINT=/api/cases/lookup \
PUBLIC_PORTAL_SESSION_ENDPOINT=/api/session \
npm run build:public --workspace @calculus/portal
```

Reverse proxy 必須讓頁面與 `/api/` 位於同一個 HTTPS origin。未設定上述 endpoint 時，public build 維持 fail closed。

## 通過條件

1. `POST /api/session` 分別發出 `JOIN`／`LOOKUP` cookie，跨 scope 使用回 `401`。
2. 一般與 Private synthetic Case ID 都只回最小狀態；response 為 `no-store`／`no-referrer`。
3. connected lookup 不把 Case ID 寫入 URL；頁面顯示「測試中」並在異常時要求以 Discord 為準。
4. Email challenge 只寫入 mode `0600` capture file；其他收件地址 fail closed。
5. staging root、DB、audit 與 capture 都不在 production path，也不載入 production secret。

External staging、數學系 hosting、production SQLite、真 Email 與 production rollout 都是後續獨立 gate。

## Loopback browser smoke

連接版 public artifact 可由同一個 loopback server 同時提供 static pages 與 `/api/`。這只供本機瀏覽器驗收，必須明示 `--allow-loopback-http`，bind host 限 `127.0.0.1`／`::1`，origin 必須精確對應該 port；其他 HTTP origin 一律拒絕。Static resolver 不列目錄、不跟 symlink、不接受 query／fragment 或 traversal。

2026-08-28 已從瀏覽器完成：Guest 表單→capture-only Email dialog→驗碼→申請成功、一般案件查詢、Private 最小狀態查詢，browser console 0 error／warning。首次停止時發現 capture receipt 與 repository allowlist 不一致；修正為共用 `EMAIL_PROVIDER_ACCEPTED` contract，並新增 worker completion／outbox scrub regression test。未知 worker failure 現在會安全停止 staging，不會只讓背景執行緒退出。
