# Compact cloud projection schema v2.0.0

`Server Database` 不是完整資料庫，也不是 Discord message archive。Local SQLite 是 operational authority；Google Sheets 只承載人需要查看／操作的充分統計量，以及少量跨系統協作 metadata。

## Carrier decision

| 資料 | 正式載體 | 是否出現在 Sheet | 理由 |
| --- | --- | --- | --- |
| 案件目前狀態、待辦、期限 | Local SQLite | `CaseBoard` 摘要 | TA 需要可視化；不需要全文 |
| 成員目前角色／驗證狀態 | Local SQLite | `Members` 去識別投影 | 方便行政調整；不含姓名、學號、Email、Discord ID |
| Bot／queue 健康狀態 | Local runtime receipts | `Operations` 摘要 | 適合遠端巡檢；不含 PID、log 或 credential |
| 重要狀態轉換 | Local SQLite | `History` 精簡事件 | 只保留有維護意義的 lifecycle event |
| 原始訊息、Private Support、附件 | 受管本機檔案／archive | 不出現 | 內容敏感且不適合表格 |
| 高頻 log／heartbeat 明細 | rotating local log | 只投影最新健康狀態 | Sheet 不是 log system |
| Secret、OAuth／Discord token | 本機 secret carrier | 絕不出現 | `_Settings` 只允許 secret reference，不允許 secret value |
| Schema／程式規則 | Git 文字檔與 migration | `_Settings` 只放版本 receipt | 文字檔可 review、diff、test；Sheet 不是 source code |
| 匯出內容 | 受管檔案 | `_Artifacts` 只有 index/checksum | 大檔與敏感內容留在有 retention 控制的載體 |

## Human views（預設顯示）

| Sheet | 用途 | 明確不保存 |
| --- | --- | --- |
| `Overview` | 當前 KPI、警示與資料時間 | 歷史明細、原始內容 |
| `CaseBoard` | 目前案件狀態、TA 待辦、期限與分析資格 | message body、附件、Private Support |
| `Members` | 不透明 member ref、course alias、角色、成員／驗證狀態、分析預設 | 姓名、學號、Email、Discord ID |
| `Operations` | 兩隻 bot、GAS、projection／queue 的狀態與最新 heartbeat | PID、完整 exception、log body、token |
| `History` | 有意義的 open／close／reopen／verification 等狀態轉換 | 高頻事件與訊息內容 |

## Machine views（預設隱藏）

| Sheet | 用途 | Boundary |
| --- | --- | --- |
| `_CommandInbox` | 帶 idempotency、claim／lease／retry 的命令 metadata | 只存 `payloadRef`，不存 payload 或 credential |
| `_EmailOutbox` | Email 工作 metadata；`providerAcceptedAt` 對應產品語意 `SENT` | 不存地址、subject、body、驗證碼 |
| `_SyncState` | source version、checksum、cursor 與人工確認 receipt | 不作 change history |
| `_Artifacts` | 匯出／sanitized package 的 index、checksum、retention 狀態 | 不存 artifact payload |
| `_Settings` | schema version、data authority 與非 secret 設定 | 不存 secret value |

隱藏頁籤只是降低操作雜訊，不是存取控制。試算表仍必須限制共用範圍；若未來 Machine views 與 TA views 的讀取者不同，應依權限邊界拆成 `TA Operations Console` 與 `System Ledger` 兩份檔案，而不是因頁籤數量拆檔。

## Safe migration from v1.3.0

選單「微積分模組管理」提供：

1. `檢查精簡資料庫遷移（不修改）`
2. `套用精簡資料庫遷移…`

遷移採 fail-closed：

- 只辨識 v1.3.0 的 21 個確切舊受管名稱；
- 除舊 `Settings` 的兩個 schema keys 外，只要任一舊頁籤有資料列，就回報 blocker 且零 mutation；
- 舊 `Settings` 只要有 operator-owned key，也整批停止；
- 通過 preflight 後才建立 10 個新頁、寫入 v2 metadata，再刪除空的舊受管頁；
- 名稱不在 allowlist 的頁籤永遠保留；
- 第二次執行應為 no-op。

Apply 完成後，五個 Machine views 會隱藏，所有新頁凍結 header row、套用淺灰粗體 header 並自動調整欄寬。

## Authenticity boundary

任何 cloud → local fetch 都不能直接覆寫 SQLite。至少要驗證：

1. 來源檔與預期 Spreadsheet 相符；
2. schema version 可支援；
3. source version 單調遞增；
4. checksum 與內容相符；
5. receipt 時間合理；
6. 人工確認本次 import scope。

未來若要自動化，以上 gate 必須先有 executable tests；Sheet 不能被當成比 local SQLite 更新就自動勝出的 source of truth。
