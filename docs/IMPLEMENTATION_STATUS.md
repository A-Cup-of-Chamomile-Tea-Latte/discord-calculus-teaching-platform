# Implementation status

Last repository／AI handoff reconciliation: 2026-08-24（Asia/Taipei）

> Runtime facts use the latest 2026-08-23 production observation handoff. This Portal maintenance work did not perform a new live probe.

## Canonical snapshot

| 領域               | 現況                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------ |
| Production writer  | Remote Linux 是唯一 production writer；Mac writers 停止                                    |
| Production runtime | 三個 systemd services；最新安全快照為 HEALTHY                                              |
| Production DB      | SQLite schema v6；lifecycle 使用 durable queue／stage resume／retry／idempotency           |
| Repository runtime | 目前 worktree 仍是較舊基線；v6 source 待 observation 後依 ownership 安全吸收，禁止機械覆寫 |
| Google             | SQLite 是 operational authority；Sheets 是 compact projection                              |
| Portal             | 公開／reviewer artifact 分離；學生資訊架構已轉為靜態入口＋最小動態服務                     |
| Portal backend     | 加入申請與單案查詢尚未接線，不因靜態 UI 完成而獲准                                         |
| Email              | 尚未啟用，不列為學生主通知；加入與案件結果採 Discord DM                                    |

## Production observation

- 起點：2026-08-23 17:12（Asia/Taipei）。
- 最早完成：2026-08-24 17:12；時間未走完前不得提前寫成 PASS。
- 起點安全快照：三服務 HEALTHY；lifecycle、cloud projection、private export 與 manual-attention queue 為 0。
- Public close → immediate reopen smoke 已最終收斂；reopen 沿用同一 thread 與案號，不重寄案號。
- production code、schema 或 service config 若換版，24 小時窗口重新起算。

## Portal 現況

### 公開學生面

- Header 收斂為加入與設定、查案件、使用指南。
- 首頁採深綠、暖白與燙金重點，NTU COOL 警示改為紅色；Footer 改連微積分統一教學網。
- 加入頁支援臺大學生／訪客、Discord username、正式 C01–C16 班別與教師標籤。
- 案件查詢契約只允許 content-free status projection；一般與 `-P` 使用同一介面。正式 adapter 尚未接線，public build 停用查詢並指引回 Discord，不用 fixture 冒充成功。
- Discord 指南與使用／隱私說明合併為 `/guide/`。
- 網頁代送、網頁隱密表單與案件詳情頁已退出公開架構。
- 2026-08-24 已完成公開四頁的手機／iPad 橫式瀏覽器 QA、reviewer 16 頁／public 5 頁 artifact 驗證與 A4 landscape 10 頁逐頁列印 QA。

### 內部與封存

- Course Manager reviewer UI 與加入狀態／去重 policy 已建立；正式 adapter 尚未接線。
- `/status/` 改為管理員建造 dashboard；全部 gate 完成後才轉長期 monitor。
- 舊 `/ask/`、`/private-support/`、`/discord-guide/` 留 reviewer 封存提示，public build 移除。
- 封存 stage 不作為新決策來源；需恢復時先寫 decision，再取回必要部分。

## 尚未完成

1. 完成 24 小時 observation 最終 checkpoint，然後安全吸收 v6 production source／docs。
2. 完成 Course Manager 加入申請 backend、SQLite migration、Discord member resolution 與 DM。
3. 完成單案 status lookup backend、auth／rate limit／audit 與 Private 最小揭露。
4. 依最新 UX checklist 完成或隱藏 production `/private open`，不可只改 Portal 文字。
5. Repository owner、公開 URL、backend origin 與首次 deploy 仍逐項人工 gate。
