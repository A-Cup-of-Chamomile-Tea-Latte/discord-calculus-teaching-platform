# NAP Build 設定來源盤點

> 由 `python -m tools.config_proposal generate` 自動產生。請修改 `config/proposed/`，不要直接編輯本檔。
> 來源優先序：最新確認設定包 → 最新產品決策 → Task 35 狀態 → Task 34 → 早期背景。

| 路徑／來源 | 性質 | 目前效力 | 真實資料 | 可進 Git |
| --- | --- | --- | --- | --- |
| project-exchange/10_CFG_DiscordSide.zip | 最新已確認 Discord Side 設定包 | 有效；最高優先 | 否 | ZIP 否；衍生 proposed config 可 |
| project-exchange/14_Discord_112_113_114_三年比較分析包.zip | 三年彙總比較證據 | 只採彙總結論；不讀原始正文 | 可能含私人研究衍生資料 | ZIP 否；本矩陣可 |
| docs/decisions/PRODUCT_DECISIONS_2026-07-23.md | Task 34 產品決策 | 未與最新 CONFIG 衝突時有效 | 否 | 可 |
| docs/reports/TASK-34-REPORT.md | Task 34 實作與驗證證據 | 歷史實作狀態 | 否 | 可 |
| docs/CONFIGURATION.md | 目前程式 runtime 設定 | 有效；描述 code，不取代產品設定 | 否 | 可 |
| docs/decisions/UNRESOLVED.md | 跨產品／技術未決事項 | 有效；需分層 | 否 | 可 |
| CODEX_TASKS/01_SHARED_CONTEXT.md | 早期共享背景 | 只補充未衝突內容 | 否 | 可 |
| 外部 Task 35 reports／private outputs | 一次性 GET-only 匯出證據 | 不複製進 canonical root | 是 | 不可 |

## 衝突處理

- 最新 Side CONFIG 的 Open／Tracked／Idle／Closed／Auto Closed 與 48h＋48h 規則，取代 Task 34 的展示狀態與 3／7 日規則。
- Task 34 的隨機案號、逐案 AI Yes／No、Working／Archive 分離與 Portal one-case boundary 繼續有效。
- 三年比較只能形成設計證據，不會把舊伺服器直接複製為新設定。
