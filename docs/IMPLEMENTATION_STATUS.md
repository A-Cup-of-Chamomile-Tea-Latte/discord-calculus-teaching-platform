# Implementation status

Last repository／AI handoff reconciliation: 2026-08-28（Asia/Taipei）

> 本頁分開記錄 production Bot、GAS provider、Portal staging 與 Discord live provisioning。v13 Bot
> 狀態來自遠端交接與 Discord metadata-only ops smoke；本機沒有直接登入朋友主機。GAS provider
> smoke 已通過，Portal 尚未 external staging，系辦交付維持 `NOT APPROVED`。

## Canonical snapshot

| 領域                 | 現況                                                                                                                                                                                                                                                                              |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Production writer    | Remote Linux 是唯一 production writer；Mac writers 已停止                                                                                                                                                                                                                         |
| Production runtime   | Active release `feab01757897`；三個 systemd services 依遠端交接均 active／enabled；Discord `/ops status` 與 `/ops attention-list` PASS                                                                                                                                            |
| Production DB        | Remote SQLite schema 13；critical queues 與 manual attention 均為 0                                                                                                                                                                                                               |
| Observation          | v13 Bot、metadata-only ops smoke、owner-only GAS provider 實寄、isolated Email service chain 與 Discord 永久入口 live provisioning PASS；白帳號完整 E2E 與 Portal rollout 仍是獨立 gate                                                                                      |
| Repository candidate | Implementation code head `7a22cb6`；branch `codex/portal-post-v13` 已包含 Portal staging package、GAS dual-scope bridge 與 Discord 永久入口。這些 post-v13 code 尚未部署到 production host，不改變 production active release                                                            |
| Google               | SQLite 是 operational authority；Sheets 是 compact projection，不是第二套主資料庫                                                                                                                                                                                                 |
| Portal               | 公開／reviewer artifact 分離；local browser smoke 與 host-bound staging package 流程已完成，package ready but not deployed。Portal 尚未 external staging，也沒有 production hosting                                                                                               |
| Portal backend       | same-origin join／Email verify／one-case lookup 與匿名分 scope session issuer 已在 local candidate 實作；synthetic composition 不接 production。正式 Portal service、origin 與 rollout 尚未接線，public build 預設仍 fail closed                                                  |
| Email                | SQLite durable outbox 與 provider code 已存在；owner-only GAS immutable v14 實寄、收件、duplicate no-op，以及 isolated Portal→outbox→GAS→人工驗碼→`PENDING_REVIEW` service chain 已通過；remote bridge／Discord 白帳號 E2E 尚未通過。Public／Private 案件通知維持 Discord DM-only |

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
- 永久入口 `開啟隱密案件` 已由 targeted provisioner 建立並 live verify。Post-apply 唯讀 plan 為 0 actions／0 unrelated drift；既有 Private category 與動態案件頻道不受影響。先前失敗的 apply 均已自動 rollback，沒有留下多餘 channel 或 mapping。
- Deployment hardening 後的 worktree gate 通過 Portal 61、Config 3、GAS 70、Python 334、Ruff、format、mypy、build、production npm audit 0 與 secret scan；exact commit 由外部 evidence receipt 綁定 archive checksum。
- 最新完整 post-v13 gate 通過 Portal 67、Config 3、GAS 70、Python 374、Ruff、format、mypy、build 與 secret scan 717／0。
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
- Connected public artifact 已在 loopback same-origin browser smoke 完成 Guest Email dialog／申請、一般與 Private lookup；這不取代外部 HTTPS staging 或 production rollout。
- Synthetic staging package builder、installer、rollback、systemd unit、smoke 與 proxy contract 已完成並通過測試。真正可部署的 package 仍須綁定 staging HTTPS origin、base path、loopback port 與 host proxy adapter；目前沒有 external staging deployment。
- `/status/` 是管理員建造 dashboard；所有 gate 完成後才轉長期 monitor。
- 舊 `/ask/`、`/private-support/`、`/discord-guide/` 留 reviewer 封存提示，public build 移除。
- 封存 stage 不是新決策來源；恢復舊設計前須先寫 decision，只取回仍適用的部分。

## 尚未完成

1. 由白帳號在已建立的 `開啟隱密案件` 執行 `/private open`，驗證 ACL、DM、close／reopen／private dump E2E。
2. 取得 staging 的 HTTPS origin、base path、loopback port 與 root-owned proxy adapter facts，產生 exact host-bound package；先部署 synthetic SQLite staging，不接 production authority。
3. External staging 通過 Portal 加入、Email、Case ID lookup、rollback 與白帳號 click-through 後，才評估 production Portal service 與 SQLite 接線。這是新的 production mutation gate。
4. Core deployment 已完成；Portal／Email 與 Discord 永久入口各自保留 rollout／rollback gate，不沿用 core PASS 代替驗收。
5. 系辦交付目前固定為 `NOT APPROVED`；現有 department draft 不是可交付 artifact。只有 PM 明示 `APPROVED FOR DEPARTMENT HANDOFF` 後才能交付或掛上統一教學網。

詳細 runtime observation：`docs/ops/PHASE2C_24H_OBSERVATION.md`。
