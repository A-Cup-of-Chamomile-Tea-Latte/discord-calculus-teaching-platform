# Implementation status

Last repository／AI handoff reconciliation: 2026-08-26（Asia/Taipei）

> 本頁分開記錄「已驗證的 production」與「repository 候選版」。2026-08-24 的 Phase 2C 收尾只做
> remote／Mac 唯讀核對，沒有部署、重啟服務或寫入 live data；本機 candidate 測試不冒充 production 狀態。

## Canonical snapshot

| 領域 | 現況 |
| --- | --- |
| Production writer | Remote Linux 是唯一 production writer；Mac writers 已停止 |
| Production runtime | 三個 systemd services；2026-08-24 17:16 唯讀核對均 active／enabled，owner-only 狀態摘要均為 `HEALTHY` |
| Production DB | Remote SQLite schema v6；lifecycle 使用 durable queue／stage resume／retry／idempotency |
| Observation | 現行 v6 baseline 的 24 小時 observation 已於 2026-08-24 17:16 PASS；remote 持續是唯一 writer，三類 queue 與 manual attention 均為 0。此收據不替 v13 deployment 背書 |
| Repository candidate | v13 deployment preparation 正在隔離分支收尾；exact commit／archive 尚未凍結，remote staging request 尚未更新 |
| Google | SQLite 是 operational authority；Sheets 是 compact projection，不是第二套主資料庫 |
| Portal | 公開／reviewer artifact 分離；學生面收斂為靜態資訊入口與已完成本機驗證的最小 backend，尚未部署 |
| Portal backend | same-origin email start／verify、join／one-case lookup 已在 runtime candidate 實作；正式 session provider、durable audit sink、origin 與 rollout 尚未接線，public build 預設仍 fail closed |
| Email | 只用於加入申請地址驗證；SQLite durable outbox 與 owner-only GAS provider candidate 已完成。Bound GAS 與 candidate 相同；standalone 尚未更新 email sender，也尚未寄真實測試信。Public／Private 案件通知維持 Discord DM-only |

## Repository integration checkpoint

- 案件狀態統一為 `OPEN`、`TRACKED`、`IDLE`、`CLOSED`、`AUTO_CLOSED`；`REOPEN` 是 lifecycle event，不是長期狀態。
- 計時採 48＋48 小時，且只在教學團隊真的回覆後啟動；「接手案件」不再冒充回覆。
- 學生案號採 `C{classCode}-{token}-{MMDD}-{HHmm}`；Guest 採 `Guest-{token}-{MMDD}-{HHmm}`；Private Support 固定 `C99…-P`。
- Forum 標題採 `[M{n} | C{classCode}][mainTag] userTitle`，班別與 Module 從正式設定取得。
- 加入申請後端重驗 NTU Mail、選填 Gmail、C01–C16 與 Discord username；Course Manager 使用兩級權限、五態審核、Discord DM 與持久暱稱配置。
- Private Support 由 Discord `/private open` 取得同一套主標籤與 AI 選擇，再建立受限頻道；圖片留在 Discord，SQLite 只保存必要案件狀態與 Discord 參照。
- Private Support 無唯一班級 mapping 時使用受控 module metadata fallback；這不改變 Discord overwrites。ACL 仍只允許提出者、Bot 與授權教學團隊。
- Private 在 48＋48 自動結案或手動結案滿 48 小時後，先 verified dump 再刪頻道；失敗保留頻道並進人工接管，已刪除案件可建立 replacement case。
- public case lookup 只允許 content-free projection：案號、類型、狀態、更新時間、是否已回覆與 Discord 連結。
- Portal backend v1 已建立 `POST /api/join` 與 `POST /api/cases/lookup`；使用外部 signed session、CSRF cookie、same-origin／Host allowlist、JSON／form allowlist、rate limit、generic errors 與 metadata-only audit。Browser 不持有 SQLite 或 Discord credential。
- Discord allowlisted live Guild 已建立 C01–C16，三個 managed forums、Private category、role hierarchy
  與 bot permissions 經 read-only verify 為 0 error／0 warning；真實 IDs 只保存在 mode `0600` secure mapping。
- Deployment hardening 後的 worktree gate 通過 Portal 61、Config 3、GAS 70、Python 331、Ruff、format、mypy、build、production npm audit 0 與 secret scan；exact commit 後仍須產生 archive checksum 與外部 evidence receipt。
- schema-shaped v6 暫存副本已演練到 v13：ledger 1–13 完整、`integrity_check=ok`、核心 row counts 不變。這不取代 production consistent backup rehearsal。

## Portal 現況

### 公開學生面

- Header 收斂為加入與設定、查案件、使用指南；視覺為深綠、暖白與燙金重點。
- 加入頁支援臺大學生／訪客、Discord username、正式 C01–C16 班別與教師標籤。
- 一般與 `-P` 案號共用查詢介面；正式 adapter 尚未接線，public build 不以 fixture 冒充成功。
- Discord 指南與使用／隱私說明合併為 `/guide/`；Portal 不代收提問內容或附件。
- reviewer 內部頁與 public artifact 已分離；public artifact 只保留允許的 5 頁。

### 內部與封存

- Course Manager reviewer UI 與加入狀態／去重 policy 已建立；same-origin adapter 已完成本機 candidate，正式 session／audit／origin 接線仍待 gate。
- `/status/` 是管理員建造 dashboard；所有 gate 完成後才轉長期 monitor。
- 舊 `/ask/`、`/private-support/`、`/discord-guide/` 留 reviewer 封存提示，public build 移除。
- 封存 stage 不是新決策來源；恢復舊設計前須先寫 decision，只取回仍適用的部分。

## 尚未完成

1. 在 production DB consistent backup 的獨立副本演練 v6 → v13，核對 backup readability、integrity、ledger、row counts 與 rollback；通過後仍須另行授權才可部署。
2. 將已完成本機驗證的 Portal same-origin 加入申請與單案查詢 backend 接到受核准的 session／audit／origin runtime；完成白帳號 E2E 與 Private 最小揭露驗收後才開放。
3. Production Discord role／category／class-module 的 live provisioning 與 secure ID capture 已完成；仍須由 host preflight 不輸出值地確認 `BOT_OWNER_IDS` bootstrap，部署後再做白帳號端到端驗收與 reviewer grant。
4. 2026-08-25 授權屬舊候選版；修補後 exact release 需在 backup／mapping gate 通過後再取得一次明示
   deploy decision。restricted deployer 的 staging migration、checksum、integrity、fresh health 與
   rollback 任一失敗仍須 fail closed。若無實際穩定性風險，不另加等待窗口，必要時最多約 8 小時。
5. Repository owner、公開 URL、backend origin、CNAME 與首次 Portal rollout 維持人工 gate，暫不阻擋上述上線前工程。

詳細 runtime observation：`docs/ops/PHASE2C_24H_OBSERVATION.md`。
