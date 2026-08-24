# Implementation status

Last repository／AI handoff reconciliation: 2026-08-24（Asia/Taipei）

> 本頁分開記錄「已驗證的 production」與「repository 候選版」。本輪整合沒有重新連線 remote、部署、重啟服務或寫入 live data，因此不把本機測試結果冒充 production 狀態。

## Canonical snapshot

| 領域 | 現況 |
| --- | --- |
| Production writer | Remote Linux 是唯一 production writer；Mac writers 已停止 |
| Production runtime | 三個 systemd services；2026-08-23 17:12 的最新安全交接快照為 `HEALTHY` |
| Production DB | Remote SQLite schema v6；lifecycle 使用 durable queue／stage resume／retry／idempotency |
| Observation | 2026-08-23 17:12 重新起算；最早 2026-08-24 17:12 才可做最終 checkpoint，本輪尚未重新探測 |
| Repository candidate | Portal、115-1 academic data、production v6 基礎與 Bot UX 已整合；Bot candidate schema v10，尚未部署 |
| Google | SQLite 是 operational authority；Sheets 是 compact projection，不是第二套主資料庫 |
| Portal | 公開／reviewer artifact 分離；學生面收斂為靜態資訊入口與最小動態服務 |
| Portal backend | 加入申請與單案查詢尚未接線；public build 因此 fail closed |
| Email | 尚未啟用；加入與案件結果採 Discord DM |

## Repository integration checkpoint

- 案件狀態統一為 `OPEN`、`TRACKED`、`IDLE`、`CLOSED`、`AUTO_CLOSED`；`REOPEN` 是 lifecycle event，不是長期狀態。
- 計時採 48＋48 小時，且只在教學團隊真的回覆後啟動；「接手案件」不再冒充回覆。
- 案號採 `C{classCode}-{token}-{MMDD}-{HHmm}`；Private Support 固定 `C99…-P`。
- Forum 標題採 `[M{n} | C{classCode}][mainTag] userTitle`，班別與 Module 從正式設定取得。
- 加入申請後端重驗 NTU Mail、選填 Gmail、C01–C16 與 Discord username；Course Manager 使用兩級權限、五態審核、Discord DM 與持久暱稱配置。
- Private Support 由 Discord `/private open` 取得同一套主標籤與 AI 選擇，再建立受限頻道；圖片留在 Discord，SQLite 只保存必要案件狀態與 Discord 參照。
- 舊 Private dump 互動入口已停用；歷史資料與 migration 保留，未草率刪除。
- public case lookup 只允許 content-free projection：案號、類型、狀態、更新時間、是否已回覆與 Discord 連結。
- Silent Walker 完成後，本機全套品質門通過：Python 278、Portal 61、GAS 66、Config Studio 3；public artifact 為 5 頁／54 個 base-safe references。
- schema-shaped v6 暫存副本已演練到 v10：ledger 1–10 完整、`integrity_check=ok`、核心 row counts 不變。這不取代 production consistent backup rehearsal。

## Portal 現況

### 公開學生面

- Header 收斂為加入與設定、查案件、使用指南；視覺為深綠、暖白與燙金重點。
- 加入頁支援臺大學生／訪客、Discord username、正式 C01–C16 班別與教師標籤。
- 一般與 `-P` 案號共用查詢介面；正式 adapter 尚未接線，public build 不以 fixture 冒充成功。
- Discord 指南與使用／隱私說明合併為 `/guide/`；Portal 不代收提問內容或附件。
- reviewer 內部頁與 public artifact 已分離；public artifact 只保留允許的 5 頁。

### 內部與封存

- Course Manager reviewer UI 與加入狀態／去重 policy 已建立；same-origin adapter 尚未接線。
- `/status/` 是管理員建造 dashboard；所有 gate 完成後才轉長期 monitor。
- 舊 `/ask/`、`/private-support/`、`/discord-guide/` 留 reviewer 封存提示，public build 移除。
- 封存 stage 不是新決策來源；恢復舊設計前須先寫 decision，只取回仍適用的部分。

## 尚未完成

1. 取得 2026-08-24 17:12 後的 owner-only production 安全摘要，完成 observation 最終 checkpoint。
2. 在 production DB 備份副本演練 v6 → v10；通過後仍須另行授權才可部署。
3. 接上 Portal same-origin 加入申請與單案查詢 backend，完成 CSRF、rate limit、audit 與 Private 最小揭露。
4. 完成 production Discord role／category／class-module 設定映射與白帳號端到端驗收。
5. Repository owner、公開 URL、backend origin 與首次 Portal deploy 仍是人工 gate。

詳細 runtime observation：`docs/ops/PHASE2C_24H_OBSERVATION.md`。
