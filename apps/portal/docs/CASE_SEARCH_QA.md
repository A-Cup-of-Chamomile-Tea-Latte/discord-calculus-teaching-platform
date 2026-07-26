# Case search manual QA

Task 12 的 public case lookup 使用本機 fixture 與 client-side adapter；以下手動檢查於 2026-07-19 執行，沒有連線至 Discord、GAS、Sheets、email 或任何正式服務。

## 測試環境

- Astro preview：`ASTRO_BASE_PATH=/portal-test npm run preview --workspace @calculus/portal -- --host 127.0.0.1 --port 4322`
- URL：`http://127.0.0.1:4322/portal-test/`
- Browser viewport：375 × 812 px
- build base path：`/portal-test/`

## 查詢互動

| 情境 | 輸入 | 預期與結果 |
| --- | --- | --- |
| 可找到 | ` c01 - 7k4m2q - 0702 - 1000 ` | 通過。整理為 `C01-7K4M2Q-0702-1000`，顯示案件標題、狀態、更新時間與 base-safe 詳情連結。 |
| 找不到 | `C01-Z9Y8X7-0702-2359` | 通過。顯示明確的找不到狀態，沒有導向任意案件頁。 |
| 格式錯誤 | `421` | 通過。顯示格式提示，輸入框設為 `aria-invalid="true"`。 |
| 匿名案件 | `C02-R8N6WX-0702-1100` | 通過。詳情顯示「對一般成員匿名」，畫面與 DOM snapshot 都沒有 raw user ID 或 private case ID。 |

## Accessibility

- 頁面有可辨識的「跳到主要內容」連結，目標 `#main-content` 存在。
- 案件輸入框可由 `一般案件編號` accessible name 唯一定位；查詢按鈕也有可辨識文字。
- 所有 `input`、`select`、`textarea` 均有 label 或等價 accessible name；沒有無名稱按鈕。
- 查詢結果區使用 `aria-live="polite"`；格式錯誤同步設定 `aria-invalid="true"`。
- 以鍵盤對 skip link 執行 Enter 後，焦點仍可明確落在該連結；原生連結、按鈕與輸入框未改寫鍵盤語意。
- 匿名案件的 follow-up placeholder 保持 disabled，避免誤以為內容會送出。

## Mobile and base-path checks

- 首頁與匿名案件詳情頁在 375 px 寬度下，`scrollWidth === clientWidth`，沒有水平溢位。
- 頁首導覽可換行，主要內容、卡片、表單與 footer 仍保持可讀。
- 所有站內 absolute links 都以 `/portal-test/` 開頭；沒有逃離 project-site base path 的連結。
- 手動畫面檢查未發現文字被裁切、控制項重疊或 disabled 狀態不清楚。
- Browser console 的 warning/error 數量：0。

## Privacy and update behavior

- Public adapter 只使用允許公開的 projection；Private Support fixture 不會出現在清單或 public lookup。
- 頁面提供明確的「重新整理此案件」連結，沒有 `setInterval`、背景 timer 或 polling。
- Discord action 只顯示 disabled placeholder；沒有真實 server/channel/message URL。
- Public case lookup 不要求 secret token；正式 rate limit、欄位政策與後端存取控制仍留待後續安全任務確認。
