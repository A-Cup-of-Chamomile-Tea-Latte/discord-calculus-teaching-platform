# Post-v13 Portal smoke evidence

核對日期：2026-08-28（Asia/Taipei）

## 結論

- Production core：依遠端交接為 active release `feab01757897`、SQLite schema 13、三服務 active／enabled、critical queues 0；Discord `/ops status` 與 `/ops attention-list` 已通過。本機沒有直接登入朋友主機重驗。
- Portal backend：exact v13 source 已有 same-origin join、Email start／verify、one-case lookup、匿名分 scope session issuer、CSRF、rate limit、generic errors 與 metadata-only audit；backend tests 25 PASS。
- Portal staging package：builder、installer、rollback、systemd unit、smoke 與 proxy contract 已完成並通過測試，ready but not deployed。真正的 host-bound package 尚待實際 HTTPS origin、base path、loopback port 與 proxy adapter；現有測試 artifact 不可部署。
- Portal rollout：未完成。現有 production 交接只列三個 core services，沒有 Portal service 或正式 session issuer 的部署證據。Owner-only GAS provider 實寄已通過，但 external staging、Portal／remote bridge 白帳號 E2E 與 production hosting 都不列為通過。
- Discord 永久入口：targeted provisioner 與 ACL preflight 已完成；live Guild 尚未建立 `開啟隱密案件`。先前失敗的 apply 已 rollback，沒有留下入口 channel 或 mapping。
- Department handoff：`NOT APPROVED`。不得交付現有 draft、staging package 或 public artifact，也不得掛上統一教學網。
- Browser boundary：public artifact 只包含 same-origin API path，掃描未發現 SQLite path、session secret、Bot token 或 Google credential。瀏覽器不直接讀寫 SQLite。
- 獨立本機 Email journey：已用暫存 SQLite 與 capturing adapter 跑通 API 建立 challenge、durable outbox、worker 取件、驗碼、加入申請與敏感 payload 清除；不連 Google、不寄真信、不修改 production。
- 受控真 Email service chain：temporary SQLite→Portal challenge→outbox→owner-only GAS v14→人工驗碼→`PENDING_REVIEW` PASS；process 結束刪除暫存 DB，production／Discord mutation 均為 NO。
- Connected browser smoke：Guest form／Email dialog／申請成功，以及一般／Private lookup PASS；console 0 error／warning。Synthetic capture receipt contract defect 已修正並加入 regression test。

## 可重現檢查

| 檢查                                           | 結果                                                                                                               |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Portal Vitest                                  | 12 files／67 tests PASS                                                                                            |
| Astro check                                    | 68 files，0 error／warning／hint                                                                                   |
| Portal backend tests                           | 25 PASS                                                                                                            |
| Portal／Email／staging／contract focused tests | 51 PASS（含 controlled real-provider runner 與 capture worker regression）                                         |
| Python repository suite                        | 最新完整 gate 372 PASS；implementation head `f79827e` 收集 374 tests，本輪未重跑完整 suite                         |
| Discord 永久入口 focused suite                 | 25／25 PASS                                                                                                        |
| GAS MailApp adapter                            | unit tests PASS；immutable v14 受控實寄由 provider 接受，寄送前 quota 100，duplicate no-op，收件匣人工確認內容正確 |
| Public build                                   | 預設 fail-closed 60、connected candidate 61 個 base-safe local references；各 5 public pages                       |
| 數學系 hosting                                 | `NOT APPROVED`；external staging 與正式 handoff gate 通過前不測、不掛載                                            |
| 本機桌面 smoke                                 | post-v13 整合版 8 routes 均有主標、無 console error、無整頁水平 overflow                                           |
| 本機窄螢幕 smoke                               | post-v13 整合版 5 個公開頁面無整頁水平 overflow                                                                    |

## 目前 staging gate

Portal backend 現已具備 local anonymous session issuer，分開 `JOIN`／`LOOKUP` scope、session／IP／global rate limit、短效安全 cookie 與 key rotation。這排除了先前「瀏覽器拿不到 session」的 local blocker，但尚未在外部 HTTPS same-origin staging 從頁面點到底。

Owner 已於 2026-08-28 決定完整 Case ID 可作 content-free status lookup 的 bearer capability，不額外要求 user ID／OAuth。此決定只適用於最小唯讀狀態；未來若增加內容或案件操作，須另加身分驗證。Local synthetic composition 使用 temporary SQLite、獨立 audit DB、staging-only secret 與 capturing-only Email transport，一般與 Private lookup 均以假案件驗證；尚未部署 external staging。完整 contract 與停止條件見 `docs/ops/PORTAL_BACKEND_V1.md`。

網站修改已整理成 `codex/portal-post-v13`。本次文件整理前的 implementation head 為 `f79827e`，已包含 staging package hardening、GAS dual-scope bridge 與 Discord 永久入口 preflight；這些 post-v13 變更尚未 external staging 或 production deployment。

## 需要授權的下一步

1. 先完成 Discord 永久入口 targeted live apply 與白帳號 `/private open` E2E；不碰其他 Guild 資源。
2. 取得實際 staging host facts，從 exact implementation commit 建立新的 host-bound package。
3. 在非數學系的 external staging 重現 local issuer、same-origin HTTPS、synthetic SQLite 與白帳號 click-through；不接 production authority。
4. GAS 單封實寄、quota receipt、收件內容與重複投遞已通過；新的 challenge 已完成 Portal→outbox→GAS→人工輸入驗證碼，申請進入 temporary SQLite 的 `PENDING_REVIEW`。Production Portal rollout 與 Discord 白帳號審核仍分開驗收。
5. 完整 staging 通過後，才評估新增只綁 loopback 的 Portal service 並接 production SQLite authority；這會改動 production service 與 secrets，需明示授權。
6. Department handoff 維持 `NOT APPROVED`。只有 PM 明示 `APPROVED FOR DEPARTMENT HANDOFF` 後，才能準備並交付對應 exact artifact。
