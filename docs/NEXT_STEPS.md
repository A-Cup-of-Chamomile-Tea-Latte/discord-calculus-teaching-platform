# Ordered next steps

更新日期：2026-08-24

## 已完成 checkpoint：Portal／Bot／academic data 整合

- Portal 公開架構、115-1 班別資料、production v6 基礎與 Bot UX 候選版已放入同一整合分支。
- public artifact 只保留 5 個允許頁面；未接線的加入與案件查詢 fail closed。
- Bot candidate 對齊五態、48＋48、C01–C16／C99 案號、Course Manager 五態與 Discord DM。
- 舊 Portal 與 Private dump 入口進入可逆 archive／inactive stage，不與現行設計並列。
- 本機品質閘已通過；不等同 production deploy 或 observation PASS。

## 1. Production observation 最終 checkpoint

1. 2026-08-24 17:12 後取得新的 owner-only `/ops status` 安全摘要。
2. 確認三服務健康、heartbeat 新鮮、remote 是唯一 writer、schema v6、queue 排空、manual attention 為 0。
3. 核對 compact Sheet projection、OAuth refresh、daily backup 與 SQLite integrity。
4. 若 production code、schema 或 service config 換版，24 小時 observation 必須從新 smoke PASS 時間重新起算。

## 2. Candidate migration 與 Discord 設定

1. 以 production v6 consistent backup 的獨立副本演練 v6 → v10；核對 ledger、integrity 與 row counts。
2. 填入 course role、visitor role、C01–C16 class role、class→Module、Private category 與 reviewer/admin 映射。
3. 用教師白帳號／學生測試帳號驗證加入、duplicate、waiting、approve、reject、archive／restore、Private ACL 與 DM。
4. 演練完成只形成 release candidate；沒有新的明示部署授權，不寫入 production。

## 3. Portal 動態能力

### 加入申請

- 建立 same-origin backend、CSRF／rate limit 與 SQLite adapter。
- 接 Course Manager durable queue、Discord member resolution、角色／暱稱與 Discord DM。
- duplicate／waiting／approved／rejected／archived 必須冪等且可稽核。

### 案件查詢

- 接受一般與 `-P` 完整案號。
- 只回傳案號、類型、狀態、更新時間、是否有教學團隊回覆與 Discord 連結。
- 不回傳題目、對話、作者、附件、AI、內部 ID；不提供 list-all 或背景 polling。

## 4. 教學上線準備

- Owner 用教師白帳號跑一次 Discord 新手流程，再補基礎／建議設定圖解簡報。
- 完成資料告知、保留／刪除、Private ACL regression、事故責任與 rollback。
- Repository、網址、backend origin 與首次 deploy 仍須明示核准。

## 固定停止線

- 不把本機 candidate 測試寫成 production PASS。
- 不把 raw messages、學生姓名／ID、Email、Discord ID、附件、Private Support、SQLite rows、credential 或 secrets 放進 Git、聊天或公開 artifact。
- SQLite 是 operational authority；Browser 永不持有 Bot token、Google owner credential 或 SQLite write access。
- 未完成 auth、rate limit 與 storage gate 前，不開啟公開動態 submission／lookup。
