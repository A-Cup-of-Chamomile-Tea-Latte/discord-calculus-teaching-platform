# Portal Desktop Review Mode

此模式以本機 fixture 審查 reduced case screen；不連 Discord、GAS、Email，不部署，也不保存表單或按鈕操作。

## Review fixture

- 一般案件：`C01-7K4M2Q-0702-1000`
- 匿名案件：`C02-R8N6WX-0702-1100`
- Private fixture：`C99-B4W9K6-0702-1500-P`（不得由 public lookup 確認存在）

案件詳情顯示 Case、Status、Last Update、Last Response、Last Student Activity、Last Read、Last Synced、Latest Teaching Response、Timeline、文字對話、附件 marker、Discord deep link 與結案資訊。附件只顯示「請至 Discord 查看」，不下載、不代理、不重新託管檔案。

`Last Read` 只有在 `VerifiedViewProvider` 回傳 `VERIFIED_VIEW` evidence 時才能填入；載入頁面本身不是已讀證明。Temporary close 與 Close Case 按鈕只是 DOM 內預覽，不寫回任何資料。

## Closure review assumptions

- Manual close：`CLOSED` + `MANUAL` + `closedAt`。
- Answered 且具有 verified view，達可設定的暫結案門檻：`TEMPORARILY_CLOSED` + `AUTO`。
- 達可設定的自動結案門檻：`CLOSED` + `AUTO`。
- 結案後有新活動：`REOPENED` + `reopenedAt`，清除 closure fields。
- 預設 fixture policy 為 3／7 日，但 UI 不硬編碼門檻。

## AI review assumptions

發問表單必須由 Original Poster 主動選 Yes 或 No，沒有預選值。Database fixture 是唯一 source of truth；Discord `AI✓`／`AI×` 只作 projection。OP 選 No 時整案排除；OP 選 Yes 時仍套用其他作者的訊息層級 eligibility interface。
