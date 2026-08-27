# Post-v13 Portal smoke evidence

核對日期：2026-08-27（Asia/Taipei）

## 結論

- Production core：依遠端交接為 active release `feab01757897`、SQLite schema 13、三服務 active／enabled、critical queues 0；Discord `/ops status` 與 `/ops attention-list` 已通過。本機沒有直接登入朋友主機重驗。
- Portal backend：exact v13 source 已有 same-origin join、Email start／verify、one-case lookup、session 驗證、CSRF、rate limit、generic errors 與 metadata-only audit；focused tests 21 PASS。
- Portal rollout：未完成。正式網址目前回 404；現有 production 交接只列三個 core services，沒有 Portal service 或正式 session issuer 的部署證據。Email／白帳號 E2E 不列為通過。
- Browser boundary：public artifact 只包含 same-origin API path，掃描未發現 SQLite path、session secret、Bot token 或 Google credential。瀏覽器不直接讀寫 SQLite。

## 可重現檢查

| 檢查 | 結果 |
| --- | --- |
| Portal Vitest | 12 files／67 tests PASS |
| Astro check | 68 files，0 error／warning／hint |
| Exact post-deploy Portal backend tests | 21 PASS |
| Public build | 5 public pages；61 個 base-safe local references |
| 正式網址 | `https://www.math.ntu.edu.tw/~calc/DC-platform-beta/` 回 404 |
| 正式 API 路徑 | `https://www.math.ntu.edu.tw/~calc/DC-platform-beta/api/join` 回 404 |
| 本機桌面 smoke | 首頁、加入、查案件、指南、登入、團隊、審核、狀態頁均有主標、無 console error、無整頁水平 overflow |
| 本機窄螢幕 smoke | 公開五頁無整頁水平 overflow；案號控制項在窄螢幕採元件內水平捲動 |

## 第一個真正 blocker

Portal backend 雖已存在於 v13 source，現有交接卻沒有它成為 production service 的證據；目前列出的三個 production services 都是 Discord／projection runtime。另需先決定並實作正式 session issuer，否則所有 API request 都會因缺少 `portal_session` 而回 401。這兩項完成前，不設定 public endpoint，也不啟用送出與查詢。

目前承載網站設計修改的工作樹也不是 v13 canonical branch：它與 post-deploy maintenance 相差 1 個本地 commit／18 個 canonical commits，且含大量未提交的使用者修改。因此不得直接把整個工作樹當成 production package；發布前要在獨立整合分支保留網站修改並吸收 v13 canonical source。

## 需要授權的下一步

1. 在朋友主機新增只綁 loopback 的 Portal service，將 `PORTAL_SQLITE_PATH` 指向同一份 production SQLite authority，另用獨立 audit DB；這會改動 production service 與 secrets，需明示授權。
2. 決定 public join／lookup 的 session 模型，完成 issuer 與 server-side Beta gate 後再做白帳號 E2E。
3. 請數學系設定 `/~calc/DC-platform-beta/api/` 的 HTTPS reverse proxy，並上傳五頁 static artifact；這會改動正式 hosting，需系辦配合。
4. 完成 GAS 實寄與 Email queue 驗收；不得以 queue=0 代替寄信 E2E。
