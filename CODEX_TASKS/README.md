# M3 任務台帳

這是 `CODEX_TASKS/` 的人類導覽與完成度入口；task 檔原始檔名保留為 stable references，避免破壞 report、batch 與交接文件中的精確路徑。

## 狀態規則

- `[Done]`：對應 `docs/reports/TASK-XX-REPORT.md` 明確記為完成，且 [實作狀態](../docs/IMPLEMENTATION_STATUS.md) 將其納入本機 fixture/local baseline。
- `Historical source`：task 是已執行的規格／批次指令，保留供追溯，**不可**因為看到 `[Done]` 就不加審查地重跑。
- `Not started`：尚無對應完成報告或目前狀態文件未納入；本次盤點沒有這類的編號 task。

## 2026-07-26 M3 狀態

| 範圍 | 狀態 | 依據 |
| --- | --- | --- |
| Task 02–08：foundation | Done | `TASK-02` 至 `TASK-08` reports；BATCH-A summary |
| Task 09–14：Portal | Done | `TASK-09` 至 `TASK-14` reports；BATCH-B summary |
| Task 15–19：GAS／Sheets fixture lane | Done | `TASK-15` 至 `TASK-19` reports；BATCH-C summary |
| Task 20–25：Discord bot fixture lane | Done | `TASK-20` 至 `TASK-25` reports；BATCH-D summary |
| Task 26–28：local export／anonymization／import | Done | `TASK-26` 至 `TASK-28` reports；BATCH-E summary |
| Task 29–33：review／integration／handoff | Done | `TASK-29` 至 `TASK-33` reports；BATCH-F summary |
| Task 34：safe foundation follow-up | Done | [`TASK-34-REPORT.md`](../docs/reports/TASK-34-REPORT.md) |
| Task 25A：relocation/hardening | Done（補充 pass） | [`TASK-25A-RELOCATION-HARDENING-REPORT.md`](../docs/reports/TASK-25A-RELOCATION-HARDENING-REPORT.md) |

這裡的 Done 僅表示**獲授權的 fixture/local scope**完成。production、真實 Discord／Google／email／OAuth、真實資料與正式部署仍是 NO-GO；阻擋因素見 [實作狀態](../docs/IMPLEMENTATION_STATUS.md) 與 [下一步](../docs/NEXT_STEPS.md)。

## M3 後續整理建議

1. 新增後續工作時，以 `TASK-35_...` 之後的連續 task number 與同號 report 命名；不要重新編號既有完成 task。
2. 若有取代舊決策，新增 ADR／decision update，不回寫舊 task 的歷史要求。
3. 任何改動 task 路徑的提案，必須同時更新 `MANIFEST.json`、`TASK_MATRIX.md`、所有 Markdown links 與 report references，並通過 link audit；目前沒有必要做這個高風險 rename。

