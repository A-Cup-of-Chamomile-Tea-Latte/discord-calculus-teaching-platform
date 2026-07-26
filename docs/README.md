# 文件總覽（M3）

本目錄是本專案的正式文件入口。M3 的原則是：保留可追溯的歷史任務與 ADR 路徑；用索引、狀態與設定說明改善可讀性，不以大量 rename 破壞既有連結或交接規格。

## 先讀哪裡

| 讀者／目的 | 建議入口 |
| --- | --- |
| 目前範圍、完成度與 production gate | [實作狀態](IMPLEMENTATION_STATUS.md) → [下一步](NEXT_STEPS.md) |
| 本機安裝、測試與 fixture demo | [本機開發](architecture/DEVELOPMENT.md) → [Fixture demo](FIXTURE_DEMO.md) |
| 目前有效的設定與環境變數 | [設定總覽](CONFIGURATION.md) |
| 架構與資料邊界 | [架構索引](architecture/README.md) → [資料模型](DATA_MODEL_OVERVIEW.md) |
| 固定與未決決策 | [ADR／決策索引](decisions/README.md) |
| 操作員的 dump、follow、匿名化與 import | [操作員流程](OPERATOR_WORKFLOW.md) |
| 學生／助教說明 | [學生快速指南](guides/STUDENT_QUICK_GUIDE.md)／[助教快速指南](guides/TA_QUICK_GUIDE.md) |
| 任務實作證據 | [任務報告索引](reports/README.md) 與 [`CODEX_TASKS/README.md`](../CODEX_TASKS/README.md) |

## 文件分層

- **Current（目前有效）**：本檔、`IMPLEMENTATION_STATUS.md`、`NEXT_STEPS.md`、`CONFIGURATION.md`、`architecture/`、`decisions/UNRESOLVED.md` 與各操作指南。
- **Evidence（可追溯證據）**：`reports/` 的 TASK／BATCH 報告；它們記錄當時範圍與測試，不能單獨覆蓋後續決策。
- **Historical decision record（歷史決策）**：`decisions/ADR-*.md` 維持穩定檔名；若被取代，應以新 ADR 或決策更新註記，而非回寫歷史。

## M3 命名與維護規則

1. 不改動 `docs/reports/TASK-XX-REPORT.md`、`docs/decisions/ADR-XXXX-*.md`、或 `CODEX_TASKS/NN_*.md` 的 canonical 路徑；這些是交接與任務規格的可參照名稱。
2. 已完成的 task 在 task 檔標題以 `[Done]` 標示；完整證據仍以同編號 report 為準。
3. 新的現況說明應更新在 Current 文件，並連回相關 report／ADR；不要把新的狀態塞進舊報告。
4. `.env`、token、secret、deployment ID、真實資料與 raw export 不得寫入此目錄。設定只記錄變數名稱、預設與安全邊界。

