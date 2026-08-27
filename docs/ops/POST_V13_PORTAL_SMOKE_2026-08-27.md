# Post-v13 Portal smoke evidence

核對日期：2026-08-27（Asia/Taipei）

## 結論

- Production core：依遠端交接為 active release `feab01757897`、SQLite schema 13、三服務 active／enabled、critical queues 0；Discord `/ops status` 與 `/ops attention-list` 已通過。本機沒有直接登入朋友主機重驗。
- Portal backend：exact v13 source 已有 same-origin join、Email start／verify、one-case lookup、session 驗證、CSRF、rate limit、generic errors 與 metadata-only audit；focused tests 21 PASS。
- Portal rollout：未完成。現有 production 交接只列三個 core services，沒有 Portal service 或正式 session issuer 的部署證據。Email／白帳號 E2E 不列為通過；數學系 hosting 不作為本輪本機／staging 驗證前提。
- Browser boundary：public artifact 只包含 same-origin API path，掃描未發現 SQLite path、session secret、Bot token 或 Google credential。瀏覽器不直接讀寫 SQLite。
- 獨立本機 Email journey：已用暫存 SQLite 與 capturing adapter 跑通 API 建立 challenge、durable outbox、worker 取件、驗碼、加入申請與敏感 payload 清除；不連 Google、不寄真信、不修改 production。

## 可重現檢查

| 檢查 | 結果 |
| --- | --- |
| Portal Vitest | 12 files／67 tests PASS |
| Astro check | 68 files，0 error／warning／hint |
| Exact post-deploy Portal backend tests | 21 PASS |
| Portal／Email／bridge focused tests | 38 PASS（含完整本機 journey） |
| GAS MailApp adapter | 4 PASS；未呼叫真實 `MailApp` |
| Public build | 5 public pages；61 個 base-safe local references |
| 數學系 hosting | 不作本輪前提；待本機與外部 staging 通過後才測 |
| 本機桌面 smoke | post-v13 整合版 8 routes 均有主標、無 console error、無整頁水平 overflow |
| 本機窄螢幕 smoke | post-v13 整合版 5 個公開頁面無整頁水平 overflow |

## 第一個真正 blocker

Portal backend 與 Email queue 已可在暫存 SQLite 獨立驗證；第一個真正 blocker 是正式 session issuer。沒有 issuer 時，瀏覽器拿不到 `portal_session`，所有 same-origin API request 都會回 401，因此目前還不能宣稱「從公開網頁點到底」已通過。

Maintenance 結論為 `READY_FOR_ISOLATED_STAGING_IMPLEMENTATION`，不是 `STAGING_DEPLOYED`：可以接續建立 session issuer 與獨立 staging composition，但 staging 必須使用 synthetic／temporary SQLite、獨立 audit DB 與 staging-only secret。現有 Private lookup 尚未把 session subject 綁到案件 ownership；完成前應在 staging 停用 Private lookup。完整 contract 與停止條件見 `docs/ops/PORTAL_BACKEND_V1.md`。

網站修改已整理成 `codex/portal-post-v13`，直接基於 post-deploy canonical `f61219b`；整合 commit 為 `5c0472c`，isolated Email journey regression commit 為 `3f04a69`。原工作樹的其他使用者修改沒有混入整合分支。

## 需要授權的下一步

1. 先在非數學系的外部 staging 完成 session issuer、same-origin HTTPS、暫存 SQLite 與白帳號 click-through；不接 production authority。
2. 以明確指定的測試收件匣做一次 GAS 實寄，核對寄件者、到信、驗碼、quota receipt 與重複投遞；需要 GAS deployment、OAuth 與 action-time 授權。
3. 上述通過後，才評估在朋友主機新增只綁 loopback 的 Portal service並接 production SQLite authority；這會改動 production service 與 secrets，需明示授權。
4. 最後才準備數學系五頁 static artifact 與限定 `/api/` 的 hosting 配合，不將數學系環境當成前兩階段的依賴。
