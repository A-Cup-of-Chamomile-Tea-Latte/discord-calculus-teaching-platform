# Portal Desktop Review Mode

此模式以本機 fixture 審查 reduced case screen；不連 Discord、GAS、Email，不部署，也不保存表單或按鈕操作。

## Review fixture

- 一般案件：`C01-7K4M2Q-0702-1000`
- 匿名案件：`C02-R8N6WX-0702-1100`
- Private fixture：`C99-B4W9K6-0702-1500-P`（不得由 public lookup 確認存在）

學生案件詳情只顯示案件編號、處理狀態、最近更新、教學團隊最近回覆、公開對話與附件數量。同步、雜湊、資料來源、分析資格與管理操作只留在內部審查頁。附件只顯示「請至 Discord 查看」，不下載、不代理、不重新託管檔案。

## Closure review assumptions

- Open 由負責助教接手後進入 `TRACKED`。
- 自教學團隊最後回覆起 48 小時沒有學生回應，進入 `IDLE` 並寄出提醒。
- `IDLE` 後再 48 小時沒有回應，進入 `AUTO_CLOSED`。
- 只有案件負責人可手動設為 `CLOSED`；學生端不顯示手動結案控制。
- `IDLE`、`CLOSED` 或 `AUTO_CLOSED` 有新回應時回到 `TRACKED`；重新開啟只記時間軸事件。

## AI review assumptions

發問表單必須由 Original Poster 主動選 Yes 或 No，沒有預選值。Database fixture 是唯一 source of truth；Discord `AI✓`／`AI×` 只作 projection。OP 選 No 時整案排除；OP 選 Yes 時仍套用其他作者的訊息層級 eligibility interface。
