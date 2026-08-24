# Ordered next steps

更新日期：2026-08-25

## 已完成 checkpoint：Portal／Bot／academic data 整合

- Portal 公開架構、115-1 班別資料、production v6 基礎與 Bot UX 候選版已放入同一整合分支。
- public artifact 只保留 5 個允許頁面；未接線的加入與案件查詢 fail closed。
- Bot candidate 對齊五態、48＋48、C01–C16／C99 案號、Course Manager 五態與 Discord DM。
- 舊 Portal 與 Private dump 入口進入可逆 archive／inactive stage，不與現行設計並列。
- 本機品質閘已通過；現行 production v6 的 24 小時 observation 也已另行 PASS，但兩者都不等同 candidate v10 deploy。

## 已完成 checkpoint：Production v6 observation

- 2026-08-24 17:12 後的 owner-only `/ops status` 顯示三服務健康、schema v6、queue 與 manual attention 歸零。
- Remote／Mac 唯讀核對確認 remote 持續是唯一 writer，三個 services active／enabled，受限部署入口仍就緒。
- Phase 2C v6 baseline 於 2026-08-24 17:16 判定 PASS；這不是 candidate v10 的部署核准。

## 1. Candidate migration 與 release safety

目前：v10 release `3411aff` 與 `target_schema=10`／`ADDITIVE` request 已在 remote staging；owner 已明示
deploy 授權。production 仍是 v6，等待 root-owned deployer 更新後才可執行 restricted deployer。

1. 取得 production v6 consistent backup；只在獨立副本演練 v6 → v10。
2. 核對 backup readability、ledger 1–10、integrity、row counts、rollback 與有界 retention。
3. 填入 course role、visitor role、C01–C16 class role、class→Module、Private category 與 reviewer/admin 映射。
4. 形成固定 smoke／rollback runbook；沒有新的明示部署授權，不寫入 production。

## 2. Portal 動態能力（本機候選已完成，正式接線仍是 gate）

- `POST /api/join` 與 `POST /api/cases/lookup` 已完成同源 middleware、session authorization、CSRF、rate limit、generic failure response、SQLite adapter、Course Manager queue、content-free projection 與 metadata-only audit。
- Portal backend tests 17/17 PASS；Portal check 0 diagnostics；Portal Vitest 61/61 PASS；以 `/api/join`、`/api/cases/lookup`、`/api/join`（CSRF seed）設定的 public artifact build PASS。
- 這些是 repository／local receipts，不是 production deploy、真實 OAuth、Discord ACL 或 public URL evidence。

### 加入申請

- 注入受保護 same-origin session provider、durable audit sink、CSRF／rate limit 設定與 SQLite adapter；在 deployment 前完成白帳號驗證。
- 接 Course Manager durable queue、Discord member resolution、角色／暱稱與 Discord DM。
- duplicate／waiting／approved／rejected／archived 必須冪等且可稽核。

### 案件查詢

- 接受一般與 `-P` 完整案號（`POST /api/cases/lookup`，一次一案）。
- 只回傳案號、類型、狀態、更新時間、是否有教學團隊回覆與 Discord 連結。
- 不回傳題目、對話、作者、附件、AI、內部 ID；不提供 list-all 或背景 polling。

## 3. 白帳號 E2E 與部署決策

- Owner 用教師白帳號／學生測試帳號驗證加入、duplicate、waiting、approve、reject、archive／restore、
  Private ACL、DM、案件查詢與 Discord 新手流程。
- 完成資料告知、保留／刪除、Private ACL regression、事故責任與 rollback。
- 上述 gate 無異常後，才向 owner 要一次明示部署核准；若沒有實際風險，不重複詢問或額外等待。
- v10 換版後不強制再等 24 小時。以 deployment smoke、白帳號 E2E 與 rollback readiness 作主 gate；
  只有具體穩定性疑慮時才啟動最多約 8 小時的 checkpoint observation。

## 暫緩的外部決策

- Repository owner、公開 URL、backend origin、CNAME 與 rollout 範圍留給 PM 與課程 owner 決定。
- 這些 gate 暫不阻擋 production backup rehearsal、設定收斂與 Portal backend 實作。

## 固定停止線

- 不把本機 candidate 測試寫成 production PASS。
- 不把 raw messages、學生姓名／ID、Email、Discord ID、附件、Private Support、SQLite rows、credential 或 secrets 放進 Git、聊天或公開 artifact。
- SQLite 是 operational authority；Browser 永不持有 Bot token、Google owner credential 或 SQLite write access。
- 未完成 auth、rate limit 與 storage gate 前，不開啟公開動態 submission／lookup。
