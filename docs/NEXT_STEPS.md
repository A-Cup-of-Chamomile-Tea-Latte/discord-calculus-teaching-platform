# Ordered next steps

更新日期：2026-08-28

## 已完成 checkpoint

- Production Bot 已是 v13，active release `feab01757897`、SQLite schema 13；三個 services active／enabled，critical queues 與 manual attention 為 0。
- GAS provider smoke 與 isolated Portal→outbox→GAS→人工驗碼→`PENDING_REVIEW` service chain 已通過。
- Portal same-origin join、Email verify、Case ID lookup、分 scope session、synthetic SQLite、staging package、installer、rollback 與 smoke 已完成本機驗證。
- 最新完整 gate 通過 Portal 67、Config 3、GAS 70、Python 376 與 secret scan 717／0。

## 1. 完成 Discord 白帳號 E2E

`開啟隱密案件-open-private-case` 與雙語 topic 已成功 live verify。白帳號 `/private open` 與動態 Private channel 建立速度已真人驗證；post-apply 唯讀 plan 為 0 actions、0 unrelated drift。

1. 確認提出者收到 Discord DM 案號。
2. 以另一個普通帳號確認動態 Private channel 不可見；提出者與教學團隊仍可見。
3. 驗證 close／reopen、private dump 與 48＋48 lifecycle；需要等候的 timer 以測試時鐘／管理工具驗證，不必真人等待 96 小時。
4. `08e4bba` 的雙語 Bot 訊息尚未部署；須先產生 exact maintenance candidate，不以本機 PASS 冒充 production PASS。

## 2. 部署 external synthetic staging

Portal staging package 的內容、builder、installer、rollback 與 smoke 已就緒，但尚未部署。現有測試 artifact 不可當成正式 staging package；真正的 package 必須綁定實際 host facts。

1. 取得 staging HTTPS origin、base path、loopback port、proxy 技術與 root-owned proxy adapter。
2. 從 exact implementation commit 建立新的 host-bound package、manifest 與 checksum，不沿用舊 department draft。
3. 在獨立 external staging 使用 synthetic SQLite；不讀寫 production SQLite，不改 production services。
4. 驗證 same-origin session、trusted proxy、CSRF、rate limit、durable audit、Portal 加入、Email 與一般／Private Case ID lookup。
5. 執行 smoke 與 rollback，保存不含 secrets 或學生資料的 receipt。

## 3. 白帳號 E2E 與 production Portal decision

- 在 external staging 走完加入、驗證信、驗碼、`PENDING_REVIEW`、duplicate、waiting 與案件狀態查詢。
- GAS provider PASS 不能代替 Portal 完整 E2E；v13 Bot PASS 也不能代替 Portal hosting PASS。
- External staging 全部通過後，才提出一次 production Portal service／SQLite authority 接線決策。未取得明示授權前，不新增 production service、不設定正式 proxy，也不開 public endpoint。

## 4. Department handoff

目前固定為 `NOT APPROVED`。不得把舊 draft、synthetic staging package 或本機 public artifact 交給系辦，也不得掛上微積分統一教學網。

只有在 external staging、白帳號 E2E、正式 artifact 掃描與 rollback plan 全部通過後，才由 PM 明示 `APPROVED FOR DEPARTMENT HANDOFF`。該授權只涵蓋核准的 exact artifact 與 API boundary，不自動授權 CNAME、其他 hosting 或額外 production mutation。

## 固定停止線

- 不把本機或 synthetic 測試寫成 production PASS。
- 不把 raw messages、學生姓名／ID、Email、Discord ID、附件、Private Support、SQLite rows、credential 或 secrets 放進 Git、聊天或公開 artifact。
- SQLite 是 operational authority；Browser 永不持有 Bot token、Google owner credential 或 SQLite write access。
- Public Case ID lookup 只回傳 content-free status projection；若未來增加內容或案件操作，必須另加身分驗證。
