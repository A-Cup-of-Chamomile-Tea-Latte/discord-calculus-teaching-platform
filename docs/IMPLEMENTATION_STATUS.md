# Implementation status

Last repository／AI handoff reconciliation: 2026-08-28（Asia/Taipei）

> 本頁分開記錄「production core」與「尚未 rollout 的 Portal／Email」。v13 core 狀態來自遠端交接與
> Discord metadata-only ops smoke；本機沒有直接登入朋友主機，Email／白帳號 E2E 也尚未完成。

## Canonical snapshot

| 領域 | 現況 |
| --- | --- |
| Production writer | Remote Linux 是唯一 production writer；Mac writers 已停止 |
| Production runtime | Active release `feab01757897`；三個 systemd services 依遠端交接均 active／enabled；Discord `/ops status` 與 `/ops attention-list` PASS |
| Production DB | Remote SQLite schema 13；critical queues 與 manual attention 均為 0 |
| Observation | v13 core 與 metadata-only ops smoke PASS；Email sender、白帳號 ACL／E2E 與 Portal rollout 仍是獨立 gate |
| Repository candidate | Post-deploy baseline 為 `f61219b31344`；Portal candidate `codex/portal-post-v13` 以 `5c0472c`、`3f04a69`、`f401a58` 為既有 checkpoints，未部署且不改變 production active release |
| Google | SQLite 是 operational authority；Sheets 是 compact projection，不是第二套主資料庫 |
| Portal | 公開／reviewer artifact 分離；學生面收斂為靜態資訊入口與已完成本機驗證的最小 backend，尚未部署 |
| Portal backend | same-origin join／Email verify／one-case lookup與匿名分 scope session issuer已在 local candidate 實作；synthetic composition 不接 production。正式 Portal service、origin 與 rollout尚未接線，public build預設仍 fail closed |
| Email | SQLite durable outbox 與 provider code 已存在；實寄與白帳號 E2E 尚未通過。Public／Private 案件通知維持 Discord DM-only |

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
- Portal backend v1 已建立 `POST /api/session`、`POST /api/join` 與 `POST /api/cases/lookup`；匿名 session 分為 `JOIN`／`LOOKUP` scope，使用不同安全 cookie、CSRF、same-origin／Host allowlist、session／IP／global rate limit、generic errors 與 metadata-only audit。Browser 不持有 SQLite 或 Discord credential。
- Owner 接受完整 Case ID 作 content-free status lookup 的 bearer capability；不額外要求 user ID／OAuth。這只適用唯讀最小狀態，未來內容或案件操作須另加身分驗證。
- Discord allowlisted live Guild 已建立 C01–C16，三個 managed forums、Private category、role hierarchy
  與 bot permissions 經 read-only verify 為 0 error／0 warning；真實 IDs 只保存在 mode `0600` secure mapping。
- Deployment hardening 後的 worktree gate 通過 Portal 61、Config 3、GAS 70、Python 334、Ruff、format、mypy、build、production npm audit 0 與 secret scan；exact commit 由外部 evidence receipt 綁定 archive checksum。
- schema-shaped v6 暫存副本已演練到 v13：ledger 1–13 完整、`integrity_check=ok`、核心 row counts 不變。這不取代 production consistent backup rehearsal。

## Portal 現況

### 公開學生面

- Header 收斂為加入與設定、查案件、使用指南；視覺為深綠、暖白與燙金重點。
- 加入頁支援臺大學生／訪客、Discord username、正式 C01–C16 班別與教師標籤。
- 一般與 `-P` 案號共用查詢介面；adapter 與 synthetic staging 已完成本機驗證，production service 尚未接線，預設 public build 不以 fixture 冒充成功。
- Discord 指南與使用／隱私說明合併為 `/guide/`；Portal 不代收提問內容或附件。
- reviewer 內部頁與 public artifact 已分離；public artifact 只保留允許的 5 頁。

### 內部與封存

- Course Manager reviewer UI 與加入狀態／去重 policy 已建立；same-origin adapter、匿名分 scope session 與 synthetic staging 已完成本機 candidate，正式 Portal service／production audit／origin 接線仍待 gate。
- `/status/` 是管理員建造 dashboard；所有 gate 完成後才轉長期 monitor。
- 舊 `/ask/`、`/private-support/`、`/discord-guide/` 留 reviewer 封存提示，public build 移除。
- 封存 stage 不是新決策來源；恢復舊設計前須先寫 decision，只取回仍適用的部分。

## 尚未完成

1. 為 Portal 建立受控 production service，使用同一份 SQLite authority、獨立 audit DB、已驗證的分 scope session issuer 與 HTTPS same-origin proxy；這是新的 production mutation gate。
2. 完成 Portal 白帳號 E2E、Private 最小揭露與 Email 實寄驗收後才開放 public endpoint。
3. Production Discord role／category／class-module 的 live provisioning 與 secure ID capture 已完成；白帳號端到端驗收與 reviewer grant 仍待完成。
4. Core deployment 已完成；Portal／Email 各自保留 rollout 與 rollback gate，不沿用 core PASS 代替驗收。
5. Repository owner、公開 URL、backend origin、CNAME 與首次 Portal rollout 維持人工 gate，暫不阻擋上述上線前工程。

詳細 runtime observation：`docs/ops/PHASE2C_24H_OBSERVATION.md`。
