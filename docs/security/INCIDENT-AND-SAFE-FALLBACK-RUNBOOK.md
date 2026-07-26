# 安全／隱私事件與安全降級 runbook

> 本文是本機原型 runbook，不取代校方法遵、資安或緊急通報流程。上線前必須填入實際人員、聯絡管道、通報時限與可執行的 kill switch。

## 角色

| 角色                 | 責任                                                               | 目前狀態              |
| -------------------- | ------------------------------------------------------------------ | --------------------- |
| Incident commander   | 分級、指派、決定停用／復原與維持 timeline                          | `[TBD]`               |
| Privacy owner        | 評估身分、Private Support、consent/export 影響與通知需求           | `[TBD]`               |
| Service owner        | 停用 Portal/GAS/bot/export，revoke token，保存技術證據             | `[TBD per component]` |
| Data steward         | 限制 Sheet/local export/backup 存取，列出影響 records/destinations | `[TBD]`               |
| Communications owner | 只由核准管道發布已確認事實與暫時指示                               | `[TBD]`               |

任何人都不應因角色空缺而繼續處理敏感資料。在原型期，最安全的預設是停止對外動作與保持 fixture-only。

## 事件分級

| 級別  | 例子                                                                                                | 第一個動作                                                     |
| ----- | --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| SEV-1 | Private Support/raw export/匿名對照被非授權者取得；bot/Google credential 泄漏；公開網頁出現真實資料 | 立即停用影響路徑、限制資料存取，指派 incident commander        |
| SEV-2 | 持續案件枚舉、騷擾 DM、email/code spam、未授權但未確認取得敏感內容、重複發文                        | 關閉該 operation 或收緊 quota，保存相關 metadata，開始範圍判定 |
| SEV-3 | 單一使用者錯誤、無敏感資料的 fixture 失敗、預期內的 provider rate limit                             | 使用原本的 fail-closed 回應，不緊密重試，登記待修              |

不確定是否包含 Private Support、身分對照、credential 或 raw export 時，先當 SEV-1 處理，再依證據降級。

## 前 30 分鐘檢核表

1. **停止擴大**：停用受影響 route/deployment/bot/export/AI handoff，停止 queue consumer 與自動 retry。Private Support 永不 fallback 到公開 channel。
2. **縮小權限**：
   - Discord token 疑似泄漏：停止受影響 bot runtime，只 revoke/rotate 該 bot token，不把另一 bot token 拿來 fallback。
   - Google/GAS 疑似泄漏：停用 deployment，收緊 Sheet sharing/Script Properties access，不使用個人帳號繼續操作。
   - Local export 疑似泄漏：從 sync/share 中移除，將檔案隔離為只有 incident/data owner 可讀，不再複製。
3. **保存最小證據**：記錄發現時間、reporter、受影響 component/version、operation/export/case 的受限 ID、近期權限變更、已做動作。不把 raw body、email、token 貼進普通 chat/ticket。
4. **確認範圍**：資料類型、使用者／案件數、可存取者、開始／結束時間、是否已下載/轉傳/送往 AI、是否有備份，以及 credential 是否可被重放。
5. **決定通報範圍**：只由 privacy/communications owner 依組織已核准流程決定；在調查中不推測、不宣稱法律定性。

## 組件安全降級

| 失敗／事件                              | 安全動作                                                                                                       | 禁止的 fallback                                                                    | 復原證據                                                                                                    |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Public case lookup 被枚舉或回傳過多欄位 | 關閉 lookup/list route，保留不含案件資料的 status page，案件進度暫由課程核准管道處理                           | 不得打包全部正式案件進 static JS；不用無驗證 query secret                          | Projection test、access gate、rate-limit/abuse test、cache purge 與公開 artifact review                     |
| GAS/Sheets 不可用或 access 異常         | 停止 metadata write/reconciliation，對需要 durable state 的 Discord write fail closed 或進明確 outbox          | 不用未稽核的本機檔案當正式 DB；不盲目重送                                          | Owner/access inventory、data reconciliation、quota/lock 正常、已知良好 deployment version                   |
| `course_assistant` 不可用               | 暫停 interaction/write，保留只讀說明                                                                           | 不讓 archive reader 取得 write token/permission                                    | Token/runtime health、idempotency/outbox reconciliation、一次小範圍 smoke test                              |
| `dump_bot`（`archive_reader` 相容名稱）不可用 | 暫停 export/fetch，保留已完成匯出不變                                                                          | 不用 writer token 擴大讀取範圍；不開全 server polling                              | Reader allowlist/permission、checkpoint/hash、bounded retry 正常                                            |
| Private Support provider/ACL 不可用     | 關閉新 intake，在公開頁只說明暫停，使用課程正式核准的替代聯絡方式                                              | 不得建一般案件、公開 thread、降級成匿名公開貼文；不回應案件是否存在                | 角色矩陣、roster revocation、search/preview/notification、closure/backup 都重測且 privacy owner 核准        |
| Email provider/quota 異常               | 暫停寄送與 resend，對使用者回 generic retry-later，保留 outbox 對帳                                            | 不把未送達 challenge 當 verified；不用公開訊息發 code；不繞過 membership authority | Quota safety margin、outbox/provider reconciliation、generic response 與 abuse limits                       |
| Activation abuse/leak                   | 作廢受影響 verifier/permission batch，凍結 redemption route，審查已兌換 permission                             | 不再發同權限長效共用碼；不回顯 plaintext                                           | Revoke/reissue、binding/actor audit、CAS/replay 與 rate-limit tests                                         |
| Raw/sanitized export 泄漏或誤送         | 停止匯出與分析，隔離檔案，列出 destinations/recipients/checksums，重新計算 consent 與 redaction                | 不只重跑 anonymizer 就當無事；不再傳送、不改寫原證據                               | Privacy owner 核准的 scope、recipient deletion/containment evidence、新 review checklist 與 release record  |
| AI/analysis destination 收到未授權資料  | 停止後續 transmission，記錄 destination/model/account/time/input package，依 provider 已核准流程請求限制與刪除 | 不以「去識別化過」代替 incident review；不對其他資料繼續自動送出                   | Consent snapshot/withdrawal、recipient deletion evidence、human release approval、destination policy review |

## 證據處理

- 只保存調查必要的最小證據，分開存放事件 timeline 與受限原始資料。
- Ticket/chat 中只用 operation/export/subject 的受限參考值，不複製 raw message、email、Private Support 內容或 credential。
- 不為了「幹淨」而立即刪除可能的 audit evidence；由 incident/privacy owner 在治理流程下決定保留與安全刪除。
- 若 secret 曾進 Git、log、archive 或聊天，一律當作已泄漏並 revoke/rotate；只刪文字或 rewrite history 不足夠。

## 復原與事後複盤

1. Root cause 已決定，受影響 credential/access 已作廢或縮小。
2. Data reconciliation 已完成；沒有 pending blind retry、重複 write 或公開 fallback。
3. 相關 regression/security tests 通過，在隔離 staging 使用虛構資料完成 bounded smoke test。
4. Privacy owner 完成 affected-data/consent/notification 決策，並記錄於受限 incident record。
5. Incident commander 核准逐步復原，先單一低風險 route，再擴大；復原期持續監看異常。
6. 事後複盤要記錄 timeline、控制為何失敗、未來 owner/deadline 與演練項目，不收錄不必要的學生原始內容。

## 原型緊急停止指示

目前沒有正式部署，因此發現任何真實資料、secret 或外部 side effect 時，立即：

1. 停止執行該流程，不再重試。
2. 不將資料傳給 Discord、Google、email、AI 或任何其他外部系統。
3. 在本機限制存取，以不含原文的方式通知使用者與 privacy owner。
4. 回到 fixture-only 狀態，直到範圍、來源與刪除／保留決策已確認。
